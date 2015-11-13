__FILENAME__ = create_tables
#!/usr/bin/env python
"""

Copyright (c) 2007  Dustin Sallings <dustin@spy.net>
"""

import sys
sys.path.append('lib')
sys.path.append('../lib')

import models

models._metadata.create_all(models._engine)

########NEW FILE########
__FILENAME__ = models
import datetime

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, mapper, relation, backref, exc

from whatsup import config

_engine = create_engine(config.CONF.get('general', 'db'))

_metadata = MetaData()

Session = sessionmaker()
Session.configure(bind=_engine)

def wants_session(orig):
    def f(*args):
        session = Session()
        try:
            return orig(*args + (session,))
        finally:
            session.close()
    return f

class Quietable(object):
    def is_quiet(self):
        """Is this user quiet?"""
        rv=False
        if self.quiet_until:
            rv = self.quiet_until > datetime.datetime.now()
        return rv

class User(Quietable):

    @staticmethod
    def by_jid(jid, session=None):
        s=session
        if not s:
            s=Session()
        try:
            return session.query(User).filter_by(jid=jid).one()
        finally:
            if not session:
                s.close()

    @staticmethod
    def update_status(jid, status, session=None):
        """Find or create a user by jid and set the user's status"""
        s=session
        if not s:
            s = Session()
        try:
            u = None
            if not status:
                status="online"
            try:
                u=User.by_jid(jid, s)
            except exc.NoResultFound, e:
                u=User()
                u.jid=jid

            u.status=status
            s.add(u)
            s.commit()
            return u
        finally:
            if not session:
                s.close()

class Watch(Quietable):

    @staticmethod
    def todo(session, timeout=10):
        """Get the items to do."""
        ID_QUERY="""select w.*
          from watches w join users on (users.id == w.user_id)
          where
            users.active is not null
            and users.active = :uactive
            and users.status not in ('dnd', 'offline', 'unavailable')
            and w.active = :wactive
            and ( w.last_update is null or w.last_update < :last_update)
          limit 50
          """
        then=datetime.datetime.now() - datetime.timedelta(minutes=timeout)
        return session.query(Watch).from_statement(ID_QUERY).params(
            uactive=True, wactive=True, last_update=then)

    def status_emoticon(self):
        if not self.active:
            rv=":-#"
        elif self.status == 200:
            rv=":)"
        else:
            rv=":("
        return rv

    def is_quiet(self):
        return super(Watch, self).is_quiet() or self.user.is_quiet()

class Pattern(object):
    pass

_users_table = Table('users', _metadata,
    Column('id', Integer, primary_key=True, index=True, unique=True),
    Column('jid', String(128), index=True, unique=True),
    Column('active', Boolean, default=True),
    Column('status', String(50)),
    Column('quiet_until', DateTime))

_watches_table = Table('watches', _metadata,
    Column('id', Integer, primary_key=True, index=True, unique=True),
    Column('user_id', Integer, ForeignKey('users.id'), index=True),
    Column('url', String(1024)),
    Column('status', Integer),
    Column('active', Boolean, default=True),
    Column('quiet_until', DateTime),
    Column('last_update', DateTime),
)
Index('idx_watches_user_url', _watches_table.c.user_id, _watches_table.c.url,
    unique=True)

_patterns_table = Table('patterns', _metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('watch_id', Integer, ForeignKey('watches.id')),
    Column('positive', Boolean),
    Column('regex', String(1024))
)

mapper(User, _users_table, properties={
    'watches': relation(Watch, cascade="all, delete, delete-orphan")
    })
mapper(Watch, _watches_table, properties={
    'user': relation(User),
    'patterns': relation(Pattern, cascade="all, delete, delete-orphan")
    })
mapper(Pattern, _patterns_table, properties={
    'watch': relation(Watch)
    })

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
"""
Configuration for whatsup.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import ConfigParser
import commands

CONF=ConfigParser.ConfigParser()
CONF.read('whatsup.conf')
SCREEN_NAME = CONF.get('xmpp', 'jid')
VERSION=commands.getoutput("git describe").strip()

BATCH_CONCURRENCY=CONF.getint('general', 'batch_concurrency')
WATCH_FREQ=CONF.getint('general', 'watch_freq')

ADMINS=CONF.get("general", "admins").split(' ')
########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python

from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import AvailablePresence

import xmpp_commands
import config
import models

class WhatsupProtocol(MessageProtocol, PresenceClientProtocol):

    def __init__(self):
        super(WhatsupProtocol, self).__init__()
        self._watching=-1
        self._users=-1

    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)
        PresenceClientProtocol.connectionInitialized(self)

    def connectionMade(self):
        print "Connected!"

        self.commands=xmpp_commands.all_commands
        print "Loaded commands: ", `self.commands.keys()`

        # send initial presence
        self._watching=-1
        self._users=-1
        self.update_presence()

    @models.wants_session
    def update_presence(self, session):
        watching=session.query(models.Watch).count()
        users=session.query(models.User).count()
        if watching != self._watching or users != self._users:
            status="Watching %s URLs for %s users" % (watching, users)
            self.available(None, None, {None: status})
            self._watching = watching
            self._users = users

    def connectionLost(self, reason):
        print "Disconnected!"

    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""

        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = config.SCREEN_NAME
        msg.addElement(('jabber:x:event', 'x')).addElement("composing")

        self.send(msg)

    def send_plain(self, jid, content):
        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = config.SCREEN_NAME
        msg["type"] = 'chat'
        msg.addElement("body", content=content)

        self.send(msg)

    def get_user(self, msg, session):
        jid=JID(msg['from'])
        try:
            rv=models.User.by_jid(jid.userhost(), session)
        except:
            print "Getting user without the jid in the DB (%s)" % jid.full()
            rv=models.User.update_status(jid.userhost(), None, session)
            self.subscribe(jid)
        return rv;

    @models.wants_session
    def _handleCommand(self, msg, cmd, args, session):
        self.commands[cmd.lower()](self.get_user(msg, session),
            self, args, session)
        session.commit()

    def onMessage(self, msg):
        if msg["type"] == 'chat' and hasattr(msg, "body") and msg.body:
            self.typing_notification(msg['from'])
            a=unicode(msg.body).split(' ', 1)
            args = a[1] if len(a) > 1 else None
            if self.commands.has_key(a[0].lower()):
                self._handleCommand(msg, a[0], args)
            else:
                self.send_plain(msg['from'], 'No such command: ' + a[0])
            self.update_presence()

    # presence stuff
    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        print "Available from %s (%s, %s)" % (entity.full(), show, statuses)
        models.User.update_status(entity.userhost(), show)

    def unavailableReceived(self, entity, statuses=None):
        print "Unavailable from %s" % entity.userhost()
        models.User.update_status(entity.userhost(), 'unavailable')

    @models.wants_session
    def subscribedReceived(self, entity, session):
        print "Subscribe received from %s" % (entity.userhost())
        welcome_message="""Welcome to whatsup.

I'll look at web pages so you don't have to.  The most basic thing you can do to add a monitor is the following:

  watch http://www.mywebsite.com/

But I can do more.  Type "help" for more info.
"""
        self.send_plain(entity.full(), welcome_message)
        msg = "New subscriber: %s ( %d )" % (entity.userhost(),
            session.query(models.User).count())
        for a in config.ADMINS:
            self.send_plain(a, msg)

    def unsubscribedReceived(self, entity):
        print "Unsubscribed received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)

    def subscribeReceived(self, entity):
        print "Subscribe received from %s" % (entity.userhost())
        self.subscribe(entity)
        self.subscribed(entity)
        self.update_presence()

    def unsubscribeReceived(self, entity):
        print "Unsubscribe received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)
        self.update_presence()

########NEW FILE########
__FILENAME__ = scheduling
import re
import datetime

import models
import config

from twisted.web import client
from twisted.internet import defer

class CheckSites(object):

    def __init__(self, client):
        self.client = client

    @models.wants_session
    def __call__(self, session):
        ds = defer.DeferredSemaphore(tokens=config.BATCH_CONCURRENCY)
        for watch in models.Watch.todo(session, config.WATCH_FREQ):
            ds.run(self.__urlCheck, watch.id, watch.url)

    def __urlCheck(self, watch_id, url):
        return client.getPage(str(url), timeout=10).addCallbacks(
            callback=lambda page: self.onSuccess(watch_id, page),
            errback=lambda err: self.onError(watch_id, err))

    def __updateDb(self, watch, status, session):
        watch.status=status
        watch.last_update = datetime.datetime.now()
        session.commit()

    def _check_patterns(self, body, watch):
        rv=200
        failed_pattern=None
        for p in watch.patterns:
            r=re.compile(p.regex)
            if r.search(body):
                if not p.positive:
                    rv = -1
                    failed_pattern=p.regex
            else:
                if p.positive:
                    rv = -1
                    failed_pattern=p.regex
        return rv, failed_pattern

    @models.wants_session
    def onSuccess(self, watch_id, page, session):
        print "Success fetching %d: %d bytes" % (watch_id, len(page))
        watch=session.query(models.Watch).filter_by(id=watch_id).one()
        status, pattern = self._check_patterns(page, watch)
        print "Pattern status of %s: %d" % (watch.url, status)
        if status == 200:
            if status != watch.status and not watch.is_quiet():
                self.client.send_plain(watch.user.jid,
                    ":) Status of %s changed from %s to %d"
                    % (watch.url, `watch.status`, status))
        else:
            self._reportError(watch, status, "Pattern failed: %s" % pattern)
        self.__updateDb(watch, status, session)

    def _reportError(self, watch, status, err_msg):
        msg = ":( Error in %s: %d - %s" % (watch.url, status, err_msg)
        if watch.is_quiet():
            print "User is quiet, not sending", msg
        else:
            self.client.send_plain(watch.user.jid, msg)

    @models.wants_session
    def onError(self, watch_id, error, session):
        print "Error fetching %d: %s" % (watch_id, error)
        watch=session.query(models.Watch).filter_by(id=watch_id).one()
        try:
            status=int(error.getErrorMessage()[0:3])
        except:
            status=-1
        self._reportError(watch, status, error.getErrorMessage())
        self.__updateDb(watch, status, session)

########NEW FILE########
__FILENAME__ = xmpp_commands
import sys
import time
import types
import datetime
import re
import sre_constants
import urlparse

from twisted.words.xish import domish
from twisted.web import client
from twisted.internet import reactor
from sqlalchemy.orm import exc

import models

all_commands={}

def arg_required(validator=lambda n: n):
    def f(orig):
        def every(self, user, prot, args, session):
            if validator(args):
                orig(self, user, prot, args, session)
            else:
                prot.send_plain(user.jid, "Arguments required for %s:\n%s"
                    % (self.name, self.extended_help))
        return every
    return f

def is_a_url(u):
    try:
        parsed = urlparse.urlparse(str(u))
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except:
        return False

class CountingFile(object):
    """A file-like object that just counts what's written to it."""
    def __init__(self):
        self.written=0
    def write(self, b):
        self.written += len(b)
    def close(self):
        pass
    def open(self):
        pass
    def read(self):
        return None

class BaseCommand(object):
    """Base class for command processors."""

    def __get_extended_help(self):
        if self.__extended_help:
            return self.__extended_help
        else:
            return self.help

    def __set_extended_help(self, v):
        self.__extended_help=v

    extended_help=property(__get_extended_help, __set_extended_help)

    def __init__(self, name, help=None, extended_help=None):
        self.name=name
        self.help=help
        self.extended_help=extended_help

    def __call__(self, user, prot, args, session):
        raise NotImplementedError()

class WatchRequired(BaseCommand):

    @arg_required(is_a_url)
    def __call__(self, user, prot, args, session):
        a=args.split(' ', 1)
        newarg=None
        if len(a) > 1: newarg=a[1]
        try:
            watch=session.query(models.Watch).filter_by(
                url=a[0]).filter_by(user_id=user.id).one()
            self.process(user, prot, watch, newarg, session)
        except exc.NoResultFound:
            prot.send_plain(user.jid, "Cannot find watch for %s" % a[0])

    def process(self, user, prot, watch, args, session):
        raise NotImplementedError()

class StatusCommand(BaseCommand):

    def __init__(self):
        super(StatusCommand, self).__init__('status', 'Check your status.')

    def __call__(self, user, prot, args, session):
        rv=[]
        rv.append("Jid:  %s" % user.jid)
        rv.append("Jabber status:  %s" % user.status)
        rv.append("Whatsup status:  %s"
            % {True: 'Active', False: 'Inactive'}[user.active])
        rv.append("You are currently watching %d URLs." % len(user.watches))
        if user.is_quiet():
            rv.append("All alerts are quieted until %s" % str(user.quiet_until))
        prot.send_plain(user.jid, "\n".join(rv))

class GetCommand(BaseCommand):

    def __init__(self):
        super(GetCommand, self).__init__('get', 'Get a web page.')

    @arg_required(is_a_url)
    def __call__(self, user, prot, args, session):
        start=time.time()
        cf = CountingFile()
        jid=user.jid
        def onSuccess(value):
            prot.send_plain(jid, "Got %d bytes in %.2fs" %
                (cf.written, (time.time() - start)))
        client.downloadPage(str(args), cf).addCallbacks(
            callback=onSuccess,
            errback=lambda error:(prot.send_plain(
                jid, "Error getting the page: %s (%s)"
                % (error.getErrorMessage(), dir(error)))))

class HelpCommand(BaseCommand):

    def __init__(self):
        super(HelpCommand, self).__init__('help', 'You need help.')

    def __call__(self, user, prot, args, session):
        rv=[]
        if args:
            c=all_commands.get(args.strip().lower(), None)
            if c:
                rv.append("Help for %s:\n" % c.name)
                rv.append(c.extended_help)
            else:
                rv.append("Unknown command %s." % args)
        else:
            for k in sorted(all_commands.keys()):
                rv.append('%s\t%s' % (k, all_commands[k].help))
        rv.append("\nFor more help, see http://dustin.github.com/whatsup/")
        prot.send_plain(user.jid, "\n".join(rv))

class WatchCommand(BaseCommand):

    def __init__(self):
        super(WatchCommand, self).__init__('watch', 'Start watching a page.')

    @arg_required(is_a_url)
    def __call__(self, user, prot, args, session):
        w=models.Watch()
        w.url=args
        w.user=user
        user.watches.append(w)
        prot.send_plain(user.jid, "Started watching %s" % w.url)

class UnwatchCommand(WatchRequired):

    def __init__(self):
        super(UnwatchCommand, self).__init__('unwatch', 'Stop watching a page.')

    def process(self, user, prot, watch, args, session):
        session.delete(watch)
        prot.send_plain(user.jid, "Stopped watching %s" % watch.url)

class WatchingCommand(BaseCommand):
    def __init__(self):
        super(WatchingCommand, self).__init__('watching', 'List your watches.')

    def __call__(self, user, prot, args, session):
        watches=[]
        rv=[("You are watching %d URLs:" % len(user.watches))]
        h={True: 'enabled', False: 'disabled'}
        for w in user.watches:
            watches.append("%s %s - (%s -- %d patterns, last=%s)"
                % (w.status_emoticon(), w.url, h[w.active], len(w.patterns),
                `w.status`))
        rv += sorted(watches)
        prot.send_plain(user.jid, "\n".join(rv))

class InspectCommand(WatchRequired):
    def __init__(self):
        super(InspectCommand, self).__init__('inspect', 'Inspect a watch.')

    def process(self, user, prot, w, args, session):
        rv=[]
        rv.append("Status for %s: %s"
            % (w.url, {True: 'enabled', False: 'disabled'}[w.active]))
        if w.is_quiet():
            qu = w.quiet_until
            if not qu:
                qu = user.quiet_until
            rv.append("Alerts are quiet until %s" % str(qu))
        rv.append("Last update:  %s" % str(w.last_update))
        if w.patterns:
            for p in w.patterns:
                rv.append("\t%s %s" % ({True: '+', False: '-'}[p.positive],
                    p.regex))
        else:
            rv.append("No match patterns configured.")
        prot.send_plain(user.jid, "\n".join(rv))

class BaseMatchCommand(WatchRequired):

    def process(self, user, prot, w, args, session):
        try:
            regex=args
            re.compile(regex) # Check the regex
            m=models.Pattern()
            m.positive=self.isPositive()
            m.regex=regex
            w.patterns.append(m)
            prot.send_plain(user.jid, "Added pattern.")
        except sre_constants.error, e:
            prot.send_plain(user.jid, "Error configuring pattern:  %s" % e.message)

class MatchCommand(BaseMatchCommand):
    def __init__(self):
        super(MatchCommand, self).__init__('match', 'Configure a match for a URL')
        self.extended_help="""Add a positive regex match for a URL.

Usage:  match http://www.example.com/ working
"""

    def isPositive(self):
        return True

class NegMatchCommand(BaseMatchCommand):
    def __init__(self):
        super(NegMatchCommand, self).__init__('negmatch', 'Configure a negative match for a URL')
        self.extended_help="""Add a negative regex match for a URL.

Usage: negmatch http://www.example.com/ hac?[kx]ed.by
"""

    def isPositive(self):
        return False

class ClearMatchesCommand(WatchRequired):
    def __init__(self):
        super(ClearMatchesCommand, self).__init__('clear_matches', 'Clear all matches for a URL')

    def process(self, user, prot, w, args, session):
        w.patterns=[]
        prot.send_plain(user.jid, "Cleared all matches for %s" % w.url)

class DisableCommand(WatchRequired):
    def __init__(self):
        super(DisableCommand, self).__init__('disable', 'Disable checks for a URL')

    def process(self, user, prot, w, args, session):
        w.active=False
        prot.send_plain(user.jid, "Disabled checks for %s" % w.url)

class EnableCommand(WatchRequired):
    def __init__(self):
        super(EnableCommand, self).__init__('enable', 'Enable checks for a URL')

    def process(self, user, prot, w, args, session):
        w.active=True
        prot.send_plain(user.jid, "Enabled checks for %s" % w.url)

class OnCommand(BaseCommand):
    def __init__(self):
        super(OnCommand, self).__init__('on', 'Enable monitoring.')

    def __call__(self, user, prot, args, session):
        user.active=True
        prot.send_plain(user.jid, "Enabled monitoring.")

class OffCommand(BaseCommand):
    def __init__(self):
        super(OffCommand, self).__init__('off', 'Disable monitoring.')

    def __call__(self, user, prot, args, session):
        user.active=False
        prot.send_plain(user.jid, "Disabled monitoring.")

class QuietCommand(BaseCommand):
    def __init__(self):
        super(QuietCommand, self).__init__('quiet', 'Temporarily quiet alerts.')
        self.extended_help="""Quiet alerts for a period of time.

Available time units:  m, h, d

You can either quiet an individual URL like this:

  quiet 5m http://broken.example.com/

or from everything:

  quiet 1h
"""

    @arg_required()
    def __call__(self, user, prot, args, session):
        m = {'m': 1, 'h': 60, 'd': 1440}
        parts=args.split(' ', 1)
        time=parts[0]
        url=None
        if len(parts) > 1: url=parts[1]
        match = re.compile(r'(\d+)([hmd])').match(time)
        if match:
            t = int(match.groups()[0]) * m[match.groups()[1]]
            u=datetime.datetime.now() + datetime.timedelta(minutes=t)

            if url:
                try:
                    w=session.query(models.Watch).filter_by(
                        url=url).filter_by(user_id=user.id).one()
                    w.quiet_until=u
                    prot.send_plain(user.jid, "%s will be quiet until %s"
                        % (w.url, str(u)))
                except exc.NoResultFound:
                    prot.send_plain(user.jid, "Cannot find watch for %s" % url)
            else:
                user.quiet_until=u
                prot.send_plain(user.jid,
                    "You won't hear from me again until %s" % str(u))
        else:
            prot.send_plain(user.jid, "I don't understand how long you want "
                "me to be quiet.  Try 5m")

class WaitForSite(BaseCommand):
    MAX_TIME = 4 * 3600 # How long a wait will be allowed to run
    def __init__(self):
        super(WaitForSite, self).__init__('waitforsite',
            'Wait for a site to become available')
        self.extended_help="""Wait for a site to become available.

Continue checking for the availability of a site until it becomes available."""

    @arg_required(is_a_url)
    def __call__(self, user, prot, args, session):
        self.try_url(user.jid, prot, str(args), time.time())
        prot.send_plain(user.jid, "I'll let you know when %s is up." % args)

    def try_url(self, jid, prot, url, start_time, attempt=1):
        start=time.time()
        cf = CountingFile()
        def onSuccess(value):
            prot.send_plain(jid, "Got %d bytes from %s in %.2fs on attempt %d" %
                (cf.written, url, (time.time() - start), attempt))
        def onError(e):
            if attempt == 1:
                prot.send_plain(jid, "%s failed first request with %s. "
                    "I'll keep trying for %d hours"
                    % (url, e.getErrorMessage(), self.MAX_TIME / 3600))
            if time.time() - start_time > self.MAX_TIME:
                prot.send_plain(jid,
                    "Giving up on %s after %d attempts in %.2f hours. "
                    "Most recent error was %s"
                    % (url, attempt, (time.time() - start_time) / 3600,
                        e.getErrorMessage()))
            else:
                reactor.callLater(60, self.try_url, jid, prot, url, start_time,
                    attempt + 1)

        client.downloadPage(url, cf).addCallbacks(
            callback=onSuccess, errback=onError)

for __t in (t for t in globals().values() if isinstance(type, type(t))):
    if BaseCommand in __t.__mro__:
        try:
            i = __t()
            all_commands[i.name] = i
        except TypeError:
            # Ignore abstract bases
            pass

########NEW FILE########
