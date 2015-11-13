__FILENAME__ = common
# -*- coding: utf-8 -*-

import os
import sys

import shelve
import abc
import time

from clint.textui import colored


def output(message, color='white', text_only=False):
    if text_only:
        return str(getattr(colored, color)(message))
    else:
        sys.stdout.write(str(getattr(colored, color)(message)))


class StashedItem():
    """
    Incapsulate all operations with single item from Stash
    """
    def __init__(self, elem, index=None, numbered=False):
        self.elem = elem
        self.value = elem['value']
        if 'tags' in elem:
            self.tags = elem['tags']
        else:
            self.tags = []
        self.is_list = isinstance(elem['value'], list)
        if (index is not None and not self.is_list) or len(elem['value']) <= index:
            raise IndexError
        self.numbered = numbered
        self.index = index

    def get_value(self):
        return self.elem['value'] if not self.index else \
            self.elem['value'][self.index] if not 'marked' in self.elem['meta'] else self.elem['value'][self.index][0]

    def get_tags(self):
        if 'tags' in self.elem:
            return self.elem['tags']
        else:
            return []


    def __repr__(self):
        if self.is_list:
            if 'marked' in self.elem['meta']:
                # it will be uncommented after implementing marked lists
                #result = self.__assemble_marked_list()
                result = self.__assemble_unmarked_list()
            else:
                result = self.__assemble_unmarked_list()
        else:
            result = self.elem['value']
        return '%s\n' % result

    def __assemble_marked_list(self):
        result = []
        template = '{mark} {data}'
        for item in self.elem['value']:
            mark = '+' if item[1] else '-'
            result.append(template.format(mark=mark, data=item[0]))
        return self.list_to_string(result, self.numbered)

    def __assemble_unmarked_list(self):
        result = []
        for item in self.elem['value']:
            result.append(item)
        return self.list_to_string(result, self.numbered)

    @staticmethod
    def list_to_string(items, is_numbered):
        if is_numbered:
            return '\n'.join(['{}. {}'.format(n+1, item) for n, item in enumerate(items)])
        else:
            return '\n'.join(items)


class AbstractStorage(object):
    # todo: update methods signature
    """
    Here will be a docstring
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_connection(self, db):
        pass

    @abc.abstractmethod
    def add(self, key, value, tags):
        """Returns created item as StashedItem"""

    @abc.abstractmethod
    def update(self, item_name, value, index=None):
        """Returns updated item as StashedItem"""

    @abc.abstractmethod
    def delete(self, item_name, index=None):
        """Returns Boolean"""

    @abc.abstractmethod
    def get(self, item_name, index=None):
        """Returns item as  StashedItem"""

    @abc.abstractmethod
    def get_all(self):
        pass

    @abc.abstractmethod
    def is_list(self, item_name):
        pass

    @abc.abstractmethod
    def exist(self, item_name):
        pass

    @abc.abstractmethod
    def get_database_data(self):
        """
        Return whole db data as python dict for sync
        """
        pass


class NotListException(Exception):
    pass


class ShelveStorage(AbstractStorage):
    """
    Storage implementation for work with python shelve library
    """
    DBFILE = os.path.join(os.path.expanduser('~'), '.stash', 'stash.db')

    def __init__(self, db_file=None):
        self.DBFILE = db_file if db_file is not None else self.DBFILE
        path_to_dir = os.path.join('/', *self.DBFILE.split('/')[1:-1])
        if not os.path.exists(path_to_dir):
            os.makedirs(path_to_dir, 0755)
        self.connection = self.get_connection(self.DBFILE)
        if not 'storage' in self.connection:
            self.connection['storage'] = {}
        if not 'last_sync' in self.connection:
            self.connection['last_sync'] = 0
        if not 'last_update' in self.connection:
            self.connection['last_update'] = 0
        self.db = self.connection['storage']
        self.last_sync = self.connection['last_sync']
        self.last_update = self.connection['last_update']

    def get_connection(self, db):
        return shelve.open(db, writeback=True)

    def update(self, item_name, value, tags, index=None, overwrite=False):
        if index is not None:
            index -= 1
            item = self.db[item_name]['value']
            if not isinstance(item, list):
                raise NotListException
            elif index > len(item):
                raise IndexError
            if index == len(item):
                self.db[item_name]['value'].append(value)
            else:
                self.db[item_name]['value'][index] = value
        else:
            if isinstance(self.db[item_name]['value'], list) and not overwrite:
                self.db[item_name]['value'].append(value)
                self.db[item_name]['tags'].append(tags)
            else:
                self.db[item_name]['value'] = value
                self.db[item_name]['tags'] = tags
        self.db[item_name]['updated'] = int(time.time())
        #self.db[item_name]['tags'] = tags
        self.last_update = int(time.time())
        return StashedItem(self.db[item_name], index)

    def delete(self, item_name, index=None):
        if index is not None:
            index -= 1
            if not isinstance(self.db[item_name]['value'], list):
                raise NotListException
            self.db[item_name]['value'].pop(index)
            self.db[item_name]['value']['updated'] = int(time.time())
        else:
            del self.db[item_name]
        self.last_update = int(time.time())
        return True

    def add(self, key, value, tags):
        self.db[key] = {'value': value, 'updated': int(time.time()), 'tags' : tags }
        self.last_update = int(time.time())
        return StashedItem(self.db[key])

    def add_dict(self, newdict):
        self.db.clear()
        for key in newdict:
            self.db[key] = newdict[key]
        self.last_update = int(time.time())
        return


    def exist(self, item_name, index=None):
        if item_name in self.db:
            if index is not None:
                try:
                    self.db[item_name]['value'][index]
                except IndexError:
                    return False
            return True
        return False

    def is_list(self, item_name):
        return isinstance(self.db[item_name]['value'], list)

    def get(self, item_name, index=None):
        index = index - 1 if index is not None else None
        item = self.db[item_name]
        return StashedItem(item, index)

    def get_all(self):
        result = {}
        for k, v in self.db.iteritems():
            result[k] = StashedItem(v)
        return result

    def tags(self, tag):
        result = {}
        for k, v in self.db.iteritems():
            if 'tags' in v:
                if tag in v['tags']:
                    result[k] = StashedItem(v)
        return result

    def alltags(self):
        result = []
        for k, v in self.db.iteritems():
            if 'tags' in v:
                for tag in v['tags']:
                    result.append(tag)
        return result


    def get_database_data(self):
        return dict(self.connection)

    def set_database_data(self, data):
        #TODO check this out
        self.connection['storage'] = data
        return True


########NEW FILE########
__FILENAME__ = web
# -*- coding: utf-8 -*-
from requests.auth import AuthBase
import requests
import json
import hashlib
import sys
import os
import getpass
from clint.textui import colored
from common import output

import netrc

STASH_HOST = 'http://getstash.herokuapp.com'

if 'STASH_HOST' in os.environ:
    STASH_HOST = os.environ['STASH_HOST']

class DuplicateKeyword(Exception):
    """
    Key already exist
    """
    pass


class WrongArgumentsSet(Exception):
    """
    Not enough arguments
    """
    pass


class WrongKey(Exception):
    """
    Key not found
    """
    pass


class NoInternetConnection(Exception):
    """
    No Internet connection or server not available
    """
    pass


class ServerError(Exception):
    """
    Server error
    """
    pass


class UnknownServerError(Exception):
    """
    Unknown server error
    """
    pass


class WrongCredentials(Exception):
    pass


class TokenAuth(AuthBase):
    """Attaches HTTP Token Authentication to the given Request object."""
    def __init__(self, username, password):
        # setup any auth-related data here
        self.username = username
        self.password = password

    def __call__(self, r):
        # modify and return the request
        r.headers['X-Token'] = self.password
        return r


class AlreadyLoggedIn(Exception):
    pass


class API(object):
    username = None
    token = None

    def check_login(self):
        """
        Check if user logged in. If True - return login and token, else returns None
        """
        netrc_path = os.path.join(os.path.expanduser('~'), '.netrc')
        if not os.path.exists(netrc_path):
            open(netrc_path, 'w').close()
        info = netrc.netrc()
        login, account, password = info.authenticators(STASH_HOST) or (None, None, None)
        if password and login:
            if self.username is None or self.token is None:
                self.username = login
                # todo: why token is equal to password?
                self.token = password
            return login, password
        return None

    def login_decorator(fn):
        def wrapper(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], API):
                if args[0].check_login() is not None:
                    return fn(*args, **kwargs)
            raise Exception('Unknown credentials.\nTry to do stash login at first.\n')
            #output('Unknown credentials.\nTry to do stash login at first.\n', color='yellow')
        return wrapper

    def send_request_decorator(fn):
        """
        Request decorator (avoiding code duplication)
        """
        def wrapper(self, *args):
            data = fn(self, *args)
            data.update(self.get_user_data())
            url = STASH_HOST + '/api/json'
            try:
                data['token'] = self.token
                headers = {'Stash-Token': self.token}
                r = requests.post(url, data=json.dumps(data), headers=headers)
            except requests.exceptions.ConnectionError:
                raise NoInternetConnection
            # todo: replace with regular python exceptions
            if r.status_code == 404:
                raise WrongKey
            if r.status_code == 401:
                raise WrongCredentials
            if r.status_code == 500:
                raise ServerError
            if r.status_code == 200:
                return r.json()
            else:
                return UnknownServerError
        return wrapper

    def get_user_data(self):
        return {'user': self.username}

    def login(self, login, password):
        if self.check_login() is not None:
            raise AlreadyLoggedIn
        m = hashlib.new('md5')
        m.update(password)
        r = self.get_token(login, password)
        #TODO check if r is an error (remove  / from stash host for example) 
        if 'token' in r:
            # todo: maybe we don't need this two lines?
            self.username = login
            self.token = r['token']
            with open(os.path.join(os.environ['HOME'], ".netrc"), "a") as f:
                f.write("machine " + STASH_HOST + " login " + login + " password " + str(r['token']) + "\n")
                f.close()
        else:
            # todo: do something
            pass
        if 'error' in r:
            raise Exception(r['error'])
        return True

    def logout(self):
        """
        Clear .netrc record
        """
        netrc_path = os.path.join(os.path.expanduser('~'), '.netrc')

        if not os.path.exists(netrc_path):
            open(netrc_path, 'w').close()

        info = netrc.netrc()

        if STASH_HOST in info.hosts:
            del info.hosts[STASH_HOST]
        else:
            raise Exception('You haven\'t logged in yet')

        with open(netrc_path, 'w') as f:
            f.write(info.__repr__())
            f.close()
        return True

    # ==========

    @send_request_decorator
    @login_decorator
    def get(self, key):
        return {'get': key}

    @send_request_decorator
    @login_decorator
    def search(self, key):
        return {'search': key}


    @send_request_decorator
    @login_decorator
    def set(self, key, value, tags, overwrite=False,append=False):
        return {'set': { key: value }, 'tags' : tags, 'overwrite': overwrite, 'append' : append}

    @send_request_decorator
    @login_decorator
    def delete(self, key):
        return {'delete': key}

    @send_request_decorator
    @login_decorator
    def all(self):
        return {'getkeys': True}

    @send_request_decorator
    @login_decorator
    def gettags(self):
        return {'gettags': True}

    @send_request_decorator
    @login_decorator
    def tags(self, key):
        return {'tags': key }

    @send_request_decorator
    @login_decorator
    def push(self, list_title, value):
        return {'push': {list_title: value}}

    @send_request_decorator
    def get_token(self, username, password):
        return {'login': {username: password}}

    # =========

    @login_decorator
    @send_request_decorator
    def sync(self, local_db_data):
        return { 'sync' : local_db_data }

    @send_request_decorator
    def get_token(self, username, password):
        return {'login': {username: password}}

    def push(self):
        """Push data to cloud"""

    def pull(self):
        """Pull data from cloud"""

########NEW FILE########
