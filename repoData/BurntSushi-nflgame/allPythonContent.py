__FILENAME__ = alert
"""
A module that provides convenience functions for sending alerts. Currently
this includes sending text (SMS) messages or emails.

This is accomplished through two mechanisms: Google Voice B{or} SMTP.

Using Google Voice
==================
To use Google Voice, this module requires a Google Voice account and depends on
pygooglevoice to access your Google Voice account.

You can sign up for a Google Voice account at
U{voice.google.com<http://voice.google.com>}.

pygooglevoice is in PyPI but unfortunately is not configured properly. You'll
have to download the source and run::

    sudo python2 setup.py install

in the directory containing setup.py. You can download pygooglevoice at
U{code.google.com/p/pygooglevoice
<http://code.google.com/p/pygooglevoice/downloads/list/>}.

A quick example of sending an SMS message with Google Voice::

    import nflgame.alert
    nflgame.alert.google_voice_login('YOUR GMAIL ADDRESS', 'YOUR PASSWORD')
    nflgame.alert.sms('1112223333', 'This is a text message!')

If you don't have a Google Voice account or don't want to install a third
party library, you can still use this module but the C{google_voice_login}
function will not work.

The disadvantage of using Google Voice is that it limits text messages. Since
you'll probably be using this module to send a fair number of alerts, this
might be prohibitive.

Using SMTP
==========
SMTP can be used to send SMS messages or emails. For sending SMS messages,
the SMTP approach requires that you know the provider of the recipient's
cell phone (i.e., Verizon, Sprint, T-Mobile). Although this is a burden,
sending SMS messages through email doesn't seem to be as vigorously rate
limited as Google Voice is.

To send an SMS message using your GMail account::

    import nflgame.alert
    nflgame.alert.gmail_login('YOUR GMAIL ADDRESS', 'YOUR PASSWORD')
    nflgame.alert.sms('1112223333', 'Test message', provider='Verizon')

In this case, the C{provider} parameter is required.

Similarly, you can send email alerts with your GMail account::

    import nflgame.alert
    nflgame.alert.gmail_login('YOUR GMAIL ADDRESS', 'YOUR PASSWORD')
    nflgame.alert.email('somewhere@someplace.com', 'Email message')

Once you login to GMail using C{gmail_login}, you may send both text messages
and emails. You may be logged into Google Voice and GMail at the same time.

Using SMTP without GMail
------------------------
You may use SMTP servers that aren't GMail by using C{smtp_login}. In fact,
C{gmail_login} is a special case of C{smtp_login}::

    def gmail_login(email, passwd):
        def connect():
            gmail = smtplib.SMTP('smtp.gmail.com', port=587)
            gmail.starttls()
            return gmail

        smtp_login(email, passwd, connect)

The connection setup must be provided as a function because it will
typically need to be reused in a long running program. (i.e., If you don't
send an alert for a while, you'll probably be disconnected from the SMTP
server. In which case, the connection setup will be executed again.)
"""
import smtplib
import sys

try:
    import googlevoice
    _gv_available = True
except ImportError:
    _gv_available = False

_voice = None
"""Store the googlevoice.Voice instance."""

_smtp = None
"""Store the smptplib.SMTP session instance."""

_email_from = None
"""Stores the login email address for use in the 'from' field."""

_smtp_connect = None
"""A function that will (re)connect and login"""


def google_voice_login(email, passwd):
    """
    Logs into your Google Voice account with your full email address
    (i.e., 'something@gmail.com') and password. This MUST be called before
    using send without the provider parameter.
    login only needs to be called once per program execution.

    Note that your Google Voice login information is probably the same as your
    gmail login information. Please be careful with your login credentials!
    (It is not a bad idea to setup an entirely separate Google Voice account
    just for sending SMS.)
    """
    global _voice

    if not _gv_available:
        print >> sys.stderr, "The pygooglevoice Python package is required " \
                             "in order to use Google Voice."
        return

    _voice = googlevoice.Voice()
    _voice.login(email, passwd)


def smtp_login(email, passwd, connectfun):
    """
    Logs into an SMTP mail server. connectfun should be a function that
    takes no parameters and returns an smtplib.SMTP instance that is ready
    to be logged into. (See the source of gmail_login for an example.)

    username and passwd are then used to log into that smtplib.SMTP instance.

    connectfun may be called again automatically if the SMTP connection
    is broken during program execution.
    """
    global _email_from, _smtp, _smtp_connect

    def connect():
        smtp = connectfun()
        smtp.login(email, passwd)
        return smtp

    _email_from = email
    _smtp_connect = connect
    _smtp = _smtp_connect()


def gmail_login(email, passwd):
    """
    Logs into your GMail account with your full email address
    (i.e., 'something@gmail.com') and password. gmail_login MUST be called
    before using sms with the provider parameter. It only needs to be called
    once per program execution.
    """
    def connect():
        gmail = smtplib.SMTP('smtp.gmail.com', port=587)
        gmail.starttls()
        return gmail

    smtp_login(email, passwd, connect)


def email(to_email, msg, from_email=None):
    """
    Sends an email to to_email with a message containing msg.

    from_email is an optional parameter that specifies the 'from'
    email address. If gmail_login was used, this is automatically
    populated using the login email address. Otherwise it is left empty.
    """
    assert _smtp is not None, \
        "Either gmail_login or smtp_login must be called to setup an " \
        "smtplib.SMTP instance."

    from_email_ = ''
    if from_email is not None:
        from_email_ = from_email
    elif _email_from is not None:
        from_email_ = _email_from

    headers = [
        'To: %s' % to_email,
        'From: %s' % from_email_,
        'Subject: nflgame alert',
    ]
    full_msg = '%s\r\n\r\n%s' % ('\r\n'.join(headers), msg)
    _send_email(from_email_, to_email, full_msg)


def sms(phone_number, msg, provider=None):
    """
    Sends an SMS message to phone_number (which should be a string) with
    a message containing msg.

    If you're using Google Voice to send SMS messages, google_voice_login
    MUST be called before sms can be called. google_voice_login only needs to
    be called once per program execution.

    The provider parameter can be used to send SMS messages via email. It
    is necessary because SMS messages are sent by sending a message to
    an email like '111222333@vtext.com' or '1112223333@txt.att.net'. Thus,
    each phone number must be paired with a provider.

    A provider can be specified either as a carrier name (i.e., 'Verizon' or
    'ATT'), or as simply the domain (i.e., 'vtext.com' or 'txt.att.net').
    Supported providers are in the module level providers variable. Please
    feel free to add to it and submit a pull request.

    The provider parameter is not currently used, but is anticipated if this
    module provides a way to send SMS messages via emails. A provider will be
    required to look up the email domain. (i.e., for Verizon it's 'vtext.com'.)

    Note that these are SMS messages, and each SMS message is limited to
    160 characters. If msg is longer than that and you're using Google Voice,
    it will be broken up into multiple SMS messages (hopefully). Otherwise,
    if you're sending SMS messages via email, the behavior will vary
    depending upon your carrier.
    """
    if provider is None:
        assert _voice is not None, \
            'You must login to Google Voice using google_voice_login before ' \
            'sending an sms without the provider parameter.'
    if provider is not None:
        assert _smtp is not None, \
            'You must login to an SMTP server using gmail_login or by ' \
            'passing an smtplib.SMTP instance via the smtp parameter' \
            'before sending an sms with the provider parameter.'

    if provider is None:
        _google_voice_sms(phone_number, msg)
    else:
        to = '%s@%s' % (phone_number, providers.get(provider, provider))
        _send_email('', to, 'To: %s\r\n\r\n%s' % (to, msg))


def _google_voice_sms(phone_number, msg):
    """
    Sends an SMS message to phone_number (which should be a string) with
    a message containing msg.

    google_voice_login MUST be called before _google_voice_sms can be called.
    google_voice_login only needs to be called once per program execution.

    Note that these are SMS messages, and each SMS message is limited to
    160 characters. If msg is longer than that, it will be broken up into
    multiple SMS messages.
    """
    try:
        _voice.send_sms(phone_number, msg)
    except googlevoice.ValidationError:
        # I seem to be getting these but the text messages still go
        # through (eventually).
        pass


def _send_email(from_email, to_email, msg):
    """
    Sends an email using nflgame.alert._smtp. It handles a connection that has
    been disconnected, and reconnects.

    Note that this only works if smtp_login (or gmail_login) was used.
    """
    global _smtp

    try:
        _smtp.sendmail(from_email, to_email, msg)
    except smtplib.SMTPServerDisconnected:
        _smtp = _smtp_connect()
        _smtp.sendmail(from_email, to_email, msg)


providers = {
    'ATT': 'txt.att.net',
    'Boost': 'myboostmobile.com',
    'Cricket': 'sms.mycricket.com',
    'Sprint': 'messaging.sprintpcs.com',
    'T-Mobile': 'tmomail.net',
    'Verizon': 'vtext.com',
    'Virgin Mobile': 'vmobl.com',
}
"""
A dictionary of providers. The keys are English name identifiers of a
SMS provider. The values are domain suffixes that come after the
'@' symbol in an email address.
"""

########NEW FILE########
__FILENAME__ = game
from collections import namedtuple
import os
import os.path as path
import gzip
import json
import socket
import sys
import urllib2

from nflgame import OrderedDict
import nflgame.player
import nflgame.sched
import nflgame.seq
import nflgame.statmap

_MAX_INT = sys.maxint

_jsonf = path.join(path.split(__file__)[0], 'gamecenter-json', '%s.json.gz')
_json_base_url = "http://www.nfl.com/liveupdate/game-center/%s/%s_gtd.json"

GameDiff = namedtuple('GameDiff', ['before', 'after', 'plays', 'players'])
"""
Represents the difference between two points in time of the same game
in terms of plays and player statistics.
"""

TeamStats = namedtuple('TeamStats',
                       ['first_downs', 'total_yds', 'passing_yds',
                        'rushing_yds', 'penalty_cnt', 'penalty_yds',
                        'turnovers', 'punt_cnt', 'punt_yds', 'punt_avg',
                        'pos_time'])
"""A collection of team statistics for an entire game."""


class FieldPosition (object):
    """
    Represents field position.

    The representation here is an integer offset where the 50 yard line
    corresponds to '0'. Being in the own territory corresponds to a negative
    offset while being in the opponent's territory corresponds to a positive
    offset.

    e.g., NE has the ball on the NE 45, the offset is -5.
    e.g., NE has the ball on the NYG 2, the offset is 48.

    This representation allows for gains in any particular play to be added
    to the field offset to get the new field position as the result of the
    play.
    """
    def __new__(cls, pos_team=None, yardline=None, offset=None):
        if not yardline and offset is None:
            return None
        return object.__new__(cls)

    def __init__(self, pos_team=None, yardline=None, offset=None):
        """
        pos_team is the team on offense, and yardline is a string formatted
        like 'team-territory yard-line'. e.g., "NE 32".

        An offset can be given directly by specifying an integer for offset.
        """
        if isinstance(offset, int):
            self.offset = offset
            return
        if yardline == '50':
            self.offset = 0
            return

        territory, yd_str = yardline.split()
        yd = int(yd_str)
        if territory == pos_team:
            self.offset = -(50 - yd)
        else:
            self.offset = 50 - yd

    def __cmp__(self, other):
        if isinstance(other, int):
            return cmp(self.offset, other)
        return cmp(self.offset, other.offset)

    def __str__(self):
        if self.offset > 0:
            return 'OPP %d' % (50 - self.offset)
        elif self.offset < 0:
            return 'OWN %d' % (50 + self.offset)
        else:
            return 'MIDFIELD'

    def add_yards(self, yards):
        """
        Returns a new field position with the yards added to self.
        Yards may be negative.
        """
        newoffset = max(-50, min(50, self.offset + yards))
        return FieldPosition(offset=newoffset)


class PossessionTime (object):
    """
    Represents the amount of time a drive lasted in (minutes, seconds).
    """
    def __init__(self, clock):
        self.clock = clock

        try:
            self.minutes, self.seconds = map(int, self.clock.split(':'))
        except ValueError:
            self.minutes, self.seconds = 0, 0

    def total_seconds(self):
        """
        Returns the total number of seconds that this possession lasted for.
        """
        return self.seconds + self.minutes * 60

    def __cmp__(self, other):
        a, b = (self.minutes, self.seconds), (other.minutes, other.seconds)
        return cmp(a, b)

    def __add__(self, other):
        new_time = PossessionTime('0:00')
        total_seconds = self.total_seconds() + other.total_seconds()
        new_time.minutes = total_seconds / 60
        new_time.seconds = total_seconds % 60
        new_time.clock = '%.2d:%.2d' % (new_time.minutes, new_time.seconds)
        return new_time

    def __sub__(self, other):
        assert self >= other
        new_time = PossessionTime('0:00')
        total_seconds = self.total_seconds() - other.total_seconds()
        new_time.minutes = total_seconds / 60
        new_time.seconds = total_seconds % 60
        new_time.clock = '%.2d:%.2d' % (new_time.minutes, new_time.seconds)
        return new_time

    def __str__(self):
        return self.clock


class GameClock (object):
    """
    Represents the current time in a game. Namely, it keeps track of the
    quarter and clock time. Also, GameClock can represent whether
    the game hasn't started yet, is half time or if it's over.
    """
    def __init__(self, qtr, clock):
        self.qtr = qtr
        self.clock = clock

        try:
            self._minutes, self._seconds = map(int, self.clock.split(':'))
        except ValueError:
            self._minutes, self._seconds = 0, 0
        except AttributeError:
            self._minutes, self._seconds = 0, 0
        try:
            self.__qtr = int(self.qtr)
            if self.__qtr >= 3:
                self.__qtr += 1  # Let halftime be quarter 3
        except ValueError:
            if self.is_pregame():
                self.__qtr = 0
            elif self.is_halftime():
                self.__qtr = 3
            elif self.is_final():
                self.__qtr = sys.maxint
            else:
                assert False, 'Unknown QTR value: "%s"' % self.qtr

    @property
    def quarter(self):
        return self.__qtr

    @quarter.setter
    def quarter(self, value):
        if isinstance(value, int):
            assert value >= 0 and value <= 4
            self.qtr = str(value)
            self.__qtr = value
        else:
            self.qtr = value
            self.__qtr = 0

    def is_pregame(self):
        return self.qtr == 'Pregame'

    def is_halftime(self):
        return self.qtr == 'Halftime'

    def is_final(self):
        return 'final' in self.qtr.lower()

    def __cmp__(self, other):
        if self.__qtr != other.__qtr:
            return cmp(self.__qtr, other.__qtr)
        elif self._minutes != other._minutes:
            return cmp(other._minutes, self._minutes)
        return cmp(other._seconds, self._seconds)

    def __str__(self):
        """
        Returns a nicely formatted string indicating the current time of the
        game. Examples include "Q1 10:52", "Q4 1:25", "Pregame", "Halftime"
        and "Final".
        """
        try:
            q = int(self.qtr)
            return 'Q%d %s' % (q, self.clock)
        except ValueError:
            return self.qtr


class Game (object):
    """
    Game represents a single pre- or regular-season game. It provides a window
    into the statistics of every player that played into the game, along with
    the winner of the game, the score and a list of all the scoring plays.
    """

    def __new__(cls, eid=None, fpath=None):
        # If we can't get a valid JSON data, exit out and return None.
        try:
            rawData = _get_json_data(eid, fpath)
        except urllib2.URLError:
            return None
        if rawData is None or rawData.strip() == '{}':
            return None
        game = object.__new__(cls)
        game.rawData = rawData

        try:
            if eid is not None:
                game.eid = eid
                game.data = json.loads(game.rawData)[game.eid]
            else:  # For when we have rawData (fpath) and no eid.
                game.eid = None
                game.data = json.loads(game.rawData)
                for k, v in game.data.iteritems():
                    if isinstance(v, dict):
                        game.eid = k
                        game.data = v
                        break
                assert game.eid is not None
        except ValueError:
            return None

        return game

    def __init__(self, eid=None, fpath=None):
        """
        Creates a new Game instance given a game identifier.

        The game identifier is used by NFL.com's GameCenter live update web
        pages. It is used to construct a URL to download JSON data for the
        game.

        If the game has been completed, the JSON data will be cached to disk
        so that subsequent accesses will not re-download the data but instead
        read it from disk.

        When the JSON data is written to disk, it is compressed using gzip.
        """
        # Make the schedule info more accessible.
        self.schedule = nflgame.sched.games.get(self.eid, None)

        # Home and team cumulative statistics.
        self.home = self.data['home']['abbr']
        self.away = self.data['away']['abbr']
        self.stats_home = _json_team_stats(self.data['home']['stats']['team'])
        self.stats_away = _json_team_stats(self.data['away']['stats']['team'])

        # Load up some simple static values.
        self.gamekey = nflgame.sched.games[self.eid]['gamekey']
        self.time = GameClock(self.data['qtr'], self.data['clock'])
        self.down = _tryint(self.data['down'])
        self.togo = _tryint(self.data['togo'])
        self.score_home = int(self.data['home']['score']['T'])
        self.score_away = int(self.data['away']['score']['T'])
        for q in (1, 2, 3, 4, 5):
            for team in ('home', 'away'):
                score = self.data[team]['score'][str(q)]
                self.__dict__['score_%s_q%d' % (team, q)] = int(score)

        if not self.game_over():
            self.winner = None
        else:
            if self.score_home > self.score_away:
                self.winner = self.home
                self.loser = self.away
            elif self.score_away > self.score_home:
                self.winner = self.away
                self.loser = self.home
            else:
                self.winner = '%s/%s' % (self.home, self.away)
                self.loser = '%s/%s' % (self.home, self.away)

        # Load the scoring summary into a simple list of strings.
        self.scores = []
        for k in sorted(map(int, self.data['scrsummary'])):
            play = self.data['scrsummary'][str(k)]
            s = '%s - Q%d - %s - %s' \
                % (play['team'], play['qtr'], play['type'], play['desc'])
            self.scores.append(s)

        # Check to see if the game is over, and if so, cache the data.
        if self.game_over() and not os.access(_jsonf % eid, os.R_OK):
            self.save()

    def is_home(self, team):
        """Returns true if team (i.e., 'NE') is the home team."""
        return team == self.home

    def season(self):
        """Returns the year of the season this game belongs to."""
        year = int(self.eid[0:4])
        month = int(self.eid[4:6])
        if month <= 3:
            year -= 1
        return year

    def game_over(self):
        """game_over returns true if the game is no longer being played."""
        return self.time.is_final()

    def playing(self):
        """playing returns true if the game is currently being played."""
        return not self.time.is_pregame() and not self.time.is_final()

    def save(self, fpath=None):
        """
        Save the JSON data to fpath. This is done automatically if the
        game is over.
        """
        if fpath is None:
            fpath = _jsonf % self.eid
        try:
            print >> gzip.open(fpath, 'w+'), self.rawData,
        except IOError:
            print >> sys.stderr, "Could not cache JSON data. Please " \
                                 "make '%s' writable." \
                                 % os.path.dirname(fpath)

    def nice_score(self):
        """
        Returns a string of the score of the game.
        e.g., "NE (32) vs. NYG (0)".
        """
        return '%s (%d) at %s (%d)' \
               % (self.away, self.score_away, self.home, self.score_home)

    def max_player_stats(self):
        """
        Returns a GenPlayers sequence of player statistics that combines
        game statistics and play statistics by taking the max value of
        each corresponding statistic.

        This is useful when accuracy is desirable. Namely, using only
        play-by-play data or using only game statistics can be unreliable.
        That is, both are inconsistently correct.

        Taking the max values of each statistic reduces the chance of being
        wrong (particularly for stats that are in both play-by-play data
        and game statistics), but does not eliminate them.
        """
        game_players = list(self.players)
        play_players = list(self.drives.plays().players())
        max_players = OrderedDict()

        # So this is a little tricky. It's possible for a player to have
        # only statistics at the play level, and therefore not be represented
        # in the game level statistics. Therefore, we initialize our
        # max_players with play-by-play stats first. Then go back through
        # and combine them with available game statistics.
        for pplay in play_players:
            newp = nflgame.player.GamePlayerStats(pplay.playerid,
                                                  pplay.name, pplay.home,
                                                  pplay.team)
            maxstats = {}
            for stat, val in pplay._stats.iteritems():
                maxstats[stat] = val

            newp._overwrite_stats(maxstats)
            max_players[pplay.playerid] = newp

        for newp in max_players.itervalues():
            for pgame in game_players:
                if pgame.playerid != newp.playerid:
                    continue

                maxstats = {}
                for stat, val in pgame._stats.iteritems():
                    maxstats[stat] = max([val,
                                          newp._stats.get(stat, -_MAX_INT)])

                newp._overwrite_stats(maxstats)
                break
        return nflgame.seq.GenPlayerStats(max_players)

    def __getattr__(self, name):
        if name == 'players':
            self.__players = _json_game_player_stats(self, self.data)
            self.players = nflgame.seq.GenPlayerStats(self.__players)
            return self.players
        if name == 'drives':
            self.__drives = _json_drives(self, self.home, self.data['drives'])
            self.drives = nflgame.seq.GenDrives(self.__drives)
            return self.drives
        raise AttributeError

    def __sub__(self, other):
        return diff(other, self)

    def __str__(self):
        return self.nice_score()


def diff(before, after):
    """
    Returns the difference between two points of time in a game in terms of
    plays and player statistics. The return value is a GameDiff namedtuple
    with two attributes: plays and players. Each contains *only* the data
    that is in the after game but not in the before game.

    This is useful for sending alerts where you're guaranteed to see each
    play statistic only once (assuming NFL.com behaves itself).
    """
    assert after.eid == before.eid

    plays = []
    after_plays = list(after.drives.plays())
    before_plays = list(before.drives.plays())
    for play in after_plays:
        if play not in before_plays:
            plays.append(play)

    # You might think that updated play data is enough. You could scan
    # it for statistics you're looking for (like touchdowns).
    # But sometimes a play can sneak in twice if its description gets
    # updated (late call? play review? etc.)
    # Thus, we do a diff on the play statistics for player data too.
    _players = OrderedDict()
    after_players = list(after.max_player_stats())
    before_players = list(before.max_player_stats())
    for aplayer in after_players:
        has_before = False
        for bplayer in before_players:
            if aplayer.playerid == bplayer.playerid:
                has_before = True
                pdiff = aplayer - bplayer
                if pdiff is not None:
                    _players[aplayer.playerid] = pdiff
        if not has_before:
            _players[aplayer.playerid] = aplayer
    players = nflgame.seq.GenPlayerStats(_players)

    return GameDiff(before=before, after=after, plays=plays, players=players)


class Drive (object):
    """
    Drive represents a single drive in an NFL game. It contains a list
    of all plays that happened in the drive, in chronological order.
    It also contains meta information about the drive such as the start
    and stop times and field position, length of possession, the number
    of first downs and a short descriptive string of the result of the
    drive.
    """
    def __init__(self, game, drive_num, home_team, data):
        if data is None or 'plays' not in data or len(data['plays']) == 0:
            return
        self.game = game
        self.drive_num = drive_num
        self.team = data['posteam']
        self.home = self.team == home_team
        self.first_downs = int(data['fds'])
        self.result = data['result']
        self.penalty_yds = int(data['penyds'])
        self.total_yds = int(data['ydsgained'])
        self.pos_time = PossessionTime(data['postime'])
        self.play_cnt = int(data['numplays'])
        self.field_start = FieldPosition(self.team, data['start']['yrdln'])
        self.time_start = GameClock(data['start']['qtr'],
                                    data['start']['time'])

        # When the game is over, the yardline isn't reported. So find the
        # last play that does report a yardline.
        if data['end']['yrdln'].strip():
            self.field_end = FieldPosition(self.team, data['end']['yrdln'])
        else:
            self.field_end = None
            playids = sorted(map(int, data['plays'].keys()), reverse=True)
            for pid in playids:
                yrdln = data['plays'][str(pid)]['yrdln'].strip()
                if yrdln:
                    self.field_end = FieldPosition(self.team, yrdln)
                    break
            if self.field_end is None:
                self.field_end = FieldPosition(self.team, '50')

        # When a drive lasts from Q1 to Q2 or Q3 to Q4, the 'end' doesn't
        # seem to change to the proper quarter. So scan all of the plays
        # and use the maximal quarter listed. (Just taking the last doesn't
        # seem to always work.)
        # lastplayid = str(max(map(int, data['plays'].keys())))
        # endqtr = data['plays'][lastplayid]['qtr']
        qtrs = [p['qtr'] for p in data['plays'].values()]
        maxq = str(max(map(int, qtrs)))
        self.time_end = GameClock(maxq, data['end']['time'])

        # One last sanity check. If the end time is less than the start time,
        # then bump the quarter if it seems reasonable.
        # This technique will blow up if a drive lasts more than fifteen
        # minutes and the quarter numbering is messed up.
        if self.time_end <= self.time_start \
                and self.time_end.quarter in (1, 3):
            self.time_end.quarter += 1

        self.__plays = _json_plays(self, data['plays'])
        self.plays = nflgame.seq.GenPlays(self.__plays)

    def __add__(self, other):
        """
        Adds the statistics of two drives together.

        Note that once two drives are added, the following fields
        automatically get None values: result, field_start, field_end,
        time_start and time_end.
        """
        assert self.team == other.team, \
            'Cannot add drives from different teams "%s" and "%s".' \
            % (self.team, other.team)
        new_drive = Drive(None, 0, '', None)
        new_drive.team = self.team
        new_drive.home = self.home
        new_drive.first_downs = self.first_downs + other.first_downs
        new_drive.penalty_yds = self.penalty_yds + other.penalty_yds
        new_drive.total_yds = self.total_yds + other.total_yds
        new_drive.pos_time = self.pos_time + other.pos_time
        new_drive.play_cnt = self.play_cnt + other.play_cnt
        new_drive.__plays = self.__plays + other.__plays
        new_drive.result = None
        new_drive.field_start = None
        new_drive.field_end = None
        new_drive.time_start = None
        new_drive.time_end = None
        return new_drive

    def __str__(self):
        return '%s (Start: %s, End: %s) %s' \
               % (self.team, self.time_start, self.time_end, self.result)


class Play (object):
    """
    Play represents a single play. It contains a list of all players
    that participated in the play (including offense, defense and special
    teams). The play also includes meta information about what down it
    is, field position, clock time, etc.

    Play objects also contain team-level statistics, such as whether the
    play was a first down, a fourth down failure, etc.
    """
    def __init__(self, drive, playid, data):
        self.data = data
        self.drive = drive
        self.playid = playid
        self.team = data['posteam']
        self.home = self.drive.home
        self.desc = data['desc']
        self.note = data['note']
        self.down = int(data['down'])
        self.yards_togo = int(data['ydstogo'])
        self.touchdown = 'touchdown' in self.desc.lower()
        self._stats = {}

        if not self.team:
            self.time, self.yardline = None, None
        else:
            self.time = GameClock(data['qtr'], data['time'])
            self.yardline = FieldPosition(self.team, data['yrdln'])

        # Load team statistics directly into the Play instance.
        # Things like third down attempts, first downs, etc.
        if '0' in data['players']:
            for info in data['players']['0']:
                if info['statId'] not in nflgame.statmap.idmap:
                    continue
                statvals = nflgame.statmap.values(info['statId'],
                                                  info['yards'])
                for k, v in statvals.iteritems():
                    v = self.__dict__.get(k, 0) + v
                    self.__dict__[k] = v
                    self._stats[k] = v

        # Load the sequence of "events" in a play into a list of dictionaries.
        self.events = _json_play_events(data['players'])

        # Now load cumulative player data for this play into
        # a GenPlayerStats generator. We then flatten this data
        # and add it to the play itself so that plays can be
        # filter by these statistics.
        self.__players = _json_play_players(self, data['players'])
        self.players = nflgame.seq.GenPlayerStats(self.__players)
        for p in self.players:
            for k, v in p.stats.iteritems():
                # Sometimes we may see duplicate statistics (like tackle
                # assists). Let's just overwrite in this case, since this
                # data is from the perspective of the play. i.e., there
                # is one assisted tackle rather than two.
                self.__dict__[k] = v
                self._stats[k] = v

    def has_player(self, playerid):
        """Whether a player with id playerid participated in this play."""
        return playerid in self.__players

    def __str__(self):
        if self.team:
            if self.down != 0:
                return '(%s, %s, Q%d, %d and %d) %s' \
                       % (self.team, self.data['yrdln'], self.time.qtr,
                          self.down, self.yards_togo, self.desc)
            else:
                return '(%s, %s, Q%d) %s' \
                       % (self.team, self.data['yrdln'], self.time.qtr,
                          self.desc)
        return self.desc

    def __eq__(self, other):
        """
        We use the play description to determine equality because the
        play description can be changed. (Like when a play is reversed.)
        """
        return self.playid == other.playid and self.desc == other.desc

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError
        return 0


def _json_team_stats(data):
    """
    Takes a team stats JSON entry and converts it to a TeamStats namedtuple.
    """
    return TeamStats(
        first_downs=int(data['totfd']),
        total_yds=int(data['totyds']),
        passing_yds=int(data['pyds']),
        rushing_yds=int(data['ryds']),
        penalty_cnt=int(data['pen']),
        penalty_yds=int(data['penyds']),
        turnovers=int(data['trnovr']),
        punt_cnt=int(data['pt']),
        punt_yds=int(data['ptyds']),
        punt_avg=int(data['ptavg']),
        pos_time=PossessionTime(data['top']))


def _json_drives(game, home_team, data):
    """
    Takes a home or away JSON entry and converts it to a list of Drive
    objects.
    """
    drive_nums = []
    for drive_num in data:
        try:
            drive_nums.append(int(drive_num))
        except:
            pass
    drives = []
    for i, drive_num in enumerate(sorted(drive_nums), 1):
        d = Drive(game, i, home_team, data[str(drive_num)])
        if not hasattr(d, 'game'):  # not a valid drive
            continue
        drives.append(d)
    return drives


def _json_plays(drive, data):
    """
    Takes a single JSON drive entry (data) and converts it to a list
    of Play objects. This includes trying to resolve duplicate play
    conflicts by only taking the first instance of a play.
    """
    plays = []
    seen_ids = set()
    seen_desc = set()  # Sometimes duplicates have different play ids...
    for playid in map(str, sorted(map(int, data))):
        p = data[playid]
        desc = (p['desc'], p['time'], p['yrdln'], p['qtr'])
        if playid in seen_ids or desc in seen_desc:
            continue
        seen_ids.add(playid)
        seen_desc.add(desc)
        plays.append(Play(drive, playid, data[playid]))
    return plays


def _json_play_players(play, data):
    """
    Takes a single JSON play entry (data) and converts it to an OrderedDict
    of player statistics.

    play is the instance of Play that this data is part of. It is used
    to determine whether the player belong to the home team or not.
    """
    players = OrderedDict()
    for playerid, statcats in data.iteritems():
        if playerid == '0':
            continue
        for info in statcats:
            if info['statId'] not in nflgame.statmap.idmap:
                continue
            if playerid not in players:
                home = play.drive.game.is_home(info['clubcode'])
                if home:
                    team_name = play.drive.game.home
                else:
                    team_name = play.drive.game.away
                stats = nflgame.player.PlayPlayerStats(playerid,
                                                       info['playerName'],
                                                       home, team_name)
                players[playerid] = stats
            statvals = nflgame.statmap.values(info['statId'], info['yards'])
            players[playerid]._add_stats(statvals)
    return players


def _json_play_events(data):
    """
    Takes a single JSON play entry (data) and converts it to a list of events.
    """
    temp = list()
    for playerid, statcats in data.iteritems():
        for info in statcats:
            if info['statId'] not in nflgame.statmap.idmap:
                continue
            statvals = nflgame.statmap.values(info['statId'], info['yards'])
            statvals['playerid'] = None if playerid == '0' else playerid
            statvals['playername'] = info['playerName'] or None
            statvals['team'] = info['clubcode']
            temp.append((int(info['sequence']), statvals))
    return [t[1] for t in sorted(temp, key=lambda t: t[0])]


def _json_game_player_stats(game, data):
    """
    Parses the 'home' and 'away' team stats and returns an OrderedDict
    mapping player id to their total game statistics as instances of
    nflgame.player.GamePlayerStats.
    """
    players = OrderedDict()
    for team in ('home', 'away'):
        for category in nflgame.statmap.categories:
            if category not in data[team]['stats']:
                continue
            for pid, raw in data[team]['stats'][category].iteritems():
                stats = {}
                for k, v in raw.iteritems():
                    if k == 'name':
                        continue
                    stats['%s_%s' % (category, k)] = v
                if pid not in players:
                    home = team == 'home'
                    if home:
                        team_name = game.home
                    else:
                        team_name = game.away
                    players[pid] = nflgame.player.GamePlayerStats(pid,
                                                                  raw['name'],
                                                                  home,
                                                                  team_name)
                players[pid]._add_stats(stats)
    return players


def _get_json_data(eid=None, fpath=None):
    """
    Returns the JSON data corresponding to the game represented by eid.

    If the JSON data is already on disk, it is read, decompressed and returned.

    Otherwise, the JSON data is downloaded from the NFL web site. If the data
    doesn't exist yet or there was an error, _get_json_data returns None.

    If eid is None, then the JSON data is read from the file at fpath.
    """
    assert eid is not None or fpath is not None

    if fpath is not None:
        return gzip.open(fpath).read()

    fpath = _jsonf % eid
    if os.access(fpath, os.R_OK):
        return gzip.open(fpath).read()
    try:
        return urllib2.urlopen(_json_base_url % (eid, eid), timeout=5).read()
    except urllib2.HTTPError:
        pass
    except socket.timeout:
        pass
    return None


def _tryint(v):
    """
    Tries to convert v to an integer. If it fails, return 0.
    """
    try:
        return int(v)
    except:
        return 0

########NEW FILE########
__FILENAME__ = live
"""
The live module provides a mechanism of periodically checking which games are
being actively played.

It requires the third party library pytz to be
installed, which makes sure game times are compared properly with respect
to time zones. pytz can be downloaded from PyPI:
http://pypi.python.org/pypi/pytz/

It works by periodically downloading data from NFL.com for games that started
before the current time. Once a game completes, the live module stops asking
NFL.com for data for that game.

If there are no games being actively played (i.e., it's been more than N hours
since the last game started), then the live module sleeps for longer periods
of time.

Thus, the live module can switch between two different modes: active and
inactive.

In the active mode, the live module downloads data from NFL.com in
short intervals. A transition to an inactive mode occurs when no more games
are being played.

In the inactive mode, the live module only checks if a game is playing (or
about to play) every 15 minutes. If a game is playing or about to play, the
live module switches to the active mode. Otherwise, it stays in the inactive
mode.

With this strategy, if the live module is working properly, you could
theoretically keep it running for the entire season.

(N.B. Half-time is ignored. Games are either being actively played or not.)

Alpha status
============
This module is emphatically in alpha status. I believe things will work OK for
the regular season, but the postseason brings new challenges. Moreover, it
will probably affect the API at least a little bit.
"""
import datetime
import time
import urllib2
import xml.dom.minidom as xml

try:
    import pytz
except ImportError:
    pass

import nflgame
import nflgame.game

# [00:21] <rasher> burntsushi: Alright, the schedule changes on Wednesday 7:00
# UTC during the regular season

_MAX_GAME_TIME = 60 * 60 * 6
"""
The assumed maximum time allowed for a game to complete. This is used to
determine whether a particular game that isn't over is currently active.
"""

_WEEK_INTERVAL = 60 * 60 * 12
"""
How often to check what the current week is. By default, it is twice a day.
"""

_CUR_SCHEDULE_URL = "http://www.nfl.com/liveupdate/scorestrip/ss.xml"
"""
Pinged infrequently to discover the current week number, year and week type.
The actual schedule of games is taken from the schedule module.
"""

_CUR_SCHEDULE_URL = "http://static.nfl.com/liveupdate/scorestrip/postseason/ss.xml"
"""
The URL for the XML schedule of the post season. This is only used
during the post season.

TODO: How do we know if it's the post season?
"""

_cur_week = None
"""The current week. It is updated infrequently automatically."""

_cur_year = None
"""The current year. It is updated infrequently automatically."""

_cur_season_phase = 'PRE'
"""The current phase of the season."""

_regular = False
"""True when it's the regular season."""

_last = None
"""
A list of the last iteration of games. These are diffed with the current
iteration of games.
"""

_completed = []
"""
A list of game eids that have been completed since the live module started
checking for updated game stats.
"""


def current_year_and_week():
    """
    Returns a tuple (year, week) where year is the current year of the season
    and week is the current week number of games being played.
    i.e., (2012, 3).

    N.B. This always downloads the schedule XML data.
    """
    _update_week_number()
    return _cur_year, _cur_week


def current_games(year=None, week=None, kind='REG'):
    """
    Returns a list of game.Games of games that are currently playing.
    This fetches all current information from NFL.com.

    If either year or week is none, then the current year and week are
    fetched from the schedule on NFL.com. If they are *both* provided, then
    the schedule from NFL.com won't need to be downloaded, and thus saving
    time.

    So for example::

        year, week = nflgame.live.current_year_and_week()
        while True:
            games = nflgame.live.current_games(year, week)
            # Do something with games
            time.sleep(60)

    The kind parameter specifies whether to fetch preseason, regular season
    or postseason games. Valid values are PRE, REG and POST.
    """
    if year is None or week is None:
        year, week = current_year_and_week()

    guesses = []
    now = _now()
    games = _games_in_week(year, week, kind=kind)
    for info in games:
        gametime = _game_datetime(info)
        if gametime >= now:
            if (gametime - now).total_seconds() <= 60 * 15:
                guesses.append(info['eid'])
        elif (now - gametime).total_seconds() <= _MAX_GAME_TIME:
            guesses.append(info['eid'])

    # Now we have a list of all games that are currently playing, are
    # about to start in less than 15 minutes or have already been playing
    # for _MAX_GAME_TIME (6 hours?). Now fetch data for each of them and
    # rule out games in the last two categories.
    current = []
    for guess in guesses:
        game = nflgame.game.Game(guess)
        if game is not None and game.playing():
            current.append(game)
    return current


def run(callback, active_interval=15, inactive_interval=900, stop=None):
    """
    Starts checking for games that are currently playing.

    Every time there is an update, callback will be called with three
    lists: active, completed and diffs. The active list is a list of
    game.Game that are currently being played. The completed list is
    a list of game.Game that have just finished. The diffs list is a
    list of `nflgame.game.GameDiff` objects, which collects statistics
    that are new since the last time `callback` was called. A game will
    appear in the completed list only once, after which that game will
    not be in either the active or completed lists. No game can ever
    be in both the `active` and `completed` lists at the same time.

    It is possible that a game in the active list is not yet playing because
    it hasn't started yet. It ends up in the active list because the "pregame"
    has started on NFL.com's GameCenter web site, and sometimes game data is
    partially filled. When this is the case, the 'playing' method on
    a nflgame.game.Game will return False.

    When in the active mode (see live module description), active_interval
    specifies the number of seconds to wait between checking for updated game
    data. Please do not make this number too low to avoid angering NFL.com.
    If you anger them too much, it is possible that they could ban your IP
    address.

    Note that NFL.com's GameCenter page is updated every 15 seconds, so
    setting the active_interval much smaller than that is wasteful.

    When in the inactive mode (see live module description), inactive_interval
    specifies the number of seconds to wait between checking whether any games
    have started or are about to start.

    With the default parameters, run will never stop. However, you may set
    stop to a Python datetime.datetime value. After time passes the stopping
    point, run will quit. (Technically, it's possible that it won't quit until
    at most inactive_interval seconds after the stopping point is reached.)
    The stop value is compared against datetime.datetime.now().
    """
    active = False
    last_week_check = _update_week_number()

    # Before we start with the main loop, we make a first pass at what we
    # believe to be the active games. Of those, we check to see if any of
    # them are actually already over, and add them to _completed.
    for info in _active_games(inactive_interval):
        game = nflgame.game.Game(info['eid'])

        # If we couldn't get a game, that probably means the JSON feed
        # isn't available yet. (i.e., we're early.)
        if game is None:
            continue

        # Otherwise, if the game is over, add it to our list of completed
        # games and move on.
        if game.game_over():
            _completed.append(info['eid'])

    while True:
        if stop is not None and datetime.datetime.now() > stop:
            return

        if time.time() - last_week_check > _WEEK_INTERVAL:
            last_week_check = _update_week_number()

        games = _active_games(inactive_interval)
        if active:
            active = _run_active(callback, games)
            if not active:
                continue
            time.sleep(active_interval)
        else:
            active = not _run_inactive(games)
            if active:
                continue
            time.sleep(inactive_interval)


def _run_active(callback, games):
    """
    The active mode traverses each of the active games and fetches info for
    each from NFL.com.

    Then each game (that has info available on NFL.com---that is, the game
    has started) is added to one of two lists: active and completed, which
    are passed as the first and second parameters to callback. A game is
    put in the active list if it's still being played, and into the completed
    list if it has finished. In the latter case, it is added to a global store
    of completed games and will never be passed to callback again.
    """
    global _last

    # There are no active games, so just quit and return False. Which means
    # we'll transition to inactive mode.
    if len(games) == 0:
        return False

    active, completed = [], []
    for info in games:
        game = nflgame.game.Game(info['eid'])

        # If no JSON was retrieved, then we're probably just a little early.
        # So just ignore it for now---but we'll keep trying!
        if game is None:
            continue

        # If the game is over, added it to completed and _completed.
        if game.game_over():
            completed.append(game)
            _completed.append(info['eid'])
        else:
            active.append(game)

    # Create a list of game diffs between the active + completed games and
    # whatever is in _last.
    diffs = []
    for game in active + completed:
        for last_game in _last or []:
            if game.eid != last_game.eid:
                continue
            diffs.append(game - last_game)

    _last = active
    callback(active, completed, diffs)
    return True


def _run_inactive(games):
    """
    The inactive mode simply checks if there are any active games. If there
    are, inactive mode needs to stop and transition to active mode---thus
    we return False. If there aren't any active games, then the inactive
    mode should continue, where we return True.

    That is, so long as there are no active games, we go back to sleep.
    """
    return len(games) == 0


def _active_games(inactive_interval):
    """
    Returns a list of all active games. In this case, an active game is a game
    that will start within inactive_interval seconds, or has started within
    _MAX_GAME_TIME seconds in the past.
    """
    games = _games_in_week(_cur_year, _cur_week, _cur_season_phase)
    active = []
    for info in games:
        if not _game_is_active(info, inactive_interval):
            continue
        active.append(info)
    return active


def _games_in_week(year, week, kind='REG'):
    """
    A list for the games matching the year/week/kind parameters.

    The kind parameter specifies whether to fetch preseason, regular season
    or postseason games. Valid values are PRE, REG and POST.
    """
    return nflgame._search_schedule(year, week, kind=kind)


def _game_is_active(gameinfo, inactive_interval):
    """
    Returns true if the game is active. A game is considered active if the
    game start time is in the past and not in the completed list (which is
    a private module level variable that is populated automatically) or if the
    game start time is within inactive_interval seconds from starting.
    """
    gametime = _game_datetime(gameinfo)
    now = _now()
    if gametime >= now:
        return (gametime - now).total_seconds() <= inactive_interval
    return gameinfo['eid'] not in _completed


def _game_datetime(gameinfo):
    hour, minute = gameinfo['time'].strip().split(':')
    d = datetime.datetime(gameinfo['year'], gameinfo['month'], gameinfo['day'],
                          (int(hour) + 12) % 24, int(minute))
    return pytz.timezone('US/Eastern').localize(d).astimezone(pytz.utc)


def _now():
    return datetime.datetime.now(pytz.utc)


def _update_week_number():
    global _cur_week, _cur_year, _cur_season_phase

    dom = xml.parse(urllib2.urlopen(_CUR_SCHEDULE_URL, timeout=5))
    gms = dom.getElementsByTagName('gms')[0]
    _cur_week = int(gms.getAttribute('w'))
    _cur_year = int(gms.getAttribute('y'))

    phase = gms.getAttribute('t').strip()
    if phase == 'P':
        _cur_season_phase = 'PRE'
    elif phase == 'POST' or phase == 'PRO':
        _cur_season_phase = 'POST'
        _cur_week -= 17
    else:
        _cur_season_phase = 'REG'
    return time.time()

########NEW FILE########
__FILENAME__ = player
import json
import os.path

from nflgame import OrderedDict
import nflgame.seq
import nflgame.statmap

_player_json_file = os.path.join(os.path.dirname(__file__), 'players.json')


def _create_players(jsonf=None):
    """
    Creates a dict of Player objects from the players.json file, keyed
    by GSIS ids.
    """
    if jsonf is None:
        jsonf = _player_json_file
    try:
        data = json.loads(open(jsonf).read())
    except IOError:
        return {}

    players = {}
    for playerid in data:
        players[playerid] = Player(data[playerid])
    return players


class Player (object):
    """
    Player instances represent meta information about a single player.
    This information includes name, team, position, status, height,
    weight, college, jersey number, birth date, years, pro, etc.

    Player information is populated from NFL.com profile pages.
    """
    def __init__(self, data):
        self.player_id = data['gsis_id']
        self.gsis_name = data.get('gsis_name', '')
        self.full_name = data.get('full_name', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.team = data.get('team', '')
        self.position = data.get('position', '')
        self.profile_id = data.get('profile_id', 0)
        self.profile_url = data.get('profile_url', '')
        self.uniform_number = data.get('number', 0)
        self.birthdate = data.get('birthdate', '')
        self.college = data.get('college', '')
        self.height = data.get('height', '')
        self.weight = data.get('weight', '')
        self.years_pro = data.get('years_pro', 0)
        self.status = data.get('status', '')

        # API backwards compatibility.
        self.gsis_id = self.player_id
        self.playerid = self.player_id
        self.name = self.full_name
        self.number = self.uniform_number

    def stats(self, year, week=None):
        games = nflgame.games(year, week)
        players = list(nflgame.combine(games).filter(playerid=self.playerid))
        if len(players) == 0:
            return GamePlayerStats(self.player_id, self.gsis_name,
                                   None, self.team)
        return players[0]

    def plays(self, year, week=None):
        plays = []
        games = nflgame.games(year, week)
        for g in games:
            plays += filter(lambda p: p.has_player(self.playerid),
                            list(g.drives.plays()))
        return nflgame.seq.GenPlays(plays)

    def __str__(self):
        return '%s (%s, %s)' % (self.name, self.position, self.team)


class PlayerDefense (Player):
    def __init__(self, team):
        self.playerid = None
        self.name = team
        self.team = team
        self.position = 'DEF'

    def stats(self, year, week=None):
        assert False, 'Cannot be called on a defense.'

    def plays(self, year, week=None):
        assert False, 'Cannot be called on a defense.'

    def __str__(self):
        return '%s Defense' % self.team


class PlayerStats (object):
    """
    Player represents a single player and all of his statistical categories.
    Every player has 'playerid', 'name' and 'home' fields.
    Additionally, depending upon which statistical categories that player
    was involved in for the game, he'll have properties such as 'passing_tds',
    'rushing_yds', 'defense_int' and 'kicking_fgm'.

    In order to know whether a paricular player belongs to a statical category,
    you may use the filtering methods of a player sequence or alternatively,
    use the has_cat method with arguments like 'passing', 'rushing', 'kicking',
    etc. (A player sequence in this case would be an instance of
    GenPlayerStats.)

    You may also inspect whether a player has a certain property by using
    the special __dict__ attribute. For example::

        if 'passing_yds' in player.__dict__:
            # Do something with player.passing_yds
    """
    def __init__(self, playerid, name, home, team):
        """
        Create a new Player instance with the player id (from NFL.com's
        GameCenter), the player's name (e.g., "T.Brady") and whether the
        player is playing in a home game or not.
        """
        self.playerid = playerid
        self.name = name
        self.home = home
        self.team = team
        self._stats = OrderedDict()

        self.player = None
        if self.playerid in nflgame.players:
            self.player = nflgame.players[self.playerid]

    def has_cat(self, cat):
        for f in self._stats:
            if f.startswith(cat):
                return True
        return False

    @property
    def guess_position(self):
        """
        Guesses the position of this player based on the statistical
        categories present in this object when player meta is not
        present.

        Note that if this resorts to a guess, then it will be more
        effective on aggregate data rather than data from just a
        single play. (e.g., if a QB runs the ball, and that's the
        only data available, the position returned will be RB.)

        When a position is guessed, only the following positions will
        be returned: QB, RB, WR, DEF, K and P.
        """
        # Look for the player meta first. Duh.
        if self.player is not None:
            return self.player.position

        stats = [
            (self.passing_att, 'QB'),
            (self.rushing_att, 'RB'),
            (self.receiving_tar, 'WR'),
            (self.defense_tkl, 'DEF'),
            (self.defense_ast, 'DEF'),
            (self.kicking_tot, 'K'),
            (self.kicking_fga, 'K'),
            (self.punting_tot, 'P'),
        ]
        return sorted(stats, reverse=True)[0][1]

    @property
    def tds(self):
        """
        Returns the total number of touchdowns credited to this player across
        all statistical categories.
        """
        n = 0
        for f, v in self.__dict__.iteritems():
            if f.endswith('tds'):
                n += v
        return n

    @property
    def twopta(self):
        """
        Returns the total number of two point conversion attempts for
        the passing, rushing and receiving categories.
        """
        return (self.passing_twopta
                + self.rushing_twopta
                + self.receiving_twopta)

    @property
    def twoptm(self):
        """
        Returns the total number of two point conversions for
        the passing, rushing and receiving categories.
        """
        return (self.passing_twoptm
                + self.rushing_twoptm
                + self.receiving_twoptm)

    @property
    def twoptmissed(self):
        """
        Returns the total number of two point conversion failures for
        the passing, rushing and receiving categories.
        """
        return (self.passing_twoptmissed
                + self.rushing_twoptmissed
                + self.receiving_twoptmissed)

    @property
    def stats(self):
        """
        Returns a dict of all stats for the player.
        """
        return self._stats

    def formatted_stats(self):
        """
        Returns a roughly-formatted string of all statistics for this player.
        """
        s = []
        for stat, val in self._stats.iteritems():
            s.append('%s: %s' % (stat, val))
        return ', '.join(s)

    def _add_stats(self, stats):
        for k, v in stats.iteritems():
            self.__dict__[k] = self.__dict__.get(k, 0) + v
            self._stats[k] = self.__dict__[k]

    def _overwrite_stats(self, stats):
        for k, v in stats.iteritems():
            self.__dict__[k] = v
            self._stats[k] = self.__dict__[k]

    def __str__(self):
        """
        Simply returns the player's name, e.g., "T.Brady".
        """
        return self.name

    def __add__(self, other):
        """
        Adds two players together. Only two player objects that correspond
        to the same human (i.e., GameCenter identifier) can be added together.

        If two different players are added together, an assertion will
        be raised.

        The effect of adding two player objects simply corresponds to the
        sums of all statistical values.

        Note that as soon as two players have been added, the 'home' property
        becomes undefined if the two operands have different values of 'home'.
        """
        assert self.playerid == other.playerid
        assert type(self) == type(other)

        if self.home != other.home:
            home = None
        else:
            home = self.home
        new_player = self.__class__(self.playerid, self.name, home, self.team)
        new_player._add_stats(self._stats)
        new_player._add_stats(other._stats)

        return new_player

    def __sub__(self, other):
        assert self.playerid == other.playerid
        assert type(self) == type(other)

        new_player = GamePlayerStats(self.playerid,
                                     self.name, self.home, self.team)
        new_player._add_stats(self._stats)
        for bk, bv in other._stats.iteritems():
            if bk not in new_player._stats:  # stat was taken away? ignore.
                continue

            new_player._stats[bk] -= bv
            if new_player._stats[bk] == 0:
                del new_player._stats[bk]
            else:
                new_player.__dict__[bk] = new_player._stats[bk]

        anydiffs = False
        for k, v in new_player._stats.iteritems():
            if v > 0:
                anydiffs = True
                break
        if not anydiffs:
            return None
        return new_player

    def __getattr__(self, name):
        # If name has one of the categories as a prefix, then return
        # a default value of zero
        for cat in nflgame.statmap.categories:
            if name.startswith(cat):
                return 0
        raise AttributeError


class GamePlayerStats (PlayerStats):
    def __init__(self, playerid, name, home, team):
        super(GamePlayerStats, self).__init__(playerid, name, home, team)
        self.games = 1

    def __add__(self, other):
        new_player = super(GamePlayerStats, self).__add__(other)
        new_player.games = self.games + other.games
        return new_player


class PlayPlayerStats (PlayerStats):
    pass

########NEW FILE########
__FILENAME__ = sched
try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict  # from PyPI
import datetime
import json
import os.path

__pdoc__ = {}

_sched_json_file = os.path.join(os.path.dirname(__file__), 'schedule.json')

def _create_schedule(jsonf=None):
    """
    Returns an ordered dict of schedule data from the schedule.json
    file, where games are ordered by the date and time that they
    started. Keys in the dictionary are GSIS ids and values are
    dictionaries with the following keys: week, month, year, home,
    away, wday, gamekey, season_type, time.
    """
    day = 60 * 60 * 24
    if jsonf is None:
        jsonf = _sched_json_file
    try:
        data = json.loads(open(jsonf).read())
    except IOError:
        return OrderedDict()

    d = OrderedDict()
    for gsis_id, info in data.get('games', []):
        d[gsis_id] = info
    last_updated = datetime.datetime.utcfromtimestamp(data.get('time', 0))

    if (datetime.datetime.utcnow() - last_updated).total_seconds() >= day:
        # Only try to update if we can write to the schedule file.
        if os.access(jsonf, os.W_OK):
            import nflgame.live
            import nflgame.update_sched
            year, week = nflgame.live.current_year_and_week()
            phase = nflgame.live._cur_season_phase
            nflgame.update_sched.update_week(d, year, phase, week)
            nflgame.update_sched.write_schedule(jsonf, d)
            last_updated = datetime.datetime.now()
    return d, last_updated

games, last_updated = _create_schedule()

__pdoc__['nflgame.sched.games'] = """
An ordered dict of schedule data, where games are ordered by the date
and time that they started. Keys in the dictionary are GSIS ids and
values are dictionaries with the following keys: week, month, year,
home, away, wday, gamekey, season_type, time.
"""

__pdoc__['nflgame.sched.last_updated'] = """
A `datetime.datetime` object representing the last time the schedule
was updated.
"""

########NEW FILE########
__FILENAME__ = seq
import functools
import itertools
import operator

from nflgame import OrderedDict
from nflgame import statmap

_BUILTIN_PREDS = {
    '__lt': operator.lt,
    '__le': operator.le,
    '__ne': operator.ne,
    '__ge': operator.ge,
    '__gt': operator.gt,
}
"""
A dictionary of suffixes to predicates that can be used in Gen.filter.
The suffix corresponds to what to add to the end of a field name to invoke
the predicate it corresponds to. For example, this::

    players.filter(receiving_rec=lambda v: v > 0)

Is equivalent to::

    players.filter(receiving_rec__gt=0)

(Django users should feel right at home.)
"""


class Gen (object):
    """
    Players implements a sequence type and provides a convenient API for
    searching sets of players.
    """

    def __init__(self, iterable):
        """
        Creates a new Players sequence from an iterable where each element
        of the iterable is an instance of the Player class.
        """
        self.__iter = iterable

    def filter(self, **kwargs):
        """
        filters the sequence based on a set of criteria. Parameter
        names should be equivalent to the properties accessible in the items
        of the sequence. For example, where the items are instances of
        the Stats class::

            players.filter(home=True, passing_tds=1, rushing_yds=lambda x: x>0)

        Returns a sequence with only players on the home team that
        have a single passing touchdown and more than zero rushing yards.

        If a field specified does not exist for a particular item, that
        item is excluded from the result set.

        If a field is set to a value, then only items with fields that equal
        that value are returned.

        If a field is set to a function---which must be a predicate---then
        only items with field values satisfying that function will
        be returned.

        Also, special suffixes that begin with '__' may be added to the
        end of a field name to invoke built in predicates.
        For example, this::

            players.filter(receiving_rec=lambda v: v > 0)

        Is equivalent to::

            players.filter(receiving_rec__gt=0)

        Other suffixes includes gt, le, lt, ne, ge, etc.

        (Django users should feel right at home.)
        """
        preds = []
        for k, v in kwargs.iteritems():
            def pred(field, value, item):
                for suffix, p in _BUILTIN_PREDS.iteritems():
                    if field.endswith(suffix):
                        f = field[:field.index(suffix)]
                        if not hasattr(item, f) or getattr(item, f) is None:
                            return False
                        return p(getattr(item, f), value)
                if not hasattr(item, field) or getattr(item, field) is None:
                    return False
                if isinstance(value, type(lambda x: x)):
                    return value(getattr(item, field))
                return getattr(item, field) == value
            preds.append(functools.partial(pred, k, v))

        gen = itertools.ifilter(lambda item: all([f(item) for f in preds]),
                                self)
        return self.__class__(gen)

    def limit(self, n):
        """
        Limit the sequence to N items.
        """
        return self.__class__(itertools.islice(self, n))

    def sort(self, field, descending=True):
        """
        sorts the sequence according to the field specified---where field is
        a property on an item in the sequence. If descending is false, items
        will be sorted in order from least to greatest.

        Note that if field does not exist in any item being sorted, a
        KeyError will be raised.
        """
        def attrget(item):
            return getattr(item, field, 0)

        return self.__class__(sorted(self, reverse=descending, key=attrget))

    def __str__(self):
        """Returns a list of items in the sequence."""
        return '[%s]' % ', '.join([str(item) for item in self])

    def __iter__(self):
        """Make this an iterable sequence."""
        if self.__iter is None:
            return iter([])
        if isinstance(self.__iter, OrderedDict):
            return self.__iter.itervalues()
        return iter(self.__iter)

    def __reversed__(self):
        """Satisfy the built in reversed."""
        return reversed(self.__iter)


class GenDrives (Gen):
    """
    GenDrives implements a sequence type and provides a convenient API
    for searching drives.
    """
    def plays(self):
        """
        Returns all of the plays, in order, belonging to every drive in
        the sequence.
        """
        return GenPlays(itertools.chain(*map(lambda d: d.plays, self)))

    def players(self):
        """
        Returns the combined player stats for every player that participated
        in any of the drives in the sequence.
        """
        return self.plays().players()

    def number(self, n, team=None):
        """
        Gets the Nth drive where the first drive corresponds to n=1. This is
        only useful given a complete collection of drives for an entire game.

        If the team parameter is specified (i.e., team='NE'), then n will
        be interpreted as *that* team's Nth drive.
        """
        assert n > 0
        n -= 1
        if team is None:
            return list(self)[n]
        else:
            i = 0
            for d in self:
                if d.team == team:
                    if i == n:
                        return d
                    i += 1
            assert False, \
                'Could not find drive %d for team %s.' % (n + 1, team)


class GenPlays (Gen):
    """
    GenPlays implements a sequence type and provides a convenient API
    for searching plays.
    """
    def players(self):
        """
        Returns the combined player stats for every play in the sequence.
        """
        players = OrderedDict()
        for play in self:
            for player in play.players:
                if player.playerid not in players:
                    players[player.playerid] = player
                else:
                    players[player.playerid] += player
        return GenPlayerStats(players)


class GenPlayerStats (Gen):
    """
    GenPlayerStats implements a sequence type and provides a convenient API for
    searching sets of player statistics.
    """
    def name(self, name):
        """
        Returns a single player whose name equals `name`. If no such player
        can be found, None is returned.

        Note that NFL GameCenter formats their names like "T.Brady" and
        "W.Welker". Thus, `name` should also be in this format.
        """
        for p in self:
            if p.name == name:
                return p
        return None

    def playerid(self, playerid):
        """
        Returns a single player whose NFL GameCenter identifier equals
        `playerid`. This probably isn't too useful, unless you're trying
        to do ID mapping. (Players have different identifiers across NFL.com.)

        If no such player with the given identifier is found, None is
        returned.
        """
        for p in self:
            if p.playerid == playerid:
                return p
        return None

    def touchdowns(self):
        """
        touchdowns is a convenience method for returning a Players
        sequence of all players with at least one touchdown.
        """
        def gen():
            for p in self:
                for f in p.__dict__:
                    if f.endswith('tds') and p.__dict__[f] > 0:
                        yield p
                        break
        return self.__class__(gen())

    def __filter_category(self, cat):
        return self.__class__(itertools.ifilter(lambda p: p.has_cat(cat),
                                                self))

    def passing(self):
        """Returns players that have a "passing" statistical category."""
        return self.__filter_category('passing')

    def rushing(self):
        """Returns players that have a "rushing" statistical category."""
        return self.__filter_category('rushing')

    def receiving(self):
        """Returns players that have a "receiving" statistical category."""
        return self.__filter_category('receiving')

    def fumbles(self):
        """Returns players that have a "fumbles" statistical category."""
        return self.__filter_category('fumbles')

    def kicking(self):
        """Returns players that have a "kicking" statistical category."""
        return self.__filter_category('kicking')

    def punting(self):
        """Returns players that have a "punting" statistical category."""
        return self.__filter_category('punting')

    def kickret(self):
        """Returns players that have a "kickret" statistical category."""
        return self.__filter_category('kickret')

    def puntret(self):
        """Returns players that have a "puntret" statistical category."""
        return self.__filter_category('puntret')

    def defense(self):
        """Returns players that have a "defense" statistical category."""
        return self.__filter_category('defense')

    def penalty(self):
        """Returns players that have a "penalty" statistical category."""
        return self.__filter_category('penalty')

    def csv(self, fileName, allfields=False):
        """
        Given a file-name fileName, csv will write the contents of
        the Players sequence to fileName formatted as comma-separated values.
        The resulting file can then be opened directly with programs like
        Excel, Google Docs, Libre Office and Open Office.

        Note that since each player in a Players sequence may have differing
        statistical categories (like a quarterback and a receiver), the
        minimum constraining set of statisical categories is used as the
        header row for the resulting CSV file. This behavior can be changed
        by setting 'allfields' to True, which will use every available field
        in the header.
        """
        import csv

        fields, rows = set([]), []
        players = list(self)
        for p in players:
            for field, stat in p.stats.iteritems():
                fields.add(field)
        if allfields:
            for statId, info in statmap.idmap.iteritems():
                for field in info['fields']:
                    fields.add(field)
        fields = sorted(list(fields))

        for p in players:
            d = {
                'name': p.name,
                'id': p.playerid,
                'home': p.home and 'yes' or 'no',
                'team': p.team,
                'pos': 'N/A',
            }
            if p.player is not None:
                d['pos'] = p.player.position

            for field in fields:
                if field in p.__dict__:
                    d[field] = p.__dict__[field]
                else:
                    d[field] = ""
            rows.append(d)

        fieldNames = ["name", "id", "home", "team", "pos"] + fields
        rows = [dict((f, f) for f in fieldNames)] + rows
        csv.DictWriter(open(fileName, 'w+'), fieldNames).writerows(rows)

    def __add__(self, other):
        """
        Adds two sequences of players by combining repeat players and summing
        their statistics.
        """
        players = OrderedDict()
        for p in itertools.chain(self, other):
            if p.playerid not in players:
                players[p.playerid] = p
            else:
                players[p.playerid] += p
        return GenPlayerStats(players)

########NEW FILE########
__FILENAME__ = statmap
"""
The stats module maps statistical category identifiers from NFL.com's
GameCenter JSON feed to a representation of what we believe that statistical
category means. This mapping has been reverse engineered with a lot of help
from reddit users rasherdk and curien.

B{Note}: We now have a data dictionary mapping statistical category id to
a description from nflgsis.com. An original copy is in the root directory
of the nflgame repository (StatIDs.html).

If you think anything here is wrong (or can figure out some of the unknowns),
please let me know by filing an issue here:
https://github.com/BurntSushi/nflgame/issues

For each statistical category identifier, we create a dict of 6 fields
describing that statistical category. The fields are cat, fields, yds, value,
desc and long.

cat specifies which statistical category the particular stat belong in. Only
statistical categories in nflgame.player.categories should be used.

fields specifies the actual statistical field corresponding to the stat. This
will manifest itself as a property on statistical objects via the API. These
fields should correspond to counters; i.e., number of receptions, rushing
attempts, tackles, etc.

yds specifies a field that contains the yardage totals relevant to the stat.
If a stat does not specify yards, this field should be blank (an empty string).

value specifies how much each statistic is worth. This is 1 in every case
except for split sacks.

desc specifies a human readable description for the statistic. It should be
concise and clear. If a statistical category is unknown, then desc should
contain a string like 'Unknown (reason for confusion)'. Valid reasons for
confusion include "data is inconsistent" or "this looks like a duplicate" all
the way to "I have no fucking clue."

long contains a verbatim description from nflgsis.com. Some of the information
clearly references legacy systems, but alas, it is included as it adds to the
context of each statistical category.
"""


def values(category_id, yards):
    """
    Returns a dictionary of field names to statistical values for a
    particular category id defined in idmap.
    """
    assert category_id in idmap, \
        'Category identifier %d is not known.' % category_id
    info = idmap[category_id]
    try:
        yards = int(yards)
    except ValueError:
        yards = 0
    except TypeError:
        #Catch errors if yards is a NoneType
        yards = 0

    vals = {}
    if info['yds']:
        vals[info['yds']] = yards
    for f in info['fields']:
        vals[f] = info.get('value', 1)
    return vals

categories = ("passing", "rushing", "receiving",
              "fumbles", "kicking", "punting", "kickret", "puntret",
              "defense", "penalty")
"""
categories is a list of all statistical categories reported by NFL's
GameCenter.
"""

idmap = {
    2: {
        'cat': 'punting',
        'fields': ['punting_blk'],
        'yds': '',
        'desc': 'Punt blocked (offense)',
        'long': 'Punt was blocked. A blocked punt is a punt that is touched '
                'behind the line of scrimmage, and is recovered, or goes '
                'out of bounds, behind the line of scrimmage. If the '
                'impetus of the punt takes it beyond the line of scrimmage, '
                'it is not a blocked punt.',
    },
    3: {
        'cat': 'team',
        'fields': ['first_down', 'rushing_first_down'],
        'yds': '',
        'desc': '1st down (rushing)',
        'long': 'A first down or TD occurred due to a rush.',
    },
    4: {
        'cat': 'team',
        'fields': ['first_down', 'passing_first_down'],
        'yds': '',
        'desc': '1st down (passing)',
        'long': 'A first down or TD occurred due to a pass.',
    },
    5: {
        'cat': 'team',
        'fields': ['first_down', 'penalty_first_down'],
        'yds': '',
        'desc': '1st down (penalty)',
        'long': 'A first down or TD occurred due to a penalty. A play can '
                'have a first down from a pass or rush and from a penalty.',
    },
    6: {
        'cat': 'team',
        'fields': ['third_down_att', 'third_down_conv'],
        'yds': '',
        'desc': '3rd down attempt converted',
        'long': '3rd down play resulted in a first down or touchdown.',
    },
    7: {
        'cat': 'team',
        'fields': ['third_down_att', 'third_down_failed'],
        'yds': '',
        'desc': '3rd down attempt failed',
        'long': '3rd down play did not result in a first down or touchdown.',
    },
    8: {
        'cat': 'team',
        'fields': ['fourth_down_att', 'fourth_down_conv'],
        'yds': '',
        'desc': '4th down attempt converted',
        'long': '4th down play resulted in a first down or touchdown.',
    },
    9: {
        'cat': 'team',
        'fields': ['fourth_down_att', 'fourth_down_failed'],
        'yds': '',
        'desc': '4th down attempt failed',
        'long': '4th down play did not result in a first down or touchdown.',
    },
    10: {
        'cat': 'rushing',
        'fields': ['rushing_att'],
        'yds': 'rushing_yds',
        'desc': 'Rushing yards',
        'long': 'Rushing yards and credit for a rushing attempt.',
    },
    11: {
        'cat': 'rushing',
        'fields': ['rushing_att', 'rushing_tds'],
        'yds': 'rushing_yds',
        'desc': 'Rushing yards, TD',
        'long': 'Rushing yards and credit for a rushing attempt where the '
                'result of the play was a touchdown.',
    },
    12: {
        'cat': 'rushing',
        'fields': [],
        'yds': 'rushing_yds',
        'desc': 'Rushing yards, No rush',
        'long': 'Rushing yards with no rushing attempt. This will occur when '
                'the initial runner laterals to a second runner, and the '
                'second runner possesses the lateral beyond the line of '
                'scrimmage. Both players get rushing yards, but only the '
                'first player gets a rushing attempt.',
    },
    13: {
        'cat': 'rushing',
        'fields': ['rushing_tds'],
        'yds': 'rushing_yds',
        'desc': 'Rushing yards, TD, No rush',
        'long': 'Rushing yards and no rushing attempt, where the result of '
                'the play was a touchdown. (See id 12.)',
    },
    14: {
        'cat': 'passing',
        'fields': ['passing_att', 'passing_incmp'],
        'yds': '',
        'desc': 'Pass incomplete',
        'long': 'Pass atempt, incomplete.',
    },
    15: {
        'cat': 'passing',
        'fields': ['passing_att', 'passing_cmp'],
        'yds': 'passing_yds',
        'desc': 'Passing yards',
        'long': 'Passing yards and a pass attempt completed.',
    },
    16: {
        'cat': 'passing',
        'fields': ['passing_att', 'passing_cmp', 'passing_tds'],
        'yds': 'passing_yds',
        'desc': 'Passing yards, TD',
        'long': 'Passing yards and a pass attempt completed that resulted in '
                'a touchdown.',
    },
    # 17: Passing Yards, No Pass
    # In SuperStat, this code was used when the initial pass receiver lateraled
    # to a teammate. It was later combined with the "Passing Yards" code to
    # determine the passer's (quarterback's) total passing yardage on the play.
    # This stat is not in use at this time.

    # 18: Passing Yards, YD, No pass
    # Passing yards, no pass attempt, with a result of touchdown. This stat
    # is not in use at this time.
    19: {
        'cat': 'passing',
        'fields': ['passing_att', 'passing_incmp', 'passing_int'],
        'yds': '',
        'desc': 'Interception (by passer)',
        'long': 'Pass attempt that resulted in an interception.',
    },
    20: {
        'cat': 'passing',
        'fields': ['passing_sk'],
        'yds': 'passing_sk_yds',
        'desc': 'Sack yards (offense)',
        'long': 'Number of yards lost on a pass play that resulted in a sack.',
    },
    21: {
        'cat': 'receiving',
        'fields': ['receiving_rec'],
        'yds': 'receiving_yds',
        'desc': 'Pass reception yards',
        'long': 'Pass reception and yards.',
    },
    22: {
        'cat': 'receiving',
        'fields': ['receiving_rec', 'receiving_tds'],
        'yds': 'receiving_yds',
        'desc': 'Pass reception yards, TD',
        'long': 'Same as previous (21), except when the play results in a '
                'touchdown.',
    },
    23: {
        'cat': 'receiving',
        'fields': [],
        'yds': 'receiving_yds',
        'desc': 'Pass reception yards, No reception',
        'long': 'Pass reception yards, no pass reception. This will occur '
                'when the pass receiver laterals to a teammate. The teammate '
                'gets pass reception yards, but no credit for a pass '
                'reception.',
    },
    24: {
        'cat': 'receiving',
        'fields': ['receiving_tds'],
        'yds': 'receiving_yds',
        'desc': 'Pass reception yards, TD, No reception',
        'long': 'Same as previous (23), except when the play results in a '
                'touchdown.',
    },
    25: {
        'cat': 'defense',
        'fields': ['defense_int'],
        'yds': 'defense_int_yds',
        'desc': 'Interception yards',
        'long': 'Interception and return yards.',
    },
    26: {
        'cat': 'defense',
        'fields': ['defense_int', 'defense_tds', 'defense_int_tds'],
        'yds': 'defense_int_yds',
        'desc': 'Interception yards, TD',
        'long': 'Same as previous (25), except when the play results in a '
                'touchdown.',
    },
    27: {
        'cat': 'defense',
        'fields': [],
        'yds': 'defense_int_yds',
        'also': [],
        'desc': 'Interception yards, No interception',
        'long': 'Interception yards, with no credit for an interception. This '
                'will occur when the player who intercepted the pass laterals '
                'to a teammate. The teammate gets interception return yards, '
                'but no credit for a pass interception.',
    },
    28: {
        'cat': 'defense',
        'fields': ['defense_tds', 'defense_int_tds'],
        'yds': 'defense_int_yds',
        'also': [],
        'desc': 'Interception yards, TD, No interception',
        'long': 'Same as previous (27), except when the play results in a '
                'touchdown.',
    },
    29: {
        'cat': 'punting',
        'fields': ['punting_tot'],
        'yds': 'punting_yds',
        'desc': 'Punting yards',
        'long': 'Punt and length of the punt. This stat is not used if '
                'the punt results in a touchback; or the punt is received '
                'in the endzone and run out; or the punt is blocked. This '
                'stat is used exclusively of the PU_EZ, PU_TB and PU_BK '
                'stats.',
    },
    30: {
        'cat': 'punting',
        'fields': ['punting_i20'],
        'yds': '',
        'desc': 'Punt inside 20',
        'long': 'This stat is recorded when the punt return ended inside the '
                'opponent\'s 20 yard line. This is not counted as a punt or '
                'towards punting yards. This stat is used solely to calculate '
                '"inside 20" stats. This stat is used in addition to either a '
                'PU or PU_EZ stat.',
    },
    31: {
        'cat': 'punting',
        'fields': ['punting_tot'],
        'yds': 'punting_yds',
        'desc': 'Punt into endzone',
        'long': 'SuperStat records this stat when the punt is received in '
                'the endzone, and then run out of the endzone. If the play '
                'ends in the endzone for a touchback, the stat is not '
                'recorded. This stat is used exclusively of the PU, PU_TB and '
                'PU_BK stats.',
    },
    32: {
        'cat': 'punting',
        'fields': ['punting_tot', 'punting_touchback'],
        'yds': 'punting_yds',
        'desc': 'Punt with touchback',
        'long': 'Punt and length of the punt when the play results in a '
                'touchback. This stat is used exclusively of the PU, PU_EZ '
                'and PU_BK stats.',
    },
    33: {
        'cat': 'puntret',
        'fields': ['puntret_tot'],
        'yds': 'puntret_yds',
        'desc': 'Punt return yards',
        'long': 'Punt return and yards.',
    },
    34: {
        'cat': 'puntret',
        'fields': ['puntret_tot', 'puntret_tds'],
        'yds': 'puntret_yds',
        'desc': 'Punt return yards, TD',
        'long': 'Same as previous (33), except when the play results in a '
                'touchdown.',
    },
    35: {
        'cat': 'puntret',
        'fields': [],
        'yds': 'puntret_yds',
        'desc': 'Punt return yards, No return',
        'long': 'Punt return yards with no credit for a punt return. This '
                'will occur when the player who received the punt laterals '
                'to a teammate. The teammate gets punt return yards, but no '
                'credit for a return.',
    },
    36: {
        'cat': 'puntret',
        'fields': ['puntret_tds'],
        'yds': 'puntret_yds',
        'desc': 'Punt return yards, TD, No return',
        'long': 'Same as previous (35), except when the play results in a '
                'touchdown.',
    },
    37: {
        'cat': 'team',
        'fields': ['puntret_oob'],
        'yds': '',
        'desc': 'Punt out of bounds',
        'long': 'Punt went out of bounds, no return on the play.',
    },
    38: {
        'cat': 'team',
        'fields': ['puntret_downed'],
        'yds': '',
        'also': [],
        'value': 1,
        'desc': 'Punt downed (no return)',
        'long': 'Punt was downed by kicking team, no return on the play. '
                'The player column this stat will always be NULL.',
    },
    39: {
        'cat': 'puntret',
        'fields': ['puntret_fair'],
        'yds': '',
        'desc': 'Punt - fair catch',
        'long': 'Punt resulted in a fair catch.',
    },
    40: {
        'cat': 'team',
        'fields': ['puntret_touchback'],
        'yds': '',
        'desc': 'Punt - touchback (no return)',
        'long': 'Punt resulted in a touchback. This is the receiving team\'s '
                'version of code 1504/28 (32) above. Both are needed for stat '
                'calculations, especially in season cumulative analysis.',
    },
    41: {
        'cat': 'kicking',
        'fields': ['kicking_tot'],
        'yds': 'kicking_yds',
        'desc': 'Kickoff yards',
        'long': 'Kickoff and length of kick.',
    },
    42: {
        'cat': 'kicking',
        'fields': ['kicking_i20'],
        'yds': '',
        'desc': 'Kickoff inside 20',
        'long': 'Kickoff and length of kick, where return ended inside '
                'opponent\'s 20 yard line. This is not counted as a kick or '
                'towards kicking yards. This code is used solely to calculate '
                '"inside 20" stats. used in addition to a 1701 code.',
    },
    43: {
        'cat': 'kicking',
        'fields': ['kicking_tot'],
        'yds': 'kicking_yds',
        'desc': 'Kickff into endzone',
        'long': 'SuperStat records this stat when the kickoff is received '
                'in the endzone, and then run out of the endzone. If the play '
                'ends in the endzone for a touchback, the stat is not '
                'recorded. Compare to "Punt into endzone."',
    },
    44: {
        'cat': 'kicking',
        'fields': ['kicking_tot', 'kicking_touchback'],
        'yds': 'kicking_yds',
        'desc': 'Kickoff with touchback',
        'long': 'Kickoff resulted in a touchback.',
    },
    45: {
        'cat': 'kickret',
        'fields': ['kickret_ret'],
        'yds': 'kickret_yds',
        'desc': 'Kickoff return yards',
        'long': 'Kickoff return and yards.',
    },
    46: {
        'cat': 'kickret',
        'fields': ['kickret_ret', 'kickret_tds'],
        'yds': 'kickret_yds',
        'desc': 'Kickoff return yards, TD',
        'long': 'Same as previous (45), except when the play results in a '
                'touchdown.',
    },
    47: {
        'cat': 'kickret',
        'fields': [],
        'yds': 'kickret_yds',
        'desc': 'Kickoff return yards, No return',
        'long': 'Kickoff yards with no return. This will occur when the '
                'player who is credited with the return laterals to a '
                'teammate. The teammate gets kickoff return yards, but no '
                'credit for a kickoff return.',
    },
    48: {
        'cat': 'kickret',
        'fields': ['kickret_tds'],
        'yds': 'kickret_yds',
        'desc': 'Kickoff return yards, TD, No return',
        'long': 'Same as previous (47), except when the play results in a '
                'touchdown.',
    },
    49: {
        'cat': 'team',
        'fields': ['kickret_oob'],
        'yds': '',
        'desc': 'Kickoff out of bounds',
        'long': 'Kicked ball went out of bounds.',
    },
    50: {
        'cat': 'kickret',
        'fields': ['kickret_fair'],
        'yds': '',
        'desc': 'Kickoff - fair catch',
        'long': 'Kick resulted in a fair catch (no return).',
    },
    51: {
        'cat': 'team',
        'fields': ['kickret_touchback'],
        'yds': '',
        'desc': 'Kickoff - touchback',
        'long': 'Kick resulted in a touchback. A touchback implies that '
                'there is no return.',
    },
    52: {
        'cat': 'fumbles',
        'fields': ['fumbles_tot', 'fumbles_forced'],
        'yds': '',
        'desc': 'Fumble - forced',
        'long': 'Player fumbled the ball, fumble was forced by another '
                'player.',
    },
    53: {
        'cat': 'fumbles',
        'fields': ['fumbles_tot', 'fumbles_notforced'],
        'yds': '',
        'desc': 'Fumble - not forced',
        'long': 'Player fumbled the ball, fumble was not forced by another '
                'player.',
    },
    54: {
        'cat': 'fumbles',
        'fields': ['fumbles_tot', 'fumbles_oob'],
        'yds': '',
        'desc': 'Fumble - out of bounds',
        'long': 'Player fumbled the ball, and the ball went out of bounds.',
    },
    55: {
        'cat': 'fumbles',
        'fields': ['fumbles_rec'],
        'yds': 'fumbles_rec_yds',
        'desc': 'Own recovery yards',
        'long': 'Yardage gained/lost by a player after he recovered a fumble '
                'by his own team.',
    },
    56: {
        'cat': 'fumbles',
        'fields': ['fumbles_rec', 'fumbles_rec_tds'],
        'yds': 'fumbles_rec_yds',
        'desc': 'Own recovery yards, TD',
        'long': 'Same as previous (55), except when the play results in a '
                'touchdown.',
    },
    57: {
        'cat': 'fumbles',
        'fields': [],
        'yds': 'fumbles_rec_yds',
        'desc': 'Own recovery yards, No recovery',
        'long': 'If a player recovered a fumble by his own team, then '
                'lateraled to a teammate, the yardage gained/lost by teammate '
                'would be recorded with this stat.',
    },
    58: {
        'cat': 'fumbles',
        'fields': ['fumbles_rec_tds'],
        'yds': 'fumbles_rec_yds',
        'desc': 'Own recovery yards, TD, No recovery',
        'long': 'Same as previous (57), except when the play results in a '
                'touchdown.',
    },
    59: {
        'cat': 'defense',
        'fields': ['defense_frec'],
        'yds': 'defense_frec_yds',
        'desc': 'Opponent recovery yards',
        'long': 'Yardage gained/lost by a player after he recovered a fumble '
                'by the opposing team.',
    },
    60: {
        'cat': 'defense',
        'fields': ['defense_frec', 'defense_tds', 'defense_frec_tds'],
        'yds': 'defense_frec_yds',
        'desc': 'Opponent recovery yards, TD',
        'long': 'Same as previous (59), except when the play results in a '
                'touchdown.',
    },
    61: {
        'cat': 'defense',
        'fields': [],
        'yds': 'defense_frec_yds',
        'desc': 'Opponent recovery yards, No recovery',
        'long': 'If a player recovered a fumble by the opposing team, then '
                'lateraled to a teammate, the yardage gained/lost by the '
                'teammate would be recorded with this stat.',
    },
    62: {
        'cat': 'defense',
        'fields': ['defense_tds', 'defense_frec_tds'],
        'yds': 'defense_frec_yds',
        'desc': 'Opponent recovery yards, TD, No recovery',
        'long': 'Same as previous, except when the play results in a '
                'touchdown.',
    },
    63: {
        'cat': 'defense',
        'fields': [],
        'yds': 'defense_misc_yds',
        'desc': 'Miscellaneous yards',
        'long': 'This is sort of a catch-all for yardage that doesn\'t '
                'fall into any other category. According to Elias, it does '
                'not include loose ball yardage. Examples are yardage on '
                'missed field goal, blocked punt. This stat is not used '
                'to "balance the books."',
    },
    64: {
        'cat': 'defense',
        'fields': ['defense_tds', 'defense_misc_tds'],
        'yds': 'defense_misc_yds',
        'desc': 'Miscellaneous yards, TD',
        'long': 'Same as previous (63), except when the play results in a '
                'touchdown.',
    },
    68: {
        'cat': 'team',
        'fields': ['timeout'],
        'yds': '',
        'desc': 'Timeout',
        'long': 'Team took a time out.',
    },
    69: {
        'cat': 'kicking',
        'fields': ['kicking_fga', 'kicking_fgmissed'],
        'yds': 'kicking_fgmissed_yds',
        'desc': 'Field goal missed yards',
        'long': 'The length of a missed field goal.',
    },
    70: {
        'cat': 'kicking',
        'fields': ['kicking_fga', 'kicking_fgm'],
        'yds': 'kicking_fgm_yds',
        'desc': 'Field goal yards',
        'long': 'The length of a successful field goal.',
    },
    71: {
        'cat': 'kicking',
        'fields': ['kicking_fga', 'kicking_fgmissed', 'kicking_fgb'],
        'yds': 'kicking_fgmissed_yds',
        'desc': 'Field goal blocked (offense)',
        'long': 'The length of an attempted field goal that was blocked. '
                'Unlike a punt, a field goal is statistically blocked even '
                'if the ball does go beyond the line of scrimmage.',
    },
    72: {
        'cat': 'kicking',
        'fields': ['kicking_xpa', 'kicking_xpmade'],
        'yds': '',
        'desc': 'Extra point - good',
        'long': 'Extra point good. SuperStat uses one code for both '
                'successful and unsuccessful extra points. I think it might '
                'be better to use 2 codes.',
    },
    73: {
        'cat': 'kicking',
        'fields': ['kicking_xpa', 'kicking_xpmissed'],
        'yds': '',
        'desc': 'Extra point - failed',
        'long': 'Extra point failed.',
    },
    74: {
        'cat': 'kicking',
        'fields': ['kicking_xpa', 'kicking_xpmissed', 'kicking_xpb'],
        'yds': '',
        'desc': 'Extra point - blocked',
        'long': 'Extra point blocked. Exclusive of the extra point failed '
                'stat.'
    },
    75: {
        'cat': 'rushing',
        'fields': ['rushing_twopta', 'rushing_twoptm'],
        'yds': '',
        'desc': '2 point rush - good',
        'long': 'Extra points by run good (old version has 0/1 in yards '
                'for failed/good).',
    },
    76: {
        'cat': 'rushing',
        'fields': ['rushing_twopta', 'rushing_twoptmissed'],
        'yds': '',
        'desc': '2 point rush - failed',
        'long': '',
    },
    77: {
        'cat': 'passing',
        'fields': ['passing_twopta', 'passing_twoptm'],
        'yds': '',
        'desc': '2 point pass - good',
        'long': 'Extra points by pass good (old version has 0/1 in yards '
                'for failed/good).',
    },
    78: {
        'cat': 'passing',
        'fields': ['passing_twopta', 'passing_twoptmissed'],
        'yds': '',
        'desc': '2 point pass - failed',
        'long': 'Extra point by pass failed.',
    },
    79: {
        'cat': 'defense',
        'fields': ['defense_tkl'],
        'yds': '',
        'desc': 'Solo tackle',
        'long': 'Tackle with no assists. Note: There are no official '
                'defensive statistics except for sacks.',
    },
    80: {
        'cat': 'defense',
        'fields': ['defense_tkl', 'defense_tkl_primary'],
        'yds': '',
        'desc': 'Assisted tackle',
        'long': 'Tackle with one or more assists.',
    },
    # 81: 1/2 tackle
    # Tackle split equally between two players. This stat is not in use at
    # this time.
    82: {
        'cat': 'defense',
        'fields': ['defense_ast'],
        'yds': '',
        'desc': 'Tackle assist',
        'long': 'Assist to a tackle.',
    },
    83: {
        'cat': 'defense',
        'fields': ['defense_sk'],
        'yds': 'defense_sk_yds',
        'value': 1.0,
        'desc': 'Sack yards (defense)',
        'long': 'Unassisted sack.',
    },
    84: {
        'cat': 'defense',
        'fields': ['defense_sk'],
        'yds': 'defense_sk_yds',
        'value': 0.5,
        'desc': '1/2 sack yards (defense)',
        'long': 'Sack split equally between two players.',
    },
    85: {
        'cat': 'defense',
        'fields': ['defense_pass_def'],
        'yds': '',
        'desc': 'Pass defensed',
        'long': 'Incomplete pass was due primarily to the player\'s action.',
    },
    86: {
        'cat': 'defense',
        'fields': ['defense_puntblk'],
        'yds': '',
        'desc': 'Punt blocked (defense)',
        'long': 'Player blocked a punt.',
    },
    87: {
        'cat': 'defense',
        'fields': ['defense_xpblk'],
        'yds': '',
        'desc': 'Extra point blocked (defense)',
        'long': 'Player blocked the extra point.',
    },
    88: {
        'cat': 'defense',
        'fields': ['defense_fgblk'],
        'yds': '',
        'desc': 'Field goal blocked (defense)',
        'long': '',
    },
    89: {
        'cat': 'defense',
        'fields': ['defense_safe'],
        'yds': '',
        'desc': 'Safety (defense)',
        'long': 'Tackle that resulted in a safety. This is in addition to '
                'a tackle.',
    },
    # 90: 1/2 safety (defense)
    # This stat was used by SuperStat when a 1/2 tackle resulted in a safety.
    # This stat is not in use at this time.
    91: {
        'cat': 'defense',
        'fields': ['defense_ffum'],
        'yds': '',
        'desc': 'Forced fumble (defense)',
        'long': 'Player forced a fumble.',
    },
    93: {
        'cat': 'penalty',
        'fields': ['penalty'],
        'yds': 'penalty_yds',
        'desc': 'Penalty',
        'long': '',
    },
    95: {
        'cat': 'team',
        'fields': ['rushing_loss'],
        'yds': 'rushing_loss_yds',
        'desc': 'Tackled for a loss',
        'long': 'Tackled for a loss (TFL) is an offensive stat. A team is '
                'charged with a TFL if its rush ends behind the line of '
                'scrimmage, and at least one defensive player is credited '
                'with ending the rush with a tackle, or tackle assist. The '
                'stat will contain yardage.',
    },
    # I'm not sure how to classify these...

    # 96: Extra point - safety
    # If there is a fumble on an extra point attempt, and the loose ball goes
    # into the endzone from impetus provided by the defensive team, and
    # becomes dead in the endzone, the offense is awarded 1 point.

    # 99: 2  point rush - safety
    # See "Extra point - safety".

    # 100: 2  point pass - safety
    # See "Extra point - safety".
    102: {
        'cat': 'team',
        'fields': ['kicking_downed'],
        'yds': '',
        'desc': 'Kickoff - kick downed',
        'long': 'SuperStat didn\'t have this code. A kickoff is "downed" when '
                'touched by an offensive player within the 10 yard free zone, '
                'and the ball is awarded to the receivers at the spot of the '
                'touch.',
    },
    103: {
        'cat': 'passing',
        'fields': [],
        'yds': 'passing_sk_yds',
        'desc': 'Sack yards (offense), No sack',
        'long': 'This stat will be used when the passer fumbles, then '
                'recovers, then laterals. The receiver of the lateral gets '
                'sack yardage but no sack.',
    },
    104: {
        'cat': 'receiving',
        'fields': ['receiving_twopta', 'receiving_twoptm'],
        'yds': '',
        'desc': '2 point pass reception - good',
        'long': '',
    },
    105: {
        'cat': 'receiving',
        'fields': ['receiving_twopta', 'receiving_twoptmissed'],
        'yds': '',
        'desc': '2 point pass reception - failed',
        'long': '',
    },
    106: {
        'cat': 'fumbles',
        'fields': ['fumbles_lost'],
        'yds': '',
        'desc': 'Fumble - lost',
        'long': '',
    },
    107: {
        'cat': 'kicking',
        'fields': ['kicking_rec'],
        'yds': '',
        'desc': 'Own kickoff recovery',
        'long': 'Direct recovery of own kickoff, whether or not the kickoff '
                'is onside',
    },
    108: {
        'cat': 'kicking',
        'fields': ['kicking_rec', 'kicking_rec_tds'],
        'yds': '',
        'desc': 'Own kickoff recovery, TD',
        'long': 'Direct recovery in endzone of own kickoff, whether or not '
                'the kickoff is onside.',
    },
    110: {
        'cat': 'defense',
        'fields': ['defense_qbhit'],
        'yds': '',
        'desc': 'Quarterback hit',
        'long': 'Player knocked the quarterback to the ground, quarterback '
                'was not the ball carrier. Not available for games before '
                '2006 season.',
    },
    111: {
        'cat': 'passing',
        'fields': [],
        'yds': 'passing_cmp_air_yds',
        'desc': 'Pass length, completion',
        'long': 'Length of the pass, not including the yards gained by the '
                'receiver after the catch. Unofficial stat. Not available for '
                'games before 2006 season.',
    },
    112: {
        'cat': 'passing',
        'fields': [],
        'yds': 'passing_incmp_air_yds',
        'desc': 'Pass length, No completion',
        'long': 'Length of the pass, if it would have been a completion.'
                'Unofficial stat. Not available for games before 2006 season.',
    },
    113: {
        'cat': 'receiving',
        'fields': [],
        'yds': 'receiving_yac_yds',
        'desc': 'Yardage gained after the catch',
        'long': 'Yardage from where the ball was caught until the player\'s '
                'action was over. Unofficial stat. Not available for games '
                'before 2006 season.',
    },
    115: {
        'cat': 'receiving',
        'fields': ['receiving_tar'],
        'yds': '',
        'desc': 'Pass target',
        'long': 'Player was the target of a pass attempt. Unofficial stat. '
                'Not available for games before 2009 season.',
    },
    120: {
        'cat': 'defense',
        'fields': ['defense_tkl_loss'],
        'yds': '',
        'desc': 'Tackle for a loss',
        'long': 'Player tackled the runner behind the line of scrimmage. '
                'Play must have ended, player must have received a tackle '
                'stat, has to be an offensive player tackled. Unofficial '
                'stat. Not available for games before 2008 season.',
    },
    # 201, 211, 212 and 213 are for NFL Europe.
    301: {
        'cat': 'team',
        'fields': ['xp_aborted'],
        'yds': '',
        'desc': 'Extra point - aborted',
        'long': '',
    },
    402: {
        'cat': 'defense',
        'fields': [],
        'yds': 'defense_tkl_loss_yds',
        'desc': 'Tackle for a loss yards',
        'long': '',
    },
    410: {
        'cat': 'kicking',
        'fields': [],
        'yds': 'kicking_all_yds',
        'desc': 'Kickoff and length of kick',
        'long': 'Kickoff and length of kick. Includes end zone yards '
                'for all kicks into the end zone, including kickoffs '
                'ending in a touchback.',
    },
}

########NEW FILE########
__FILENAME__ = update_players
# Here's an outline of how this program works.
# Firstly, we load a dictionary mapping GSIS identifier to a dictionary of
# player meta data. This comes from either the flag `json-update-file` or
# nflgame's "players.json" file. We then build a reverse map from profile
# identifier (included in player meta data) to GSIS identifier.
#
# We then look at all players who have participated in the last week of
# play. Any player in this set that is not in the aforementioned mapping
# has his GSIS identifier and name (e.g., `T.Brady`) added to a list of
# players to update.
#
# (N.B. When the initial mappings are empty, then every player who recorded
# a statistic since 2009 is added to this list.)
#
# For each player in the list to update, we need to obtain the profile
# identifier. This is done by sending a single HEAD request to the
# `gsis_profile` URL. The URL is a redirect to their canonical profile page,
# with which we extract the profile id. We add this mapping to both of the
# mappings discussed previously. (But note that the meta data in the GSIS
# identifier mapping is incomplete.)
#
# We now fetch the roster lists for each of the 32 teams from NFL.com.
# The roster list contains all relevant meta data *except* the GSIS identifier.
# However, since we have a profile identifier for each player (which is
# included in the roster list), we can connect player meta data with a
# particular GSIS identifier. If we happen to see a player on the roster that
# isn't in the mapping from profile identifier to GSIS identifier, then we need
# to do a full GET request on that player's profile to retrieve the GSIS
# identifier. (This occurs when a player has been added to a roster but hasn't
# recorded any statistics. e.g., Rookies, benchwarmers or offensive linemen.)
#
# We overwrite the initial dictionary of player meta data for each player in
# the roster data, including adding new entries for new players. We then save
# the updated mapping from GSIS identifier to player meta data to disk as JSON.
# (The JSON dump is sorted by key so that diffs are meaningful.)
#
# This approach requires a few thousand HEAD requests to NFL.com on the first
# run. But after that, most runs will only require 32 requests for the roster
# list (small potatoes) and perhaps a few HEAD/GET requests if there happens to
# be a new player found.

from __future__ import absolute_import, division, print_function
import argparse
import json
import multiprocessing.pool
import os
import re
import sys

import httplib2

from bs4 import BeautifulSoup

import nflgame
import nflgame.live
import nflgame.player

urls = {
    'roster': 'http://www.nfl.com/teams/roster?team=%s',
    'gsis_profile': 'http://www.nfl.com/players/profile?id=%s',
}

def new_http():
    http = httplib2.Http(timeout=10)
    http.follow_redirects = False
    return http


def initial_mappings(conf):
    metas, reverse = {}, {}
    try:
        with open(conf.json_update_file) as fp:
            metas = json.load(fp)
        for gsis_id, meta in metas.items():
            reverse[meta['profile_id']] = gsis_id
    except IOError as e:
        eprint('Could not open "%s": %s' % (conf.json_update_file, e))
    # Delete some keys in every entry. We do this to stay fresh.
    # e.g., any player with "team" set should be actively on a roster.
    for k in metas:
        metas[k].pop('team', None)
        metas[k].pop('status', None)
        metas[k].pop('position', None)
    return metas, reverse


def profile_id_from_url(url):
    if url is None:
        return None
    m = re.search('/([0-9]+)/', url)
    return None if m is None else int(m.group(1))


def profile_url(gsis_id):
    resp, content = new_http().request(urls['gsis_profile'] % gsis_id, 'HEAD')
    if resp['status'] != '301':
        return None
    loc = resp['location']
    if not loc.startswith('http://'):
        loc = 'http://www.nfl.com' + loc
    return loc


def gsis_id(profile_url):
    resp, content = new_http().request(profile_url, 'GET')
    if resp['status'] != '200':
        return None
    m = re.search('GSIS\s+ID:\s+([0-9-]+)', content)
    if m is None:
        return None
    gid = m.group(1).strip()
    if len(gid) != 10:  # Can't be valid...
        return None
    return gid


def roster_soup(team):
    resp, content = new_http().request(urls['roster'] % team, 'GET')
    if resp['status'] != '200':
        return None
    return BeautifulSoup(content)


def try_int(s):
    try:
        return int(s)
    except ValueError:
        return 0


def first_int(s):
    m = re.search('[0-9]+', s)
    if m is None:
        return 0
    return int(m.group(0))


def first_word(s):
    m = re.match('\S+', s)
    if m is None:
        return ''
    return m.group(0)


def height_as_inches(txt):
    # Defaults to 0 if `txt` isn't parseable.
    feet, inches = 0, 0
    pieces = re.findall('[0-9]+', txt)
    if len(pieces) >= 1:
        feet = try_int(pieces[0])
        if len(pieces) >= 2:
            inches = try_int(pieces[1])
    return feet * 12 + inches


def meta_from_soup_row(team, soup_row):
    tds, data = [], []
    for td in soup_row.find_all('td'):
        tds.append(td)
        data.append(td.get_text().strip())
    profile_url = 'http://www.nfl.com%s' % tds[1].a['href']

    name = tds[1].a.get_text().strip()
    if ',' not in name:
        last_name, first_name = name, ''
    else:
        last_name, first_name = map(lambda s: s.strip(), name.split(','))

    return {
        'team': team,
        'profile_id': profile_id_from_url(profile_url),
        'profile_url': profile_url,
        'number': try_int(data[0]),
        'first_name': first_name,
        'last_name': last_name,
        'full_name': '%s %s' % (first_name, last_name),
        'position': data[2],
        'status': data[3],
        'height': height_as_inches(data[4]),
        'weight': first_int(data[5]),
        'birthdate': data[6],
        'years_pro': try_int(data[7]),
        'college': data[8],
    }


def meta_from_profile_html(html):
    if not html:
        return html
    try:
        soup = BeautifulSoup(html)
        pinfo = soup.find(id='player-bio').find(class_='player-info')

        # Get the full name and split it into first and last.
        # Assume that if there are no spaces, then the name is the last name.
        # Otherwise, all words except the last make up the first name.
        # Is that right?
        name = pinfo.find(class_='player-name').get_text().strip()
        name_pieces = name.split(' ')
        if len(name_pieces) == 1:
            first, last = '', name
        else:
            first, last = ' '.join(name_pieces[0:-1]), name_pieces[-1]
        meta = {
            'first_name': first,
            'last_name': last,
            'full_name': name,
        }

        # The position is only in the <title>... Weird.
        title = soup.find('title').get_text()
        m = re.search(',\s+([A-Z]+)', title)
        if m is not None:
            meta['position'] = m.group(1)

        # Look for a whole bunch of fields in the format "Field: Value".
        search = pinfo.get_text()
        fields = {'Height': 'height', 'Weight': 'weight', 'Born': 'birthdate',
                  'College': 'college'}
        for f, key in fields.items():
            m = re.search('%s:\s+([\S ]+)' % f, search)
            if m is not None:
                meta[key] = m.group(1)
                if key == 'height':
                    meta[key] = height_as_inches(meta[key])
                elif key == 'weight':
                    meta[key] = first_int(meta[key])
                elif key == 'birthdate':
                    meta[key] = first_word(meta[key])

        # Experience is a little weirder...
        m = re.search('Experience:\s+([0-9]+)', search)
        if m is not None:
            meta['years_pro'] = int(m.group(1))

        return meta
    except AttributeError:
        return None


def players_from_games(existing, games):
    for g in games:
        if g is None:
            continue
        for d in g.drives:
            for p in d.plays:
                for player in p.players:
                    if player.playerid not in existing:
                        yield player.playerid, player.name


def eprint(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def progress(cur, total):
    ratio = 100 * (float(cur) / float(total))
    eprint('\r%d/%d complete. (%0.2f%%)' % (cur, total, ratio), end='')


def progress_done():
    eprint('\nDone!')


def run():
    parser = argparse.ArgumentParser(
        description='Efficiently download player meta data from NFL.com. Note '
                    'that each invocation of this program guarantees at least '
                    '32 HTTP requests to NFL.com',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    aa = parser.add_argument
    aa('--json-update-file', type=str, default=None,
       help='When set, the file provided will be updated in place with new '
            'meta data from NFL.com. If this option is not set, then the '
            '"players.json" file that comes with nflgame will be updated '
            'instead.')
    aa('--simultaneous-reqs', type=int, default=3,
       help='The number of simultaneous HTTP requests sent to NFL.com at a '
            'time. Set this lower if you are worried about hitting their '
            'servers.')
    aa('--full-scan', action='store_true',
       help='Forces a full scan of nflgame player data since 2009. Typically, '
            'this is only done when starting with a fresh JSON player '
            'database. But it can be useful to re-scan all of the players if '
            'past errors went ignored and data is missing. The advantage of '
            'using this option over starting fresh is that an existing '
            '(gsis_id <-> profile_id) mapping can be used for the majority of '
            'players, instead of querying NFL.com for the mapping all over '
            'again.')
    aa('--no-block', action='store_true',
       help='When set, this program will exit with an error instead of '
            'displaying a prompt to continue. This is useful when calling '
            'this program from another script. The idea here is not to block '
            'indefinitely if something goes wrong and the program wants to '
            'do a fresh update.')
    aa('--phase', default=None, choices=['PRE', 'REG', 'POST'],
       help='Force the update to use the given phase of the season.')
    aa('--year', default=None, type=int,
       help='Force the update to use nflgame players from a specific year.')
    aa('--week', default=None, type=int,
       help='Force the update to use nflgame players from a specific week.')
    args = parser.parse_args()

    if args.json_update_file is None:
        args.json_update_file = nflgame.player._player_json_file
    teams = [team[0] for team in nflgame.teams]
    pool = multiprocessing.pool.ThreadPool(args.simultaneous_reqs)

    # Before doing anything laborious, make sure we have write access to
    # the JSON database.
    if not os.access(args.json_update_file, os.W_OK):
        eprint('I do not have write access to "%s".' % args.json_update_file)
        eprint('Without write access, I cannot update the player database.')
        sys.exit(1)

    # Fetch the initial mapping of players.
    metas, reverse = initial_mappings(args)
    if len(metas) == 0:
        if args.no_block:
            eprint('I want to do a full update, but I have been told to\n'
                   'exit instead of asking if you want to continue.')
            sys.exit(1)

        eprint("nflgame doesn't know about any players.")
        eprint("Updating player data will require several thousand HTTP HEAD "
               "requests to NFL.com.")
        eprint("It is strongly recommended to find the 'players.json' file "
               "that comes with nflgame.")
        eprint("Are you sure you want to continue? [y/n] ", end='')
        answer = raw_input()
        if answer[0].lower() != 'y':
            eprint("Quitting...")
            sys.exit(1)

    # Accumulate errors as we go. Dump them at the end.
    errors = []

    # Now fetch a set of players that aren't in our mapping already.
    # Restrict the search to the current week if we have a non-empty mapping.
    if len(metas) == 0 or args.full_scan:
        eprint('Loading players in games since 2009, this may take a while...')
        players = {}

        # Grab players one game a time to avoid obscene memory requirements.
        for _, schedule in nflgame.sched.games.itervalues():
            # If the game is too far in the future, skip it...
            if nflgame.live._game_datetime(schedule) > nflgame.live._now():
                continue
            g = nflgame.game.Game(schedule['eid'])
            for pid, name in players_from_games(metas, [g]):
                players[pid] = name
        eprint('Done.')
    else:
        year, week = nflgame.live.current_year_and_week()
        phase = nflgame.live._cur_season_phase
        if args.phase is not None:
            phase = args.phase
        if args.year is not None:
            year = args.year
        if args.week is not None:
            week = args.week

        eprint('Loading games for %s %d week %d' % (phase, year, week))
        games = nflgame.games(year, week, kind=phase)
        players = dict(players_from_games(metas, games))

    # Find the profile ID for each new player.
    if len(players) > 0:
        eprint('Finding (profile id -> gsis id) mapping for players...')

        def fetch(t):  # t[0] is the gsis_id and t[1] is the gsis name
            return t[0], t[1], profile_url(t[0])
        for i, t in enumerate(pool.imap(fetch, players.items()), 1):
            gid, name, purl = t
            pid = profile_id_from_url(purl)

            progress(i, len(players))
            if purl is None or pid is None:
                errors.append('Could not get profile URL for (%s, %s)'
                              % (gid, name))
                continue

            assert gid not in metas
            metas[gid] = {'gsis_id': gid, 'gsis_name': name,
                          'profile_url': purl, 'profile_id': pid}
            reverse[pid] = gid
        progress_done()

    # Get the soup for each team roster.
    eprint('Downloading team rosters...')
    roster = []

    def fetch(team):
        return team, roster_soup(team)
    for i, (team, soup) in enumerate(pool.imap(fetch, teams), 1):
        progress(i, len(teams))

        if soup is None:
            errors.append('Could not get roster for team %s' % team)
            continue
        for row in soup.find(id='result').find('tbody').find_all('tr'):
            roster.append(meta_from_soup_row(team, row))
    progress_done()

    # Find the gsis identifiers for players that are in the roster but haven't
    # recorded a statistic yet. (i.e., Not in nflgame play data.)
    purls = [r['profile_url']
             for r in roster if r['profile_id'] not in reverse]
    if len(purls) > 0:
        eprint('Fetching GSIS identifiers for players not in nflgame...')

        def fetch(purl):
            return purl, gsis_id(purl)
        for i, (purl, gid) in enumerate(pool.imap(fetch, purls), 1):
            progress(i, len(purls))

            if gid is None:
                errors.append('Could not get GSIS id at %s' % purl)
                continue
            reverse[profile_id_from_url(purl)] = gid
        progress_done()

    # Now merge the data from `rosters` into `metas` by using `reverse` to
    # establish the correspondence.
    for data in roster:
        gsisid = reverse.get(data['profile_id'], None)
        if gsisid is None:
            errors.append('Could not find gsis_id for %s' % data)
            continue
        merged = dict(metas.get(gsisid, {}), **data)
        merged['gsis_id'] = gsisid
        metas[gsisid] = merged

    # Finally, try to scrape meta data for players who aren't on a roster
    # but have recorded a statistic in nflgame.
    gids = [(gid, meta['profile_url'])
            for gid, meta in metas.iteritems()
            if 'full_name' not in meta and 'profile_url' in meta]
    if len(gids):
        eprint('Fetching meta data for players not on a roster...')

        def fetch(t):
            gid, purl = t
            resp, content = new_http().request(purl, 'GET')
            if resp['status'] != '200':
                if resp['status'] == '404':
                    return gid, purl, False
                else:
                    return gid, purl, None
            return gid, purl, content
        for i, (gid, purl, html) in enumerate(pool.imap(fetch, gids), 1):
            progress(i, len(gids))
            more_meta = meta_from_profile_html(html)
            if not more_meta:
                # If more_meta is False, then it was a 404. Not our problem.
                if more_meta is None:
                    errors.append('Could not fetch HTML for %s' % purl)
                continue
            metas[gid] = dict(metas[gid], **more_meta)
        progress_done()

    assert len(metas) > 0, "Have no players to add... ???"
    with open(args.json_update_file, 'w+') as fp:
        json.dump(metas, fp, indent=4, sort_keys=True)

    if len(errors) > 0:
        eprint('\n')
        eprint('There were some errors during the download. Usually this is a')
        eprint('result of an HTTP request timing out, which means the')
        eprint('resulting "players.json" file is probably missing some data.')
        eprint('An appropriate solution is to re-run the script until there')
        eprint('are no more errors (or when the errors are problems on ')
        eprint('NFL.com side.)')
        eprint('-' * 79)
        eprint(('\n' + ('-' * 79) + '\n').join(errors))

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = update_sched
from __future__ import absolute_import, division, print_function
import argparse
import time
import json
import os
import sys
import urllib2
import xml.dom.minidom as xml

import nflgame
from nflgame import OrderedDict


def year_phase_week():
    cur_year, _ = nflgame.live.current_year_and_week()
    season_types = (
        ('PRE', xrange(1, 4 + 1)),
        ('REG', xrange(1, 17 + 1)),
        ('POST', xrange(1, 4 + 1)),
    )
    for year in range(2009, cur_year+1):
        for stype, weeks in season_types:
            for week in weeks:
                yield year, stype, week


def schedule_url(year, stype, week):
    """
    Returns the NFL.com XML schedule URL. `year` should be an
    integer, `stype` should be one of the strings `PRE`, `REG` or
    `POST`, and `gsis_week` should be a value in the range
    `[1, 17]`.
    """
    xmlurl = 'http://www.nfl.com/ajax/scorestrip?'
    if stype == 'POST':
        week += 17
        if week == 21:  # NFL.com you so silly
            week += 1
    return '%sseason=%d&seasonType=%s&week=%d' % (xmlurl, year, stype, week)


def week_schedule(year, stype, week):
    """
    Returns a list of dictionaries with information about each game in
    the week specified. The games are ordered by gsis_id. `year` should
    be an integer, `stype` should be one of the strings `PRE`, `REG` or
    `POST`, and `gsis_week` should be a value in the range `[1, 17]`.
    """
    url = schedule_url(year, stype, week)
    try:
        dom = xml.parse(urllib2.urlopen(url))
    except urllib2.HTTPError:
        print >> sys.stderr, 'Could not load %s' % url
        return []

    games = []
    for g in dom.getElementsByTagName("g"):
        gsis_id = g.getAttribute('eid')
        games.append({
            'eid': gsis_id,
            'wday': g.getAttribute('d'),
            'year': year,
            'month': int(gsis_id[4:6]),
            'day': int(gsis_id[6:8]),
            'time': g.getAttribute('t'),
            'season_type': stype,
            'week': week,
            'home': g.getAttribute('h'),
            'away': g.getAttribute('v'),
            'gamekey': g.getAttribute('gsis'),
        })
    return games


def new_schedule():
    """
    Builds an entire schedule from scratch.
    """
    sched = OrderedDict()
    for year, stype, week in year_phase_week():
        update_week(sched, year, stype, week)
    return sched


def update_week(sched, year, stype, week):
    """
    Updates the schedule for the given week in place. `year` should be
    an integer year, `stype` should be one of the strings `PRE`, `REG`
    or `POST`, and `week` should be an integer in the range `[1, 17]`.
    """
    for game in week_schedule(year, stype, week):
        sched[game['eid']] = game


def write_schedule(fpath, sched):
    alist = []
    for gsis_id in sorted(sched):
        alist.append([gsis_id, sched[gsis_id]])
    json.dump({'time': time.time(), 'games': alist},
              open(fpath, 'w+'), indent=1, sort_keys=True)


def eprint(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def run():
    parser = argparse.ArgumentParser(
        description='Updates nflgame\'s schedule to correspond to the latest '
                    'information.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    aa = parser.add_argument
    aa('--json-update-file', type=str, default=None,
       help='When set, the file provided will be updated in place with new '
            'schedule data from NFL.com. If this option is not set, then the '
            '"schedule.json" file that comes with nflgame will be updated '
            'instead.')
    aa('--rebuild', action='store_true',
       help='When set, the entire schedule will be rebuilt.')
    aa('--year', default=None, type=int,
       help='Force the update to a specific year. (Must also set --phase '
            'and --week.)')
    aa('--phase', default=None, choices=['PRE', 'REG', 'POST'],
       help='Force the update to a specific phase. (Must also set --year '
            'and --week.)')
    aa('--week', default=None, type=int,
       help='Force the update to a specific week. (Must also set --year '
            'and --phase.)')
    args = parser.parse_args()

    if args.json_update_file is None:
        args.json_update_file = nflgame.sched._sched_json_file

    # Before doing anything laborious, make sure we have write access to
    # the JSON database.
    if not os.access(args.json_update_file, os.W_OK):
        eprint('I do not have write access to "%s".' % args.json_update_file)
        eprint('Without write access, I cannot update the schedule.')
        sys.exit(1)

    if args.rebuild:
        sched = new_schedule()
    else:
        if None not in (args.year, args.phase, args.week):
            year, phase, week = args.year, args.phase, args.week
        else:
            year, week = nflgame.live.current_year_and_week()
            phase = nflgame.live._cur_season_phase

        sched, last = nflgame.sched._create_schedule(args.json_update_file)
        print('Last updated: %s' % last)
        update_week(sched, year, phase, week)
    write_schedule(args.json_update_file, sched)

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = version
__version__ = '1.2.5'

########NEW FILE########
