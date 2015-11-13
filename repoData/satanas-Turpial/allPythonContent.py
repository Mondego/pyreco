__FILENAME__ = main
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Turpial
#
# Author: Wil Alvarez (aka Satanas)
# Oct 7, 2011

import os
import sys
import logging
import subprocess

from optparse import OptionParser, SUPPRESS_HELP

from turpial import DESC
from turpial.ui import util

from libturpial.api.core import Core
from libturpial.common.tools import *
from libturpial import VERSION as LIBTURPIAL_VERSION

LOG_FMT = logging.Formatter('[%(asctime)s] [%(name)s::%(levelname)s] %(message)s', '%Y%m%d-%H:%M')


class Turpial:
    def __init__(self):
        parser = OptParser()
        parser.add_option('-d', '--debug', dest='debug', action='store_true',
            help='show debug info in shell during execution', default=False)
        parser.add_option('-i', '--interface', dest='interface',
            help='select interface to use. Available: %s' % util.available_interfaces(),
            default=util.DEFAULT_INTERFACE)
        parser.add_option('-c', '--clean', dest='clean', action='store_true',
            help='clean all bytecodes', default=False)
        parser.add_option('--version', dest='version', action='store_true',
            help='show the version of Turpial and exit', default=False)
        parser.add_option('-s', dest='mac', action='store_true', default=False,
            help=SUPPRESS_HELP)
        parser.add_option('-p', dest='mac', action='store_true', default=False,
            help=SUPPRESS_HELP)

        (options, args) = parser.parse_args()

        if not options.mac and parser.failed:
            parser.print_help()
            sys.exit(-2)

        self.interface = options.interface

        if options.debug or options.clean:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self.log = logging.getLogger('Controller')
        #handler = logging.StreamHandler()
        #handler.setFormatter(LOG_FMT)
        #self.log.addHandler(handler)

        if options.clean:
            clean_bytecodes(__file__, self.log)
            sys.exit(0)

        # TODO: Override with any configurated value
        if options.interface in util.INTERFACES.keys():
            self.ui = util.INTERFACES[options.interface](debug=options.debug)
        else:
            print "'%s' is not a valid interface. Availables interfaces are %s" % (
            options.interface, util.available_interfaces())
            sys.exit(-1)

        if options.version:
            print DESC
            print "libturpial v%s" % LIBTURPIAL_VERSION
            print "Python v%X" % sys.hexversion
            sys.exit(0)


        self.log.debug('Starting %s' % DESC)

        self.ui.show_main()
        try:
            self.ui.main_loop()
        except KeyboardInterrupt:
            self.log.debug('Intercepted Keyboard Interrupt')
            self.ui.main_quit()

class OptParser(OptionParser):
    def __init__(self):
        OptionParser.__init__(self)
        self.failed = False

    def error(self, error):
        print error
        self.failed = True

    def exit(self):
        pass

def main():
    #try:
    #    subprocess.call(['turpial-unity-daemon', 'stop'])
    #    subprocess.call(['turpial-unity-daemon', 'start'])
    #except:
    #    pass
    t = Turpial()
    #try:
    #    subprocess.call(['turpial-unity-daemon', 'stop'])
    #except:
    #    pass

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = singleton
# -*- coding: utf-8 -*-

# Singleton for Turpial
#
# Author: Wil Alvarez (aka Satanas)
# Dic 20, 2011

import os
import sys
import logging
import tempfile

from libturpial.common.tools import *

if detect_os() == OS_LINUX:
    import fcntl

class Singleton:
    def __init__(self, pid_name='turpial.pid'):
        self.fd = None
        self.log = logging.getLogger('Sys')
        self.filepath = os.path.abspath(os.path.join(tempfile.gettempdir(), pid_name))

        if detect_os() == OS_LINUX:
            self.fd = open(self.filepath, 'w')
            try:
                fcntl.lockf(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                self.__exit()
        elif detect_os() == OS_WINDOWS:
            try:
                # If file already exists, we try to remove it (in case previous
                # execution was interrupted)
                if os.path.exists(self.filepath):
                    os.unlink(self.filepath)
                self.fd = os.open(self.filepath, os.O_CREAT|os.O_EXCL|os.O_RDWR)
            except OSError, err:
                if err.errno == 13:
                    self.__exit()

    def __del__(self):
        if detect_os() == OS_WINDOWS:
            if self.fd:
                os.close(self.fd)
                os.unlink(self.filepath)

    def __exit(self):
        self.log.error("Another instance is already running")
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

# Base class for all the Turpial interfaces
#
# Author: Wil Alvarez (aka Satanas)
# Oct 09, 2011

import os
import time

from turpial.ui.lang import i18n
from turpial.singleton import Singleton

from libturpial.common import OS_MAC
from libturpial.common.tools import detect_os

MIN_WINDOW_WIDTH = 250
BROADCAST_ACCOUNT = 'broadcast'

class Base(Singleton):
    ACTION_REPEAT = 'repeat'
    ACTION_UNREPEAT = 'unrepeat'
    ACTION_FAVORITE = 'favorite'
    ACTION_UNFAVORITE = 'unfavorite'

    '''Parent class for every UI interface'''
    def __init__(self):
        Singleton.__init__(self, 'turpial.pid')

        self.images_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), '..', 'data', 'pixmaps'))
        self.sounds_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), '..', 'data', 'sounds'))
        self.fonts_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), '..', 'data', 'fonts'))
        # Keep a list of installed app fonts to ease registration
        # in the toolkit side
        self.fonts = [
            os.path.join(self.fonts_path, f)
            for f in os.listdir(self.fonts_path)
        ]

        self.home_path = os.path.expanduser('~')

        if detect_os() == OS_MAC:
            self.command_key_shortcut = u'⌘'
            self.command_separator = ''
        else:
            self.command_key_shortcut = 'Ctrl'
            self.command_separator = '+'

        self.bgcolor = "#363636"
        self.fgcolor = "#fff"

        # Unity integration
        #self.unitylauncher = UnityLauncherFactory().create();
        #self.unitylauncher.add_quicklist_button(self.show_update_box, i18n.get('new_tweet'), True)
        #self.unitylauncher.add_quicklist_checkbox(self.sound.disable, i18n.get('enable_sounds'), True, not self.sound._disable)
        #self.unitylauncher.add_quicklist_button(self.show_update_box_for_direct, i18n.get('direct_message'), True)
        #self.unitylauncher.add_quicklist_button(self.show_accounts_dialog, i18n.get('accounts'), True)
        #self.unitylauncher.add_quicklist_button(self.show_preferences, i18n.get('preferences'), True)
        #self.unitylauncher.add_quicklist_button(self.main_quit, i18n.get('exit'), True)
        #self.unitylauncher.show_menu()

    # TODO: Put this in util.py
    def humanize_size(self, size, unit='B', decimals=2):
        if size == 0:
            rtn = '0 %s' % unit
            return rtn.strip()

        prefix = ''
        kbsize = size / 1024
        if kbsize > 0:
            mbsize = kbsize / 1024
            if mbsize > 0:
                gbsize = mbsize / 1024
                if gbsize > 0:
                    prefix = 'G'
                    amount = mbsize / 1024.0
                else:
                    prefix = 'M'
                    amount = kbsize / 1024.0
            else:
                prefix = 'K'
                amount = size / 1024.0
        else:
            amount = size

        if (prefix != ''):
            amount = round(amount, decimals)

        rtn = "%s %s%s" % (amount, prefix, unit)
        return rtn.strip()

    def humanize_timestamp(self, status_timestamp):
        now = time.time()
        # FIXME: Workaround to fix the timestamp
        offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        seconds = now - status_timestamp + offset

        minutes = seconds / 60.0
        if minutes < 1.0:
            timestamp = i18n.get('now')
        else:
            if minutes < 60.0:
                timestamp = "%i m" % minutes
            else:
                hours = minutes / 60.0
                if hours < 24.0:
                    timestamp = "%i h" % hours
                else:
                    dt = time.localtime(status_timestamp)
                    month = time.strftime(u'%b', dt)
                    year = dt.tm_year

                    if year == time.localtime(now).tm_year:
                        timestamp = u"%i %s" % (dt.tm_mday, month)
                    else:
                        timestamp = u"%i %s %i" % (dt.tm_mday, month, year)
        return timestamp

    def humanize_time_intervals(self, interval):
        if interval > 1:
            unit = i18n.get('minutes')
        else:
            unit = i18n.get('minute')
        return " ".join([str(interval), unit])

    def get_shortcut_string(self, key, modifier=None):
        if modifier:
            return self.command_separator.join([self.command_key_shortcut, modifier, key])
        else:
            return self.command_separator.join([self.command_key_shortcut, key])

    def get_error_message_from_response(self, response, default=None):
        if response is None:
            return default

        if 'errors' in response:
            if 'message' in reponse['errors']:
                msg = response['errors']['message']
                if msg.find('Rate limit exceeded') >= 0:
                    return i18n.get('rate_limit_exceeded')
                elif msg.find('you are not authorized to see') >= 0:
                    return i18n.get('not_authorized_to_see_status')
        return default

    #================================================================
    # Common methods to all interfaces
    #================================================================

    #================================================================
    # Methods to override
    #================================================================

    def main_loop(self):
        raise NotImplementedError

    def main_quit(self, widget=None, force=False):
        raise NotImplementedError

    def show_main(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

"""Shell interface for Turpial"""
#
# Author: Wil Alvarez (aka Satanas)
# 26 Jun, 2011

import cmd
import getpass
import logging

VERSION = '2.0'

INTRO = [
    'Welcome to Turpial (shell mode).', 
    'Type "help" to get a list of available commands.',
    'Type "help <command>" to get a detailed help about that command'
]

ARGUMENTS = {
    'account': ['add', 'edit', 'delete', 'list', 'change', 'default'],
    'status': ['update', 'reply', 'delete', 'conversation'],
    'profile': ['me', 'user', 'update'],
    'friend': ['list', 'follow', 'unfollow', 'block', 'unblock', 'spammer',
        'check'],
    'direct': ['send', 'delete'],
    'favorite': ['mark', 'unmark'],
}

class Main(cmd.Cmd):
    def __init__(self, core):
        cmd.Cmd.__init__(self)
        
        self.log = logging.getLogger('Turpial:CMD')
        self.prompt = 'turpial> '
        self.intro = '\n'.join(INTRO)
        self.core = core
        self.account = None
        
    def show_main(self):
        pass
        
    def main_loop(self):
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            self.do_exit()
        except EOFError:
            self.do_exit()
    
    def __validate_index(self, index, array, blank=False):
        try:
            a = array[int(index)]
            return True
        except IndexError:
            return False
        except ValueError:
            if blank and index == '':
                return True
            elif not blank and index == '':
                return False
            elif blank and index != '':
                return False
        except TypeError:
            if index is None:
                return False
    
    def __validate_accounts(self):
        if len(self.core.list_accounts()) > 0:
            return True
        print "You don't have any registered account. Run 'account add' command"
        return False
    
    def __validate_default_account(self):
        if self.account:
            return True
        print "You don't have a default account. Run 'account change' command"
        return False
        
    def __validate_arguments(self, arg_array, value):
        if value in arg_array:
            return True
        else:
            print 'Invalid Argument'
            return False
    
    def __build_message_menu(self):
        text = raw_input('Message: ')
        if text == '':
            print 'You must write something to post'
            return None
        
        if len(text) > 140:
            trunc = raw_input ('Your message has more than 140 characters. Do you want truncate it? [Y/n]: ')
            if trunc.lower() == 'y' or trunc == '':
                return text[:140]
            return None
        return text
    
    def __build_accounts_menu(self, _all=False):
        if len(self.core.list_accounts()) == 1: 
            return self.core.list_accounts()[0]
        
        index = None
        while 1:
            accounts = self.__show_accounts()
            if _all:
                index = raw_input('Select account (or Enter for all): ')
            else:
                index = raw_input('Select account: ')
            if not self.__validate_index(index, accounts, _all):
                print "Invalid account"
            else:
                break
        if index == '':
            return ''
        else:
            return accounts[int(index)]
    
    def __build_password_menu(self, account):
        passwd = None
        while 1:
            passwd = getpass.unix_getpass("Password for '%s' in '%s': " % (
                account.split('-')[0], account.split('-')[1]))
            if passwd:
                return passwd
            else:
                print "Password can't be blank"
            
    def __build_change_account_menu(self):
        if len(self.core.list_accounts()) == 1:
            if self.account:
                print "Your unique account is already your default"
            else:
                self.__add_first_account_as_default()
        elif len(self.core.list_accounts()) > 1:
            while 1:
                accounts = self.__show_accounts()
                index = raw_input('Select you new default account (or Enter for keep current): ')
                if index == '':
                    print "Default account remain with no changes"
                    return True
                if not self.__validate_index(index, accounts):
                    print "Invalid account"
                else:
                    break
            self.account = accounts[int(index)]
            print "Set %s in %s as your new default account" % (
                self.account.split('-')[0], self.account.split('-')[1])
        
    def __build_protocols_menu(self):
        index = None
        protocols = self.core.list_protocols()
        while 1:
            print "Available protocols:"
            for i in range(len(protocols)):
                print "[%i] %s" % (i, protocols[i])
            index = raw_input('Select protocol: ')
            if not self.__validate_index(index, protocols):
                print "Invalid protocol"
            else:
                break
        return protocols[int(index)]
    
    def __build_confirm_menu(self, message):
        confirm = raw_input(message + ' [y/N]: ')
        if confirm.lower() == 'y':
            return True
        else:
            return False
            
    def __user_input(self, message, blank=False):
        while 1:
            text = raw_input(message)
            if text == '' and not blank:
                print "You can't leave this field blank"
                continue
            break
        return text
        
    def __add_first_account_as_default(self):
        self.account = self.core.list_accounts()[0]
        print "Selected account %s in %s as default (*)" % (
            self.account.split('-')[0], self.account.split('-')[1])
    
    def __show_accounts(self):
        if len(self.core.list_accounts()) == 0:
            print "There are no registered accounts"
            return
        
        accounts = []
        print "Available accounts:"
        for acc in self.core.list_accounts():
            ch = ''
            if acc == self.account:
                ch = ' (*)'
            print "[%i] %s - %s%s" % (len(accounts), acc.split('-')[0], acc.split('-')[1], ch)
            accounts.append(acc)
        return accounts
        
    def __show_profiles(self, people):
        if not statuses:
            print "There are no profiles to show"
            return

        if people.code > 0: 
            print people.errmsg
            return
        
        for p in people:
            protected = '<protected>' if p.protected else ''
            following = '<following>' if p.following else ''
            
            header = "@%s (%s) %s %s" % (p.username, p.fullname, 
                following, protected)
            print header
            print '-' * len(header)
            print "URL: %s" % p.url
            print "Location: %s" % p.location
            print "Bio: %s" % p.bio
            if p.last_update: 
                print "Last: %s" % p.last_update
            print ''
    
    def __show_statuses(self, statuses):
        if not statuses:
            print "There are no statuses to show"
            return
        
        if statuses.code > 0:
            print statuses.errmsg
            return
        
        count = 1
        for status in statuses:
            text = status.text.replace('\n', ' ')
            inreply = ''
            client = ''
            if status.in_reply_to_user:
                inreply = ' in reply to %s' % status.in_reply_to_user
            if status.source:
                client = ' from %s' % status.source.name
            print "%d. @%s: %s (id: %s)" % (count, status.username, text, status.id_)
            print "%s%s%s" % (status.datetime, client, inreply)
            if status.reposted_by:
                users = ''
                for u in status.reposted_by:
                    users += u + ' '
                print 'Retweeted by %s' % status.reposted_by
            print
            count += 1
    
    def __process_login(self, acc):
        if not self.core.has_stored_passwd(acc):
            passwd = self.__build_password_menu(acc)
            username = acc.split('-')[0]
            protocol = acc.split('-')[1]
            self.core.register_account(username, protocol, passwd)
        
        rtn = self.core.login(acc)
        if rtn.code > 0:
            print rtn.errmsg
            return
        
        auth_obj = rtn.items
        if auth_obj.must_auth():
            print "Please visit %s, authorize Turpial and type the pin returned" % auth_obj.url
            pin = self.__user_input('Pin: ')
            self.core.authorize_oauth_token(acc, pin)
        
        rtn = self.core.auth(acc)
        if rtn.code > 0:
            print rtn.errmsg
        else:
            print 'Logged in with account %s' % acc.split('-')[0]
        
    def default(self, line):
        print '\n'.join(['Command not found.', INTRO[1], INTRO[2]])
        
    def emptyline(self):
        pass
    
    def do_account(self, arg):
        if not self.__validate_arguments(ARGUMENTS['account'], arg): 
            self.help_account(False)
            return False
        
        if arg == 'add':
            username = raw_input('Username: ')
            password = getpass.unix_getpass('Password: ')
            remember = self.__build_confirm_menu('Remember password')
            protocol = self.__build_protocols_menu()
            acc_id = self.core.register_account(username, protocol, password, remember)
            print 'Account added'
            if len(self.core.list_accounts()) == 1: 
                self.__add_first_account_as_default()
        elif arg == 'edit':
            if not self.__validate_default_account(): 
                return False
            password = getpass.unix_getpass('New Password: ')
            username = self.account.split('-')[0]
            protocol = self.account.split('-')[1]
            remember = self.__build_confirm_menu('Remember password')
            self.core.register_account(username, protocol, password, remember)
            print 'Account edited'
        elif arg == 'delete':
            if not self.__validate_accounts(): 
                return False
            account = self.__build_accounts_menu()
            conf = self.__build_confirm_menu('Do you want to delete account %s?' %
                account)
            if not conf:
                print 'Command cancelled'
                return False
            del_all = self.__build_confirm_menu('Do you want to delete all data?')
            self.core.unregister_account(account, del_all)
            if self.account == account:
                self.account = None
            print 'Account deleted'
        elif arg == 'change':
            if not self.__validate_accounts():
                return False
            self.__build_change_account_menu()
        elif arg == 'list':
            self.__show_accounts()
        elif arg == 'default':
            print "Your default account is %s in %s" % (
                self.account.split('-')[0], self.account.split('-')[1])
    
    def help_account(self, desc=True):
        text = 'Manage user accounts'
        if not desc:
            text = ''
        print '\n'.join([text,
            'Usage: account <arg>\n',
            'Possible arguments are:',
            '  add:\t\t Add a new user account',
            '  edit:\t\t Edit an existing user account',
            '  delete:\t Delete a user account',
            '  list:\t\t Show all registered accounts',
            '  default:\t Show default account',
        ])
    
    def do_login(self, arg):
        if not self.__validate_accounts(): 
            return False
        
        _all = True
        if len(self.core.list_accounts()) > 1:
            _all = self.__build_confirm_menu('Do you want to login with all available accounts?')
        
        if _all:
            work = False
            for acc in self.core.list_accounts():
                if self.core.is_account_logged_in(acc):
                    continue
                work = True
                self.__process_login(acc)
            if not work:
                print "Already logged in with all available accounts"
        else:
            acc = self.__build_accounts_menu()
            self.__process_login(acc)
    
    def help_login(self):
        print 'Login with one or many accounts'
    
    def do_profile(self, arg):
        if not self.__validate_arguments(ARGUMENTS['profile'], arg): 
            self.help_profile(False)
            return False
        
        if not self.__validate_default_account(): 
            return False
        
        if arg == 'me':
            profile = self.core.get_own_profile(self.account)
            if profile is None:
                print 'You must be logged in'
            else:
                self.__show_profiles(profile)
        elif arg == 'user':
            username = raw_input('Type the username: ')
            if username == '':
                print 'You must specify a username'
                return False
            profile = self.core.get_user_profile(self.account, username)
            if profile is None:
                print 'You must be logged in'
            else:
                self.__show_profiles(profile)
        elif arg == 'update':
            args = {}
            name = raw_input('Type your name (ENTER for none): ')
            bio = raw_input('Type your bio (ENTER for none): ')
            url = raw_input('Type your url (ENTER for none): ')
            location = raw_input('Type your location (ENTER for none): ')
            
            if name != '':
                args['name'] = name
            if bio != '':
                args['description'] = bio
            if url != '':
                args['url'] = url
            if location != '':
                args['location'] = location
            result = self.core.update_profile(self.account, args)
            
            if result.code > 0: 
                print result.errmsg
            else:
                print 'Profile updated'
    
    def help_profile(self, desc=True):
        text = 'Manage user profile'
        if not desc:
            text = ''
        print '\n'.join([text,
            'Usage: profile <arg>\n',
            'Possible arguments are:',
            '  me:\t\t Show own profile',
            '  user:\t\t Show profile for a specific user',
            '  update:\t Update own profile',
        ])
    
    def do_status(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['status'], arg): 
            self.help_status(False)
            return False
        
        if arg == 'update':
            message = self.__build_message_menu()
            if not message:
                print 'You must to write something'
                return False
            
            broadcast = self.__build_confirm_menu('Do you want to post the message in all available accounts?')
            if broadcast:
                for acc in self.core.list_accounts():
                    rtn = self.core.update_status(acc, message)
                    if rtn.code > 0:
                        print rtn.errmsg
                    else:
                        print 'Message posted in account %s' % acc.split('-')[0]
            else:
                rtn = self.core.update_status(self.account, message)
                if rtn.code > 0:
                    print rtn.errmsg
                else:
                    print 'Message posted in account %s' % self.account.split('-')[0]
        elif arg == 'reply':
            reply_id = raw_input('Status ID: ')
            if reply_id == '':
                print "You must specify a valid id"
                return False
            message = self.__build_message_menu()
            if not message:
                print 'You must to write something'
                return False
            rtn = self.core.update_status(self.account, message, reply_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Reply posted in account %s' % self.account.split('-')[0]
        elif arg == 'delete':
            status_id = raw_input('Status ID: ')
            if status_id == '':
                print "You must specify a valid id"
                return False
            rtn = self.core.destroy_status(self.account, status_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Status deleted'
        elif arg == 'conversation':
            status_id = raw_input('Status ID: ')
            if status_id == '':
                print "You must specify a valid id"
                return False
            rtn = self.core.get_conversation(self.account, status_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                self.__show_statuses(rtn)
    
    def help_status(self, desc=True):
        text = 'Manage statuses for each protocol'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: status <arg>\n',
            'Possible arguments are:',
            '  update:\t Update status ',
            '  delete:\t Delete status',
            '  conversation:\t Show related tweets as conversation',
        ])
    
    def do_column(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        lists = self.core.list_columns_per_account(self.account)
        if arg == '':
            self.help_column(False)
        elif arg == 'list':
            if len(lists) == 0:
                print "No column available. Maybe you need to login"
                return False
            print "Available columns:"
            for li in lists:
                print "  %s" % li
        elif arg == 'public':
            rtn = self.core.get_public_timeline(self.account)
            self.__show_statuses(rtn)
        else:
            if len(lists) == 0:
                print "No column available. Maybe you need to login"
                return False
            if arg in lists:
                rtn = self.core.get_column_statuses(self.account, arg)
                self.__show_statuses(rtn)
            else:
                print "Invalid column '%s'" % arg
    
    def help_column(self, desc=True):
        text = 'Show user columns'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: column <arg>\n',
            'Possible arguments are:',
            '  list:\t\t List all available columns for that account',
            '  timeline:\t Show timeline',
            '  replies:\t Show replies',
            '  directs:\t Show directs messages',
            '  favorites:\t Show statuses marked as favorites',
            '  public:\t Show public timeline',
            '  <list_id>:\t Show statuses for the user list with id <list_id>',
        ])
        
    def do_friend(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['friend'], arg): 
            self.help_friend(False)
            return False
        
        if arg == 'list':
            friends = self.core.get_friends(self.account)
            if friends.code > 0:
                print rtn.errmsg
                return False
            
            if len(friends) == 0:
                print "Hey! What's wrong with you? You've no friends"
                return False
            print "Friends list:"
            for fn in friends:
                print "+ @%s (%s)" % (fn.username, fn.fullname)
        elif arg == 'follow':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.follow(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Following %s" % user
        elif arg == 'unfollow':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.unfollow(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Not following %s" % user
        elif arg == 'block':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.block(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Blocking user %s" % username
        elif arg == 'unblock':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.unblock(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Unblocking user %s" % username
        elif arg == 'spammer':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.report_spam(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            print "Reporting user %s as spammer" % username
        elif arg == 'check':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            rtn = self.core.is_friend(self.account, username)
            if rtn.code > 0:
                print rtn.errmsg
                return False
            if rtn.items:
                print "%s is following you" % username
            else:
                print "%s is not following you" % username
    
    def help_friend(self, desc=True):
        text = 'Manage user friends'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: friend <arg>\n',
            'Possible arguments are:',
            '  list:\t\t List all friends',
            '  follow:\t Follow user',
            '  unfollow:\t Unfollow friend',
            '  block:\t Block user',
            '  unblock:\t Unblock user',
            '  spammer:\t Report user as spammer',
            '  check:\t Verify if certain user is following you',
        ])
    
    def do_direct(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['direct'], arg): 
            self.help_direct(False)
            return False
        
        if arg == 'send':
            username = raw_input('Username: ')
            if username == '':
                print "You must specify a valid user"
                return False
            message = self.__build_message_menu()
            if not message:
                print 'You must to write something'
                return False
            
            rtn = self.core.send_direct(self.account, username, message)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Direct message sent'
        elif arg == 'delete':
            dm_id = raw_input('Direct message ID: ')
            if dm_id == '':
                print "You must specify a valid id"
                return False
            rtn = self.core.destroy_direct(self.account, dm_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Direct message deleted'
    
    def help_direct(self, desc=True):
        text = 'Manage user direct messages'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: direct <arg>\n',
            'Possible arguments are:',
            '  send:\t\t Send direct message',
            '  delete:\t Destroy direct message',
        ])
    
    def do_favorite(self, arg):
        if not self.__validate_default_account(): 
            return False
        
        if not self.__validate_arguments(ARGUMENTS['favorite'], arg): 
            self.help_status(False)
            return False
        
        if arg == 'mark':
            status_id = raw_input('Status ID: ')
            if status_id == '':
                print "You must specify a valid id"
                return False
            rtn = self.core.mark_favorite(self.account, status_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Status marked as favorite'
        elif arg == 'unmark':
            status_id = raw_input('Status ID: ')
            if status_id == '':
                print "You must specify a valid id"
                return False
            rtn = self.core.unmark_favorite(self.account, status_id)
            if rtn.code > 0:
                print rtn.errmsg
            else:
                print 'Status unmarked as favorite'
    
    def help_favorite(self, desc=True):
        text = 'Manage favorite marks of statuses'
        if not desc:
            text = ''
        print '\n'.join([text,
           'Usage: direct <arg>\n',
            'Possible arguments are:',
            '  mark:\t\t Mark a status as favorite',
            '  unmark:\t Remove favorite mark from a status',
        ])
    
    def do_search(self, arg=None):
        if not self.__validate_default_account(): 
            return False
        
        if arg: 
            self.help_search()
            return False
        
        query = raw_input('Type what you want to search for: ')
        rtn = self.core.search(self.account, query)
        self.__show_statuses(rtn)
    
    def help_search(self):
        print 'Search for a pattern'
    
    def do_trends(self, arg=None):
        if not self.__validate_default_account(): 
            return False
        
        if arg: 
            self.help_trends()
            return False
        
        trends = self.core.trends(self.account)
        if trends.code > 0:
            print trends.errmsg
            return False
        
        for trend in trends:
            print trend.title
            print "=" * len(trend.title)
            for topic in trend.items:
                promoted = ''
                if topic.promoted:
                    promoted = '*'
                print "%s%s |" % (topic.name, promoted),
            print
    
    def help_trends(self):
        print 'Show global and local trends'
    
    def do_EOF(self, line):
        return self.do_exit('')
        
    def do_exit(self, line=None):
        print
        self.log.debug('Bye')
        return True
    
    def help_help(self):
        print 'Show help. Dah!'
        
    def help_exit(self):
        print 'Close the application'
    
    def help_EOF(self):
        print 'Close the application'
    
    def show_shorten_url(self, text):
        print "URL Cortada:", text

########NEW FILE########
__FILENAME__ = about
# -*- coding: utf-8 -*-

# Ventana para subir el ego de los desarrolladores de Turpial xD
#
# Author: Wil Alvarez (aka Satanas)
# Dic 21, 2009

import os

from gi.repository import Gtk

from turpial import NAME
from turpial import VERSION
from turpial.ui.lang import i18n

class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent=None):
        Gtk.AboutDialog.__init__(self)
        self.set_logo(parent.load_image('turpial.png', True))
        self.set_name(NAME)
        self.set_version(VERSION)
        self.set_modal(True)
        self.set_copyright('Copyright (C) 2009 - 2012 Wil Alvarez')
        self.set_comments(i18n.get('about_description'))
        self.set_website('http://turpial.org.ve')

        try:
            path = os.path.realpath(os.path.join(os.path.dirname(__file__), 
                '..', '..', '..', 'COPYING'))
            lic = file(path, 'r')
            license = lic.read()
            lic.close()
        except Exception, msg:
            license =  'This script is free software; you can redistribute it '
            license += 'and/or modify it under the\nterms of the GNU General Public '
            license += 'License as published by the Free Software\nFoundation; either ' 
            license += 'version 3 of the License, or (at your option) any later version.'
            license += '\n\nYou should have received a copy of the GNU General Public '
            license += 'License along with\nthis script (see license); if not, write to '
            license += 'the Free Software\nFoundation, Inc., 59 Temple Place, Suite 330, '
            license += 'Boston, MA  02111-1307  USA'
        self.set_license(license)
        authors = []
        try:
            path = os.path.realpath(os.path.join(os.path.dirname(__file__), 
                '..', '..', '..', 'AUTHORS'))
            f = file(path, 'r')
            for line in f:
                authors.append(line.strip('\n'))
            f.close()
        except Exception, msg:
            authors = [i18n.get('file_not_found')]
        self.set_authors(authors)

        self.connect("response", self.__response)
        self.connect("close", self.__close)
        self.connect("delete_event", self.__close)


    def __response(self, dialog, response, *args):
        if response < 0:
            dialog.destroy()
            dialog.emit_stop_by_name('response')

    def __close(self, widget, event=None):
        self.destroy()
        return True

    def quit(self):
        self.destroy()

########NEW FILE########
__FILENAME__ = accounts
# -*- coding: utf-8 -*-

# GTK account manager for Turpial
#
# Author: Wil Alvarez (aka Satanas)

import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n
from turpial.ui.gtk.markuplabel import MarkupLabel

from libturpial.common import LoginStatus

log = logging.getLogger('Gtk')

class AccountsDialog(Gtk.Window):
    def __init__(self, base):
        Gtk.Window.__init__(self)

        self.base = base
        self.set_title(i18n.get('accounts'))
        self.set_size_request(360, 320)
        self.set_resizable(False)
        self.set_icon(self.base.load_image('turpial.png', True))
        self.set_transient_for(base)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_gravity(Gdk.Gravity.STATIC)
        self.connect('delete-event', self.__close)
        self.connect('key-press-event', self.__key_pressed)

        self.model = Gtk.ListStore(GdkPixbuf.Pixbuf, str, GdkPixbuf.Pixbuf, str, object)
        self.model.set_sort_column_id(1, Gtk.SortType.DESCENDING)

        icon = Gtk.CellRendererPixbuf()
        icon.set_property('yalign', 0.5)
        icon.set_property('xalign', 0.5)
        icon.set_padding(7,7)

        account = Gtk.CellRendererText()
        account.set_property('wrap-width', 260)
        account.set_property('yalign', 0.5)
        account.set_property('xalign', 0)

        status = Gtk.CellRendererPixbuf()
        status.set_property('yalign', 0.5)
        status.set_property('xalign', 0.5)
        status.set_padding(7,7)

        column = Gtk.TreeViewColumn('accounts')
        column.set_alignment(0.0)
        column.pack_start(icon, False)
        column.pack_start(account, True)
        column.pack_start(status, False)
        column.add_attribute(account, 'markup', 1)
        column.add_attribute(icon, 'pixbuf', 0)
        column.add_attribute(status, 'pixbuf', 2)

        self.acc_list = Gtk.TreeView()
        self.acc_list.set_headers_visible(False)
        #self.acc_list.set_events(gtk.gdk.POINTER_MOTION_MASK)
        self.acc_list.set_level_indentation(0)
        self.acc_list.set_resize_mode(Gtk.ResizeMode.IMMEDIATE)
        self.acc_list.set_model(self.model)
        self.acc_list.set_tooltip_column(0)
        self.acc_list.append_column(column)
        self.acc_list.connect("query-tooltip", self.__tooltip_query)
        ###self.acc_list.connect("cursor-changed", self.__on_select)

        select = self.acc_list.get_selection()
        select.connect('changed', self.__on_select)
        #self.acc_list.connect("button-release-event", self.__on_click)
        #self.click_handler = self.list.connect("cursor-changed", self.__on_select)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.acc_list)

        self.btn_add = Gtk.Button(i18n.get('add'))
        self.btn_login = Gtk.Button(i18n.get('login'))
        self.btn_login.set_sensitive(False)
        self.btn_delete = Gtk.Button(i18n.get('delete'))

        self.btn_add.connect('clicked', self.__on_add)
        self.btn_delete.connect('clicked', self.__on_delete)
        self.btn_login.connect('clicked', self.__on_login)

        box_button = Gtk.HButtonBox()
        box_button.set_spacing(6)
        box_button.set_layout(Gtk.ButtonBoxStyle.END)
        box_button.pack_start(self.btn_delete, False, False, 0)
        box_button.pack_start(self.btn_login, False, False, 0)
        box_button.pack_start(self.btn_add, False, False, 0)

        vbox = Gtk.VBox(False)
        vbox.set_border_width(6)
        vbox.pack_start(scroll, True, True, 0)
        vbox.pack_start(box_button, False, False, 6)
        self.add(vbox)

        self.showed = False
        self.form = None

    def __close(self, widget, event=None):
        self.showed = False
        self.hide()
        return True

    def __key_pressed(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.__close(widget)

    def __get_selected(self):
        select = self.acc_list.get_selection()
        if select is None:
            return None

        model, row = select.get_selected()
        if row is None:
            return None

        acc = model.get_value(row, 4)
        return acc

    def __tooltip_query(self, treeview, x, y, mode, tooltip):
        path = treeview.get_path_at_pos(x, y)
        if path:
            treepath, column = path[:2]
            model = treeview.get_model()
            iter_ = model.get_iter(treepath)
            text = model.get_value(iter_, 3)
            tooltip.set_text(text)
        return False

    def __on_select(self, widget):
        acc = self.__get_selected()
        if acc is None:
            self.btn_delete.set_sensitive(False)
            self.btn_login.set_sensitive(False)
            self.btn_login.set_label(i18n.get('login'))
            return

        if acc.logged_in == LoginStatus.NONE:
            self.btn_login.set_label(i18n.get('login'))
            self.btn_login.set_sensitive(True)
            self.btn_delete.set_sensitive(True)
        elif acc.logged_in == LoginStatus.IN_PROGRESS:
            self.btn_login.set_label(i18n.get('in_progress'))
            self.btn_login.set_sensitive(False)
            self.btn_delete.set_sensitive(False)
        elif acc.logged_in == LoginStatus.DONE:
            self.btn_login.set_label(i18n.get('logged_in'))
            self.btn_login.set_sensitive(False)
            self.btn_delete.set_sensitive(True)

    def __on_delete(self, widget):
        acc = self.__get_selected()
        if acc is None:
            return
        self.__lock(True)
        self.base.delete_account(acc.id_)

    def __on_login(self, widget):
        acc = self.__get_selected()
        if acc is None:
            return
        self.base.login(acc.id_)
        self.btn_login.set_label(i18n.get('in_progress'))
        self.btn_login.set_sensitive(False)

    def __on_add(self, widget):
        self.form = AccountForm(self.base, self)

    def __lock(self, value):
        value = not value
        self.acc_list.set_sensitive(value)
        self.btn_login.set_sensitive(value)
        self.btn_add.set_sensitive(value)
        self.btn_delete.set_sensitive(value)

    def update(self):
        if self.showed:
            self.model.clear()
            empty = True
            self.btn_login.set_sensitive(False)
            self.btn_delete.set_sensitive(False)
            for acc in self.base.get_all_accounts():
                empty = False
                imagename = "%s.png" % acc.protocol_id
                pix = self.base.load_image(imagename, True)
                username = "<span size='large'><b>%s</b></span>" % acc.username
                status = ''
                status_pix = None
                if acc.logged_in == LoginStatus.NONE:
                    status = i18n.get('disconnected')
                    status_pix = self.base.load_image('mark-disconnected.png', True)
                elif acc.logged_in == LoginStatus.IN_PROGRESS:
                    status = i18n.get('connecting...')
                    status_pix = self.base.load_image('mark-connecting.png', True)
                elif acc.logged_in == LoginStatus.DONE:
                    status = i18n.get('connected')
                    status_pix = self.base.load_image('mark-connected.png', True)

                self.model.append([pix, username, status_pix, status, acc])
                del pix
                del status_pix
            if empty:
                self.btn_login.set_label(i18n.get('login'))
            else:
                self.acc_list.set_cursor((0, ))

    def cancel_login(self, message):
        if self.form:
            # Delete account if wasn't configured properly
            iter_ = self.model.get_iter_first()
            # If this is the first account you try to add delete it, else loop
            # throught the model and see which ones are registered but are not
            # in the model
            if iter_ is None:
                try:
                    self.base.delete_account(self.base.get_accounts_list()[0])
                except:
                    pass
            else:
                curr_acc = []
                while iter_:
                    acc = self.model.get_value(iter_, 4)
                    curr_acc.append(acc.id_)
                    iter_ = self.model.iter_next(iter_)

                for acc_id in self.base.get_accounts_list():
                    if acc_id not in curr_acc:
                        self.base.delete_account(acc_id)
            self.form.cancel('<span foreground="red">' + message + '</span>')
        self.update()

    def done_login(self):
        if self.form:
            self.form.done()
            return True
        return False

    def done_delete(self):
        self.__lock(False)
        self.update()

    def status_message(self, message):
        if self.form:
            self.form.set_loading_message(message)

    def show(self):
        if self.showed:
            self.present()
        else:
            self.showed = True
            self.update()
            self.show_all()

    def quit(self):
        self.destroy()

# Update list after add account
class AccountForm(Gtk.Window):
    def __init__(self, base, parent, user=None, pwd=None, protocol=None):
        Gtk.Window.__init__(self)

        self.base = base
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title(i18n.get('create_account'))
        self.set_size_request(290, 200)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_gravity(Gdk.Gravity.STATIC)
        self.connect('delete-event', self.__close)
        self.connect('key-press-event', self.__key_pressed)

        plabel = Gtk.Label(i18n.get('protocol'))
        plabel.set_alignment(0, 0.5)

        plist = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        for p in self.base.get_protocols_list():
            image = '%s.png' % p
            t_icon = self.base.load_image(image, True)
            plist.append([t_icon, p, p])

        self.protocol = Gtk.ComboBox()
        self.protocol.set_model(plist)
        icon = Gtk.CellRendererPixbuf()
        txt = Gtk.CellRendererText()
        self.protocol.pack_start(icon, False)
        self.protocol.pack_start(txt, False)
        self.protocol.add_attribute(icon, 'pixbuf', 0)
        self.protocol.add_attribute(txt, 'markup', 1)

        self.username = Gtk.Entry()
        user_box = Gtk.HBox(False)
        user_box.pack_start(self.username, True, True, 0)

        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        pass_box = Gtk.HBox(True)
        pass_box.pack_start(self.password, True, True, 0)

        self.cred_label = Gtk.Label(i18n.get('user_and_password'))
        self.cred_label.set_alignment(0, 0.5)

        cred_box = Gtk.VBox(False)
        cred_box.pack_start(self.cred_label, False, False, 0)
        cred_box.pack_start(user_box, False, False, 0)
        cred_box.pack_start(pass_box, False, False, 0)

        self.btn_signin = Gtk.Button(i18n.get('signin'))

        self.spinner = Gtk.Spinner()
        self.waiting_label = MarkupLabel(xalign=0.5)
        waiting_box = Gtk.HBox()
        waiting_box.pack_start(self.spinner, False, False, 10)
        waiting_box.pack_start(self.waiting_label, True, False, 0)

        vbox = Gtk.VBox(False)
        vbox.set_border_width(12)
        vbox.pack_start(plabel, False, False, 0)
        vbox.pack_start(self.protocol, False, False, 0)
        vbox.pack_start(Gtk.EventBox(), False, False, 6)
        vbox.pack_start(cred_box, True, True, 0)
        vbox.pack_start(waiting_box, False, False, 0)
        vbox.pack_start(self.btn_signin, False, False, 6)

        self.add(vbox)
        self.show_all()

        self.protocol.connect('changed', self.__on_change_protocol)
        self.password.connect('activate', self.__on_sign_in)
        self.btn_signin.connect('clicked', self.__on_sign_in)

        self.protocol.set_active(0)
        self.working = False
        self.spinner.hide()

    def __close(self, widget, event=None):
        if not self.working:
            self.destroy()
            return False
        else:
            return True

    def __key_pressed(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.__close(widget)

    def __on_change_protocol(self, widget):
        index = widget.get_active()
        model = widget.get_model()
        if index < 0:
            return

        self.waiting_label.set_text('')
        protocol = model[index][1]
        if protocol == 'twitter':
            self.username.set_visible(False)
            self.password.set_visible(False)
            self.cred_label.set_visible(False)
            self.btn_signin.grab_focus()
        elif protocol == 'identica':
            self.username.set_visible(True)
            self.password.set_visible(True)
            self.cred_label.set_visible(True)
            self.username.grab_focus()

    def __on_sign_in(self, widget):
        self.working = True
        username = self.username.get_text()
        passwd = self.password.get_text()
        model = self.protocol.get_model()
        pindex = self.protocol.get_active()
        protocol = model[pindex][1]

        # Validate
        if protocol == 'identica':
            if username == '' or passwd == '':
                self.waiting_label.set_error_text(i18n.get('credentials_could_not_be_empty'))
                return True

        self.__lock()
        self.waiting_label.set_text(i18n.get('connecting'))
        self.spinner.show()
        self.spinner.start()
        self.base.save_account(username, protocol, passwd)

    def __lock(self):
        self.username.set_sensitive(False)
        self.password.set_sensitive(False)
        self.protocol.set_sensitive(False)
        self.btn_signin.set_sensitive(False)

    def __unlock(self):
        self.username.set_sensitive(True)
        self.password.set_sensitive(True)
        self.protocol.set_sensitive(True)
        self.btn_signin.set_sensitive(True)

    def cancel(self, message):
        self.working = False
        self.__unlock()
        self.waiting_label.set_error_text(message)
        self.spinner.stop()
        self.spinner.hide()

    def set_loading_message(self, message):
        self.waiting_label.set_text(message)

    def done(self):
        self.working = False
        self.destroy()

########NEW FILE########
__FILENAME__ = column
# -*- coding: utf-8 -*-

# GTK3 widget to implement columns in Turpial

import pdb
import time
import urllib2

from xml.sax.saxutils import unescape

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import PangoCairo

from turpial.ui.lang import i18n
from libturpial.common import StatusType


ICON_MARGIN = 5

class StatusesColumn(Gtk.VBox):
    def __init__(self, base, column):
        Gtk.VBox.__init__(self)

        self.base = base
        self.set_size_request(250, -1)
        #self.set_double_buffered(True)

        # Variables that defines column status
        self.last_id = None
        self.updating = False
        self.menu = None
        self.column = column
        self.status_ref = []

        # Header
        #============================================================
        # TODO: Implement factory for this images
        img = '%s.png' % column.protocol_id
        caption = "%s :: %s" % (column.account_id.split('-')[0],
            urllib2.unquote(column.column_name))
        icon = Gtk.Image()
        icon.set_from_pixbuf(self.base.load_image(img, True))
        icon.set_margin_top(ICON_MARGIN)
        icon.set_margin_right(ICON_MARGIN * 2)
        icon.set_margin_bottom(ICON_MARGIN)
        icon.set_margin_left(ICON_MARGIN)

        label = Gtk.Label()
        label.set_use_markup(True)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_markup('<span foreground="#ffffff"><b>%s</b></span>' % (caption))
        label.set_alignment(0, 0.5)

        btn_close = Gtk.Button()
        btn_close.set_image(self.base.load_image('action-delete.png'))
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_tooltip_text(i18n.get('delete_column'))
        btn_close.connect('clicked', self.__delete_column, column.id_)

        self.btn_config = Gtk.Button()
        self.btn_config.set_image(self.base.load_image('action-refresh.png'))
        self.btn_config.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_config.set_tooltip_text(i18n.get('column_options'))
        self.btn_config.connect('clicked', self.show_config_menu)
        self.connect('realize', self.__on_realize)

        self.spinner = Gtk.Spinner()

        inner_header = Gtk.HBox()
        inner_header.pack_start(icon, False, False, 0)
        inner_header.pack_start(label, True, True, 0)
        inner_header.pack_start(btn_close, False, False, 0)
        inner_header.pack_start(self.btn_config, False, False, 0)
        inner_header.pack_start(self.spinner, False, False, 0)

        header = Gtk.EventBox()
        header.add(inner_header)
        header.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0, 0, 0))

        # Content
        #============================================================

        self._list = Gtk.TreeView()
        self._list.set_headers_visible(False)
        #self._list.set_events(gtk.gdk.POINTER_MOTION_MASK)
        self._list.set_level_indentation(0)
        #self._list.set_resize_mode(gtk.RESIZE_IMMEDIATE)

        self.model = Gtk.ListStore(
            GdkPixbuf.Pixbuf, # avatar
            str, # id
            str, # username
            str, # plain text message
            str, # datetime
            str, # client
            bool, # favorited?
            bool, # repeated?
            bool, # own?
            bool, # protected?
            bool, # verified?
            str, # in_reply_to_id
            str, # in_reply_to_user
            str, # reposted_by
            Gdk.Color, # color
            int, # status type
            str, # account_id
            float, # unix timestamp
            object, #status
        )

        # Sort by unix timestamp
        #self.model.set_sort_column_id(17, Gtk.SortType.DESCENDING)

        cell_avatar = Gtk.CellRendererPixbuf()
        cell_avatar.set_property('yalign', 0)
        cell_status = StatusCellRenderer(self.base, self._list)
        cell_status.set_property('wrap-mode', Pango.WrapMode.WORD_CHAR)
        cell_status.set_property('wrap-width', 260)
        cell_status.set_property('yalign', 0)
        cell_status.set_property('xalign', 0)

        column = Gtk.TreeViewColumn('tweets')
        column.set_alignment(0.0)
        column.pack_start(cell_avatar, False)
        column.pack_start(cell_status, True)
        column.set_attributes(cell_status, text=3, datetime=4, client=5,
            favorited=6, repeated=7, protected=9, verified=10, username=2,
            in_reply_to_user=12, reposted_by=13, cell_background_gdk=14,
            timestamp=17, entities=18)
        column.set_attributes(cell_avatar, pixbuf=0, cell_background_gdk=14)


        self._list.set_model(self.model)
        self._list.append_column(column)
        #self._list.connect("button-release-event", self.__on_click)
        #self.click_handler = self._list.connect("cursor-changed", self.__on_select)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add_with_viewport(self._list)
        scroll.set_margin_top(ICON_MARGIN)
        scroll.set_margin_right(ICON_MARGIN)
        scroll.set_margin_bottom(ICON_MARGIN)
        scroll.set_margin_left(ICON_MARGIN)

        content = Gtk.EventBox()
        content.add(scroll)

        self.pack_start(header, False, False, 0)
        self.pack_start(content, True, True, 0)

        self.show_all()

        self.btn_config.hide()
        self.spinner.show()

    def __delete_column(self, widget, column_id):
        self.base.delete_column(column_id)

    def __mark_favorite(self, child, status):
        if child.status.id_ != status.id_:
            return
        child.set_favorited_mark(True)

    def __unmark_favorite(self, child, status):
        if child.status.id_ != status.id_:
            return
        child.set_favorited_mark(False)

    def __mark_repeat(self, child, status):
        if child.status.id_ != status.id_:
            return
        child.set_repeated_mark(True)

    def __unmark_repeat(self, child, status):
        if child.status.id_ != status.id_:
            return
        child.set_repeated_mark(False)

    def __delete_status(self, child, status):
        if child.status.id_ != status.id_:
            return
        self._list.remove(child)

    def __refresh(self, widget, column_id):
        self.base.refresh_column(column_id)

    def __on_realize(self, widget, data=None):
        # Assuming that this code is only executed the first time you instance
        # a Status Column
        self.btn_config.hide()
        self.spinner.start()
        self.spinner.show()

    def clear(self):
        self._list.get_model().clear()

    def start_updating(self):
        pdb.set_trace()
        self.spinner.start()
        self.spinner.show()
        self.btn_config.hide()
        self.updating = True
        return self.last_id

    def stop_updating(self):
        pdb.set_trace()
        self.spinner.stop()
        self.spinner.hide()
        self.btn_config.show()
        self.updating = False

    def update(self, statuses):
        pdb.set_trace()
        num_to_del = 0
        num_new_statuses = len(statuses)
        num_curr_statuses = len(self.status_ref)
        max_statuses = self.base.get_max_statuses_per_column()
        model = self._list.get_model()

        # Set last_id before reverse, that way we guarantee that last_id holds
        # the id for the newest status
        self.last_id = statuses[0].id_

        # We need to reverse statuses because they come ordered as the newest first
        statuses.reverse()

        for status in statuses:
            # We don't insert duplicated statuses
            if status.id_ in self.status_ref:
                continue

            print '    Adding: %s' % status.text[:30]
            pix = self.base.factory.unknown_avatar()

            row = [pix, str(status.id_), status.username, status.text, status.datetime, status.source.name,
                status.favorited, status.repeated, status.is_own, status.protected, status.verified,
                str(status.in_reply_to_id), status.in_reply_to_user, status.reposted_by, None,
                StatusType.NORMAL, status.account_id, status.timestamp, status.entities]

            # We ensure that status is inserted at top
            model.prepend(row)
            self.status_ref.insert(0, status.id_)
            num_curr_statuses += 1

        # We only delete statuses if we overpass the max allowed
        if (num_curr_statuses) > max_statuses:
            num_to_del = num_curr_statuses - max_statuses
            ids_to_del = self.status_ref[-num_to_del:]

            for id_ in ids_to_del:
                iter_ = model.get_iter_first()
                while iter_:
                    if model.get_value(iter_, 1) == str(id_):
                        print '    Deleting: %s' % model.get_value(iter_, 3)[:30]
                        model.remove(iter_)
                        index = self.status_ref.index(id_)
                        del(self.status_ref[index])
                        num_curr_statuses -= 1
                        break
                    iter_ = self.model.iter_next(iter_)

        print '    %i statuses after update' % num_curr_statuses

        #self.mark_all_as_read()
        #self.__set_last_time()

        #if self.get_vadjustment().get_value() == 0.0:
        #    self.list.scroll_to_cell((0,))

        #self.click_handler = self.list.connect("cursor-changed", self.__on_select)

    ###def mark_favorite(self, status):
    ###    self._list.foreach(self.__mark_favorite, status)

    ###def unmark_favorite(self, status):
    ###    self._list.foreach(self.__unmark_favorite, status)

    ###def mark_repeat(self, status):
    ###    self._list.foreach(self.__mark_repeat, status)

    ###def unmark_repeat(self, status):
    ###    self._list.foreach(self.__unmark_repeat, status)

    ###def delete_status(self, status):
    ###    self._list.foreach(self.__delete_status, status)

    def show_config_menu(self, widget):
        notif = Gtk.CheckMenuItem(i18n.get('notificate'))
        sound = Gtk.CheckMenuItem(i18n.get('sound'))
        refresh = Gtk.MenuItem(i18n.get('manual_update'))
        refresh.connect('activate', self.__refresh, self.column.id_)

        self.menu = Gtk.Menu()
        self.menu.append(sound)
        self.menu.append(notif)
        self.menu.append(refresh)

        self.menu.show_all()
        self.menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())


class StatusCellRenderer(Gtk.CellRendererText):
    username = GObject.property(type=str, default='')
    datetime = GObject.property(type=str, default='')
    client = GObject.property(type=str, default='')
    favorited = GObject.property(type=bool, default=False)
    repeated = GObject.property(type=bool, default=False)
    protected = GObject.property(type=bool, default=False)
    verified = GObject.property(type=bool, default=False)
    in_reply_to_user = GObject.property(type=str, default='')
    reposted_by = GObject.property(type=str, default='')
    timestamp= GObject.property(type=float)
    entities = GObject.property(type=object)

    HEADER_PADDING = MESSAGE_PADDING = 4
    FOOTER_PADDING = 2

    def __init__(self, base, treeview):
        GObject.GObject.__init__(self)
        self.base = base
        #self._layout = treeview.create_pango_layout('')

        # With this, we accumulate the width of each part of header
        self.accum_header_width = 0
        # This holds the total height for a given status
        self.total_height = 0


    def __highlight_elements(self, text):
        for elements in self.get_property('entities').values():
            for u in elements:
                cad = u'<span foreground="%s">%s</span>' % (
                    self.base.get_color_scheme('links'), u.display_text)
                text = text.replace(u.search_for, cad)
        return text

    def __render_reposted_icon(self, cr, cell_area):
        if not self.get_property('reposted_by'):
            self.accum_header_width += self.HEADER_PADDING
            return

        y = cell_area.y
        x = cell_area.x + self.HEADER_PADDING
        icon = self.base.factory.reposted_mark()
        Gdk.cairo_set_source_pixbuf(cr, icon, x, y)
        self.accum_header_width += icon.get_width() + self.HEADER_PADDING
        cr.paint()
        return

    def __render_username(self, context, cr, cell_area, layout):
        username = self.get_property('username').decode('utf-8')
        y = cell_area.y
        x = cell_area.x + self.accum_header_width

        user = '<span size="9000" foreground="%s"><b>%s</b></span>' % (
            self.base.get_color_scheme('links'), username)
        layout.set_markup(user, -1)
        inkRect, logicalRect = layout.get_pixel_extents()
        self.accum_header_width += logicalRect.width + self.HEADER_PADDING
        self.total_height = 20

        context.save()
        Gtk.render_layout(context, cr, x, y, layout)
        context.restore()
        return

    def __render_protected_icon(self, cr, cell_area):
        if not self.get_property('protected'):
            return

        y = cell_area.y
        x = cell_area.x + self.accum_header_width
        icon = self.base.factory.protected_mark()
        Gdk.cairo_set_source_pixbuf(cr, icon, x, y)
        self.accum_header_width += icon.get_width() + self.HEADER_PADDING
        cr.paint()
        return

    def __render_verified_icon(self, cr, cell_area):
        if not self.get_property('verified'):
            return

        y = cell_area.y
        x = cell_area.x + self.accum_header_width
        icon = self.base.factory.verified_mark()
        Gdk.cairo_set_source_pixbuf(cr, icon, x, y)
        # TODO: Do it with cairo_context.move_to
        self.accum_header_width += icon.get_width() + self.HEADER_PADDING
        cr.paint()
        return

    def __render_message(self, context, cr, cell_area, layout):
        y = cell_area.y + self.total_height
        x = cell_area.x + self.MESSAGE_PADDING

        text = self.get_property('text').decode('utf-8')
        #escaped_text = GObject.markup_escape_text(text)
        pango_text = u'<span size="9000">%s</span>' % text
        pango_text = self.__highlight_elements(pango_text)

        layout.set_markup(pango_text, -1)

        inkRect, logicalRect = layout.get_pixel_extents()
        self.total_height += logicalRect.height + self.MESSAGE_PADDING

        context.save()
        Gtk.render_layout(context, cr, x, y, layout)
        context.restore()
        return

    def __render_datetime(self, context, cr, cell_area, layout):
        #datetime = self.get_property('datetime').decode('utf-8')
        # Ported to base
        datetime = self.base.humanize_timestamp(self.get_property('timestamp'))
        in_reply_to_user = self.get_property('in_reply_to_user')

        y = cell_area.y + self.total_height
        x = cell_area.x + self.MESSAGE_PADDING

        if in_reply_to_user:
            pango_text = u'<span size="7000" foreground="#999">%s %s %s</span>' % (
                datetime, i18n.get('in_reply_to'), in_reply_to_user)
        else:
            pango_text = u'<span size="7000" foreground="#999">%s</span>' % datetime

        layout.set_markup(pango_text, -1)

        inkRect, logicalRect = layout.get_pixel_extents()
        self.total_height += logicalRect.height + self.FOOTER_PADDING

        context.save()
        Gtk.render_layout(context, cr, x, y, layout)
        context.restore()
        return

    def __render_reposted_by(self, context, cr, cell_area, layout):
        reposted_by = self.get_property('reposted_by')
        if not reposted_by:
            return

        y = cell_area.y + self.total_height
        x = cell_area.x + self.MESSAGE_PADDING

        reposted_by = reposted_by.decode('utf-8')
        pango_text = u'<span size="7000" foreground="#999">%s %s</span>' % (
            i18n.get('retweeted_by'), reposted_by)

        layout.set_markup(pango_text, -1)

        inkRect, logicalRect = layout.get_pixel_extents()
        self.total_height += logicalRect.height + self.FOOTER_PADDING

        context.save()
        Gtk.render_layout(context, cr, x, y, layout)
        context.restore()
        return

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    #def do_get_preferred_size(self, treeview):
    def do_get_preferred_height_for_width(self, treeview, width):
        column = treeview.get_column(0)
        column_width = column.get_width() - 50
        text = self.get_property('text')
        text = text.decode('utf-8')
        font = Pango.FontDescription('Sans')
        layout = treeview.create_pango_layout('')
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_font_description(font)
        layout.set_width(Pango.SCALE * column_width)
        layout.set_text(self.get_property('text'), -1)

        inkRect, logicalRect = layout.get_pixel_extents()
        height = 40
        if self.get_property('reposted_by'):
            height += 15
        height += logicalRect.height
        #print 'calculating height ******************', width, column_width, height
        return height, height

    def do_render(self, cr, widget, bg_area, cell_area, flags):
        # Initialize values
        self.accum_header_width = 0
        self.total_height = 0

        context = widget.get_style_context()
        xpad = self.get_property('xpad')
        ypad = self.get_property('ypad')

        # Setting up font and layout
        font = Pango.FontDescription('Sans')
        layout = PangoCairo.create_layout(cr)
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_font_description(font)
        layout.set_width(Pango.SCALE * cell_area.width)

        context.save()

        # Render header
        self.__render_reposted_icon(cr, cell_area)
        self.__render_username(context, cr, cell_area, layout)
        self.__render_protected_icon(cr, cell_area)
        self.__render_verified_icon(cr, cell_area)

        # Render body
        self.__render_message(context, cr, cell_area, layout)
        self.__render_datetime(context, cr, cell_area, layout)
        self.__render_reposted_by(context, cr, cell_area, layout)

        context.restore()
        return

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

# Common functions or constants for GTK3 in Turpial

OUTTER_BOTTOM_MARGIN = 5
AVATAR_MARGIN = 5

class StatusProgress:
    FAVING = 'adding_to_fav'
    UNFAVING = 'removing_from_fav'
    RETWEETING = 'retweeting'
    UNRETWEETING = 'unretweeting'
    DELETING = 'deleting'


def escape_text_for_markup(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

########NEW FILE########
__FILENAME__ = container
# -*- coding: utf-8 -*-

# GTK3 container for all columns in Turpial

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n
from turpial.ui.gtk.column import StatusesColumn

class Container(Gtk.VBox):
    def __init__(self, base):
        Gtk.VBox.__init__(self)

        self.base = base
        self.child = None
        #self.set_double_buffered(True)
        self.columns = {}
        self.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(65535, 65535,65535))

    def __scrolling_right(self):
        if len(self.columns) > 0:
            adjustment = self.child.get_hadjustment()
            max_value = adjustment.get_upper()
            adjustment.set_value(max_value)

    def empty(self):
        if self.child:
            self.remove(self.child)

        placeholder = Gtk.Image()

        image = Gtk.Image()
        image.set_from_pixbuf(self.base.load_image('logo.png', True))

        welcome = Gtk.Label()
        welcome.set_use_markup(True)
        welcome.set_markup('<b>' + i18n.get('welcome') + '</b>')

        no_accounts = Gtk.Label()
        no_accounts.set_use_markup(True)
        no_accounts.set_line_wrap(True)
        no_accounts.set_justify(Gtk.Justification.CENTER)
        if len(self.base.get_accounts_list()) > 0:
            no_accounts.set_markup(i18n.get('no_registered_columns'))
        else:
            no_accounts.set_markup(i18n.get('no_active_accounts'))

        self.child = Gtk.VBox()
        self.child.pack_start(placeholder, False, False, 40)
        self.child.pack_start(image, False, False, 20)
        self.child.pack_start(welcome, False, False, 10)
        self.child.pack_start(no_accounts, False, False, 0)

        self.add(self.child)
        self.show_all()

    def normal(self, accounts, columns):
        self.columns = {}

        box = Gtk.HBox()

        for col in columns:
            self.columns[col.id_] = StatusesColumn(self.base, col)
            box.pack_start(self.columns[col.id_], True, True, 0)

        self.child = Gtk.ScrolledWindow()
        self.child.add_with_viewport(box)

        self.add(self.child)
        self.show_all()

    def start_updating(self, column_id):
        return self.columns[column_id].start_updating()

    def stop_updating(self, column_id, errmsg=None, errtype=None):
        self.columns[column_id].stop_updating()
        if errmsg:
            self.base.show_notice(errmsg, errtype)

    def is_updating(self, column_id):
        return self.columns[column_id].updating

    def update_column(self, column_id, statuses):
        self.columns[column_id].update(statuses)
        self.stop_updating(column_id)

    def add_column(self, column):
        if len(self.columns) > 1:
            self.columns[column.id_] = StatusesColumn(self.base, column)
            hbox = self.child.get_children()[0].get_child()
            hbox.pack_start(self.columns[column.id_], True, True, 0)
        else:
            self.remove(self.child)
            accounts = self.base.get_accounts_list()
            columns = self.base.get_registered_columns()
            self.normal(accounts, columns)

        self.show_all()
        self.scroll()

    def remove_column(self, column_id):
        hbox = self.child.get_children()[0].get_child()
        hbox.remove(self.columns[column_id])
        del self.columns[column_id]
        if len(self.columns) == 0:
            self.empty()

    def mark_status_favorite(self, status):
        # TODO: Optimize this function. Map?
        for key, column in self.columns.iteritems():
            column.mark_favorite(status)

    def unmark_status_favorite(self, status):
        for key, column in self.columns.iteritems():
            column.unmark_favorite(status)

    def mark_status_repeat(self, status):
        for key, column in self.columns.iteritems():
            column.mark_repeat(status)

    def unmark_status_repeat(self, status):
        for key, column in self.columns.iteritems():
            column.unmark_repeat(status)

    def delete_status(self, status):
        for key, column in self.columns.iteritems():
            column.delete_status(status)

    def scroll(self):
        GObject.timeout_add(250, self.__scrolling_right)


########NEW FILE########
__FILENAME__ = dock
# -*- coding: utf-8 -*-

# GTK3 dock for Turpial

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n

from libturpial.common import ProtocolType

class Dock(Gtk.EventBox):
    def __init__(self, base):
        Gtk.EventBox.__init__(self)

        self.base = base
        self.column_menu = None
        self.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0, 0, 0))

        self.btn_updates = DockButton(base, 'dock-updates.png', i18n.get('update_status'))
        self.btn_messages = DockButton(base, 'dock-messages.png', i18n.get('direct_messages'))
        self.btn_search = DockButton(base, 'dock-search.png', i18n.get('search'))
        self.btn_stats = DockButton(base, 'dock-stats.png', i18n.get('statistics'))
        self.btn_columns = DockButton(base, 'dock-columns.png', i18n.get('columns'))
        self.btn_accounts = DockButton(base, 'dock-accounts.png', i18n.get('accounts'))
        self.btn_preferences = DockButton(base, 'dock-preferences.png', i18n.get('preferences'))
        self.btn_about = DockButton(base, 'dock-about.png', i18n.get('about'))

        self.btn_updates.connect('clicked', self.base.show_update_box)
        self.btn_messages.connect('clicked', self.base.show_update_box, True)
        self.btn_search.connect('clicked', self.base.show_search_dialog)
        self.btn_columns.connect('clicked', self.show_columns_menu)
        self.btn_accounts.connect('clicked', self.base.show_accounts_dialog)
        self.btn_preferences.connect('clicked', self.base.show_preferences_dialog)
        self.btn_about.connect('clicked', self.base.show_about_dialog)

        box = Gtk.HBox()
        box.pack_end(self.btn_updates, False, False, 0)
        box.pack_end(self.btn_messages, False, False, 0)
        box.pack_end(self.btn_columns, False, False, 0)
        box.pack_end(self.btn_accounts, False, False, 0)
        box.pack_end(self.btn_search, False, False, 0)
        box.pack_end(self.btn_stats, False, False, 0)
        box.pack_end(self.btn_preferences, False, False, 0)
        box.pack_end(self.btn_about, False, False, 0)

        align = Gtk.Alignment()
        align.set(1, -1, -1, -1)
        align.add(box)

        self.add(align)

    def __save_column(self, widget, column_id):
        self.base.save_column(column_id)

    def empty(self):
        self.btn_updates.hide()
        self.btn_messages.hide()
        self.btn_stats.hide()

    def normal(self):
        self.btn_updates.show()
        self.btn_messages.show()
        self.btn_stats.show()

    def show_columns_menu(self, widget):
        self.menu = Gtk.Menu()

        empty = True
        columns = self.base.get_all_columns()
        reg_columns = self.base.get_registered_columns()

        for acc in self.base.get_all_accounts():
            name = "%s (%s)" % (acc.username, i18n.get(acc.protocol_id))
            temp = Gtk.MenuItem(name)
            if acc.logged_in:
                # Build submenu for columns in each account
                temp_menu = Gtk.Menu()
                for key, col in columns[acc.id_].iteritems():
                    item = Gtk.MenuItem(key)
                    if col.id_ != "":
                        item.set_sensitive(False)
                    item.connect('activate', self.__save_column, col.build_id())
                    temp_menu.append(item)
                # Add public timeline
                public_tl = Gtk.MenuItem(i18n.get('public_timeline').lower())
                public_tl.connect('activate', self.__save_column, acc.id_ + '-public')
                temp_menu.append(public_tl)

                temp.set_submenu(temp_menu)

                # Add view profile item
                temp_menu.append(Gtk.SeparatorMenuItem())
                item = Gtk.MenuItem(i18n.get('view_profile'))
                item.connect('activate', self.__save_column, acc.id_)
                temp_menu.append(item)
            else:
                temp.set_sensitive(False)
            self.menu.append(temp)
            empty = False

        if empty:
            empty_menu = Gtk.MenuItem(i18n.get('no_registered_accounts'))
            empty_menu.set_sensitive(False)
            self.menu.append(empty_menu)
        else:
            self.menu.append(Gtk.SeparatorMenuItem())
        self.menu.show_all()
        self.menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

class DockButton(Gtk.Button):
    def __init__(self, base, image, tooltip):
        Gtk.Button.__init__(self)
        self.set_image(base.load_image(image))
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_tooltip_text(tooltip)
        self.set_size_request(24, 24)
        #self.btn_updates.set_default_size(24, 24)


########NEW FILE########
__FILENAME__ = factory
# -*- coding: utf-8 -*-

# Lazy factory for images in GTK3 Turpial

class ImagesFactory:
    def __init__(self, base):
        self.base = base
        self._unknown_avatar = None
        self._reposted_mark = None
        self._verified_mark = None
        self._protected_mark = None

    def unknown_avatar(self, pixbuf=True):
        if not self._unknown_avatar:
            self._unknown_avatar = self.base.load_image('unknown.png', pixbuf)
        return self._unknown_avatar

    def reposted_mark(self):
        if not self._reposted_mark:
            self._reposted_mark = self.base.load_image('mark-reposted.png', True)
        return self._reposted_mark

    def protected_mark(self):
        if not self._protected_mark:
            self._protected_mark = self.base.load_image('mark-protected.png', True)
        return self._protected_mark

    def verified_mark(self):
        if not self._verified_mark:
            self._verified_mark = self.base.load_image('mark-verified.png', True)
        return self._verified_mark

########NEW FILE########
__FILENAME__ = htmlview
# -*- coding: utf-8 -*-

# Widget for HTML view in Turpial
#
# Author: Wil Alvarez (aka Satanas)

import os

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import WebKit
from gi.repository import GObject

class HtmlView(Gtk.VBox):
    __gsignals__ = {
        "action-request": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING, )),
        "link-request": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING, )),
        "load-started": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
        "load-finished": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, coding='utf-8'):
        Gtk.VBox.__init__(self, False)

        self.coding = coding
        self.uri = 'file://' + os.path.dirname(__file__)

        self.settings = WebKit.WebSettings()

        self.settings.set_property('enable-default-context-menu', False)
        self.settings.set_property('enable-developer-extras', True)
        self.settings.set_property('enable-plugins', True)
        self.settings.set_property('enable-java_applet', False)
        self.settings.set_property('enable-page-cache', True)
        self.settings.set_property('enable-file-access-from-file-uris', True)
        self.settings.set_property('enable-offline-web-application_cache', False)
        self.settings.set_property('enable-html5-local-storage', False)
        self.settings.set_property('enable-html5-database', False)
        self.settings.set_property('enable-xss-auditor', False)
        try:
            self.settings.set_property('enable-dns-prefetching', False)
        except TypeError:
            pass
        self.settings.set_property('enable-caret-browsing', False)
        self.settings.set_property('resizable-text-areas', False)
        self.settings.web_security_enabled = False

        try:
            self.settings.set_property('enable-accelerated-compositing', True)
        except TypeError:
            print "No support for accelerated compositing"

        self.view = WebKit.WebView()
        self.view.set_settings(self.settings)

        #Added new properties in this way cause 'from' is recognized as a key word
        self.view.get_settings().set_property('enable-universal-access-from-file-uris', True)

        self.view.connect('load-started', self.__started)
        self.view.connect('load-finished', self.__finished)
        self.view.connect('console-message', self.__console_message)
        self.view.connect('navigation-policy-decision-requested', self.__process)
        self.view.connect('new-window-policy-decision-requested', self.__on_new_window_requested);

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.view)

        self.pack_start(scroll, True, True, 0)

    def __on_new_window_requested(self, view, frame, request, decision, u_data):
        self.emit('link-request', request.get_uri())

    def __console_message(self, view, message, line, source_id, data=None):
        #print "%s <%s:%i>" % (message, source_id, line)
        print "%s" % message
        return True

    def __process(self, view, frame, request, action, policy, data=None):
        url = request.get_uri()
        if url is None:
            pass
        elif url.startswith('cmd:'):
            policy.ignore()
            self.emit('action-request', url[4:])
        elif url.startswith('link:'):
            policy.ignore()
            self.emit('link-request', url[5:])
        policy.use()

    def __started(self, widget, frame):
        self.emit('load-started')

    def __finished(self, widget, frame):
        self.emit('load-finished')

    def load(self, url):
        GLib.idle_add(self.view.load_uri, url)

    def render(self, html):
        GLib.idle_add(self.view.load_string, html, "text/html", self.coding, self.uri)

    def execute(self, script):
        script = script.replace('\n', ' ')
        self.view.execute_script(script)

    def stop(self):
        self.view.stop_loading()

GObject.type_register(HtmlView)

########NEW FILE########
__FILENAME__ = imageview
# -*- coding: utf-8 -*-

""" Window to show embedded images """
#
# Author: Wil Alvarez (aka Satanas)
# Aug 31, 2012

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n

class ImageView(Gtk.Window):
    STATUS_IDLE = 0
    STATUS_LOADING = 1
    STATUS_LOADED = 2

    def __init__(self, baseui):
        Gtk.Window.__init__(self)

        self.mainwin = baseui
        self.set_title(i18n.get('image_preview'))
        self.set_size_request(100, 100)
        self.set_default_size(300, 300)
        self.set_transient_for(baseui)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.connect('delete-event', self.quit)
        self.connect('size-allocate', self.__resize)

        self.error_msg = Gtk.Label()
        self.error_msg.set_alignment(0.5, 0.5)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(96, 96)

        self.loading_box = Gtk.Box(spacing=0)
        self.loading_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.loading_box.pack_start(self.spinner, True, False, 0)
        self.loading_box.pack_start(self.error_msg, True,True, 0)

        self.image = Gtk.Image()
        self.image_box = Gtk.ScrolledWindow()
        self.image_box.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        image_box = Gtk.EventBox()
        image_box.add(self.image)
        image_box.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0, 0, 0))
        self.image_box.add_with_viewport(image_box)

        self.last_size = (0, 0)
        self.status = self.STATUS_IDLE
        self.pixbuf = None

    def __resize(self, widget, allocation=None):
        if self.status != self.STATUS_LOADED:
            return

        if allocation:
            if self.last_size == (allocation.width, allocation.height):
                return
            win_width, win_height = allocation.width, allocation.height
        else:
            win_width, win_height = self.get_size()

        scale = min(float(win_width)/self.pix_width, float(win_height)/self.pix_height)
        new_width = int(scale * self.pix_width)
        new_height = int(scale * self.pix_height)
        pix = self.pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
        self.image.set_from_pixbuf(pix)
        del pix
        self.last_size = self.get_size()

    def __clear(self):
        current_child = self.get_child()
        if current_child:
            self.remove(current_child)

        del self.pixbuf
        self.pixbuf = None
        self.status = self.STATUS_IDLE
        self.error_msg.hide()

    def loading(self):
        self.__clear()
        self.spinner.start()
        self.resize(300, 300)
        self.add(self.loading_box)
        self.status = self.STATUS_LOADING
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.show_all()

    def update(self, path):
        self.__clear()
        self.spinner.stop()
        self.add(self.image_box)

        # Picture information. This will not change until the next update
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        self.pix_width = self.pixbuf.get_width()
        self.pix_height = self.pixbuf.get_height()
        self.pix_rate = self.pix_width / self.pix_height

        self.status = self.STATUS_LOADED
        self.resize(self.pix_width, self.pix_height)
        self.show_all()
        self.present()

    def error(self, error=''):
        if error:
            self.error_msg.set_label(error)
        else:
            self.error_msg.set_label(i18n.get('error_loading_image'))
        self.spinner.stop()
        self.spinner.hide()

    def quit(self, widget, event):
        self.hide()
        self.__clear()
        self.last_size = (300, 300)
        return True

########NEW FILE########
__FILENAME__ = indicator
# -*- coding: utf-8 -*-

""" Indicator module for Turpial """
#
# Author: Wil Alvarez (aka Satanas)

import os
import logging

from gi.repository import GObject

from turpial.ui.lang import i18n

log = logging.getLogger('Indicator')

INDICATOR = True

try:
    #from gi.repository import Indicate
    INDICATOR = False
except ImportError, exc:
    log.info('Could not import Indicate module. Support for indicators disabled')
    INDICATOR = False

class Indicators(GObject.GObject):
    __gsignals__ = {
        "main-clicked": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
        "indicator-clicked": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT, )),
    }

    def __init__(self, disable=False):
        GObject.GObject.__init__(self)
        self.indicators = {}
        self.activate()
        self.disable = disable

        if not INDICATOR:
            log.debug('Module not available')
            self.disable = True
            return

        if disable:
            log.debug('Module disabled')
            return

        desktop_file = os.path.join(os.getcwd(), "turpial.desktop")

        server = Indicate.indicate_server_ref_default()
        server.set_type("message.micro")
        server.set_desktop_file(desktop_file)
        server.show()

        server.connect("server-display", self.__on_server_display)

    def __on_server_display(self, server, data):
        self.emit('main-clicked')

    def __on_user_display(self, indicator, data):
        self.emit('indicator-clicked', indicator)

    def toggle_activation(self):
        if self.active:
            self.active = False
        else:
            self.active = True

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def add_update(self, column, count):
        if self.disable:
            log.debug('Module disabled. Adding no indicators')
            return

        global INDICATOR
        if self.active and INDICATOR:
            message = "%s :: %s (%s)" % (column.account_id.split('-')[0],
                column.column_name, i18n.get(column.protocol_id))

            indicator = Indicate.Indicator()
            indicator.connect("user-display", self.__on_user_display)
            indicator.set_property("name", message)
            indicator.set_property("count", str(count))
            indicator.label = message
            self.indicators[message] = indicator
            self.indicators[message].show()

    def clean(self):
        for key, indicator in self.indicators.iteritems():
            print indicator
            indicator.hide()

GObject.type_register(Indicators)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

# GTK3 main view for Turpial

import os
import urllib2

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf

from turpial import DESC
from turpial.ui.base import *
from turpial.ui.gtk.dock import Dock
from turpial.ui.gtk.tray import TrayIcon
from turpial.ui.gtk.worker import Worker
from turpial.ui.gtk.container import Container
from turpial.ui.gtk.imageview import ImageView
from turpial.ui.gtk.indicator import Indicators
from turpial.ui.gtk.factory import ImagesFactory

# Dialogs
from turpial.ui.gtk.about import AboutDialog
from turpial.ui.gtk.oauth import OAuthDialog
from turpial.ui.gtk.search import SearchDialog
from turpial.ui.gtk.updatebox import UpdateBox
from turpial.ui.gtk.profiles import ProfileDialog
from turpial.ui.gtk.accounts import AccountsDialog
from turpial.ui.gtk.preferences import PreferencesDialog

#gtk.gdk.set_program_class("Turpial")

GObject.threads_init()

# TODO: Improve all splits for accounts_id with a common function
class Main(Base, Gtk.Window):
    def __init__(self, core):
        Base.__init__(self, core)
        Gtk.Window.__init__(self)

        self.log = logging.getLogger('Gtk')
        self.set_title(DESC)
        self.set_size_request(250, 250)
        self.set_default_size(300, 480)
        self.set_icon(self.load_image('turpial.svg', True))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_gravity(Gdk.Gravity.STATIC)
        self.connect('delete-event', self.__on_close)
        self.connect('key-press-event', self.__on_key_press)
        self.connect('focus-in-event', self.__on_focus)
        #self.connect('size-request', self.__size_request)

        # Configuration
        self.showed = True
        self.minimize = 'on'
        self.is_fullscreen = False

        self.timers = {}
        self.updating = {}
        self.columns = {}

        self.indicator = Indicators()
        self.indicator.connect('main-clicked', self.__on_main_indicator_clicked)
        self.indicator.connect('indicator-clicked', self.__on_indicator_clicked)

        self.openstatuses = {}

        self.worker = Worker()
        self.worker.set_timeout_callback(self.__worker_timeout_callback)
        self.worker.start()

        self.avatars_worker = Worker()
        self.avatars_worker.set_timeout_callback(self.__worker_timeout_callback)
        self.avatars_worker.start()

        self.factory = ImagesFactory(self)

        # Persistent dialogs
        self.accounts_dialog = AccountsDialog(self)
        self.profile_dialog = ProfileDialog(self)
        self.update_box = UpdateBox(self)

        self.imageview = ImageView(self)

        self.tray = TrayIcon(self)
        self.tray.connect("activate", self.__on_tray_click)
        self.tray.connect("popup-menu", self.__show_tray_menu)

        self.dock = Dock(self)
        self._container = Container(self)

        vbox = Gtk.VBox()
        vbox.pack_start(self._container, True, True, 0)
        vbox.pack_start(self.dock, False, False, 0)
        self.add(vbox)

    def __on_close(self, widget, event=None):
        if self.core.minimize_on_close():
            self.showed = False
            if self.unitylauncher.is_supported():
                self.iconify()
            else:
                self.hide()
        else:
            self.main_quit(widget)
        return True

    def __on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname.upper() == 'F' and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.__toogle_fullscreen()
            return True
        return False

    def __toogle_fullscreen(self):
        if self.is_fullscreen:
            self.unfullscreen()
            self.is_fullscreen = False
        else:
            self.fullscreen()
            self.is_fullscreen = True

    #================================================================
    # Tray icon
    #================================================================

    def __on_tray_click(self, widget):
        if self.showed:
            self.showed = False
            self.hide()
        else:
            self.showed = True
            self.show()

    def __show_tray_menu(self, widget, button, activate_time):
        return self.tray.popup(button, activate_time)

    def __on_main_indicator_clicked(self, indicator):
        self.showed = True
        self.show()
        self.present()

    def __on_indicator_clicked(self, indicator, data):
        self.indicator.clean()
        self.__on_main_indicator_clicked(indicator)

    def __on_focus(self, widget, event):
        try:
            self.set_urgency_hint(False)
            self.unitylauncher.set_count_visible(False)
            self.unitylauncher.set_count(0)
        except Exception:
            pass
        self.tray.clear()

    #================================================================
    # Overrided methods
    #================================================================

    def main_loop(self):
        try:
            Gdk.threads_enter()
            Gtk.main()
            Gdk.threads_leave()
        except Exception:
            sys.exit(0)

    def main_quit(self, widget=None, force=False):
        self.log.debug('Exiting...')
        self.unitylauncher.quit()
        self.destroy()
        self.tray = None
        self.worker.quit()
        self.worker.join()
        self.avatars_worker.quit()
        self.avatars_worker.join()
        if widget:
            Gtk.main_quit()
        if force:
            sys.exit(0)

    def show_main(self):
        self.start()
        self.show_all()
        self.update_container()

    def show_notice(self, message, type_):
        pass

    def show_media(self, url):
        self.imageview.loading()
        self.worker.register(self.core.get_media_content, (url, None),
            self.__show_media_callback)

    def show_user_avatar(self, account_id, user):
        self.imageview.loading()
        self.worker.register(self.core.get_profile_image, (account_id, user),
            self.__show_user_avatar_callback)

    def show_user_profile(self, account_id, user):
        self.profile_dialog.loading()
        self.worker.register(self.core.get_user_profile, (account_id, user),
            self.__show_user_profile_callback)

    def login(self, account_id):
        #return
        self.accounts_dialog.update()
        self.worker.register(self.core.login, (account_id), self.__login_callback, account_id)


    #================================================================
    # Hooks definitions
    #================================================================

    def after_delete_account(self, deleted, err_msg=None):
        self.accounts_dialog.done_delete()

    def after_save_account(self, account_id, err_msg=None):
        self.worker.register(self.core.login, (account_id), self.__login_callback, account_id)

    def after_save_column(self, column, err_msg=None):
        self._container.add_column(column)
        self.dock.normal()
        self.tray.normal()
        self.download_stream(column)
        self.__add_timer(column)

    def after_delete_column(self, column_id, err_msg=None):
        self._container.remove_column(column_id)
        if len(self.get_registered_columns()) == 0:
            self.dock.empty()
            self.tray.empty()
        self.__remove_timer(column_id)

    def after_login(self):
        #self.worker.register(self.core.load_all_friends_list, (), self.load_all_friends_response)
        pass

    def after_update_status(self, response, account_id):
        if response.code > 0:
            self.update_box.update_error(response.errmsg)
        else:
            self.update_box.done()

    def after_broadcast_status(self, response):
        bad_acc = []
        good_acc = []
        error = False
        for resp in response:
            if resp.code > 0:
                error = True
                protocol = i18n.get(resp.account_id.split('-')[1])
                bad_acc.append("%s (%s)" % (resp.account_id.split('-')[0], protocol))
            else:
                good_acc.append(resp.account_id)

        if error:
            self.update_box.broadcast_error(good_acc, bad_acc)
        else:
            self.update_box.done()

    def after_direct_message(self, response):
        if response.code > 0:
            self.update_box.update_error(response.errmsg)
        else:
            self.update_box.done()

    def after_favorite(self, response, action):
        # TODO: Check for errors
        if action == self.ACTION_FAVORITE:
            self._container.mark_status_favorite(response.items)
        else:
            self._container.unmark_status_favorite(response.items)

    def after_repeat(self, response, action):
        # TODO: Check for errors
        if action == self.ACTION_REPEAT:
            self._container.mark_status_repeat(response.items)
        else:
            self._container.unmark_status_repeat(response.items)

    def after_delete_status(self, response):
        if response.code > 0:
            # show notice
            # unlock status
            pass
        else:
            self._container.delete_status(response.items)

    def after_autoshort_url(self, response):
        self.update_box.update_after_short_url(response)

    #================================================================
    # Own methods
    #================================================================

    def load_image(self, filename, pixbuf=False):
        img_path = os.path.join(self.images_path, filename)
        pix = GdkPixbuf.Pixbuf.new_from_file(img_path)
        if pixbuf:
            return pix
        avatar = Gtk.Image()
        avatar.set_from_pixbuf(pix)
        del pix
        return avatar

    def show_about_dialog(self, widget=None):
        about_dialog = AboutDialog(self)
        about_dialog.show()

    def show_accounts_dialog(self, widget=None):
        self.accounts_dialog.show()

    def show_preferences_dialog(self, widget=None):
        preferences_dialog = PreferencesDialog(self)
        preferences_dialog.show()

    def show_search_dialog(self, widget=None):
        search_dialog = SearchDialog(self)
        search_dialog.show()

    def show_update_box(self, widget=None, direct=False):
        self.update_box.show()

    def show_update_box_for_reply(self, in_reply_id, account_id, in_reply_user):
        self.update_box.show_for_reply(in_reply_id, account_id, in_reply_user)

    def show_update_box_for_reply_direct(self, in_reply_id, account_id, in_reply_user):
        self.update_box.show_for_reply_direct(in_reply_id, account_id, in_reply_user)

    def show_update_box_for_quote(self, message):
        self.update_box.show_for_quote(message)

    def show_confirm_dialog(self, message, callback, *args):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, message)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            callback(*args)

    def confirm_repeat_status(self, status):
        self.show_confirm_dialog(i18n.get('do_you_want_to_repeat_status'),
            self.repeat_status, status)

    def confirm_unrepeat_status(self, status):
        self.show_confirm_dialog(i18n.get('do_you_want_to_undo_repeat_status'),
            self.unrepeat_status, status)

    def confirm_favorite_status(self, status):
        self.favorite_status(status)

    def confirm_unfavorite_status(self, status):
        self.unfavorite_status(status)

    def confirm_delete_status(self, status):
        self.show_confirm_dialog(i18n.get('do_you_want_to_delete_status'),
            self.delete_status, status)

    def update_column(self, arg, data):
        column, notif, max_ = data

        if arg.code > 0:
            self._container.stop_updating(column.id_, arg.errmsg, 'error')
            print arg.errmsg
            return

        # Notifications
        # FIXME
        count = len(arg.items)

        if count > 0:
            self.log.debug('Updated %s statuses in column %s' % (count, column.id_))
            self._container.update_column(column.id_, arg.items)
        else:
            self.log.debug('Column %s not updated' % column.id_)
            self._container.stop_updating(column.id_)
        #    if notif and self.core.show_notifications_in_updates():
        #        self.notify.updates(column, count)
        #    if self.core.play_sounds_in_updates():
        #        self.sound.updates()
        #    if not self.is_active():
        #        self.unitylauncher.increment_count(count)
        #        self.unitylauncher.set_count_visible(True)
        #    else:
        #        self.unitylauncher.set_count_visible(False)
        #column.inc_size(count)

        # self.restore_open_tweets() ???

    def update_container(self):
        columns = self.get_registered_columns()
        if len(columns) == 0:
            self._container.empty()
            self.dock.empty()
            self.tray.empty()
        else:
            self._container.normal(self.get_accounts_list(), columns)
            self.dock.normal()
            self.tray.normal()

    def fetch_status_avatar(self, status, callback):
        self.worker.register(self.core.get_status_avatar, (status),
            callback)

    #================================================================
    # Callbacks
    #================================================================

    def __login_callback(self, arg, account_id):
        if arg.code > 0:
            # FIXME: Implemente notice
            # self.show_notice(arg.errmsg, 'error')
            self.accounts_dialog.cancel_login(arg.errmsg)
            return

        self.accounts_dialog.status_message(i18n.get('authenticating'))
        auth_obj = arg.items
        if auth_obj.must_auth():
            oauthwin = OAuthDialog(self, self.accounts_dialog.form, account_id)
            oauthwin.connect('response', self.__oauth_callback)
            oauthwin.connect('cancel', self.__cancel_callback)
            oauthwin.open(auth_obj.url)
        else:
            self.__auth_callback(arg, account_id, False)

    def __oauth_callback(self, widget, verifier, account_id):
        self.accounts_dialog.status_message(i18n.get('authorizing'))
        self.worker.register(self.core.authorize_oauth_token, (account_id, verifier), self.__auth_callback, account_id)

    def __cancel_callback(self, widget, reason, account_id):
        self.delete_account(account_id)
        self.accounts_dialog.cancel_login(i18n.get(reason))

    def __auth_callback(self, arg, account_id, register = True):
        if arg.code > 0:
            # FIXME: Implemente notice
            #self.show_notice(msg, 'error')
            self.accounts_dialog.cancel_login(arg.errmsg)
        else:
            self.worker.register(self.core.auth, (account_id), self.__done_callback, (account_id, register))

    def __done_callback(self, arg, userdata):
        (account_id, register) = userdata
        if arg.code > 0:
            self.core.change_login_status(account_id, LoginStatus.NONE)
            self.accounts_dialog.cancel_login(arg.errmsg)
            #self.show_notice(msg, 'error')
        else:
            if register:
                account_id = self.core.name_as_id(account_id)

            self.accounts_dialog.done_login()
            self.accounts_dialog.update()

            response = self.core.get_own_profile(account_id)
            if response.code > 0:
                #self.show_notice(response.errmsg, 'error')
                pass
            else:
                pass
                #if self.core.show_notifications_in_login():
                #    self.notify.login(response.items)

            for col in self.get_registered_columns():
                if col.account_id == account_id:
                    self.download_stream(col, True)
                    self.__add_timer(col)

    def __show_media_callback(self, response):
        if response.err:
            self.imageview.error(response.errmsg)
        else:
            content_obj = response.response
            if content_obj.is_image():
                content_obj.save_content()
                self.imageview.update(content_obj.path)
            elif content_obj.is_video() or content_obj.is_map():
                self.imageview.error('Media not supported yet')

    def __show_user_avatar_callback(self, response):
        if response.code > 0:
            self.imageview.error(response.errmsg)
        else:
            self.imageview.update(response.items)

    def __show_user_profile_callback(self, response):
        if response.code > 0:
            self.profile_dialog.error(response.errmsg)
        else:
            self.profile_dialog.update(response.items)

    def __worker_timeout_callback(self, funct, arg, user_data):
        if user_data:
            GObject.timeout_add(Worker.TIMEOUT, funct, arg, user_data)
        else:
            GObject.timeout_add(Worker.TIMEOUT, funct, arg)

    #================================================================
    # Timer Methods
    #================================================================

    def __add_timer(self, column):
        self.__remove_timer(column.id_)

        interval = self.core.get_update_interval()
        self.timers[column.id_] = GObject.timeout_add(interval * 60 * 1000,
            self.download_stream, column)
        self.log.debug('--Created timer for %s every %i min' % (column.id_, interval))

    def __remove_timer(self, column_id):
        if self.timers.has_key(column_id):
            GObject.source_remove(self.timers[column_id])
            self.log.debug('--Removed timer for %s' % column_id)

    def download_stream(self, column, notif=True):
        if self._container.is_updating(column.id_):
            return True

        last_id = self._container.start_updating(column.id_)
        count = self.core.get_max_statuses_per_column()

        self.worker.register(self.core.get_column_statuses, (column.account_id,
            column.column_name, count, last_id), self.update_column,
            (column, notif, count))
        return True

    def refresh_column(self, column_id):
        for col in self.get_registered_columns():
            if col.slug == column_id:
                self.download_stream(col)

########NEW FILE########
__FILENAME__ = markuplabel
# -*- coding: utf-8 -*-

# GTK3 widget to implement labels with markup in Turpial

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from turpial.ui.gtk.common import *

class MarkupLabel(Gtk.Label):
    def __init__(self, xalign=0, yalign=0.5, act_as_link=False):
        Gtk.Label.__init__(self)

        self.act_as_link = act_as_link
        self.set_use_markup(True)
        self.set_justify(Gtk.Justification.LEFT)
        self.set_alignment(xalign, yalign)
        self.set_line_wrap(True)
        self.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

    def set_error_text(self, text):
        text = escape_text_for_markup(text)
        self.set_markup("<span foreground='#ff0000'>%s</span>" % text) # size='small'

    def set_handy_cursor(self):
        handy_cursor = Gdk.Cursor(Gdk.CursorType.HAND1)
        print handy_cursor
        self.get_window().set_cursor(handy_cursor)
        print self.get_window().get_cursor()

    def show(self):
        Gtk.Label.show(self)
        if self.act_as_link:
            self.set_handy_cursor()

########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -*-

""" Widget to make the OAuth dance from Turpial"""
#
# Author: Wil Alvarez (aka Satanas)

from gi.repository import Gtk
from gi.repository import GObject

from turpial.ui.lang import i18n
from turpial.ui.gtk.htmlview import HtmlView

DELETE_COOKIES_SCRIPT = """
function delete_cookies() {
    var cookies = document.cookie.split(';');
    for (var i=0; i<cookies.length; i++) {
        var cookie = cookies[i];
        console.log(cookie);
    }
}
delete_cookies();
"""

class OAuthDialog(Gtk.Window):
    __gsignals__ = {
        "response": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING, GObject.TYPE_STRING,)),
        "cancel": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING, GObject.TYPE_STRING,)),
    }

    def __init__(self, mainwin, parent, account_id):
        Gtk.Window.__init__(self)

        self.account_id = account_id
        self.mainwin = mainwin
        self.set_title(i18n.get('secure_auth'))
        self.set_default_size(800, 550)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.connect('delete-event', self.__cancel)

        self.view = HtmlView()
        self.view.connect('load-started', self.__started)
        self.view.connect('load-finished', self.__finished)

        self.label = Gtk.Label()
        self.label.set_use_markup(True)
        self.label.set_alignment(0, 0)
        self.label.set_markup(i18n.get('authorize_turpial'))

        self.waiting_label = Gtk.Label()
        self.waiting_label.set_use_markup(True)
        self.waiting_label.set_alignment(1.0, 0.0)

        self.spinner = Gtk.Spinner()

        lblbox = Gtk.HBox(False, 2)
        lblbox.pack_start(self.label, True, True, 2)
        lblbox.pack_start(self.waiting_label, True, True, 2)
        lblbox.pack_start(self.spinner, False, False, 2)

        self.pin = Gtk.Entry()
        cancel = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        cancel.set_size_request(80, 0)
        accept = Gtk.Button(stock=Gtk.STOCK_OK)
        accept.set_size_request(80, 0)
        accept.set_can_default(True)
        accept.grab_default()

        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(self.pin, True, True, 2)
        hbox.pack_start(cancel, False, False, 2)
        hbox.pack_start(accept, False, False, 2)

        vbox = Gtk.VBox(False, 5)
        vbox.pack_start(self.view, True, True, 0)
        vbox.pack_start(lblbox, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)
        vbox.set_property('margin', 10)

        self.pin.connect('activate', self.__accept)
        cancel.connect('clicked', self.__cancel)
        accept.connect('clicked', self.__accept)

        self.add(vbox)
        self.show_all()

    def __cancel(self, widget, event=None):
        self.quit()

    def __accept(self, widget):
        verifier = self.pin.get_text()
        if verifier == '':
            return

        self.quit(verifier)

    def __started(self, widget):
        self.spinner.start()
        self.waiting_label.set_markup(i18n.get('loading'))

    def __finished(self, widget):
        self.spinner.stop()
        self.spinner.hide()
        self.waiting_label.set_markup('')

    def open(self, uri):
        self.view.execute(DELETE_COOKIES_SCRIPT);
        self.view.load(uri)
        self.show_all()
        self.__started(None)

    def quit(self, response=None):
        self.view.stop()
        if response:
            self.emit('response', response, self.account_id)
        else:
            self.emit('cancel', 'login_cancelled', self.account_id)
        self.destroy()


########NEW FILE########
__FILENAME__ = tabs
# -*- coding: utf-8 -*-

""" Preferences tabs for Turpial"""
#
# Author: Wil Alvarez (aka Satanas)

import subprocess


from turpial.ui.lang import i18n
from turpial.ui.gtk.preferences.widgets import *

from libturpial.api.services.shorturl import URL_SERVICES
from libturpial.api.services.uploadpic import PIC_SERVICES

class GeneralTab(GenericTab):
    def __init__(self, current):
        GenericTab.__init__(
            self,
            _('Adjust update frequency for columns'),
            current
        )

        interval = int(self.current['update-interval'])
        tweets = int(self.current['statuses'])
        profile = True if self.current['profile-color'] == 'on' else False
        minimize = True if self.current['minimize-on-close'] == 'on' else False

        self.interval = TimeScroll(_('Update Interval'), interval, unit='min')
        self.tweets = TimeScroll(_('Statuses'), tweets, min=20, max=200)

        self.profile_colors = CheckBox(_('Load profile color'), profile,
            _('Use your profile color for highlighted elements'))
        self.profile_colors.set_sensitive(False)

        self.minimize = CheckBox(_('Minimize to tray'), minimize,
            _('Send Turpial to system tray when closing main window'))

        self.add_child(self.interval, False, False, 5)
        self.add_child(self.tweets, False, False, 5)
        self.add_child(HSeparator(), False, False)
        self.add_child(self.profile_colors, False, False, 2)
        self.add_child(self.minimize, False, False, 2)
        self.show_all()

    def get_config(self):
        minimize = 'on' if self.minimize.get_active() else 'off'
        profile = 'on' if self.profile_colors.get_active() else 'off'

        return {
            'update-interval': int(self.interval.value),
            'profile-color': profile,
            'minimize-on-close': minimize,
            'statuses': int(self.tweets.value),
        }

class NotificationsTab(GenericTab):
    def __init__(self, notif, sounds):
        GenericTab.__init__(
            self,
            _('Select the notifications you want to receive from Turpial'),
            None
        )
        self.notif = notif
        self.sounds = sounds

        nupdates  = True if self.notif['updates'] == 'on' else False
        nlogin = True if self.notif['login'] == 'on' else False
        nicon = True if self.notif['icon'] == 'on' else False
        slogin = True if self.sounds['login'] == 'on' else False
        supdates = True if self.sounds['updates'] == 'on' else False

        self.nupdates = CheckBox(_('Updates'), nupdates,
            _('Show a notification when you get updates'), 10)

        self.nlogin = CheckBox(_('Login'), nlogin,
            _('Show a notification at login with user profile'), 10)

        self.nicon = CheckBox(_('Tray icon'), nicon, 
            _('Change the tray icon when you have notifications'), 10)

        self.slogin = CheckBox(_('Login'), slogin,
            _('Play a sound when you login'), 10)

        self.supdates = CheckBox(_('Updates'), supdates,
            _('Play a sound when you get updates'), 10)

        self.add_child(TitleLabel(_('Notifications')), False, False)
        self.add_child(self.nlogin, False, False, 2)
        self.add_child(self.nupdates, False, False, 2)
        self.add_child(self.nicon, False, False, 2)
        self.add_child(TitleLabel(_('Sounds')), False, False)
        self.add_child(self.slogin, False, False, 2)
        self.add_child(self.supdates, False, False, 2)
        self.show_all()

    def get_config(self):
        nupdates = 'on' if self.nupdates.get_active() else 'off'
        nlogin = 'on' if self.nlogin.get_active() else 'off'
        nicon = 'on' if self.nicon.get_active() else 'off'
        slogin = 'on' if self.slogin.get_active() else 'off'
        supdates = 'on' if self.supdates.get_active() else 'off'

        return {
            'updates': nupdates,
            'login': nlogin,
            'icon': nicon,
        }, {
            'login': slogin,
            'updates': supdates,
        }

class ServicesTab(GenericTab):
    def __init__(self, current):
        GenericTab.__init__(
            self,
            _('Select your preferred services to shorten URLs and to upload images'),
            current
        )

        self.shorten = ComboBox(_('Shorten URL'), URL_SERVICES, self.current['shorten-url'])
        self.upload = ComboBox(_('Upload images'), PIC_SERVICES, self.current['upload-pic'])

        self.add_child(self.shorten, False, False, 2)
        self.add_child(self.upload, False, False, 2)
        self.show_all()

    def get_config(self):
        return {
            'shorten-url': self.shorten.get_active_text(),
            'upload-pic': self.upload.get_active_text(),
        }

class FilterTab(GenericTab):
    def __init__(self, parent):
        GenericTab.__init__(
            self, 
            _("Filter out anything that bothers you")
        )

        self.mainwin = parent

        self.filtered = self.mainwin.get_filters()
        self.updated_filtered = set(self.filtered)

        self.term_input = Gtk.Entry()
        self.term_input.connect('activate', self.__add_filter)

        add_button = Gtk.Button(stock=Gtk.STOCK_ADD)
        add_button.set_size_request(80, -1)
        add_button.connect("clicked", self.__add_filter)
        self.del_button = Gtk.Button(stock=Gtk.STOCK_DELETE)
        self.del_button.set_size_request(80, -1)
        self.del_button.set_sensitive(False)
        self.del_button.connect("clicked", self.__remove_filter)

        input_box = Gtk.HBox()
        input_box.pack_start(self.term_input, True, True, 2)
        input_box.pack_start(add_button, False, False, 0)
        input_box.pack_start(self.del_button, False, False, 0)

        self.model = Gtk.ListStore(str)
        self._list = Gtk.TreeView()
        self._list.set_headers_visible(False)
        self._list.set_level_indentation(0)
        self._list.set_rules_hint(True)
        self._list.set_resize_mode(Gtk.ResizeMode.IMMEDIATE)
        self._list.set_model(self.model)
        self._list.connect('cursor-changed', self.__cursor_changed)

        column = Gtk.TreeViewColumn('')
        column.set_alignment(0.0)
        term = Gtk.CellRendererText()
        column.pack_start(term, True)
        column.add_attribute(term, 'markup', 0)
        self._list.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self._list)

        for filtered_item in self.filtered:
            self.model.append([filtered_item])

        self.add_child(input_box, False, False, 2)
        self.add_child(scroll, True, True, 2)
        self.show_all()

    def __process(self, model, path, iter_):
        filtered_item = model.get_value(iter_, 0)
        self.filtered.append(filtered_item)

    def __cursor_changed(self, widget):
        self.del_button.set_sensitive(True)

    def __add_filter(self, widget):
        new_filter = self.term_input.get_text()
        if (new_filter != '') and (new_filter not in self.updated_filtered):
            self.model.append([new_filter])
            self.updated_filtered.add(new_filter)
        self.term_input.set_text("")
        self.term_input.grab_focus()

    def __remove_filter(self, widget):
        model, term = self._list.get_selection().get_selected()
        if term:
            str_term = self.model.get_value(term, 0)
            self.model.remove(term)
            self.updated_filtered.remove(str_term)
            self.del_button.set_sensitive(False)
            self.term_input.grab_focus()

    def get_filters(self):
        self.filtered = []
        self.model.foreach(self.__process, None)
        return self.filtered

class BrowserTab(GenericTab):
    def __init__(self, parent, current):
        GenericTab.__init__(
            self,
            _('Setup your favorite web browser to open all links'),
            current
        )

        self.mainwin = parent

        chk_default = Gtk.RadioButton.new_with_label_from_widget(None, _('Default web browser'))
        chk_other = Gtk.RadioButton.new_with_label_from_widget(chk_default, _('Choose another web browser'))

        cmd_lbl = Gtk.Label(_('Command'))
        cmd_lbl.set_size_request(90, -1)
        cmd_lbl.set_alignment(1.0, 0.5)
        self.command = Gtk.Entry()
        btn_test = Gtk.Button(_('Test'))
        btn_browse = Gtk.Button(_('Browse'))

        cmd_box = Gtk.HBox(False)
        cmd_box.pack_start(cmd_lbl, False, False, 3)
        cmd_box.pack_start(self.command, True, True, 3)

        buttons_box = Gtk.HButtonBox()
        buttons_box.set_spacing(6)
        buttons_box.set_layout(Gtk.ButtonBoxStyle.END)
        buttons_box.pack_start(btn_test, False, False, 0)
        buttons_box.pack_start(btn_browse, False, False, 0)

        self.other_vbox = Gtk.VBox(False, 2)
        self.other_vbox.pack_start(cmd_box, False, False, 2)
        self.other_vbox.pack_start(buttons_box, False, False, 2)
        self.other_vbox.set_sensitive(False)

        self.add_child(chk_default, False, False, 2)
        self.add_child(chk_other, False, False, 2)
        self.add_child(self.other_vbox, False, False, 2)

        if current['cmd'] != '':
            self.other_vbox.set_sensitive(True)
            self.command.set_text(current['cmd'])
            chk_other.set_active(True)

        btn_browse.connect('clicked', self.__browse)
        btn_test.connect('clicked', self.__test)
        chk_default.connect('toggled', self.__activate, 'default')
        chk_other.connect('toggled', self.__activate, 'other')

        self.show_all()

    def __test(self, widget):
        cmd = self.command.get_text()
        if cmd != '':
            subprocess.Popen([cmd, 'http://turpial.org.ve/'])

    def __browse(self, widget):
        dia = Gtk.FileChooserDialog(
            title = _('Select the full path of your web browser'),
            parent=self.mainwin,
            action=Gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.RESPONSE_CANCEL,
                Gtk.STOCK_OK, Gtk.RESPONSE_OK))
        resp = dia.run()

        if resp == Gtk.RESPONSE_OK:
            self.command.set_text(dia.get_filename())
        dia.destroy()

    def __activate(self, widget, param):
        if param == 'default':
            self.other_vbox.set_sensitive(False)
            self.command.set_text('')
        else:
            self.other_vbox.set_sensitive(True)

    def get_config(self):
        return {
            'cmd': self.command.get_text()
        }

class AdvancedTab(GenericTab):
    def __init__(self, mainwin, current):
        GenericTab.__init__(
            self,
            _('Advanced options. Use it only if you know what you do'),
            current
        )
        self.mainwin = mainwin
        cache_size = self.mainwin.get_cache_size()
        label = "%s <span foreground='#999999'>%s</span>" % (
            i18n.get('delete_all_images_in_cache'),
            cache_size)
        self.cachelbl = Gtk.Label()
        self.cachelbl.set_use_markup(True)
        self.cachelbl.set_markup(label)
        self.cachelbl.set_alignment(0.0, 0.5)
        self.cachebtn = Gtk.Button(_('Clean cache'))
        self.cachebtn.set_size_request(110, -1)
        self.cachebtn.connect('clicked', self.__clean_cache)
        if cache_size == '0 B':
            self.cachebtn.set_sensitive(False)

        configlbl = Gtk.Label(_('Restore config to default'))
        configlbl.set_alignment(0.0, 0.5)
        self.configbtn = Gtk.Button(_('Restore config'))
        self.configbtn.set_size_request(110, -1)
        self.configbtn.connect('clicked', self.__restore_default_config)

        table = Gtk.Table(2, 2, False)
        table.attach(self.cachebtn, 0, 1, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(self.cachelbl, 1, 2, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, xpadding=5)
        table.attach(self.configbtn, 0, 1, 1, 2, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(configlbl, 1, 2, 1, 2, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, xpadding=5)

        timeout = int(self.current['socket-timeout'])
        show_avatars = True if self.current['show-user-avatars'] == 'on' else False

        self.timeout = TimeScroll(_('Timeout'), timeout, min=5, max=120,
            unit='sec', lbl_size=120)

        self.show_avatars = CheckBox(_('Load user avatars'), show_avatars, 
            _('Disable loading user avatars for slow connections'))
        self.show_avatars.set_sensitive(False)

        self.add_child(TitleLabel(_('Maintenance')), False, False, 2)
        self.add_child(table, False, False, 2)
        self.add_child(TitleLabel(_('Connection')), False, False, 2)
        self.add_child(self.timeout, False, False, 2)
        self.add_child(self.show_avatars, False, False, 2)
        self.show_all()

    def __clean_cache(self, widget):
        self.mainwin.delete_all_cache()
        self.cachebtn.set_sensitive(False)
        label = "%s <span foreground='#999999'>%s</span>" % (
            i18n.get('delete_all_images_in_cache'),
            self.mainwin.get_cache_size())
        self.cachelbl.set_markup(label)

    def __restore_default_config(self, widget):
        message = Gtk.MessageDialog(self.mainwin, Gtk.DIALOG_MODAL |
            Gtk.DIALOG_DESTROY_WITH_PARENT, Gtk.MESSAGE_QUESTION,
            Gtk.BUTTONS_YES_NO)
        message.set_markup(i18n.get('restore_config_warning'))
        response = message.run()
        message.destroy()
        if response == Gtk.RESPONSE_YES:
            self.mainwin.restore_default_config()
            self.configbtn.set_sensitive(False)
            self.mainwin.main_quit(force=True)

    def get_config(self):
        show_avatars = 'on' if self.show_avatars.get_active() else 'off'

        return {
            'socket-timeout': int(self.timeout.value),
            'show-user-avatars': show_avatars,
        }

class ProxyTab(GenericTab):
    def __init__(self, current):
        GenericTab.__init__(
            self,
            _('Proxy settings for Turpial (Need Restart)'),
            current
        )

        self.server = ProxyField(_('Server/Port'), current['server'],
            current['port'])
        self.username = FormField(_('Username'), current['username'])
        self.password = FormField(_('Password'), current['password'], True)

        self.add_child(self.server, False, False, 2)
        self.add_child(self.username, False, False, 2)
        self.add_child(self.password, False, False, 2)

        self.show_all()

    def get_config(self):
        server, port = self.server.get_proxy()
        return {
            'username': self.username.get_text(),
            'password': self.password.get_text(),
            'server': server,
            'port': port,
        }


########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-

""" Preferences widgets for Turpial"""
#
# Author: Wil Alvarez (aka Satanas)

from gi.repository import Gtk

class GenericTab(Gtk.VBox):
    def __init__(self, desc, current=None):
        Gtk.VBox.__init__(self, False)

        self.current = current
        description = Gtk.Label()
        description.set_line_wrap(True)
        description.set_use_markup(True)
        description.set_markup(desc)
        description.set_justify(Gtk.Justification.FILL)

        desc_align = Gtk.Alignment(xalign=0.0, yalign=0.0)
        desc_align.set_padding(0, 5, 10, 10)
        desc_align.add(description)

        self._container = Gtk.VBox(False, 2)

        hbox = Gtk.HBox(False, 10)
        hbox.pack_start(self._container, True, True, 10)

        self.pack_start(desc_align, False, False, 5)
        self.pack_start(hbox, True, True, 0)

    def add_child(self, child, expand=True, fill=True, padding=0):
        self._container.pack_start(child, expand, fill, padding)

    def get_config(self):
        raise NotImplemented

class TitleLabel(Gtk.Alignment):
    def __init__(self, text, padding=0):
        Gtk.Alignment.__init__(self, xalign=0.0, yalign=0.0)
        caption ="<b>%s</b>" % text
        label = Gtk.Label()
        label.set_line_wrap(True)
        label.set_use_markup(True)
        label.set_markup(caption)
        label.set_justify(Gtk.Justification.FILL)

        self.set_padding(10, 0, padding, 0)
        self.add(label)

class CheckBox(Gtk.Alignment):
    def __init__(self, title, is_active, tooltip, padding=0):
        Gtk.Alignment.__init__(self)
        self.set_padding(0, 0, padding, 0)

        self.checkbtn = Gtk.CheckButton(title)
        self.checkbtn.set_active(is_active)
        try:
            self.checkbtn.set_has_tooltip(True)
            self.checkbtn.set_tooltip_text(tooltip)
        except Exception:
            pass
        self.add(self.checkbtn)

    def get_active(self):
        return self.checkbtn.get_active()

class ComboBox(Gtk.HBox):
    def __init__(self, caption, array, current):
        Gtk.HBox.__init__(self, False)
        i = 0
        default = -1
        lbl = Gtk.Label(caption)
        lbl.set_alignment(0.0, 0.5)
        self.combo = Gtk.ComboBoxText()
        self.combo.set_size_request(180, -1)
        for key, v in array.iteritems():
            self.combo.append_text(key)
            if key == current:
                default = i
            i += 1
        self.combo.set_active(default)

        self.pack_start(self.combo, False, False, 5)
        self.pack_start(lbl, True, True, 5)

    def get_active_text(self):
        return self.combo.get_active_text()

class FormField(Gtk.HBox):
    def __init__(self, caption, current, password=False):
        Gtk.HBox.__init__(self, False)
        lbl = Gtk.Label(caption)
        lbl.set_alignment(0.0, 0.5)
        self.entry = Gtk.Entry()
        if password:
            self.entry.set_visibility(False)
        self.entry.set_size_request(180, -1)
        self.entry.set_text(current)

        self.pack_start(self.entry, False, False, 2)
        self.pack_start(lbl, True, True, 5)

    def get_text(self):
        return self.entry.get_text()

class ProxyField(Gtk.HBox):
    def __init__(self, caption, server, port):
        Gtk.HBox.__init__(self, False)
        lbl = Gtk.Label(caption)
        lbl.set_alignment(0.0, 0.5)
        self.server = Gtk.Entry()
        self.server.set_size_request(130, -1)
        self.server.set_text(server)

        self.port = Gtk.Entry()
        self.port.set_size_request(50, -1)
        self.port.set_text(port)

        self.pack_start(self.server, False, False, 2)
        self.pack_start(self.port, False, False, 2)
        self.pack_start(lbl, True, True, 5)

    def get_proxy(self):
        return self.server.get_text(), self.port.get_text()

class HSeparator(Gtk.HBox):
    def __init__(self, spacing=15):
        Gtk.HBox.__init__(self, False)
        self.set_size_request(-1, spacing)

class TimeScroll(Gtk.HBox):
    def __init__(self, caption='', val=5, min=1, max=60, step=3, page=6, size=0, lbl_size=150, unit=''):
        Gtk.HBox.__init__(self, False)

        self.value = val
        self.unit = unit
        self.caption = caption

        self.label = Gtk.Label()
        self.label.set_size_request(lbl_size, -1)
        self.label.set_alignment(xalign=0.0, yalign=0.5)
        self.label.set_use_markup(True)

        adj = Gtk.Adjustment(val, min, max, step, page, size)
        scale = Gtk.HScale()
        scale.set_draw_value(False)
        scale.set_adjustment(adj)
        scale.set_property('value-pos', Gtk.PositionType.RIGHT)

        self.pack_start(scale, True, True, 3)
        self.pack_start(self.label, False, False, 3)

        self.show_all()
        self.__on_change(scale)
        scale.connect('value-changed', self.__on_change)

    def __on_change(self, widget):
        self.value = widget.get_value()
        label = "%s <span foreground='#999999'>%i %s</span>" % (self.caption,
            self.value, self.unit)
        self.label.set_markup(label)


########NEW FILE########
__FILENAME__ = profiles
# -*- coding: utf-8 -*-

# GTK profile dialog for Turpial
#
# Author: Wil Alvarez (aka Satanas)

import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n
from turpial.ui.gtk.common import *
from turpial.ui.gtk.markuplabel import MarkupLabel

log = logging.getLogger('Gtk')

BORDER_WIDTH = 8

class ProfileDialog(Gtk.Window):
    STATUS_IDLE = 0
    STATUS_LOADING = 1
    STATUS_LOADED = 2

    def __init__(self, base):
        Gtk.Window.__init__(self)

        self.base = base
        self.window_width = 300
        self.set_title(i18n.get('user_profile'))
        self.set_default_size(self.window_width, 250)
        #self.set_resizable(False)
        self.set_icon(self.base.load_image('turpial.png', True))
        self.set_transient_for(self.base)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_gravity(Gdk.Gravity.STATIC)
        self.connect('delete-event', self.__close)
        #self.connect('key-press-event', self.__key_pressed)

        self.profile_box = ProfileBox(self.base)

        # Error stuffs
        self.error_msg = Gtk.Label()
        self.error_msg.set_alignment(0.5, 0.5)

        self.spinner = Gtk.Spinner()

        self.loading_box = Gtk.Box(spacing=0)
        self.loading_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.loading_box.pack_start(self.spinner, True, False, 0)
        self.loading_box.pack_start(self.error_msg, True,True, 0)

        self.showed = False

    def __close(self, widget, event=None):
        self.showed = False
        self.hide()
        return True

    def __key_pressed(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.__close(widget)

    def __clear(self):
        current_child = self.get_child()
        if current_child:
            self.remove(current_child)
        self.status = self.STATUS_IDLE
        self.error_msg.hide()

    def loading(self):
        self.__clear()
        self.spinner.start()
        self.add(self.loading_box)
        self.status = self.STATUS_LOADING
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.show_all()

    def update(self, profile):
        self.__clear()
        self.add(self.profile_box)
        self.profile_box.update(profile)
        self.show_all()

        self.status = self.STATUS_LOADED
        self.present()

    def show(self, profile):
        if self.showed:
            self.present()
        else:
            self.showed = True
            self.show_all()
            self.update(profile)

    def error(self, error=''):
        if error:
            self.error_msg.set_label(error)
        else:
            self.error_msg.set_label(i18n.get('error_loading_profile'))
        self.spinner.stop()
        self.spinner.hide()


    def quit(self):
        self.destroy()

class ProfileBox(Gtk.VBox):
    def __init__(self, base):
        Gtk.VBox.__init__(self, spacing=0)

        self.base = base
        self.avatar = Gtk.Image()
        self.avatar.set_margin_right(AVATAR_MARGIN)
        # This resize is to avoid bad redimentioning on parent window
        self.set_size_request(300, -1)
        avatar_box = Gtk.Alignment()
        avatar_box.add(self.avatar)
        avatar_box.set(0.5, 0, -1, -1)
        #avatar_box.connect('button-press-event', self.__on_click_avatar)

        self.favorited_mark = Gtk.Image()
        self.protected_mark = Gtk.Image()
        self.verified_mark = Gtk.Image()
        self.reposted_mark = Gtk.Image()
        self.repeated_mark = Gtk.Image()

        self.username = MarkupLabel()
        self.username.set_ellipsize(Pango.EllipsizeMode.END)
        self.fullname = MarkupLabel()

        fullname_box = Gtk.HBox()
        fullname_box.pack_start(self.fullname, False, False, 2)
        fullname_box.pack_start(self.verified_mark, False, False, 2)
        fullname_box.pack_start(self.protected_mark, False, False, 0)

        userdata_box = Gtk.VBox()
        userdata_box.pack_start(fullname_box, False, False, 2)
        userdata_box.pack_start(self.username, False, False, 2)

        header_box = Gtk.HBox()
        header_box.set_border_width(BORDER_WIDTH)
        header_box.pack_start(avatar_box, False, False, 0)
        header_box.pack_start(userdata_box, False, False, 0)

        self.bio = DescriptionBox(self.base, 'icon-bio.png', i18n.get('bio'))
        self.location = DescriptionBox(self.base, 'icon-location.png', i18n.get('location'))
        self.web = DescriptionBox(self.base, 'icon-home.png', i18n.get('web'))

        desc_box = Gtk.VBox(spacing=0)
        desc_box.set_border_width(BORDER_WIDTH)
        desc_box.pack_start(self.bio, False, False, 0)
        desc_box.pack_start(self.location, False, False, 0)
        desc_box.pack_start(self.web, False, False, 0)

        self.following = StatBox(i18n.get('following'))
        self.followers = StatBox(i18n.get('followers'))
        self.statuses = StatBox(i18n.get('statuses'))
        self.favorites = StatBox(i18n.get('favorites'))

        stats_box = Gtk.HBox(spacing=0)
        stats_box.set_border_width(BORDER_WIDTH)
        stats_box.pack_start(self.following, True, True, 0)
        stats_box.pack_start(Gtk.VSeparator(), False, False, 2)
        stats_box.pack_start(self.followers, True, True, 0)
        stats_box.pack_start(Gtk.VSeparator(), False, False, 2)
        stats_box.pack_start(self.statuses, True, True, 0)
        stats_box.pack_start(Gtk.VSeparator(), False, False, 2)
        stats_box.pack_start(self.favorites, True, True, 0)

        self.pack_start(header_box, False, False, 0)
        self.pack_start(Gtk.HSeparator(), False, False, 0)
        self.pack_start(desc_box, False, False, 0)
        self.pack_start(Gtk.HSeparator(), False, False, 0)
        self.pack_start(stats_box, False, False, 0)

    def update(self, profile):
        self.base.fetch_status_avatar(profile, self.update_avatar)

        self.avatar.set_from_pixbuf(self.base.load_image('unknown.png', True))
        name = '<span size="9000" foreground="%s"><b>%s</b></span>' % (
            self.base.get_color_scheme('links'), profile.fullname
        )
        self.fullname.set_markup(name)
        self.username.set_markup('@' + profile.username)
        if profile.bio != '':
            self.bio.set_description(profile.bio)
        if profile.location != '':
            self.location.set_description(profile.location)
        if profile.url:
            self.web.set_description(profile.url, True)

        # After showing all widgets we set the marks
        if profile.protected:
            self.set_protected_mark(True)
        else:
            self.set_protected_mark(False)

        if profile.verified:
            self.set_verified_mark(True)
        else:
            self.set_verified_mark(False)

        self.following.set_value(profile.friends_count)
        self.followers.set_value(profile.followers_count)
        self.statuses.set_value(profile.statuses_count)
        self.favorites.set_value(profile.favorites_count)

    def update_avatar(self, response):
        if response.code == 0:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(response.items, 48, 48, True)
            self.avatar.set_from_pixbuf(pix)
            del pix

    def set_protected_mark(self, value):
        if value:
            self.protected_mark.set_from_pixbuf(self.base.load_image('mark-protected.png', True))
        else:
            self.protected_mark.set_from_pixbuf(None)

    def set_verified_mark(self, value):
        if value:
            self.verified_mark.set_from_pixbuf(self.base.load_image('mark-verified.png', True))
        else:
            self.verified_mark.set_from_pixbuf(None)

class DescriptionBox(Gtk.VBox):
    def __init__(self, base, image, caption):
        Gtk.VBox.__init__(self, spacing=0)

        icon = Gtk.Image()
        icon.set_from_pixbuf(base.load_image(image, True))
        title = MarkupLabel()
        title.set_markup('<b>%s</b>' % caption)
        self.description = MarkupLabel()
        self.description.set_margin_bottom(10)

        title_box = Gtk.HBox()
        title_box.set_margin_bottom(4)
        title_box.pack_start(icon, False, False, 0)
        title_box.pack_start(title, False, False, 5)

        desc_box = Gtk.HBox()
        desc_box.pack_start(self.description, True, True, 0)

        self.pack_start(title_box, False, False, 0)
        self.pack_start(desc_box, False, False, 0)

    def set_description(self, message, as_link=False):
        if as_link:
            self.description.set_markup('<a href="%s">%s</a>' % (message, message))
        else:
            self.description.set_markup(message)

class StatBox(Gtk.VBox):
    def __init__(self, caption):
        Gtk.VBox.__init__(self, spacing=0)

        self.value = MarkupLabel(xalign=0.5)
        self.value.set_margin_bottom(6)
        self.caption = MarkupLabel(xalign=0.5)
        self.caption.set_text(caption)

        self.pack_start(self.value, False, False, 0)
        self.pack_start(self.caption, False, False, 0)

    def set_value(self, value):
        self.value.set_markup('<b>%s</b>' % value)


########NEW FILE########
__FILENAME__ = search
# -*- coding: utf-8 -*-

# GTK search for Turpial
#
# Author: Wil Alvarez (aka Satanas)

import urllib2
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n
from turpial.ui.gtk.markuplabel import MarkupLabel

from libturpial.common import ColumnType
from libturpial.common import LoginStatus

log = logging.getLogger('Gtk')

class SearchDialog(Gtk.Window):
    def __init__(self, base):
        Gtk.Window.__init__(self)

        self.base = base
        self.set_title(i18n.get('search'))
        self.set_size_request(300, 120)
        self.set_resizable(False)
        self.set_icon(self.base.load_image('turpial.png', True))
        self.set_transient_for(base)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_gravity(Gdk.Gravity.STATIC)
        self.set_modal(True)
        self.connect('delete-event', self.__close)

        alabel = Gtk.Label(i18n.get('account'))
        clabel = Gtk.Label(i18n.get('criteria'))

        alist = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        for acc in self.base.get_accounts_list():
            image = '%s.png' % acc.split('-')[1]
            icon = self.base.load_image(image, True)
            alist.append([icon, acc.split('-')[0], acc])

        self.account = Gtk.ComboBox()
        self.account.set_model(alist)
        icon = Gtk.CellRendererPixbuf()
        txt = Gtk.CellRendererText()
        self.account.pack_start(icon, False)
        self.account.pack_start(txt, False)
        self.account.add_attribute(icon, 'pixbuf', 0)
        self.account.add_attribute(txt, 'markup', 1)
        self.account.connect('changed', self.__reset_error)

        self.criteria = Gtk.Entry()
        self.criteria.connect('activate', self.__on_add)
        self.criteria.set_tooltip_text(i18n.get('search_criteria_tooltip'))
        self.criteria.connect('changed', self.__reset_error)

        help_text = i18n.get('this_search_support_advanced_operators')
        help_text += ' "", OR, -, from, to, filter, source, place, since, until. '
        help_text += i18n.get('for_more_information_visit')
        help_text += " <a href='https://dev.twitter.com/docs/using-search'>%s</a>" % (
            i18n.get('twitter_search_documentation'))

        help_label = MarkupLabel()
        help_label.set_markup(help_text)
        help_label.set_margin_top(10)
        help_label.set_size_request(300, -1)

        self.error_message = MarkupLabel(xalign=0.5)

        table = Gtk.Table(3, 2, False)
        table.attach(alabel, 0, 1, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(self.account, 1, 2, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(clabel, 0, 1, 1, 2, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(self.criteria, 1, 2, 1, 2, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        table.attach(help_label, 0, 2, 2, 3, Gtk.AttachOptions.SHRINK)
        table.set_margin_top(4)
        table.set_row_spacing(0, 2)
        table.set_row_spacing(1, 2)

        self.btn_add = Gtk.Button(i18n.get('add'))
        self.btn_close = Gtk.Button(i18n.get('close'))

        self.btn_add.connect('clicked', self.__on_add)
        self.btn_close.connect('clicked', self.__close)

        box_button = Gtk.HButtonBox()
        box_button.set_spacing(6)
        box_button.set_layout(Gtk.ButtonBoxStyle.END)
        box_button.pack_start(self.btn_close, False, False, 0)
        box_button.pack_start(self.btn_add, False, False, 0)
        box_button.set_margin_top(10)

        vbox = Gtk.VBox(False)
        vbox.set_border_width(6)
        vbox.pack_start(table, False, False, 0)
        vbox.pack_start(self.error_message, False, False, 5)
        vbox.pack_start(box_button, False, False, 0)
        self.add(vbox)

    def __close(self, widget, event=None):
        self.destroy()
        return True

    def __reset_error(self, widget=None):
        self.error_message.set_markup('')

    def __on_add(self, widget, event=None):
        model = self.account.get_model()
        index = self.account.get_active()
        criteria = self.criteria.get_text()
        if index < 0 or criteria == '':
            self.error_message.set_error_text(i18n.get('fields_cant_be_empty'))
            self.error_message.set_size_request(-1, 10)
        else:
            account_id = model[index][2]
            column_id = "%s-%s:%s" % (account_id, ColumnType.SEARCH, urllib2.quote(criteria))
            self.base.save_column(column_id)
            self.__close(None)

    def show(self):
        self.show_all()

########NEW FILE########
__FILENAME__ = statusmenu
# -*- coding: utf-8 -*-

# GTK3 widget to implement status menu in Turpial

from gi.repository import Gtk

from turpial.ui.lang import i18n
from turpial.ui.gtk.common import *

from libturpial.common import StatusType, ProtocolType

class StatusMenu(Gtk.Menu):
    def __init__(self, base, status, in_progress):
        Gtk.Menu.__init__(self)

        self.base = base
        # Detect if current status is performing some operation
        for k,v in in_progress.iteritems():
            if v:
                self.__busy_item(i18n.get(k))
                return

        if status._type == StatusType.NORMAL:
            self.__normal(status)
        elif status._type == StatusType.DIRECT:
            self.__direct_message(status)

    def __busy_item(self, text):
        busymenu = Gtk.MenuItem(text)
        busymenu.set_sensitive(False)
        self.append(busymenu)

    def __reply_item(self, status, direct=False):
        if not status.is_own:
            item = Gtk.MenuItem(i18n.get('reply'))
            if direct:
                item.connect('activate', self.__on_reply_direct, status)
            else:
                item.connect('activate', self.__on_reply, status)
            self.append(item)

    def __repeat_item(self, status):
        # TODO: Validates if is protected
        if not status.is_own:
            if status.get_protocol_id() == ProtocolType.TWITTER:
                qt = "RT @%s %s" % (status.username, status.text)
                if status.retweeted:
                    repeat = Gtk.MenuItem(i18n.get('retweeted'))
                    repeat.connect('activate', self.__on_unrepeat, status)
                else:
                    repeat = Gtk.MenuItem(i18n.get('retweet'))
                    repeat.connect('activate', self.__on_repeat, status)
            elif status.get_protocol_id() == ProtocolType.IDENTICA:
                qt = "RD @%s %s" % (status.username, status.text)
                if status.repeated:
                    repeat = Gtk.MenuItem(i18n.get('redented'))
                    repeat.connect('activate', self.__on_unrepeat, status)
                else:
                    repeat = Gtk.MenuItem(i18n.get('redent'))
                    repeat.connect('activate', self.__on_repeat, status)

            quote = Gtk.MenuItem(i18n.get('quote'))
            quote.connect('activate', self.__on_quote, qt)

            self.append(repeat)
            self.append(quote)

    def __fav_item(self, status):
        if status.favorited:
            unfav = Gtk.MenuItem(i18n.get('favorited'))
            unfav.connect('activate', self.__on_unfavorite, status)
            self.append(unfav)
        else:
            fav = Gtk.MenuItem(i18n.get('favorite'))
            fav.connect('activate', self.__on_favorite, status)
            self.append(fav)


    def __conversation_item(self, status):
        if status.in_reply_to_id:
            in_reply = Gtk.MenuItem(i18n.get('view_conversation'))
            self.append(in_reply)

    def __delete_item(self, status):
        if status.is_own:
            delete = Gtk.MenuItem(i18n.get('delete'))
            delete.connect('activate', self.__on_delete, status)
            self.append(delete)

    def __delete_message_item(self, status):
        if status.is_own:
            delete = Gtk.MenuItem(i18n.get('delete'))
            delete.connect('activate', self.__on_delete_message, status)
            self.append(delete)

    def __delete_direct_message_item(self, status):
        delete = Gtk.MenuItem(i18n.get('delete'))
        self.append(delete)

    # Callbacks

    def __on_reply(self, widget, status):
        self.base.show_update_box_for_reply(status.in_reply_to_id,
                status.account_id, ' '.join(map(lambda x: '@' + x, status.get_mentions())))

    def __on_reply_direct(self, widget, status):
        self.base.show_update_box_for_reply_direct(status.in_reply_to_id,
                status.account_id, ' '.join(status.get_mentions()))

    def __on_quote(self, widget, message):
        self.base.show_update_box_for_quote(message)

    def __on_repeat(self, widget, status):
        self.base.confirm_repeat_status(status)

    def __on_unrepeat(self, widget, status):
        self.base.confirm_unrepeat_status(status)

    def __on_favorite(self, widget, status):
        self.base.confirm_favorite_status(status)

    def __on_unfavorite(self, widget, status):
        self.base.confirm_unfavorite_status(status)

    def __on_delete(self, widget, status):
        self.base.confirm_delete_status(status)

    def __on_delete_message(self, widget, status):
        pass

    # Methods to build menu

    def __normal(self, status):
        self.__reply_item(status)
        self.__repeat_item(status)
        self.__delete_item(status)
        self.__fav_item(status)
        self.__conversation_item(status)

    def __direct_message(self, status):
        self.__reply_item(status, True)
        self.__delete_direct_message_item(status)



########NEW FILE########
__FILENAME__ = statuswidget
# -*- coding: utf-8 -*-

# GTK3 widget to implement statuses in Turpial

import re

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf

from turpial.ui.lang import i18n
from turpial.ui.gtk.common import *
from turpial.ui.gtk.statusmenu import StatusMenu
#from turpial.ui.gtk.imagebutton import ImageButton
from turpial.ui.gtk.markuplabel import MarkupLabel


class StatusWidget(Gtk.EventBox):
    def __init__(self, base, status):
        Gtk.EventBox.__init__(self)

        self.base = base
        self.status = status
        self.set_margin_bottom(OUTTER_BOTTOM_MARGIN)
        self.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(65535, 65535, 65535))

        # Variables to control work in progress over the status
        self.in_progress = {
            StatusProgress.FAVING:  False,
            StatusProgress.UNFAVING: False,
            StatusProgress.RETWEETING: False,
            StatusProgress.UNRETWEETING: False,
            StatusProgress.DELETING: False,
        }

        self.avatar = Gtk.Image()
        self.avatar.set_margin_right(AVATAR_MARGIN)
        self.avatar_box = Gtk.Alignment()
        self.avatar_box.add(self.avatar)
        self.avatar_box.set(0.5, 0, -1, -1)

        self.favorited_mark = Gtk.Image()
        self.protected_mark = Gtk.Image()
        self.verified_mark = Gtk.Image()
        self.reposted_mark = Gtk.Image()
        self.repeated_mark = Gtk.Image()

        self.username = MarkupLabel(act_as_link=True)
        self.username.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_text = MarkupLabel()
        self.footer = MarkupLabel()

        # Setting user image
        self.avatar.set_from_pixbuf(self.base.load_image('unknown.png', True))
        # Building the status style
        user = '<span size="9000" foreground="%s"><b>%s</b></span>' % (
            self.base.get_color_scheme('links'), status.username
        )
        self.username.set_markup(user)

        text = status.text.replace('&gt;', '>')
        text = text.replace('&lt;', '<')
        pango_text = '<span size="9000">%s</span>' % escape_text_for_markup(text)
        pango_text = self.__highlight_urls(status, pango_text)
        pango_text = self.__highlight_hashtags(status, pango_text)
        pango_text = self.__highlight_groups(status, pango_text)
        pango_text = self.__highlight_mentions(status, pango_text)
        self.status_text.set_markup(pango_text)

        footer = '<span size="small" foreground="#999">%s' % status.datetime
        if status.source:
            footer += ' %s %s' % (_('from'), status.source.name)
        if status.in_reply_to_user:
            footer += ' %s %s' % (_('in reply to'), status.in_reply_to_user)
        if status.reposted_by:
            footer += '\n%s %s' % (_('Retweeted by'), status.reposted_by)
        footer += '</span>'
        self.footer.set_markup(footer)

        starbox = Gtk.HBox()
        starbox.pack_start(self.repeated_mark, False, False, 2)
        starbox.pack_start(self.favorited_mark, False, False, 2)

        staralign = Gtk.Alignment()
        staralign.set(1, -1, -1, -1)
        staralign.add(starbox)

        header = Gtk.HBox()
        header.pack_start(self.reposted_mark, False, False, 2)
        header.pack_start(self.username, False, False, 2)
        header.pack_start(self.verified_mark, False, False, 2)
        header.pack_start(self.protected_mark, False, False, 0)
        header.pack_start(staralign, True, True, 0)

        content = Gtk.VBox()
        content.pack_start(header, False, False, 0)
        content.pack_start(self.status_text, True, True, 0)
        content.pack_start(self.footer, False, False, 0)

        box = Gtk.HBox()
        box.pack_start(self.avatar_box, False, False, 0)
        box.pack_start(content, True, True, 0)

        bbox = Gtk.VBox()
        bbox.pack_start(box, True, True, 0)
        self.add(bbox)
        self.show_all()

        # After showing all widgets we set the marks
        self.set_favorited_mark(status.favorited)
        self.set_protected_mark(status.protected)
        self.set_verified_mark(status.verified)
        self.set_repeated_mark(status.repeated)
        self.set_reposted_mark(status.reposted_by)

        self.connect('button-release-event', self.__on_click)
        self.click_url_handler = self.status_text.connect('activate-link', self.__open_url)
        self.click_avatar_handler = self.avatar_box.connect('button-press-event', self.__on_click_avatar)
        self.click_username_handler = self.username.connect('button-release-event', self.__on_click_username)

        self.base.fetch_status_avatar(status, self.update_avatar)

    def __on_click_username(self, widget, event=None):
        print 'clicked username', widget, event

    def __on_click(self, widget, event=None, data=None):
        # Capture clicks for avatar
        if event.x <= 48 and event.y <= 48 and event.button == 1:
            self.__on_click_avatar()
            return True
        print event.x, event.y
        if event.button != 3:
            return False
        self.menu = StatusMenu(self.base, self.status, self.in_progress)
        self.menu.show_all()
        self.menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def __on_click_avatar(self):
        self.base.show_user_avatar(self.status.account_id, self.status.username)

    def __highlight_urls(self, status, text):
        for url in status.entities['urls']:
            if url.url == None:
                url.url = url.search_for
            cad = "<a href='%s'>%s</a>" % (escape_text_for_markup(url.url), escape_text_for_markup(url.display_text))
            text = text.replace(url.search_for, cad)
        return text

    def __highlight_hashtags(self, status, text):
        for h in status.entities['hashtags']:
            url = "%s-search:%%23%s" % (self.status.account_id, h.display_text[1:])
            cad = '<a href="hashtags:%s">%s</a>' % (url, h.display_text)
            text = text.replace(h.search_for, cad)
        return text

    def __highlight_groups(self, status, text):
        for h in status.entities['groups']:
            cad = '<a href="groups:%s">%s</a>' % (h.url, h.display_text)
            text = text.replace(h.search_for, cad)
        return text

    def __highlight_mentions(self, status, text):
        for h in status.entities['mentions']:
            args = "%s:%s" % (status.account_id, h.display_text[1:])
            cad = '<a href="profile:%s">%s</a>' % (args, h.display_text)
            pattern = re.compile(h.search_for, re.IGNORECASE)
            text = pattern.sub(cad, text)
        return text

    def __open_url(self, widget, url):
        if url.startswith('http'):
            self.base.open_url(url)
        elif url.startswith('hashtag'):
            column_id = url.replace('hashtags:', '')
            self.base.save_column(column_id)
        elif url.startswith('groups'):
            print "Opening groups"
        elif url.startswith('profile'):
            url = url.replace('profile:', '')
            account_id = url.split(':')[0]
            username = url.split(':')[1]
            self.base.show_user_profile(account_id, username)
        return True

    def __del__(self):
        print 'garbage collected'

    def release(self):
        self.avatar_box.disconnect(self.click_avatar_handler)
        self.username.disconnect(self.click_username_handler)
        self.status_text.disconnect(self.click_url_handler)


    def update(self, status):
        self.status = status
        # render again

    def update_avatar(self, response):
        if response.code == 0:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(response.items, 48, 48, True)
            self.avatar.set_from_pixbuf(pix)
            del pix

    def set_favorited_mark(self, value):
        if value:
            self.favorited_mark.set_from_pixbuf(self.base.load_image('mark-favorite.png', True))
        else:
            self.favorited_mark.set_from_pixbuf(None)
        self.status.favorited = value

    def set_repeated_mark(self, value):
        if value:
            self.repeated_mark.set_from_pixbuf(self.base.load_image('mark-repeated.png', True))
        else:
            self.repeated_mark.set_from_pixbuf(None)
        self.status.repeated = value

    def set_protected_mark(self, value):
        if value:
            self.protected_mark.set_from_pixbuf(self.base.load_image('mark-protected.png', True))
        else:
            self.protected_mark.set_from_pixbuf(None)

    def set_verified_mark(self, value):
        if value:
            self.verified_mark.set_from_pixbuf(self.base.load_image('mark-verified.png', True))
        else:
            self.verified_mark.set_from_pixbuf(None)

    def set_reposted_mark(self, value):
        if value:
            self.reposted_mark.set_from_pixbuf(self.base.load_image('mark-reposted.png', True))
        else:
            self.reposted_mark.set_from_pixbuf(None)


########NEW FILE########
__FILENAME__ = tray
# -*- coding: utf-8 -*-

# GTK3 tray icon for Turpial

from gi.repository import Gtk

from turpial import DESC
from turpial.ui.lang import i18n

class TrayIcon(Gtk.StatusIcon):
    def __init__(self, base):
        Gtk.StatusIcon.__init__(self)

        self.base = base
        self.set_from_pixbuf(self.base.load_image('turpial-tray.png', True))
        self.set_tooltip_text(DESC)
        self.menu = Gtk.Menu()

    def __build_common_menu(self):
        accounts = Gtk.MenuItem(i18n.get('accounts'))
        preferences = Gtk.MenuItem(i18n.get('preferences'))
        sounds = Gtk.CheckMenuItem(i18n.get('enable_sounds'))
        #sound_.set_active(not self.sound._disable)
        exit_ = Gtk.MenuItem(i18n.get('exit'))

        self.menu.append(accounts)
        self.menu.append(preferences)
        self.menu.append(sounds)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu.append(exit_)

        accounts.connect('activate', self.base.show_accounts_dialog)
        preferences.connect('activate', self.base.show_preferences_dialog)
        sounds.connect('toggled', self.base.disable_sound)
        exit_.connect('activate', self.base.main_quit)

    def empty(self):
        self.menu = Gtk.Menu()
        self.__build_common_menu()

    def normal(self):
        self.menu = Gtk.Menu()

        tweet = Gtk.MenuItem(i18n.get('new_tweet'))
        tweet.connect('activate', self.base.show_update_box)
        direct = Gtk.MenuItem(i18n.get('direct_message'))
        direct.connect('activate', self.base.show_update_box, True)

        self.menu.append(tweet)
        self.menu.append(direct)

        self.__build_common_menu()

    def popup(self, button, activate_time):
        self.menu.show_all()
        self.menu.popup(None, None, None, None, button, activate_time)
        return True

    # Change the tray icon image to indicate updates
    def notify(self):
        self.set_from_pixbuf(self.base.load_image('turpial-tray-update.png', True))

    # Clear the tray icon image
    def clear(self):
        self.set_from_pixbuf(self.base.load_image('turpial-tray.png', True))


########NEW FILE########
__FILENAME__ = updatebox
# -*- coding: utf-8 -*-

""" Widget to update statuses in Turpial """
#
# Author: Wil Alvarez (aka Satanas)

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from turpial.ui.lang import i18n

SPELLING = False
try:
    #import gtkspell
    SPELLING = False
except:
    pass

#from turpial.ui.Gtk.friendwin import FriendsWin
from turpial.ui.gtk.markuplabel import MarkupLabel

MAX_CHAR = 140

class UpdateBox(Gtk.Window):
    def __init__(self, base):
        Gtk.Window.__init__(self)

        self.blocked = False
        self.base = base
        self.title_caption = i18n.get('whats_happening')
        #self.set_resizable(False)
        self.set_default_size(500, 120)
        self.set_transient_for(base)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_gravity(Gdk.Gravity.STATIC)

        self.update_text = MessageTextView()

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.update_text)

        self.btn_update = Gtk.Button(i18n.get('update'))
        self.btn_update.set_tooltip_text(i18n.get('update_status') + ' (Ctrl + Enter)')

        self.btn_short = Gtk.Button()
        self.btn_short.set_image(self.base.load_image('action-shorten.png'))
        self.btn_short.set_tooltip_text(i18n.get('short_urls'))

        self.btn_upload = Gtk.Button()
        self.btn_upload.set_image(self.base.load_image('action-upload.png'))
        self.btn_upload.set_tooltip_text(i18n.get('upload_image'))

        self.spinner = Gtk.Spinner()
        self.message = MarkupLabel(xalign=1)

        opt_box = Gtk.HBox()
        opt_box.pack_start(self.btn_upload, False, False, 1)
        opt_box.pack_start(self.btn_short, False, False, 1)

        opt_align = Gtk.Alignment()
        opt_align.set(0, -1, -1, -1)
        opt_align.add(opt_box)

        box = Gtk.HBox()
        box.pack_start(opt_align, False, False, 0)
        box.pack_start(self.message, True, True, 0)
        box.pack_start(self.spinner, False, False, 5)
        box.pack_start(self.btn_update, False, False, 2)
        buttonbox = Gtk.Alignment()
        buttonbox.set_property('xalign', 1)
        buttonbox.add(box)

        self.accounts = {}
        self.accbox = Gtk.HBox()
        for account in self.base.get_all_accounts():
            chk = Gtk.CheckButton(account.id_.split('-')[0])
            chk.set_margin_right(5)
            img = Gtk.Image()
            img.set_from_pixbuf(self.base.load_image(account.id_.split('-')[1] + '.png', True))
            self.accbox.pack_start(img, False, False, 0)
            self.accbox.pack_start(chk, False, False, 0)
            self.accounts[account.id_] = chk

        vbox = Gtk.VBox()
        vbox.pack_start(scroll, True, True, 3)
        vbox.pack_start(buttonbox, False, False, 0)
        vbox.pack_start(self.accbox, False, False, 0)
        vbox.set_margin_right(3)
        vbox.set_margin_left(3)

        self.add(vbox)

        _buffer = self.update_text.get_buffer()
        #self.connect('key-press-event', self.__detect_shortcut)
        _buffer.connect('changed', self.__count_chars)
        self.connect('delete-event', self.__unclose)
        #self.btn_upload.connect('clicked', self.__release)
        self.btn_short.connect('clicked', self.__short_url)
        self.btn_update.connect('clicked', self.__update_callback)
        #self.btn_url.connect('clicked', self.short_url)
        #self.btn_url.set_sensitive(False)
        self.update_text.connect('key-press-event', self.__on_key_pressed)

        if SPELLING:
            try:
                self.spell = Gtkspell.Spell (self.update_text)
            except Exception, e_msg:
                # FIXME: Usar el log
                print 'DEBUG:UI:Can\'t load Gtkspell -> %s' % e_msg
        else:
            # FIXME: Usar el log
            print 'DEBUG:UI:Can\'t load Gtkspell'

        self.__reset()
        self.__count_chars()

    def __on_key_pressed(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Return' and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.__update_callback(widget)
            return True
        elif keyname == 'Escape':
            self.__unclose(widget)
            return True
        return False

    def __unclose(self, widget, event=None):
        if not self.blocked:
            if self.__count_chars() < 140:
                self.base.show_confirm_dialog(i18n.get('do_you_want_to_discard_message'), self.done)
            else:
                self.done()
        return True

    def __reset(self):
        self._account_id = None
        self._in_reply_id = None
        self._in_reply_user = None
        self._message = None
        self._direct_message_to = None
        self.message.set_markup('')

    def __count_chars(self, widget=None):
        _buffer = self.update_text.get_buffer()
        remain = MAX_CHAR - _buffer.get_char_count()
        self.set_title("%s (%i)" % (self.title_caption, remain))
        return remain

    def __update_callback(self, widget):
        status = self.update_text.get_text()
        accounts = []
        for key, chk in self.accounts.iteritems():
            if chk.get_active():
                accounts.append(key)

        # Validate basic variables
        if len(accounts) == 0:
            self.message.set_error_text(i18n.get('select_account_to_post'))
            return

        if status == '':
            self.message.set_error_text(i18n.get('you_must_write_something'))
            return

        if len(status) > MAX_CHAR:
            self.message.set_error_text(i18n.get('message_looks_like_testament'))
            return

        # Send direct message
        if self._direct_message_to:
            if len(accounts) > 1:
                self.message.set_error_text(i18n.get('can_send_message_to_one_account'))
            else:
                self.lock(i18n.get('sending_message'))
                self.base.direct_message(accounts[0], self._direct_message_to, status)
        # Send regular status
        else:
            self.lock(i18n.get('updating_status'))
            self.base.update_status(accounts, status, self._in_reply_id)

    def __show(self, message=None, status_id=None, account_id=None, reply_id=None, reply_user=None, ):
        # Check for new accounts
        for account in self.base.get_all_accounts():
            if not account.id_ in self.accounts:
                chk = Gtk.CheckButton(account.id_.split('-')[0])
                chk.set_margin_right(5)
                img = Gtk.Image()
                img.set_from_pixbuf(self.base.load_image(account.id_.split('-')[1] + '.png', True))
                self.accbox.pack_start(img, False, False, 0)
                self.accbox.pack_start(chk, False, False, 0)
                self.accounts[account.id_] = chk

        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_focus(self.update_text)

        if self._message:
            self.update_text.set_text(self._message)

        # TODO: Save the previous state of checkboxes
        if self._account_id:
            for key, account in self.accounts.iteritems():
                account.set_sensitive(False)
                account.set_active(False)
            self.accounts[self._account_id].set_active(True)

        self.show_all()
        self.unlock()
        self.__count_chars()

    def __short_url(self, widget):
        self.lock(i18n.get('shorting_urls'))
        message = self.update_text.get_text()
        if len(message) == 0:
            self.unlock(i18n.get('no_url_to_short'))
        else:
            self.base.autoshort_url(message)

    def close(self):
        self.__unclose(None)

    def show(self):
        self.title_caption = i18n.get('whats_happening')
        self.__show()

    def show_for_quote(self, message):
        self.title_caption = i18n.get('update_status')
        self._message = message
        self.__show()
        self.update_text.move_cursor(MessageTextView.CURSOR_START)

    def show_for_reply(self, in_reply_id, account_id, in_reply_user):
        self.title_caption = i18n.get('reply_status')
        self._in_reply_id = in_reply_id
        self._in_reply_user = in_reply_user
        self._account_id = account_id
        self._message = "%s " % (in_reply_user)
        self.__show()
        self.update_text.move_cursor(MessageTextView.CURSOR_END)

    def show_for_direct(self, account_id, username):
        self.title_caption = "%s @%s" % (i18n.get('send_message_to'), username)
        self._account_id = account_id
        self._direct_message_to = username
        self.__show()

    def show_for_reply_direct(self, in_reply_id, account_id, username):
        self.title_caption = "%s @%s" % (i18n.get('reply_message_to'), username)
        self._in_reply_id = in_reply_id
        self._account_id = account_id
        self._direct_message_to = username
        self.__show()

    def done(self, widget=None, event=None):
        self.update_text.clear()
        self.__reset()
        self.hide()
        return True

    def clear(self, widget):
        self.update_text.clear()
        self._direct_message_to = None

    def lock(self, msg):
        self.blocked = True
        self.update_text.set_sensitive(False)
        self.btn_update.set_sensitive(False)
        self.spinner.start()
        self.spinner.show()
        self.message.set_markup(msg)

        for key, account in self.accounts.iteritems():
            account.set_sensitive(False)

    def unlock(self, msg=None):
        self.blocked = False
        self.update_text.set_sensitive(True)
        self.btn_update.set_sensitive(True)
        self.spinner.stop()
        self.spinner.hide()

        if not self._account_id:
            for key, account in self.accounts.iteritems():
                account.set_sensitive(True)

        if msg:
            if msg != 'Unknown error':
                self.message.set_error_text(msg)
            else:
                self.message.set_error_text(i18n.get('i_couldnt_update_status'))
        else:
            self.message.set_text('')

        self.set_focus(self.update_text)


    def update_error(self, msg=None):
        self.unlock(msg)

    def broadcast_error(self, posted_accounts, err_accounts):
        errmsg = i18n.get('error_posting_to') % (', '.join(err_accounts))
        self.unlock(errmsg)
        for account_id in posted_accounts:
            self.accounts[account_id].set_sensitive(False)
            self.accounts[account_id].set_active(False)

    def update_after_short_url(self, response):
        if response.code == 815:
            self.unlock(i18n.get('url_already_short'))
        elif response.code == 812:
            self.unlock(i18n.get('no_url_to_short'))
        elif response.code > 0:
            self.unlock(i18n.get('couldnt_shrink_urls'))
        else:
            self.update_text.set_text(response.items)
            self.update_text.move_cursor(MessageTextView.CURSOR_END)
            self.unlock()


    """

    def show_friend_dialog(self, widget):
        f = FriendsWin(self, self.add_friend,
            self.base.request_friends_list())

    def add_friend(self, user):
        if user is None: return

        _buffer = self.update_text.get_buffer()
        end_offset = _buffer.get_property('cursor-position')
        start_offset = end_offset - 1

        end = _buffer.get_iter_at_offset(end_offset)
        start = _buffer.get_iter_at_offset(start_offset)
        text = _buffer.get_text(start, end)

        if (text != ' ') and (start_offset > 0):
            user = ' ' + user

        _buffer.insert_at_cursor(user)

        
    def __on_url_changed(self, widget):
        url_lenght = widget.get_text_length()
        if url_lenght == 0:
            self.btn_url.set_sensitive(False)
        else:
            self.btn_url.set_sensitive(True)
        return False

    def __detect_shortcut(self, widget, event=None):
        keyname = Gtk.gdk.keyval_name(event.keyval)

        if (event.state & Gtk.gdk.CONTROL_MASK) and keyname.lower() == 'f':
            self.show_friend_dialog(widget)
            return True
        elif (event.state & Gtk.gdk.CONTROL_MASK) and keyname.lower() == 'l':
            self.clear(widget)
            return True
        elif (event.state & Gtk.gdk.CONTROL_MASK) and keyname.lower() == 't':
            self.update(widget)
            return True
        return False
    """

class MessageTextView(Gtk.TextView):
    '''Class for the message textview (where user writes new messages)
    for chat/groupchat windows'''

    CURSOR_START = 1
    CURSOR_END = 2

    def __init__(self):
        GObject.GObject.__init__(self)
        Gtk.TextView.__init__(self)

        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_accepts_tab(False)

    def destroy(self):
        import gc
        GObject.idle_add(lambda:gc.collect())

    def clear(self, widget=None):
        self.get_buffer().set_text('')

    def set_text(self, message):
        self.get_buffer().set_text(message)

    def get_text(self):
        _buffer = self.get_buffer()
        start, end = _buffer.get_bounds()
        return _buffer.get_text(start, end, False)

    def move_cursor(self, position=CURSOR_END):
        _buffer = self.get_buffer()
        start_iter = _buffer.get_start_iter()
        end_iter = _buffer.get_end_iter()
        length = len(_buffer.get_text(start_iter, end_iter, False))

        if position == self.CURSOR_START:
            _buffer.place_cursor(start_iter)
        elif position == self.CURSOR_END:
            _buffer.place_cursor(end_iter)
        else:
            pass


########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-

# GTK Worker for Turpial
#
# Author: Wil Alvarez (aka Satanas)
# Nov 18, 2011

import Queue
import threading

class Worker(threading.Thread):
    TIMEOUT = 200
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.queue = Queue.Queue()
        self.exit_ = False

    def set_timeout_callback(self, tcallback):
        self.tcallback = tcallback

    def register(self, funct, args, callback, user_data=None):
        self.queue.put((funct, args, callback, user_data))

    def quit(self):
        self.exit_ = True

    def run(self):
        while not self.exit_:
            try:
                req = self.queue.get(True, 0.3)
            except Queue.Empty:
                continue
            except:
                continue

            (funct, args, callback, user_data) = req

            if type(args) == tuple:
                rtn = funct(*args)
            elif args:
                rtn = funct(args)
            else:
                rtn = funct()

            if callback:
                self.tcallback(callback, rtn, user_data)

########NEW FILE########
__FILENAME__ = html
# -*- coding: utf-8 -*-

# Webkit container for Turpial
#
# Author: Wil Alvarez (aka Satanas)
# Oct 05, 2011

import re
import os
import sys
import urllib

from turpial import VERSION
from turpial.ui.lang import i18n
from libturpial.common import ARG_SEP, LoginStatus
from libturpial.api.services.showmedia import utils as showmediautils

#pyinstaller compatibility validation
if getattr(sys, 'frozen', None):
    DATA_DIR = os.path.realpath(os.path.join(sys._MEIPASS))
else:
    DATA_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'data'))

IMAGES_DIR = os.path.join(DATA_DIR, 'pixmaps')
LAYOUT_DIR = os.path.join(DATA_DIR, 'layout')
JS_LAYOUT_DIR = os.path.join(LAYOUT_DIR, 'js')
CSS_LAYOUT_DIR = os.path.join(LAYOUT_DIR, 'css')

IMG_PATTERN = re.compile('(<% img [\'"](.*?)[\'"] %>)')
RESIZED_IMG_PATTERN = re.compile('(<% rimg [\'"](.*?)[\'"], (.*?), (.*?) %>)')
CSS_IMG_PATTERN = re.compile('(<% css_img [\'"](.*?)[\'"] %>)')
PARTIAL_PATTERN = re.compile('(<% partial [\'"](.*?)[\'"] %>)')
I18N_PATTERN = re.compile('(<% \$(.*?) %>)')

class HtmlParser:
    def __init__(self,*args):
        self.scripts = []
        self.scripts_impress = []
        self.styles = []
        self.styles_impress = []
        self.partials = {}

    def __url_quote(self, text):
        ntext = text.encode('utf-8').replace('\\\\', '\\')
        return urllib.quote(ntext)

    def __open_template(self, res):
        filepath = os.path.realpath(os.path.join(LAYOUT_DIR, res + '.template'))
        fd = open(filepath, 'r')
        resource = fd.read()
        fd.close()
        return resource

    def __open_partial(self, name):
        filepath = os.path.join(LAYOUT_DIR, name + '.partial')
        fd = open(filepath, 'r')
        resource = fd.read()
        fd.close()
        return resource

    def __load_layout(self, res):
        self.scripts = []
        self.scripts_impress = []
        self.styles = []
        self.styles_impress = []
        self.partials = {}

        self.app_layout = self.__open_template(res)

        # Load default js

        for js in ['jquery', 'jquery.hotkeys', 'jquery.autocomplete', 'common']:
            filepath = os.path.realpath(os.path.join(JS_LAYOUT_DIR, js + '.js'))
            self.scripts.append(filepath)

        for js in ['animation', 'fx-m']:
            filepath = os.path.realpath(os.path.join(JS_LAYOUT_DIR, js + '.js'))
            self.scripts_impress.append(filepath)

        # Load default css
        for css in ['common', 'jquery.autocomplete', 'grids-min']:
            filepath = os.path.realpath(os.path.join(CSS_LAYOUT_DIR, css + '.css'))
            self.styles.append(filepath)

        # Load default css_impress
        for css in ['general', 'index']:
            filepath = os.path.realpath(os.path.join(CSS_LAYOUT_DIR, css + '.css'))
            self.styles_impress.append(filepath)

        js_file = os.path.realpath(os.path.join(LAYOUT_DIR, 'js', res + '.js'))
        if os.path.isfile(js_file):
            self.scripts.append(js_file)

        css_file = os.path.realpath(os.path.join(LAYOUT_DIR, 'css', res + '.css'))
        if os.path.isfile(css_file):
            self.styles.append(css_file)

    def __image_tag(self, filename, base=True, width=None, height=None, class_=None, visible=True, tooltip=''):
        if base:
            filepath = os.path.realpath(os.path.join(IMAGES_DIR, filename))
        else:
            filepath = os.path.realpath(os.path.join(DEFAULT_IMAGES_DIR, filename))

        class_tag = ''
        if class_:
            class_tag = "class='%s'" % class_

        visible_tag = ''
        if not visible:
            visible_tag = "style='display: none;'"

        tooltip_tag = ''
        if tooltip:
            tooltip_tag = """ title="%s" alt="%s" """ % (tooltip, tooltip)

        if width and height:
            return "<img src='file://%s' width='%s' height='%s' %s %s %s/>" % (filepath, width, height, class_tag, visible_tag, tooltip_tag)
        else:
            return "<img src='file://%s' %s %s %s/>" % (filepath, class_tag, visible_tag, tooltip_tag)

    def __query_tag(self):
        return "<img style='display:none;' id='query' src='' alt='' />"

    def __verified_tag(self, verified):
        if verified:
            return self.__image_tag("mark-verified.png", 16, 16, class_='mark')
        else:
            return ''

    def __protected_tag(self, protected):
        if protected:
            return self.__image_tag("mark-locked.png", 16, 16, class_='mark')
        else:
            return ''

    def __reposted_tag(self, reposted):
        if reposted:
            return self.__image_tag("mark-repeated.png", 16, 16, class_='repost_mark')
        else:
            return ''

    def __favorite_tag(self, favorite):
        if favorite:
            return self.__image_tag("action-fav.png", 16, 16, class_='star')
        else:
            return self.__image_tag("action-unfav.png", 16, 16, class_='star')

    def __retweeted_tag(self):
        return self.__image_tag("mark-retweeted.png", 16, 16, class_='retweeted')

    def __retweeted_visible(self, status):
        if status.retweeted:
            return 'display: block;'
        return 'display: none;'

    def __favorite_visible(self, status):
        if status.is_favorite:
            return 'display: block;'
        return 'display: none;'

    def __login_action_tag(self, account):
        if account.logged_in == LoginStatus.NONE:
            return "<a href='cmd:login:%s'>%s</a>" % (account.id_, i18n.get('login'))
        elif account.logged_in == LoginStatus.IN_PROGRESS:
            return "<span class=\"progress\">%s</span>" % (i18n.get('in_progress'))
        elif account.logged_in == LoginStatus.DONE:
            return "<span class=\"done\">%s</span>" % (i18n.get('logged_in'))

    def __highlight_username(self, status):
        args = "'%s', '%s'" % (status.account_id, status.username)
        return '<a href="javascript: show_profile_window(%s);">%s</a>' % (args, status.username)

    def __highlight_hashtags(self, status, text):
        for h in status.entities['hashtags']:
            cad = '<a href="cmd:show_hashtag:%s">%s</a>' % (h.url, h.display_text)
            text = text.replace(h.search_for, cad)
        return text

    def __highlight_groups(self, status, text):
        for h in status.entities['groups']:
            cad = '<a href="cmd:show_group:%s">%s</a>' % (h.url, h.display_text)
            text = text.replace(h.search_for, cad)
        return text

    def __highlight_mentions(self, status, text):
        for h in status.entities['mentions']:
            args = "'%s', '%s'" % (status.account_id, h.display_text[1:])
            cad = '<a href="javascript: show_profile_window(%s);">%s</a>' % (args, h.display_text)
            pattern = re.compile(h.search_for, re.IGNORECASE)
            text = pattern.sub(cad, text)
        return text

    def __highlight_urls(self, status, text):
        for url in status.entities['urls']:
            if url.url == None:
                url.url = url.search_for
            #if url.url[0:7] != "http://":
            #    url.url = "http://%s" % url.url
            if not showmediautils.is_service_supported(url.url):
                cad = '<a href="link:%s" title="%s">%s</a>' % (url.url, url.url,
                    url.display_text)
            else:
                pars = ARG_SEP.join([url.url.replace(":", "$"), status.account_id])
                cad = '<a href="cmd:show_media:%s" title="%s">%s</a>' % (pars, url.url,
                    url.display_text)
            text = text.replace(url.search_for, cad)
        return text

    def __build_status_menu(self, status):
        menu = ''
        if not status.is_own and not status.is_direct():
            # Reply
            mentions = status.get_reply_mentions()
            str_mentions = '[\'' + '\',\''.join(mentions) + '\']'
            title = i18n.get('in_reply_to').capitalize() + " " + mentions[0]
            cmd = "'%s','%s','%s',%s" % (status.account_id, status.id_, title, str_mentions)
            menu += "<a href=\"javascript: reply_status(%s)\" class='action'>%s</a>" % (cmd, self.__image_tag('action-reply.png',
                tooltip=i18n.get('reply')))

            # Repeat
            args = ARG_SEP.join([status.account_id, status.id_, status.username, self.__url_quote(status.text)])
            menu += "<a href='cmd:repeat_menu:%s' class='action'>%s</a>" % (args, self.__image_tag('action-repeat.png',
                tooltip=i18n.get('repeat')))

            # Conversation
            if status.in_reply_to_user:
                args = ARG_SEP.join([status.account_id, status.id_, '%s' % status.in_reply_to_id])
                menu += """<a href='cmd:show_conversation:%s' class='action'>%s</a>""" % (args, self.__image_tag('action-conversation.png',
                    tooltip=i18n.get('conversation')))

        elif not status.is_own and status.is_direct():
            # Reply
            cmd = "'%s','%s'" % (status.account_id, status.username)
            menu += "<a href=\"javascript: reply_direct(%s)\" class='action'>%s</a>" % (cmd, self.__image_tag('action-reply.png',
                tooltip=i18n.get('reply')))

            # Delete
            cmd = ARG_SEP.join([status.account_id, status.id_])
            menu += """<a href="javascript:show_confirm_window('%s', '%s', 'cmd:delete_direct:%s')" class='action'>%s</a>""" % (
                    i18n.get('confirm_delete'), i18n.get('do_you_want_to_delete_direct_message'), cmd, self.__image_tag('action-delete.png',
                    tooltip=i18n.get('delete')))
        elif status.is_own and not status.is_direct():
            cmd = ARG_SEP.join([status.account_id, status.id_])
            menu += """<a href="javascript:show_confirm_window('%s', '%s', 'cmd:delete_status:%s')" class='action'>%s</a>""" % (
                    i18n.get('confirm_delete'), i18n.get('do_you_want_to_delete_status'), cmd, self.__image_tag('action-clear.png',
                    tooltip=i18n.get('delete')))
        elif status.is_own and status.is_direct():
            cmd = ARG_SEP.join([status.account_id, status.id_])
            menu += """<a href="javascript:show_confirm_window('%s', '%s', 'cmd:delete_direct:%s')" class='action'>%s</a>""" % (
                    i18n.get('confirm_delete'), i18n.get('do_you_want_to_delete_direct_message'), cmd, self.__image_tag('action-clear.png',
                    tooltip=i18n.get('delete')))
        return menu

    def __build_profile_menu(self, profile):
        if profile.is_me():
            return "<span class='disabled action_you'>%s</span>" % (i18n.get('this_is_you'))

        menu = ''
        cmd = "'%s','%s'" % (profile.account_id, profile.username)
        # Direct Messages
        menu += "<a href=\"javascript: send_direct_from_profile(%s)\" class='action'>%s</a>" % (cmd, i18n.get('message'))

        # Follow
        cmd = ARG_SEP.join([profile.account_id, profile.username])
        if profile.following:
            label = i18n.get('do_you_want_to_unfollow_user') % profile.username
            menu += """<a id='profile-follow-cmd' href="javascript:show_confirm_window('%s', '%s', 'cmd:unfollow:%s')" class='action'>%s</a>""" % (
                    i18n.get('confirm_unfollow'), label, cmd, i18n.get('unfollow'))
        elif profile.follow_request:
            menu += "<span class='action'>%s</span>" % (i18n.get('requested'))
        else:
            menu += "<a id='profile-follow-cmd' href='cmd:follow:%s' class='action'>%s</a>" % (cmd, i18n.get('follow'))

        # Mute
        if profile.muted:
            menu += "<a id='profile-mute-cmd' href='cmd:unmute:%s' class='action'>%s</a>" % (profile.username, i18n.get('unmute'))
        else:
            menu += "<a id='profile-mute-cmd' href='cmd:mute:%s' class='action'>%s</a>" % (profile.username, i18n.get('mute'))

        # Block
        menu += "<a href='cmd:block:%s' class='action'>%s</a>" % (cmd, i18n.get('block'))

        # Spam
        menu += "<a href='cmd:report_spam:%s' class='action'>%s</a>" % (cmd, i18n.get('spam'))

        return menu

    def __account_buttons(self, accounts):
        buttons = ''
        for acc in accounts:
            name = acc.split('-')[0]
            image_name = acc.split('-')[1] + ".png"
            image = self.__image_tag(image_name, 16, 16)
            #buttons += "<a href='#' title='%s' class='toggle'>%s</a>" % (name, image)
            buttons += "<div class='checkbox' title='%s'>%s<label><span>%s</span><input id='acc-selector-%s' type='checkbox' class='acc_selector' value='%s' style='vertial-align:middle;' /></label><div class='clearfix'></div></div>" % (name, image, name, acc, acc)
        return buttons

    def __parse_tags(self, page):
        for part in PARTIAL_PATTERN.findall(page):
            page = page.replace(part[0], self.partials[part[1]])

        for img in IMG_PATTERN.findall(page):
            page = page.replace(img[0], self.__image_tag(img[1]))

        for img in RESIZED_IMG_PATTERN.findall(page):
            page = page.replace(img[0], self.__image_tag(img[1], width=img[2], height=img[3]))

        for img in CSS_IMG_PATTERN.findall(page):
            filepath = os.path.realpath(os.path.join(IMAGES_DIR, img[1]))
            page = page.replace(img[0], 'file://' + filepath)

        for text in I18N_PATTERN.findall(page):
            # TODO: Escape invalid characters
            page = page.replace(text[0], i18n.get(text[1]))
        return page

    def __render(self, tofile=True):
        page = self.app_layout

        js_tags = '<script type="text/javascript">'
        for js in self.scripts:
            fd = open(js, 'r')
            resource = fd.read()
            fd.close()
            js_tags += resource + '\n'
        js_tags += '</script>'
        page = page.replace('<% javascripts %>', js_tags)

        js_tags = '<script type="text/javascript">'
        for js in self.scripts_impress:
            fd = open(js, 'r')
            resource = fd.read()
            fd.close()
            js_tags += resource + '\n'
        js_tags += '</script>'
        page = page.replace('<% javascripts_impress %>', js_tags)

        css_tags = '<style type="text/css">'
        for css in self.styles:
            fd = open(css, 'r')
            resource = fd.read()
            fd.close()
            css_tags += resource + '\n'
        css_tags += '</style>'
        page = page.replace('<% stylesheets %>', css_tags)

        css_tags = '<style type="text/css">'
        for css in self.styles_impress:
            fd = open(css, 'r')
            resource = fd.read()
            fd.close()
            css_tags += resource + '\n'
        css_tags += '</style>'

        page = page.replace('<% stylesheets_impress %>', css_tags)

        page = page.replace('<% query %>', self.__query_tag())

        page = self.__parse_tags(page)
        if tofile:
            fd = open('/tmp/output.html', 'w')
            fd.write(page)
            fd.close()
        return page

    def js_string_array(self, array):
        return '["' + '","'.join(array) + '"]'

    def parse_command(self, command):
        action = command.split(':')[0]
        try:
            args = command.split(':')[1].split(ARG_SEP)
        except IndexError:
            args = []
        return action, args

    def empty(self):
        self.__load_layout('empty')
        return self.__render()

    def main(self, accounts, columns):
        self.__load_layout('main')
        hdr_content = ''
        col_content = ''
        for column in columns:
            hdr, col = self.render_column(column)
            hdr_content += hdr
            col_content += col
        acc_buttons = self.__account_buttons(accounts)
        self.app_layout = self.app_layout.replace('<% @headers %>', hdr_content)
        self.app_layout = self.app_layout.replace('<% @columns %>', col_content)
        self.app_layout = self.app_layout.replace('<% @account_buttons %>', acc_buttons)

        page = self.__render(tofile=False)
        # TODO: Look for a better way of handle javascript code from python
        page = page.replace('<% @arg_sep %>', ARG_SEP)
        page = page.replace('<% @num_columns %>', str(len(columns)))

        fd = open('/tmp/output.html', 'w')
        fd.write(page)
        fd.close()
        return page

    def accounts(self, accounts):
        self.__load_layout('accounts')
        acc_list = self.render_account_list(accounts)
        self.app_layout = self.app_layout.replace('<% @accounts %>', acc_list)
        return self.__render()

    def about(self):
        self.__load_layout('about2')
        self.app_layout = self.app_layout.replace('<% VERSION  %>', VERSION)
        return self.__render()

    def account_form(self, plist, user='', pwd='', prot=''):
        self.__load_layout('account_form')

        protocols = self.protocols_for_options(plist, prot)
        self.app_layout = self.app_layout.replace('<% @user %>', user)
        self.app_layout = self.app_layout.replace('<% @pwd %>', pwd)
        self.app_layout = self.app_layout.replace('<% @protocols %>', protocols)
        return self.__render()

    def protocols_for_options(self, plist, default=''):
        ''' Receive an array of protocols like ['protocol1', 'protocol2'] '''
        protocols = '<option value="null">%s</option>' % i18n.get('--select--')
        for p in plist:
            checked = ''
            if p == default:
                checked = 'checked="checked"'
            protocols += '<option value="%s" %s>%s</option>' % (p, checked, p.capitalize())
        return protocols

    def render_account_list(self, accounts):
        self.partials['accounts'] = ''
        partial = self.__open_partial('account')
        for acc in accounts:
            section = partial.replace('<% @account_id %>', acc.id_)
            section = section.replace('<% @account_name %>', acc.profile.username)
            section = section.replace('<% @protocol_id %>', acc.id_.split('-')[1])
            section = section.replace('@protocol_img', acc.id_.split('-')[1] + '.png')
            section = section.replace('<% @login_action %>', self.__login_action_tag(acc))

            self.partials['accounts'] += section + '\n'
        page = self.__parse_tags(self.partials['accounts'])

        return page

    def statuses(self, statuses):
        result = ''
        for status in statuses:
            result += self.status(status) + '\n'
        page = self.__parse_tags(result)
        return page

    def single_status(self, status):
        result = self.status(status)
        page = self.__parse_tags(result)
        return page

    def render_column(self, column):
        protocol_img = column.protocol_id + '.png'
        label = ''
        if column.column_name == 'public':
            label = "%s :: %s" % (column.column_name, i18n.get('timeline'))
        else:
            label = "%s :: %s" % (column.account_id.split('-')[0], column.column_name)

        col_header = self.__open_partial('column_header')
        col_header = col_header.replace('<% @column_label %>', label)
        col_header = col_header.replace('<% @column_id %>', column.id_)
        col_header = col_header.replace('@protocol_img', protocol_img)

        col_content = self.__open_partial('column_content')
        col_content = col_content.replace('<% @column_id %>', column.id_)

        header = self.__parse_tags(col_header)
        column = self.__parse_tags(col_content)
        return header, column

    def status(self, status, ignore_reply=False, profile_status=False):
        timestamp = status.datetime
        if status.source:
            if status.source.url:
                timestamp += ' %s <a href="link:%s">%s</a>' % (i18n.get('from'), status.source.url, status.source.name)
            else:
                timestamp += ' %s %s' % (i18n.get('from'), status.source.name)

        if status.in_reply_to_user and not ignore_reply:
            timestamp += ' %s %s' % (i18n.get('in_reply_to'), status.in_reply_to_user)

        reposted_by = ''
        if status.reposted_by:
            count = len(status.reposted_by)
            if count > 1:
                temp = '%i %s' % (count, i18n.get('people'))
            elif count == 1:
                temp = '1 %s' % i18n.get('person')
            reposted_by = '%s %s' % (i18n.get('retweeted_by'), status.reposted_by)

        args = ARG_SEP.join([status.account_id, status.id_])
        tmp_cmd = "<a name='fav-cmd' href='%s' class='action'>%s</a>"
        if status.is_favorite:
            cmd = "cmd:unfav_status:%s" % args
            fav_cmd = tmp_cmd % (cmd, self.__image_tag('action-fav.png', tooltip=i18n.get('-fav')))
            is_fav = 'true'
            show_fav = ''
        else:
            cmd = "cmd:fav_status:%s" % args
            fav_cmd = tmp_cmd % (cmd, self.__image_tag('action-unfav.png', tooltip=i18n.get('+fav')))
            is_fav = 'false'
            show_fav = 'display: none'

        message = self.__highlight_urls(status, status.text)
        message = self.__highlight_hashtags(status, message)
        message = self.__highlight_groups(status, message)
        message = self.__highlight_mentions(status, message)
        message = message.replace('\r', ' ')
        message = message.replace('\\"', '"')
        message = message.replace('\\', "&#92;")
        username = self.__highlight_username(status)
        menu = self.__build_status_menu(status)

        args = ARG_SEP.join([status.account_id, status.id_])

        # Decide what template to use
        if profile_status:
            section = self.__open_partial('profile_status')
        else:
            section = self.__open_partial('status')

        section = section.replace('<% @status_id %>', status.id_)
        section = section.replace('<% @status_display_id %>', status.display_id)
        if status.in_reply_to_id:
            section = section.replace('<% @status_replyto_id %>', '%s' % status.id_)
        else:
            section = section.replace('<% @status_replyto_id %>', '')

        section = section.replace('<% @avatar %>', status.avatar)
        section = section.replace('<% @account_id %>', status.account_id)
        section = section.replace('<% @clean_username %>', status.username)
        section = section.replace('<% @username %>', username)
        section = section.replace('<% @message %>', message)
        section = section.replace('<% @timestamp %>', timestamp)
        section = section.replace('<% @reposted_by %>', reposted_by)
        section = section.replace('<% @verified %>', self.__verified_tag(status.is_verified))
        section = section.replace('<% @protected %>', self.__protected_tag(status.is_protected))
        section = section.replace('<% @reposted %>', self.__reposted_tag(status.reposted_by))
        section = section.replace('<% @is_fav %>', is_fav)
        section = section.replace('<% @show_favorite %>', show_fav)
        section = section.replace('<% @favorite_cmd %>', fav_cmd)
        section = section.replace('<% @retweeted_visible %>', self.__retweeted_visible(status))
        section = section.replace('<% @retweeted %>', self.__retweeted_tag())
        section = section.replace('<% @menu %>', menu)

        return section

    def profile(self, profile):
        bio_icon = self.__image_tag('icon-bio.png', width='16', height='16', class_='mark')
        loc_icon = self.__image_tag('icon-location.png', width='16', height='16', class_='mark')
        web_icon = self.__image_tag('icon-web.png', width='16', height='16', class_='mark')
        url = ''
        if profile.url != '' and profile.url != None:
            url = '<a href="link:%s">%s</a>' % (profile.url, profile.url)
        bio = ''
        if profile.bio:
            bio = profile.bio
        location = ''
        if profile.location:
            location = profile.location
        section = self.__open_partial('profile')
        section = section.replace('<% @account_id %>', profile.account_id)
        section = section.replace('<% @avatar %>', profile.avatar)
        section = section.replace('<% @fullname %>', profile.fullname)
        section = section.replace('<% @username %>', profile.username)
        section = section.replace('<% @verified %>', self.__verified_tag(profile.verified))
        section = section.replace('<% @protected %>', self.__protected_tag(profile.protected))
        section = section.replace('<% @bio_icon %>', bio_icon)
        section = section.replace('<% @location_icon %>', loc_icon)
        section = section.replace('<% @web_icon %>', web_icon)
        section = section.replace('<% @bio %>', bio)
        section = section.replace('<% @location %>', location)
        section = section.replace('<% @web %>', url)
        section = section.replace('<% @following %>', str(profile.friends_count))
        section = section.replace('<% @followers %>', str(profile.followers_count))
        section = section.replace('<% @posts %>', str(profile.statuses_count))
        section = section.replace('<% @favorites %>', str(profile.favorites_count))
        section = section.replace('<% @menu %>', self.__build_profile_menu(profile))
        recent = ''
        for status in profile.recent_updates:
            recent += self.status(status, profile_status=True)
        section = section.replace('<% @recent_updates %>', recent)
        page = self.__parse_tags(section)
        #print page
        return page

########NEW FILE########
__FILENAME__ = lang
# -*- coding: utf-8 -*-

# Module to handle i18n

import os
import gettext

# Initialize gettext
gettext_domain = 'turpial'
# localedir definition in development mode
if os.path.isdir(os.path.join(os.path.dirname(__file__), '..', 'i18n')):
    localedir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'i18n'))
    trans = gettext.install(gettext_domain, localedir, unicode=1)
else:
    trans = gettext.install(gettext_domain, unicode=1)

STRINGS = {
    'welcome': _('Welcome!'),
    'twitter': 'Twitter',
    'identica': 'Identi.ca',
    'add_new_account': _('Add a new account'),
    'to_start_using_turpial': _('to start using Turpial'),
    'you_have_accounts_registered': _('You have accounts registered, now'),
    'add_some_columns': _('add some columns'),
    'update_status': _('Update status'),
    'send_direct_message': _('Send direct message'),
    'settings': _('Settings'),
    'preferences': _('Preferences'),
    'about_turpial': _('About Turpial'),
    'search': _('Search'),
    'account': _('Account'),
    'accounts': _('Accounts'),
    'columns': _('Columns'),
    'authorize_turpial': _('Authorize Turpial'),
    'authorize': _('Authorize'),
    'type_the_pin': _('Type the PIN'),
    'save': _('Save'),
    'copy_the_pin': _('Authorize Turpial and copy the PIN in the text box'),
    'user_profile': _("User Profile"),
    'bio': _("Bio"),
    'location': _("Location"),
    'web': _("Web"),
    'tweets': _('Tweets'),
    'following': _('Following'),
    'followers': _('Followers'),
    'favorites': _('Favorites'),
    'criteria': _('Criteria'),
    'criteria_tooltip': _('Use hashtags, mentions or any text you want as search criteria'),
    'select_friend_to_send_message': _('Select friend to send message'),
    'friend': _('Friend'),
    'select': _('Select'),
    'load_friends_list': _('Load friends list'),
    'whats_happening': _("What's happening?"),
    'upload_image': _("Upload image"),
    'short_urls': _("Short URLs"),
    'update': _('Update'),
    'delete_column': _("Delete column"),
    'now': _("now"),
    'retweeted_by': _("Retweeted by"),
    'new': _('New'),
    'delete': _('Delete'),
    'relogin': _('Relogin'),
    'register_a_new_account': _('Register a new account'),
    'delete_an_existing_account': _('Delete an existing account'),
    'register_a_twitter_account': _('Register a Twitter account'),
    'register_an_identica_account': _('Register an Identi.ca account'),
    'no_registered_accounts': _('No registered accounts'),
    'problems_registering_new_account': _('Problems registering a new account'),
    'broadcast': _('Broadcast'),
    'you_can_not_submit_an_empty_message': _("You can not submit an empty message"),
    'message_too_long': _("Hey! That message is too long, it looks like a testament"),
    'view_conversation': _("View conversation"),
    'hide_conversation': _("Hide conversation"),
    'reply': _('Reply'),
    'quote': _('Quote'),
    'retweet': _('Retweet'),
    'mark_as_favorite': _('Mark as favorite'),
    'remove_from_favorites': _('Remove from favorites'),
    'reply_to': _('Reply to'),
    'quoting': _('Quoting'),
    'confirm_retweet': _('Confirm Retweet'),
    'do_you_want_to_retweet_status': _('Do you want to retweet this status to all your friends?'),
    'confirm_delete': _('Confirm Delete'),
    'do_you_want_to_delete_status': _('Do you want to delete this status?'),
    'do_you_want_to_delete_direct_message': _('Do you want to delete this direct message?'),
    'loading': _('Loading...'),
    'status_repeated': _('Status repeated'),
    'status_deleted': _('Status deleted'),
    'direct_message_deleted': _('Direct message deleted'),
    'status_marked_as_favorite': _('Status marked as favorite'),
    'status_removed_from_favorites': _('Status removed from favorites'),
    'send_message_to': _('Send message to'),
    'follow': _('Follow'),
    'follow_requested': _('Follow requested'),
    'unfollow': _('Unfollow'),
    'mute': _("Mute"),
    'unmute': _("Unmute"),
    'block': _("Block"),
    'report_as_spam': _("Report as spam"),
    'this_is_you': _("This is you!"),
    'conversation': _("Conversation"),
    'quit': _('Quit'),
    'in_progress': _("In progress..."),
    'select_an_account_before_post': _("Select an account before post"),
    'image_preview': _("Image Preview"),
    'confirm_discard': _('Confirm Discard'),
    'do_you_want_to_discard_message': _('Do you want to discard this message?'),
    'info': _('Info'),
    'recent': _('Recent'),
    'delete_account_confirm': _("Do you really want to delete the account %s?"),
    'messages_queue': _('Messages queue'),
    'delete_selected_message': _('Delete selected message'),
    'delete_all': _('Delete all'),
    'delete_all_messages_in_queue': _('Delete all messages in queue'),
    'message': _('Message'),
    'delete_message_from_queue_confirm': _('Do you want to delete this message from the queue?'),
    'clear_message_queue_confirm': _('Do you want to clear the queue?'),
    'messages_will_be_send': _('Messages will be send every %s as long as Turpial remain open'),
    'next_message_should_be_posted_in': _('Next message should be posted in'),
    'minute': _("minute"),
    'minutes': _("minutes"),
    'add_to_queue': _('Add to Queue'),
    'about_description': _('Microblogging client written in Python'),
    'you_are_now_following': _("You are now following @%s"),
    'you_are_no_longer_following': _("You are no longer following @%s"),
    'has_been_reported_as_spam': _("@%s has been reported as spam"),
    'has_been_blocked': _("@%s has been blocked"),
    'has_been_muted': _("@%s has been muted"),
    'has_been_unmuted': _("@%s has been unmuted"),
    'message_posted': _("Message posted"),
    'message_broadcasted': _("Message broadcasted"),
    'message_queued': _("Message queued"),
    'message_from_queue_has_been_posted': _('A message from queue has been posted'),
    'message_from_queue_has_been_broadcasted': _('A message from queue has been broadcasted'),
    'message_queued_due_to_error': _('A message has been queued due to error posting'),
    'message_queued_successfully': _('A message has been queued successfully'),
    'close': _('Close'),
    'general': _('General'),
    'notifications': _('Notifications'),
    'services': _('Services'),
    'web_browser': _('Web Browser'),
    'filters': _('Filters'),
    'proxy': _('Proxy'),
    'advanced': _('Advanced'),
    'general_tab_description': _("Adjust update frequency and other general parameters"),
    'notifications_tab_description': _("Select the notifications you want to receive from Turpial"),
    'web_browser_tab_description': _('Setup your favorite web browser to open links'),
    'services_tab_description': _("Select your preferred service to short URLs and upload images"),
    'proxy_tab_description': _("Proxy settings for Turpial (Need Restart)"),
    'advanced_tab_description': _("Advanced options. Please, keep away unless you know what you are doing"),
    'default_update_frequency': _("Default update frequency"),
    'queue_frequency': _("Queue frequency"),
    'statuses_per_column': _("Statuses per column"),
    'minimize_on_close': _("Minimize on close"),
    'notify_on_updates': _("Notify on updates"),
    'notify_on_actions': _("Notify on actions"),
    'sound_on_login': _("Sound on login"),
    'sound_on_updates': _("Sound on updates"),
    'use_default_browser': _("Use default browser"),
    'set_custom_browser': _("Set custom browser"),
    'command': _("Command"),
    'clean_cache': _("Clean cache"),
    'delete_all_files_in_cache': _("Delete all files in cache"),
    'restore_config_to_default': _("Restore configuration to default"),
    'restore_config': _("Restore config"),
    'socket_timeout': _("Socket timeout"),
    'show_avatars': _("Show user avatars"),
    'type': _("Type"),
    'host': _("Host"),
    'port': _("Port"),
    'with_authentication': _("With authentication"),
    'username': _("Username"),
    'password': _("Password"),
    'add_filter': _("Add filter"),
    'create_a_new_filter': _("Create a new filter"),
    'delete_selected_filter': _("Delete selected filter"),
    'delete_all_filters': _("Delete all filters"),
    'clear_filters_confirm': _('Do you want to clear all the filters?'),
    'error_loading_image': _("Error loading image"),
    'error_saving_image': _("Error saving image"),
    'error_loading_conversation': _("Error loading conversation"),
    'error_updating_column': _("Error updating column"),
    'error_repeating_status': _("Error repeating status"),
    'error_deleting_status': _("Error deleting status"),
    'error_marking_status_as_favorite': _("Error marking status as favorite"),
    'error_unmarking_status_as_favorite': _("Error unmarking status as favorite"),
    'error_posting_status': _("Error posting status"),
    'problems_loading_user_profile': _("Problems loading user profile"),
    'having_trouble_to_follow_user': _("Having some troubles to follow this user"),
    'having_trouble_to_unfollow_user': _("Having some troubles to unfollow this user"),
    'could_not_block_user': _("Uh oh, I could not block this user"),
    'having_issues_reporting_user_as_spam': _("Having issues reporting this user as spam"),
    'can_not_send_direct_message': _("Can not send direct message"),
    'error_shorting_url': _("Error shorting URL"),
    'error_uploading_image': _("Error uploading image"),
    'new_tweet': _("1 new tweet"),
    'new_tweets': _("%s new tweets"),
    'tweet_filtered': _("1 tweet filtered"),
    'tweets_filtered': _("%s tweets filtered"),
    'no_new_tweets': _('No new tweets'),
    'has_been_updated': _("has been updated"),
    'test': _("Test"),
    'open': _("Open"),
    'open_in_browser': _("Open in browser"),
    'default_update_frequency_tooltip': _("Set the default update frequency value for newly created columns"),
    'queue_frequency_tooltip': _("Set how often are posted messages from the queue"),
    'minimize_on_close_tooltip': _("Send Turpial to system tray instead of closing"),
    'notify_on_actions_toolip': _("Display system notifications when you perform action like follow, block, etc"),
    'sound_on_login_tooltip': _("Play sounds at startup"),
    'sound_on_updates_tooltip': _("Play sounds when you get updates"),
    'socket_timeout_tooltip': _("Set the timeout to wait before closing the connection"),
    'show_avatars_tooltip': _("When selected Turpial show user avatars, Otherwise it will show a black box (recommended for slow or limited internet connections)"),
    'confirm_restore': _("Confirm restore"),
    'do_you_want_to_restore_config': _("Do you want to restore your configuration to default? Turpial will be closed and must be restarted after this operation"),
    'config_restored_successfully': _("Configuration restored to default successfully. Please, restart Turpial"),
    'that_account_does_not_exist': _("Wait! That account does not exist"),
    'hi_there': _("Hi there!"),
    'give_me_a_minute': _("Give me a minute, I am shaking my feathers and stretching my wings..."),
    'confirm_close': _("Confirm close"),
    'do_you_want_to_close_turpial': _("Do you want to close Turpial?"),
    'oh_oh': _("Uh oh..."),
    'something_terrible_happened': _("Something terrible happened, I could not reach the Internet"),
    'try_again': _("Try again"),
    'verify_image': _("Verify image"),
    'copy_image_url': _("Copy image URL"),
    'view_exif_info': _("View EXIF info"),
    'exif_data_not_available': _('EXIF data not available'),
    'show_hide': _("Show / Hide"),
    'inline_preview': _("Inline preview"),
    'inline_preview_tooltip': _("Show images preview inline"),
    'open_images_in_browser': _("Open images in browser"),
    'open_images_in_browser_tooltip': _("Open all images in your web browser"),
    'post_next': _("Post next"),
    'post_next_tooltip': _("Post next message in queue manually"),
    'add_photo': _("Add photo"),
    'remove_photo': _("Remove photo"),
    'follows_you': _("Follows you"),
    'show_notifications': _("Show notifications"),
    'notifications_tooltip': _("Display system notifications when you get updates"),
    'update_frequency': _("Update frequency"),
    'update_frequency_tooltip': _("Set the update frequency for this column"),
    'column_options': _("Column options"),
    'notify_on_updates': _("Default notification on updates"),
    'notify_on_updates_tooltip': _("Set notifications preference for updates in newly created columns"),
    'rate_limit_exceeded': _("Rate limit exceeded"),
    'not_authorized_to_see_status': _("You are not authorized to see this status"),
}

class i18n:
    @staticmethod
    def get(key):
        try:
            return STRINGS[key]
        except KeyError:
            return key

########NEW FILE########
__FILENAME__ = notification
# -*- coding: utf-8 -*-

# Notification module for Turpial

import os
import logging

from turpial.ui.lang import i18n
from libturpial.common import OS_LINUX, OS_MAC
from libturpial.common.tools import get_username_from, detect_os

LINUX_NOTIFY = True
OSX_NOTIFY = True

try:
    import pynotify
except ImportError:
    LINUX_NOTIFY = False

try:
    from Foundation import NSUserNotification
    from Foundation import NSUserNotificationCenter
except ImportError:
    OSX_NOTIFY = False

class NotificationSystem:
    @staticmethod
    def create(images_path):
        current_os = detect_os()
        if current_os == OS_LINUX:
            return LinuxNotificationSystem(images_path)
        elif current_os == OS_MAC:
            return OsxNotificationSystem(images_path)

class BaseNotification:
    def __init__(self, disable=False):
        self.activate()
        self.disable = disable

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def notify(self, title, message, icon=None):
        raise NotImplementedError

    def updates(self, column, count, filtered=0):
        if count > 1:
            message = i18n.get('new_tweets') % count
        elif count == 1:
            message = i18n.get('new_tweet')
        else:
            message = i18n.get('no_new_tweets')

        filtered_message = ''
        if filtered == 1:
            filtered_message = ''.join([' (', i18n.get('tweet_filtered'), ')'])
        elif filtered > 1:
            filtered_message = ''.join([' (', i18n.get('tweets_filtered') % filtered, ')'])

        message += filtered_message

        title = "%s-%s %s" % (get_username_from(column.account_id),
                              column.slug, i18n.get('has_been_updated'))
        self.notify(title, message)

    def user_followed(self, username):
        self.notify(i18n.get('follow'), i18n.get('you_are_now_following') % username)

    def user_unfollowed(self, username):
        self.notify(i18n.get('unfollow'), i18n.get('you_are_no_longer_following') % username)

    def user_reported_as_spam(self, username):
        self.notify(i18n.get('report_as_spam'), i18n.get('has_been_reported_as_spam') % username)

    def user_blocked(self, username):
        self.notify(i18n.get('block'), i18n.get('has_been_blocked') % username)

    def user_muted(self, username):
        self.notify(i18n.get('mute'), i18n.get('has_been_muted') % username)

    def user_unmuted(self, username):
        self.notify(i18n.get('unmute'), i18n.get('has_been_unmuted') % username)

    def message_queued_successfully(self):
        self.notify(i18n.get('message_queued'), i18n.get('message_queued_successfully'))

    def message_from_queue_posted(self):
        self.notify(i18n.get('message_posted'), i18n.get('message_from_queue_has_been_posted'))

    def message_from_queue_broadcasted(self):
        self.notify(i18n.get('message_broadcasted'),
                    i18n.get('message_from_queue_has_been_broadcasted'))

    def message_queued_due_error(self):
        self.notify(i18n.get('message_queued'), i18n.get('message_queued_due_error'))

    def following_error(self, message, follow):
        if follow:
            self.notify(i18n.get('turpial_follow'), message)
        else:
            self.notify(i18n.get('turpial_unfollow'), message)

class LinuxNotificationSystem(BaseNotification):
    def __init__(self, images_path, disable=False):
        BaseNotification.__init__(self, not LINUX_NOTIFY)
        self.images_path = images_path

    def notify(self, title, message, icon=None):
        if self.disable:
            return

        if self.active and not self.disable:
            if pynotify.init("Turpial"):
                if not icon:
                    iconpath = os.path.join(self.images_path, 'turpial-notification.png')
                    icon = os.path.realpath(iconpath)
                icon = "file://%s" % icon
                notification = pynotify.Notification(title, message, icon)
                try:
                    notification.show()
                except Exception, e:
                    print e

class OsxNotificationSystem(BaseNotification):
    def __init__(self, images_path, disable=False):
        BaseNotification.__init__(self, not OSX_NOTIFY)
        self.images_path = images_path

    def notify(self, title, message, icon=None):
        if self.disable:
            return

        if self.active and not self.disable:
            notification = NSUserNotification.alloc().init()
            notification.setTitle_(title)
            notification.setInformativeText_(message)

            center = NSUserNotificationCenter.defaultUserNotificationCenter()
            center.scheduleNotification_(notification)
            #center.deliverNotification_(notification)

########NEW FILE########
__FILENAME__ = about
# -*- coding: utf-8 -*-

# Qt about dialog for Turpial

from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout

from PyQt4.QtCore import Qt

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import ModalDialog

from turpial import VERSION


class AboutDialog(ModalDialog):
    def __init__(self, base):
        ModalDialog.__init__(self, 320, 250)
        self.setWindowTitle(i18n.get('about_turpial'))

        icon = QLabel()
        icon.setPixmap(base.load_image('turpial.png', True))
        icon.setAlignment(Qt.AlignCenter)

        app_name = QLabel("<b>Turpial %s</b>" % VERSION)
        app_name.setAlignment(Qt.AlignCenter)
        app_description = QLabel(i18n.get('about_description'))
        app_description.setAlignment(Qt.AlignCenter)
        copyright = QLabel('Copyleft (C) 2009 - 2013 Wil Alvarez')
        copyright.setAlignment(Qt.AlignCenter)

        close_button = QPushButton(i18n.get('close'))
        close_button.clicked.connect(self.__on_close)

        button_box = QHBoxLayout()
        button_box.addStretch(1)
        button_box.setSpacing(4)
        button_box.addWidget(close_button)

        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.addWidget(icon, 1)
        vbox.addWidget(app_name)
        vbox.addWidget(app_description)
        vbox.addWidget(copyright)
        vbox.addLayout(button_box)

        self.setLayout(vbox)
        self.exec_()

    def __on_close(self):
        self.close()

########NEW FILE########
__FILENAME__ = accounts
# -*- coding: utf-8 -*-

# Qt account manager for Turpial

import os
import sys
import traceback

from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QStyle
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QListView
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QTextDocument
from PyQt4.QtGui import QStandardItem
from PyQt4.QtGui import QAbstractItemView
from PyQt4.QtGui import QStandardItemModel
from PyQt4.QtGui import QStyledItemDelegate
from PyQt4.QtGui import QHBoxLayout, QVBoxLayout

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QSize
from PyQt4.QtCore import QRect
from PyQt4.QtCore import QTimer

from turpial.ui.lang import i18n
from turpial.ui.qt.oauth import OAuthDialog
from turpial.ui.qt.widgets import ModalDialog, ErrorLabel

from libturpial.api.models.account import Account
from libturpial.common.tools import get_protocol_from, get_username_from

USERNAME_FONT = QFont("Helvetica", 14)
PROTOCOL_FONT = QFont("Helvetica", 11)

class AccountsDialog(ModalDialog):
    def __init__(self, base):
        ModalDialog.__init__(self, 380,325)
        self.base = base
        self.setWindowTitle(i18n.get('accounts'))

        self.list_ = QListView()
        self.list_.setResizeMode(QListView.Adjust)
        self.list_.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        account_delegate = AccountDelegate(base)
        self.list_.setItemDelegate(account_delegate)
        self.list_.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_.clicked.connect(self.__account_clicked)

        twitter_menu = QAction(i18n.get('twitter'), self)
        twitter_menu.setIcon(QIcon(base.load_image('twitter.png', True)))
        twitter_menu.setToolTip(i18n.get('register_a_twitter_account'))
        twitter_menu.triggered.connect(self.__register_twitter_account)

        # TODO: Enable when identi.ca support is ready
        identica_menu = QAction(i18n.get('identica'), self)
        identica_menu.setIcon(QIcon(base.load_image('identica.png', True)))
        identica_menu.setToolTip(i18n.get('register_an_identica_account'))
        identica_menu.setEnabled(False)

        self.menu = QMenu()
        self.menu.addAction(twitter_menu)
        self.menu.addAction(identica_menu)

        self.new_button = QPushButton(i18n.get('new'))
        self.new_button.setMenu(self.menu)
        self.new_button.setToolTip(i18n.get('register_a_new_account'))

        self.delete_button = QPushButton(i18n.get('delete'))
        self.delete_button.setEnabled(False)
        self.delete_button.setToolTip(i18n.get('delete_an_existing_account'))
        self.delete_button.clicked.connect(self.__delete_account)

        self.relogin_button = QPushButton(i18n.get('relogin'))
        self.relogin_button.setEnabled(False)
        self.relogin_button.setToolTip(i18n.get('relogin_this_account'))
        self.relogin_button.clicked.connect(self.__relogin_account)

        button_box = QHBoxLayout()
        button_box.addStretch(1)
        button_box.setSpacing(4)
        button_box.addWidget(self.new_button)
        button_box.addWidget(self.delete_button)
        button_box.addWidget(self.relogin_button)

        self.error_message = ErrorLabel()
        self.error_message.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(self.list_)
        layout.addWidget(self.error_message)
        layout.addLayout(button_box)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        self.__update()

        self.base.account_deleted.connect(self.__update)
        self.base.account_loaded.connect(self.__update)
        self.base.account_registered.connect(self.__update)

        self.exec_()

    def __update(self):
        model = QStandardItemModel()
        self.list_.setModel(model)
        accounts = self.base.core.get_registered_accounts()
        count = 0
        for account in accounts:
            item = QStandardItem()
            filepath = os.path.join(self.base.images_path, 'unknown.png')
            item.setData(filepath, AccountDelegate.AvatarRole)
            item.setData(get_username_from(account.id_), AccountDelegate.UsernameRole)
            item.setData(get_protocol_from(account.id_).capitalize(), AccountDelegate.ProtocolRole)
            item.setData(account.id_, AccountDelegate.IdRole)
            model.appendRow(item)
            count += 1

        self.__enable(True)
        self.delete_button.setEnabled(False)
        self.relogin_button.setEnabled(False)

    def __account_clicked(self, point):
        self.delete_button.setEnabled(True)
        self.relogin_button.setEnabled(True)

    def __delete_account(self):
        self.__enable(False)
        selection = self.list_.selectionModel()
        index = selection.selectedIndexes()[0]
        account_id = str(index.data(AccountDelegate.IdRole).toPyObject())
        message = i18n.get('delete_account_confirm') % account_id
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            message)
        if not confirmation:
            self.__enable(True)
            return
        self.base.delete_account(account_id)

    def __register_twitter_account(self):
        self.__enable(False)
        account = Account.new('twitter')
        try:
            oauth_dialog = OAuthDialog(self, account.request_oauth_access())
        except Exception, e:
            err_msg = "%s: %s" % (sys.exc_info()[0], sys.exc_info()[1])
            print traceback.format_exc()
            print err_msg
            self.error(i18n.get('problems_registering_new_account'))
            self.__enable(True)
            return

        if oauth_dialog.result() == QDialog.Accepted:
            pin = oauth_dialog.pin.text()
            try:
                account.authorize_oauth_access(pin)
                self.base.save_account(account)
            except Exception, e:
                err_msg = "%s: %s" % (sys.exc_info()[0], sys.exc_info()[1])
                print traceback.format_exc()
                print err_msg
                self.error(i18n.get('problems_registering_new_account'))
        self.__enable(True)

    def __relogin_account(self):
        self.__enable(False)
        selection = self.list_.selectionModel()
        try:
            index = selection.selectedIndexes()[0]
            account_id = str(index.data(AccountDelegate.IdRole).toPyObject())
            self.base.load_account(account_id)
        except Exception, e:
                err_msg = "%s: %s" % (sys.exc_info()[0], sys.exc_info()[1])
                print traceback.format_exc()
                print err_msg
                self.error(i18n.get('that_account_does_not_exist'))
                self.__enable(True)

    def __enable(self, value):
        # TODO: Display a loading message/indicator
        self.list_.setEnabled(value)
        self.new_button.setEnabled(value)
        self.delete_button.setEnabled(value)
        self.relogin_button.setEnabled(value)

    def __on_timeout(self):
        self.error_message.setText('')
        self.error_message.setVisible(False)

    def error(self, message):
        self.error_message.setText(message)
        self.error_message.setVisible(True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)
        self.timer.start(5000)

class AccountDelegate(QStyledItemDelegate):
    UsernameRole = Qt.UserRole + 100
    ProtocolRole = Qt.UserRole + 101
    AvatarRole = Qt.UserRole + 102
    IdRole = Qt.UserRole + 103

    AVATAR_SIZE = 48
    BOX_MARGIN = 4
    TEXT_MARGIN = 0

    def __init__(self, base):
        QStyledItemDelegate.__init__(self)
        self.avatar = None

    def sizeHint(self, option, index):
        height = self.AVATAR_SIZE + (self.BOX_MARGIN * 2)
        self.size = QSize(option.rect.width(), height)
        return self.size

    def paint(self, painter, option, index):
        painter.save()

        selected = False
        cell_width = self.size.width()

        rect = option.rect
        rect.width = self.size.width()
        rect.height = self.size.height()
        protocol_color = "999"
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
            protocol_color = "ddd"
            selected = True

        # Draw avatar
        if not self.avatar:
            avatar_filepath = index.data(self.AvatarRole).toPyObject()
            self.avatar = QPixmap(avatar_filepath)
        x = option.rect.left() + self.BOX_MARGIN
        y = option.rect.top() + self.BOX_MARGIN
        rect = QRect(x, y, self.AVATAR_SIZE, self.AVATAR_SIZE)
        painter.drawPixmap(rect, self.avatar)

        # Draw username
        username_string = index.data(self.UsernameRole).toPyObject()
        username = QTextDocument()
        username.setHtml("%s" % username_string)
        username.setDefaultFont(USERNAME_FONT)
        #username.setTextWidth(self.__calculate_text_width(width))

        x = option.rect.left() + self.BOX_MARGIN + self.AVATAR_SIZE
        y = option.rect.top() + self.BOX_MARGIN
        painter.translate(x, y)
        if selected:
            painter.setPen(option.palette.highlightedText().color())
        username.drawContents(painter)

        # Draw protocol
        y = username.size().height() + self.TEXT_MARGIN
        painter.translate(0, y)
        protocol_string = index.data(self.ProtocolRole).toPyObject()
        protocol = QTextDocument()
        protocol.setHtml("<span style='color: #%s;'>%s</span>" % (protocol_color, protocol_string))
        protocol.setDefaultFont(PROTOCOL_FONT)
        protocol.drawContents(painter)

        painter.restore()

########NEW FILE########
__FILENAME__ = column
# -*- coding: utf-8 -*-

# Qt widget to implement statuses column in Turpial

#from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QSize
from PyQt4.QtCore import QRect
from PyQt4.QtCore import QLine
from PyQt4.QtCore import QTimer

from PyQt4.QtGui import QFont
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QTextDocument
from PyQt4.QtGui import QStyledItemDelegate
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout

from turpial.ui.lang import i18n
from turpial.ui.qt.webview import StatusesWebView
from turpial.ui.qt.widgets import ImageButton, BarLoadIndicator
from turpial.ui.qt.preferences import Slider

from libturpial.common import get_preview_service_from_url, unescape_list_name, OS_MAC
from libturpial.common.tools import get_account_id_from, get_column_slug_from, get_protocol_from,\
        get_username_from, detect_os

class StatusesColumn(QWidget):
    NOTIFICATION_ERROR = 'error'
    NOTIFICATION_SUCCESS = 'success'
    NOTIFICATION_WARNING = 'warning'
    NOTIFICATION_INFO = 'notice'
    SLIDER_INTERVAL = 5000

    def __init__(self, base, column_id, include_header=True):
        QWidget.__init__(self)
        self.base = base
        self.setMinimumWidth(280)
        self.statuses = []
        self.conversations = {}
        self.id_ = None
        #self.fgcolor = "#e3e3e3"
        #self.fgcolor = "#f9a231"
        #self.updating = False
        self.last_id = None

        self.loader = BarLoadIndicator()
        self.loader.setVisible(False)

        self.slider = Slider('', 5, unit='m')
        self.slider.changed.connect(self.__on_slider_update)
        self.slider.hide()

        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)

        sliderbox = QHBoxLayout()
        sliderbox.setSpacing(8)
        sliderbox.setContentsMargins(10, 5, 10, 0)

        self.webview = StatusesWebView(self.base, self.id_)
        self.webview.link_clicked.connect(self.__link_clicked)
        self.webview.hashtag_clicked.connect(self.__hashtag_clicked)
        self.webview.profile_clicked.connect(self.__profile_clicked)
        self.webview.cmd_clicked.connect(self.__cmd_clicked)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        if include_header:
            header = self.__build_header(column_id)
            layout.addWidget(header)
            layout.addWidget(self.slider)
            layout.addWidget(self.loader)
        layout.addWidget(self.webview, 1)

        self.setLayout(layout)

    def __on_timeout(self):
        current_value = self.base.get_column_update_interval(self.id_)
        new_value = self.slider.get_value()
        if current_value != new_value:
            self.base.set_column_update_interval(self.id_, new_value)
            column = self.base.get_column_from_id(self.id_)
            self.base.add_timer(column)
        self.hide_slider()

    def __on_slider_update(self, value):
        self.timer.stop()
        self.timer.start(self.SLIDER_INTERVAL)

    def __build_header(self, column_id):
        self.set_column_id(column_id)
        username = get_username_from(self.account_id)
        column_slug = get_column_slug_from(column_id)
        column_slug = unescape_list_name(column_slug)
        column_slug = column_slug.replace('%23', '#')
        column_slug = column_slug.replace('%40', '@')

        #font = QFont('Titillium Web', 18, QFont.Normal, False)
        # This is to handle the 96dpi vs 72dpi screen resolutions on Mac vs the world
        if detect_os() == OS_MAC:
            font = QFont('Maven Pro Light', 25, 0, False)
            font2 = QFont('Monda', 14, 0, False)
        else:
            font = QFont('Maven Pro Light', 16, QFont.Light, False)
            font2 = QFont('Monda', 10, QFont.Light, False)

        bg_style = "background-color: %s; color: %s;" % (self.base.bgcolor, self.base.fgcolor)
        caption = QLabel(username)
        caption.setStyleSheet("QLabel { %s }" % bg_style)
        caption.setFont(font)

        caption2 = QLabel(column_slug)
        caption2.setStyleSheet("QLabel { %s }" % bg_style)
        caption2.setFont(font2)
        caption2.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

        caption_box = QHBoxLayout()
        caption_box.setSpacing(8)
        caption_box.addWidget(caption)
        caption_box.addWidget(caption2)
        caption_box.addStretch(1)

        close_button = ImageButton(self.base, 'action-menu-shadowed.png', i18n.get('column_options'))
        close_button.clicked.connect(self.__show_options_menu)

        header_layout = QHBoxLayout()
        header_layout.addLayout(caption_box, 1)
        header_layout.addWidget(close_button)

        header = QWidget()
        header.setStyleSheet("QWidget { %s }" % bg_style)
        header.setLayout(header_layout)
        return header

    def __show_options_menu(self):
        self.hide_slider()
        self.options_menu = QMenu(self)

        notifications = QAction(i18n.get('notifications'), self)
        notifications.setCheckable(True)
        notifications.setChecked(self.base.get_column_notification(self.id_))
        notifications.triggered.connect(self.__toogle_notifications)
        notifications.setToolTip(i18n.get('notifications_toolip'))

        caption = "%s (%sm)" % (i18n.get('update_frequency'), self.base.get_column_update_interval(self.id_))
        update = QAction(caption, self)
        update.triggered.connect(self.show_slider)
        update.setToolTip(i18n.get('update_frequency_tooltip'))

        delete = QAction(i18n.get('delete'), self)
        delete.triggered.connect(self.__delete_column)

        self.options_menu.addAction(notifications)
        self.options_menu.addAction(update)
        self.options_menu.addAction(delete)
        self.options_menu.exec_(QCursor.pos())

    def __toogle_notifications(self):
        notify = not self.base.get_column_notification(self.id_)
        self.base.set_column_notification(self.id_, notify)

    def __delete_column(self):
        self.base.core.delete_column(self.id_)

    def __link_clicked(self, url):
        url = str(url)
        preview_service = get_preview_service_from_url(url)
        self.base.open_url(url)

    def __hashtag_clicked(self, hashtag):
        self.base.add_search_column(self.account_id, str(hashtag))

    def __profile_clicked(self, username):
        self.base.show_profile_dialog(self.account_id, str(username))

    def __cmd_clicked(self, url):
        status_id = str(url.split(':')[1])
        cmd = url.split(':')[0]
        status = None
        try:
            print 'Seeking for status in self array'
            for status_ in self.statuses:
                if status_.id_ == status_id:
                    status = status_
                    break
            if status is None:
                raise KeyError
        except KeyError:
            print 'Seeking for status in conversations array'
            for status_root, statuses in self.conversations.iteritems():
                for item in statuses:
                    if item.id_ == status_id:
                        status = item
                        break
                if status is not None:
                    break

        if status is None:
            self.notify_error(status_id, i18n.get('try_again'))

        if cmd == 'reply':
            self.__reply_status(status)
        elif cmd == 'quote':
            self.__quote_status(status)
        elif cmd == 'repeat':
            self.__repeat_status(status)
        elif cmd == 'delete':
            self.__delete_status(status)
        elif cmd == 'favorite':
            self.__mark_status_as_favorite(status)
        elif cmd == 'unfavorite':
            self.__unmark_status_as_favorite(status)
        elif cmd == 'delete_direct':
            self.__delete_direct_message(status)
        elif cmd == 'reply_direct':
            self.__reply_direct_message(status)
        elif cmd == 'view_conversation':
            self.__view_conversation(status)
        elif cmd == 'hide_conversation':
            self.__hide_conversation(status)
        elif cmd == 'show_avatar':
            self.__show_avatar(status)

    def __reply_status(self, status):
        self.base.show_update_box_for_reply(self.account_id, status)

    def __quote_status(self, status):
        self.base.show_update_box_for_quote(self.account_id, status)

    def __repeat_status(self, status):
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_retweet'),
            i18n.get('do_you_want_to_retweet_status'))
        if confirmation:
            self.lock_status(status.id_)
            self.base.repeat_status(self.id_, self.account_id, status)

    def __delete_status(self, status):
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            i18n.get('do_you_want_to_delete_status'))
        if confirmation:
            self.lock_status(status.id_)
            self.base.delete_status(self.id_, self.account_id, status)

    def __delete_direct_message(self, status):
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            i18n.get('do_you_want_to_delete_direct_message'))
        if confirmation:
            self.lock_status(status.id_)
            self.base.delete_direct_message(self.id_, self.account_id, status)

    def __reply_direct_message(self, status):
        self.base.show_update_box_for_reply_direct(self.account_id, status)

    def __mark_status_as_favorite(self, status):
        self.lock_status(status.id_)
        self.base.mark_status_as_favorite(self.id_, self.account_id, status)

    def __unmark_status_as_favorite(self, status):
        self.lock_status(status.id_)
        self.base.unmark_status_as_favorite(self.id_, self.account_id, status)

    def __view_conversation(self, status):
        self.webview.view_conversation(status.id_)
        self.base.get_conversation(self.account_id, status, self.id_, status.id_)

    def __hide_conversation(self, status):
        del self.conversations[status.id_]
        self.webview.clear_conversation(status.id_)

    def __show_avatar(self, status):
        self.base.show_profile_image(self.account_id, status.username)

    def __set_last_status_id(self, statuses):
        if statuses[0].repeated_by:
            self.last_id = statuses[0].original_status_id
        else:
            self.last_id = statuses[0].id_

    def show_slider(self):
        self.slider.set_value(self.base.get_column_update_interval(self.id_))
        self.slider.show()
        self.timer.start(self.SLIDER_INTERVAL)

    def hide_slider(self):
        self.slider.hide()

    def set_column_id(self, column_id):
        self.id_ = column_id
        self.account_id = get_account_id_from(column_id)
        self.protocol_id = get_protocol_from(self.account_id)
        self.webview.column_id = column_id

    def clear(self):
        self.webview.clear()

    def start_updating(self):
        self.loader.setVisible(True)
        return self.last_id

    def stop_updating(self):
        self.loader.setVisible(False)

    def update_timestamps(self):
        self.webview.sync_timestamps(self.statuses)
        self.webview.clear_new_marks()

    def update_statuses(self, statuses):
        self.__set_last_status_id(statuses)

        self.update_timestamps()
        self.webview.update_statuses(statuses)

        # Filter repeated statuses
        unique_statuses = [s1 for s1 in statuses if s1 not in self.statuses]

        # Remove old conversations
        to_remove = self.statuses[-(len(unique_statuses)):]
        self.statuses = statuses + self.statuses[: -(len(unique_statuses))]
        for status in to_remove:
            if self.conversations.has_key(status.id_):
                del self.conversations[status.id_]

    def update_conversation(self, status, status_root_id):
        status_root_id = str(status_root_id)
        self.webview.update_conversation(status, status_root_id)
        if status_root_id in self.conversations:
            self.conversations[status_root_id].append(status)
        else:
            self.conversations[status_root_id] = [status]

    def error_in_conversation(self, status_root_id):
        self.webview.clear_conversation(status_root_id)

    def mark_status_as_favorite(self, status_id):
        mark = "setFavorite('%s')" % status_id
        self.webview.execute_javascript(mark)

    def unmark_status_as_favorite(self, status_id):
        mark = "unsetFavorite('%s');" % status_id
        self.webview.execute_javascript(mark)

    def mark_status_as_repeated(self, status_id):
        mark = "setRepeated('%s');" % status_id
        self.webview.execute_javascript(mark)

    def remove_status(self, status_id):
        operation = "removeStatus('%s');" % status_id
        self.webview.execute_javascript(operation)

    def lock_status(self, status_id):
        operation = "lockStatus('%s');" % status_id
        self.webview.execute_javascript(operation)

    def release_status(self, status_id):
        operation = "releaseStatus('%s');" % status_id
        self.webview.execute_javascript(operation)

    def notify(self, id_, type_, message):
        message = message.replace("'", "\"")
        notification = "addNotify('%s', '%s', '%s');" % (id_, type_, message)
        self.webview.execute_javascript(notification)

    def notify_error(self, id_, message):
        self.notify(id_, self.NOTIFICATION_ERROR, message)

    def notify_success(self, id_, message):
        self.notify(id_, self.NOTIFICATION_SUCCESS, message)

    def notify_warning(self, id_, message):
        self.notify(id_, self.NOTIFICATION_WARNING, message)

    def notify_info(self, id_, message):
        self.notify(id_, self.NOTIFICATION_INFO, message)


class StatusDelegate(QStyledItemDelegate):
    FullnameRole = Qt.UserRole + 100
    UsernameRole = Qt.UserRole + 101
    AvatarRole = Qt.UserRole + 102
    MessageRole = Qt.UserRole + 103
    DateRole = Qt.UserRole + 104
    RepostedRole = Qt.UserRole + 105
    ProtectedRole = Qt.UserRole + 106
    FavoritedRole = Qt.UserRole + 107
    RepeatedRole = Qt.UserRole + 108
    VerifiedRole = Qt.UserRole + 109
    URLsEntitiesRole = Qt.UserRole + 110

    AVATAR_SIZE = 48
    BOX_MARGIN = 2
    LEFT_MESSAGE_MARGIN = 8
    TOP_MESSAGE_MARGIN = 0
    BOTTOM_MESSAGE_MARGIN = 0
    COMPLEMENT_HEIGHT = 5

    def __init__(self, base):
        QStyledItemDelegate.__init__(self)
        self.favorite_icon = base.load_image('mark-favorite.png', True)
        self.verified_icon = base.load_image('mark-verified.png', True)
        self.protected_icon = base.load_image('mark-protected.png', True)
        self.repeated_icon = base.load_image('mark-repeated.png', True)
        self.reposted_icon = base.load_image('mark-reposted.png', True)
        self.avatar = None

    def __calculate_text_width(self, width):
        width -= ((self.BOX_MARGIN * 2) + self.AVATAR_SIZE + self.LEFT_MESSAGE_MARGIN)
        return width

    def __render_fullname(self, width, index):
        fullname = index.data(self.FullnameRole).toPyObject()
        doc = QTextDocument()
        doc.setHtml("<b>%s</b>" % fullname)
        doc.setDefaultFont(FULLNAME_FONT)
        doc.setTextWidth(self.__calculate_text_width(width))
        return doc

    def __render_status_message(self, width, index):
        message = unicode(index.data(self.MessageRole).toPyObject())
        urls = index.data(self.URLsEntitiesRole).toPyObject()
        for url in urls:
            pretty_url = "<a href='%s'>%s</a>" % (url.url, url.display_text)
            message = message.replace(url.search_for, pretty_url)
        doc = QTextDocument()
        doc.setHtml(message)
        doc.setTextWidth(self.__calculate_text_width(width))
        return doc

    def __render_username(self, width, index):
        username_string = index.data(self.UsernameRole).toPyObject()
        username = QTextDocument()
        if username_string != '':
            username.setHtml("<span style='color: #666;'>@%s</span>" % username_string)
        else:
            username.setHtml("<span style='color: #666;'></span>" % username_string)
        username.setDefaultFont(USERNAME_FONT)
        username.setTextWidth(self.__calculate_text_width(width))
        return username

    def sizeHint(self, option, index):
        fullname = self.__render_fullname(option.rect.size().width(), index)
        message = self.__render_status_message(option.rect.size().width(), index)

        height = option.rect.top() + fullname.size().height() + self.TOP_MESSAGE_MARGIN + message.size().height()
        if height < self.AVATAR_SIZE:
            height = self.AVATAR_SIZE + self.COMPLEMENT_HEIGHT

        height += self.BOTTOM_MESSAGE_MARGIN + 16 + (self.BOX_MARGIN * 3)

        self.size = QSize(option.rect.width(), height)
        return self.size

    def paint(self, painter, option, index):
        painter.save()

        cell_width = self.size.width()

        #if option.state & QStyle.State_Selected:
        #    painter.fillRect(option.rect, option.palette.highlight())
        #painter.drawRect(option.rect)


        # Draw marks before translating painter
        # =====================================

        # Draw avatar
        if not self.avatar:
            avatar_filepath = index.data(self.AvatarRole).toPyObject()
            self.avatar = QPixmap(avatar_filepath)
        x = option.rect.left() + (self.BOX_MARGIN * 2)
        y = option.rect.top() + (self.BOX_MARGIN * 2)
        rect = QRect(x, y, self.AVATAR_SIZE, self.AVATAR_SIZE)
        painter.drawPixmap(rect, self.avatar)

        # Draw verified account icon
        if index.data(self.VerifiedRole).toPyObject():
            rect2 = QRect(rect.right() - 11, rect.bottom() - 10, 16, 16)
            painter.drawPixmap(rect2, self.verified_icon)

        marks_margin = 0
        # Favorite mark
        if index.data(self.FavoritedRole).toPyObject():
            x = cell_width - 16 - self.BOX_MARGIN
            y = option.rect.top() + self.BOX_MARGIN
            rect = QRect(x, y, 16, 16)
            painter.drawPixmap(rect, self.favorite_icon)
            marks_margin = 16

        # Draw reposted icon
        if index.data(self.RepeatedRole).toPyObject():
            x = cell_width - 16 - self.BOX_MARGIN - marks_margin
            y = option.rect.top() + self.BOX_MARGIN
            rect = QRect(x, y, 16, 16)
            painter.drawPixmap(rect, self.repeated_icon)

        # Draw protected account icon
        protected_icon_margin = 0
        if index.data(self.ProtectedRole).toPyObject():
            x = option.rect.left() + self.BOX_MARGIN + self.AVATAR_SIZE + self.LEFT_MESSAGE_MARGIN
            y = option.rect.top() + self.BOX_MARGIN
            rect = QRect(x, y, 16, 16)
            painter.drawPixmap(rect, self.protected_icon)
            protected_icon_margin = 16

        # ==== End of pixmap drawing ====

        accumulated_height = 0

        # Draw fullname
        fullname = self.__render_fullname(cell_width, index)
        x = option.rect.left() + self.BOX_MARGIN + self.AVATAR_SIZE
        x += self.LEFT_MESSAGE_MARGIN + protected_icon_margin
        y = option.rect.top()
        painter.translate(x, y)
        fullname.drawContents(painter)

        # Draw username
        username = self.__render_username(cell_width, index)
        painter.translate(fullname.idealWidth(), 0)
        username.drawContents(painter)

        # Draw status message
        x = -fullname.idealWidth() - protected_icon_margin
        y = fullname.size().height() + self.TOP_MESSAGE_MARGIN
        painter.translate(x, y)
        message = self.__render_status_message(cell_width, index)
        message.drawContents(painter)
        accumulated_height += y + message.size().height()

        # Draw reposted by
        x = self.BOX_MARGIN + 16 - (self.LEFT_MESSAGE_MARGIN + self.AVATAR_SIZE)
        y = message.size().height() + self.BOTTOM_MESSAGE_MARGIN
        if accumulated_height < self.AVATAR_SIZE:
            y += (self.AVATAR_SIZE - accumulated_height) + self.COMPLEMENT_HEIGHT
        painter.translate(x, y)

        reposted_by = index.data(self.RepostedRole).toPyObject()
        if reposted_by:
            reposted = QTextDocument()
            reposted.setHtml("<span style='color: #999;'>%s</span>" % reposted_by)
            reposted.setDefaultFont(FOOTER_FONT)
            reposted.setTextWidth(self.__calculate_text_width(cell_width))
            reposted.drawContents(painter)

            # Draw reposted icon
            rect2 = QRect(-16, 3, 16, 16)
            painter.drawPixmap(rect2, self.reposted_icon)

        # Draw datetime
        datetime = index.data(self.DateRole).toPyObject()
        timestamp = QTextDocument()
        timestamp.setHtml("<span style='color: #999;'>%s</span>" % datetime)
        timestamp.setDefaultFont(FOOTER_FONT)
        timestamp.setTextWidth(self.__calculate_text_width(cell_width))
        x = self.size.width() - timestamp.idealWidth() - 20 - self.BOX_MARGIN
        painter.translate(x, 0)
        timestamp.drawContents(painter)

        painter.resetTransform()
        painter.translate(0, option.rect.bottom())
        line = QLine(0, 0, option.rect.width(), 0)
        painter.setPen(QColor(230, 230, 230))
        painter.drawLine(line)

        painter.restore()

########NEW FILE########
__FILENAME__ = container
# -*- coding: utf-8 -*-

# Qt container for all columns in Turpial

from PyQt4.QtCore import Qt

from PyQt4.QtGui import QFont
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QScrollArea
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout

from turpial.ui.lang import i18n
from turpial.ui.qt.column import StatusesColumn
from turpial.ui.qt.widgets import BarLoadIndicator

from libturpial.common import OS_MAC
from libturpial.common.tools import detect_os

class Container(QVBoxLayout):
    def __init__(self, base):
        QVBoxLayout.__init__(self)
        self.base = base
        self.child = None
        self.columns = {}
        self.is_empty = None
        self.loading()

    def __link_clicked(self, url):
        if url == 'cmd:add_columns':
            self.base.show_column_menu(QCursor.pos())
        elif url == 'cmd:add_accounts':
            self.base.show_accounts_dialog()
        elif url == 'cmd:restart':
            self.base.restart()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def empty(self, with_accounts=None):
        if self.child:
            self.clear_layout(self)

        image = self.base.load_image('turpial-196.png', True)
        logo = QLabel()
        logo.setPixmap(image)
        logo.setAlignment(Qt.AlignCenter)
        logo.setContentsMargins(0, 80, 0, 0)

        appname = QLabel('Turpial 3')
        if detect_os() == OS_MAC:
            font = QFont('Maven Pro Light', 28, 0, False)
            font2 = QFont('Ubuntu', 16, 0, False)
        else:
            font = QFont('Maven Pro Light', 18, QFont.Light, False)
            font2 = QFont('Ubuntu', 12, QFont.Normal, False)
        appname.setFont(font)

        welcome = QLabel()
        welcome.setText(i18n.get('welcome'))
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setFont(font)

        message = QLabel()
        if with_accounts:
            text = "%s <a href='cmd:add_columns'>%s</a>" % (i18n.get('you_have_accounts_registered'),
                i18n.get('add_some_columns'))
        else:
            text = "<a href='cmd:add_accounts'>%s</a> %s" % (i18n.get('add_new_account'),
                i18n.get('to_start_using_turpial'))
        message.setText(text)
        message.linkActivated.connect(self.__link_clicked)
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        message.setFont(font2)

        self.child = QVBoxLayout()
        self.child.addWidget(logo)
        self.child.addWidget(welcome)
        self.child.setSpacing(10)
        self.child.addWidget(message)
        self.child.setSpacing(10)
        self.child.setContentsMargins(30, 0, 30, 60)

        self.insertLayout(0, self.child)
        self.is_empty = True

    def loading(self):
        if self.child:
            self.clear_layout(self)

        image = self.base.load_image('turpial-196.png', True)
        logo = QLabel()
        logo.setPixmap(image)
        logo.setAlignment(Qt.AlignCenter)
        logo.setContentsMargins(0, 80, 0, 0)

        appname = QLabel('Turpial 3')
        if detect_os() == OS_MAC:
            font = QFont('Maven Pro Light', 28, 0, False)
            font2 = QFont('Ubuntu', 16, 0, False)
        else:
            font = QFont('Maven Pro Light', 18, QFont.Light, False)
            font2 = QFont('Ubuntu', 12, QFont.Normal, False)
        appname.setFont(font)

        welcome = QLabel()
        welcome.setText(i18n.get('hi_there'))
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setFont(font)

        message = QLabel()
        message.setText(i18n.get('give_me_a_minute'))
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        message.setFont(font2)

        loader = BarLoadIndicator(None)

        self.child = QVBoxLayout()
        self.child.addWidget(logo)
        self.child.addWidget(welcome)
        self.child.addSpacing(10)
        self.child.addWidget(message)
        #self.child.setSpacing(10)
        self.child.addStretch(1)
        self.child.addWidget(loader)
        self.child.setContentsMargins(30, 0, 30, 30)

        self.insertLayout(0, self.child)
        self.is_empty = True

    def error(self):
        if self.child:
            self.clear_layout(self)

        image = self.base.load_image('turpial-196.png', True)
        logo = QLabel()
        logo.setPixmap(image)
        logo.setAlignment(Qt.AlignCenter)
        logo.setContentsMargins(0, 80, 0, 0)

        appname = QLabel('Turpial 3')
        if detect_os() == OS_MAC:
            font = QFont('Maven Pro Light', 28, 0, False)
            font2 = QFont('Ubuntu', 16, 0, False)
        else:
            font = QFont('Maven Pro Light', 18, QFont.Light, False)
            font2 = QFont('Ubuntu', 12, QFont.Normal, False)
        appname.setFont(font)

        welcome = QLabel()
        welcome.setText(i18n.get('oh_oh'))
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setFont(font)

        message = QLabel()
        text = "%s. <a href='cmd:restart'>%s</a>" % (i18n.get('something_terrible_happened'),
            i18n.get('try_again'))
        message.setText(text)
        message.linkActivated.connect(self.__link_clicked)
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        message.setFont(font2)

        self.child = QVBoxLayout()
        self.child.addWidget(logo)
        self.child.addWidget(welcome)
        self.child.addSpacing(10)
        self.child.addWidget(message)
        #self.child.setSpacing(10)
        self.child.addStretch(1)
        self.child.setContentsMargins(30, 0, 30, 30)

        self.insertLayout(0, self.child)
        self.is_empty = True

    def normal(self):
        columns = self.base.core.get_registered_columns()

        if self.child:
            self.clear_layout(self)

        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.columns = {}
        for column in columns:
            self.columns[column.id_] = StatusesColumn(self.base, column.id_)
            hbox.addWidget(self.columns[column.id_], 1)

        viewport = QWidget()
        viewport.setLayout(hbox)

        self.child = QScrollArea()
        self.child.setWidgetResizable(True)
        self.child.setWidget(viewport)

        self.addWidget(self.child, 1)
        self.is_empty = False

    def start_updating(self, column_id):
        return self.columns[column_id].start_updating()

    def stop_updating(self, column_id, errmsg=None, errtype=None):
        self.columns[column_id].stop_updating()

    def is_updating(self, column_id):
        #return self.columns[column_id].updating
        return False

    def update_timestamps(self, column_id):
        self.columns[column_id].update_timestamps()
        self.stop_updating(column_id)

    def update_column(self, column_id, statuses):
        if column_id not in self.columns:
            return
        self.columns[column_id].update_statuses(statuses)
        self.stop_updating(column_id)
        self.base.add_extra_friends_from_statuses(statuses)

    def add_column(self, column_id):
        if self.is_empty:
            self.normal()
        else:
            viewport = self.child.widget()
            hbox = viewport.layout()
            self.columns[column_id] = StatusesColumn(self.base, column_id)
            hbox.addWidget(self.columns[column_id], 1)

    def remove_column(self, column_id):
        self.columns[column_id].deleteLater()
        del self.columns[column_id]

    def mark_status_as_favorite(self, status_id):
        for id_, column in self.columns.iteritems():
            column.mark_status_as_favorite(status_id)
            column.release_status(status_id)

    def unmark_status_as_favorite(self, status_id):
        for id_, column in self.columns.iteritems():
            column.unmark_status_as_favorite(status_id)
            column.release_status(status_id)

    def mark_status_as_repeated(self, status_id):
        for id_, column in self.columns.iteritems():
            column.mark_status_as_repeated(status_id)
            column.release_status(status_id)

    def remove_status(self, status_id):
        for id_, column in self.columns.iteritems():
            column.remove_status(status_id)

    def update_conversation(self, status, column_id, status_root_id):
        for id_, column in self.columns.iteritems():
            if id_ == column_id:
                column.update_conversation(status, status_root_id)

    def error_loading_conversation(self, column_id, status_root_id, response=None):
        for id_, column in self.columns.iteritems():
            if id_ == column_id:
                column.error_in_conversation(status_root_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_loading_conversation'))
        self.notify_error(column_id, self.base.random_id(), message)

    def error_updating_column(self, column_id, response=None):
        self.stop_updating(column_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_updating_column'))
        self.notify_error(column_id, self.base.random_id(), message)

    def error_repeating_status(self, column_id, status_id, response=None):
        for id_, column in self.columns.iteritems():
            column.release_status(status_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_repeating_status'))
        self.notify_error(column_id, status_id, message)

    def error_deleting_status(self, column_id, status_id, response=None):
        for id_, column in self.columns.iteritems():
            column.release_status(status_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_deleting_status'))
        self.notify_error(column_id, status_id, message)

    def error_marking_status_as_favorite(self, column_id, status_id, response=None):
        for id_, column in self.columns.iteritems():
            column.release_status(status_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_marking_status_as_favorite'))
        self.notify_error(column_id, status_id, message)

    def error_unmarking_status_as_favorite(self, column_id, status_id, response=None):
        for id_, column in self.columns.iteritems():
            column.release_status(status_id)
        message = self.base.get_error_message_from_response(response, i18n.get('error_unmarking_status_as_favorite'))
        self.notify_error(column_id, status_id, message)

    def notify_error(self, column_id, id_, message):
        self.columns[str(column_id)].notify_error(id_, message)

    def notify_success(self, column_id, id_, message):
        self.columns[str(column_id)].notify_success(id_, message)

    def notify_warning(self, column_id, id_, message):
        self.columns[str(column_id)].notify_warning(id_, message)

    def notify_info(self, column_id, id_, message):
        self.columns[str(column_id)].notify_info(id_, message)

########NEW FILE########
__FILENAME__ = dock
# -*- coding: utf-8 -*-

# Qt dock for Turpial

from functools import partial

from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QToolBar
from PyQt4.QtGui import QStatusBar
from PyQt4.QtGui import QSizePolicy

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QPoint
from PyQt4.QtCore import pyqtSignal

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import ImageButton

from libturpial.common import OS_MAC
from libturpial.common.tools import detect_os

class Dock(QStatusBar):

    accounts_clicked = pyqtSignal()
    columns_clicked = pyqtSignal(QPoint)
    search_clicked = pyqtSignal()
    updates_clicked = pyqtSignal()
    messages_clicked = pyqtSignal()
    queue_clicked = pyqtSignal()
    filters_clicked = pyqtSignal()
    preferences_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    LOADING = -1
    EMPTY = 0
    WITH_ACCOUNTS = 1
    NORMAL = 2

    def __init__(self, base):
        QStatusBar.__init__(self)
        self.base = base
        self.status = self.LOADING

        style = "background-color: %s; border: 0px solid %s;" % (self.base.bgcolor, self.base.bgcolor)

        self.updates_button = ImageButton(base, 'dock-updates.png',
                i18n.get('update_status'))
        self.messages_button = ImageButton(base, 'dock-messages.png',
                i18n.get('send_direct_message'))
        self.search_button = ImageButton(base, 'dock-search.png',
                i18n.get('search'))
        self.settings_button = ImageButton(base, 'dock-preferences.png',
                i18n.get('settings'))
        self.settings_button.setStyleSheet("QPushButton { %s opacity: 128; }; QToolButton:hover { %s opacity: 255;}" % (style, style))

        self.updates_button.clicked.connect(self.__updates_clicked)
        self.messages_button.clicked.connect(self.__messages_clicked)
        self.search_button.clicked.connect(self.__search_clicked)
        self.settings_button.clicked.connect(self.__settings_clicked)

        # TODO: Set tooltip for doc buttons

        separator = QWidget()
        separator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        toolbar = QToolBar()
        toolbar.addWidget(self.settings_button)
        toolbar.addWidget(separator)
        toolbar.addWidget(self.search_button)
        toolbar.addWidget(self.messages_button)
        toolbar.addWidget(self.updates_button)
        toolbar.setMinimumHeight(30)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setStyleSheet("QToolBar { %s }" % style)

        self.addPermanentWidget(toolbar, 1)
        self.setSizeGripEnabled(False)

        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("QStatusBar { %s }" % style)
        self.loading()

    def __accounts_clicked(self):
        self.accounts_clicked.emit()

    def __columns_clicked(self):
        self.columns_clicked.emit(QCursor.pos())

    def __search_clicked(self):
        self.search_clicked.emit()

    def __updates_clicked(self):
        self.updates_clicked.emit()

    def __messages_clicked(self):
        self.messages_clicked.emit()

    def __queue_clicked(self):
        self.queue_clicked.emit()

    def __filters_clicked(self):
        self.filters_clicked.emit()

    def __preferences_clicked(self):
        self.preferences_clicked.emit()

    def __about_clicked(self):
        self.base.show_about_dialog()

    def __quit_clicked(self):
        self.quit_clicked.emit()

    def __settings_clicked(self):
        self.settings_menu = QMenu(self)

        accounts = QAction(i18n.get('accounts'), self)
        accounts.triggered.connect(partial(self.__accounts_clicked))

        queue = QAction(i18n.get('messages_queue'), self)
        queue.triggered.connect(partial(self.__queue_clicked))

        columns = QAction(i18n.get('columns'), self)

        filters = QAction(i18n.get('filters'), self)
        filters.triggered.connect(partial(self.__filters_clicked))

        preferences = QAction(i18n.get('preferences'), self)
        preferences.triggered.connect(partial(self.__preferences_clicked))

        about_turpial = QAction(i18n.get('about_turpial'), self)
        about_turpial.triggered.connect(partial(self.__about_clicked))

        quit = QAction(i18n.get('quit'), self)
        quit.triggered.connect(self.__quit_clicked)

        if self.status > self.EMPTY:
            columns_menu = self.base.build_columns_menu()
            columns.setMenu(columns_menu)
        elif self.status == self.EMPTY:
            queue.setEnabled(False)
            columns.setEnabled(False)
        elif self.status == self.LOADING:
            accounts.setEnabled(False)
            queue.setEnabled(False)
            columns.setEnabled(False)
            filters.setEnabled(False)
            preferences.setEnabled(False)

        self.settings_menu.addAction(accounts)
        self.settings_menu.addAction(columns)
        self.settings_menu.addAction(filters)
        self.settings_menu.addAction(queue)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(preferences)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(about_turpial)
        self.settings_menu.addAction(quit)
        self.settings_menu.exec_(QCursor.pos())

    def loading(self):
        self.updates_button.setEnabled(False)
        self.messages_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.status = self.LOADING

    def empty(self, with_accounts=None):
        self.updates_button.setEnabled(False)
        self.messages_button.setEnabled(False)
        self.search_button.setEnabled(False)
        if with_accounts:
            self.status = self.WITH_ACCOUNTS
        else:
            self.status = self.EMPTY


    def normal(self):
        self.updates_button.setEnabled(True)
        self.messages_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.status = self.NORMAL

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-

# Qt filters dialog for Turpial

from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QListWidget
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QVBoxLayout

from PyQt4.QtCore import Qt

from turpial.ui.lang import i18n

from turpial.ui.qt.widgets import Window


class FiltersDialog(Window):
    def __init__(self, base):
        Window.__init__(self, base, i18n.get('filters'))
        self.setFixedSize(280, 360)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        self.expression = QLineEdit()
        self.expression.returnPressed.connect(self.__new_filter)

        self.new_button = QPushButton(i18n.get('add_filter'))
        self.new_button.setToolTip(i18n.get('create_a_new_filter'))
        self.new_button.clicked.connect(self.__new_filter)

        expression_box = QHBoxLayout()
        expression_box.addWidget(self.expression)
        expression_box.addWidget(self.new_button)

        self.list_ = QListWidget()
        self.list_.clicked.connect(self.__filter_clicked)

        self.delete_button = QPushButton(i18n.get('delete'))
        self.delete_button.setEnabled(False)
        self.delete_button.setToolTip(i18n.get('delete_selected_filter'))
        self.delete_button.clicked.connect(self.__delete_filter)

        self.clear_button = QPushButton(i18n.get('delete_all'))
        self.clear_button.setEnabled(False)
        self.clear_button.setToolTip(i18n.get('delete_all_filters'))
        self.clear_button.clicked.connect(self.__delete_all)

        button_box = QHBoxLayout()
        button_box.addStretch(1)
        button_box.addWidget(self.clear_button)
        button_box.addWidget(self.delete_button)

        layout = QVBoxLayout()
        layout.addLayout(expression_box)
        layout.addWidget(self.list_, 1)
        layout.addLayout(button_box)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        self.__update()
        self.show()

    def __update(self):
        row = 0
        self.expression.setText('')
        self.list_.clear()
        for expression in self.base.core.list_filters():
            self.list_.addItem(expression)
            row += 1

        self.__enable(True)
        self.delete_button.setEnabled(False)
        if row == 0:
            self.clear_button.setEnabled(False)
        self.expression.setFocus()

    def __filter_clicked(self, point):
        self.delete_button.setEnabled(True)
        self.clear_button.setEnabled(True)

    def __new_filter(self):
        expression = str(self.expression.text())
        self.list_.addItem(expression)
        self.__save_filters()

    def __delete_filter(self):
        self.list_.takeItem(self.list_.currentRow())
        self.__save_filters()

    def __delete_all(self):
        self.__enable(False)
        message = i18n.get('clear_filters_confirm')
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            message)
        if not confirmation:
            self.__enable(True)
            return
        self.list_.clear()
        self.__save_filters()
        self.raise_()

    def __enable(self, value):
        self.list_.setEnabled(value)
        self.delete_button.setEnabled(value)
        self.clear_button.setEnabled(value)

    def __save_filters(self):
        filters = []
        for i in range(self.list_.count()):
            filters.append(str(self.list_.item(i).text()))
        self.base.save_filters(filters)
        self.__update()

########NEW FILE########
__FILENAME__ = imageview
# -*- coding: utf-8 -*-

# Qt image view for Turpial

import os
import shutil

from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMovie
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QPalette
from PyQt4.QtGui import QSizePolicy
from PyQt4.QtGui import QScrollArea
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QApplication

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QSize

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import Window, BarLoadIndicator

GOOGLE_SEARCH_URL = 'https://www.google.com/searchbyimage?&image_url='

try:
    import exifread
    EXIF_SUPPORT = True
except:
    EXIF_SUPPORT = False

class ImageView(Window):
    EMPTY = 0
    LOADING = 1
    LOADED = 2
    def __init__(self, base):
        Window.__init__(self, base, i18n.get('image_preview'))

        self.loader = BarLoadIndicator()
        self.source_url = None
        self.original_url = None
        self.local_file = None
        self.pixmap = None
        self.status = self.EMPTY

        self.view = QLabel()

        self.error_label = QLabel(i18n.get('error_loading_image'))
        self.error_label.setAlignment(Qt.AlignHCenter)
        self.error_label.setStyleSheet("QLabel {background-color: #ffecec;}")

        self.exif_data = QLabel()
        self.exif_data.setVisible(False)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.loader)
        layout.addWidget(self.error_label)
        layout.addWidget(self.view)
        layout.addWidget(self.exif_data)

        self.setLayout(layout)
        self.__clear()

    def __clear(self):
        self.setFixedSize(350, 350)
        self.view.setMovie(None)
        self.view.setPixmap(QPixmap())
        self.menu = None
        self.source_url = None
        self.original_url = None
        self.local_file = None
        self.pixmap = None
        self.exif_data.setVisible(False)
        self.status = self.EMPTY

    def __load(self, url):
        self.local_file = url
        self.loader.setVisible(False)
        self.pixmap = self.base.load_image(url, True)
        screen_size = self.base.get_screen_size()

        if (screen_size.width() - 10 < self.pixmap.width() or screen_size.height() - 10 < self.pixmap.height()):
            width = min(self.pixmap.width(), screen_size.width())
            height = min(self.pixmap.height(), screen_size.height())
            self.pixmap = self.pixmap.scaled(QSize(screen_size.width(), screen_size.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setFixedSize(self.pixmap.width(), self.pixmap.height())

        if EXIF_SUPPORT:
            fd = open(url, 'rb')
            tags = exifread.process_file(fd)
            if tags != {}:
                data = {
                    'Camera': "%s %s" % (tags['Image Make'], tags['Image Model']),
                    'Software': '' if 'Image Software' not in tags else tags['Image Software'],
                    'Original Datetime': '' if 'EXIF DateTimeOriginal' not in tags else tags['EXIF DateTimeOriginal'],
                    'Dimensions': "%s x %s" % (tags['EXIF ExifImageWidth'], tags['EXIF ExifImageLength']),
                    'Copyright': '' if 'Image Copyright' not in tags else tags['Image Copyright'],
                    'Comment': '' if 'EXIF UserComment' not in tags else tags['EXIF UserComment']
                }
                exif_data = ''
                for key in ['Camera', 'Software', 'Original Datetime', 'Dimensions', 'Copyright', 'Comment']:
                    if exif_data != '':
                        exif_data += ' – '
                    exif_data += "%s: %s" % (key, data[key])
            else:
                exif_data = i18n.get('exif_data_not_available')
            self.exif_data.setText(exif_data)

        if url.find('.gif') > 0:
            movie = QMovie(url)
            self.view.setMovie(movie)
            movie.start()
        else:
            self.view.setPixmap(self.pixmap)
        self.view.adjustSize()
        self.status = self.LOADED
        self.show()

    def __copy_to_clipboard(self, url):
        clip = QApplication.clipboard()
        clip.setText(url)

    def __show_exif_data(self):
        self.exif_data.setVisible(True)

    def __save_image(self):
        local_extension = os.path.splitext(self.local_file)[1]
        dialog = QFileDialog(self)
        dialog.setDefaultSuffix(local_extension[1:])
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setNameFilter("Images (*.png *.gif *.jpg *.jpeg)")
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.selectFile("Untitled%s" % os.path.splitext(self.local_file)[1])
        if (dialog.exec_() == QDialog.Accepted):
            filenames = dialog.selectedFiles()
            if len(filenames) > 0:
                filename = str(filenames[0])

                try:
                    shutil.copy(self.local_file, filename)
                except Exception, exc:
                    print exc
                    self.error_label.setText(i18n.get('error_saving_image'))
                    self.error_label.setVisible(True)

    def __popup_menu(self, point):
        self.menu = QMenu(self)

        if self.status == self.LOADED:
            save = QAction(i18n.get('save'), self)
            open_ = QAction(i18n.get('open_in_browser'), self)
            copy = QAction(i18n.get('copy_image_url'), self)
            verify_image = QAction(i18n.get('verify_image'), self)
            view_info = QAction(i18n.get('view_exif_info'), self)

            if self.source_url:
                open_.triggered.connect(lambda x: self.base.open_in_browser(self.original_url))
                copy.triggered.connect(lambda x: self.__copy_to_clipboard(self.source_url))
                verify_url = ''.join([GOOGLE_SEARCH_URL, self.source_url])
                verify_image.triggered.connect(lambda x: self.base.open_in_browser(verify_url))
            else:
                open_.setEnabled(False)
                copy.setEnabled(False)
                verify_image.setEnabled(False)

            if EXIF_SUPPORT:
                view_info.triggered.connect(lambda x: self.__show_exif_data())
            else:
                view_info.setEnabled(False)

            save.triggered.connect(lambda x: self.__save_image())
            view_info.triggered.connect(lambda x: self.__show_exif_data())

            self.menu.addAction(save)
            self.menu.addAction(open_)
            self.menu.addAction(copy)
            self.menu.addAction(verify_image)
            self.menu.addAction(view_info)
        else:
            loading = QAction(i18n.get('loading'), self)
            loading.setEnabled(False)
            self.menu.addAction(loading)

        self.menu.exec_(QCursor.pos())

    def closeEvent(self, event):
        event.ignore()
        self.__clear()
        self.hide()

    def start_loading(self, image_url=None):
        self.status = self.LOADING
        self.loader.setVisible(True)
        self.error_label.setVisible(False)
        self.show()

    def load_from_url(self, url):
        self.__load(url)

    def load_from_object(self, media):
        if media.info:
            self.source_url = media.info['source_url']
            self.original_url = media.info['original_url']
        self.__load(media.path)

    def error(self):
        self.loader.setVisible(False)
        self.error_label.setVisible(True)


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

# Qt main view for Turpial

import os
import sys
import random
import urllib2
import webbrowser
import subprocess


from functools import partial

from PyQt4.QtGui import (
    QMenu, QImage, QWidget, QAction, QPixmap, QDialog, QMessageBox,
    QVBoxLayout, QApplication, QFontDatabase, QIcon, QDesktopWidget,
)

from PyQt4.QtCore import QTimer, pyqtSignal, QRect, Qt

from turpial.ui.base import * #NOQA
from turpial.ui.sound import SoundSystem
from turpial.ui.notification import NotificationSystem

from turpial.ui.qt.dock import Dock
from turpial.ui.qt.tray import TrayIcon
from turpial.ui.qt.worker import CoreWorker
from turpial.ui.qt.queue import QueueDialog
from turpial.ui.qt.about import AboutDialog
from turpial.ui.qt.search import SearchDialog
from turpial.ui.qt.shortcuts import Shortcuts
from turpial.ui.qt.updatebox import UpdateBox
from turpial.ui.qt.container import Container
from turpial.ui.qt.imageview import ImageView
from turpial.ui.qt.filters import FiltersDialog
from turpial.ui.qt.profile import ProfileDialog
from turpial.ui.qt.accounts import AccountsDialog
from turpial.ui.qt.preferences import PreferencesDialog
from turpial.ui.qt.selectfriend import SelectFriendDialog

from libturpial.common import ColumnType, get_preview_service_from_url, escape_list_name, OS_MAC
from libturpial.common.tools import detect_os


class Main(Base, QWidget):

    account_deleted = pyqtSignal()
    account_loaded = pyqtSignal()
    account_registered = pyqtSignal()

    def __init__(self, debug=False):
        self.app = QApplication(['Turpial'] + sys.argv)

        Base.__init__(self)
        QWidget.__init__(self)

        self.debug = debug

        for font_path in self.fonts:
            QFontDatabase.addApplicationFont(font_path)

        #database = QFontDatabase()
        #for f in database.families():
        #    print f

        self.templates_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), 'templates'))

        self.setWindowTitle('Turpial')
        self.app.setApplicationName('Turpial')
        self.setWindowIcon(QIcon(self.get_image_path('turpial.svg')))
        self.resize(320, 480)
        self.center_on_screen()

        self.ignore_quit = True
        self.showed = True
        self.core_ready = False
        self.timers = {}
        self.extra_friends = []

        self.update_box = UpdateBox(self)
        self.profile_dialog = ProfileDialog(self)
        self.profile_dialog.options_clicked.connect(self.show_profile_menu)
        self.image_view = ImageView(self)
        self.queue_dialog = QueueDialog(self)
        self.shortcuts = Shortcuts(self)

        self.core = CoreWorker()
        self.core.ready.connect(self.after_core_initialized)
        self.core.status_updated.connect(self.after_update_status)
        self.core.status_broadcasted.connect(self.after_broadcast_status)
        self.core.status_repeated.connect(self.after_repeat_status)
        self.core.status_deleted.connect(self.after_delete_status)
        self.core.message_deleted.connect(self.after_delete_message)
        self.core.message_sent.connect(self.after_send_message)
        self.core.column_updated.connect(self.after_update_column)
        self.core.account_saved.connect(self.after_save_account)
        self.core.account_loaded.connect(self.after_load_account)
        self.core.account_deleted.connect(self.after_delete_account)
        self.core.column_saved.connect(self.after_save_column)
        self.core.column_deleted.connect(self.after_delete_column)
        self.core.status_marked_as_favorite.connect(self.after_marking_status_as_favorite)
        self.core.status_unmarked_as_favorite.connect(self.after_unmarking_status_as_favorite)
        self.core.fetched_user_profile.connect(self.after_get_user_profile)
        self.core.urls_shorted.connect(self.update_box.after_short_url)
        self.core.media_uploaded.connect(self.update_box.after_upload_media)
        self.core.friends_list_updated.connect(self.update_box.update_friends_list)
        self.core.user_muted.connect(self.after_mute_user)
        self.core.user_unmuted.connect(self.after_unmute_user)
        self.core.user_blocked.connect(self.after_block_user)
        self.core.user_reported_as_spam.connect(self.after_report_user_as_spam)
        self.core.user_followed.connect(self.after_follow_user)
        self.core.user_unfollowed.connect(self.after_unfollow_user)
        self.core.status_from_conversation.connect(self.after_get_status_from_conversation)
        self.core.fetched_profile_image.connect(self.after_get_profile_image)
        self.core.fetched_avatar.connect(self.update_profile_avatar)
        self.core.fetched_image_preview.connect(self.after_get_image_preview)
        self.core.status_pushed_to_queue.connect(self.after_push_status_to_queue)
        self.core.status_poped_from_queue.connect(self.after_pop_status_from_queue)
        self.core.status_posted_from_queue.connect(self.after_post_status_from_queue)
        self.core.status_deleted_from_queue.connect(self.after_delete_status_from_queue)
        self.core.queue_cleared.connect(self.after_clear_queue)
        self.core.exception_raised.connect(self.on_exception)

        self.core.start()

        self._container = Container(self)

        self.os_notifications = NotificationSystem.create(self.images_path)
        self.sounds = SoundSystem(self.sounds_path)

        self.dock = Dock(self)

        self.dock.accounts_clicked.connect(self.show_accounts_dialog)
        self.dock.columns_clicked.connect(self.show_column_menu)
        self.dock.search_clicked.connect(self.show_search_dialog)
        self.dock.updates_clicked.connect(self.show_update_box)
        self.dock.messages_clicked.connect(self.show_friends_dialog_for_direct_message)
        self.dock.queue_clicked.connect(self.show_queue_dialog)
        self.dock.filters_clicked.connect(self.show_filters_dialog)
        self.dock.preferences_clicked.connect(self.show_preferences_dialog)
        self.dock.quit_clicked.connect(self.main_quit)

        self.tray = TrayIcon(self)
        self.tray.updates_clicked.connect(self.show_update_box)
        self.tray.messages_clicked.connect(self.show_friends_dialog_for_direct_message)
        self.tray.settings_clicked.connect(self.show_preferences_dialog)
        self.tray.quit_clicked.connect(self.main_quit)
        self.tray.toggled.connect(self.toggle_tray_icon)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._container, 1)
        layout.addWidget(self.dock)

        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)
        self.add_keyboard_shortcuts()

    def open_in_browser(self, url):
        browser = self.core.get_default_browser()

        if browser != '':
            cmd = browser.split(' ')
            cmd.append(url)
            subprocess.Popen(cmd)
        else:
            webbrowser.open(url)

    def toggle_tray_icon(self):
        if self.showed:
            if self.isActiveWindow():
                self.showed = False
                self.hide()
            else:
                self.raise_()
        else:
            self.showed = True
            self.show()
            self.raise_()

    def add_keyboard_shortcuts(self):
        for key, shortcut in self.shortcuts:
            if detect_os() != OS_MAC and key == 'preferences':
                continue
            self.addAction(shortcut.action)

        self.shortcuts.get('accounts').activated.connect(self.show_accounts_dialog)
        self.shortcuts.get('filters').activated.connect(self.show_filters_dialog)
        self.shortcuts.get('tweet').activated.connect(self.show_update_box)
        self.shortcuts.get('message').activated.connect(self.show_friends_dialog_for_direct_message)
        self.shortcuts.get('search').activated.connect(self.show_search_dialog)
        self.shortcuts.get('queue').activated.connect(self.show_queue_dialog)
        self.shortcuts.get('quit').activated.connect(self.closeEvent)

        if detect_os() == OS_MAC:
            self.shortcuts.get('preferences').activated.connect(self.show_preferences_dialog)

    def add_extra_friends_from_statuses(self, statuses):
        current_friends_list = self.load_friends_list()
        for status in statuses:
            for user in status.get_mentions():
                if user not in current_friends_list and user not in self.extra_friends:
                    self.extra_friends.append(user)

    def is_exception(self, response):
        return isinstance(response, Exception)

    def random_id(self):
        return str(random.getrandbits(128))

    def center_on_screen(self):
        current_position = self.frameGeometry()
        current_position.moveCenter(self.app.desktop().availableGeometry().center())
        self.move(current_position.topLeft())

    def get_screen_size(self):
        return self.app.desktop().availableGeometry()

    def resizeEvent(self, event):
        if self.core.status > self.core.LOADING:
            self.core.set_window_size(event.size().width(), event.size().height())

    def closeEvent(self, event=None):
        if event:
            event.ignore()

        if self.core.status > self.core.LOADING:
            if self.core.get_minimize_on_close():
                self.hide()
                self.showed = False
            else:
                self.main_quit()
        else:
            confirmation = self.show_confirmation_message(i18n.get('confirm_close'),
                i18n.get('do_you_want_to_close_turpial'))
            if confirmation:
                self.main_quit()

    #================================================================
    # Overrided methods
    #================================================================

    def start(self):
        pass

    def restart(self):
        self.core.restart()
        self._container.loading()

    def main_loop(self):
        try:
            self.app.exec_()
        except Exception:
            sys.exit(0)

    def main_quit(self, widget=None, force=False):
        self.app.quit()
        sys.exit(0)

    def show_main(self):
        self.start()
        self.show()

    #================================================================
    # Main methods
    #================================================================

    def show_error_message(self, title, message, error):
        full_message = "%s (%s)" % (message, error)
        message = QMessageBox.critical(self, title, full_message, QMessageBox.Ok)

    def show_information_message(self, title, message):
        message = QMessageBox.information(self, title, message, QMessageBox.Ok)

    def show_confirmation_message(self, title, message):
        confirmation = QMessageBox.question(self, title, message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirmation == QMessageBox.No:
            return False
        return True

    def show_about_dialog(self):
        AboutDialog(self)

    def show_accounts_dialog(self):
        accounts = AccountsDialog(self)

    def show_queue_dialog(self):
        self.queue_dialog.show()

    def show_profile_dialog(self, account_id, username):
        self.profile_dialog.start_loading(username)
        self.core.get_user_profile(account_id, username)

    def show_preferences_dialog(self):
        self.preferences_dialog = PreferencesDialog(self)

    def show_search_dialog(self):
        search = SearchDialog(self)
        if search.result() == QDialog.Accepted:
            account_id = str(search.get_account().toPyObject())
            criteria = str(search.get_criteria())
            self.add_search_column(account_id, criteria)

    def show_filters_dialog(self):
        self.filters_dialog = FiltersDialog(self)

    def show_profile_image(self, account_id, username):
        self.image_view.start_loading()
        self.core.get_profile_image(account_id, username)

    def show_update_box(self):
        self.update_box.show()

    def show_update_box_for_reply(self, account_id, status):
        self.update_box.show_for_reply(account_id, status)

    def show_update_box_for_quote(self, account_id, status):
        self.update_box.show_for_quote(account_id, status)

    def show_update_box_for_send_direct(self, account_id, username):
        self.update_box.show_for_send_direct(account_id, username)

    def show_update_box_for_reply_direct(self, account_id, status):
        self.update_box.show_for_reply_direct(account_id, status)

    def show_column_menu(self, point):
        self.columns_menu = self.build_columns_menu()
        self.columns_menu.exec_(point)

    def show_profile_menu(self, point, profile):
        self.profile_menu = QMenu(self)


        if profile.following:
            message_menu = QAction(i18n.get('send_direct_message'), self)
            message_menu.triggered.connect(partial(
                self.show_update_box_for_send_direct, profile.account_id, profile.username))
            self.profile_menu.addAction(message_menu)

        if self.core.is_muted(profile.username):
            mute_menu = QAction(i18n.get('unmute'), self)
            mute_menu.triggered.connect(partial(self.unmute, profile.username))
        else:
            mute_menu = QAction(i18n.get('mute'), self)
            mute_menu.triggered.connect(partial(self.mute, profile.username))

        block_menu = QAction(i18n.get('block'), self)
        block_menu.triggered.connect(partial(self.block, profile.account_id, profile.username))
        spam_menu = QAction(i18n.get('report_as_spam'), self)
        spam_menu.triggered.connect(partial(self.report_as_spam, profile.account_id,
            profile.username))

        # FIXME: Use the profile_url variable in libturpial's twitter.py
        # Put this value on every profile object
        user_profile_url = "http://twitter.com/%s" % (profile.username)
        open_in_browser_menu = QAction(i18n.get('open_in_browser'), self)
        open_in_browser_menu.triggered.connect(lambda x: self.open_in_browser(user_profile_url))

        self.profile_menu.addAction(open_in_browser_menu)
        self.profile_menu.addAction(mute_menu)
        self.profile_menu.addAction(block_menu)
        self.profile_menu.addAction(spam_menu)

        self.profile_menu.exec_(point)

    def show_friends_dialog_for_direct_message(self):
        friend = SelectFriendDialog(self)
        if friend.is_accepted():
            self.show_update_box_for_send_direct(friend.get_account(), friend.get_username())

    def save_account(self, account):
        self.core.save_account(account)

    def load_account(self, account_id):
        self.core.load_account(account_id)

    def delete_account(self, account_id):
        self.core.delete_account(account_id)

    def add_column(self, column_id):
        self.core.save_column(column_id)

    def add_search_column(self, account_id, criteria):
        column_id = "%s-%s>%s" % (account_id, ColumnType.SEARCH, urllib2.quote(criteria))
        self.add_column(column_id)

    def get_column_from_id(self, column_id):
        columns = self.core.get_registered_columns()
        for column in columns:
            if column_id == column.id_:
                return column
        return None

    def get_shorten_url_service(self):
        return self.core.get_shorten_url_service()

    def get_upload_media_service(self):
        return self.core.get_upload_media_service()

    def load_friends_list(self):
        return self.core.load_friends_list()

    def load_friends_list_with_extras(self):
        return self.extra_friends + self.core.load_friends_list()

    def open_url(self, url):
        preview_service = get_preview_service_from_url(url)
        if preview_service and not self.core.get_show_images_in_browser():
            self.core.get_image_preview(preview_service, url)
            self.image_view.start_loading(image_url=url)
        else:
            self.open_in_browser(url)

    def load_image(self, filename, pixbuf=False):
        img_path = os.path.join(self.images_path, filename)
        if pixbuf:
            return QPixmap(img_path)
        return QImage(img_path)

    def get_image_path(self, filename):
        return os.path.join(self.images_path, filename)

    def update_dock(self):
        accounts = self.core.get_registered_accounts()
        columns = self.core.get_registered_columns()

        if len(columns) == 0:
            if len(accounts) == 0:
                self.dock.empty(False)
            else:
                self.dock.normal()
        else:
            self.dock.normal()

    def update_container(self):
        accounts = self.core.get_registered_accounts()
        columns = self.core.get_registered_columns()

        if len(columns) == 0:
            if len(accounts) == 0:
                self._container.empty(False)
                self.dock.empty(False)
            else:
                self._container.empty(True)
                self.dock.normal()
            self.tray.empty()
        else:
            self._container.normal()
            self.dock.normal()
            self.tray.normal()
            for column in columns:
                self.download_stream(column)
                self.add_timer(column)
            self.fetch_friends_list()

    def build_columns_menu(self):
        columns_menu = QMenu(self)

        available_columns = self.core.get_available_columns()
        accounts = self.core.get_all_accounts()

        if len(accounts) == 0:
            empty_menu = QAction(i18n.get('no_registered_accounts'), self)
            empty_menu.setEnabled(False)
            columns_menu.addAction(empty_menu)
        else:
            for account in accounts:
                name = "%s (%s)" % (account.username, i18n.get(account.protocol_id))
                account_menu = QAction(name, self)

                if len(available_columns[account.id_]) > 0:
                    available_columns_menu = QMenu(self)
                    for column in available_columns[account.id_]:
                        item = QAction(column.slug, self)
                        if column.__class__.__name__ == 'List':
                            slug = escape_list_name(column.slug)
                            column_id = "-".join([account.id_, slug])
                            item.triggered.connect(partial(self.add_column, column_id))
                        else:
                            item.triggered.connect(partial(self.add_column, column.id_))
                        available_columns_menu.addAction(item)

                    account_menu.setMenu(available_columns_menu)
                else:
                    account_menu.setEnabled(False)
                columns_menu.addAction(account_menu)

        return columns_menu

    def update_status(self, account_id, message, in_reply_to_id=None):
        self.core.update_status(account_id, message, in_reply_to_id)

    def update_status_with_media(self, account_id, message, in_reply_to_id=None, media=None):
        self.core.update_status_with_media(account_id, message, in_reply_to_id, media)

    def broadcast_status(self, message):
        accounts = []
        for account in self.core.get_registered_accounts():
            accounts.append(account.id_)
        self.core.broadcast_status(accounts, message)

    def repeat_status(self, column_id, account_id, status):
        self.core.repeat_status(column_id, account_id, status.id_)

    def delete_status(self, column_id, account_id, status):
        self.core.delete_status(column_id, account_id, status.id_)

    def delete_direct_message(self, column_id, account_id, status):
        self.core.delete_direct_message(column_id, account_id, status.id_)

    def send_direct_message(self, account_id, username, message):
        self.core.send_direct_message(account_id, username, message)

    def mark_status_as_favorite(self, column_id, account_id, status):
        self.core.mark_status_as_favorite(column_id, account_id, status.id_)

    def unmark_status_as_favorite(self, column_id, account_id, status):
        self.core.unmark_status_as_favorite(column_id, account_id, status.id_)

    def short_urls(self, message):
        self.core.short_urls(message)

    def upload_media(self, account_id, filename):
        self.core.upload_media(account_id, filename)

    def fetch_friends_list(self):
        self.core.get_friends_list()

    def mute(self, username):
        self.core.mute(username)

    def unmute(self, username):
        self.core.unmute(username)

    def block(self, account_id, username):
        self.core.block(account_id, username)

    def report_as_spam(self, account_id, username):
        self.core.report_as_spam(account_id, username)

    def follow(self, account_id, username):
        self.core.follow(account_id, username)

    def unfollow(self, account_id, username):
        self.core.unfollow(account_id, username)

    def get_conversation(self, account_id, status, column_id, status_root_id):
        self.core.get_status_from_conversation(account_id, status.in_reply_to_id, column_id,
            status_root_id)

    def push_status_to_queue(self, account_id, message):
        self.core.push_status_to_queue(account_id, message)

    def update_status_from_queue(self, args=None):
        self.core.pop_status_from_queue()

    def delete_message_from_queue(self, index):
        self.core.delete_status_from_queue(index)

    def clear_queue(self):
        self.core.clear_statuses_queue()

    def get_config(self):
        return self.core.read_config()

    def get_cache_size(self):
        return self.humanize_size(self.core.get_cache_size())

    def clean_cache(self):
        self.core.delete_cache()

    def save_filters(self, filters):
        self.core.save_filters(filters)

    def update_config(self, new_config):
        current_config = self.core.read_config()
        current_queue_interval = int(current_config['General']['queue-interval'])

        self.core.update_config(new_config)

        if current_queue_interval != new_config['General']['queue-interval']:
            self.turn_on_queue_timer(force=True)

    def restore_config(self):
        self.core.restore_config()

    def set_column_update_interval(self, column_id, interval):
        self.core.set_update_interval_per_column(column_id, interval)

    def get_column_update_interval(self, column_id):
        return self.core.get_update_interval_per_column(column_id)

    def set_column_notification(self, column_id, value):
        self.core.set_show_notifications_in_column(column_id, value)

    def get_column_notification(self, column_id):
        return self.core.get_show_notifications_in_column(column_id)

    #================================================================
    # Hooks definitions
    #================================================================

    def after_core_initialized(self, response):
        if self.is_exception(response):
            self.core.status = self.core.ERROR
            self._container.error()
        else:
            self.core.add_config_option('General', 'minimize-on-close', 'off')
            self.core.add_config_option('General', 'inline-preview', 'off')
            self.core.add_config_option('General', 'show-images-in-browser', 'off')
            self.core.add_config_option('General', 'queue-interval', 30)
            self.core.add_config_option('Window', 'size', '320,480')
            self.core.add_config_option('Notifications', 'actions', 'on')
            self.core.add_config_option('Notifications', 'updates', 'on')
            self.core.add_config_option('Sounds', 'updates', 'on')
            self.core.add_config_option('Sounds', 'login', 'on')
            self.core.add_config_option('Browser', 'cmd', '')
            self.core.add_config_option('Advanced', 'show-user-avatars', 'on')

            # This is for backwards compatibility
            columns = self.core.sanitize_search_columns()
            notifications = self.core.read_section('Notifications')
            updates = self.core.read_section('Updates')

            if updates is None:
                updates = {}

            for key in columns:
                if key not in notifications.keys():
                    notifications[key] = 'on' if self.core.get_notify_on_updates() else 'off'
                if key not in updates.keys():
                    updates[key] = self.core.get_update_interval()

            self.core.write_section('Notifications', notifications)
            self.core.write_section('Updates', updates)

            # Remove deprecated config values
            self.core.remove_config_option('Notifications', 'on-updates')
            self.core.remove_config_option('Notifications', 'on-actions')
            self.core.remove_config_option('Sounds', 'on-updates')
            self.core.remove_config_option('Sounds', 'on-actions')
            self.core.remove_config_option('Sounds', 'on-login')

            width, height = self.core.get_window_size()
            self.resize(width, height)
            self.center_on_screen()
            if self.core.get_sound_on_login():
                self.sounds.startup()
            self.queue_dialog.start()
            self.update_container()
            self.turn_on_queue_timer()
            self.core.status = self.core.READY

    def after_save_account(self, account_id):
        self.account_registered.emit()
        if len(self.core.get_registered_accounts()) == 1:
            self.update_container()
        self.update_dock()
        timeline = "%s-timeline" % account_id
        self.add_column(timeline)

    def after_load_account(self):
        self.account_loaded.emit()

    def after_delete_account(self):
        self.account_deleted.emit()

    def after_delete_column(self, column_id):
        column_id = str(column_id)
        self._container.remove_column(column_id)
        self.remove_timer(column_id)

        columns = self.core.get_registered_columns()
        if len(columns) == 0:
            self.update_container()

    def after_save_column(self, column_id):
        column_id = str(column_id)
        self._container.add_column(column_id)
        column = self.get_column_from_id(column_id)
        self.download_stream(column)
        self.add_timer(column)

    def after_update_column(self, response, data):
        column, max_ = data

        if self.is_exception(response):
            self._container.error_updating_column(column.id_, response)
        else:
            count = len(response)
            if count > 0:
                updates = self.core.filter_statuses(response)
                filtered = count - len(updates)
                if self.core.get_show_notifications_in_column(column.id_):
                    self.os_notifications.updates(column, len(updates), filtered)

                if self.core.get_sound_on_updates():
                    self.sounds.updates()
                self._container.update_column(column.id_, updates)
            else:
                self._container.update_timestamps(column.id_)


    def after_update_status(self, response, account_id):
        if self.is_exception(response):
            self.update_box.error(i18n.get('error_posting_status'), response)
        else:
            self.update_box.done()

    def after_broadcast_status(self, response):
        if self.is_exception(response):
            self.update_box.error(i18n.get('error_posting_status'), response)
        else:
            self.update_box.done()

    def after_repeat_status(self, response, column_id, account_id, status_id):
        column_id = str(column_id)
        if self.is_exception(response):
            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.error_repeating_status(status_id, response)
            else:
                self._container.error_repeating_status(column_id, status_id, response)
        else:
            message = i18n.get('status_repeated')
            self._container.mark_status_as_repeated(response.id_)

            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.last_statuses.mark_status_as_repeated(response.id_)
                self.profile_dialog.last_statuses.release_status(response.id_)
                self.profile_dialog.last_statuses.notify_success(response.id_, message)
            else:
                self._container.notify_success(column_id, response.id_, message)

    def after_delete_status(self, response, column_id, account_id, status_id):
        if self.is_exception(response):
            self._container.error_deleting_status(column_id, status_id, response)
        else:
            self._container.remove_status(response.id_)
            self._container.notify_success(column_id, response.id_, i18n.get('status_deleted'))

    def after_delete_message(self, response, column_id, account_id, status_id):
        if self.is_exception(response):
            self._container.error_deleting_status(column_id, status_id, response)
        else:
            self._container.remove_status(response.id_)
            self._container.notify_success(column_id, response.id_, i18n.get('direct_message_deleted'))

    def after_send_message(self, response, account_id):
        if self.is_exception(response):
            self.update_box.error(i18n.get('can_not_send_direct_message'))
        else:
            self.update_box.done()

    def after_marking_status_as_favorite(self, response, column_id, account_id, status_id):
        column_id = str(column_id)
        if self.is_exception(response):
            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.error_marking_status_as_favorite(status_id, response)
            else:
                self._container.error_marking_status_as_favorite(column_id, status_id, response)
        else:
            message = i18n.get('status_marked_as_favorite')
            self._container.mark_status_as_favorite(response.id_)

            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.last_statuses.mark_status_as_favorite(response.id_)
                self.profile_dialog.last_statuses.release_status(response.id_)
                self.profile_dialog.last_statuses.notify_success(response.id_, message)
            else:
                self._container.notify_success(column_id, response.id_, message)

    def after_unmarking_status_as_favorite(self, response, column_id, account_id, status_id):
        column_id = str(column_id)
        if self.is_exception(response):
            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.error_unmarking_status_as_favorite(status_id, response)
            else:
                self._container.error_unmarking_status_as_favorite(column_id, status_id, response)
        else:
            message = i18n.get('status_removed_from_favorites')
            self._container.unmark_status_as_favorite(response.id_)

            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.last_statuses.unmark_status_as_favorite(response.id_)
                self.profile_dialog.last_statuses.release_status(response.id_)
                self.profile_dialog.last_statuses.notify_success(response.id_, message)
            else:
                self._container.notify_success(column_id, response.id_, message)

    def after_get_user_profile(self, response, account_id):
        if self.is_exception(response):
            self.profile_dialog.error(i18n.get('problems_loading_user_profile'))
        else:
            self.profile_dialog.loading_finished(response, account_id)
            self.core.get_avatar_from_status(response)

    def after_mute_user(self, username):
        if self.core.get_notify_on_actions():
            self.os_notifications.user_muted(username)

    def after_unmute_user(self, username):
        if self.core.get_notify_on_actions():
            self.os_notifications.user_unmuted(username)

    def after_block_user(self, profile):
        if self.is_exception(profile):
            self.profile_dialog.error(i18n.get('could_not_block_user'))
        else:
            if self.core.get_notify_on_actions():
                self.os_notifications.user_blocked(profile.username)

    def after_report_user_as_spam(self, profile):
        if self.is_exception(profile):
            self.profile_dialog.error(i18n.get('having_issues_reporting_user_as_spam'))
        else:
            if self.core.get_notify_on_actions():
                self.os_notifications.user_reported_as_spam(profile.username)

    def after_follow_user(self, profile):
        if self.is_exception(profile):
            self.profile_dialog.error(i18n.get('having_trouble_to_follow_user'))
        else:
            self.profile_dialog.update_following(profile.username, True)
            if self.core.get_notify_on_actions():
                self.os_notifications.user_followed(profile.username)

    def after_unfollow_user(self, profile):
        if self.is_exception(profile):
            self.profile_dialog.error(i18n.get('having_trouble_to_unfollow_user'))
        else:
            self.profile_dialog.update_following(profile.username, False)
            if self.core.get_notify_on_actions():
                self.os_notifications.user_unfollowed(profile.username)

    def after_get_status_from_conversation(self, response, column_id, status_root_id):
        column_id = str(column_id)
        if self.is_exception(response):
            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.error_loading_conversation(status_root_id, response)
            else:
                self._container.error_loading_conversation(column_id, status_root_id, response)
        else:
            if self.profile_dialog.is_for_profile(column_id):
                self.profile_dialog.last_statuses.update_conversation(response, status_root_id)
            else:
                self._container.update_conversation(response, column_id, status_root_id)

            if response.in_reply_to_id:
                self.core.get_status_from_conversation(response.account_id, response.in_reply_to_id,
                    column_id, status_root_id)

    def after_get_profile_image(self, image_path):
        self.image_view.load_from_url(str(image_path))

    def update_profile_avatar(self, image_path, username):
        if not self.is_exception(image_path):
            self.profile_dialog.update_avatar(str(image_path), str(username))

    def after_get_image_preview(self, response):
        if self.is_exception(response):
            self.image_view.error()
        else:
            self.image_view.load_from_object(response)

    def after_push_status_to_queue(self, account_id):
        self.update_box.done()
        self.turn_on_queue_timer()
        if self.core.get_notify_on_actions():
            self.os_notifications.message_queued_successfully()

    def after_pop_status_from_queue(self, status):
        if status:
            self.core.post_status_from_queue(status.account_id, status.text)

    def after_post_status_from_queue(self, response, account_id, message):
        if self.is_exception(response):
            if self.core.get_notify_on_actions():
                self.os_notifications.message_queued_due_error()
            print "+++Message queued again for error posting"
            self.push_status_to_queue(account_id, message)
        else:
            self.turn_off_queue_timer()
            if self.core.get_notify_on_actions():
                if account_id == BROADCAST_ACCOUNT:
                    self.os_notifications.message_from_queue_broadcasted()
                else:
                    self.os_notifications.message_from_queue_posted()

    def after_delete_status_from_queue(self):
        self.queue_dialog.update()

    def after_clear_queue(self):
        self.queue_dialog.update()
        self.queue_dialog.update_timestamp()
        self.turn_off_queue_timer()

    def on_exception(self, exception):
        print 'Exception', exception

    # ------------------------------------------------------------
    # Timer Methods
    # ------------------------------------------------------------

    def add_timer(self, column):
        self.remove_timer(column.id_)

        interval = self.core.get_update_interval_per_column(column.id_) * 60 * 1000
        timer = Timer(interval, column, self.download_stream)
        self.timers[column.id_] = timer
        print '--Created timer for %s every %i sec' % (column.id_, interval)

    def remove_timer(self, column_id):
        if column_id in self.timers:
            self.timers[column_id].stop()
            del self.timers[column_id]
            print '--Removed timer for %s' % column_id

    def download_stream(self, column):
        if self._container.is_updating(column.id_):
            return True

        last_id = self._container.start_updating(column.id_)
        self.core.get_column_statuses(column, last_id)
        return True

    def set_queue_timer(self):
        self.remove_timer('queue')
        interval = self.core.get_queue_interval() * 60 * 1000
        timer = Timer(interval, None, self.update_status_from_queue)
        self.timers['queue'] = timer
        print '--Created timer for queue every %i sec' % interval

    def turn_on_queue_timer(self, force=False):
        self.queue_dialog.update()
        if (len(self.core.list_statuses_queue()) > 0 and 'queue' not in self.timers) or force:
            self.set_queue_timer()
            self.queue_dialog.update_timestamp()

    def turn_off_queue_timer(self):
        self.queue_dialog.update()
        if len(self.core.list_statuses_queue()) == 0:
            self.remove_timer('queue')
            self.queue_dialog.update_timestamp()

class Timer:
    def __init__(self, interval, column, callback):
        self.interval = interval
        self.column = column
        self.callback = callback
        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)
        self.timer.start(interval)

    def __on_timeout(self):
        self.callback(self.column)

    def get_id(self):
        return self.timer.timerId()

    def stop(self):
        self.timer.stop()

########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -*-

# Qt OAuth dialog for Turpial

from PyQt4.QtCore import QUrl
from PyQt4.QtWebKit import QWebView

from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import HLine


class OAuthDialog(QDialog):
    def __init__(self, account_dialog, url):
        QDialog.__init__(self)
        self.account_dialog = account_dialog
        self.setWindowTitle(i18n.get('authorize_turpial'))
        self.resize(800, 550)
        self.setModal(True)

        self.webview = QWebView()
        qurl = QUrl(url)
        self.webview.setUrl(qurl)

        message = QLabel(i18n.get('copy_the_pin'))
        message.setStyleSheet("QLabel { color: #fff; font-size: 14px;}")

        self.pin = QLineEdit()
        self.pin.setPlaceholderText(i18n.get('type_the_pin'))

        authorize_btn = QPushButton(i18n.get('authorize'))
        authorize_btn.clicked.connect(self.accept)

        open_in_browser_btn = QPushButton(i18n.get('open_in_browser'))
        open_in_browser_btn.clicked.connect(self.__external_open)

        widgets_box = QHBoxLayout()
        widgets_box.setSpacing(3)
        widgets_box.setContentsMargins(10, 10, 10, 10)
        widgets_box.addWidget(message, 1)
        widgets_box.addWidget(self.pin)
        widgets_box.addWidget(open_in_browser_btn)
        widgets_box.addWidget(authorize_btn)
        style = "background-color: %s; border: 0px solid %s; color: #fff;" % (self.account_dialog.base.bgcolor,
            self.account_dialog.base.bgcolor)
        self.setStyleSheet("QDialog { %s }" % style)

        layout = QVBoxLayout()
        layout.addWidget(self.webview)
        #layout.addWidget(HLine(2))
        layout.addLayout(widgets_box)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.exec_()

    def __external_open(self):
        self.account_dialog.base.open_in_browser(str(self.webview.url()))
        self.reject()

########NEW FILE########
__FILENAME__ = preferences
# -*- coding: utf-8 -*-

# Qt preferences dialog for Turpial

import subprocess

from datetime import datetime, timedelta

from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QSlider
from PyQt4.QtGui import QComboBox
from PyQt4.QtGui import QCheckBox
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QTabWidget
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QButtonGroup
from PyQt4.QtGui import QRadioButton
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout

from PyQt4.QtCore import Qt
from PyQt4.QtCore import pyqtSignal

from turpial.ui.lang import i18n

from turpial.ui.qt.widgets import Window

#TODO: Enable tp open dialog in a specific tab
class PreferencesDialog(Window):
    def __init__(self, base):
        Window.__init__(self, base, i18n.get('preferences'))
        self.setFixedSize(600, 370)
        self.current_config = self.base.get_config()
        self.setAttribute(Qt.WA_QuitOnClose, False)

        self.tabbar = QTabWidget()
        self.tabbar.setTabsClosable(False)
        self.tabbar.setMovable(False)
        self.tabbar.setUsesScrollButtons(True)
        self.tabbar.setElideMode(Qt.ElideNone)

        self.general_page = GeneralPage(base)
        self.notifications_page = NotificationsPage(base)
        self.services_page = ServicesPage(base)
        self.browser_page = BrowserPage(base)
        self.proxy_page = ProxyPage(base)
        self.advanced_page = AdvancedPage(base)

        self.tabbar.addTab(self.general_page, i18n.get('general'))
        self.tabbar.addTab(self.notifications_page, i18n.get('notifications'))
        self.tabbar.addTab(self.services_page, i18n.get('services'))
        self.tabbar.addTab(self.browser_page, i18n.get('web_browser'))
        self.tabbar.addTab(self.proxy_page, i18n.get('proxy'))
        self.tabbar.addTab(self.advanced_page, i18n.get('advanced'))

        self.save_button = QPushButton(i18n.get('save'))
        self.save_button.clicked.connect(self.__on_save)
        self.close_button = QPushButton(i18n.get('close'))
        self.close_button.clicked.connect(self.__on_close)

        button_box = QHBoxLayout()
        button_box.addStretch(1)
        button_box.setSpacing(4)
        button_box.addWidget(self.close_button)
        button_box.addWidget(self.save_button)

        vbox = QVBoxLayout()
        vbox.addWidget(self.tabbar, 1)
        vbox.addLayout(button_box)
        vbox.setContentsMargins(10, 10, 10, 10)
        self.setLayout(vbox)
        self.show()

    def __on_close(self):
        self.close()

    def __on_save(self):
        notif, sounds = self.notifications_page.get_config()

        new_config = {
            'General': self.general_page.get_config(),
            'Notifications': notif,
            'Sounds': sounds,
            'Services': self.services_page.get_config(),
            'Browser': self.browser_page.get_config(),
            'Proxy': self.proxy_page.get_config(),
            'Advanced': self.advanced_page.get_config()
        }
        self.base.update_config(new_config)
        self.close()

class BasePage(QWidget):
    def __init__(self, caption):
        QWidget.__init__(self)

        caption = "".join(["<b>", caption, "<b/>"])
        description = QLabel(caption)
        description.setWordWrap(True)
        description.setTextFormat(Qt.RichText)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.addWidget(description)
        self.layout.addSpacing(15)
        self.layout.setSpacing(5)

        self.setLayout(self.layout)

class GeneralPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('general_tab_description'))

        update_frequency = base.core.get_update_interval()
        queue_frequency = base.core.get_queue_interval()
        statuses = base.core.get_statuses_per_column()
        minimize_on_close = base.core.get_minimize_on_close()
        inline_preview = base.core.get_inline_preview()
        images_in_browser = base.core.get_show_images_in_browser()

        self.update_frequency = Slider(i18n.get('default_update_frequency'), unit='min',
            default_value=update_frequency, tooltip=i18n.get('default_update_frequency_tooltip'),
            caption_size=150)
        self.statuses_per_column = Slider(i18n.get('statuses_per_column'), minimum_value=20,
            maximum_value=200, default_value=statuses, caption_size=150)
        self.queue_frequency = Slider(i18n.get('queue_frequency'), minimum_value=5,
            maximum_value=720, default_value=queue_frequency, single_step=15, time=True,
            tooltip=i18n.get('queue_frequency_tooltip'), caption_size=150)
        self.minimize_on_close = CheckBox(i18n.get('minimize_on_close'), checked=minimize_on_close,
            tooltip=i18n.get('minimize_on_close_tooltip'))
        self.inline_preview = CheckBox(i18n.get('inline_preview'), checked=inline_preview,
            tooltip=i18n.get('inline_preview_tooltip'))
        self.images_in_browser = CheckBox(i18n.get('open_images_in_browser'), checked=images_in_browser,
            tooltip=i18n.get('open_images_in_browser_tooltip'))

        self.layout.addWidget(self.statuses_per_column)
        self.layout.addWidget(self.queue_frequency)
        self.layout.addWidget(self.update_frequency)
        self.layout.addSpacing(10)
        self.layout.addWidget(self.minimize_on_close)
        self.layout.addWidget(self.inline_preview)
        self.layout.addWidget(self.images_in_browser)
        self.layout.addStretch(1)

    def get_config(self):
        minimize = 'on' if self.minimize_on_close.get_value() else 'off'
        inline_preview = 'on' if self.inline_preview.get_value() else 'off'
        images_in_browser = 'on' if self.images_in_browser.get_value() else 'off'

        return {
            'update-interval': self.update_frequency.get_value(),
            'statuses': self.statuses_per_column.get_value(),
            'queue-interval': self.queue_frequency.get_value(),
            'minimize-on-close': minimize,
            'inline-preview': inline_preview,
            'show-images-in-browser': images_in_browser,
        }

class NotificationsPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('notifications_tab_description'))

        notify_on_updates = base.core.get_notify_on_updates()
        notify_on_actions = base.core.get_notify_on_actions()
        sound_on_login = base.core.get_sound_on_login()
        sound_on_updates = base.core.get_sound_on_updates()

        self.notify_on_new = CheckBox(i18n.get('notify_on_updates'), checked=notify_on_updates,
            tooltip=i18n.get('notify_on_updates_tooltip'))
        self.notify_on_actions = CheckBox(i18n.get('notify_on_actions'), checked=notify_on_actions,
            tooltip=i18n.get('notify_on_actions_toolip'))
        self.sound_on_login = CheckBox(i18n.get('sound_on_login'), checked=sound_on_login,
            tooltip=i18n.get('sound_on_login_tooltip'))
        self.sound_on_updates = CheckBox(i18n.get('sound_on_updates'), checked=sound_on_updates,
            tooltip=i18n.get('sound_on_updates_tooltip'))

        self.layout.addWidget(self.notify_on_new)
        self.layout.addSpacing(15)
        self.layout.addWidget(self.notify_on_actions)
        self.layout.addSpacing(15)
        self.layout.addWidget(self.sound_on_login)
        self.layout.addWidget(self.sound_on_updates)
        self.layout.addStretch(1)

    def get_config(self):
        notif = {
            'updates': 'on' if self.notify_on_new.get_value() else 'off',
            'actions': 'on' if self.notify_on_actions.get_value() else 'off'
        }
        sound = {
            'login': 'on' if self.sound_on_login.get_value() else 'off',
            'updates': 'on' if self.sound_on_updates.get_value() else 'off'
        }
        return notif, sound

class ServicesPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('services_tab_description'))

        short_url_services = base.core.get_available_short_url_services()
        default_short_url_service = base.core.get_shorten_url_service()
        self.short_url = ComboBox(i18n.get('short_urls'), sorted(short_url_services), default_short_url_service,
            expand_combo=True)

        upload_media_services = base.core.get_available_upload_media_services()
        default_upload_media_service = base.core.get_upload_media_service()
        self.upload_media = ComboBox(i18n.get('upload_image'), sorted(upload_media_services),
                default_upload_media_service, expand_combo=True)

        self.layout.addWidget(self.short_url)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.upload_media)
        self.layout.addStretch(1)

    def get_config(self):
        return {
            'shorten-url': self.short_url.get_value(),
            'upload-pic': self.upload_media.get_value()
        }

class BrowserPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('web_browser_tab_description'))

        current_browser = base.core.get_default_browser()

        self.command = QLineEdit()

        self.default_browser = RadioButton(i18n.get('use_default_browser'), self)
        self.default_browser.selected.connect(self.__on_defaul_selected)
        self.custom_browser = RadioButton(i18n.get('set_custom_browser'), self)
        self.custom_browser.selected.connect(self.__on_custom_selected)

        custom_label = QLabel(i18n.get('command'))
        self.open_button = QPushButton(i18n.get('open'))
        self.test_button = QPushButton(i18n.get('test'))
        self.test_button.clicked.connect(self.__on_test)

        command_box = QHBoxLayout()
        command_box.setSpacing(5)
        command_box.addWidget(custom_label)
        command_box.addWidget(self.command, 1)
        #command_box.addWidget(self.open_button)
        command_box.addWidget(self.test_button)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.default_browser.radiobutton)
        self.button_group.addButton(self.custom_browser.radiobutton)
        self.button_group.setExclusive(True)

        self.layout.addWidget(self.default_browser)
        self.layout.addSpacing(10)
        self.layout.addWidget(self.custom_browser)
        self.layout.addLayout(command_box)
        self.layout.addStretch(1)

        if current_browser == '' or current_browser is None:
            self.default_browser.set_value(True)
            self.command.setText('')
            self.__on_defaul_selected()
        else:
            self.custom_browser.set_value(True)
            self.command.setText(current_browser)
            self.__on_custom_selected()

    def __on_test(self):
        cmd = str(self.command.text())
        if cmd != '':
            subprocess.Popen([cmd, 'http://turpial.org.ve/'])

    def __on_defaul_selected(self):
        self.open_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.command.setEnabled(False)

    def __on_custom_selected(self):
        self.open_button.setEnabled(True)
        self.test_button.setEnabled(True)
        self.command.setEnabled(True)

    def get_config(self):
        if self.default_browser.get_value():
            cmd = ''
        else:
            cmd = str(self.command.text())
        return { 'cmd': cmd }

class ProxyPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('proxy_tab_description'))

        config = base.core.get_proxy_configuration()
        if config['username'] != '':
            default_authenticated = True
        else:
            default_authenticated = False

        self.protocol = ComboBox(i18n.get('type'), ['HTTP', 'HTTPS'], 'HTTP', expand_combo=True)
        self.host = LineEdit(i18n.get('host'), default_value=config['server'])
        self.port = LineEdit(i18n.get('port'), text_size=100, default_value=config['port'])
        self.authenticated = CheckBox(i18n.get('with_authentication'), checked=default_authenticated)
        self.authenticated.status_changed.connect(self.__on_click_authenticated)
        self.username = LineEdit(i18n.get('username'), default_value=config['username'])
        self.password = LineEdit(i18n.get('password'), default_value=config['password'])

        self.layout.addWidget(self.protocol)
        self.layout.addWidget(self.host)
        self.layout.addWidget(self.port)
        self.layout.addWidget(self.authenticated)
        self.layout.addWidget(self.username)
        self.layout.addWidget(self.password)
        self.layout.addStretch(1)

        self.__on_click_authenticated(default_authenticated)

    def __on_click_authenticated(self, checked):
        self.__show_authentication_widgets(checked)

    def __show_authentication_widgets(self, visible):
        self.username.set_visible(visible)
        self.password.set_visible(visible)

    def get_config(self):
        if self.authenticated.get_value():
            username = self.username.get_value()
            password = self.password.get_value()
        else:
            username = ''
            password = ''

        return {
            'protocol': self.protocol.get_value(),
            'server': self.host.get_value(),
            'port': self.port.get_value(),
            'username': username,
            'password': password
        }

class AdvancedPage(BasePage):
    def __init__(self, base):
        BasePage.__init__(self, i18n.get('advanced_tab_description'))
        self.base = base

        socket_timeout = base.core.get_socket_timeout()
        show_avatars = base.core.get_show_user_avatars()

        clean_cache_caption = "%s\n(%s)" % (i18n.get('delete_all_files_in_cache'), base.get_cache_size())
        self.clean_cache = PushButton(clean_cache_caption, i18n.get('clean_cache'))
        self.clean_cache.clicked.connect(self.__on_clean_cache)
        self.restore_config = PushButton(i18n.get('restore_config_to_default'), i18n.get('restore_config'))
        self.restore_config.clicked.connect(self.__on_config_restore)
        self.socket_timeout = Slider(i18n.get('socket_timeout'), default_value=socket_timeout,
            minimum_value=5, maximum_value=120, unit='sec', tooltip=i18n.get('socket_timeout_tooltip'))
        self.show_avatars = CheckBox(i18n.get('show_avatars'), checked=show_avatars,
            tooltip=i18n.get('show_avatars_tooltip'))

        self.layout.addWidget(self.clean_cache)
        self.layout.addWidget(self.restore_config)
        self.layout.addSpacing(15)
        self.layout.addWidget(self.socket_timeout)
        self.layout.addSpacing(10)
        self.layout.addWidget(self.show_avatars)
        self.layout.addStretch(1)

    def __on_clean_cache(self):
        self.base.clean_cache()
        clean_cache_caption = "%s\n(0 B)" % (i18n.get('delete_all_files_in_cache'))
        self.clean_cache.button.setEnabled(False)
        self.clean_cache.description.setText(clean_cache_caption)

    def __on_config_restore(self):
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_restore'),
            i18n.get('do_you_want_to_restore_config'))
        if confirmation:
            self.base.restore_config()
            self.base.show_information_message(i18n.get('restart_turpial'), i18n.get('config_restored_successfully'))
            self.base.main_quit()

    def get_config(self):
        show_avatars = 'on' if self.show_avatars.get_value() else 'off'
        return {
            'socket-timeout': self.socket_timeout.get_value(),
            'show-user-avatars': show_avatars
        }


################################################################################
### Widgets
################################################################################

# TODO: Add tooltips
class Slider(QWidget):
    changed = pyqtSignal(int)

    def __init__(self, caption, default_value, minimum_value=1, maximum_value=60, single_step=1,
            page_step=6, caption_size=None, unit='', time=False, tooltip=''):
        QWidget.__init__(self)

        self.value = default_value
        self.unit = unit
        self.time = time

        description = QLabel(caption)
        description.setWordWrap(True)
        description.setToolTip(tooltip)
        if caption_size:
            description.setFixedWidth(caption_size)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(maximum_value)
        self.slider.setMinimum(minimum_value)
        self.slider.setSingleStep(single_step)
        self.slider.setPageStep(page_step)
        self.slider.setToolTip(tooltip)
        #self.slider.setTickInterval(2)
        #self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.valueChanged.connect(self.__on_change)

        self.value_label = QLabel()

        hbox = QHBoxLayout()
        hbox.addWidget(description)
        hbox.addWidget(self.slider)
        hbox.addWidget(self.value_label)
        hbox.setMargin(0)
        self.setLayout(hbox)
        self.setContentsMargins(5, 0, 5, 0)
        self.slider.setValue(self.value)
        self.__on_change(self.value)

    def __on_change(self, value):
        # FIXME: Fill with spaces to reach the maximum length
        self.value = value
        unit = self.unit
        if self.time:
            minutes = timedelta(minutes=self.value)
            date = datetime(1, 1, 1) + minutes
            text = "%02dh %02dm" % (date.hour, date.minute)
        else:
            text = "%s %s" % (self.value, self.unit)
        self.value_label.setText(text)
        self.changed.emit(self.value)

    def get_value(self):
        return int(self.slider.value())

    def set_value(self, value):
        self.slider.setValue(value)

class CheckBox(QWidget):
    status_changed = pyqtSignal(bool)

    def __init__(self, caption, checked=False, tooltip=''):
        QWidget.__init__(self)

        self.value = checked

        self.checkbox = QCheckBox(caption)
        self.checkbox.stateChanged.connect(self.__on_change)
        self.checkbox.setToolTip(tooltip)

        hbox = QHBoxLayout()
        hbox.addWidget(self.checkbox)
        hbox.setMargin(0)
        self.setLayout(hbox)
        #self.setContentsMargins(5, 0, 5, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.checkbox.setChecked(self.value)

    def __on_change(self, value):
        self.value = value
        if value == Qt.Unchecked:
            self.status_changed.emit(False)
        else:
            self.status_changed.emit(True)

    def get_value(self):
        return self.checkbox.isChecked()

class ComboBox(QWidget):
    def __init__(self, caption, values, default_value, caption_size=None, expand_combo=False):
        QWidget.__init__(self)

        self.values = values

        description = QLabel(caption)
        description.setWordWrap(True)
        if caption_size:
            description.setMaximumWidth(caption_size)

        self.combo = QComboBox()
        for item in values:
            self.combo.addItem(item, item)

        for i in range(0, len(values)):
            if values[i] == default_value:
                self.combo.setCurrentIndex(i)
                break

        hbox = QHBoxLayout()
        hbox.addWidget(description)
        hbox.addSpacing(10)
        if expand_combo:
            hbox.addWidget(self.combo, 1)
        else:
            hbox.addWidget(self.combo)
        hbox.setMargin(0)
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)

    def get_value(self):
        return str(self.values[self.combo.currentIndex()])

class RadioButton(QWidget):
    selected = pyqtSignal()

    def __init__(self, caption, parent, selected=False):
        QWidget.__init__(self)

        self.value = selected
        self.radiobutton = QRadioButton(caption, parent)
        self.radiobutton.clicked.connect(self.__on_change)

        hbox = QHBoxLayout()
        hbox.addWidget(self.radiobutton)
        hbox.setMargin(0)
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)
        self.radiobutton.setChecked(self.value)

    def __on_change(self):
        self.value = True
        self.selected.emit()

    def set_value(self, value):
        self.radiobutton.setChecked(value)

    def get_value(self):
        return self.radiobutton.isChecked()

class PushButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, caption, button_text, caption_size=None):
        QWidget.__init__(self)

        self.description = QLabel(caption)
        self.description.setWordWrap(True)
        if caption_size:
            self.description.setMaximumWidth(caption_size)

        self.button = QPushButton(i18n.get(button_text))
        self.button.clicked.connect(self.__on_click)

        hbox = QHBoxLayout()
        hbox.addWidget(self.description, 1)
        hbox.addSpacing(10)
        hbox.addWidget(self.button)
        hbox.setMargin(0)
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)

    def __on_click(self):
        self.clicked.emit()

class LineEdit(QWidget):
    def __init__(self, caption, default_value=None, caption_size=None, text_size=None):
        QWidget.__init__(self)

        self.description = QLabel(caption)
        self.description.setWordWrap(True)
        if caption_size:
            self.description.setMaximumWidth(caption_size)

        self.line_edit = QLineEdit()
        if default_value:
            self.line_edit.setText(default_value)
        if text_size:
            self.line_edit.setMaximumWidth(text_size)

        hbox = QHBoxLayout()
        hbox.addWidget(self.description)
        hbox.addSpacing(10)
        hbox.addWidget(self.line_edit)
        if text_size:
            hbox.addStretch(1)
        hbox.setMargin(0)
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)

    def set_visible(self, value):
        self.description.setVisible(value)
        self.line_edit.setVisible(value)

    def get_value(self):
        return str(self.line_edit.text())

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-

# Qt profile dialog for Turpial

from PyQt4.QtGui import QFont
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QTabWidget
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QToolButton

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QPoint
from PyQt4.QtCore import QTimer
from PyQt4.QtCore import pyqtSignal

from turpial.ui.lang import i18n
from turpial.ui.qt.column import StatusesColumn
from turpial.ui.qt.widgets import ImageButton, VLine, Window, ErrorLabel, \
                                  BarLoadIndicator, StyledLabel

from libturpial.common.tools import get_username_from


class ProfileDialog(Window):

    options_clicked = pyqtSignal(QPoint, object)

    def __init__(self, base):
        Window.__init__(self, base, i18n.get('user_profile'))
        self.account_id = None
        self.setFixedSize(370, 550)

        self.this_is_you_label = StyledLabel(i18n.get('this_is_you'))
        self.follows_you_label = StyledLabel(i18n.get('follows_you'))

        self.avatar = ClickableLabel()
        self.avatar.setPixmap(base.load_image('unknown.png', True))
        self.avatar.clicked.connect(self.__show_avatar)

        self.username = QLabel('')
        self.username.setTextFormat(Qt.RichText)
        self.username.setAlignment(Qt.AlignCenter)
        self.fullname = QLabel('')
        self.fullname.setTextFormat(Qt.RichText)
        self.fullname.setStyleSheet("QLabel { font-size: 18px;}")
        self.bio = QLabel('')
        self.bio.setWordWrap(True)
        self.bio.setAlignment(Qt.AlignCenter)

        self.verified_icon = QLabel()
        self.verified_icon.setPixmap(base.load_image('mark-verified.png', True))
        self.protected_icon = QLabel()
        self.protected_icon.setPixmap(base.load_image('mark-protected.png', True))

        self.options_button = ImageButton(base, 'action-status-menu.png', '', borders=True)
        self.options_button.clicked.connect(self.__options_clicked)

        self.error_message = ErrorLabel()
        self.follow_button = QPushButton()
        self.loader = BarLoadIndicator()
        self.loading_label = QLabel(i18n.get('loading'))

        fullname_box = QHBoxLayout()
        fullname_box.setAlignment(Qt.AlignCenter)
        fullname_box.addWidget(self.fullname)
        fullname_box.addWidget(self.verified_icon)
        fullname_box.addWidget(self.protected_icon)

        username_box = QHBoxLayout()
        username_box.addWidget(self.username, 1)

        bio_box = QHBoxLayout()
        bio_box.addWidget(self.bio, 1)

        user_info_box = QVBoxLayout()
        user_info_box.setContentsMargins(5, 10, 5, 10)
        user_info_box.setSpacing(5)
        user_info_box.addWidget(self.avatar, 0, Qt.AlignCenter)
        user_info_box.addLayout(fullname_box, 1)
        #user_info_box.addWidget(self.username, 1, Qt.AlignCenter)
        user_info_box.addLayout(username_box)
        user_info_box.addLayout(bio_box)
        user_info_box.setSpacing(5)

        header_box = QHBoxLayout()
        header_box.setContentsMargins(0, 0, 0, 0)
        #header_box.addLayout(user_info_box, 1)
        header_box.addLayout(user_info_box)

        options_box = QHBoxLayout()
        options_box.setContentsMargins(10, 0, 10, 5)
        options_box.setSpacing(5)
        options_box.addWidget(self.options_button)
        options_box.addStretch(1)
        options_box.addWidget(self.error_message)
        options_box.addWidget(self.follows_you_label)
        options_box.addWidget(self.follow_button)
        options_box.addWidget(self.this_is_you_label)
        options_box.addWidget(self.loading_label)

        self.last_statuses = StatusesColumn(self.base, None, False)

        self.tweets = StatInfoBox('tweets', '')
        self.following = StatInfoBox('following', '')
        self.followers = StatInfoBox('followers', '')

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 5, 0, 10)
        footer_layout.setSpacing(0)
        footer_layout.addLayout(self.tweets)
        footer_layout.addWidget(VLine())
        footer_layout.addLayout(self.following)
        footer_layout.addWidget(VLine())
        footer_layout.addLayout(self.followers)

        footer = QWidget()
        footer.setLayout(footer_layout)
        footer.setStyleSheet("QWidget { background-color: #333; color: white; }")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header_box)
        layout.addLayout(options_box)
        layout.addWidget(self.loader)
        layout.addWidget(self.last_statuses)
        layout.addWidget(footer)
        self.setLayout(layout)

        self.__clear()

    def __clear(self):
        self.profile = None
        self.showed = False
        self.account_id = None
        self.verified_icon.setVisible(False)
        self.protected_icon.setVisible(False)
        self.loader.setVisible(False)
        self.options_button.setEnabled(False)
        self.error_message.setVisible(False)
        self.follows_you_label.setVisible(False)
        self.follow_button.setVisible(False)
        self.this_is_you_label.setVisible(False)
        self.loading_label.setVisible(False)
        self.avatar.setPixmap(self.base.load_image('unknown.png', True))
        self.fullname.setText('')
        self.username.setText('')
        self.bio.setText('')
        self.bio.setVisible(False)
        #self.web.set_info('')
        self.tweets.set_value('')
        self.following.set_value('')
        self.followers.set_value('')
        self.last_statuses.id_ = None
        self.last_statuses.clear()

    def __options_clicked(self):
        self.options_clicked.emit(QCursor.pos(), self.profile)

    def __show_avatar(self):
        self.base.show_profile_image(self.account_id, self.profile.username)

    def __on_timeout(self):
        self.error_message.setText('')
        self.error_message.setVisible(False)

    def __follow(self, account_id, username):
        self.loader.setVisible(True)
        self.follow_button.setEnabled(False)
        self.base.follow(account_id, username)

    def __unfollow(self, account_id, username):
        self.loader.setVisible(True)
        self.follow_button.setEnabled(False)
        self.base.unfollow(account_id, username)

    def __update_following(self, following):
        self.loader.setVisible(False)
        if following:
            self.follow_button.setText(i18n.get('unfollow'))
            self.follow_button.clicked.connect(lambda: self.__unfollow(self.profile.account_id,
                                                                       self.profile.username))
        else:
            self.follow_button.setText(i18n.get('follow'))
            self.follow_button.clicked.connect(lambda: self.__follow(self.profile.account_id,
                                                                     self.profile.username))
        self.follow_button.setEnabled(True)

    def __show_error_in_column(self, status_id, message):
        self.last_statuses.release_status(status_id)
        self.last_statuses.notify_error(status_id, message)

    def closeEvent(self, event=None):
        if event:
            event.ignore()
        self.__clear()
        self.hide()

    def start_loading(self, profile_username):
        self.__clear()
        self.loader.setVisible(True)
        self.loading_label.setVisible(True)
        self.options_button.setEnabled(False)
        self.show()
        self.raise_()
        self.showed = True

    def loading_finished(self, profile, account_id):
        self.profile = profile
        self.account_id = str(account_id)
        self.loader.setVisible(False)
        self.loading_label.setVisible(False)
        self.fullname.setText('<b>%s</b>' % profile.fullname)
        it_is_you = get_username_from(account_id) == profile.username

        username = '@%s' % profile.username
        if profile.location:
            username = ' | '.join([username, profile.location])
        self.username.setText(username)

        if profile.bio:
            self.bio.setText(profile.bio)
            self.bio.setVisible(True)
        else:
            self.bio.setVisible(False)

        if it_is_you:
            self.this_is_you_label.setVisible(True)
            self.follow_button.setVisible(False)
            self.options_button.setEnabled(False)
        else:
            self.this_is_you_label.setVisible(False)
            self.follow_button.setVisible(True)
            self.options_button.setEnabled(True)

        if profile.followed_by and not it_is_you:
            self.follows_you_label.setVisible(True)

        if profile.follow_request:
            self.follow_button.setText(i18n.get('follow_requested'))
            self.follow_button.setEnabled(False)
        else:
            self.__update_following(profile.following)

        self.verified_icon.setVisible(profile.verified)
        self.protected_icon.setVisible(profile.protected)
        self.avatar.setPixmap(self.base.load_image('unknown.png', True))
        #self.location.set_info(profile.location)

        if profile.url:
            profile_url ="<a href='%s'>%s</a>" % (profile.url, profile.url)
            #self.web.set_info(profile_url)

        self.tweets.set_value(self.base.humanize_size(profile.statuses_count, '', decimals=1))
        self.following.set_value(self.base.humanize_size(profile.friends_count, '', decimals=1))
        self.followers.set_value(self.base.humanize_size(profile.followers_count, '', decimals=1))

        column_id = "%s-profile_recent" % self.account_id
        self.last_statuses.set_column_id(column_id)
        self.last_statuses.update_statuses(profile.recent_updates)
        self.show()
        self.raise_()

    def is_for_profile(self, column_id):
        if column_id.find('profile_recent') > 0:
            return True
        return False

    def update_avatar(self, image_path, username):
        if not self.profile or username != self.profile.username or not self.showed:
            return
        self.avatar.setPixmap(self.base.load_image(image_path, True))

    def update_following(self, username, following):
        if not self.profile or username != self.profile.username or not self.showed:
            return
        self.profile.following = following
        self.__update_following(following)

    def error(self, message):
        self.loader.setVisible(False)
        self.fullname.setText('')
        self.error_message.setText(message)
        self.error_message.setVisible(True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)
        self.timer.start(5000)
        self.show()
        self.raise_()

    def error_marking_status_as_favorite(self, status_id, response):
        message = self.base.get_error_message_from_response(response, i18n.get('error_marking_status_as_favorite'))
        self.__show_error_in_column(status_id, message)

    def error_unmarking_status_as_favorite(self, status_id, response):
        message = self.base.get_error_message_from_response(response, i18n.get('error_unmarking_status_as_favorite'))
        self.__show_error_in_column(status_id, message)

    def error_repeating_status(self, status_id, response):
        message = self.base.get_error_message_from_response(response, i18n.get('error_repeating_status'))
        self.__show_error_in_column(status_id, message)

    def error_loading_conversation(self, status_root_id, response):
        message = self.base.get_error_message_from_response(response, i18n.get('error_loading_conversation'))
        self.last_statuses.error_in_conversation(status_root_id)
        self.last_statuses.notify_error(status_id, message)


class ProfileHeader(QWidget):
    def __init__(self, base):
        QWidget.__init__(self)
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        self.setStyleSheet("QWidget { background-color: #fff; }")
        self.webview = ProfileHeaderWebview(base)

    def clear(self):
        self.webview.clear()

    def update_profile(self, profile):
        self.webview.update_profile(profile)


class UserField(QVBoxLayout):
    def __init__(self, base, title, image, text=None, text_as_link=False):
        QVBoxLayout.__init__(self)
        icon = QLabel()
        icon.setPixmap(base.load_image(image, True))
        caption = QLabel("<b>%s</b>" % i18n.get(title))
        header = QHBoxLayout()
        header.addWidget(icon)
        header.addWidget(caption, 1)

        if text:
            self.text = QLabel(text)
        else:
            self.text = QLabel()
        self.text.setOpenExternalLinks(True);

        self.setSpacing(5)
        self.setContentsMargins(10, 0, 10, 0)
        self.addLayout(header)
        self.addWidget(self.text)

    def set_info(self, text=None):
        if text is not None:
            self.text.setText(text)

    def set_word_wrap(self, value):
        self.text.setWordWrap(value)

class StatInfoBox(QVBoxLayout):
    def __init__(self, title, value=None):
        QVBoxLayout.__init__(self)
        value = value or '0'

        font = QFont()
        font.setPointSize(16)
        font.setBold(True)

        self.stat = QLabel(value)
        self.stat.setAlignment(Qt.AlignCenter)
        self.stat.setFont(font)

        font2 = QFont()
        font2.setPointSize(10)
        caption = QLabel(i18n.get(title))
        caption.setAlignment(Qt.AlignCenter)
        caption.setFont(font2)

        self.setSpacing(5)
        self.setContentsMargins(0, 0, 0, 0)
        self.addWidget(self.stat)
        self.addWidget(caption)

    def set_value(self, value):
        self.stat.setText(value)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self):
        QLabel.__init__(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

########NEW FILE########
__FILENAME__ = queue
# -*- coding: utf-8 -*-

# Qt status queue for Turpial

import time

from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QTableView
from PyQt4.QtGui import QHeaderView
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QAbstractItemView
from PyQt4.QtGui import QStandardItem
from PyQt4.QtGui import QStandardItemModel

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QTimer
from PyQt4.QtCore import QString

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import Window
from turpial.ui.base import BROADCAST_ACCOUNT

from libturpial.common.tools import get_protocol_from, get_username_from


class QueueDialog(Window):
    def __init__(self, base):
        Window.__init__(self, base, i18n.get('messages_queue'))
        self.setFixedSize(500, 400)
        self.last_timestamp = None
        self.showed = False

        self.list_ = QTableView()
        self.list_.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_.clicked.connect(self.__account_clicked)

        self.caption = QLabel()
        self.caption.setWordWrap(True)
        self.caption.setAlignment(Qt.AlignCenter)

        self.estimated_time = QLabel()
        self.estimated_time.setWordWrap(True)
        self.estimated_time.setAlignment(Qt.AlignCenter)

        self.delete_button = QPushButton(i18n.get('delete'))
        self.delete_button.setEnabled(False)
        self.delete_button.setToolTip(i18n.get('delete_selected_message'))
        self.delete_button.clicked.connect(self.__delete_message)

        self.post_next_button = QPushButton(i18n.get('post_next'))
        self.post_next_button.setEnabled(False)
        self.post_next_button.setToolTip(i18n.get('post_next_tooltip'))
        self.post_next_button.clicked.connect(self.__post_next_message)

        self.clear_button = QPushButton(i18n.get('delete_all'))
        self.clear_button.setEnabled(False)
        self.clear_button.setToolTip(i18n.get('delete_all_messages_in_queue'))
        self.clear_button.clicked.connect(self.__delete_all)

        button_box = QHBoxLayout()
        button_box.addStretch(1)
        button_box.addWidget(self.post_next_button)
        button_box.addWidget(self.clear_button)
        button_box.addWidget(self.delete_button)

        layout = QVBoxLayout()
        layout.addWidget(self.list_, 1)
        layout.addWidget(self.caption)
        layout.addWidget(self.estimated_time)
        layout.addLayout(button_box)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

    def __account_clicked(self, point):
        self.delete_button.setEnabled(True)
        self.clear_button.setEnabled(True)

    def __delete_message(self):
        self.__disable()
        selection = self.list_.selectionModel()
        index = selection.selectedIndexes()[0]
        message = i18n.get('delete_message_from_queue_confirm')
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            message)
        if not confirmation:
            self.__enable()
            return
        self.base.delete_message_from_queue(index.row())

    def __delete_all(self):
        self.__disable()
        message = i18n.get('clear_message_queue_confirm')
        confirmation = self.base.show_confirmation_message(i18n.get('confirm_delete'),
            message)
        if not confirmation:
            self.__enable()
            return
        self.base.clear_queue()

    def __post_next_message(self):
        self.__disable()
        self.base.update_status_from_queue()

    def __enable(self):
        self.list_.setEnabled(True)
        self.delete_button.setEnabled(False)
        if len(self.base.core.list_statuses_queue()) > 0:
            self.clear_button.setEnabled(True)
            self.post_next_button.setEnabled(True)
        else:
            self.clear_button.setEnabled(False)
            self.post_next_button.setEnabled(False)

    def __disable(self):
        self.list_.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.post_next_button.setEnabled(False)

    def __on_timeout(self):
        now = int(time.time())
        interval = self.base.core.get_queue_interval() * 60
        if self.last_timestamp:
            est_time = ((self.last_timestamp + interval) - now) / 60
        else:
            est_time = 0

        humanized_est_time = self.base.humanize_time_intervals(est_time)
        next_message = ' '.join([i18n.get('next_message_should_be_posted_in'), humanized_est_time])

        if len(self.base.core.list_statuses_queue()) == 0:
            self.estimated_time.setText('')
        else:
            self.estimated_time.setText(next_message)

    def start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)
        self.timer.start(60000)

    def closeEvent(self, event=None):
        if event:
            event.ignore()
        self.hide()
        self.showed = False

    def show(self):
        if self.showed:
            self.raise_()
            return

        self.update()
        Window.show(self)
        self.showed = True

    def update(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderItem(0, QStandardItem(i18n.get('account')))
        model.setHorizontalHeaderItem(1, QStandardItem(i18n.get('message')))
        self.list_.setModel(model)
        self.list_.resizeColumnToContents(1)

        now = int(time.time())
        interval = self.base.core.get_queue_interval() * 60
        if self.last_timestamp:
            est_time = ((self.last_timestamp + interval) - now) / 60
        else:
            est_time = 0

        row = 0
        for status in self.base.core.list_statuses_queue():
            username = get_username_from(status.account_id)
            icon = QStandardItem(QString.fromUtf8(username))
            icon.setEditable(False)
            if status.account_id != BROADCAST_ACCOUNT:
                protocol_image = "%s.png" % get_protocol_from(status.account_id)
                icon.setIcon(QIcon(self.base.load_image(protocol_image, True)))
            model.setItem(row, 0, icon)

            text = QStandardItem(QString.fromUtf8(status.text))
            text.setEditable(False)
            model.setItem(row, 1, text)
            self.list_.resizeRowToContents(row)
            row += 1

        humanized_interval = self.base.humanize_time_intervals(self.base.core.get_queue_interval())
        humanized_est_time = self.base.humanize_time_intervals(est_time)

        warning = i18n.get('messages_will_be_send') % humanized_interval
        next_message = ' '.join([i18n.get('next_message_should_be_posted_in'), humanized_est_time])
        self.caption.setText(warning)

        if row == 0:
            self.estimated_time.setText('')
        else:
            self.estimated_time.setText(next_message)

        self.list_.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.list_.resizeColumnsToContents()

        self.__enable()

    def update_timestamp(self):
        if len(self.base.core.list_statuses_queue()) > 0:
            self.last_timestamp = int(time.time())
        else:
            self.last_timestamp = None

########NEW FILE########
__FILENAME__ = search
# -*- coding: utf-8 -*-

# Qt search dialog for Turpial

from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QComboBox
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QFormLayout, QVBoxLayout, QHBoxLayout

from PyQt4.QtCore import Qt

from turpial.ui.lang import i18n

from libturpial.common.tools import get_protocol_from, get_username_from


class SearchDialog(QDialog):
    def __init__(self, base):
        QDialog.__init__(self)
        self.base = base
        self.setWindowTitle(i18n.get('search'))
        self.setFixedSize(270, 110)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint)
        self.setModal(True)

        self.accounts_combo = QComboBox()
        accounts = self.base.core.get_registered_accounts()
        for account in accounts:
            protocol = get_protocol_from(account.id_)
            icon = QIcon(base.get_image_path('%s.png' % protocol))
            self.accounts_combo.addItem(icon, get_username_from(account.id_), account.id_)

        self.criteria = QLineEdit()
        self.criteria.setToolTip(i18n.get('criteria_tooltip'))

        form = QFormLayout()
        form.addRow(i18n.get('criteria'), self.criteria)
        form.addRow(i18n.get('account'), self.accounts_combo)
        form.setContentsMargins(30, 10, 10, 5)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        button = QPushButton(i18n.get('search'))
        button_box = QHBoxLayout()
        button_box.addStretch(0)
        button_box.addWidget(button)
        button_box.setContentsMargins(0, 0, 15, 15)

        button.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(button_box)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.criteria.setFocus()

        self.exec_()

    def get_criteria(self):
        return self.criteria.text()

    def get_account(self):
        index = self.accounts_combo.currentIndex()
        return self.accounts_combo.itemData(index)


########NEW FILE########
__FILENAME__ = selectfriend
# -*- coding: utf-8 -*-

# Qt select friend dialog for Turpial

from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QComboBox
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QCompleter
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QFormLayout, QVBoxLayout, QHBoxLayout

from PyQt4.QtCore import Qt

from turpial.ui.lang import i18n
from turpial.ui.qt.widgets import ModalDialog

from libturpial.common.tools import get_protocol_from, get_username_from


class SelectFriendDialog(ModalDialog):
    def __init__(self, base):
        ModalDialog.__init__(self, 290, 110)
        self.base = base
        self.setWindowTitle(i18n.get('select_friend_to_send_message'))

        self.accounts_combo = QComboBox()
        accounts = self.base.core.get_registered_accounts()
        for account in accounts:
            protocol = get_protocol_from(account.id_)
            icon = QIcon(base.get_image_path('%s.png' % protocol))
            self.accounts_combo.addItem(icon, get_username_from(account.id_), account.id_)

        completer = QCompleter(self.base.load_friends_list())
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.friend = QLineEdit()
        self.friend.setCompleter(completer)
        select_button = QPushButton(i18n.get('select'))
        select_button.clicked.connect(self.__validate)

        friend_caption = "%s (@)" % i18n.get('friend')
        form = QFormLayout()
        form.addRow(friend_caption, self.friend)
        form.addRow(i18n.get('account'), self.accounts_combo)
        form.setContentsMargins(30, 10, 10, 5)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        button = QPushButton(i18n.get('search'))
        button_box = QHBoxLayout()
        button_box.addStretch(0)
        button_box.addWidget(select_button)
        button_box.setContentsMargins(0, 0, 15, 15)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(button_box)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        #load_button = ImageButton(base, 'action-status-menu.png',
        #        i18n.get('load_friends_list'))

        self.exec_()

    def __validate(self):
        if self.get_username() != '':
            self.accept()


    def get_account(self):
        index = self.accounts_combo.currentIndex()
        return str(self.accounts_combo.itemData(index).toPyObject())

    def get_username(self):
        return str(self.friend.text())

########NEW FILE########
__FILENAME__ = shortcuts
# -*- coding: utf-8 -*-

# Qt shortcuts for Turpial

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QObject
from PyQt4.QtCore import pyqtSignal

from PyQt4.QtGui import QAction
from PyQt4.QtGui import QShortcut
from PyQt4.QtGui import QKeySequence

class Shortcuts:
    def __init__(self, base):
        Shortcut.base = base
        self.__shortcuts = {
            'accounts': Shortcut(Qt.CTRL + Qt.Key_A, 'A'),
            'filters': Shortcut(Qt.CTRL + Qt.Key_F, 'F'),
            'tweet': Shortcut(Qt.CTRL + Qt.Key_T, 'T'),
            'message': Shortcut(Qt.CTRL + Qt.Key_M, 'M'),
            'search': Shortcut(Qt.CTRL + Qt.Key_S, 'S'),
            'queue': Shortcut(Qt.CTRL + Qt.Key_U, 'U'),
            'preferences': Shortcut(Qt.CTRL + Qt.Key_Comma, ','),
            'quit': Shortcut(Qt.CTRL + Qt.Key_Q, 'Q'),
        }

    def __iter__(self):
        return self.__shortcuts.iteritems()

    def get(self, action):
        return self.__shortcuts[action]

class Shortcut(QObject):
    activated = pyqtSignal()

    def __init__(self, sequence, key, modifier=None):
        QObject.__init__(self)
        self.sequence = QKeySequence(sequence)
        self.caption = self.base.get_shortcut_string(key, modifier)
        self.action = QAction(self.base)
        self.action.setShortcutContext(Qt.ApplicationShortcut)
        self.action.setShortcut(self.sequence)
        self.action.triggered.connect(self.__triggered)

    def __triggered(self):
        self.activated.emit()

########NEW FILE########
__FILENAME__ = tray
# -*- coding: utf-8 -*-

# Qt tray icon for Turpial

from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QCursor
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QSystemTrayIcon

from PyQt4.QtCore import QPoint
from PyQt4.QtCore import pyqtSignal

from turpial import DESC
from turpial.ui.lang import i18n

from libturpial.common import OS_MAC
from libturpial.common.tools import detect_os

class TrayIcon(QSystemTrayIcon):

    settings_clicked = pyqtSignal(QPoint)
    updates_clicked = pyqtSignal()
    messages_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()
    toggled = pyqtSignal()

    def __init__(self, base):
        QSystemTrayIcon.__init__(self)

        self.base = base
        if detect_os() == OS_MAC:
            icon = QIcon(base.get_image_path('turpial-tray-mono-dark.png'))
        else:
            icon = QIcon(base.get_image_path('turpial-tray.png'))
        self.setIcon(icon)
        self.setToolTip(DESC)

        self.activated.connect(self.__activated)
        self.loading()
        self.show()

    def __build_header_menu(self):
        show = QAction(i18n.get('show_hide'), self)
        show.triggered.connect(self.__show_clicked)

        self.menu.addAction(show)
        self.menu.addSeparator()

    def __build_common_menu(self):
        settings = QAction(i18n.get('settings'), self)
        settings.triggered.connect(self.__settings_clicked)
        quit = QAction(i18n.get('quit'), self)
        quit.triggered.connect(self.__quit_clicked)

        self.menu.addAction(settings)
        self.menu.addSeparator()
        self.menu.addAction(quit)

    def __settings_clicked(self):
        self.settings_clicked.emit(QCursor.pos())

    def __updates_clicked(self):
        self.updates_clicked.emit()

    def __messages_clicked(self):
        self.messages_clicked.emit()

    def __quit_clicked(self):
        self.quit_clicked.emit()

    def __show_clicked(self):
        self.toggled.emit()

    def __activated(self, reason):
        if reason == QSystemTrayIcon.Context:
            self.menu.popup(QCursor.pos())

    def empty(self):
        self.menu = QMenu()
        self.__build_common_menu()
        self.setContextMenu(self.menu)

    def loading(self):
        self.menu = QMenu()
        loading = QAction(i18n.get('loading'), self)
        loading.setEnabled(False)
        self.menu.addAction(loading)
        self.setContextMenu(self.menu)

    def normal(self):
        self.menu = QMenu()

        self.__build_header_menu()

        updates = QAction(i18n.get('update_status'), self)
        updates.triggered.connect(self.__updates_clicked)
        messages = QAction(i18n.get('send_direct_message'), self)
        messages.triggered.connect(self.__messages_clicked)
        self.menu.addAction(updates)
        self.menu.addAction(messages)

        self.__build_common_menu()

        self.setContextMenu(self.menu)

    # Change the tray icon image to indicate updates
    def notify(self):
        self.set_from_pixbuf(self.base.load_image('turpial-tray-update.png', True))

    # Clear the tray icon image
    def clear(self):
        self.set_from_pixbuf(self.base.load_image('turpial-tray.png', True))

########NEW FILE########
__FILENAME__ = updatebox
# -*- coding: utf-8 -*-

# Qt update box for Turpial

from PyQt4.QtGui import QFont
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QComboBox
from PyQt4.QtGui import QTextEdit
from PyQt4.QtGui import QCompleter
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QTextCursor
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QFileDialog

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QTimer
from PyQt4.QtCore import pyqtSignal

from turpial.ui.lang import i18n
from turpial.ui.base import BROADCAST_ACCOUNT
from turpial.ui.qt.widgets import ImageButton, ErrorLabel, BarLoadIndicator

from libturpial.common.tools import get_urls
from libturpial.common import get_username_from, get_protocol_from

MAX_CHAR = 140

class UpdateBox(QWidget):
    def __init__(self, base):
        QWidget.__init__(self)
        self.base = base
        self.showed = False
        self.setFixedSize(500, 120)

        self.text_edit = CompletionTextEdit()

        self.upload_button = ImageButton(base, 'action-add-media.png',
                i18n.get('add_photo'), borders=True)
        self.short_button = ImageButton(base, 'action-shorten.png',
                i18n.get('short_urls'), borders=True)

        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.char_count = QLabel('140')
        self.char_count.setFont(font)

        self.update_button = QPushButton(i18n.get('update'))
        self.update_button.setToolTip(self.base.get_shortcut_string('Enter'))
        self.queue_button = QPushButton(i18n.get('add_to_queue'))
        self.queue_button.setToolTip(self.base.get_shortcut_string('P'))

        self.accounts_combo = QComboBox()

        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        buttons.addWidget(self.accounts_combo)
        buttons.addWidget(self.upload_button)
        buttons.addWidget(self.short_button)
        buttons.addStretch(0)
        buttons.addWidget(self.char_count)
        buttons.addWidget(self.queue_button)
        buttons.addWidget(self.update_button)

        self.loader = BarLoadIndicator()

        self.error_message = ErrorLabel()

        self.media = None
        self.preview_image = QLabel()
        self.preview_image.setVisible(False)

        text_edit_box = QHBoxLayout()
        text_edit_box.addWidget(self.text_edit)
        text_edit_box.addSpacing(5)
        text_edit_box.addWidget(self.preview_image)

        self.update_button.clicked.connect(self.__update_status)
        self.queue_button.clicked.connect(self.__queue_status)
        self.short_button.clicked.connect(self.__short_urls)
        self.upload_button.clicked.connect(self.__media_clicked)
        self.text_edit.textChanged.connect(self.__update_count)
        self.text_edit.quit.connect(self.closeEvent)
        self.text_edit.activated.connect(self.__update_status)
        self.text_edit.enqueued.connect(self.__queue_status)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        #layout.addWidget(self.text_edit)
        layout.addLayout(text_edit_box)
        layout.addWidget(self.loader)
        layout.addSpacing(5)
        layout.addWidget(self.error_message)
        layout.addLayout(buttons)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        self.__clear()

    def __count_chars(self):
        message = self.text_edit.toPlainText()
        urls = [str(url) for url in get_urls(message) if len(url) > 23]
        for url in urls:
            message = message.replace(url, '0' * 23)
        if self.media:
            message += '0' * 23
        return MAX_CHAR - len(message)

    def __update_count(self):
        remaining_chars = self.__count_chars()
        if remaining_chars < 0:
            self.char_count.setStyleSheet("QLabel { color: #D40D12 }")
        elif remaining_chars <= 10:
            self.char_count.setStyleSheet("QLabel { color: #D4790D }")
        else:
            self.char_count.setStyleSheet("QLabel { color: #000000 }")
        self.char_count.setText(str(remaining_chars))

    def __validate(self, message, accounts, index):
        if len(message) == 0:
            self.error(i18n.get('you_can_not_submit_an_empty_message'))
            return False

        if index == 0 and len(accounts) > 1:
            self.error(i18n.get('select_an_account_before_post'))
            return False

        if self.__count_chars() < 0:
            self.error(i18n.get('message_too_long'))
            return False

        index = self.accounts_combo.currentIndex()
        account_id = str(self.accounts_combo.itemData(index).toPyObject())
        if self.media and account_id == BROADCAST_ACCOUNT:
            self.error(i18n.get('broadcast_status_with_media_not_supported'))
            return False

        return True

    def __short_urls(self):
        self.enable(False)
        message = unicode(self.text_edit.toPlainText())
        self.base.short_urls(message)

    def __media_clicked(self):
        if self.media:
            self.__remove_media()
        else:
            self.__upload_media()

    def __upload_media(self):
        filename = str(QFileDialog.getOpenFileName(self, i18n.get('upload_image'),
            self.base.home_path))

        if filename != '':
            self.media = filename
            pix = QPixmap(filename)
            scaled_pix = pix.scaled(100, 100, Qt.KeepAspectRatio)
            self.preview_image.setPixmap(scaled_pix)
            self.preview_image.setVisible(True)
            self.upload_button.change_icon('action-remove-media.png')
            self.upload_button.setToolTip(i18n.get('remove_photo'))
            self.queue_button.setEnabled(False)
            self.__update_count()

    def __remove_media(self):
        self.media = None
        self.preview_image.setPixmap(QPixmap())
        self.preview_image.setVisible(False)
        self.upload_button.change_icon('action-add-media.png')
        self.upload_button.setToolTip(i18n.get('add_photo'))
        self.queue_button.setEnabled(True)

    def __update_status(self):
        index = self.accounts_combo.currentIndex()
        accounts = self.base.core.get_registered_accounts()
        message = unicode(self.text_edit.toPlainText())

        if not self.__validate(message, accounts, index):
            self.enable(True)
            return

        self.enable(False)
        account_id = str(self.accounts_combo.itemData(index).toPyObject())

        if self.direct_message_to:
            self.base.send_direct_message(account_id, self.direct_message_to, message)
        else:
            if account_id == 'broadcast':
                self.base.broadcast_status(message)
            else:
                if self.media:
                    self.base.update_status_with_media(account_id, message, self.media,
                                                       self.in_reply_to_id)
                else:
                    self.base.update_status(account_id, message, self.in_reply_to_id)

    def __queue_status(self):
        index = self.accounts_combo.currentIndex()
        accounts = self.base.core.get_registered_accounts()
        account_id = str(self.accounts_combo.itemData(index).toPyObject())
        message = unicode(self.text_edit.toPlainText())

        if not self.__validate(message, accounts, index):
            self.enable(True)
            return

        self.enable(False)
        self.base.push_status_to_queue(account_id, message)

    def __clear(self):
        self.account_id = None
        self.in_reply_to_id = None
        self.in_reply_to_user = None
        self.direct_message_to = None
        self.quoting = False
        self.message = None
        self.media = None
        self.cursor_position = None
        self.text_edit.setText('')
        self.accounts_combo.setCurrentIndex(0)
        self.queue_button.setEnabled(True)
        self.loader.setVisible(False)
        self.preview_image.setPixmap(QPixmap())
        self.preview_image.setVisible(False)
        self.upload_button.change_icon('action-add-media.png')
        self.upload_button.setToolTip(i18n.get('add_photo'))
        self.error_message.setVisible(False)
        self.error_message.setText('')
        self.enable(True)
        self.showed = False

    def __show(self):
        self.update_friends_list()
        short_service = self.base.get_shorten_url_service()
        short_tooltip = "%s (%s)" % (i18n.get('short_url'), short_service)
        self.short_button.setToolTip(short_tooltip)
        upload_service = self.base.get_upload_media_service()
        upload_tooltip = "%s (%s)" % (i18n.get('upload_image'), upload_service)
        self.upload_button.setToolTip(upload_tooltip)
        self.accounts_combo.clear()
        accounts = self.base.core.get_registered_accounts()
        if len(accounts) > 1:
            self.accounts_combo.addItem('--', '')
        for account in accounts:
            protocol = get_protocol_from(account.id_)
            icon = QIcon(self.base.get_image_path('%s.png' % protocol))
            self.accounts_combo.addItem(icon, get_username_from(account.id_), account.id_)
        if len(accounts) > 1:
            icon = QIcon(self.base.get_image_path('action-conversation.png'))
            self.accounts_combo.addItem(icon, i18n.get('broadcast'), 'broadcast')
        if self.account_id:
            index = self.accounts_combo.findData(self.account_id)
            if index > 0:
                self.accounts_combo.setCurrentIndex(index)
            self.accounts_combo.setEnabled(False)
        if self.message:
            self.text_edit.setText(self.message)
            cursor = self.text_edit.textCursor()
            cursor.movePosition(self.cursor_position, QTextCursor.MoveAnchor)
            self.text_edit.setTextCursor(cursor)

        QWidget.show(self)
        self.showed = True

    def __on_timeout(self):
        self.error_message.setText('')
        self.error_message.setVisible(False)

    def show(self):
        if self.showed:
            return self.raise_()
        self.setWindowTitle(i18n.get('whats_happening'))
        self.__show()

    def show_for_reply(self, account_id, status):
        if self.showed:
            return self.raise_()
        title = "%s @%s" % (i18n.get('reply_to'), status.username)
        self.setWindowTitle(title)
        self.account_id = account_id
        self.in_reply_to_id = status.id_
        self.in_reply_to_user = status.username
        mentions = ' '.join(["@%s" % user for user in status.get_mentions()])
        self.message = "%s " % mentions
        self.cursor_position = QTextCursor.End
        self.__show()

    def show_for_send_direct(self, account_id, username):
        if self.showed:
            return self.raise_()
        title = "%s @%s" % (i18n.get('send_message_to'), username)
        self.setWindowTitle(title)
        self.account_id = account_id
        self.direct_message_to = username
        self.__show()
        self.queue_button.setEnabled(False)

    def show_for_reply_direct(self, account_id, status):
        if self.showed:
            return self.raise_()
        title = "%s @%s" % (i18n.get('send_message_to'), status.username)
        self.setWindowTitle(title)
        self.account_id = account_id
        self.direct_message_to = status.username
        self.__show()
        self.queue_button.setEnabled(False)

    def show_for_quote(self, account_id, status):
        if self.showed:
            return self.raise_()
        self.setWindowTitle(i18n.get('quoting'))
        self.account_id = account_id
        self.message = " RT @%s %s" % (status.username, status.text)
        self.cursor_position = QTextCursor.Start
        self.quoting = True
        self.__show()
        self.queue_button.setEnabled(False)

    def closeEvent(self, event=None):
        message = unicode(self.text_edit.toPlainText())

        if len(message) > 0:
            confirmation = self.base.show_confirmation_message(i18n.get('confirm_discard'),
                i18n.get('do_you_want_to_discard_message'))
            if not confirmation:
                return

        if event:
            event.ignore()
        self.__clear()
        self.hide()

    def enable(self, value):
        self.text_edit.setEnabled(value)
        if not self.account_id:
            self.accounts_combo.setEnabled(value)
        if self.in_reply_to_id or self.direct_message_to or self.quoting:
            self.queue_button.setEnabled(False)
        else:
            self.queue_button.setEnabled(value)
        self.upload_button.setEnabled(value)
        self.short_button.setEnabled(value)
        self.update_button.setEnabled(value)
        self.loader.setVisible(not value)

    def done(self):
        self.__clear()
        self.hide()

    def error(self, message, response=None):
        if response is not None:
            message = self.base.get_error_message_from_response(response, message)

        self.enable(True)
        self.error_message.setText(message)
        self.error_message.setVisible(True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.__on_timeout)
        self.timer.start(5000)

    def after_short_url(self, message):
        if self.base.is_exception(message):
            self.error(i18n.get('error_shorting_url'))
        else:
            self.text_edit.setText(message)
        self.enable(True)

    def after_upload_media(self, media_url):
        if self.base.is_exception(media_url):
            self.error(i18n.get('error_uploading_image'))
        else:
            text_cursor = self.text_edit.textCursor()
            text_cursor.select(QTextCursor.WordUnderCursor)
            if text_cursor.selectedText() != '':
                media_url = " %s" % media_url
            text_cursor.clearSelection()
            text_cursor.insertText(media_url)
            self.text_edit.setTextCursor(text_cursor)
        self.enable(True)

    def update_friends_list(self):
        completer = QCompleter(self.base.load_friends_list_with_extras())
        self.text_edit.setCompleter(completer)


class CompletionTextEdit(QTextEdit):
    IGNORED_KEYS = (
        Qt.Key_Enter,
        Qt.Key_Return,
        Qt.Key_Escape,
        Qt.Key_Tab,
        Qt.Key_Backtab
    )

    quit = pyqtSignal()
    activated = pyqtSignal()
    enqueued = pyqtSignal()

    def __init__(self):
        QTextEdit.__init__(self)
        self.completer = None
        self.setAcceptRichText(False)
        self.setTabChangesFocus(True)

    def setCompleter(self, completer):
        if self.completer:
            self.completer.activated.disconnect()

        self.completer = completer
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        if self.completer.widget() != self:
            return

        tc = self.textCursor()
        extra = (completion.length() - self.completer.completionPrefix().length())
        tc.movePosition(QTextCursor.StartOfWord)
        tc.select(QTextCursor.WordUnderCursor)
        tc.insertText(''.join([str(completion), ' ']))
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        text = ""
        while True:
            tc.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
            text = tc.selectedText()
            if tc.position() == 0:
                break
            if text.startsWith(' '):
                text = text[1:]
                break

        return text

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QTextEdit.focusInEvent(self, event)

    def keyPressEvent(self, event):
        #print self.completer
        if self.completer and self.completer.popup().isVisible():
            if event.key() in self.IGNORED_KEYS:
                event.ignore()
                return

        if event.key() == Qt.Key_Escape:
            self.quit.emit()
            return

        QTextEdit.keyPressEvent(self, event)

        hasModifier = event.modifiers() != Qt.NoModifier
        enterKey = event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return
        queueKey = event.key() == Qt.Key_P

        if hasModifier and event.modifiers() == Qt.ControlModifier and enterKey:
            self.activated.emit()
            return

        if hasModifier and event.modifiers() == Qt.ControlModifier and queueKey:
            self.enqueued.emit()
            return

        completionPrefix = self.textUnderCursor()

        if hasModifier or event.text().isEmpty() or not completionPrefix.startsWith('@'):
            self.completer.popup().hide()
            #print 'me fui', event.key(), int(event.modifiers())
            return

        if completionPrefix.startsWith('@') and completionPrefix[1:] != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completionPrefix[1:])
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cursor_rect)



########NEW FILE########
__FILENAME__ = webview
# -*- coding: utf-8 -*-

# Qt widget to show statusesin Turpial using a QWebView

import re
import os

from jinja2 import Template

from PyQt4.QtWebKit import QWebView
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtWebKit import QWebSettings

from PyQt4.QtCore import Qt
from PyQt4.QtCore import pyqtSignal

from turpial.ui.lang import i18n
from libturpial.common import is_preview_service_supported

class StatusesWebView(QWebView):

    link_clicked = pyqtSignal(str)
    hashtag_clicked = pyqtSignal(str)
    profile_clicked = pyqtSignal(str)
    cmd_clicked = pyqtSignal(str)

    EMPTY_PAGE = '<html><head></head><body></body></html>'

    def __init__(self, base, column_id):
        QWebView.__init__(self)
        self.base = base
        self.column_id = column_id
        self.linkClicked.connect(self.__element_clicked)
        page = self.page()
        page.setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        page.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        if not self.base.debug:
            self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setPage(page)
        self.setHtml(self.EMPTY_PAGE)
        self.status_template = self.__load_template('status.html')

        self.stylesheet = self.__load_stylesheet()
        self.show()

    def __element_clicked(self, qurl):
        try:
            url = str(qurl.toString())
        except UnicodeEncodeError:
            return

        if url.startswith('http'):
            self.link_clicked.emit(url)
        elif url.startswith('hashtag'):
            hashtag = "#%s" % url.split(':')[2]
            self.hashtag_clicked.emit(hashtag)
        elif url.startswith('profile'):
            self.profile_clicked.emit(url.split(':')[1])
        elif url.startswith('cmd'):
            self.cmd_clicked.emit(url.split('cmd:')[1])

    def __load_template(self, name):
        path = os.path.join(self.base.templates_path, name)
        fd = open(path)
        content = fd.read()
        fd.close()
        return Template(content)

    def __load_stylesheet(self):
        attrs = {
            'mark_protected': os.path.join(self.base.images_path, 'mark-protected.png'),
            'mark_favorited': os.path.join(self.base.images_path, 'mark-favorited2.png'),
            'mark_repeated': os.path.join(self.base.images_path, 'mark-repeated2.png'),
            'mark_reposted': os.path.join(self.base.images_path, 'mark-reposted.png'),
            'mark_verified': os.path.join(self.base.images_path, 'mark-verified.png'),
            'action_reply': os.path.join(self.base.images_path, 'action-reply.png'),
            'action_reply_direct': os.path.join(self.base.images_path, 'action-reply-direct.png'),
            'action_repeat': os.path.join(self.base.images_path, 'action-repeat.png'),
            'action_quote': os.path.join(self.base.images_path, 'action-quote.png'),
            'action_favorite': os.path.join(self.base.images_path, 'action-favorite.png'),
            'action_reply_shadowed': os.path.join(self.base.images_path, 'action-reply-shadowed.png'),
            'action_reply_direct_shadowed': os.path.join(self.base.images_path, 'action-reply-direct-shadowed.png'),
            'action_repeat_shadowed': os.path.join(self.base.images_path, 'action-repeat-shadowed.png'),
            'action_quote_shadowed': os.path.join(self.base.images_path, 'action-quote-shadowed.png'),
            'action_favorite_shadowed': os.path.join(self.base.images_path, 'action-favorite-shadowed.png'),
            'action_delete': os.path.join(self.base.images_path, 'action-delete.png'),
            'action_delete_shadowed': os.path.join(self.base.images_path, 'action-delete-shadowed.png'),
        }
        stylesheet = self.__load_template('style.css')
        return stylesheet.render(attrs)

    def __render_status(self, status, with_conversation=True):
        repeated_by = None
        conversation_id = None
        view_conversation = None
        hide_conversation = None
        message = status.text
        message = message.replace('\n', '<br/>')
        message = message.replace('\'', '&apos;')
        timestamp = self.base.humanize_timestamp(status.timestamp)

        media = []
        if status.entities:
            # Highlight URLs
            for url in status.entities['urls']:
                pretty_url = "<a href='%s' title='%s'>%s</a>" % (url.url, url.url, url.display_text)
                message = message.replace(url.search_for, pretty_url)

                if is_preview_service_supported(url.url) and self.base.core.get_inline_preview():
                    media.append(url.url)

            # Highlight hashtags
            sorted_hashtags = {}
            for hashtag in status.entities['hashtags']:
                pretty_hashtag = "<a href='hashtag:%s:%s'>%s</a>" % (hashtag.account_id,
                        hashtag.display_text[1:], hashtag.display_text)
                pattern = r"%s\b" % hashtag.search_for
                message = re.sub(pattern, pretty_hashtag, message)

            # Highlight mentions
            for mention in status.entities['mentions']:
                pretty_mention = "<a href='profile:%s'>%s</a>" % (mention.url, mention.display_text)
                message = message.replace(mention.search_for, pretty_mention)

        if status.repeated_by:
            repeated_by = "%s %s" % (i18n.get('retweeted_by'), status.repeated_by)
        if status.in_reply_to_id and with_conversation:
            conversation_id = "%s-conversation-%s" % (self.column_id, status.id_)
            view_conversation = i18n.get('view_conversation')
            hide_conversation = i18n.get('hide_conversation')

        if self.base.core.get_show_user_avatars():
            avatar = status.avatar
        else:
            avatar = "file://%s" % os.path.join(self.base.images_path, 'unknown.png')

        attrs = {'status': status, 'message': message, 'repeated_by': repeated_by,
                'timestamp': timestamp, 'view_conversation': view_conversation,
                'reply': i18n.get('reply'), 'hide_conversation': hide_conversation,
                'quote': i18n.get('quote'), 'retweet': i18n.get('retweet'),
                'mark_as_favorite': i18n.get('mark_as_favorite'), 'delete': i18n.get('delete'),
                'remove_from_favorites': i18n.get('remove_from_favorites'),
                'conversation_id': conversation_id, 'in_progress': i18n.get('in_progress'), 
                'loading': i18n.get('loading'), 'avatar': avatar, 'media': media}

        return self.status_template.render(attrs)

    def update_statuses(self, statuses):
        statuses_ = statuses[:]
        content = ''

        current_page = self.page().currentFrame().toHtml()

        if current_page == self.EMPTY_PAGE:
            for status in statuses_:
                content += self.__render_status(status)
            column = self.__load_template('column.html')
            args = {'stylesheet': self.stylesheet, 'content': content,
                'favorite_tooltip': i18n.get('mark_as_favorite'),
                'unfavorite_tooltip': i18n.get('remove_from_favorites')}
            html = column.render(args)

            fd = open('/tmp/turpial-debug.html', 'w')
            fd.write(html.encode('ascii', 'ignore'))
            fd.close()
            self.setHtml(html)
            self.clear_new_marks()
        else:
            statuses_.reverse()
            for status in statuses_:
                content = self.__render_status(status)
                self.append_status(content, status.id_)
            self.execute_javascript('restoreScrollPosition()')

    def clear(self):
        self.setHtml('')

    def execute_javascript(self, js_cmd):
        self.page().mainFrame().evaluateJavaScript(js_cmd)

    def update_conversation(self, status, status_root_id):
        status_rendered = self.__render_status(status, with_conversation=False)
        status_rendered = status_rendered.replace("\n", '')
        status_rendered = status_rendered.replace('\'', '"')
        conversation = """updateConversation('%s', '%s')""" % (status_root_id, status_rendered)
        self.execute_javascript(conversation)

    def view_conversation(self, status_root_id):
        conversation = "viewConversation('%s')" % status_root_id
        self.execute_javascript(conversation)

    def clear_conversation(self, status_root_id):
        conversation = "clearConversation('%s')" % status_root_id
        self.execute_javascript(conversation)

    def append_status(self, html, status_id):
        html = html.replace("\n", '')
        html = html.replace('\'', '"')

        fd = open('/tmp/turpial-update-column.html', 'w')
        fd.write(html.encode('ascii', 'ignore'))
        fd.close()

        cmd = """appendStatus('%s', '%s')""" % (html, status_id)
        self.execute_javascript(cmd)

    def sync_timestamps(self, statuses):
        for status in statuses:
            new_timestamp = self.base.humanize_timestamp(status.timestamp)
            cmd = """updateTimestamp('%s', '%s')""" % (status.id_, new_timestamp)
            self.execute_javascript(cmd)

    def clear_new_marks(self):
        self.execute_javascript("clearNewMarks()")


########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-

# Qt util widgets for Turpial

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QSize

from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QToolButton
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QProgressBar

class BarLoadIndicator(QProgressBar):
    def __init__(self, maximum_height=6):
        QProgressBar.__init__(self)
        self.setMinimum(0)
        self.setMaximum(0)
        if maximum_height is not None:
            if maximum_height < 6:
                maximum_height = 6
            self.setMaximumHeight(maximum_height)
        self.setTextVisible(False)

class ImageButton(QToolButton):
    def __init__(self, base, image, tooltip, borders=False):
        QToolButton.__init__(self)
        self.base = base
        self.change_icon(image)
        self.setToolTip(tooltip)
        self.setMaximumSize(24, 24)
        if not borders:
            self.setStyleSheet("QToolButton { border: none; outline: none; }")

    def change_icon(self, image):
        self.setIcon(QIcon(self.base.get_image_path(image)))
        self.setIconSize(QSize(24, 24))

class StyledLabel(QLabel):
    def __init__(self, text, bg_color='#ccc', color='#000'):
        QLabel.__init__(self)
        style = "background-color:%s; color:%s; font-size:10px; border-radius:3px;" % (bg_color,
                                                                                       color)
        self.setText(text)
        self.setContentsMargins(5, 0, 5, 0)
        self.setStyleSheet("QLabel { %s }" % style)
        self.setMinimumHeight(22)

class HLine(QFrame):
    def __init__(self, minimum_height=20):
        QFrame.__init__(self)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        if minimum_height:
            self.setMinimumHeight(20)

class VLine(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setMinimumWidth(5)

class ToggleButton(QToolButton):
    def __init__(self, base, image, text=None, tooltip=None):
        QToolButton.__init__(self)
        icon = QIcon(base.get_image_path(image))
        self.setIcon(icon)
        self.setCheckable(True)
        if text:
            self.setText(text)
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.setMaximumHeight(24)
        else:
            self.setMaximumSize(24, 24)

        if tooltip:
            self.setToolTip(tooltip)

class ModalDialog(QDialog):
    def __init__(self, width, height):
        QDialog.__init__(self)
        self.setFixedSize(width, height)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setModal(True)

    def is_accepted(self):
        return self.result() == QDialog.Accepted

class Window(QWidget):
    def __init__(self, base, title):
        QWidget.__init__(self)
        self.setWindowTitle(title)
        self.base = base

    def __center_on_parent(self):
        geo = self.base.geometry()
        cx = geo.x() + (geo.width() / 2)
        cy = geo.y() + (geo.height() / 2)
        geo2 = self.geometry()
        fx = cx - (geo2.width() / 2)
        fy = cy - (geo2.height() / 2)
        self.setGeometry(fx,fy, geo2.width(), geo2.height())

    def show(self):
        QWidget.show(self)
        self.__center_on_parent()

class ErrorLabel(QLabel):
    def __init__(self):
        QLabel.__init__(self)

        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        self.setStyleSheet("QLabel {color: #f00}")

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-

# Qt Worker for Turpial

import os
import Queue

from PyQt4.QtCore import QThread
from PyQt4.QtCore import pyqtSignal

from turpial.ui.base import BROADCAST_ACCOUNT

from libturpial.api.core import Core
from libturpial.api.models.status import Status
from libturpial.api.models.column import Column
from libturpial.common.tools import get_account_id_from, get_column_slug_from

class CoreWorker(QThread):

    ready = pyqtSignal(object)
    status_updated = pyqtSignal(object, str)
    status_broadcasted = pyqtSignal(object)
    status_repeated = pyqtSignal(object, str, str, str)
    status_deleted = pyqtSignal(object, str, str, str)
    status_pushed_to_queue = pyqtSignal(str)
    status_poped_from_queue = pyqtSignal(object)
    status_deleted_from_queue = pyqtSignal()
    queue_cleared = pyqtSignal()
    status_posted_from_queue = pyqtSignal(object, str, str)
    message_deleted = pyqtSignal(object, str, str, str)
    message_sent = pyqtSignal(object, str)
    column_updated = pyqtSignal(object, tuple)
    account_saved = pyqtSignal(str)
    account_loaded = pyqtSignal()
    account_deleted = pyqtSignal()
    column_saved = pyqtSignal(str)
    column_deleted = pyqtSignal(str)
    status_marked_as_favorite = pyqtSignal(object, str, str, str)
    status_unmarked_as_favorite = pyqtSignal(object, str, str, str)
    fetched_user_profile = pyqtSignal(object, str)
    urls_shorted = pyqtSignal(object)
    media_uploaded = pyqtSignal(object)
    friends_list_updated = pyqtSignal()
    user_muted = pyqtSignal(str)
    user_unmuted = pyqtSignal(str)
    user_blocked = pyqtSignal(object)
    user_reported_as_spam = pyqtSignal(object)
    user_followed = pyqtSignal(object, str)
    user_unfollowed = pyqtSignal(object, str)
    exception_raised = pyqtSignal(object)
    status_from_conversation = pyqtSignal(object, str, str)
    fetched_profile_image = pyqtSignal(object)
    fetched_avatar = pyqtSignal(object, str)
    fetched_image_preview = pyqtSignal(object)
    cache_deleted = pyqtSignal()

    ERROR = -1
    LOADING = 0
    READY = 1

    def __init__(self):
        QThread.__init__(self)
        self.queue = Queue.Queue()
        self.exit_ = False
        self.status = self.LOADING
        #self.core = Core()

        #self.queue_path = os.path.join(self.core.config.basedir, 'queue')
        #if not os.path.isfile(self.queue_path):
        #    open(self.queue_path, 'w').close()
        self.core = None
        self.restart()

    #def __del__(self):
    #    self.wait()

    def restart(self):
        self.register(self.login, (), self.__after_login, None)

    def __get_from_queue(self, index=0):
        lines = open(self.queue_path).readlines()
        if not lines:
            return None

        row = lines[index].strip()
        account_id, message = row.split("\1")
        del lines[index]

        open(self.queue_path, 'w').writelines(lines)
        status = Status()
        status.account_id = account_id
        status.text = self.__unescape_queue_message(message)
        return status

    def __get_column_num_from_id(self, column_id):
        column_key = None
        for i in range(1, len(self.get_registered_columns()) + 1):
            column_num = "column%s" % i
            stored_id = self.core.config.read('Columns', column_num)
            if stored_id == column_id:
                column_key = column_num
            else:
                i += 1
        return column_key

    def __escape_queue_message(self, message):
        message = message.replace('\n', '\0')
        return message

    def __unescape_queue_message(self, message):
        message = message.replace('\0', '\n')
        return message

    #================================================================
    # Core methods
    #================================================================

    def login(self):
        self.core = Core()
        # FIXME: Dirty hack that must be fixed in libturpial
        self.core.config.cfg.optionxform = str
        self.queue_path = os.path.join(self.core.config.basedir, 'queue')
        if not os.path.isfile(self.queue_path):
            open(self.queue_path, 'w').close()

    def get_update_interval(self):
        return self.core.get_update_interval()

    def get_statuses_per_column(self):
        return self.core.get_max_statuses_per_column()

    def get_proxy_configuration(self):
        return self.core.config.read_section('Proxy')

    def get_socket_timeout(self):
        return self.core.get_socket_timeout()

    # Custom config
    def get_minimize_on_close(self):
        return self.core.config.read('General', 'minimize-on-close', boolean=True)

    def set_minimize_on_close(self, value):
        self.core.config.read('General', 'minimize-on-close', value)

    def get_show_user_avatars(self):
        return self.core.config.read('Advanced', 'show-user-avatars', boolean=True)

    def get_sound_on_login(self):
        return self.core.config.read('Sounds', 'login', boolean=True)

    def get_sound_on_updates(self):
        return self.core.config.read('Sounds', 'updates', boolean=True)

    def get_notify_on_updates(self):
        return self.core.config.read('Notifications', 'updates', boolean=True)

    def get_notify_on_actions(self):
        return self.core.config.read('Notifications', 'actions', boolean=True)

    def get_window_size(self):
        size = self.core.config.read('Window', 'size')
        return int(size.split(',')[0]), int(size.split(',')[1])

    def set_window_size(self, width, height):
        window_size = "%s,%s" % (width, height)
        self.core.config.write('Window', 'size', window_size)

    def get_default_browser(self):
        return self.core.config.read('Browser', 'cmd')

    def get_queue_interval(self):
        return int(self.core.config.read('General', 'queue-interval'))

    def get_inline_preview(self):
        return self.core.config.read('General', 'inline-preview', boolean=True)

    def set_inline_preview(self, value):
        self.core.config.write('General', 'inline-preview', value)

    def get_show_images_in_browser(self):
        return self.core.config.read('General', 'show-images-in-browser', boolean=True)

    def set_show_images_in_browser(self, value):
        self.core.config.write('General', 'show-images-in-browser', value)

    def get_update_interval_per_column(self, column_id):
        return int(self.core.config.read('Updates', column_id))

    def set_update_interval_per_column(self, column_id, interval):
        self.core.config.write('Updates', column_id, interval)

    def get_show_notifications_in_column(self, column_id):
        return self.core.config.read('Notifications', column_id, boolean=True)

    def set_show_notifications_in_column(self, column_id, value):
        self.core.config.write('Notifications', column_id, 'on' if value else 'off')

    def get_cache_size(self):
        return self.core.get_cache_size()

    def delete_cache(self):
        self.core.delete_cache()

    def read_config(self):
        return self.core.get_config()

    def update_config(self, new_config):
        for section in new_config:
            for option in new_config[section]:
                self.core.write_config_value(section, option, new_config[section][option])

    def write_config_option(self, section, option, value):
        self.core.config.write(section, option, value)

    def read_section(self, section):
        return self.core.config.read_section(section)

    def write_section(self, section, items):
        self.core.config.write_section(section, items)

    def add_config_option(self, section, option, default_value):
        self.core.register_new_config_option(section, option, default_value)

    # TODO: Implement this in libturpial
    def remove_config_option(self, section, option):
        if section in self.core.config._ConfigBase__config:
            if option in self.core.config._ConfigBase__config[section]:
                del self.core.config._ConfigBase__config[section][option]

        if section in self.core.config.extra_sections:
            if option in self.core.config.extra_sections[section]:
                del self.core.config.extra_sections[section][option]

        self.core.config.cfg.remove_option(section, option)

        _fd = open(self.core.config.configpath, 'w')
        self.core.config.cfg.write(_fd)
        _fd.close()

    # TODO: Implement this in libturpial
    def remove_section(self, section):
        if section in self.core.config._ConfigBase__config:
            del self.core.config._ConfigBase__config[section]

        if section in self.core.config.extra_sections:
            del self.core.config.extra_sections[section]

        self.core.config.cfg.remove_section(section)

        _fd = open(self.core.config.configpath, 'w')
        self.core.config.cfg.write(_fd)
        _fd.close()

    def sanitize_search_columns(self):
        i = 1
        columns = []
        while True:
            column_num = "column%s" % i
            column_id = self.core.config.read('Columns', column_num)
            if column_id is None:
                break
            elif column_id is not None and column_id.find('search:') >= 0:
                column_id = column_id.replace('search:', 'search>')
                self.core.config.write('Columns', column_num, column_id)
            columns.append(column_id)
            i += 1
        return columns

    def get_shorten_url_service(self):
        return self.core.get_shorten_url_service()

    def get_upload_media_service(self):
        return self.core.get_upload_media_service()

    def get_available_columns(self):
        return self.core.available_columns()

    def get_all_accounts(self):
        return self.core.registered_accounts()

    def get_all_columns(self):
        return self.core.all_columns()

    def get_registered_accounts(self):
        return self.core.registered_accounts()

    def get_available_short_url_services(self):
        return self.core.available_short_url_services()

    def get_available_upload_media_services(self):
        return self.core.available_upload_media_services()

    def get_registered_columns(self):
        return self.core.registered_columns_by_order()

    def is_muted(self, username):
        return self.core.is_muted(username)

    def load_friends_list(self):
        return self.core.load_all_friends_list()

    def save_account(self, account):
        account_id = self.core.register_account(account)
        self.__after_save_account(account_id)

    # FIXME: Remove this after implement this in libturpial
    def load_account(self, account_id, trigger_signal=True):
        if trigger_signal:
            self.register(self.core.account_manager.load, (account_id),
                self.__after_load_account)
        else:
            self.core.account_manager.load(account_id)
            self.__after_load_account()

    def delete_account(self, account_id):
        # FIXME: Implement try/except
        for col in self.get_registered_columns():
            if col.account_id == account_id:
                self.delete_column(col.id_)
        self.core.unregister_account(str(account_id), True)
        self.__after_delete_account()

    def save_column(self, column_id):
        reg_column_id = self.core.register_column(column_id)
        notify = 'on' if self.get_notify_on_updates() else 'off'
        self.write_config_option('Notifications', column_id, notify)
        self.write_config_option('Updates', column_id, self.get_update_interval())
        self.__after_save_column(reg_column_id)

    def delete_column(self, column_id):
        deleted_column = self.core.unregister_column(column_id)
        self.remove_config_option('Notifications', column_id)
        self.remove_config_option('Updates', column_id)
        self.__after_delete_column(column_id)

    def get_column_statuses(self, column, last_id):
        count = self.core.get_max_statuses_per_column()
        self.register(self.core.get_column_statuses, (column.account_id,
            column.slug, count, last_id), self.__after_update_column,
            (column, count))

    def update_status(self, account_id, message, in_reply_to_id=None):
        self.register(self.core.update_status, (account_id,
            message, in_reply_to_id), self.__after_update_status, account_id)

    def update_status_with_media(self, account_id, message, media, in_reply_to_id=None):
        if self.get_upload_media_service() != 'pic.twitter.com':
            media_url = self.core.upload_media(account_id, media)
            message = "%s %s" % (message, media_url)
            self.register(self.core.update_status, (account_id,
                message, in_reply_to_id), self.__after_update_status, account_id)
        else:
            self.register(self.core.update_status, (account_id,
                message, in_reply_to_id, media), self.__after_update_status, account_id)

    def broadcast_status(self, accounts, message):
        self.register(self.core.broadcast_status, (accounts, message),
            self.__after_broadcast_status)

    def repeat_status(self, column_id, account_id, status_id):
        self.register(self.core.repeat_status, (account_id, status_id),
            self.__after_repeat_status, (column_id, account_id, status_id))

    def delete_status(self, column_id, account_id, status_id):
        self.register(self.core.destroy_status, (account_id, status_id),
            self.__after_delete_status, (column_id, account_id, status_id))

    def delete_direct_message(self, column_id, account_id, status_id):
        self.register(self.core.destroy_direct_message, (account_id, status_id),
            self.__after_delete_direct_message, (column_id, account_id, status_id))

    def send_direct_message(self, account_id, username, message):
        self.register(self.core.send_direct_message, (account_id, username,
            message), self.__after_send_direct_message, account_id)

    def mark_status_as_favorite(self, column_id, account_id, status_id):
        self.register(self.core.mark_status_as_favorite, (account_id, status_id),
            self.__after_mark_status_as_favorite, (column_id, account_id, status_id))

    def unmark_status_as_favorite(self, column_id, account_id, status_id):
        self.register(self.core.unmark_status_as_favorite, (account_id, status_id),
            self.__after_unmark_status_as_favorite, (column_id, account_id, status_id))

    def get_user_profile(self, account_id, user_profile=None):
        self.register(self.core.get_user_profile, (account_id, user_profile),
            self.__after_get_user_profile, account_id)

    def short_urls(self, message):
        self.register(self.core.short_url_in_message, (message),
            self.__after_short_urls)

    def upload_media(self, account_id, filepath):
        self.register(self.core.upload_media, (account_id, filepath),
            self.__after_upload_media)

    def get_friends_list(self):
        self.register(self.core.get_all_friends_list, None,
            self.__after_get_friends_list)

    def mute(self, username):
        self.register(self.core.mute, username, self.__after_mute_user)

    def unmute(self, username):
        self.register(self.core.unmute, username, self.__after_unmute_user)

    def block(self, account_id, username):
        self.register(self.core.block, (account_id, username), self.__after_block_user)

    def report_as_spam(self, account_id, username):
        self.register(self.core.report_as_spam, (account_id, username),
            self.__after_report_user_as_spam)

    def follow(self, account_id, username):
        self.register(self.core.follow, (account_id, username),
            self.__after_follow_user, account_id)

    def unfollow(self, account_id, username):
        self.register(self.core.unfollow, (account_id, username),
            self.__after_unfollow_user, account_id)

    def get_status_from_conversation(self, account_id, status_id, column_id, status_root_id):
        self.register(self.core.get_single_status, (account_id, status_id),
            self.__after_get_status_from_conversation, (column_id, status_root_id))

    def get_profile_image(self, account_id, username):
        self.register(self.core.get_profile_image, (account_id, username, False),
            self.__after_get_profile_image)

    def get_avatar_from_status(self, status):
        self.register(self.core.get_status_avatar, (status),
            self.__after_get_avatar_from_status, status.username)

    def get_image_preview(self, preview_service, url):
        self.register(preview_service.do_service, (url),
            self.__after_get_image_preview)

    def push_status_to_queue(self, account_id, message):
        fd = open(self.queue_path, 'a+')
        message = self.__escape_queue_message(message)
        row = "%s\1%s\n" % (account_id, message)
        fd.write(row.encode('utf-8'))
        fd.close()
        self.__after_push_status_to_queue(account_id)

    def pop_status_from_queue(self):
        status = self.__get_from_queue()
        self.__after_pop_status_from_queue(status)

    def delete_status_from_queue(self, index=0):
        status = self.__get_from_queue(index)
        self.__after_delete_status_from_queue()

    def list_statuses_queue(self):
        statuses = []
        lines = []
        if os.path.exists(self.queue_path):
            lines = open(self.queue_path).readlines()
        for line in lines:
            account_id, message = line.strip().split("\1")
            status = Status()
            status.account_id = account_id
            status.text = self.__unescape_queue_message(message)
            statuses.append(status)
        return statuses

    def clear_statuses_queue(self):
        open(self.queue_path, 'w').writelines([])
        self.__after_clear_queue()

    def post_status_from_queue(self, account_id, message):
        if account_id == BROADCAST_ACCOUNT:
            self.register(self.core.broadcast_status, (None, message),
                self.__after_post_status_from_queue, (account_id, message))
        else:
            self.register(self.core.update_status, (account_id, message),
                self.__after_post_status_from_queue, (account_id, message))

    def delete_cache(self):
        self.register(self.core.delete_cache, None, self.__after_delete_cache)

    def list_filters(self):
        return self.core.list_filters()

    def save_filters(self, filters):
        self.core.save_filters(filters)

    def restore_config(self):
        self.core.delete_current_config()

    def filter_statuses(self, statuses):
        return self.core.filter_statuses(statuses)

    #================================================================
    # Callbacks
    #================================================================

    def __after_login(self, response):
        self.ready.emit(response)

    def __after_save_account(self, account_id):
        self.account_saved.emit(account_id)

    def __after_load_account(self, response=None):
        self.account_loaded.emit()

    def __after_delete_account(self):
        self.account_deleted.emit()

    def __after_save_column(self, column_id):
        self.column_saved.emit(column_id)

    def __after_delete_column(self, column_id):
        self.column_deleted.emit(column_id)

    def __after_update_column(self, response, data):
        self.column_updated.emit(response, data)

    def __after_update_status(self, response, account_id):
        self.status_updated.emit(response, account_id)

    def __after_broadcast_status(self, response):
        self.status_broadcasted.emit(response)

    def __after_repeat_status(self, response, args):
        column_id = args[0]
        account_id = args[1]
        status_id = args[2]
        self.status_repeated.emit(response, column_id, account_id, status_id)

    def __after_delete_status(self, response, args):
        column_id = args[0]
        account_id = args[1]
        status_id = args[2]
        self.status_deleted.emit(response, column_id, account_id, status_id)

    def __after_delete_direct_message(self, response, args):
        column_id = args[0]
        account_id = args[1]
        status_id = args[2]
        self.message_deleted.emit(response, column_id, account_id, status_id)

    def __after_send_direct_message(self, response, account_id):
        self.message_sent.emit(response, account_id)

    def __after_mark_status_as_favorite(self, response, args):
        column_id = args[0]
        account_id = args[1]
        status_id = args[2]
        self.status_marked_as_favorite.emit(response, column_id, account_id, status_id)

    def __after_unmark_status_as_favorite(self, response, args):
        column_id = args[0]
        account_id = args[1]
        status_id = args[2]
        self.status_unmarked_as_favorite.emit(response, column_id, account_id, status_id)

    def __after_get_user_profile(self, response, account_id):
        self.fetched_user_profile.emit(response, account_id)

    def __after_short_urls(self, response):
        self.urls_shorted.emit(response)

    def __after_upload_media(self, response):
        self.media_uploaded.emit(response)

    def __after_get_friends_list(self, response):
        self.friends_list_updated.emit()

    def __after_mute_user(self, response):
        self.user_muted.emit(response)

    def __after_unmute_user(self, response):
        self.user_unmuted.emit(response)

    def __after_block_user(self, response):
        self.user_blocked.emit(response)

    def __after_report_user_as_spam(self, response):
        self.user_reported_as_spam.emit(response)

    def __after_follow_user(self, response, account_id):
        self.user_followed.emit(response, account_id)

    def __after_unfollow_user(self, response, account_id):
        self.user_unfollowed.emit(response, account_id)

    def __after_get_status_from_conversation(self, response, args):
        column_id = args[0]
        status_root_id = args[1]
        self.status_from_conversation.emit(response, column_id, status_root_id)

    def __after_get_profile_image(self, response):
        self.fetched_profile_image.emit(response)

    def __after_get_avatar_from_status(self, response, args):
        username = args
        self.fetched_avatar.emit(response, username)

    def __after_get_image_preview(self, response):
        self.fetched_image_preview.emit(response)

    def __after_push_status_to_queue(self, account_id):
        self.status_pushed_to_queue.emit(account_id)

    def __after_pop_status_from_queue(self, status):
        self.status_poped_from_queue.emit(status)

    def __after_delete_status_from_queue(self):
        self.status_deleted_from_queue.emit()

    def __after_clear_queue(self):
        self.queue_cleared.emit()

    def __after_post_status_from_queue(self, response, args):
        account_id = args[0]
        message = args[1]
        self.status_posted_from_queue.emit(response, account_id, message)

    def __after_delete_cache(self, response=None):
        self.cache_deleted.emit()

    #================================================================
    # Worker methods
    #================================================================

    def register(self, funct, args, callback, user_data=None):
        self.queue.put((funct, args, callback, user_data))

    def quit(self):
        self.exit_ = True

    def run(self):
        while not self.exit_:
            try:
                req = self.queue.get(True, 0.3)
            except Queue.Empty:
                continue
            except:
                continue

            (funct, args, callback, user_data) = req

            try:
                if type(args) == tuple:
                    rtn = funct(*args)
                elif args:
                    rtn = funct(args)
                else:
                    rtn = funct()
            except Exception, e:
                #self.exception_raised.emit(e)
                #continue
                rtn = e

            if callback:
                if user_data:
                    callback(rtn, user_data)
                else:
                    callback(rtn)



########NEW FILE########
__FILENAME__ = sound
# -*- coding: utf-8 -*-

# Base class for Turpial sound module using Qt"""

import os

SYSTEM = None

try:
    import gst
    import gobject
    gobject.threads_init()
    SYSTEM = 'gst'
except:
    try:
        from PyQt4.phonon import Phonon
        SYSTEM = 'phonon'
    except Exception, e:
        print e

print "DEBUG::Using %s as sound system" % SYSTEM

class SoundSystem:
    def __init__(self, sounds_path, disable=False):
        self.sounds_path = sounds_path
        self.activate()
        self.disable = disable
        self.sounds = {}

        if SYSTEM == 'gst':
            self.sounds['startup'] = GstSound(os.path.join(self.sounds_path, 'startup.ogg'))
            self.sounds['notification_1'] = GstSound(os.path.join(self.sounds_path, 'notification-1.ogg'))
            self.sounds['notification_2'] = GstSound(os.path.join(self.sounds_path, 'notification-2.ogg'))
        elif SYSTEM == 'phonon':
            self.sounds['startup'] = QtSound(os.path.join(self.sounds_path, 'startup.ogg'))
            self.sounds['notification_1'] = QtSound(os.path.join(self.sounds_path, 'notification-1.ogg'))
            self.sounds['notification_2'] = QtSound(os.path.join(self.sounds_path, 'notification-2.ogg'))
        else:
            self.sounds['startup'] = DummySound()
            self.sounds['notification_1'] = DummySound()
            self.sounds['notification_2'] = DummySound()

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def startup(self):
        self.sounds['startup'].play()

    def updates(self):
        self.sounds['notification_1'].play()

    def notification(self):
        self.sounds['notification_2'].play()


class GstSound:
    def __init__(self, file_path):
        self.player = gst.element_factory_make("playbin2", "player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.__on_gst_message)
        self.player.set_property("uri", "file://" + file_path)

    def __on_gst_message(self, bus, message):
        type_ = message.type
        if type_ == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif type_ == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()

    def play(self):
        self.player.set_state(gst.STATE_PLAYING)


class QtSound:
    def __init__(self, file_path):
        self.sound = Phonon.createPlayer(Phonon.MusicCategory, Phonon.MediaSource(file_path))

    def play(self):
        self.sound.play()

class DummySound:
    def __init__(self):
        pass

    def play(self):
        pass

########NEW FILE########
__FILENAME__ = daemon
#!/usr/bin/env python

# -*- coding: utf-8 -*-

# TurpialUnityDaemon a separate process to launch to use unity API without conflicts
#
# Author: Andrea Stagi (aka 4ndreaSt4gi)
# May 22, 2012

try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import Unity, GObject, Dbusmenu
    UNITY_SUPPORT = True
except Exception, e:
    print 'Could not load all modules for Unity support: %s' % e
    print 'Disabling Unity support'
    UNITY_SUPPORT = False

import os
import sys
import time
import atexit
import tempfile
from signal import SIGTERM

BUS_NAME = "org.turpial.ve"
CONTROLLER_OBJ_PATH = "/org/turpial/ve/turpialunity"

class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        pass

if UNITY_SUPPORT:
    class TurpialUnity(dbus.service.Object):

        def __init__(self, loop):
            self.loop = loop
            bus = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
            dbus.service.Object.__init__(self, bus, CONTROLLER_OBJ_PATH)
            self.launcher = Unity.LauncherEntry.get_for_desktop_id("turpial.desktop")
            self.ql = Dbusmenu.Menuitem.new()

        @dbus.service.method(BUS_NAME)
        def set_count(self, count):
            self.launcher.set_property("count", count)

        @dbus.service.method(BUS_NAME)
        def set_count_visible(self, visible):
            self.launcher.set_property("count_visible", visible)

        @dbus.service.method(BUS_NAME)
        def add_quicklist_button(self, label, visible):

            def _pressCallback(arg1, arg2, arg3):
                self.buttonPressed(label)

            item = Dbusmenu.Menuitem.new()
            item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, label)
            item.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, visible)
            item.connect("item-activated", _pressCallback, None)
            self.ql.child_append(item)

        @dbus.service.method(BUS_NAME)
        def add_quicklist_checkbox(self, label, visible, status):

            def _check_callback(menuitem, a, b):
                if menuitem.property_get_int (Dbusmenu.MENUITEM_PROP_TOGGLE_STATE) == Dbusmenu.MENUITEM_TOGGLE_STATE_CHECKED:
                    menuitem.property_set_int (Dbusmenu.MENUITEM_PROP_TOGGLE_STATE, Dbusmenu.MENUITEM_TOGGLE_STATE_UNCHECKED)
                    self.checkChanged(label, False)
                else:
                    menuitem.property_set_int (Dbusmenu.MENUITEM_PROP_TOGGLE_STATE, Dbusmenu.MENUITEM_TOGGLE_STATE_CHECKED)
                    self.checkChanged(label, True)

            check = Dbusmenu.Menuitem.new ()
            check.property_set (Dbusmenu.MENUITEM_PROP_LABEL, label)
            check.property_set (Dbusmenu.MENUITEM_PROP_TOGGLE_TYPE, Dbusmenu.MENUITEM_TOGGLE_CHECK)
            if status:
                check.property_set_int (Dbusmenu.MENUITEM_PROP_TOGGLE_STATE, Dbusmenu.MENUITEM_TOGGLE_STATE_CHECKED)
            else:
                check.property_set_int (Dbusmenu.MENUITEM_PROP_TOGGLE_STATE, Dbusmenu.MENUITEM_TOGGLE_STATE_UNCHECKED)
            check.connect (Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, _check_callback, None)
            check.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, visible)
            self.ql.child_append(check)

        @dbus.service.method(BUS_NAME)
        def show_menu(self):
            self.launcher.set_property("quicklist", self.ql)

        @dbus.service.method(BUS_NAME)
        def clean_quicklist(self):
            pass

        @dbus.service.method(BUS_NAME)
        def quit(self):
            self.loop.quit()

        @dbus.service.signal(BUS_NAME)
        def buttonPressed(self, signal):
            pass

        def checkChanged(self, signal, value):
            pass


class TurpialUnityDaemon(Daemon):
    def __init__(self):
        pid_path = os.path.abspath(os.path.join(tempfile.gettempdir(), 'turpial-daemon.pid'))
        stderr_path = os.path.abspath(os.path.join(tempfile.gettempdir(), 'turpial-daemon.log'))
        Daemon.__init__(self, pid_path, stderr=stderr_path)
        self.mainloop = None
        self.service = None

    def stop(self):
        Daemon.stop(self)

    def run(self):
        DBusGMainLoop(set_as_default=True)
        self.mainloop = GObject.MainLoop()
        self.service = TurpialUnity(self.mainloop)
        self.mainloop.run()

def main():
    if len(sys.argv) != 2:
        print "Usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

    try:
        if UNITY_SUPPORT:
            daemon = TurpialUnityDaemon()
        else:
            sys.exit(-1)
    except Exception, e:
        print "Error running the Unity Daemon: %s" % e
        sys.exit(-1)

    cmd = sys.argv[1]
    if cmd == 'start':
        daemon.start()
    elif cmd == 'stop':
        daemon.stop()
    elif cmd == 'restart':
        daemon.restart()
    else:
        print "Unknown command"
        sys.exit(2)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = unitylauncher
# -*- coding: utf-8 -*-

# UnityLauncher to integrate Turpial in Unity
#
# Author: Andrea Stagi (aka 4ndreaSt4gi)
# Feb 22, 2012

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    import_success = True
except ImportError:
    import_success = False

BUS_NAME = "org.turpial.ve"
CONTROLLER_OBJ_PATH = "/org/turpial/ve/turpialunity"

class NoneUnityDBusController(object):

    def __init__ (self):
        pass

    def onSignalReceived(self, label_selected):
        pass

    def set_count(self, count):
        pass

    def increment_count(self, count):
        pass

    def get_count(self):
        pass

    def set_count_visible(self, visible):
        pass

    def add_quicklist_button(self, callback, label, visible):
        pass

    def add_quicklist_checkbox(self, callback, label, visible, status):
        pass

    def is_supported(self):
        return False

    def show_menu(self):
        pass

    def quit(self):
        pass

class UnityLauncher(object):

    def __init__ (self):
        self.dbus_loop = DBusGMainLoop(set_as_default=True)
        self.count = 0
        self.callbacks = {}
        self.bus = dbus.SessionBus(mainloop=self.dbus_loop)
        self.service = self.bus.get_object(BUS_NAME, CONTROLLER_OBJ_PATH)
        self.service.connect_to_signal("buttonPressed", self.onButtonPressed)
        self.service.connect_to_signal("checkChanged", self.onCheckChanged)

    def onButtonPressed(self, label_selected):
        self.callbacks[label_selected]()

    def onCheckChanged(self, label_selected, value):
        self.callbacks[label_selected](value)

    def set_count(self, count):
        self.count = count
        self.service.set_count(self.count)

    def increment_count(self, count):
        self.count += count
        self.set_count(self.count)

    def get_count(self):
        return self.count

    def set_count_visible(self, visible):
        self.service.set_count_visible(visible)

    def add_quicklist_button(self, callback, label, visible):
        self.service.add_quicklist_button(label, visible)
        self.callbacks[label] = callback

    def add_quicklist_checkbox(self, callback, label, visible, status):
        self.service.add_quicklist_checkbox(label, visible, status)
        self.callbacks[label] = callback

    def is_supported(self):
        return True

    def show_menu(self):
        self.service.show_menu()

    def quit(self):
        self.service.quit()
        self.bus.close()

class UnityLauncherFactory:

    def create(self):
        if not import_success:
            return NoneUnityDBusController()
        try:
            return UnityLauncher()
        except dbus.exceptions.DBusException:
            return NoneUnityDBusController()

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

# Utilities for Turpial interfaces

import xml.sax.saxutils as saxutils

from libturpial.common.tools import *

try:
    # TODO: Implement this function for other platforms
    if detect_os() == OS_LINUX:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        libc.prctl(15, 'turpial', 0, 0)
except ImportError, exc:
    print exc

INTERFACES = {}
DEFAULT_INTERFACE = None

# Load gtk3
#try:
#    from turpial.ui.gtk.main import Main as _GTK
#    INTERFACES['gtk'] = _GTK
#    DEFAULT_INTERFACE = DEFAULT_INTERFACE or 'gtk'
#except ImportError, exc:
#    print 'Could not initialize GTK interface.'
#    print exc

# Load qt
try:
    from turpial.ui.qt.main import Main as _QT
    INTERFACES['qt'] = _QT
    DEFAULT_INTERFACE = DEFAULT_INTERFACE or 'qt'
except ImportError, exc:
    print 'Could not initialize QT interface.'
    print exc

# Load cmd
try:
    from turpial.ui.cmd.main import Main as _CMD
    INTERFACES['cmd'] = _CMD
    DEFAULT_INTERFACE = DEFAULT_INTERFACE or 'cmd'
except ImportError, exc:
    print 'Could not initialize CMD interface.'
    print exc

def available_interfaces():
    return ', '.join(INTERFACES.keys())

def unescape_text(text):
    text = saxutils.unescape(text)
    text = text.replace('&quot;', '"')
    text = text.replace('\r\n', ' ')
    text = text.replace('\n', ' ')
    return text

########NEW FILE########
