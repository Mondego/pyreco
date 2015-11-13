__FILENAME__ = cointipbot
#!/usr/bin/env python
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

from ctb import ctb_action, ctb_coin, ctb_db, ctb_exchange, ctb_log, ctb_misc, ctb_user

import gettext, locale, logging, praw, smtplib, sys, time, traceback, yaml
from email.mime.text import MIMEText
from jinja2 import Environment, PackageLoader

from requests.exceptions import HTTPError, ConnectionError, Timeout
from praw.errors import ExceptionList, APIException, InvalidCaptcha, InvalidUser, RateLimitExceeded
from socket import timeout

# Configure CointipBot logger
logging.basicConfig()
lg = logging.getLogger('cointipbot')


class CointipBot(object):
    """
    Main class for cointip bot
    """

    conf = None
    db = None
    reddit = None
    coins = {}
    exchanges = {}
    jenv = None
    runtime = {'ev': {}, 'regex': []}

    def init_logging(self):
        """
        Initialize logging handlers
        """

        handlers = {}
        levels = ['warning', 'info', 'debug']
        lg = logging.getLogger('cointipbot')
        bt = logging.getLogger('bitcoin')

        # Get handlers
        handlers = {}
        for l in levels:
            if self.conf.logs.levels[l].enabled:
                handlers[l] = logging.FileHandler(self.conf.logs.levels[l].filename, mode='a' if self.conf.logs.levels[l].append else 'w')
                handlers[l].setFormatter(logging.Formatter(self.conf.logs.levels[l].format))

        # Set handlers
        for l in levels:
            if handlers.has_key(l):
                level = logging.WARNING if l == 'warning' else (logging.INFO if l == 'info' else logging.DEBUG)
                handlers[l].addFilter(ctb_log.LevelFilter(level))
                lg.addHandler(handlers[l])
                bt.addHandler(handlers[l])

        # Set default levels
        lg.setLevel(logging.DEBUG)
        bt.setLevel(logging.DEBUG)

        lg.info('CointipBot::init_logging(): -------------------- logging initialized --------------------')
        return True

    def parse_config(self):
        """
        Returns a Python object with CointipBot configuration
        """
        lg.debug('CointipBot::parse_config(): parsing config files...')

        conf = {}
        try:
            prefix='./conf/'
            for i in ['coins', 'db', 'exchanges', 'fiat', 'keywords', 'logs', 'misc', 'reddit', 'regex']:
                lg.debug("CointipBot::parse_config(): reading %s%s.yml", prefix, i)
                conf[i] = yaml.load(open(prefix+i+'.yml'))
        except yaml.YAMLError as e:
            lg.error("CointipBot::parse_config(): error reading config file: %s", e)
            if hasattr(e, 'problem_mark'):
                lg.error("CointipBot::parse_config(): error position: (line %s, column %s)", e.problem_mark.line+1, e.problem_mark.column+1)
            sys.exit(1)

        lg.info('CointipBot::parse_config(): config files has been parsed')
        return ctb_misc.DotDict(conf)

    def connect_db(self):
        """
        Returns a database connection object
        """
        lg.debug('CointipBot::connect_db(): connecting to database...')

        dsn = "mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8" % (self.conf.db.auth.user, self.conf.db.auth.password, self.conf.db.auth.host, self.conf.db.auth.port, self.conf.db.auth.dbname)
        dbobj = ctb_db.CointipBotDatabase(dsn)

        try:
            conn = dbobj.connect()
        except Exception as e:
            lg.error("CointipBot::connect_db(): error connecting to database: %s", e)
            sys.exit(1)

        lg.info("CointipBot::connect_db(): connected to database %s as %s", self.conf.db.auth.dbname, self.conf.db.auth.user)
        return conn

    def connect_reddit(self):
        """
        Returns a praw connection object
        """
        lg.debug('CointipBot::connect_reddit(): connecting to Reddit...')

        conn = praw.Reddit(user_agent = self.conf.reddit.auth.user)
        conn.login(self.conf.reddit.auth.user, self.conf.reddit.auth.password)

        lg.info("CointipBot::connect_reddit(): logged in to Reddit as %s", self.conf.reddit.auth.user)
        return conn

    def self_checks(self):
        """
        Run self-checks before starting the bot
        """

        # Ensure bot is a registered user
        b = ctb_user.CtbUser(name=self.conf.reddit.auth.user.lower(), ctb=self)
        if not b.is_registered():
            b.register()

        # Ensure (total pending tips) < (CointipBot's balance)
        for c in self.coins:
            ctb_balance = b.get_balance(coin=c, kind='givetip')
            pending_tips = float(0)
            actions = ctb_action.get_actions(atype='givetip', state='pending', coin=c, ctb=self)
            for a in actions:
                pending_tips += a.coinval
            if (ctb_balance - pending_tips) < -0.000001:
                raise Exception("CointipBot::self_checks(): CointipBot's %s balance (%s) < total pending tips (%s)" % (c.upper(), ctb_balance, pending_tips))

        # Ensure coin balances are positive
        for c in self.coins:
            b = float(self.coins[c].conn.getbalance())
            if b < 0:
                raise Exception("CointipBot::self_checks(): negative balance of %s: %s" % (c, b))

        # Ensure user accounts are intact and balances are not negative
        sql = "SELECT username FROM t_users ORDER BY username"
        for mysqlrow in self.db.execute(sql):
            u = ctb_user.CtbUser(name=mysqlrow['username'], ctb=self)
            if not u.is_registered():
                raise Exception("CointipBot::self_checks(): user %s is_registered() failed" % mysqlrow['username'])
        #    for c in vars(self.coins):
        #        if u.get_balance(coin=c, kind='givetip') < 0:
        #            raise Exception("CointipBot::self_checks(): user %s %s balance is negative" % (mysqlrow['username'], c))

        return True

    def expire_pending_tips(self):
        """
        Decline any pending tips that have reached expiration time limit
        """

        # Calculate timestamp
        seconds = int(self.conf.misc.times.expire_pending_hours * 3600)
        created_before = time.mktime(time.gmtime()) - seconds
        counter = 0

        # Get expired actions and decline them
        for a in ctb_action.get_actions(atype='givetip', state='pending', created_utc='< ' + str(created_before), ctb=self):
            a.expire()
            counter += 1

        # Done
        return (counter > 0)

    def check_inbox(self):
        """
        Evaluate new messages in inbox
        """
        lg.debug('> CointipBot::check_inbox()')

        try:

            # Try to fetch some messages
            messages = list(ctb_misc.praw_call(self.reddit.get_unread, limit=self.conf.reddit.scan.batch_limit))
            messages.reverse()

            # Process messages
            for m in messages:
                # Sometimes messages don't have an author (such as 'you are banned from' message)
                if not m.author:
                    lg.info("CointipBot::check_inbox(): ignoring msg with no author")
                    ctb_misc.praw_call(m.mark_as_read)
                    continue

                lg.info("CointipBot::check_inbox(): %s from %s", "comment" if m.was_comment else "message", m.author.name)

                # Ignore duplicate messages (sometimes Reddit fails to mark messages as read)
                if ctb_action.check_action(msg_id=m.id, ctb=self):
                    lg.warning("CointipBot::check_inbox(): duplicate action detected (msg.id %s), ignoring", m.id)
                    ctb_misc.praw_call(m.mark_as_read)
                    continue

                # Ignore self messages
                if m.author and m.author.name.lower() == self.conf.reddit.auth.user.lower():
                    lg.debug("CointipBot::check_inbox(): ignoring message from self")
                    ctb_misc.praw_call(m.mark_as_read)
                    continue

                # Ignore messages from banned users
                if m.author and self.conf.reddit.banned_users:
                    lg.debug("CointipBot::check_inbox(): checking whether user '%s' is banned..." % m.author)
                    u = ctb_user.CtbUser(name = m.author.name, redditobj = m.author, ctb = self)
                    if u.banned:
                        lg.info("CointipBot::check_inbox(): ignoring banned user '%s'" % m.author)
                        ctb_misc.praw_call(m.mark_as_read)
                        continue

                action = None
                if m.was_comment:
                    # Attempt to evaluate as comment / mention
                    action = ctb_action.eval_comment(m, self)
                else:
                    # Attempt to evaluate as inbox message
                    action = ctb_action.eval_message(m, self)

                # Perform action, if found
                if action:
                    lg.info("CointipBot::check_inbox(): %s from %s (m.id %s)", action.type, action.u_from.name, m.id)
                    lg.debug("CointipBot::check_inbox(): message body: <%s>", m.body)
                    action.do()
                else:
                    lg.info("CointipBot::check_inbox(): no match")
                    if self.conf.reddit.messages.sorry and not m.subject in ['post reply', 'comment reply']:
                        user = ctb_user.CtbUser(name=m.author.name, redditobj=m.author, ctb=self)
                        tpl = self.jenv.get_template('didnt-understand.tpl')
                        msg = tpl.render(user_from=user.name, what='comment' if m.was_comment else 'message', source_link=m.permalink if hasattr(m, 'permalink') else None, ctb=self)
                        lg.debug("CointipBot::check_inbox(): %s", msg)
                        user.tell(subj='What?', msg=msg, msgobj=m if not m.was_comment else None)

                # Mark message as read
                ctb_misc.praw_call(m.mark_as_read)

        except (HTTPError, ConnectionError, Timeout, timeout) as e:
            lg.warning("CointipBot::check_inbox(): Reddit is down (%s), sleeping", e)
            time.sleep(self.conf.misc.times.sleep_seconds)
            pass
        except RateLimitExceeded as e:
             lg.warning("CointipBot::check_inbox(): rate limit exceeded, sleeping for %s seconds", e.sleep_time) 
             time.sleep(e.sleep_time)
             time.sleep(1)
             pass
        except Exception as e:
            lg.error("CointipBot::check_inbox(): %s", e)
            raise

        lg.debug("< CointipBot::check_inbox() DONE")
        return True

    def init_subreddits(self):
        """
        Determine a list of subreddits and create a PRAW object
        """
        lg.debug("> CointipBot::init_subreddits()")

        try:

            if not hasattr(self.conf.reddit, 'subreddits'):
                my_reddits_list = None
                my_reddits_string = None

                if hasattr(self.conf.reddit.scan, 'these_subreddits'):
                    # Subreddits are specified in conf.yml
                    my_reddits_list = list(self.conf.reddit.scan.these_subreddits)

                elif self.conf.reddit.scan.my_subreddits:
                    # Subreddits are subscribed to by bot user
                    my_reddits = ctb_misc.praw_call(self.reddit.get_my_subreddits, limit=None)
                    my_reddits_list = []
                    for my_reddit in my_reddits:
                        my_reddits_list.append(my_reddit.display_name.lower())
                    my_reddits_list.sort()

                else:
                    # No subreddits configured
                    lg.debug("< CointipBot::check_subreddits() DONE (no subreddits configured to scan)")
                    return False

                # Build subreddits string
                my_reddits_string = "+".join(my_reddits_list)

                # Get multi-reddit PRAW object
                lg.debug("CointipBot::check_subreddits(): multi-reddit string: %s", my_reddits_string)
                self.conf.reddit.subreddits = ctb_misc.praw_call(self.reddit.get_subreddit, my_reddits_string)

        except Exception as e:
            lg.error("CointipBot::check_subreddits(): coudln't get subreddits: %s", e)
            raise

        lg.debug("< CointipBot::init_subreddits() DONE")
        return True

    def check_subreddits(self):
        """
        Evaluate new comments from configured subreddits
        """
        lg.debug("> CointipBot::check_subreddits()")

        try:
            # Process comments until old comment reached

            # Get last_processed_comment_time if necessary
            if not hasattr(self.conf.reddit, 'last_processed_comment_time') or self.conf.reddit.last_processed_comment_time <= 0:
                self.conf.reddit.last_processed_comment_time = ctb_misc.get_value(conn=self.db, param0='last_processed_comment_time')
            updated_last_processed_time = 0

            # Fetch comments from subreddits
            my_comments = ctb_misc.praw_call(self.conf.reddit.subreddits.get_comments, limit=self.conf.reddit.scan.batch_limit)

            # Match each comment against regex
            counter = 0
            for c in my_comments:
                # Stop processing if old comment reached
                #lg.debug("check_subreddits(): c.id %s from %s, %s <= %s", c.id, c.subreddit.display_name, c.created_utc, self.conf.reddit.last_processed_comment_time)
                if c.created_utc <= self.conf.reddit.last_processed_comment_time:
                    lg.debug("CointipBot::check_subreddits(): old comment reached")
                    break
                counter += 1
                if c.created_utc > updated_last_processed_time:
                    updated_last_processed_time = c.created_utc

                # Ignore duplicate comments (may happen when bot is restarted)
                if ctb_action.check_action(msg_id=c.id, ctb=self):
                    lg.warning("CointipBot::check_inbox(): duplicate action detected (comment.id %s), ignoring", c.id)
                    continue

                # Ignore comments from banned users
                if c.author and self.conf.reddit.banned_users:
                    lg.debug("CointipBot::check_subreddits(): checking whether user '%s' is banned..." % c.author)
                    u = ctb_user.CtbUser(name = c.author.name, redditobj = c.author, ctb = self)
                    if u.banned:
                        lg.info("CointipBot::check_subreddits(): ignoring banned user '%s'" % c.author)
                        continue

                # Attempt to evaluate comment
                action = ctb_action.eval_comment(c, self)

                # Perform action, if found
                if action:
                    lg.info("CointipBot::check_subreddits(): %s from %s (%s)", action.type, action.u_from.name, c.id)
                    lg.debug("CointipBot::check_subreddits(): comment body: <%s>", c.body)
                    action.do()
                else:
                    lg.info("CointipBot::check_subreddits(): no match")

            lg.debug("CointipBot::check_subreddits(): %s comments processed", counter)
            if counter >= self.conf.reddit.scan.batch_limit - 1:
                lg.warning("CointipBot::check_subreddits(): conf.reddit.scan.batch_limit (%s) was not large enough to process all comments", self.conf.reddit.scan.batch_limit)

        except (HTTPError, RateLimitExceeded, timeout) as e:
            lg.warning("CointipBot::check_subreddits(): Reddit is down (%s), sleeping", e)
            time.sleep(self.conf.misc.times.sleep_seconds)
            pass
        except Exception as e:
            lg.error("CointipBot::check_subreddits(): coudln't fetch comments: %s", e)
            raise

        # Save updated last_processed_time value
        if updated_last_processed_time > 0:
            self.conf.reddit.last_processed_comment_time = updated_last_processed_time
        ctb_misc.set_value(conn=self.db, param0='last_processed_comment_time', value0=self.conf.reddit.last_processed_comment_time)

        lg.debug("< CointipBot::check_subreddits() DONE")
        return True

    def refresh_ev(self):
        """
        Refresh coin/fiat exchange values using self.exchanges
        """

        # Return if rate has been checked in the past hour
        seconds = int(1 * 3600)
        if hasattr(self.conf.exchanges, 'last_refresh') and self.conf.exchanges.last_refresh + seconds > int(time.mktime(time.gmtime())):
            lg.debug("< CointipBot::refresh_ev(): DONE (skipping)")
            return

        # For each enabled coin...
        for c in vars(self.conf.coins):
            if self.conf.coins[c].enabled:

                # Get BTC/coin exchange rate
                values = []
                result = 0.0

                if not self.conf.coins[c].unit == 'btc':
                    # For each exchange that supports this coin...
                    for e in self.exchanges:
                        if self.exchanges[e].supports_pair(_name1=self.conf.coins[c].unit, _name2='btc'):
                            # Get ticker value from exchange
                            value = self.exchanges[e].get_ticker_value(_name1=self.conf.coins[c].unit, _name2='btc')
                            if value and float(value) > 0.0:
                                values.append(float(value))

                    # Result is average of all responses
                    if len(values) > 0:
                        result = sum(values) / float(len(values))

                else:
                    # BTC/BTC rate is always 1
                    result = 1.0

                # Assign result to self.runtime['ev']
                if not self.runtime['ev'].has_key(c):
                    self.runtime['ev'][c] = {}
                self.runtime['ev'][c]['btc'] = result

        # For each enabled fiat...
        for f in vars(self.conf.fiat):
            if self.conf.fiat[f].enabled:

                # Get fiat/BTC exchange rate
                values = []
                result = 0.0

                # For each exchange that supports this fiat...
                for e in self.exchanges:
                    if self.exchanges[e].supports_pair(_name1='btc', _name2=self.conf.fiat[f].unit):
                        # Get ticker value from exchange
                        value = self.exchanges[e].get_ticker_value(_name1='btc', _name2=self.conf.fiat[f].unit)
                        if value and float(value) > 0.0:
                            values.append(float(value))

                # Result is average of all responses
                if len(values) > 0:
                    result = sum(values) / float(len(values))

                # Assign result to self.runtime['ev']
                if not self.runtime['ev'].has_key('btc'):
                    self.runtime['ev']['btc'] = {}
                self.runtime['ev']['btc'][f] = result

        lg.debug("CointipBot::refresh_ev(): %s", self.runtime['ev'])

        # Update last_refresh
        self.conf.exchanges.last_refresh = int(time.mktime(time.gmtime()))

    def coin_value(self, _coin, _fiat):
        """
        Quick method to return _fiat value of _coin
        """
        try:
            value = self.runtime['ev'][_coin]['btc'] * self.runtime['ev']['btc'][_fiat]
        except KeyError as e:
            lg.warning("CointipBot::coin_value(%s, %s): KeyError", _coin, _fiat)
            value = 0.0
        return value

    def notify(self, _msg=None):
        """
        Send _msg to configured destination
        """

        # Construct MIME message
        msg = MIMEText(_msg)
        msg['Subject'] = self.conf.misc.notify.subject
        msg['From'] = self.conf.misc.notify.addr_from
        msg['To'] = self.conf.misc.notify.addr_to

        # Send MIME message
        server = smtplib.SMTP(self.conf.misc.notify.smtp_host)
        if self.conf.misc.notify.smtp_tls:
            server.starttls()
        server.login(self.conf.misc.notify.smtp_username, self.conf.misc.notify.smtp_password)
        server.sendmail(self.conf.misc.notify.addr_from, self.conf.misc.notify.addr_to, msg.as_string())
        server.quit()

    def __init__(self, self_checks=True, init_reddit=True, init_coins=True, init_exchanges=True, init_db=True, init_logging=True):
        """
        Constructor. Parses configuration file and initializes bot.
        """
        lg.info("CointipBot::__init__()...")

        # Configuration
        self.conf = self.parse_config()

        # Logging
        if init_logging:
            self.init_logging()

        # Templating with jinja2
        self.jenv = Environment(trim_blocks=True, loader=PackageLoader('cointipbot', 'tpl/jinja2'))

        # Database
        if init_db:
            self.db = self.connect_db()

        # Coins
        if init_coins:
            for c in vars(self.conf.coins):
                if self.conf.coins[c].enabled:
                    self.coins[c] = ctb_coin.CtbCoin(_conf=self.conf.coins[c])
            if not len(self.coins) > 0:
                lg.error("CointipBot::__init__(): Error: please enable at least one type of coin")
                sys.exit(1)

        # Exchanges
        if init_exchanges:
            for e in vars(self.conf.exchanges):
                if self.conf.exchanges[e].enabled:
                    self.exchanges[e] = ctb_exchange.CtbExchange(_conf=self.conf.exchanges[e])
            if not len(self.exchanges) > 0:
                lg.warning("Cointipbot::__init__(): Warning: no exchanges are enabled")

        # Reddit
        if init_reddit:
            self.reddit = self.connect_reddit()
            self.init_subreddits()
            # Regex for Reddit messages
            ctb_action.init_regex(self)

        # Self-checks
        if self_checks:
            self.self_checks()

        lg.info("< CointipBot::__init__(): DONE, batch-limit = %s, sleep-seconds = %s", self.conf.reddit.scan.batch_limit, self.conf.misc.times.sleep_seconds)

    def __str__(self):
        """
        Return string representation of self
        """
        me = "<CointipBot: sleepsec=%s, batchlim=%s, ev=%s"
        me = me % (self.conf.misc.times.sleep_seconds, self.conf.reddit.scan.batch_limit, self.runtime['ev'])
        return me

    def main(self):
        """
        Main loop
        """

        while (True):
            try:
                lg.debug("CointipBot::main(): beginning main() iteration")

                # Refresh exchange rate values
                self.refresh_ev()

                # Check personal messages
                self.check_inbox()

                # Expire pending tips
                self.expire_pending_tips()

                # Check subreddit comments for tips
                if self.conf.reddit.scan.my_subreddits or hasattr(self.conf.reddit.scan, 'these_subreddits'):
                    self.check_subreddits()

                # Sleep
                lg.debug("CointipBot::main(): sleeping for %s seconds...", self.conf.misc.times.sleep_seconds)
                time.sleep(self.conf.misc.times.sleep_seconds)

            except Exception as e:
                lg.error("CointipBot::main(): exception: %s", e)
                tb = traceback.format_exc()
                lg.error("CointipBot::main(): traceback: %s", tb)
                # Send a notification, if enabled
                if self.conf.misc.notify.enabled:
                    self.notify(_msg=tb)
                sys.exit(1)

########NEW FILE########
__FILENAME__ = ctb_action
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import ctb_user, ctb_misc, ctb_stats

import logging, praw, re, time
from random import randint

lg = logging.getLogger('cointipbot')

class CtbActionExc(Exception):
    pass

class CtbAction(object):
    """
    Action class for cointip bot
    """

    type=None           # 'accept', 'decline', 'history', 'info', 'register', 'givetip', 'withdraw', 'redeem', 'rates'
    state=None          # 'completed', 'pending', 'failed', 'declined'
    txid=None           # cryptocoin transaction id, a 64-char string, if applicable

    u_from=None         # CtbUser instance
    u_to=None           # CtbUser instance, if applicable
    addr_to=None        # destination cryptocoin address of 'givetip' and 'withdraw' actions, if applicable

    coin=None           # coin for this action (for example, 'ltc')
    fiat=None           # fiat for this action (for example, 'usd'), if applicable
    coinval=None        # coin value of 'givetip' and 'withdraw' actions
    fiatval=None        # fiat value of the 'givetip' or 'withdraw' action
    keyword=None        # keyword that's used instead of coinval/fiatval

    subreddit=None      # subreddit that originated the action, if applicable

    msg=None            # Reddit object pointing to originating message/comment
    msg_id=None         #
    ctb=None            # CointipBot instance


    def __init__(self, atype=None, msg=None, msg_id=None, from_user=None, to_user=None, to_addr=None, coin=None, fiat=None, coin_val=None, fiat_val=None, keyword=None, subr=None, ctb=None):
        """
        Initialize CtbAction object with given parameters and run basic checks
        """
        lg.debug("> CtbAction::__init__(%s)", vars())

        self.type = atype

        self.coin = coin.lower() if coin else None
        self.fiat = fiat.lower() if fiat else None
        self.coinval = coin_val
        self.fiatval = fiat_val
        self.keyword = keyword.lower() if keyword else None

        self.msg = msg
        self.ctb = ctb

        self.msg_id = self.msg.id if self.msg else msg_id

        self.addr_to = to_addr
        self.u_to = ctb_user.CtbUser(name=to_user, ctb=ctb) if to_user else None
        self.u_from = ctb_user.CtbUser(name=msg.author.name, redditobj=msg.author, ctb=ctb) if (msg and hasattr(msg, 'author') and msg.author) else ctb_user.CtbUser(name=from_user, ctb=ctb)
        self.subreddit = subr

        # Do some checks
        if not self.type:
            raise Exception("CtbAction::__init__(type=?): type not set")
        if not self.ctb:
            raise Exception("CtbAction::__init__(type=%s): no reference to CointipBot", self.type)
        #if not self.msg:
        #    raise Exception("CtbAction::__init__(type=%s): no reference to Reddit message/comment", self.type)
        if self.type in ['givetip', 'withdraw']:
            if not (bool(self.u_to) ^ bool(self.addr_to)):
                raise Exception("CtbAction::__init__(atype=%s, from_user=%s): u_to xor addr_to must be set" % (self.type, self.u_from.name))
            if not (bool(self.coin) or bool(self.fiat) or bool(self.keyword)):
                raise Exception("CtbAction::__init__(atype=%s, from_user=%s): coin or fiat or keyword must be set" % (self.type, self.u_from.name))
            if not (bool(self.coinval) or bool(self.fiatval) or bool(self.keyword)):
                raise Exception("CtbAction::__init__(atype=%s, from_user=%s): coinval or fiatval or keyword must be set" % (self.type, self.u_from.name))
            if (not self.coinval or not float(self.coinval) > 0.0) and (not self.fiatval or not float(self.fiatval) > 0.0) and (not self.keyword):
                raise CtbActionExc("CtbAction::__init__(type=%s, from_user=%s, to_user=%s): no (coinval or fiatval or keyword) given" % (self.type, self.u_from, self.u_to))

        # Convert coinval and fiat to float, if necesary
        if self.coinval and type(self.coinval) == unicode and self.coinval.replace('.', '').isnumeric():
            self.coinval = float(self.coinval)
        if self.fiatval and type(self.fiatval) == unicode and self.fiatval.replace('.', '').isnumeric():
            self.fiatval = float(self.fiatval)

        lg.debug("CtbAction::__init__(): %s", self)

        # Determine coinval or fiatval, if keyword is given instead of numeric value
        if self.type in ['givetip', 'withdraw']:

            if self.keyword:
                if not self.ctb.conf.keywords[self.keyword].for_coin and not self.fiat:
                    # If fiat-only, set fiat to 'usd' if missing
                    self.fiat = 'usd'
                if not self.ctb.conf.keywords[self.keyword].for_coin and not self.fiatval:
                    # If fiat-only, set fiatval as coinval, and clear coinval
                    self.fiatval = self.coinval
                    self.coinval = None
                if not self.coin and not self.fiat:
                    # If both coin and fiat missing, set fiat to 'usd'
                    self.fiat = 'usd'

            if self.keyword and self.fiat and not self.coin and not self.ctb.conf.keywords[self.keyword].for_fiat:
                # If keyword is coin-only but only fiat is set, give up
                raise CtbActionExc("CtbAction::__init__(type=%s): keyword is coin-only, but only fiat is set")

            if self.keyword and self.fiat and not ( type(self.fiatval) in [float, int] and self.fiatval > 0.0 ):
                # Determine fiat value
                lg.debug("CtbAction::__init__(): determining fiat value given '%s'", self.keyword)
                val = self.ctb.conf.keywords[self.keyword].value
                if type(val) == float:
                    self.fiatval = val
                elif type(val) == str:
                    lg.debug("CtbAction::__init__(): evaluating '%s'", val)
                    self.fiatval = eval(val)
                    if not type(self.fiatval) == float:
                        raise CtbActionExc("CtbAction::__init__(atype=%s, from_user=%s): couldn't determine fiatval from keyword '%s' (not float)" % (self.type, self.u_from.name, self.keyword))
                else:
                    raise CtbActionExc("CtbAction::__init__(atype=%s, from_user=%s): couldn't determine fiatval from keyword '%s' (not float or str)" % (self.type, self.u_from.name, self.keyword))

            elif self.keyword and self.coin and not ( type(self.coinval) in [float, int] and self.coinval > 0.0 ):
                # Determine coin value
                lg.debug("CtbAction::__init__(): determining coin value given '%s'", self.keyword)
                val = self.ctb.conf.keywords[self.keyword].value
                if type(val) == float:
                    self.coinval = val
                elif type(val) == str:
                    lg.debug("CtbAction::__init__(): evaluating '%s'", val)
                    self.coinval = eval(val)
                    if not type(self.coinval) == float:
                        raise CtbActionExc("CtbAction::__init__(atype=%s, from_user=%s): couldn't determine coinval from keyword '%s' (not float)" % (self.type, self.u_from.name, self.keyword))
                else:
                    raise CtbActionExc("CtbAction::__init__(atype=%s, from_user=%s): couldn't determine coinval from keyword '%s' (not float or str)" % (self.type, self.u_from.name, self.keyword))

            # By this point we should have a proper coinval or fiatval
            if not type(self.coinval) in [float, int] and not type(self.fiatval) in [float, int]:
                raise CtbActionExc("CtbAction::__init__(atype=%s, from_user=%s): coinval or fiatval isn't determined" % (self.type, self.u_from.name))

        # Determine coin, if given only fiat, using exchange rates
        if self.type in ['givetip']:
            if self.fiat and not self.coin:
                lg.debug("CtbAction::__init__(atype=%s, from_user=%s): determining coin..." % (self.type, self.u_from.name))
                if not self.u_from.is_registered():
                    # Can't proceed, abort
                    raise CtbActionExc("CtbAction::__init__(): can't determine coin for un-registered user %s", self.u_from.name)
                # Choose a coin based on from_user's available balance (pick first one that can satisfy the amount)
                cc = self.ctb.conf.coins
                for c in sorted(self.ctb.coins):
                    lg.debug("CtbAction::__init__(atype=%s, from_user=%s): considering %s" % (self.type, self.u_from.name, c))
                    # First, check if we have a ticker value for this coin and fiat
                    if not self.ctb.coin_value(cc[c].unit, self.fiat) > 0.0:
                        continue
                    # Compare available and needed coin balances
                    coin_balance_avail = self.u_from.get_balance(coin=cc[c].unit, kind='givetip')
                    coin_balance_need = self.fiatval / self.ctb.coin_value(cc[c].unit, self.fiat)
                    if coin_balance_avail > coin_balance_need or abs(coin_balance_avail - coin_balance_need) < 0.000001:
                        # Found coin with enough balance
                        self.coin = cc[c].unit
                        break
            if not self.coin:
                # Couldn't deteremine coin, abort
                raise CtbActionExc("CtbAction::__init__(): can't determine coin for user %s" % self.u_from.name)

        # Calculate fiat or coin value with exchange rates
        if self.type in ['givetip', 'withdraw']:
            if not self.fiat:
                # Set fiat to 'usd' if not specified
                self.fiat = 'usd'
            if not self.fiatval:
                # Determine fiat value
                if self.ctb.coin_value(self.ctb.conf.coins[self.coin].unit, self.fiat) <= 0.0:
                    raise CtbActionExc("CtbAction::__init__(): coin_value returned 0")
                self.fiatval = self.coinval * self.ctb.coin_value(self.ctb.conf.coins[self.coin].unit, self.fiat)
            elif not self.coinval:
                # Determine coin value
                if self.ctb.coin_value(self.ctb.conf.coins[self.coin].unit, self.fiat) <= 0.0:
                    raise CtbActionExc("CtbAction::__init__(): coin_value returned 0")
                self.coinval = self.fiatval / self.ctb.coin_value(self.ctb.conf.coins[self.coin].unit, self.fiat)

        # Final check to make sure coin value is determined
        if self.type in ['givetip', 'withdraw']:
            if not self.coinval or not type(self.coinval) in [float, int]:
                raise CtbActionExc("CtbAction::__init__(): couldn't determine coin value, giving up. CtbAction: <%s>", self)

        lg.debug("< CtbAction::__init__(atype=%s, from_user=%s) DONE", self.type, self.u_from.name)

    def __str__(self):
        """""
        Return string representation of self
        """
        me = "<CtbAction: type=%s, msg.body=%s, from_user=%s, to_user=%s, to_addr=%s, coin=%s, fiat=%s, coin_val=%s, fiat_val=%s, subreddit=%s>"
        me = me % (self.type, self.msg.body if self.msg else '', self.u_from, self.u_to, self.addr_to, self.coin, self.fiat, self.coinval, self.fiatval, self.subreddit)
        return me

    def update(self, state=None):
        """
        Update action state in database
        """
        lg.debug("> CtbAction::update(%s)", state)

        if not state:
            raise Exception("CtbAction::update(): state is null")
        if not self.type or not self.msg_id:
            raise Exception("CtbAction::update(): type or msg_id missing")

        conn = self.ctb.db
        sql = "UPDATE t_action SET state=%s WHERE type=%s AND msg_id=%s"

        try:
            mysqlexec = conn.execute(sql, (state, self.type, self.msg_id))
            if mysqlexec.rowcount <= 0:
                raise Exception("query didn't affect any rows")
        except Exception as e:
            lg.error("CtbAction::update(%s): error executing query <%s>: %s", state, sql % (state, self.type, self.msg_id))
            raise

        lg.debug("< CtbAction::update() DONE")
        return True

    def save(self, state=None):
        """
        Save action to database
        """
        lg.debug("> CtbAction::save(%s)", state)

        # Make sure no negative values exist
        if self.coinval < 0.0:
            self.coinval = 0.0
        if self.fiatval < 0.0:
            self.fiatval = 0.0

        conn = self.ctb.db
        sql = "INSERT INTO t_action (type, state, created_utc, from_user, to_user, to_addr, coin_val, fiat_val, txid, coin, fiat, subreddit, msg_id, msg_link)"
        sql += " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        try:
            mysqlexec = conn.execute(sql,
                    (self.type,
                     state,
                     self.msg.created_utc,
                     self.u_from.name.lower(),
                     self.u_to.name.lower() if self.u_to else None,
                     self.addr_to,
                     self.coinval,
                     self.fiatval,
                     self.txid,
                     self.coin,
                     self.fiat,
                     self.subreddit,
                     self.msg.id,
                     self.msg.permalink if hasattr(self.msg, 'permalink') else None))
            if mysqlexec.rowcount <= 0:
                raise Exception("query didn't affect any rows")
        except Exception as e:
            lg.error("CtbAction::save(%s): error executing query <%s>: %s", state, sql % (
                self.type,
                state,
                self.msg.created_utc,
                self.u_from.name.lower(),
                self.u_to.name.lower() if self.u_to else None,
                self.addr_to,
                self.coinval,
                self.fiatval,
                self.txid,
                self.coin,
                self.fiat,
                self.subreddit,
                self.msg.id,
                self.msg.permalink if hasattr(self.msg, 'permalink') else None), e)
            raise

        lg.debug("< CtbAction::save() DONE")
        return True

    def do(self):
        """
        Call appropriate function depending on action type
        """
        lg.debug("> CtbAction::do()")

        if not self.ctb.conf.regex.actions[self.type].enabled:
	        msg = self.ctb.jenv.get_template('command-disabled.tpl').render(a=self, ctb=self.ctb)
	        lg.info("CtbAction::do(): action %s is disabled", self.type)
	        ctb_misc.praw_call(self.msg.reply, msg)
	        return False

        if self.type == 'accept':
            return self.accept()

        if self.type == 'decline':
            return self.decline()

        if self.type == 'givetip':
            result = self.givetip()
            ctb_stats.update_user_stats(ctb=self.ctb, username=self.u_from.name)
            if self.u_to:
                ctb_stats.update_user_stats(ctb=self.ctb, username=self.u_to.name)
            return result

        if self.type == 'history':
            return self.history()

        if self.type == 'info':
            return self.info()

        if self.type == 'register':
            return self.register()

        if self.type == 'withdraw':
            return self.givetip()

        if self.type == 'redeem':
            return self.redeem()

        if self.type == 'rates':
            return self.rates()

        lg.debug("< CtbAction::do() DONE")
        return None

    def history(self):
        """
        Provide user with transaction history
        """
        lg.debug("> CtbAction::history()")

        # Generate history array
        history = []
        sql_history = self.ctb.conf.db.sql.userhistory.sql
        limit = int(self.ctb.conf.db.sql.userhistory.limit)

        mysqlexec = self.ctb.db.execute(sql_history, (self.u_from.name.lower(), self.u_from.name.lower(), limit))
        for m in mysqlexec:
            history_entry = []
            for k in mysqlexec.keys():
                history_entry.append(ctb_stats.format_value(m, k, self.u_from.name.lower(), self.ctb, compact=True))
            history.append(history_entry)

        # Send message to user
        msg = self.ctb.jenv.get_template('history.tpl').render(history=history, keys=mysqlexec.keys(), limit=limit, a=self, ctb=self.ctb)
        lg.debug("CtbAction::history(): %s", msg)
        ctb_misc.praw_call(self.msg.reply, msg)

        # Save as completed
        self.save('completed')

        lg.debug("< CtbAction::history() DONE")
        return True

    def accept(self):
        """
        Accept pending tip
        """
        lg.debug("> CtbAction::accept()")

        # Register as new user if necessary
        if not self.u_from.is_registered():
            if not self.u_from.register():
                lg.warning("CtbAction::accept(): self.u_from.register() failed")
                self.save('failed')
                return False

        # Get pending actions
        actions = get_actions(atype='givetip', to_user=self.u_from.name, state='pending', ctb=self.ctb)
        if actions:

            # Accept each action
            for a in actions:
                a.givetip(is_pending=True)
                # Update u_from (tip action) stats
                ctb_stats.update_user_stats(ctb=a.ctb, username=a.u_from.name)
            # Update u_from (accept action) stats
            ctb_stats.update_user_stats(ctb=a.ctb, username=self.u_from.name)
            # Save this action
            self.save('completed')

        else:

            # No pending actions found, reply with error message
            msg = self.ctb.jenv.get_template('no-pending-tips.tpl').render(user_from=self.u_from.name, a=self, ctb=self.ctb)
            lg.debug("CtbAction::accept(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            # Save this action
            self.save('failed')

        lg.debug("< CtbAction::accept() DONE")
        return True

    def decline(self):
        """
        Decline pending tips
        """
        lg.debug("> CtbAction::decline()")

        actions = get_actions(atype='givetip', to_user=self.u_from.name, state='pending', ctb=self.ctb)
        if actions:
            for a in actions:
                # Move coins back into a.u_from account
                lg.info("CtbAction::decline(): moving %.9f %s from %s to %s", a.coinval, a.coin.upper(), self.ctb.conf.reddit.auth.user, a.u_from.name)
                if not self.ctb.coins[a.coin].sendtouser(_userfrom=self.ctb.conf.reddit.auth.user, _userto=a.u_from.name, _amount=a.coinval):
                    raise Exception("CtbAction::decline(): failed to sendtouser()")

                # Update transaction as declined
                a.update('declined')

                # Update u_from (tip action) stats
                ctb_stats.update_user_stats(ctb=a.ctb, username=a.u_from.name)

                # Respond to tip comment
                msg = self.ctb.jenv.get_template('confirmation.tpl').render(title='Declined', a=a, ctb=a.ctb, source_link=a.msg.permalink if a.msg else None)
                lg.debug("CtbAction::decline(): " + msg)
                if self.ctb.conf.reddit.messages.declined:
                    if not ctb_misc.praw_call(a.msg.reply, msg):
                        a.u_from.tell(subj="+tip declined", msg=msg)
                else:
                    a.u_from.tell(subj="+tip declined", msg=msg)

            # Update u_from (decline action) stats
            ctb_stats.update_user_stats(ctb=a.ctb, username=self.u_from.name)

            # Notify self.u_from
            msg = self.ctb.jenv.get_template('pending-tips-declined.tpl').render(user_from=self.u_from.name, ctb=self.ctb)
            lg.debug("CtbAction::decline(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)

            # Save action to database
            self.save('completed')

        else:

            msg = self.ctb.jenv.get_template('no-pending-tips.tpl').render(user_from=self.u_from.name, ctb=self.ctb)
            lg.debug("CtbAction::decline(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)

            # Save action to database
            self.save('failed')

        lg.debug("< CtbAction::decline() DONE")
        return True

    def expire(self):
        """
        Expire a pending tip
        """
        lg.debug("> CtbAction::expire()")

        # Move coins back into self.u_from account
        lg.info("CtbAction::expire(): moving %.9f %s from %s to %s", self.coinval, self.coin.upper(), self.ctb.conf.reddit.auth.user, self.u_from.name)
        if not self.ctb.coins[self.coin].sendtouser(_userfrom=self.ctb.conf.reddit.auth.user, _userto=self.u_from.name, _amount=self.coinval):
            raise Exception("CtbAction::expire(): sendtouser() failed")

        # Update transaction as expired
        self.update('expired')

        # Update user stats
        ctb_stats.update_user_stats(ctb=self.ctb, username=self.u_from.name)
        ctb_stats.update_user_stats(ctb=self.ctb, username=self.u_to.name)

        # Respond to tip comment
        msg = self.ctb.jenv.get_template('confirmation.tpl').render(title='Expired', a=self, ctb=self.ctb, source_link=self.msg.permalink if self.msg else None)
        lg.debug("CtbAction::expire(): " + msg)
        if self.ctb.conf.reddit.messages.expired:
            if not ctb_misc.praw_call(self.msg.reply, msg):
                self.u_from.tell(subj="+tip expired", msg=msg)
        else:
            self.u_from.tell(subj="+tip expired", msg=msg)

        lg.debug("< CtbAction::expire() DONE")
        return True

    def validate(self, is_pending=False):
        """
        Validate an action
        """
        lg.debug("> CtbAction::validate()")

        if self.type in ['givetip', 'withdraw']:
            # Check if u_from has registered
            if not self.u_from.is_registered():
                msg = self.ctb.jenv.get_template('not-registered.tpl').render(a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): %s", msg)
                self.u_from.tell(subj="+tip failed", msg=msg)
                self.save('failed') if not is_pending else self.update('failed')
                return False

            if self.u_to and not self.u_to.is_on_reddit():
                msg = self.ctb.jenv.get_template('not-on-reddit.tpl').render(a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): %s", msg)
                self.u_from.tell(subj="+tip failed", msg=msg)
                self.save('failed') if not is_pending else self.update('failed')
                return False

            # Verify that coin type is set
            if not self.coin:
                msg = self.ctb.jenv.get_template('no-coin-balances.tpl').render(a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): %s", msg)
                self.u_from.tell(subj="+tip failed", msg=msg)
                self.save('failed') if not is_pending else self.update('failed')
                return False

            # Verify that u_from has coin address
            if not self.u_from.get_addr(coin=self.coin):
                lg.error("CtbAction::validate(): user %s doesn't have %s address", self.u_from.name, self.coin.upper())
                self.save('failed') if not is_pending else self.update('failed')
                raise Exception

            # Verify minimum transaction size
            txkind = 'givetip' if self.u_to else 'withdraw'
            if self.coinval < self.ctb.conf.coins[self.coin].txmin[txkind]:
                msg = self.ctb.jenv.get_template('tip-below-minimum.tpl').render(min_value=self.ctb.conf.coins[self.coin].txmin[txkind], a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): " + msg)
                self.u_from.tell(subj="+tip failed", msg=msg)
                self.save('failed') if not is_pending else self.update('failed')
                return False

            # Verify balance (unless it's a pending transaction being processed, in which case coins have been already moved to pending acct)
            if self.u_to and not is_pending:
                # Tip to user (requires less confirmations)
                balance_avail = self.u_from.get_balance(coin=self.coin, kind='givetip')
                if not ( balance_avail > self.coinval or abs(balance_avail - self.coinval) < 0.000001 ):
                    msg = self.ctb.jenv.get_template('tip-low-balance.tpl').render(balance=balance_avail, action_name='tip', a=self, ctb=self.ctb)
                    lg.debug("CtbAction::validate(): " + msg)
                    self.u_from.tell(subj="+tip failed", msg=msg)
                    self.save('failed') if not is_pending else self.update('failed')
                    return False
            elif self.addr_to:
                # Tip/withdrawal to address (requires more confirmations)
                balance_avail = self.u_from.get_balance(coin=self.coin, kind='withdraw')
                balance_need = self.coinval
                # Add mandatory network transaction fee
                balance_need += self.ctb.conf.coins[self.coin].txfee
                if not ( balance_avail > balance_need or abs(balance_avail - balance_need) < 0.000001 ):
                    msg = self.ctb.jenv.get_template('tip-low-balance.tpl').render(balance=balance_avail, action_name='withdraw', a=self, ctb=self.ctb)
                    lg.debug("CtbAction::validate(): " + msg)
                    self.u_from.tell(subj="+tip failed", msg=msg)
                    self.save('failed') if not is_pending else self.update('failed')
                    return False

            # Check if u_to has any pending coin tips from u_from
            if self.u_to and not is_pending:
                if check_action(atype='givetip', state='pending', to_user=self.u_to.name, from_user=self.u_from.name, coin=self.coin, ctb=self.ctb):
                    # Send notice to u_from
                    msg = self.ctb.jenv.get_template('tip-already-pending.tpl').render(a=self, ctb=self.ctb)
                    lg.debug("CtbAction::validate(): " + msg)
                    self.u_from.tell(subj="+tip failed", msg=msg)
                    self.save('failed') if not is_pending else self.update('failed')
                    return False

            # Check if u_to has registered, if applicable
            if self.u_to and not self.u_to.is_registered():
                # u_to not registered:
                # - move tip into pending account
                # - save action as 'pending'
                # - notify u_to to accept tip

                # Move coins into pending account
                minconf = self.ctb.coins[self.coin].conf.minconf.givetip
                lg.info("CtbAction::validate(): moving %.9f %s from %s to %s (minconf=%s)...", self.coinval, self.coin.upper(), self.u_from.name, self.ctb.conf.reddit.auth.user, minconf)
                if not self.ctb.coins[self.coin].sendtouser(_userfrom=self.u_from.name, _userto=self.ctb.conf.reddit.auth.user, _amount=self.coinval, _minconf=minconf):
                    raise Exception("CtbAction::validate(): sendtouser() failed")

                # Save action as pending
                self.save('pending')

                # Respond to tip comment
                msg = self.ctb.jenv.get_template('confirmation.tpl').render(title='Verified', a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): " + msg)
                if self.ctb.conf.reddit.messages.verified:
                    if not ctb_misc.praw_call(self.msg.reply, msg):
                        self.u_from.tell(subj="+tip pending +accept", msg=msg)
                else:
                    self.u_from.tell(subj="+tip pending +accept", msg=msg)

                # Send notice to u_to
                msg = self.ctb.jenv.get_template('tip-incoming.tpl').render(a=self, ctb=self.ctb)
                lg.debug("CtbAction::validate(): %s", msg)
                self.u_to.tell(subj="+tip pending", msg=msg)

                # Action saved as 'pending', return false to avoid processing it further
                return False

            # Validate addr_to, if applicable
            if self.addr_to:
                if not self.ctb.coins[self.coin].validateaddr(_addr=self.addr_to):
                    msg = self.ctb.jenv.get_template('address-invalid.tpl').render(a=self, ctb=self.ctb)
                    lg.debug("CtbAction::validate(): " + msg)
                    self.u_from.tell(subj="+tip failed", msg=msg)
                    self.save('failed') if not is_pending else self.update('failed')
                    return False

        # Action is valid
        lg.debug("< CtbAction::validate() DONE")
        return True

    def givetip(self, is_pending=False):
        """
        Initiate tip
        """
        lg.debug("> CtbAction::givetip()")

        # Check if action has been processed
        if check_action(atype=self.type, msg_id=self.msg_id, ctb=self.ctb, is_pending=is_pending):
            # Found action in database, returning
            lg.warning("CtbAction::givetipt(): duplicate action %s (msg.id %s), ignoring", self.type, self.msg.id)
            return False

        # Validate action
        if not self.validate(is_pending=is_pending):
            # Couldn't validate action, returning
            return False

        if self.u_to:
            # Process tip to user

            res = False
            if is_pending:
                # This is accept() of pending transaction, so move coins from pending account to receiver
                lg.info("CtbAction::givetip(): moving %.9f %s from %s to %s...", self.coinval, self.coin.upper(), self.ctb.conf.reddit.auth.user, self.u_to.name)
                res = self.ctb.coins[self.coin].sendtouser(_userfrom=self.ctb.conf.reddit.auth.user, _userto=self.u_to.name, _amount=self.coinval)
            else:
                # This is not accept() of pending transaction, so move coins from tipper to receiver
                lg.info("CtbAction::givetip(): moving %.9f %s from %s to %s...", self.coinval, self.coin.upper(), self.u_from.name, self.u_to.name)
                res = self.ctb.coins[self.coin].sendtouser(_userfrom=self.u_from.name, _userto=self.u_to.name, _amount=self.coinval)

            if not res:
                # Tx failed
                # Save/update action as failed
                self.save('failed') if not is_pending else self.update('failed')

                # Send notice to u_from
                msg = self.ctb.jenv.get_template('tip-went-wrong.tpl').render(a=self, ctb=self.ctb)
                self.u_from.tell(subj="+tip failed", msg=msg)

                raise Exception("CtbAction::givetip(): sendtouser() failed")

            # Transaction succeeded
            self.save('completed') if not is_pending else self.update('completed')

            # Send confirmation to u_to
            msg = self.ctb.jenv.get_template('tip-received.tpl').render(a=self, ctb=self.ctb)
            lg.debug("CtbAction::givetip(): " + msg)
            self.u_to.tell(subj="+tip received", msg=msg)

            # This is not accept() of pending transaction, so post verification comment
            if not is_pending:
                msg = self.ctb.jenv.get_template('confirmation.tpl').render(title='Verified', a=self, ctb=self.ctb)
                lg.debug("CtbAction::givetip(): " + msg)
                if self.ctb.conf.reddit.messages.verified:
                    if not ctb_misc.praw_call(self.msg.reply, msg):
                        self.u_from.tell(subj="+tip succeeded", msg=msg)
                else:
                    self.u_from.tell(subj="+tip succeeded", msg=msg)

            lg.debug("< CtbAction::givetip() DONE")
            return True

        elif self.addr_to:
            # Process tip to address
            try:
                lg.info("CtbAction::givetip(): sending %.9f %s to %s...", self.coinval, self.coin, self.addr_to)
                self.txid = self.ctb.coins[self.coin].sendtoaddr(_userfrom=self.u_from.name, _addrto=self.addr_to, _amount=self.coinval)

            except Exception as e:

                # Transaction failed
                self.save('failed') if not is_pending else self.update('failed')
                lg.error("CtbAction::givetip(): sendtoaddr() failed")

                # Send notice to u_from
                msg = self.ctb.jenv.get_template('tip-went-wrong.tpl').render(a=self, ctb=self.ctb)
                self.u_from.tell(subj="+tip failed", msg=msg)

                raise

            # Transaction succeeded
            self.save('completed') if not is_pending else self.update('completed')

            # Post verification comment
            msg = self.ctb.jenv.get_template('confirmation.tpl').render(title='Verified', a=self, ctb=self.ctb)
            lg.debug("CtbAction::givetip(): " + msg)
            if self.ctb.conf.reddit.messages.verified:
                if not ctb_misc.praw_call(self.msg.reply, msg):
                    self.u_from.tell(subj="+tip succeeded", msg=msg)
            else:
                self.u_from.tell(subj="+tip succeeded", msg=msg)

            lg.debug("< CtbAction::givetip() DONE")
            return True

        lg.debug("< CtbAction::givetip() DONE")
        return None

    def info(self):
        """
        Send user info about account
        """
        lg.debug("> CtbAction::info()")

        # Check if user exists
        if not self.u_from.is_registered():
            msg = self.ctb.jenv.get_template('not-registered.tpl').render(a=self, ctb=self.ctb)
            self.u_from.tell(subj="+info failed", msg=msg)
            return False

        # Info array to pass to template
        info = []

        # Get coin balances
        for c in sorted(self.ctb.coins):
            coininfo = ctb_misc.DotDict({})
            coininfo.coin = c
            try:
                # Get tip balance
                coininfo.balance = self.ctb.coins[c].getbalance(_user=self.u_from.name, _minconf=self.ctb.conf.coins[c].minconf.givetip)
                info.append(coininfo)
            except Exception as e:
                lg.error("CtbAction::info(%s): error retrieving %s coininfo: %s", self.u_from.name, c, e)
                raise

        # Get fiat balances
        fiat_total = 0.0
        for i in info:
            i.fiat_symbol = self.ctb.conf.fiat.usd.symbol
            if self.ctb.coin_value(self.ctb.conf.coins[i.coin].unit, 'usd') > 0.0:
                i.fiat_balance = i.balance * self.ctb.coin_value(self.ctb.conf.coins[i.coin].unit, 'usd')
                fiat_total += i.fiat_balance

        # Get coin addresses from MySQL
        for i in info:
            sql = "SELECT address FROM t_addrs WHERE username = '%s' AND coin = '%s'" % (self.u_from.name.lower(), i.coin)
            mysqlrow = self.ctb.db.execute(sql).fetchone()
            if not mysqlrow:
                raise Exception("CtbAction::info(%s): no result from <%s>" % (self.u_from.name, sql))
            i.address = mysqlrow['address']

        # Format and send message
        msg = self.ctb.jenv.get_template('info.tpl').render(info=info, fiat_symbol=self.ctb.conf.fiat.usd.symbol, fiat_total=fiat_total, a=self, ctb=self.ctb)
        ctb_misc.praw_call(self.msg.reply, msg)

        # Save action to database
        self.save('completed')

        lg.debug("< CtbAction::info() DONE")
        return True

    def register(self):
        """
        Register a new user
        """
        lg.debug("> CtbAction::register()")

        # If user exists, do nothing
        if self.u_from.is_registered():
            lg.debug("CtbAction::register(%s): user already exists", self.u_from.name)
            msg = self.ctb.jenv.get_template('already-registered.tpl').render(a=self, ctb=self.ctb)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        result = self.u_from.register()

        # Save action to database
        if result:
            self.save('completed')
        else:
            self.save('failed')

        # Send welcome message to user
        if result:
            msg = self.ctb.jenv.get_template('welcome.tpl').render(a=self, ctb=self.ctb)
            ctb_misc.praw_call(self.msg.reply, msg)

        lg.debug("< CtbAction::register() DONE")
        return result

    def redeem(self):
        """
        Redeem karma for coins
        """
        lg.debug("> CtbAction::redeem()")

        # Check if user is registered
        if not self.u_from.is_registered():
            msg = self.ctb.jenv.get_template('not-registered.tpl').render(a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        # Check if this user has redeemed karma in the past
        has_redeemed = False
        if self.ctb.conf.reddit.redeem.multicoin:
            # Check if self.coin has been redeemed
            has_redeemed = check_action(atype='redeem', from_user=self.u_from.name, state='completed', coin=self.coin, ctb=self.ctb)
        else:
            # Check if any coin has been redeemed
            has_redeemed = check_action(atype='redeem', from_user=self.u_from.name, state='completed', ctb=self.ctb)
        if has_redeemed:
            msg = self.ctb.jenv.get_template('redeem-already-done.tpl').render(coin=self.ctb.conf.coins[self.coin].name if self.ctb.conf.reddit.redeem.multicoin else None, a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        # Check if this user has > minimum karma
        user_karma = int(self.u_from.prawobj.link_karma) + int(self.u_from.prawobj.comment_karma)
        if user_karma < self.ctb.conf.reddit.redeem.min_karma:
            msg = self.ctb.jenv.get_template('redeem-low-karma.tpl').render(user_karma=user_karma, a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        # Determine amount
        self.fiat = self.ctb.conf.reddit.redeem.unit
        self.coinval, self.fiatval = self.u_from.get_redeem_amount(coin=self.coin, fiat=self.fiat)

        # Check if coinval and fiatval are valid
        if not self.coinval or not self.fiatval or not self.coinval > 0.0 or not self.fiatval > 0.0:
            msg = self.ctb.jenv.get_template('redeem-cant-compute.tpl').render(a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        # Check if redeem account has enough balance
        funds = self.ctb.coins[self.coin].getbalance(_user=self.ctb.conf.reddit.redeem.account, _minconf=1)
        if self.coinval > funds or abs(self.coinval - funds) < 0.000001:
            # Reply with 'not enough funds' message
            msg = self.ctb.jenv.get_template('redeem-low-funds.tpl').render(a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('failed')
            return False

        # Transfer coins
        if self.ctb.coins[self.coin].sendtouser(_userfrom=self.ctb.conf.reddit.redeem.account, _userto=self.u_from.name, _amount=self.coinval, _minconf=1):
            # Success, send confirmation
            msg = self.ctb.jenv.get_template('redeem-confirmation.tpl').render(a=self, ctb=self.ctb)
            lg.debug("CtbAction::redeem(): %s", msg)
            ctb_misc.praw_call(self.msg.reply, msg)
            self.save('completed')
            return True
        else:
            raise Exception("CtbAction::redeem(): sendtouser failed")

    def rates(self, fiat='usd'):
        """
        Send info on coin exchange rates
        """
        lg.debug("> CtbAction::rates()")

        coins = []
        exchanges = []
        rates = {}

        # Get exchange rates
        for coin in self.ctb.coins:
            coins.append(coin)
            rates[coin] = {'average': {}}
            rates[coin]['average']['btc'] = self.ctb.runtime['ev'][coin]['btc']
            rates[coin]['average'][fiat] = self.ctb.runtime['ev'][coin]['btc'] * self.ctb.runtime['ev']['btc'][fiat]
            for exchange in self.ctb.exchanges:
                try:
                    rates[coin][exchange] = {}
                    if self.ctb.exchanges[exchange].supports_pair(_name1=coin, _name2='btc'):
                        rates[coin][exchange]['btc'] = self.ctb.exchanges[exchange].get_ticker_value(_name1=coin, _name2='btc')
                        if coin == 'btc' and self.ctb.exchanges[exchange].supports_pair(_name1='btc', _name2=fiat):
                            # Use exchange value to calculate btc's fiat value
                            rates[coin][exchange][fiat] = rates[coin][exchange]['btc'] * self.ctb.exchanges[exchange].get_ticker_value(_name1='btc', _name2=fiat)
                        else:
                            # Use average value to calculate coin's fiat value
                            rates[coin][exchange][fiat] = rates[coin][exchange]['btc'] * self.ctb.runtime['ev']['btc'][fiat]
                    else:
                        rates[coin][exchange]['btc'] = None
                        rates[coin][exchange][fiat] = None
                except TypeError as e:
                    msg = self.ctb.jenv.get_template('rates-error.tpl').render(exchange=exchange, a=self, ctb=self.ctb)
                    lg.debug("CtbAction::rates(): %s", msg)
                    ctb_misc.praw_call(self.msg.reply, msg)
                    self.save('failed')
                    return False

        for exchange in self.ctb.exchanges:
            exchanges.append(exchange)

        lg.debug("CtbAction::rates(): %s", rates)

        # Send message
        msg = self.ctb.jenv.get_template('rates.tpl').render(coins=sorted(coins), exchanges=sorted(exchanges), rates=rates, fiat=fiat, a=self, ctb=self.ctb)
        lg.debug("CtbAction::rates(): %s", msg)
        ctb_misc.praw_call(self.msg.reply, msg)
        self.save('completed')
        return True

def init_regex(ctb):
    """
    Initialize regular expressions used to match messages and comments
    """
    lg.debug("> init_regex()")

    cc = ctb.conf.coins
    fiat = ctb.conf.fiat
    actions = ctb.conf.regex.actions
    ctb.runtime['regex'] = []

    for a in vars(actions):
        if actions[a].simple:

            # Add simple message actions (info, register, accept, decline, history, rates)

            entry = ctb_misc.DotDict(
                {'regex':       actions[a].regex,
                 'action':      a,
                 'rg_amount':   0,
                 'rg_keyword':  0,
                 'rg_address':  0,
                 'rg_to_user':  0,
                 'coin':        None,
                 'fiat':        None,
                 'keyword':     None
                })
            lg.debug("init_regex(): ADDED %s: %s", entry.action, entry.regex)
            ctb.runtime['regex'].append(entry)

        else:

            # Add non-simple actions (givetip, redeem, withdraw)

            for r in sorted(vars(actions[a].regex)):
                lg.debug("init_regex(): processing regex %s", actions[a].regex[r].value)
                rval1 = actions[a].regex[r].value
                rval1 = rval1.replace('{REGEX_TIP_INIT}', ctb.conf.regex.values.tip_init.regex)
                rval1 = rval1.replace('{REGEX_USER}', ctb.conf.regex.values.username.regex)
                rval1 = rval1.replace('{REGEX_AMOUNT}', ctb.conf.regex.values.amount.regex)
                rval1 = rval1.replace('{REGEX_KEYWORD}', ctb.conf.regex.values.keywords.regex)

                if actions[a].regex[r].rg_coin > 0:

                    for c in sorted(vars(cc)):

                        if not cc[c].enabled:
                            continue
                        # lg.debug("init_regex(): processing coin %s", c)

                        rval2 = rval1.replace('{REGEX_COIN}', cc[c].regex.units)
                        rval2 = rval2.replace('{REGEX_ADDRESS}', cc[c].regex.address)

                        if actions[a].regex[r].rg_fiat > 0:

                            for f in sorted(vars(fiat)):

                                if not fiat[f].enabled:
                                    continue
                                # lg.debug("init_regex(): processing fiat %s", f)

                                rval3 = rval2.replace('{REGEX_FIAT}', fiat[f].regex.units)
                                entry = ctb_misc.DotDict(
                                    {'regex':           rval3,
                                     'action':          a,
                                     'rg_amount':       actions[a].regex[r].rg_amount,
                                     'rg_keyword':      actions[a].regex[r].rg_keyword,
                                     'rg_address':      actions[a].regex[r].rg_address,
                                     'rg_to_user':      actions[a].regex[r].rg_to_user,
                                     'coin':            cc[c].unit,
                                     'fiat':            fiat[f].unit
                                    })
                                lg.debug("init_regex(): ADDED %s: %s", entry.action, entry.regex)
                                ctb.runtime['regex'].append(entry)

                        else:

                            entry = ctb_misc.DotDict(
                                {'regex':           rval2,
                                 'action':          a,
                                 'rg_amount':       actions[a].regex[r].rg_amount,
                                 'rg_keyword':      actions[a].regex[r].rg_keyword,
                                 'rg_address':      actions[a].regex[r].rg_address,
                                 'rg_to_user':      actions[a].regex[r].rg_to_user,
                                 'coin':            cc[c].unit,
                                 'fiat':            None
                                })
                            lg.debug("init_regex(): ADDED %s: %s", entry.action, entry.regex)
                            ctb.runtime['regex'].append(entry)

                elif actions[a].regex[r].rg_fiat > 0:

                    for f in sorted(vars(fiat)):

                        if not fiat[f].enabled:
                            continue
                        # lg.debug("init_regex(): processing fiat %s", f)

                        rval2 = rval1.replace('{REGEX_FIAT}', fiat[f].regex.units)
                        entry = ctb_misc.DotDict(
                            {'regex':           rval2,
                             'action':          a,
                             'rg_amount':       actions[a].regex[r].rg_amount,
                             'rg_keyword':      actions[a].regex[r].rg_keyword,
                             'rg_address':      actions[a].regex[r].rg_address,
                             'rg_to_user':      actions[a].regex[r].rg_to_user,
                             'coin':            None,
                             'fiat':            fiat[f].unit
                            })
                        lg.debug("init_regex(): ADDED %s: %s", entry.action, entry.regex)
                        ctb.runtime['regex'].append(entry)

                elif actions[a].regex[r].rg_keyword > 0:

                    entry = ctb_misc.DotDict(
                        {'regex':           rval1,
                         'action':          a,
                         'rg_amount':       actions[a].regex[r].rg_amount,
                         'rg_keyword':      actions[a].regex[r].rg_keyword,
                         'rg_address':      actions[a].regex[r].rg_address,
                         'rg_to_user':      actions[a].regex[r].rg_to_user,
                         'coin':            None,
                         'fiat':            None
                        })
                    lg.debug("init_regex(): ADDED %s: %s", entry.action, entry.regex)
                    ctb.runtime['regex'].append(entry)

    lg.info("< init_regex() DONE (%s expressions)", len(ctb.runtime['regex']))
    return None

def eval_message(msg, ctb):
    """
    Evaluate message body and return a CtbAction
    object if successful
    """
    lg.debug("> eval_message()")

    body = msg.body
    for r in ctb.runtime['regex']:

        # Attempt a match
        rg = re.compile(r.regex, re.IGNORECASE|re.DOTALL)
        #lg.debug("matching '%s' with '%s'", msg.body, r.regex)
        m = rg.search(body)

        if m:
            # Match found
            lg.debug("eval_message(): match found")

            # Extract matched fields into variables
            u_from = msg.author
            u_to = m.group(r.rg_to_user)[1:] if r.rg_to_user > 0 else None
            to_addr = m.group(r.rg_address) if r.rg_address > 0 else None
            amount = m.group(r.rg_amount) if r.rg_amount > 0 else None
            keyword = m.group(r.rg_keyword) if r.rg_keyword > 0 else None

            # Ignore 'givetip' without u_to and without to_addr
            if r.action == 'givetip' and not u_to and not to_addr:
                lg.warning("eval_message(): givetip: no to_user and no to_addr specified, ignoring")
                return None

            # Return CtbAction instance with given variables
            lg.debug("eval_message(): creating action %s: from_user=%s, to_addr=%s, amount=%s, coin=%s, fiat=%s" % (r.action, u_from, to_addr, amount, r.coin, r.fiat))
            try:
                action = CtbAction(
                    atype=r.action,
                    msg=msg,
                    from_user=u_from,
                    to_user=u_to,
                    to_addr=to_addr,
                    coin=r.coin,
                    coin_val=amount if not r.fiat else None,
                    fiat=r.fiat,
                    fiat_val=amount if r.fiat else None,
                    keyword=keyword,
                    ctb=ctb)
                return action
            except CtbActionExc as e:
                lg.warning("eval_message(): " + str(e))
                return None

    # No match found
    lg.debug("eval_message(): no match found")
    return None

def eval_comment(comment, ctb):
    """
    Evaluate comment body and return a CtbAction object if successful
    """
    lg.debug("> eval_comment()")

    body = comment.body
    for r in ctb.runtime['regex']:

        # Skip non-public actions
        if not ctb.conf.regex.actions[r.action].public:
            continue

        # Attempt a match
        rg = re.compile(r.regex, re.IGNORECASE|re.DOTALL)
        #lg.debug("eval_comment(): matching '%s' with <%s>", comment.body, r.regex)
        m = rg.search(body)

        if m:
            # Match found
            lg.debug("eval_comment(): match found")

            # Extract matched fields into variables
            u_to = m.group(r.rg_to_user)[1:] if r.rg_to_user > 0 else None
            to_addr = m.group(r.rg_address) if r.rg_address > 0 else None
            amount = m.group(r.rg_amount) if r.rg_amount > 0 else None
            keyword = m.group(r.rg_keyword) if r.rg_keyword > 0 else None

            # If no destination mentioned, find parent submission's author
            if not u_to and not to_addr:
                # set u_to to author of parent comment
                u_to = ctb_misc.reddit_get_parent_author(comment, ctb.reddit, ctb)
                if not u_to:
                    # couldn't determine u_to, giving up
                    lg.warning("eval_comment(): couldn't determine u_to, giving up")
                    return None

            # Check if from_user == to_user
            if u_to and comment.author.name.lower() == u_to.lower():
                lg.warning("eval_comment(): comment.author.name == u_to, ignoring comment", comment.author.name)
                return None

            # Return CtbAction instance with given variables
            lg.debug("eval_comment(): creating action %s: to_user=%s, to_addr=%s, amount=%s, coin=%s, fiat=%s" % (r.action, u_to, to_addr, amount, r.coin, r.fiat))
            try:
                action = CtbAction(
                    atype=r.action,
                    msg=comment,
                    to_user=u_to,
                    to_addr=to_addr,
                    coin=r.coin,
                    coin_val=amount if not r.fiat else None,
                    fiat=r.fiat,
                    fiat_val=amount if r.fiat else None,
                    keyword=keyword,
                    subr=comment.subreddit,
                    ctb=ctb)
                return action
            except CtbActionExc as e:
                lg.warning("eval_comment(): " + str(e))
                return None

    # No match found
    lg.debug("< eval_comment() DONE (no match)")
    return None

def check_action(atype=None, state=None, coin=None, msg_id=None, created_utc=None, from_user=None, to_user=None, subr=None, ctb=None, is_pending=False):
    """
    Return True if action with given attributes exists in database
    """
    lg.debug("> check_action(%s)", atype)

    # Build SQL query
    sql = "SELECT * FROM t_action"
    sql_terms = []
    if atype or state or coin or msg_id or created_utc or from_user or to_user or subr or is_pending:
        sql += " WHERE "
        if atype:
            sql_terms.append("type = '%s'" % atype)
        if state:
            sql_terms.append("state = '%s'" % state)
        if coin:
            sql_terms.append("coin = '%s'" % coin)
        if msg_id:
            sql_terms.append("msg_id = '%s'" % msg_id)
        if created_utc:
            sql_terms.append("created_utc = %s" % created_utc)
        if from_user:
            sql_terms.append("from_user = '%s'" % from_user.lower())
        if to_user:
            sql_terms.append("to_user = '%s'" % to_user.lower())
        if subr:
            sql_terms.append("subreddit = '%s'" % subr)
        if is_pending:
            sql_terms.append("state <> 'pending'")
        sql += ' AND '.join(sql_terms)

    try:
        lg.debug("check_action(): <%s>", sql)
        mysqlexec = ctb.db.execute(sql)
        if mysqlexec.rowcount <= 0:
            lg.debug("< check_action() DONE (no)")
            return False
        else:
            lg.debug("< check_action() DONE (yes)")
            return True
    except Exception as e:
        lg.error("check_action(): error executing <%s>: %s", sql, e)
        raise

    lg.warning("< check_action() DONE (should not get here)")
    return None

def get_actions(atype=None, state=None, coin=None, msg_id=None, created_utc=None, from_user=None, to_user=None, subr=None, ctb=None):
    """
    Return an array of CtbAction objects from database with given attributes
    """
    lg.debug("> get_actions(%s)", atype)

    # Build SQL query
    sql = "SELECT * FROM t_action"
    sql_terms = []
    if atype or state or coin or msg_id or created_utc or from_user or to_user or subr:
        sql += " WHERE "
        if atype:
            sql_terms.append("type = '%s'" % atype)
        if state:
            sql_terms.append("state = '%s'" % state)
        if coin:
            sql_terms.append("coin = '%s'" % coin)
        if msg_id:
            sql_terms.append("msg_id = '%s'" % msg_id)
        if created_utc:
            sql_terms.append("created_utc %s" % created_utc)
        if from_user:
            sql_terms.append("from_user = '%s'" % from_user.lower())
        if to_user:
            sql_terms.append("to_user = '%s'" % to_user.lower())
        if subr:
            sql_terms.append("subreddit = '%s'" % subr)
        sql += ' AND '.join(sql_terms)

    while True:
        try:
            r = []
            lg.debug("get_actions(): <%s>", sql)
            mysqlexec = ctb.db.execute(sql)

            if mysqlexec.rowcount <= 0:
                lg.debug("< get_actions() DONE (no)")
                return r

            for m in mysqlexec:
                lg.debug("get_actions(): found %s / %s", m['msg_link'], m['msg_id'])

                # Get PRAW message/comment pointer (msg)
                msg = None
                if m['msg_link']:
                    submission = ctb_misc.praw_call(ctb.reddit.get_submission, m['msg_link'])
                    if not len(submission.comments) > 0:
                        lg.warning("get_actions(): could not fetch msg (deleted?) from msg_link %s", m['msg_link'])
                    else:
                        # msg points to comment that initiated the action
                        msg = submission.comments[0]
                        # check if msg.author is present
                        if not msg.author:
                            lg.warning("get_actions(): could not fetch msg.author (deleted?) from msg_link %s", m['msg_link'])
                #elif m['msg_id']:
                #    msg = praw.objects.Message(ctb.reddit, {'id': m['msg_id']})

                r.append( CtbAction( atype=atype,
                                     msg=msg,
                                     from_user=m['from_user'],
                                     to_user=m['to_user'],
                                     to_addr=m['to_addr'] if not m['to_user'] else None,
                                     coin=m['coin'],
                                     fiat=m['fiat'],
                                     coin_val=float(m['coin_val']) if m['coin_val'] else None,
                                     fiat_val=float(m['fiat_val']) if m['fiat_val'] else None,
                                     subr=m['subreddit'],
                                     ctb=ctb,
                                     msg_id=m['msg_id']))

            lg.debug("< get_actions() DONE (yes)")
            return r

        except Exception as e:
            lg.error("get_actions(): error executing <%s>: %s", sql, e)
            raise

    lg.warning("< get_actions() DONE (should not get here)")
    return None

########NEW FILE########
__FILENAME__ = ctb_coin
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging, re, time
from pifkoin.bitcoind import Bitcoind, BitcoindException
from httplib import CannotSendRequest

lg = logging.getLogger('cointipbot')

class CtbCoin(object):
    """
    Coin class for cointip bot
    """

    conn = None
    conf = None

    def __init__(self, _conf = None):
        """
        Initialize CtbCoin with given parameters. _conf is a coin config dictionary defined in conf/coins.yml
        """

        # verify _conf is a config dictionary
        if not _conf or not hasattr(_conf, 'name') or not hasattr(_conf, 'config_file') or not hasattr(_conf, 'txfee'):
            raise Exception("CtbCoin::__init__(): _conf is empty or invalid")

        self.conf = _conf

        # connect to coin daemon
        try:
            lg.debug("CtbCoin::__init__(): connecting to %s...", self.conf.name)
            self.conn = Bitcoind(self.conf.config_file, rpcserver=self.conf.config_rpcserver)
        except BitcoindException as e:
            lg.error("CtbCoin::__init__(): error connecting to %s using %s: %s", self.conf.name, self.conf.config_file, e)
            raise

        lg.info("CtbCoin::__init__():: connected to %s", self.conf.name)
        time.sleep(0.5)

        # set transaction fee
        lg.info("Setting tx fee of %f", self.conf.txfee)
        self.conn.settxfee(self.conf.txfee)

    def getbalance(self, _user = None, _minconf = None):
        """
        Get user's tip or withdraw balance. _minconf is number of confirmations to use.
        Returns (float) balance
        """
        lg.debug("CtbCoin::getbalance(%s, %s)", _user, _minconf)

        user = self.verify_user(_user=_user)
        minconf = self.verify_minconf(_minconf=_minconf)
        balance = float(0)

        try:
            balance = self.conn.getbalance(user, minconf)
        except BitcoindException as e:
            lg.error("CtbCoin.getbalance(): error getting %s (minconf=%s) balance for %s: %s", self.conf.name, minconf, user, e)
            raise

        time.sleep(0.5)
        return float(balance)

    def sendtouser(self, _userfrom = None, _userto = None, _amount = None, _minconf = 1):
        """
        Transfer (move) coins to user
        Returns (bool)
        """
        lg.debug("CtbCoin::sendtouser(%s, %s, %.9f)", _userfrom, _userto, _amount)

        userfrom = self.verify_user(_user=_userfrom)
        userto = self.verify_user(_user=_userto)
        amount = self.verify_amount(_amount=_amount)

        # send request to coin daemon
        try:
            lg.info("CtbCoin::sendtouser(): moving %.9f %s from %s to %s", amount, self.conf.name, userfrom, userto)
            result = self.conn.move(userfrom, userto, amount)
            time.sleep(0.5)
        except Exception as e:
            lg.error("CtbCoin::sendtouser(): error moving %.9f %s from %s to %s: %s", amount, self.conf.name, userfrom, userto, e)
            return False

        time.sleep(0.5)
        return True

    def sendtoaddr(self, _userfrom = None, _addrto = None, _amount = None):
        """
        Send coins to address
        Returns (string) txid
        """
        lg.debug("CtbCoin::sendtoaddr(%s, %s, %.9f)", _userfrom, _addrto, _amount)

        userfrom = self.verify_user(_user=_userfrom)
        addrto = self.verify_addr(_addr=_addrto)
        amount = self.verify_amount(_amount=_amount)
        minconf = self.verify_minconf(_minconf=self.conf.minconf.withdraw)
        txid = ""

        # send request to coin daemon
        try:
            lg.info("CtbCoin::sendtoaddr(): sending %.9f %s from %s to %s", amount, self.conf.name, userfrom, addrto)

            # Unlock wallet, if applicable
            if hasattr(self.conf, 'walletpassphrase'):
                lg.debug("CtbCoin::sendtoaddr(): unlocking wallet...")
                self.conn.walletpassphrase(self.conf.walletpassphrase, 1)

            # Perform transaction
            lg.debug("CtbCoin::sendtoaddr(): calling sendfrom()...")
            txid = self.conn.sendfrom(userfrom, addrto, amount, minconf)

            # Lock wallet, if applicable
            if hasattr(self.conf, 'walletpassphrase'):
                lg.debug("CtbCoin::sendtoaddr(): locking wallet...")
                self.conn.walletlock()

        except Exception as e:
            lg.error("CtbCoin::sendtoaddr(): error sending %.9f %s from %s to %s: %s", amount, self.conf.name, userfrom, addrto, e)
            raise

        time.sleep(0.5)
        return str(txid)

    def validateaddr(self, _addr = None):
        """
        Verify that _addr is a valid coin address
        Returns (bool)
        """
        lg.debug("CtbCoin::validateaddr(%s)", _addr)

        addr = self.verify_addr(_addr=_addr)
        addr_valid = self.conn.validateaddress(addr)
        time.sleep(0.5)

        if not addr_valid.has_key('isvalid') or not addr_valid['isvalid']:
            lg.debug("CtbCoin::validateaddr(%s): not valid", addr)
            return False
        else:
            lg.debug("CtbCoin::validateaddr(%s): valid", addr)
            return True

    def getnewaddr(self, _user = None):
        """
        Generate a new address for _user
        Returns (string) address
        """

        user = self.verify_user(_user=_user)
        addr = ""
        counter = 0

        while True:
            try:
                # Unlock wallet for keypoolrefill
                if hasattr(self.conf, 'walletpassphrase'):
                    self.conn.walletpassphrase(self.conf.walletpassphrase, 1)

                # Generate new address
                addr = self.conn.getnewaddress(user)

                # Lock wallet
                if hasattr(self.conf, 'walletpassphrase'):
                    self.conn.walletlock()

                if not addr:
                    raise Exception("CtbCoin::getnewaddr(%s): empty addr", user)

                time.sleep(0.1)
                return str(addr)

            except BitcoindException as e:
                lg.error("CtbCoin::getnewaddr(%s): BitcoindException: %s", user, e)
                raise
            except CannotSendRequest as e:
                if counter < 3:
                    lg.warning("CtbCoin::getnewaddr(%s): CannotSendRequest, retrying")
                    counter += 1
                    time.sleep(10)
                    continue
                else:
                    raise
            except Exception as e:
                if str(e) == "timed out" and counter < 3:
                    lg.warning("CtbCoin::getnewaddr(%s): timed out, retrying")
                    counter += 1
                    time.sleep(10)
                    continue
                else:
                    lg.error("CtbCoin::getnewaddr(%s): Exception: %s", user, e)
                    raise


    def verify_user(self, _user = None):
        """
        Verify and return a username
        """

        if not _user or not type(_user) in [str, unicode]:
            raise Exception("CtbCoin::verify_user(): _user wrong type (%s) or empty (%s)", type(_user), _user)

        return str(_user.lower())

    def verify_addr(self, _addr = None):
        """
        Verify and return coin address
        """

        if not _addr or not type(_addr) in [str, unicode]:
            raise Exception("CtbCoin::verify_addr(): _addr wrong type (%s) or empty (%s)", type(_addr),_addr)

        return re.escape(str(_addr))

    def verify_amount(self, _amount = None):
        """
        Verify and return amount
        """

        if not _amount or not type(_amount) in [int, float] or not _amount > 0:
            raise Exception("CtbCoin::verify_amount(): _amount wrong type (%s), empty, or negative (%s)", type(_amount), _amount)

        return _amount

    def verify_minconf(self, _minconf = None):
        """
        Verify and return minimum number of confirmations
        """

        if not _minconf or not type(_minconf) == int or not _minconf >= 0:
            raise Exception("CtbCoin::verify_minconf(): _minconf wrong type (%s), empty, or negative (%s)", type(_minconf), _minconf)

        return _minconf

########NEW FILE########
__FILENAME__ = ctb_db
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, Numeric, UnicodeText
from sqlalchemy.pool import SingletonThreadPool

class CointipBotDatabase:

  metadata = MetaData()

  def __init__(self, dsn_url):
    '''Pass a DSN URL conforming to the SQLAlchemy API'''
    self.dsn_url = dsn_url

  def connect(self):
    '''Return a connection object'''
    engine = create_engine(self.dsn_url, echo_pool=True, poolclass=SingletonThreadPool)
    self.metadata.create_all(engine)
    return engine

########NEW FILE########
__FILENAME__ = ctb_exchange
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import json, logging, urllib2, httplib

lg = logging.getLogger('cointipbot')

class CtbExchange(object):
    """
    Exchange class for cointip bot
    """

    conf = None

    def __init__(self, _conf = None):
        """
        Initialize CtbExchange with given parameters.
            _conf is an exchange config dictionary defind in conf/exchanges.yml
        """

        if not _conf or not hasattr(_conf, 'urlpaths') or not hasattr(_conf, 'jsonpaths') or not hasattr(_conf, 'coinlist') or not hasattr(_conf, 'fiatlist'):
            raise Exception("CtbExchange::__init__(): _conf is empty or invalid")

        self.conf = _conf

        # Convert coinlist and fiatlist values to lowercase
        self.conf.coinlist = map(lambda x:x.lower(), self.conf.coinlist)
        self.conf.fiatlist = map(lambda x:x.lower(), self.conf.fiatlist)

        lg.debug("CtbExchange::__init__(): initialized exchange %s" % self.conf.domain)

    def supports(self, _name = None):
        """
        Return True if exchange supports given coin/fiat _name
        """

        if not _name or not type(_name) in [str, unicode]:
            raise Exception("CtbExchange::supports(): _name is empty or wrong type")

        name = str(_name).lower()

        if name in self.conf.coinlist or name in self.conf.fiatlist:
            #lg.debug("CtbExchange::supports(%s): YES" % name)
            return True
        else:
            #lg.debug("CtbExchange::supports(%s): NO" % name)
            return False

    def supports_pair(self, _name1 = None, _name2 = None):
        """
        Return true of exchange supports given coin/fiat pair
        """

        return self.supports(_name=_name1) and self.supports(_name=_name2)

    def get_ticker_value(self, _name1 = None, _name2 = None):
        """
        Return (float) ticker value for given pair
        """

        if _name1 == _name2:
            return float(1)

        if not self.supports_pair(_name1=_name1, _name2=_name2):
            raise Exception("CtbExchange::get_ticker_value(%s, %s, %s): pair not supported" % (self.conf.domain, _name1, _name2))

        results = []
        for myurlpath in self.conf.urlpaths:
            for myjsonpath in self.conf.jsonpaths:

                toreplace = {'{THING_FROM}': _name1.upper() if self.conf.uppercase else _name1.lower(), '{THING_TO}': _name2.upper() if self.conf.uppercase else _name2.lower()}
                for t in toreplace:
                    myurlpath = myurlpath.replace(t, toreplace[t])
                    myjsonpath = myjsonpath.replace(t, toreplace[t])

                try:
                    lg.debug("CtbExchange::get_ticker_value(%s, %s, %s): calling %s to get %s...", self.conf.domain, _name1, _name2, myurlpath, myjsonpath)
                    if self.conf.https:
                        connection = httplib.HTTPSConnection(self.conf.domain, timeout=5)
                        connection.request("GET", myurlpath, {}, {})
                    else:
                        connection = httplib.HTTPConnection(self.conf.domain, timeout=5)
                        connection.request("GET", myurlpath)
                    response = json.loads(connection.getresponse().read())
                    result = xpath_get(response, myjsonpath)
                    lg.debug("CtbExchange::get_ticker_value(%s, %s, %s): result: %.6f", self.conf.domain, _name1, _name2, float(result))
                    results.append( float(result) )

                except urllib2.URLError as e:
                    lg.error("CtbExchange::get_ticker_value(%s, %s, %s): %s", self.conf.domain, _name1, _name2, e)
                    return 0.0
                except urllib2.HTTPError as e:
                    lg.error("CtbExchange::get_ticker_value(%s, %s, %s): %s", self.conf.domain, _name1, _name2, e)
                    return 0.0
                except Exception as e:
                    lg.error("CtbExchange::get_ticker_value(%s, %s, %s): %s", self.conf.domain, _name1, _name2, e)
                    return 0.0

        # Return average of all responses
        return ( sum(results) / float(len(results)) )


def xpath_get(mydict, path):
    elem = mydict
    try:
        for x in path.strip('.').split('.'):
            try:
                x = int(x)
                elem = elem[x]
            except ValueError:
                elem = elem.get(x)
    except:
        pass
    return elem

########NEW FILE########
__FILENAME__ = ctb_log
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging

class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno >= self.level

########NEW FILE########
__FILENAME__ = ctb_misc
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import ctb_user

import logging, time

from requests.exceptions import HTTPError, ConnectionError, Timeout
from praw.errors import ExceptionList, APIException, InvalidCaptcha, InvalidUser, RateLimitExceeded
from socket import timeout

lg = logging.getLogger('cointipbot')


def praw_call(prawFunc, *extraArgs, **extraKwArgs):
    """
    Call prawFunc() with extraArgs and extraKwArgs
    Retry if Reddit is down
    """

    while True:

        try:
            res = prawFunc(*extraArgs, **extraKwArgs)
            return res

        except (HTTPError, ConnectionError, Timeout, timeout) as e:
            if str(e) in [ "400 Client Error: Bad Request", "403 Client Error: Forbidden", "404 Client Error: Not Found" ]:
                lg.warning("praw_call(): Reddit returned error (%s)", e)
                return False
            else:
                lg.warning("praw_call(): Reddit returned error (%s), sleeping...", e)
                time.sleep(30)
                pass
        except APIException as e:
            if str(e) == "(DELETED_COMMENT) `that comment has been deleted` on field `parent`":
                lg.warning("praw_call(): deleted comment: %s", e)
                return False
            else:
                raise
        except RateLimitExceeded as e:
            lg.warning("praw_call(): rate limit exceeded, sleeping for %s seconds", e.sleep_time)
            time.sleep(e.sleep_time)
            time.sleep(1)
            pass
        except Exception as e:
            raise

    return True

def reddit_get_parent_author(comment, reddit, ctb):
    """
    Return author of comment's parent comment
    """
    lg.debug("> reddit_get_parent_author()")

    while True:

        try:

            parentpermalink = comment.permalink.replace(comment.id, comment.parent_id[3:])
            commentlinkid = None
            if hasattr(comment, 'link_id'):
                commentlinkid = comment.link_id[3:]
            else:
                comment2 = reddit.get_submission(comment.permalink).comments[0]
                commentlinkid = comment2.link_id[3:]
            parentid = comment.parent_id[3:]

            if commentlinkid == parentid:
                parentcomment = reddit.get_submission(parentpermalink)
            else:
                parentcomment = reddit.get_submission(parentpermalink).comments[0]

            if parentcomment and hasattr(parentcomment, 'author') and parentcomment.author:
                lg.debug("< reddit_get_parent_author(%s) -> %s", comment.id, parentcomment.author.name)
                return parentcomment.author.name
            else:
                lg.warning("< reddit_get_parent_author(%s) -> NONE", comment.id)
                return None

        except (IndexError, APIException) as e:
            lg.warning("reddit_get_parent_author(): couldn't get author: %s", e)
            return None
        except (HTTPError, RateLimitExceeded, timeout) as e:
            if str(e) in [ "400 Client Error: Bad Request", "403 Client Error: Forbidden", "404 Client Error: Not Found" ]:
                lg.warning("reddit_get_parent_author(): Reddit returned error (%s)", e)
                return None
            else:
                lg.warning("reddit_get_parent_author(): Reddit returned error (%s), sleeping...", e)
                time.sleep(ctb.conf.misc.times.sleep_seconds)
                pass
        except Exception as e:
            raise

    lg.error("reddit_get_parent_author(): returning None (should not get here)")
    return None

def get_value(conn, param0=None):
    """
    Fetch a value from t_values table
    """
    lg.debug("> get_value()")

    if param0 == None:
        raise Exception("get_value(): param0 == None")

    value = None
    sql = "SELECT value0 FROM t_values WHERE param0 = %s"

    try:

        mysqlrow = conn.execute(sql, (param0)).fetchone()
        if mysqlrow == None:
            lg.error("get_value(): query <%s> didn't return any rows", sql % (param0))
            return None
        value = mysqlrow['value0']

    except Exception, e:
       lg.error("get_value(): error executing query <%s>: %s", sql % (param0), e)
       raise

    lg.debug("< get_value() DONE (%s)", value)
    return value

def set_value(conn, param0=None, value0=None):
    """
    Set a value in t_values table
    """
    lg.debug("> set_value(%s, %s)", param0, value0)

    if param0 == None or value0 == None:
        raise Exception("set_value(): param0 == None or value0 == None")
    sql = "REPLACE INTO t_values (param0, value0) VALUES (%s, %s)"

    try:

        mysqlexec = conn.execute(sql, (param0, value0))
        if mysqlexec.rowcount <= 0:
            lg.error("set_value(): query <%s> didn't affect any rows", sql % (param0, value0))
            return False

    except Exception, e:
        lg.error("set_value: error executing query <%s>: %s", sql % (param0, value0), e)
        raise

    lg.debug("< set_value() DONE")
    return True

def add_coin(coin, db, coins):
    """
    Add new coin address to each user
    """
    lg.debug("> add_coin(%s)", coin)

    sql_select = "SELECT username FROM t_users WHERE username NOT IN (SELECT username FROM t_addrs WHERE coin = %s) ORDER BY username"
    sql_insert = "REPLACE INTO t_addrs (username, coin, address) VALUES (%s, %s, %s)"

    try:

        mysqlsel = db.execute(sql_select, (coin))
        for m in mysqlsel:
            # Generate new coin address for user
            new_addr = coins[coin].getnewaddr(_user=m['username'])
            lg.info("add_coin(): got new address %s for %s", new_addr, m['username'])
            # Add new coin address to MySQL
            mysqlins = db.execute(sql_insert, (m['username'].lower(), coin, new_addr))
            if mysqlins.rowcount <= 0:
                raise Exception("add_coin(%s): rowcount <= 0 when executing <%s>", coin, sql_insert % (m['username'].lower(), coin, new_addr))
            time.sleep(1)

    except Exception, e:
        lg.error("add_coin(%s): error: %s", coin, e)
        raise

    lg.debug("< add_coin(%s) DONE", coin)
    return True

class DotDict(object):
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
               setattr(self, a, [DotDict(x) if isinstance(x, dict) else x for x in b])
            else:
               setattr(self, a, DotDict(b) if isinstance(b, dict) else b)
    def __getitem__(self, val):
        return getattr(self, val)
    def has_key(self, key):
        return hasattr(self, key)

########NEW FILE########
__FILENAME__ = ctb_stats
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging, re, time
import ctb_misc

lg = logging.getLogger('cointipbot')

def update_stats(ctb=None):
    """
    Update stats wiki page
    """

    stats = ""

    if not ctb.conf.reddit.stats.enabled:
        return None

    for s in sorted(vars(ctb.conf.db.sql.globalstats)):
        lg.debug("update_stats(): getting stats for '%s'" % s)
        sql = ctb.conf.db.sql.globalstats[s].query
        stats += "\n\n### %s\n\n" % ctb.conf.db.sql.globalstats[s].name
        stats += "%s\n\n" % ctb.conf.db.sql.globalstats[s].desc

        mysqlexec = ctb.db.execute(sql)
        if mysqlexec.rowcount <= 0:
            lg.warning("update_stats(): query <%s> returned nothing" % ctb.conf.db.sql.globalstats[s].query)
            continue

        if ctb.conf.db.sql.globalstats[s].type == "line":
            m = mysqlexec.fetchone()
            k = mysqlexec.keys()[0]
            value = format_value(m, k, '', ctb)
            stats += "%s = **%s**\n" % (k, value)

        elif ctb.conf.db.sql.globalstats[s].type == "table":
            stats += ("|".join(mysqlexec.keys())) + "\n"
            stats += ("|".join([":---"] * len(mysqlexec.keys()))) + "\n"
            for m in mysqlexec:
                values = []
                for k in mysqlexec.keys():
                    values.append(format_value(m, k, '', ctb))
                stats += ("|".join(values)) + "\n"

        else:
            lg.error("update_stats(): don't know what to do with type '%s'" % ctb.conf.db.sql.globalstats[s].type)
            return False

        stats += "\n"

    lg.debug("update_stats(): updating subreddit '%s', page '%s'" % (ctb.conf.reddit.stats.subreddit, ctb.conf.reddit.stats.page))
    return ctb_misc.praw_call(ctb.reddit.edit_wiki_page, ctb.conf.reddit.stats.subreddit, ctb.conf.reddit.stats.page, stats, "Update by ALTcointip bot")

def update_tips(ctb=None):
    """
    Update page listing all tips
    """

    if not ctb.conf.reddit.stats.enabled:
        return None

    # Start building stats page
    tip_list = "### All Completed Tips\n\n"

    q = ctb.db.execute(ctb.conf.db.sql.tips.sql_set)
    tips = ctb.db.execute(ctb.conf.db.sql.tips.sql_list, (ctb.conf.db.sql.tips.limit))
    tip_list += ("|".join(tips.keys())) + "\n"
    tip_list += ("|".join([":---"] * len(tips.keys()))) + "\n"

    # Build tips table
    for t in tips:
        values = []
        for k in tips.keys():
            values.append(format_value(t, k, '', ctb, compact=True))
        tip_list += ("|".join(values)) + "\n"

    lg.debug("update_tips(): updating subreddit '%s', page '%s'" % (ctb.conf.reddit.stats.subreddit, ctb.conf.reddit.stats.page_tips))
    ctb_misc.praw_call(ctb.reddit.edit_wiki_page, ctb.conf.reddit.stats.subreddit, ctb.conf.reddit.stats.page_tips, tip_list, "Update by ALTcointip bot")

    return True

def update_all_user_stats(ctb=None):
    """
    Update individual user stats for all uers
    """

    if not ctb.conf.reddit.stats.enabled:
        lg.error('update_all_user_stats(): stats are not enabled in config.yml')
        return None

    users = ctb.db.execute(ctb.conf.db.sql.userstats.users)
    for u in users:
        update_user_stats(ctb=ctb, username=u['username'])

def update_user_stats(ctb=None, username=None):
    """
    Update individual user stats for given username
    """

    if not ctb.conf.reddit.stats.enabled:
        return None

    # List of coins
    coins_q = ctb.db.execute(ctb.conf.db.sql.userstats.coins)
    coins = []
    for c in coins_q:
        coins.append(c['coin'])

    # List of fiat
    fiat_q = ctb.db.execute(ctb.conf.db.sql.userstats.fiat)
    fiat = []
    for f in fiat_q:
        fiat.append(f['fiat'])

    # Start building stats page
    user_stats = "### Tipping Summary for /u/%s\n\n" % username
    page = ctb.conf.reddit.stats.page + '_' + username

    # Total Tipped
    user_stats += "#### Total Tipped (Fiat)\n\n"
    user_stats += "fiat|total\n:---|---:\n"
    total_tipped = []
    for f in fiat:
        mysqlexec = ctb.db.execute(ctb.conf.db.sql.userstats.total_tipped_fiat, (username, f))
        total_tipped_fiat = mysqlexec.fetchone()
        if total_tipped_fiat['total_fiat'] != None:
            user_stats += "**%s**|%s %.2f\n" % (f, ctb.conf.fiat[f].symbol, total_tipped_fiat['total_fiat'])
            total_tipped.append("%s%.2f" % (ctb.conf.fiat[f].symbol, total_tipped_fiat['total_fiat']))
    user_stats += "\n"

    user_stats += "#### Total Tipped (Coins)\n\n"
    user_stats += "coin|total\n:---|---:\n"
    for c in coins:
        mysqlexec = ctb.db.execute(ctb.conf.db.sql.userstats.total_tipped_coin, (username, c))
        total_tipped_coin = mysqlexec.fetchone()
        if total_tipped_coin['total_coin'] != None:
            user_stats += "**%s**|%s %.6f\n" % (c, ctb.conf.coins[c].symbol, total_tipped_coin['total_coin'])
    user_stats += "\n"

    # Total received
    user_stats += "#### Total Received (Fiat)\n\n"
    user_stats += "fiat|total\n:---|---:\n"
    total_received = []
    for f in fiat:
        mysqlexec = ctb.db.execute(ctb.conf.db.sql.userstats.total_received_fiat, (username, f))
        total_received_fiat = mysqlexec.fetchone()
        if total_received_fiat['total_fiat'] != None:
            user_stats += "**%s**|%s %.2f\n" % (f, ctb.conf.fiat[f].symbol, total_received_fiat['total_fiat'])
            total_received.append("%s%.2f" % (ctb.conf.fiat[f].symbol, total_received_fiat['total_fiat']))
    user_stats += "\n"

    user_stats += "#### Total Received (Coins)\n\n"
    user_stats += "coin|total\n:---|---:\n"
    for c in coins:
        mysqlexec = ctb.db.execute(ctb.conf.db.sql.userstats.total_received_coin, (username, c))
        total_received_coin = mysqlexec.fetchone()
        if total_received_coin['total_coin'] != None:
            user_stats += "**%s**|%s %.6f\n" % (c, ctb.conf.coins[c].symbol, total_received_coin['total_coin'])
    user_stats += "\n"

    # History
    user_stats += "#### History\n\n"
    history = ctb.db.execute(ctb.conf.db.sql.userstats.history, (username, username))
    user_stats += ("|".join(history.keys())) + "\n"
    user_stats += ("|".join([":---"] * len(history.keys()))) + "\n"

    # Build history table
    num_tipped = 0
    num_received = 0
    for m in history:
        if m['state'] == 'completed':
            if m['from_user'].lower() == username.lower():
                num_tipped += 1
            elif m['to_user'].lower() == username.lower():
                num_received += 1
        values = []
        for k in history.keys():
            values.append(format_value(m, k, username, ctb))
        user_stats += ("|".join(values)) + "\n"

    # Submit changes
    lg.debug("update_user_stats(): updating subreddit '%s', page '%s'" % (ctb.conf.reddit.stats.subreddit, page))
    ctb_misc.praw_call(ctb.reddit.edit_wiki_page, ctb.conf.reddit.stats.subreddit, page, user_stats, "Update by ALTcointip bot")

    # Update user flair on subreddit
    if ctb.conf.reddit.stats.userflair and ( len(total_tipped) > 0 or len(total_received) > 0 ):
        flair = ""
        if len(total_tipped) > 0:
            flair += "tipped[" + '|'.join(total_tipped) + "]"
            flair += " (%d)" % num_tipped
        if len(total_received) > 0:
            if len(total_tipped) > 0:
                flair += " / "
            flair += "received[" + '|'.join(total_received) + "]"
            flair += " (%d)" % num_received
        lg.debug("update_user_stats(): updating flair for %s (%s)", username, flair)
        r = ctb_misc.praw_call(ctb.reddit.get_subreddit, ctb.conf.reddit.stats.subreddit)
        res = ctb_misc.praw_call(r.set_flair, username, flair, '')
        lg.debug(res)

    return True

def format_value(m, k, username, ctb, compact=False):
    """
    Format value for display based on its type
    m[k] is the value, k is the database row name
    """

    if not m[k]:
        return '-'

    # Format cryptocoin
    if type(m[k]) == float and k.find("coin") > -1:
        coin_symbol = ctb.conf.coins[m['coin']].symbol
        return "%s&nbsp;%.5g" % (coin_symbol, m[k])

    # Format fiat
    elif type(m[k]) == float and ( k.find("fiat") > -1 or k.find("usd") > -1 ):
        fiat_symbol = ctb.conf.fiat[m['fiat']].symbol
        return "%s&nbsp;%.2f" % (fiat_symbol, m[k])

    # Format username
    elif k.find("user") > -1 and type( m[k] ) in [str, unicode]:
        if compact:
            return ("**/u/%s**" % m[k]) if m[k].lower() == username.lower() else ("/u/%s" % m[k])
        else:
            un = ("**%s**" % m[k]) if m[k].lower() == username.lower() else m[k]
            toreturn = "[%s](/u/%s)" % (un, re.escape(m[k]))
            if m[k].lower() != username.lower():
                toreturn += "^[[stats]](/r/%s/wiki/%s_%s)" % (ctb.conf.reddit.stats.subreddit, ctb.conf.reddit.stats.page, m[k])
            return toreturn

    # Format address
    elif k.find("addr") > -1:
        displayaddr = m[k][:6] + "..." + m[k][-5:]
        return "[%s](%s%s)" % (displayaddr, ctb.conf.coins[m['coin']].explorer.address, m[k])

    # Format state
    elif k.find("state") > -1:
        if m[k] == 'completed':
            return unicode('✓', 'utf8')
        else:
            return m[k]

    # Format type
    elif k.find("type") > -1:
        if m[k] == 'givetip':
            return 'tip'
        if compact:
            if m[k] == 'withdraw':
                return 'w'
            if m[k] == 'redeem':
                return 'r'

    # Format subreddit
    elif k.find("subreddit") > -1:
        return "/r/%s" % m[k]

    # Format link
    elif k.find("link") > -1:
        return "[link](%s)" % m[k]

    # Format time
    elif k.find("utc") > -1:
        return "%s" % time.strftime('%Y-%m-%d', time.localtime(m[k]))

    # It's something else
    else:
        return str(m[k])

########NEW FILE########
__FILENAME__ = ctb_user
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import ctb_misc

import logging, time, praw, re

lg = logging.getLogger('cointipbot')

class CtbUser(object):
    """
    User class for cointip bot
    """

    # Basic properties
    name=None
    giftamount=None
    joindate=None
    addr={}
    banned=False

    # Objects
    prawobj=None
    ctb=None

    def __init__(self, name=None, redditobj=None, ctb=None):
        """
        Initialize CtbUser object with given parameters
        """
        lg.debug("> CtbUser::__init__(%s)", name)

        if not bool(name):
            raise Exception("CtbUser::__init__(): name must be set")
        self.name = name

        if not bool(ctb):
            raise Exception("CtbUser::__init__(): ctb must be set")
        self.ctb = ctb

        if bool(redditobj):
            self.prawobj = redditobj

        # Determine if user is banned
        if ctb.conf.reddit.banned_users:
            if ctb.conf.reddit.banned_users.method == 'subreddit':
                for u in ctb.reddit.get_banned(ctb.conf.reddit.banned_users.subreddit):
                    if self.name.lower() == u.name.lower():
                        self.banned = True
            elif ctb.conf.reddit.banned_users.method == 'list':
                for u in ctb.conf.reddit.banned_users.list:
                    if self.name.lower() == u.lower():
                        self.banned = True
            else:
                lg.warning("CtbUser::__init__(): invalid method '%s' in banned_users config" % ctb.conf.reddit.banned_users.method)

        lg.debug("< CtbUser::__init__(%s) DONE", name)

    def __str__(self):
        """
        Return string representation of self
        """
        me = "<CtbUser: name=%s, giftamnt=%s, joindate=%s, addr=%s, redditobj=%s, banned=%s>"
        me = me % (self.name, self.giftamount, self.joindate, self.addr, self.prawobj, self.banned)
        return me

    def get_balance(self, coin=None, kind=None):
        """
        If coin is specified, return float with coin balance for user. Else, return a dict with balance of each coin for user.
        """
        lg.debug("> CtbUser::balance(%s)", self.name)

        if not bool(coin) or not bool(kind):
            raise Exception("CtbUser::balance(%s): coin or kind not set" % self.name)

        # Ask coin daemon for account balance
        lg.info("CtbUser::balance(%s): getting %s %s balance", self.name, coin, kind)
        balance = self.ctb.coins[coin].getbalance(_user=self.name, _minconf=self.ctb.conf.coins[coin].minconf[kind])

        lg.debug("< CtbUser::balance(%s) DONE", self.name)
        return float(balance)

    def get_addr(self, coin=None):
        """
        Return coin address of user
        """
        lg.debug("> CtbUser::get_addr(%s, %s)", self.name, coin)

        if hasattr(self.addr, coin):
            return self.addr[coin]

        sql = "SELECT address from t_addrs WHERE username = %s AND coin = %s"
        mysqlrow = self.ctb.db.execute(sql, (self.name.lower(), coin.lower())).fetchone()
        if not mysqlrow:
            lg.debug("< CtbUser::get_addr(%s, %s) DONE (no)", self.name, coin)
            return None
        else:
            self.addr[coin] = mysqlrow['address']
            lg.debug("< CtbUser::get_addr(%s, %s) DONE (%s)", self.name, coin, self.addr[coin])
            return self.addr[coin]

        lg.debug("< CtbUser::get_addr(%s, %s) DONE (should never happen)", self.name, coin)
        return None

    def is_on_reddit(self):
        """
        Return true if username exists Reddit. Also set prawobj pointer while at it.
        """
        lg.debug("> CtbUser::is_on_reddit(%s)", self.name)

        # Return true if prawobj is already set
        if bool(self.prawobj):
            lg.debug("< CtbUser::is_on_reddit(%s) DONE (yes)", self.name)
            return True

        try:
            self.prawobj = ctb_misc.praw_call(self.ctb.reddit.get_redditor, self.name)
            if self.prawobj:
                return True
            else:
                return False

        except Exception as e:
            lg.debug("< CtbUser::is_on_reddit(%s) DONE (no)", self.name)
            return False

        lg.warning("< CtbUser::is_on_reddit(%s): returning None (shouldn't happen)", self.name)
        return None

    def is_registered(self):
        """
        Return true if user is registered with CointipBot
        """
        lg.debug("> CtbUser::is_registered(%s)", self.name)

        try:
            # First, check t_users table
            sql = "SELECT * FROM t_users WHERE username = %s"
            mysqlrow = self.ctb.db.execute(sql, (self.name.lower())).fetchone()

            if not mysqlrow:
                lg.debug("< CtbUser::is_registered(%s) DONE (no)", self.name)
                return False

            else:
                # Next, check t_addrs table for whether  user has correct number of coin addresses
                sql_coins = "SELECT COUNT(*) AS count FROM t_addrs WHERE username = %s"
                mysqlrow_coins = self.ctb.db.execute(sql_coins, (self.name.lower())).fetchone()

                if int(mysqlrow_coins['count']) != len(self.ctb.coins):
                    if int(mysqlrow_coins['count']) == 0:
                        # Bot probably crashed during user registration process
                        # Delete user
                        lg.warning("CtbUser::is_registered(%s): deleting user, incomplete registration", self.name)
                        sql_delete = "DELETE FROM t_users WHERE username = %s"
                        mysql_res = self.ctb.db.execute(sql_delete, (self.name.lower()))
                        # User is not registered
                        return False
                    else:
                        raise Exception("CtbUser::is_registered(%s): user has %s coins but %s active" % (self.name, mysqlrow_coins['count'], len(self.ctb.coins)))

                # Set some properties
                self.giftamount = mysqlrow['giftamount']

                # Done
                lg.debug("< CtbUser::is_registered(%s) DONE (yes)", self.name)
                return True

        except Exception, e:
            lg.error("CtbUser::is_registered(%s): error while executing <%s>: %s", self.name, sql % self.name.lower(), e)
            raise

        lg.warning("< CtbUser::is_registered(%s): returning None (shouldn't happen)", self.name)
        return None

    def tell(self, subj=None, msg=None, msgobj=None):
        """
        Send a Reddit message to user
        """
        lg.debug("> CtbUser::tell(%s)", self.name)

        if not bool(subj) or not bool(msg):
            raise Exception("CtbUser::tell(%s): subj or msg not set", self.name)

        if not self.is_on_reddit():
            raise Exception("CtbUser::tell(%s): not a Reddit user", self.name)

        if bool(msgobj):
            lg.debug("CtbUser::tell(%s): replying to message", msgobj.id)
            ctb_misc.praw_call(msgobj.reply, msg)
        else:
            lg.debug("CtbUser::tell(%s): sending message", self.name)
            ctb_misc.praw_call(self.prawobj.send_message, subj, msg)

        lg.debug("< CtbUser::tell(%s) DONE", self.name)
        return True

    def register(self):
        """
        Add user to database and generate coin addresses
        """
        lg.debug("> CtbUser::register(%s)", self.name)

        # Add user to database
        try:
            sql_adduser = "INSERT INTO t_users (username) VALUES (%s)"
            mysqlexec = self.ctb.db.execute(sql_adduser, (self.name.lower()))
            if mysqlexec.rowcount <= 0:
                raise Exception("CtbUser::register(%s): rowcount <= 0 while executing <%s>" % ( self.name, sql_adduser % (self.name.lower()) ))
        except Exception, e:
            lg.error("CtbUser::register(%s): exception while executing <%s>: %s", self.name, sql_adduser % (self.name.lower()), e)
            raise

        # Get new coin addresses
        new_addrs = {}
        for c in self.ctb.coins:
            new_addrs[c] = self.ctb.coins[c].getnewaddr(_user=self.name.lower())
            lg.info("CtbUser::register(%s): got %s address %s", self.name, c, new_addrs[c])

        # Add coin addresses to database
        for c in new_addrs:
            try:
                sql_addr = "REPLACE INTO t_addrs (username, coin, address) VALUES (%s, %s, %s)"
                mysqlexec = self.ctb.db.execute(sql_addr, (self.name.lower(), c, new_addrs[c]))
                if mysqlexec.rowcount <= 0:
                    # Undo change to database
                    delete_user(_username=self.name.lower(), _db=self.ctb.db)
                    raise Exception("CtbUser::register(%s): rowcount <= 0 while executing <%s>" % (self.name, sql_addr % (self.name.lower(), c, new_addrs[c])))

            except Exception, e:
                # Undo change to database
                delete_user(_username=self.name.lower(), _db=self.ctb.db)
                raise

        lg.debug("< CtbUser::register(%s) DONE", self.name)
        return True

    def get_redeem_amount(self, coin=None, fiat=None):
        """
        Return karma redeem amount for a given coin
        """
        lg.debug("> CtbUser::get_redeem_amount(%s)", coin)

        if not coin or not self.ctb.coins.has_key(coin):
            raise Exception("CtbUser::get_redeem_amount(%s): invalid coin" % coin)
        if not fiat or not self.ctb.conf.fiat.has_key(fiat):
            raise Exception("CtbUser::get_redeem_amount(%s): invalid fiat" % fiat)

        # Check if we have coin's fiat value
        coin_value = self.ctb.coin_value(coin, fiat)
        if not coin_value or not coin_value > 0.0:
            lg.warning("CtbUser::get_redeem_amount(%s): coin_value not available", coin)
            return (None, None)

        # First, determine fiat value due to link karma
        link_mul = self.ctb.conf.reddit.redeem.multiplier.link
        if type(link_mul) in [str, unicode]:
            link_mul = eval(link_mul)
        if not type(link_mul) == float:
            raise Exception("CtbUser::get_redeem_amount(): type of link_mul is not float")
        link_val = float(self.prawobj.link_karma) * link_mul

        # Second, determine fiat value due to comment karma
        comm_mul = self.ctb.conf.reddit.redeem.multiplier.comment
        if type(comm_mul) in [str, unicode]:
            comm_mul = eval(comm_mul)
        if not type(comm_mul) == float:
            raise Exception("CtbUser::get_redeem_amount(): type of comm_mul is not float")
        comm_val = float(self.prawobj.comment_karma) * comm_mul

        # Third, determine base fiat value from config
        base_val = self.ctb.conf.reddit.redeem.base
        if type(base_val) in [str, unicode]:
            base_val = eval(base_val)
        if not type(base_val) == float:
            raise Exception("CtbUser::get_redeem_amount(): type of base_val is not float")

        # Sum link_val, comm_val, and base_val to get total fiat
        total_fiat = link_val + comm_val + base_val

        # Check if above maximum
        if total_fiat > self.ctb.conf.reddit.redeem.maximum:
            total_fiat = self.ctb.conf.reddit.redeem.maximum

        # Determine total coin value using exchange rate
        total_coin = total_fiat / coin_value

        lg.debug("< CtbUser::get_redeem_amount(%s) DONE", coin)
        return (total_coin, total_fiat)


def delete_user(_username=None, _db=None):
    """
    Delete _username from t_users and t_addrs tables
    """
    lg.debug("> delete_user(%s)", _username)

    try:
        sql_arr = ["DELETE FROM t_users WHERE username = %s",
                   "DELETE FROM t_addrs WHERE username = %s"]
        for sql in sql_arr:
            mysqlexec = _db.execute(sql, _username.lower())
            if mysqlexec.rowcount <= 0:
                lg.warning("delete_user(%s): rowcount <= 0 while executing <%s>", _username, sql % _username.lower())

    except Exception, e:
        lg.error("delete_user(%s): error while executing <%s>: %s", _username, sql % _username.lower(), e)
        return False

    lg.debug("< delete_user(%s) DONE", _username)
    return True

########NEW FILE########
__FILENAME__ = _add_coin
# Here's how to add a new coin type to CointipBot

# * Make sure CointipBot instance is NOT running
# * Install and run coin daemon, make sure it's synced with network
# * Configure and nable new coin in config.yml
# * Then run this script, specifying coin (such as "python _add_coin.py btc")
# * After this script has finished, you can reusme the tip bot normally

import cointipbot, logging, sys
from ctb import ctb_coin, ctb_misc

if not len(sys.argv) == 2:
        print "Usage: %s COIN" % sys.argv[0]
        print "(COIN refers to ctb.conf[COIN], a hash location in coins.yml)"
        sys.exit(1)

coin = sys.argv[1]

logging.basicConfig()
lg = logging.getLogger('cointipbot')
lg.setLevel(logging.DEBUG)

ctb = cointipbot.CointipBot(self_checks=False, init_reddit=False, init_coins=False, init_exchanges=False, init_db=True, init_logging=True)
ctb.coins[coin] = ctb_coin.CtbCoin(_conf=ctb.conf.coins[coin])
ctb_misc.add_coin(coin, ctb.db, ctb.coins)

########NEW FILE########
__FILENAME__ = _backup_config
# Simple script to back up ALTcointip conf/ dir

import sys, os, datetime
from distutils.spawn import find_executable
import cointipbot

if not len(sys.argv) in [2, 3] or not os.access(sys.argv[1], os.W_OK):
	print "Usage: %s DIRECTORY [RSYNC-TO]" % sys.argv[0]
	print "(DIRECTORY must be writeable, RSYNC-TO is optional location to RSYNC the file to)"
	sys.exit(1)

ctb = cointipbot.CointipBot(self_checks=False, init_reddit=False, init_coins=False, init_db=False, init_logging=False)

if not find_executable('zip'):
	print "zip executable not found, please install zip"
	sys.exit(1)

if hasattr(ctb.conf.misc.backup, 'encryptionpassphrase') and not find_executable('gpg'):
	print "encryptionpassphrase is specified but gpg executable not found, please install gpg"
	sys.exit(1)

filename = "%s/conf_%s.zip" % (sys.argv[1], datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

print "Backing up to %s..." % filename
os.popen("zip -r %s conf/" % filename)

try:
	print "Encrypting..."
	os.popen("gpg --batch --passphrase '%s' -c %s" % (ctb.conf.misc.backup.encryptionpassphrase, filename))
	os.popen("rm -f %s" % filename)
	filename += '.gpg'
except AttributeError:
	print "Not encrypting"

if len(sys.argv) == 3:
	print "Calling rsync..."
	os.popen("rsync -urltv %s %s" % (filename, sys.argv[2]))

########NEW FILE########
__FILENAME__ = _backup_db
# Simple script to back up ALTcointip database

import sys, os, datetime
from distutils.spawn import find_executable
import cointipbot

if not len(sys.argv) in [2, 3] or not os.access(sys.argv[1], os.W_OK):
	print "Usage: %s DIRECTORY [RSYNC-TO]" % sys.argv[0]
	print "(DIRECTORY must be writeable, RSYNC-TO is optional location to RSYNC the file to)"
	sys.exit(1)

ctb = cointipbot.CointipBot(self_checks=False, init_reddit=False, init_coins=False, init_db=True, init_logging=False)

if not find_executable('gzip'):
        print "gzip executable not found, please install gzip"
        sys.exit(1)

if hasattr(ctb.conf.misc.backup, 'encryptionpassphrase') and not find_executable('gpg'):
        print "encryptionpassphrase is specified but gpg executable not found, please install gpg"
        sys.exit(1)

filename = "%s/%s_%s.sql.gz" % (sys.argv[1], ctb.conf.db.auth.dbname, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

print "Backing up to %s..." % filename
os.popen("mysqldump -u %s -p%s -h %s -e --opt -c %s | gzip --best -c >%s" % (ctb.conf.db.auth.user, ctb.conf.db.auth.password, ctb.conf.db.auth.host, ctb.conf.db.auth.dbname, filename))

try:
	print "Encrypting..."
	os.popen("gpg --batch --passphrase '%s' -c %s" % (ctb.conf.misc.backup.encryptionpassphrase, filename))
	os.popen("rm -f %s" % filename)
	filename += '.gpg'
except AttributeError:
	print "Not encrypting"

if len(sys.argv) == 3:
	print "Calling rsync..."
	os.popen("rsync -urltv %s %s" % (filename, sys.argv[2]))

########NEW FILE########
__FILENAME__ = _backup_wallets
# Simple script to back up active coin wallets

import sys, os, datetime, logging
from distutils.spawn import find_executable
import cointipbot

logging.basicConfig()
lg = logging.getLogger('cointipbot')
lg.setLevel(logging.DEBUG)

if not len(sys.argv) in [2, 3] or not os.access(sys.argv[1], os.W_OK):
	print "Usage: %s DIRECTORY [RSYNC-TO]" % sys.argv[0]
	print "(DIRECTORY must be writeable, RSYNC-TO is optional location to RSYNC the file to)"
	sys.exit(1)

ctb = cointipbot.CointipBot(self_checks=False, init_reddit=False, init_coins=True, init_db=False, init_logging=False)

if not find_executable('gzip'):
	print "gzip executable not found, please install gzip"
	sys.exit(1)

if hasattr(ctb.conf.misc.backup, 'encryptionpassphrase') and not find_executable('gpg'):
	print "encryptionpassphrase is specified but gpg executable not found, please install gpg"
	sys.exit(1)

for c in ctb.coins:
	filename = "%s/wallet_%s_%s.dat" % (sys.argv[1], ctb.conf.coins[c].unit, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

	print "Backing up %s wallet to %s..." % (ctb.conf.coins[c].name, filename)
	ctb.coins[c].conn.backupwallet(filename)

	print "Compressing..."
        os.popen("gzip --best %s" % filename)
	filename += '.gz'

	try:
		print "Encrypting..."
		os.popen("gpg --batch --passphrase '%s' -c %s" % (ctb.conf.misc.backup.encryptionpassphrase, filename))
		os.popen("rm -f %s" % filename)
		filename += '.gpg'
	except AttributeError:
		print "Not encrypting"

	if len(sys.argv) == 3:
		print "Calling rsync..."
		os.popen("rsync -urltv %s %s" % (filename, sys.argv[2]))

########NEW FILE########
__FILENAME__ = _update_stats
"""
    This file is part of ALTcointip.

    ALTcointip is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ALTcointip is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ALTcointip.  If not, see <http://www.gnu.org/licenses/>.
"""

import cointipbot, logging
from ctb import ctb_stats

logging.basicConfig()
lg = logging.getLogger('cointipbot')
lg.setLevel(logging.DEBUG)

ctb = cointipbot.CointipBot(self_checks=False, init_reddit=True, init_coins=False, init_exchanges=False, init_db=True, init_logging=False)

# Update stats page
result = ctb_stats.update_stats(ctb=ctb)
lg.debug(result)

# Update tips page
result = ctb_stats.update_tips(ctb=ctb)
lg.debug(result)

# This isn't needed because it happens during the tip processing
#result = ctb_stats.update_all_user_stats(ctb=ctb)
#lg.debug(result)

########NEW FILE########
