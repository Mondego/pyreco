__FILENAME__ = dumpmon
# dumpmon.py
# Author: Jordan Wright
# Version: 0.0 (in dev)

# ---------------------------------------------------
# To Do:
#
#	- Refine Regex
#	- Create/Keep track of statistics

from lib.regexes import regexes
from lib.Pastebin import Pastebin, PastebinPaste
from lib.Slexy import Slexy, SlexyPaste
from lib.Pastie import Pastie, PastiePaste
from lib.helper import log
from time import sleep
from twitter import Twitter, OAuth
from settings import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, log_file
import threading
import logging


def monitor():
    '''
    monitor() - Main function... creates and starts threads

    '''
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="more verbose", action="store_true")
    args = parser.parse_args()
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s', filename=log_file, level=level)
    logging.info('Monitoring...')
    bot = Twitter(
        auth=OAuth(ACCESS_TOKEN, ACCESS_TOKEN_SECRET,
            CONSUMER_KEY, CONSUMER_SECRET)
        )
    # Create lock for both output log and tweet action
    log_lock = threading.Lock()
    tweet_lock = threading.Lock()

    pastebin_thread = threading.Thread(
        target=Pastebin().monitor, args=[bot, tweet_lock])
    slexy_thread = threading.Thread(
        target=Slexy().monitor, args=[bot, tweet_lock])
    pastie_thead = threading.Thread(
        target=Pastie().monitor, args=[bot, tweet_lock])

    for thread in (pastebin_thread, slexy_thread, pastie_thead):
        thread.daemon = True
        thread.start()

    # Let threads run
    try:
        while(1):
            sleep(5)
    except KeyboardInterrupt:
        logging.warn('Stopped.')


if __name__ == "__main__":
    monitor()

########NEW FILE########
__FILENAME__ = helper
'''
helper.py - provides misc. helper functions
Author: Jordan

'''

import requests
import settings
from time import sleep, strftime
import logging


r = requests.Session()


def download(url, headers=None):
    if not headers:
        headers = None
    if headers:
        r.headers.update(headers)
    try:
        response = r.get(url).text
    except requests.ConnectionError:
        logging.warn('[!] Critical Error - Cannot connect to site')
        sleep(5)
        logging.warn('[!] Retrying...')
        response = download(url)
    return response


def log(text):
    '''
    log(text): Logs message to both STDOUT and to .output_log file

    '''
    print(text)
    with open(settings.log_file, 'a') as logfile:
        logfile.write(text + '\n')


def build_tweet(paste):
    '''
    build_tweet(url, paste) - Determines if the paste is interesting and, if so, builds and returns the tweet accordingly

    '''
    tweet = None
    if paste.match():
        tweet = paste.url
        if paste.type == 'db_dump':
            if paste.num_emails > 0:
                tweet += ' Emails: ' + str(paste.num_emails)
            if paste.num_hashes > 0:
                tweet += ' Hashes: ' + str(paste.num_hashes)
            if paste.num_hashes > 0 and paste.num_emails > 0:
                tweet += ' E/H: ' + str(round(
                    paste.num_emails / float(paste.num_hashes), 2))
            tweet += ' Keywords: ' + str(paste.db_keywords)
        elif paste.type == 'google_api':
            tweet += ' Found possible Google API key(s)'
        elif paste.type in ['cisco', 'juniper']:
            tweet += ' Possible ' + paste.type + ' configuration'
        elif paste.type == 'ssh_private':
            tweet += ' Possible SSH private key'
        elif paste.type == 'honeypot':
            tweet += ' Dionaea Honeypot Log'
        tweet += ' #infoleak'
    if paste.num_emails > 0:
        print(paste.emails)
    return tweet

########NEW FILE########
__FILENAME__ = Paste
from .regexes import regexes
import settings
import logging
import re

class Paste(object):
    def __init__(self):
        '''
        class Paste: Generic "Paste" object to contain attributes of a standard paste

        '''
        self.emails = 0
        self.hashes = 0
        self.num_emails = 0
        self.num_hashes = 0
        self.text = None
        self.type = None
        self.sites = None
        self.db_keywords = 0.0

    def match(self):
        '''
        Matches the paste against a series of regular expressions to determine if the paste is 'interesting'

        Sets the following attributes:
                self.emails
                self.hashes
                self.num_emails
                self.num_hashes
                self.db_keywords
                self.type

        '''
        # Get the amount of emails
        self.emails = list(set(regexes['email'].findall(self.text)))
        self.hashes = regexes['hash32'].findall(self.text)
        self.num_emails = len(self.emails)
        self.num_hashes = len(self.hashes)
        if self.num_emails > 0:
            self.sites = list(set([re.search('@(.*)$', email).group(1).lower() for email in self.emails]))
        for regex in regexes['db_keywords']:
            if regex.search(self.text):
                logging.debug('\t[+] ' + regex.search(self.text).group(1))
                self.db_keywords += round(1/float(
                    len(regexes['db_keywords'])), 2)
        for regex in regexes['blacklist']:
            if regex.search(self.text):
                logging.debug('\t[-] ' + regex.search(self.text).group(1))
                self.db_keywords -= round(1.25 * (
                    1/float(len(regexes['db_keywords']))), 2)
        if (self.num_emails >= settings.EMAIL_THRESHOLD) or (self.num_hashes >= settings.HASH_THRESHOLD) or (self.db_keywords >= settings.DB_KEYWORDS_THRESHOLD):
            self.type = 'db_dump'
        if regexes['cisco_hash'].search(self.text) or regexes['cisco_pass'].search(self.text):
            self.type = 'cisco'
        if regexes['honeypot'].search(self.text):
            self.type = 'honeypot'
        if regexes['google_api'].search(self.text):
            self.type = 'google_api'
        # if regexes['juniper'].search(self.text): self.type = 'Juniper'
        for regex in regexes['banlist']:
            if regex.search(self.text):
                self.type = None
                break
        return self.type

########NEW FILE########
__FILENAME__ = Pastebin
from .Site import Site
from .Paste import Paste
from bs4 import BeautifulSoup
from . import helper
from time import sleep
from settings import SLEEP_PASTEBIN
from twitter import TwitterError
import logging


class PastebinPaste(Paste):
    def __init__(self, id):
        self.id = id
        self.headers = None
        self.url = 'http://pastebin.com/raw.php?i=' + self.id
        super(PastebinPaste, self).__init__()


class Pastebin(Site):
    def __init__(self, last_id=None):
        if not last_id:
            last_id = None
        self.ref_id = last_id
        self.BASE_URL = 'http://pastebin.com'
        self.sleep = SLEEP_PASTEBIN
        super(Pastebin, self).__init__()

    def update(self):
        '''update(self) - Fill Queue with new Pastebin IDs'''
        logging.info('Retrieving Pastebin ID\'s')
        results = BeautifulSoup(helper.download(self.BASE_URL + '/archive')).find_all(
            lambda tag: tag.name == 'td' and tag.a and '/archive/' not in tag.a['href'] and tag.a['href'][1:])
        new_pastes = []
        if not self.ref_id:
            results = results[:60]
        for entry in results:
            paste = PastebinPaste(entry.a['href'][1:])
            # Check to see if we found our last checked URL
            if paste.id == self.ref_id:
                break
            new_pastes.append(paste)
        for entry in new_pastes[::-1]:
            logging.info('Adding URL: ' + entry.url)
            self.put(entry)
    def get_paste_text(self, paste):
        return helper.download(paste.url)

########NEW FILE########
__FILENAME__ = Pastie
from .Site import Site
from .Paste import Paste
from bs4 import BeautifulSoup
from . import helper
from time import sleep
from settings import SLEEP_PASTIE
from twitter import TwitterError
import logging


class PastiePaste(Paste):
    def __init__(self, id):
        self.id = id
        self.headers = None
        self.url = 'http://pastie.org/pastes/' + self.id + '/text'
        super(PastiePaste, self).__init__()


class Pastie(Site):
    def __init__(self, last_id=None):
        if not last_id:
            last_id = None
        self.ref_id = last_id
        self.BASE_URL = 'http://pastie.org'
        self.sleep = SLEEP_PASTIE
        super(Pastie, self).__init__()

    def update(self):
        '''update(self) - Fill Queue with new Pastie IDs'''
        logging.info('Retrieving Pastie ID\'s')
        results = [tag for tag in BeautifulSoup(helper.download(
            self.BASE_URL + '/pastes')).find_all('p', 'link') if tag.a]
        new_pastes = []
        if not self.ref_id:
            results = results[:60]
        for entry in results:
            paste = PastiePaste(entry.a['href'].replace(
                self.BASE_URL + '/pastes/', ''))
            # Check to see if we found our last checked URL
            if paste.id == self.ref_id:
                break
            new_pastes.append(paste)
        for entry in new_pastes[::-1]:
            logging.debug('Adding URL: ' + entry.url)
            self.put(entry)

    def get_paste_text(self, paste):
        return BeautifulSoup(helper.download(paste.url)).pre.text
########NEW FILE########
__FILENAME__ = regexes
import re

regexes = {
    'email': re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}', re.I),
    #'ssn' : re.compile(r'\d{3}-?\d{2}-?\d{4}'),
    'hash32': re.compile(r'[^<A-F\d/]([A-F\d]{32})[^A-F\d]', re.I),
    'FFF': re.compile(r'FBI\s*Friday', re.I),  # will need to work on this to not match CSS
    'lulz': re.compile(r'(lulzsec|antisec)', re.I),
    'cisco_hash': re.compile(r'enable\s+secret', re.I),
    'cisco_pass': re.compile(r'enable\s+password', re.I),
    'google_api': re.compile(r'\W(AIza.{35})'),
    'honeypot': re.compile(r'<dionaea\.capture>', re.I),
    'db_keywords': [
    re.compile(
    r'((customers?|email|users?|members?|acc(?:oun)?ts?)([-_|/\s]?(address|name|id[^")a-zA-Z0-9_]|[-_:|/\\])))', re.I),
        re.compile(
            r'((\W?pass(wor)?d|hash)[\s|:])', re.I),
        re.compile(
            r'((\btarget|\bsite)\s*?:?\s*?(([a-z][\w-]+:/{1,3})?([-\w\s_/]+\.)*[\w=/?%]+))', re.I),  # very basic URL check - may be improved later
        re.compile(
            r'(my\s?sql[^i_\.]|sql\s*server)', re.I),
        re.compile(
            r'((host|target)[-_\s]+ip:)', re.I),
        re.compile(
            r'(data[-_\s]*base|\Wdb)', re.I),  # added the non-word char before db.. we'll see if that helps
        re.compile(r'(table\s*?:)', re.I),
        re.compile(
            r'((available|current)\s*(databases?|dbs?)\W)', re.I),
        re.compile(r'(hacked\s*by)', re.I)
    ],
    'blacklist': [  # I was hoping to not have to make a blacklist, but it looks like I don't really have a choice
    re.compile(
    r'(select\s+.*?from|join|declare\s+.*?\s+as\s+|update.*?set|insert.*?into)', re.I),  # SQL
        re.compile(
            r'(define\(.*?\)|require_once\(.*?\))', re.I),  # PHP
        re.compile(
            r'(function.*?\(.*?\))', re.I),
        re.compile(
            r'(Configuration(\.Factory|\s*file))', re.I),
        re.compile(
            r'((border|background)-color)', re.I),  # Basic CSS (Will need to be improved)
        re.compile(
            r'(Traceback \(most recent call last\))', re.I),
        re.compile(
            r'(java\.(util|lang|io))', re.I),
        re.compile(r'(sqlserver\.jdbc)', re.I)
    ],
    # The banlist is the list of regexes that are found in crash reports
    'banlist': [
        re.compile(r'faf\.fa\.proxies', re.I),
        re.compile(r'Technic Launcher is starting', re.I),
        re.compile(r'OTL logfile created on', re.I),
        re.compile(r'RO Game Client crashed!', re.I),
        re.compile(r'Selecting PSO2 Directory', re.I),
        re.compile(r'TDSS Rootkit', re.I),
        re.compile(r'SysInfoCrashReporterKey', re.I),
        re.compile(r'Current OS Full name: ', re.I),
        re.compile(r'Multi Theft Auto: ', re.I),
        re.compile(r'Initializing cgroup subsys cpuset', re.I),
        re.compile(r'Init vk network', re.I),
        re.compile(r'MediaTomb UPnP Server', re.I)
    ]
}

########NEW FILE########
__FILENAME__ = Site
from Queue import Queue
import requests
import time
import re
from pymongo import MongoClient
from requests import ConnectionError
from twitter import TwitterError
from settings import USE_DB, DB_HOST, DB_PORT
import logging
import helper


class Site(object):
    '''
    Site - parent class used for a generic
    'Queue' structure with a few helper methods
    and features. Implements the following methods:

            empty() - Is the Queue empty
            get(): Get the next item in the queue
            put(item): Puts an item in the queue
            tail(): Shows the last item in the queue
            peek(): Shows the next item in the queue
            length(): Returns the length of the queue
            clear(): Clears the queue
            list(): Lists the contents of the Queue
            download(url): Returns the content from the URL

    '''
    # I would have used the built-in queue, but there is no support for a peek() method
    # that I could find... So, I decided to implement my own queue with a few
    # changes
    def __init__(self, queue=None):
        if queue is None:
            self.queue = []
        if USE_DB:
            # Lazily create the db and collection if not present
            self.db_client = MongoClient(DB_HOST, DB_PORT).paste_db.pastes


    def empty(self):
        return len(self.queue) == 0

    def get(self):
        if not self.empty():
            result = self.queue[0]
            del self.queue[0]
        else:
            result = None
        return result

    def put(self, item):
        self.queue.append(item)

    def peek(self):
        return self.queue[0] if not self.empty() else None

    def tail(self):
        return self.queue[-1] if not self.empty() else None

    def length(self):
        return len(self.queue)

    def clear(self):
        self.queue = []

    def list(self):
        print('\n'.join(url for url in self.queue))

    def monitor(self, bot, t_lock):
        self.update()
        while(1):
            while not self.empty():
                paste = self.get()
                self.ref_id = paste.id
                logging.info('[*] Checking ' + paste.url)
                paste.text = self.get_paste_text(paste)
                tweet = helper.build_tweet(paste)
                if tweet:
                    logging.info(tweet)
                    with t_lock:
                        if USE_DB:
                            self.db_client.save({
                                'pid' : paste.id,
                                'text' : paste.text,
                                'emails' : paste.emails,
                                'hashes' : paste.hashes,
                                'num_emails' : paste.num_emails,
                                'num_hashes' : paste.num_hashes,
                                'type' : paste.type,
                                'db_keywords' : paste.db_keywords,
                                'url' : paste.url
                               })
                        try:
                            bot.statuses.update(status=tweet)
                        except TwitterError:
                            pass
            self.update()
            while self.empty():
                logging.debug('[*] No results... sleeping')
                time.sleep(self.sleep)
                self.update()

########NEW FILE########
__FILENAME__ = Slexy
from .Site import Site
from .Paste import Paste
from bs4 import BeautifulSoup
from . import helper
from time import sleep
from settings import SLEEP_SLEXY
from twitter import TwitterError
import logging


class SlexyPaste(Paste):
    def __init__(self, id):
        self.id = id
        self.headers = {'Referer': 'http://slexy.org/view/' + self.id}
        self.url = 'http://slexy.org/raw/' + self.id
        super(SlexyPaste, self).__init__()


class Slexy(Site):
    def __init__(self, last_id=None):
        if not last_id:
            last_id = None
        self.ref_id = last_id
        self.BASE_URL = 'http://slexy.org'
        self.sleep = SLEEP_SLEXY
        super(Slexy, self).__init__()

    def update(self):
        '''update(self) - Fill Queue with new Slexy IDs'''
        logging.info('[*] Retrieving Slexy ID\'s')
        results = BeautifulSoup(helper.download(self.BASE_URL + '/recent')).find_all(
            lambda tag: tag.name == 'td' and tag.a and '/view/' in tag.a['href'])
        new_pastes = []
        if not self.ref_id:
            results = results[:60]
        for entry in results:
            paste = SlexyPaste(entry.a['href'].replace('/view/', ''))
            # Check to see if we found our last checked URL
            if paste.id == self.ref_id:
                break
            new_pastes.append(paste)
        for entry in new_pastes[::-1]:
            logging.info('[+] Adding URL: ' + entry.url)
            self.put(entry)

    def get_paste_text(self, paste):
        return helper.download(paste.url, paste.headers)

########NEW FILE########
