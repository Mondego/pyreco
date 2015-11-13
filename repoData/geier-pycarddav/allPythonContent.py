__FILENAME__ = backend
#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The SQLite backend implementation.

Database Layout
===============

current version number: 9
tables: version, accounts, account_$ACCOUNTNAME

version:
    version (INT): only one line: current db version

account:
    account (TEXT): name of the account
    resource (TEXT)
    ctag (TEXT) ctag of the collection

$ACCOUNTNAME_r:   # as in resource
    href (TEXT)
    etag (TEXT)
    name (TEXT): name as in vcard, seperated by ';'
    fname (TEXT): formated name
    status (INT): status of this card, see below for meaning
    vcard (TEXT): the actual vcard

"""

# TODO rename account to resource or similar

from __future__ import print_function

try:
    from pycarddav import model
    import xdg.BaseDirectory
    import sys
    import sqlite3
    import logging
    from os import path

except ImportError, error:
    print(error)
    sys.exit(1)


OK = 0  # not touched since last sync
NEW = 1  # new card, needs to be created on the server
CHANGED = 2  # properties edited or added (news to be pushed to server)
DELETED = 9  # marked for deletion (needs to be deleted on server)


class SQLiteDb(object):
    """Querying the addressbook database

    the type() of parameters named "account" should be something like str()
    and of parameters named "accountS" should be an iterable like list()
    """

    def __init__(self,
                 db_path=None,
                 encoding="utf-8",
                 errors="strict",
                 debug=False):
        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path('pycard') + 'abook.db'
        self.db_path = path.expanduser(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.encoding = encoding
        self.errors = errors
        self.debug = debug
        self.display_all = False
        self.print_function = "print_contact_info"
        self._create_default_tables()
        self._check_table_version()

    def __del__(self):
        self.conn.close()

    def search(self, search_string, accounts, where='vcard'):
        """returns list of parsed vcards from db matching search_string
        where can be any of 'vcard', 'name', 'fname' or 'allnames' (meaning is
        searched for both 'name' or 'fname' for matches)
        """
        if where not in ('vcard', 'name', 'fname', 'allnames'):
            raise ValueError("Invalid 'where' argument")

        search_str = '%' + search_string + '%'
        sql_fmt = 'SELECT href, vcard, etag FROM {0} WHERE '

        if where == 'allnames':
            sql_fmt += 'name LIKE (?) OR fname LIKE (?)'
            sql_args = (search_str, search_str)
        else:
            sql_fmt += where + ' LIKE (?)'
            sql_args = (search_str,)

        result = list()
        for account in accounts:
            rows = self.sql_ex(sql_fmt.format(account + '_r'), sql_args)
            result.extend((self.get_vcard_from_data(account, *r) for r in rows))
        return result

    def _dump(self, account_name):
        """return table self.account, used for testing"""
        sql_s = 'SELECT * FROM {0}'.format(account_name + '_r')
        result = self.sql_ex(sql_s)
        return result

    def _check_table_version(self):
        """tests for current db Version
        if the table is still empty, insert db_version
        """
        database_version = 11  # the current db VERSION
        self.cursor.execute('SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            stuple = (database_version, )  # database version db Version
            self.cursor.execute('INSERT INTO version (version) VALUES (?)',
                                stuple)
            self.conn.commit()
        elif not result[0] == database_version:
            raise Exception(str(self.db_path) +
                            " is probably an invalid or outdated database.\n"
                            "You should consider to remove it and sync again "
                            "using pycardsyncer.\n")

    def _create_default_tables(self):
        """creates version and account tables and insert table version number

        """
        # CREATE TABLE IF NOT EXISTS is faster than checking if it exists
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS version
                                ( version INTEGER )''')
            logging.debug("made sure version table exists")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                account TEXT NOT NULL,
                resource TEXT NOT NULL,
                ctag TEXT
                )''')
            logging.debug("made sure accounts table exists ")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()
        self._check_table_version()  # insert table version

    def sql_ex(self, statement, stuple=''):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        self.conn.commit()
        return result

    def check_account_table(self, account_name, resource):
        count_sql_s = """SELECT count(*) FROM accounts
                WHERE account = ? AND resource = ?"""
        self.cursor.execute(count_sql_s, (account_name, resource))
        result = self.cursor.fetchone()

        if(result[0] != 0):
            return
        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                href TEXT,
                etag TEXT,
                name TEXT,
                fname TEXT,
                vcard TEXT,
                status INT NOT NULL,
                PRIMARY KEY(href)
                )""".format(account_name + '_r')
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        self.sql_ex(sql_s, (account_name + '_r', resource))
        logging.debug("made sure {0} table exists".format(account_name))

    def needs_update(self, href, account_name, etag=''):
        """checks if we need to update this vcard
        if no table with the name account_$ACCOUNT exists, it will be created

        :param href: href of vcard
        :type href: str()
        :param etag: etag of vcard
        :type etag: str()
        :return: True or False
        """
        stuple = (href,)
        sql_s = 'SELECT etag FROM {0} WHERE href = ?'.format(account_name + '_r')
        result = self.sql_ex(sql_s, stuple)
        if len(result) is 0:
            return True
        elif etag != result[0][0]:
            return True
        else:
            return False

    def update(self, vcard, account_name, href='', etag='', status=OK):
        """insert a new or update an existing card in the db

        :param vcard: vcard to be inserted or updated
        :type vcard: model.VCard() or unicode() (an actual vcard)
        :param href: href of the card on the server, if this href already
                     exists in the db the card gets updated. If no href is
                     given, a random href is chosen and it is implied that this
                     card does not yet exist on the server, but will be
                     uploaded there on next sync.
        :type href: str()
        :param etag: the etga of the vcard, if this etag does not match the
                     remote etag on next sync, this card will be updated from
                     the server. For locally created vcards this should not be
                     set
        :type etag: str()
        :param status: status of the vcard
                       * OK: card is in sync with remote server
                       * NEW: card is not yet on the server, this needs to be
                              set for locally created vcards
                       * CHANGED: card locally changed, will be updated on the
                                  server on next sync (if remote card has not
                                  changed since last sync)
                       * DELETED: card locally delete, will also be deleted on
                                  one the server on next sync (if remote card
                                  has not changed)
        :type status: one of backend.OK, backend.NEW, backend.CHANGED,
                      BACKEND.DELETED

        """
        if isinstance(vcard, (str, unicode)):  # unicode for py2, str for py3
            try:
                vcard_s = vcard.decode('utf-8')
            except UnicodeEncodeError:
                vcard_s = vcard  # incase it's already unicode and py2
            try:
                vcard = model.vcard_from_string(vcard)
            except Exception as error:
                logging.error('VCard {0} could not be inserted into the '
                              'db'.format(href))
                logging.debug(error)
                logging.info(vcard)
                return
        else:
            vcard_s = vcard.vcf
        if href == '':
            href = get_random_href()
        stuple = (etag, vcard.name, vcard.fname, vcard_s, status, href, href)
        sql_s = ('INSERT OR REPLACE INTO {0} '
                 '(etag, name, fname, vcard, status, href) '
                 'VALUES (?, ?, ?, ?, ?, '
                 'COALESCE((SELECT href FROM {0} WHERE href = ?), ?)'
                 ');'.format(account_name + '_r'))
        self.sql_ex(sql_s, stuple)

    def update_href(self, old_href, new_href, account_name, etag='', status=OK):
        """updates old_href to new_href, can also alter etag and status,
        see update() for an explanation of these parameters"""
        stuple = (new_href, etag, status, old_href)
        sql_s = 'UPDATE {0} SET href = ?, etag = ?, status = ? \
             WHERE href = ?;'.format(account_name + '_r')
        self.sql_ex(sql_s, stuple)

    def href_exists(self, href, account_name):
        """returns True if href already exist in db

        :param href: href
        :type href: str()
        :returns: True or False
        """
        sql_s = 'SELECT href FROM {0} WHERE href = ?;'.format(account_name + '_r')
        if len(self.sql_ex(sql_s, (href, ))) == 0:
            return False
        else:
            return True

    def get_etag(self, href, account_name):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        sql_s = 'SELECT etag FROM {0} WHERE href=(?);'.format(account_name + '_r')
        etag = self.sql_ex(sql_s, (href,))[0][0]
        return etag

    def delete_vcard_from_db(self, href, account_name):
        """
        removes the whole vcard,
        returns nothing
        """
        stuple = (href, )
        logging.debug("locally deleting " + str(href))
        self.sql_ex('DELETE FROM {0} WHERE href=(?)'.format(account_name + '_r'),
                    stuple)

    def get_all_href_from_db(self, accounts):
        """returns a list with all parsed vcards
        """
        result = list()
        for account in accounts:
            rows = self.sql_ex(
                'SELECT href, vcard, etag FROM {0} ORDER BY fname'
                ' COLLATE NOCASE'.format(account + '_r'))
            result.extend((self.get_vcard_from_data(account, *r) for r in rows))
        return result

    def get_all_href_from_db_not_new(self, accounts):
        """returns list of all not new hrefs"""
        result = list()
        for account in accounts:
            sql_s = 'SELECT href FROM {0} WHERE status != (?)'.format(account + '_r')
            stuple = (NEW,)
            hrefs = self.sql_ex(sql_s, stuple)
            result = result + [(href[0], account) for href in hrefs]
        return result

#    def get_names_href_from_db(self, searchstring=None):
#        """
#        :return: list of tuples(name, href) of all entries from the db
#        """
#        if searchstring is None:
#            return self.sql_ex('SELECT fname, href FROM {0} '
#                               'ORDER BY name'.format(self.account))
#        else:
#            return [(c.fname, c.href) for c in self.search(searchstring)]

    def get_vcard_from_data(self, account_name, href, vcard, etag):
        """returns a VCard()
        """
        vcard = model.vcard_from_string(vcard)
        vcard.href = href
        vcard.account = account_name
        vcard.etag = etag
        return vcard

    def get_vcard_from_db(self, href, account_name):
        """returns a VCard()
        """
        sql_s = 'SELECT vcard, etag FROM {0} WHERE href=(?)'.format(account_name + '_r')
        result = self.sql_ex(sql_s, (href, ))
        return self.get_vcard_from_data(account_name, href, *result[0])

    def get_changed(self, account_name):
        """returns list of hrefs of locally edited vcards
        """
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account_name + '_r')
        result = self.sql_ex(sql_s, (CHANGED, ))
        return [row[0] for row in result]

    def get_new(self, account_name):
        """returns list of hrefs of locally added vcards
        """
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account_name + '_r')
        result = self.sql_ex(sql_s, (NEW, ))
        return [row[0] for row in result]

    def get_marked_delete(self, account_name):
        """returns list of tuples (hrefs, etags) of locally deleted vcards
        """
        sql_s = 'SELECT href, etag FROM {0} WHERE status == (?)'.format(account_name + '_r')
        result = self.sql_ex(sql_s, (DELETED, ))
        return result

    def mark_delete(self, href, account_name):
        """marks the entry as to be deleted on server on next sync
        """
        sql_s = 'UPDATE {0} SET STATUS = ? WHERE href = ?'.format(account_name + '_r')
        self.sql_ex(sql_s, (DELETED, href, ))

    def reset_flag(self, href, account_name):
        """
        resets the status for a given href to 0 (=not edited locally)
        """
        sql_s = 'UPDATE {0} SET status = ? WHERE href = ?'.format(account_name + '_r')
        self.sql_ex(sql_s, (OK, href, ))


def get_random_href():
    """returns a random href
    """
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()

########NEW FILE########
__FILENAME__ = carddav
#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
contains the class PyCardDAv and some associated functions and definitions
"""

from collections import namedtuple
import requests
import urlparse
import logging
import lxml.etree as ET


def get_random_href():
    """returns a random href"""
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()


class UploadFailed(Exception):
    """uploading the card failed"""
    pass


class NoWriteSupport(Exception):
    """write support has not been enabled"""
    pass


class PyCardDAV(object):
    """class for interacting with a CardDAV server

    Since PyCardDAV relies heavily on Requests [1] its SSL verification is also
    shared by PyCardDAV [2]. For now, only the *verify* keyword is exposed
    through PyCardDAV.

    [1] http://docs.python-requests.org/
    [2] http://docs.python-requests.org/en/latest/user/advanced/

    raises:
        requests.exceptions.SSLError
        requests.exceptions.ConnectionError
        more requests.exceptions depending on the actual error
        Exception (shame on me)

    """

    def __init__(self, resource, debug='', user='', passwd='',
                 verify=True, write_support=False, auth='basic'):
        #shutup urllib3
        urllog = logging.getLogger('requests.packages.urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)
        urllog = logging.getLogger('urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)

        split_url = urlparse.urlparse(resource)
        url_tuple = namedtuple('url', 'resource base path')
        self.url = url_tuple(resource,
                             split_url.scheme + '://' + split_url.netloc,
                             split_url.path)
        self.debug = debug
        self.session = requests.session()
        self.write_support = write_support
        self._settings = {'verify': verify}
        if auth == 'basic':
            self._settings['auth'] = (user, passwd,)
        if auth == 'digest':
            from requests.auth import HTTPDigestAuth
            self._settings['auth'] = HTTPDigestAuth(user, passwd)
        self._default_headers = {"User-Agent": "pyCardDAV"}

        headers = self.headers
        headers['Depth'] = '1'
        response = self.session.request('OPTIONS',
                                        self.url.resource,
                                        headers=headers,
                                        **self._settings)
        response.raise_for_status()   # raises error on not 2XX HTTP status code
        if 'addressbook' not in response.headers.get('DAV', ''):
            raise Exception("URL is not a CardDAV resource")

    @property
    def verify(self):
        """gets verify from settings dict"""
        return self._settings['verify']

    @verify.setter
    def verify(self, verify):
        """set verify"""
        self._settings['verify'] = verify

    @property
    def headers(self):
        """returns the headers"""
        return dict(self._default_headers)

    def _check_write_support(self):
        """checks if user really wants his data destroyed"""
        if not self.write_support:
            raise NoWriteSupport

    def get_abook(self):
        """does the propfind and processes what it returns

        :rtype: list of hrefs to vcards
        """
        xml = self._get_xml_props()
        abook = self._process_xml_props(xml)
        return abook

    def get_vcard(self, href):
        """
        pulls vcard from server

        :returns: vcard
        :rtype: string
        """
        response = self.session.get(self.url.base + href,
                                    headers=self.headers,
                                    **self._settings)
        response.raise_for_status()
        return response.content

    def update_vcard(self, card, href, etag):
        """
        pushes changed vcard to the server
        card: vcard as unicode string
        etag: str or None, if this is set to a string, card is only updated if
              remote etag matches. If etag = None the update is forced anyway
         """
         # TODO what happens if etag does not match?
        self._check_write_support()
        remotepath = str(self.url.base + href)
        headers = self.headers
        headers['content-type'] = 'text/vcard'
        if etag is not None:
            headers['If-Match'] = etag
        self.session.put(remotepath, data=card, headers=headers,
                         **self._settings)

    def delete_vcard(self, href, etag):
        """deletes vcard from server

        deletes the resource at href if etag matches,
        if etag=None delete anyway
        :param href: href of card to be deleted
        :type href: str()
        :param etag: etag of that card, if None card is always deleted
        :type href: str()
        :returns: nothing
        """
        # TODO: what happens if etag does not match, url does not exist etc ?
        self._check_write_support()
        remotepath = str(self.url.base + href)
        headers = self.headers
        headers['content-type'] = 'text/vcard'
        if etag is not None:
            headers['If-Match'] = etag
        response = self.session.delete(remotepath,
                                       headers=headers,
                                       **self._settings)
        response.raise_for_status()

    def upload_new_card(self, card):
        """
        upload new card to the server

        :param card: vcard to be uploaded
        :type card: unicode
        :rtype: tuple of string (path of the vcard on the server) and etag of
                new card (string or None)
        """
        self._check_write_support()
        card = card.encode('utf-8')
        for _ in range(0, 5):
            rand_string = get_random_href()
            remotepath = str(self.url.resource + rand_string + ".vcf")
            headers = self.headers
            headers['content-type'] = 'text/vcard'  # TODO perhaps this should
            # be set to the value this carddav server uses itself
            headers['If-None-Match'] = '*'
            response = requests.put(remotepath, data=card, headers=headers,
                                    **self._settings)
            if response.ok:
                parsed_url = urlparse.urlparse(remotepath)
                if 'etag' not in response.headers.keys() or response.headers['etag'] is None:
                    etag = ''
                else:
                    etag = response.headers['etag']

                return (parsed_url.path, etag)
        response.raise_for_status()

    def _get_xml_props(self):
        """PROPFIND method

        gets the xml file with all vcard hrefs

        :rtype: str() (an xml file)
        """
        headers = self.headers
        headers['Depth'] = '1'
        response = self.session.request('PROPFIND',
                                        self.url.resource,
                                        headers=headers,
                                        **self._settings)
        response.raise_for_status()

        return response.content

    @classmethod
    def _process_xml_props(cls, xml):
        """processes the xml from PROPFIND, listing all vcard hrefs

        :param xml: the xml file
        :type xml: str()
        :rtype: dict() key: href, value: etag
        """
        namespace = "{DAV:}"

        element = ET.XML(xml)
        abook = dict()
        for response in element.iterchildren():
            if (response.tag == namespace + "response"):
                href = ""
                etag = ""
                insert = False
                for refprop in response.iterchildren():
                    if (refprop.tag == namespace + "href"):
                        href = refprop.text
                    for prop in refprop.iterchildren():
                        for props in prop.iterchildren():
                            # different servers give different getcontenttypes:
                            # e.g.:
                            #  "text/vcard"
                            #  "text/x-vcard"
                            #  "text/x-vcard; charset=utf-8"
                            #  "text/directory;profile=vCard"
                            #  "text/directory"
                            #  "text/vcard; charset=utf-8"  CalendarServer
                            if (props.tag == namespace + "getcontenttype" and
                                    props.text.split(';')[0].strip() in ['text/vcard', 'text/x-vcard']):
                                insert = True
                            if (props.tag == namespace + "resourcetype" and
                                namespace + "collection" in [c.tag for c in props.iterchildren()]):
                                insert = False
                                break
                            if (props.tag == namespace + "getetag"):
                                etag = props.text
                        if insert:
                            abook[href] = etag
        return abook

########NEW FILE########
__FILENAME__ = query
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
query the local db
"""

from pycarddav import backend

from os import path

import sys

__all__ = [ 'query' ]

def query(conf):
    # testing if the db exists
    if not path.exists(path.expanduser(conf.sqlite.path)):
        sys.exit(str(conf.sqlite.path) + " file does not exist, please sync"
                 " with pycardsyncer first.")

    search_string = conf.query.search_string.decode("utf-8")

    my_dbtool = backend.SQLiteDb(db_path=path.expanduser(conf.sqlite.path),
                                 encoding="utf-8",
                                 errors="stricts",
                                 debug=False)

    if conf.query.importing:
        action = importing
    elif conf.query.backup:
        action = backup
    #elif conf.query.edit:
    #   action = edit
    elif conf.query.delete: # mark a card for deletion
        action = delete
    else:
        action = search

    action(my_dbtool, search_string, conf)

    return 0


def importing(my_dbtool, search_string, conf):
    from pycarddav import model
    cards = model.cards_from_file(conf.query.importing)
    for card in cards:
        my_dbtool.update(card, conf.sync.accounts[0], status=backend.NEW)

def backup(my_dbtool, search_string, conf):
    with open(conf.query.backup, 'w') as vcf_file:
        if search_string == "":
            vcards = my_dbtool.get_all_href_from_db(conf.sync.accounts)
        else:
            vcards = my_dbtool.search(search_string, conf.sync.accounts,
                    conf.query.where)
        for vcard in vcards:
            vcf_file.write(vcard.vcf.encode('utf-8'))

def edit(my_dbtool, search_string, conf):
    from pycarddav import ui
    names = my_dbtool.select_entry2(search_string)
    href = ui.select_entry(names)
    if href is None:
        sys.exit("Found no matching cards.")

def delete(my_dbtool, search_string, conf):
    vcards = my_dbtool.search(search_string, conf.sync.accounts,
            conf.query.where)
    if len(vcards) is 0:
        sys.exit('Found no matching cards.')
    elif len(vcards) is 1:
        card = vcards[0]
    else:
        from pycarddav import ui
        href_account_list = [(c.href, c.account) for c in vcards]
        pane = ui.VCardChooserPane(my_dbtool,
                                   href_account_list=href_account_list)
        ui.start_pane(pane)
        card = pane._walker.selected_vcard
    if card.href in my_dbtool.get_new(card.account):
        # cards not yet on the server get deleted directly, otherwise we
        # will try to delete them on the server later (where they don't
        # exist) and this will raise an exception
        my_dbtool.delete_vcard_from_db(card.href, card.account)
    else:
        my_dbtool.mark_delete(card.href, card.account)
        print(u'vcard {0} - "{1}" deleted from local db, '
              'will be deleted on the server on the next '
              'sync'.format(card.href, card.fname))

def search(my_dbtool, search_string, conf):
    print("searching for " + conf.query.search_string + "...")

    for vcard in my_dbtool.search(search_string, conf.sync.accounts,
            conf.query.where):
        if conf.query.mutt_format:
            lines = vcard.print_email()
        elif conf.query.tel:
            lines = vcard.print_tel()
        elif conf.query.display_all:
            lines = vcard.pretty
        else:
            lines = vcard.pretty_min
        if not lines == '':
            print(lines.encode('utf-8'))


########NEW FILE########
__FILENAME__ = sync
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
syncs the remote database to the local db
"""

from pycarddav import carddav
from pycarddav import backend

import logging

__all__ = ['sync']


def sync(conf):
    """this should probably be seperated from the class definitions"""

    syncer = carddav.PyCardDAV(conf.account.resource,
                               user=conf.account.user,
                               passwd=conf.account.passwd,
                               write_support=conf.account.write_support,
                               verify=conf.account.verify,
                               auth=conf.account.auth)
    my_dbtool = backend.SQLiteDb(db_path=conf.sqlite.path,
                                 encoding="utf-8",
                                 errors="stricts",
                                 debug=conf.debug)
    # sync:
    abook = syncer.get_abook()  # type(abook): dict
    my_dbtool.check_account_table(conf.account.name, conf.account.resource)

    for href, etag in abook.iteritems():
        if my_dbtool.needs_update(href, conf.account.name, etag=etag):
            logging.debug("getting %s etag: %s", href, etag)
            vcard = syncer.get_vcard(href)
            my_dbtool.update(vcard, conf.account.name, href=href, etag=etag)

    remote_changed = False
    # for now local changes overwritten by remote changes
    logging.debug("looking for locally changed vcards...")

    hrefs = my_dbtool.get_changed(conf.account.name)

    for href in hrefs:
        try:
            logging.debug("trying to update %s", href)
            card = my_dbtool.get_vcard_from_db(href, conf.account.name)
            logging.debug("%s", my_dbtool.get_etag(href, conf.account.name))
            syncer.update_vcard(card.vcf, href, None)
            my_dbtool.reset_flag(href, conf.account.name)
            remote_changed = True
        except carddav.NoWriteSupport:
            logging.info('failed to upload changed card {0}, '
                         'you need to enable write support, '
                         'see the documentation', href)
    # uploading
    hrefs = my_dbtool.get_new(conf.account.name)
    for href in hrefs:
        try:
            logging.debug("trying to upload new card %s", href)
            card = my_dbtool.get_vcard_from_db(href, conf.account.name)
            (href_new, etag_new) = syncer.upload_new_card(card.vcf)
            my_dbtool.update_href(href,
                                  href_new,
                                  conf.account.name,
                                  status=backend.OK)
            remote_changed = True
        except carddav.NoWriteSupport:
            logging.info('failed to upload card %s, '
                         'you need to enable write support, '
                         'see the documentation', href)

    # deleting locally deleted cards on the server
    hrefs_etags = my_dbtool.get_marked_delete(conf.account.name)

    for href, etag in hrefs_etags:
        try:
            logging.debug('trying to delete card %s', href)
            syncer.delete_vcard(href, etag)
            my_dbtool.delete_vcard_from_db(href, conf.account.name)
            remote_changed = True
        except carddav.NoWriteSupport:
            logging.info('failed to delete card {0}, '
                         'you need to enable write support, '
                         'see the documentation'.format(href))

    # detecting remote-deleted cards
    # is there a better way to compare a list of unicode() with a list of str()
    # objects?

    if remote_changed:
        abook = syncer.get_abook()  # type (abook): dict
    r_href_account_list = my_dbtool.get_all_href_from_db_not_new(
        [conf.account.name])
    delete = set([href for href, account in r_href_account_list]).difference(abook.keys())
    for href in delete:
        my_dbtool.delete_vcard_from_db(href, conf.account.name)

########NEW FILE########
__FILENAME__ = model
#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The pycarddav abstract model and tools for VCard handling.
"""

from __future__ import print_function

import base64
import logging
import sys
from collections import defaultdict

import vobject


def list_clean(string):
    """ transforms a comma seperated string to a list, stripping whitespaces
    "HOME, WORK,pref" -> ['HOME', 'WORK', 'pref']

    string: string of comma seperated elements
    returns: list()
    """

    string = string.split(',')
    rstring = list()
    for element in string:
        rstring.append(element.strip(' '))
    return rstring


NO_STRINGS = [u"n", "n", u"no", "no"]
YES_STRINGS = [u"y", "y", u"yes", "yes"]

PROPERTIES = ['EMAIL', 'TEL']
PROPS_ALL = ['FN', 'N', 'VERSION', 'NICKNAME', 'PHOTO', 'BDAY', 'ADR',
             'LABEL', 'TEL', 'EMAIL', 'MAILER', 'TZ', 'GEO', 'TITLE', 'ROLE',
             'LOGO', 'AGENT', 'ORG', 'NOTE', 'REV', 'SOUND', 'URL', 'UID',
             'KEY', 'CATEGORIES', 'PRODID', 'REV', 'SORT-STRING', 'SOUND',
             'URL', 'VERSION', 'UTC-OFFSET']
PROPS_ALLOWED = ['NICKNAME', 'BDAY', 'ADR', 'LABEL', 'TEL', 'EMAIL',
                 'MAILER', 'TZ', 'GEO', 'TITLE', 'ROLE', 'AGENT',
                 'ORG', 'NOTE', 'REV', 'SOUND', 'URL', 'UID', 'KEY',
                 'CATEGORIES', 'PRODID', 'REV', 'SORT-STRING', 'SOUND',
                 'URL', 'VERSION', 'UTC-OFFSET']
PROPS_ONCE = ['FN', 'N', 'VERSION']
PROPS_LIST = ['NICKNAME', 'CATEGORIES']
PROPS_BIN = ['PHOTO', 'LOGO', 'SOUND', 'KEY']


RTEXT = '\x1b[7m'
NTEXT = '\x1b[0m'
BTEXT = '\x1b[1m'


def get_names(display_name):
    first_name, last_name = '', display_name

    if display_name.find(',') > 0:
        # Parsing something like 'Doe, John Abraham'
        last_name, first_name = display_name.split(',')

    elif display_name.find(' '):
        # Parsing something like 'John Abraham Doe'
        # TODO: This fails for compound names. What is the most common case?
        name_list = display_name.split(' ')
        last_name = ''.join(name_list[-1])
        first_name = ' '.join(name_list[:-1])

    return first_name.strip().capitalize(), last_name.strip().capitalize()


def fix_vobject(vcard):
    """trying to fix some more or less common errors in vcards

    for now only missing FN properties are handled (and reconstructed from N)
    :type vcard: vobject.base.Component (vobject based vcard)

    """
    if 'fn' not in vcard.contents:
        logging.debug('vcard has no formatted name, reconstructing...')
        fname = vcard.contents['n'][0].valueRepr()
        fname = fname.strip()
        vcard.add('fn')
        vcard.fn.value = fname
    return vcard

def vcard_from_vobject(vcard):
    vcard = fix_vobject(vcard)
    vdict = VCard()
    if vcard.name != "VCARD":
        raise Exception  # TODO proper Exception type
    for line in vcard.getChildren():
        # this might break, was tried/excepted before
        line.transformFromNative()
        property_name = line.name
        property_value = line.value

        try:
            if line.ENCODING_paramlist == [u'b']:
                property_value = base64.b64encode(line.value)

        except AttributeError:
            pass
        if type(property_value) == list:
            property_value = (',').join(property_value)

        vdict[property_name].append((property_value, line.params,))
    return vdict


def vcard_from_string(vcard_string):
    """
    vcard_string: str() or unicode()
    returns VCard()
    """
    try:
        vcard = vobject.readOne(vcard_string)
    except vobject.base.ParseError as error:
        raise Exception(error)  # TODO proper exception
    return vcard_from_vobject(vcard)


def vcard_from_email(display_name, email):
    fname, lname = get_names(display_name)
    vcard = vobject.vCard()
    vcard.add('n')
    vcard.n.value = vobject.vcard.Name(family=lname, given=fname)
    vcard.add('fn')
    vcard.fn.value = display_name
    vcard.add('email')
    vcard.email.value = email
    vcard.email.type_param = 'INTERNET'
    return vcard_from_vobject(vcard)


def cards_from_file(cards_f):
    collector = list()
    for vcard in vobject.readComponents(cards_f):
        collector.append(vcard_from_vobject(vcard))
    return collector


class VCard(defaultdict):
    """
    internal representation of a VCard. This is dict with some
    associated methods,
    each dict item is a list of tuples
    i.e.:
    >>> vcard['EMAIL']
    [('hanz@wurst.com', ['WORK', 'PREF']), ('hanz@wurst.net', ['HOME'])]


    self.href: unique id (really just the url) of the VCard
    self.account: account which this card is associated with
    db_path: database file from which to initialize the VCard

    self.edited:
        0: nothing changed
        1: name and/or fname changed
        2: some property was deleted
    """

    def __init__(self, ddict=''):

        if ddict == '':
            defaultdict.__init__(self, list)
        else:
            defaultdict.__init__(self, list, ddict)
        self.href = ''
        self.account = ''
        self.etag = ''
        self.edited = 0

    def serialize(self):
        return self.items().__repr__()

    @property
    def name(self):
        return unicode(self['N'][0][0]) if self['N'] else ''

    @name.setter
    def name(self, value):
        if not self['N']:
            self['N'] = [('', {})]
        self['N'][0][0] = value

    @property
    def fname(self):
        return unicode(self['FN'][0][0]) if self['FN'] else ''

    @fname.setter
    def fname(self, value):
        self['FN'][0] = (value, {})

    def alt_keys(self):
        keylist = self.keys()
        for one in [x for x in ['FN', 'N', 'VERSION'] if x in keylist]:
            keylist.remove(one)
        keylist.sort()
        return keylist

    def print_email(self):
        """prints only name, email and type for use with mutt"""
        collector = list()
        try:
            for one in self['EMAIL']:
                try:
                    typelist = ','.join(one[1][u'TYPE'])
                except KeyError:
                    typelist = ''
                collector.append(one[0] + "\t" + self.fname + "\t" + typelist)
            return '\n'.join(collector)
        except KeyError:
            return ''

    def print_tel(self):
        """prints only name, email and type for use with mutt"""
        collector = list()
        try:
            for one in self['TEL']:
                try:
                    typelist = ','.join(one[1][u'TYPE'])
                except KeyError:
                    typelist = ''
                collector.append(self.fname + "\t" + one[0] + "\t" + typelist)
            return '\n'.join(collector)
        except KeyError:
            return ''

    @property
    def pretty(self):
        return self._pretty_base(self.alt_keys())

    @property
    def pretty_min(self):
        return self._pretty_base(['TEL', 'EMAIL'])

    def _pretty_base(self, keylist):
        collector = list()
        if sys.stdout.isatty():
            collector.append('\n' + BTEXT + 'Name: ' + self.fname + NTEXT)
        else:
            collector.append('\n' + 'Name: ' + self.fname)
        for key in keylist:
            for value in self[key]:
                try:
                    types = ' (' + ', '.join(value[1]['TYPE']) + ')'
                except KeyError:
                    types = ''
                try:
                    line = key + types + ': ' + value[0]
                except UnicodeDecodeError:
                    line = key + types + ': ' + '<BINARY DATA>'
                collector.append(line)
        return '\n'.join(collector)

    def _line_helper(self, line):
        collector = list()
        for key in line[1].keys():
            collector.append(key + '=' + ','.join(line[1][key]))
        if collector == list():
            return ''
        else:
            return (';' + ';'.join(collector))

    @property
    def vcf(self):
        """serialize to VCARD as specified in RFC2624,
        if no UID is specified yet, one will be added (as a UID is mandatory
        for carddav as specified in RF6352
        TODO make shure this random uid is unique"""
        import string
        import random

        def generate_random_uid():
            """generate a random uid, when random isn't broken, getting a
            random UID from a pool of roughly 10^56 should be good enough"""
            choice = string.ascii_uppercase + string.digits
            return ''.join([random.choice(choice) for _ in range(36)])
        if 'UID' not in self.keys():
            self['UID'] = [(generate_random_uid(), dict())]
        collector = list()
        collector.append('BEGIN:VCARD')
        collector.append('VERSION:3.0')
        for key in ['FN', 'N']:
            try:
                collector.append(key + ':' + self[key][0][0])
            except IndexError:  # broken vcard without FN or N
                collector.append(key + ':')
        for prop in self.alt_keys():
            for line in self[prop]:

                types = self._line_helper(line)
                collector.append(prop + types + ':' + line[0])
        collector.append('END:VCARD')
        return '\n'.join(collector)

########NEW FILE########
__FILENAME__ = ui
#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The pycarddav interface to add, edit, or select a VCard.
"""

from __future__ import print_function

try:
    import sys
    import urwid

    import pycarddav

except ImportError, error:
    print(error)
    sys.exit(1)


class VCardWalker(urwid.ListWalker):
    """A walker to browse a VCard list.

    This walker returns a selectable Text for each of the passed VCard
    references. Either accounts or href_account_list needs to be supplied. If
    no list of tuples of references are passed to the constructor, then all
    cards from the specified accounts are browsed.
    """

    class Entry(urwid.Text):
        """A specialized Text which can be used for browsing in a list."""
        _selectable = True

        def keypress(self, _, key):
            return key

    class NoEntry(urwid.Text):
        """used as an indicator that no match was found"""
        _selectable = False

        def __init__(self):
            urwid.Text.__init__(self, 'No matching entries found.')

    def __init__(self, database, accounts=None, href_account_list=None,
                 searchtext=''):
        urwid.ListWalker.__init__(self)
        self._db = database
        self.update(accounts, href_account_list, searchtext)
        self._current = 0

    def update(self, accounts=None, href_account_list=None, searchtext=''):
        if (accounts is None and href_account_list is None and
                searchtext is None):
            raise Exception
        self._href_account_list = (href_account_list or
                                   self._db.search(searchtext, accounts))

    @property
    def selected_vcard(self):
        """Return the focused VCard."""
        return self._db.get_vcard_from_db(
            self._href_account_list[self._current].href,
            self._href_account_list[self._current].account)

    def get_focus(self):
        """Return (focused widget, focused position)."""
        return self._get_at(self._current)

    def set_focus(self, pos):
        """Focus on pos."""
        self._current = pos
        self._modified()

    def get_next(self, pos):
        """Return (widget after pos, position after pos)."""
        if pos >= len(self._href_account_list) - 1:
            return None, None
        return self._get_at(pos + 1)

    def get_prev(self, pos):
        """Return (widget before pos, position before pos)."""
        if pos <= 0:
            return None, None
        return self._get_at(pos - 1)

    def _get_at(self, pos):
        """Return a textual representation of the VCard at pos."""
        if pos >= len(self._href_account_list):
            return VCardWalker.NoEntry(), pos
        vcard = self._db.get_vcard_from_db(self._href_account_list[pos].href,
                                           self._href_account_list[pos].account
                                           )
        label = vcard.fname
        if vcard['EMAIL']:
            label += ' (%s)' % vcard['EMAIL'][0][0]
        return urwid.AttrMap(VCardWalker.Entry(label), 'list', 'list focused'), pos


class SearchField(urwid.WidgetWrap):
    """a search widget"""
    _selectable = True

    def __init__(self, updatefunc, window):
        self.updatefunc = updatefunc
        self.window = window
        self.edit = urwid.AttrWrap(urwid.Edit(caption=('', 'Search for: ')),
                                   'edit', 'edit focused')
        self.cancel = urwid.AttrWrap(
            urwid.Button(label='Cancel', on_press=self.destroy),
            'button', 'button focused')
        self.search = urwid.AttrWrap(
            urwid.Button(label='Search', on_press=self.search,
                         user_data=self.edit), 'button', 'button focused')
        buttons = urwid.GridFlow([self.cancel, self.search], 10, 3, 1, 'left')
        widget = urwid.Pile([self.edit,
                             urwid.Padding(buttons, 'right', 26, 1, 1, 1)])
        urwid.WidgetWrap.__init__(self, urwid.Padding(widget, 'center', left=1,
                                                      right=1))

    def search(self, button, text_edit):
        search_text = text_edit.get_edit_text()
        self.updatefunc(search_text)
        self.window.backtrack()

    def destroy(self, button):
        self.window.backtrack()


class Pane(urwid.WidgetWrap):
    """An abstract Pane to be used in a Window object."""
    def __init__(self, widget, title=None, description=None):
        self.widget = widget
        urwid.WidgetWrap.__init__(self, widget)
        self._title = title or ''
        self._description = description or ''
        self.window = None

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    def get_keys(self):
        """Return a description of the keystrokes recognized by this pane.

        This method returns a list of tuples describing the keys
        handled by a pane. This list is used to build a contextual
        pane help. Each tuple is a pair of a list of keys and a
        description.

        The abstract pane returns the default keys handled by the
        window. Panes which do not override there keys should extend
        this list.
        """
        return [(['up', 'down', 'pg.up', 'pg.down'],
                 'navigate through the fields.'),
                (['esc'], 'backtrack to the previous pane or exit.'),
                (['F1', '?'], 'open this pane help.')]


class HelpPane(Pane):
    """A contextual help screen."""
    def __init__(self, pane):
        content = []
        for key_list, description in pane.get_keys():
            key_text = []
            for key in key_list:
                if key_text:
                    key_text.append(', ')
                key_text.append(('bright', key))
            content.append(
                urwid.Columns(
                    [urwid.Padding(urwid.Text(key_text), left=10),
                     urwid.Padding(urwid.Text(description), right=10)]))

        Pane.__init__(self, urwid.ListBox(urwid.SimpleListWalker(content)),
                      'Help')


class VCardChooserPane(Pane):
    """A VCards chooser.

    This pane allows to browse a list of VCards. If no references are
    passed to the constructor, then the whole database is browsed. A
    VCard can be selected to be used in another pane, like the
    EditorPane.
    """
    def __init__(self, database, accounts=None, href_account_list=None):
        self.database = database
        self.accounts = accounts
        self._walker = VCardWalker(database,
                                   accounts=accounts,
                                   href_account_list=href_account_list)
        Pane.__init__(self, urwid.ListBox(self._walker), 'Browse...')

    def get_keys(self):
        keys = Pane.get_keys(self)
        keys.append(([' ', 'enter'], 'select a contact.'))
        keys.append((['/'], 'search for contacts'))
        return keys

    def keypress(self, size, key):
        self._w.keypress(size, key)
        if key in ['space', 'enter']:
            self.window.backtrack(self._walker.selected_vcard)
        if key in ['/']:
            self.search()
        else:
            return key

    def search(self):
        search = urwid.LineBox(SearchField(self.update, self.window))
        self.window.overlay(search, 'Search')

    def update(self, searchtext):
        self._walker = VCardWalker(self.database, accounts=self.accounts,
                                   searchtext=searchtext)
        self._w = urwid.ListBox(self._walker)


class EditorPane(Pane):
    """A VCard editor."""
    def __init__(self, database, account, vcard):
        self._vcard = vcard
        self._db = database
        self._account = account

        self._label = vcard.fname if vcard.fname else vcard['EMAIL'][0][0]
        self._fname_edit = urwid.Edit(u'', u'')
        self._lname_edit = urwid.Edit(u'', u'')
        self._email_edits = None

        Pane.__init__(self, self._build_ui(), 'Edit %s' % vcard.fname)

    def get_keys(self):
        keys = Pane.get_keys(self)
        keys.append((['F8'], 'save this contact.'))
        return keys

    def keypress(self, size, key):
        self._w.keypress(size, key)
        if key == 'f8':
            self._validate()
            self.window.backtrack()
        else:
            return key

    def on_button_press(self, button):
        if button.get_label() == 'Merge':
            self.window.open(VCardChooserPane(self._db,
                                              accounts=[self._account]),
                             self.on_merge_vcard)
        else:
            if button.get_label() == 'Store':
                self._validate()
            self.window.backtrack()

    def on_merge_vcard(self, vcard):
        # TODO: this currently merges only one email field, which is ok to use with mutt.
        if vcard:
            vcard['EMAIL'].append(self._vcard['EMAIL'][0])
            self._vcard = vcard
            self._w = self._build_ui()
            self._status = pycarddav.backend.CHANGED

    def _build_ui(self):
        content = []
        content.extend(self._build_names_section())
        content.extend(self._build_emails_section())
        content.extend(self._build_buttons_section())

        return urwid.ListBox(urwid.SimpleListWalker(content))

    def _build_names_section(self):
        names = self._vcard.name.split(';')
        if len(names) > 1:
            self._lname_edit.set_edit_text(names[0])
            self._fname_edit.set_edit_text(names[1])
        else:
            self._lname_edit.set_edit_text(u'')
            self._fname_edit.set_edit_text(names[0])

        return [urwid.Divider(),
                urwid.Columns([
                    ('fixed', 15, urwid.AttrWrap(urwid.Text(u'First Name'), 'line header')),
                    urwid.AttrWrap(self._fname_edit, 'edit', 'edit focused')]),
                urwid.Divider(),
                urwid.Columns([
                    ('fixed', 15, urwid.AttrWrap(urwid.Text(u'Last Name'), 'line header')),
                    urwid.AttrWrap(self._lname_edit, 'edit', 'edit focused')])]

    def _build_emails_section(self):
        self._email_edits = []
        content = []
        for mail in self._vcard['EMAIL']:
            edit = urwid.Edit('', mail[0])
            self._email_edits.append(edit)
            content.extend([
                urwid.Divider(),
                urwid.Columns([
                    ('fixed', 15, urwid.AttrWrap(urwid.Text(u'Email'), 'line header')),
                    urwid.AttrWrap(edit, 'edit', 'edit focused')])])

        return content

    def _build_buttons_section(self):
        buttons = [u'Cancel', u'Merge', u'Store']
        row = urwid.GridFlow([urwid.AttrWrap(urwid.Button(lbl, self.on_button_press),
                             'button', 'button focused') for lbl in buttons],
                             10, 3, 1, 'left')
        return [urwid.Divider('-', 1, 1),
                urwid.Padding(row, 'right', 13 * len(buttons), None, 1, 1)]

    def _validate(self):
        self._vcard.fname = ' '.join(
            [self._fname_edit.edit_text, self._lname_edit.edit_text])
        for i, edit in enumerate(self._email_edits):
            self._vcard['EMAIL'][i] = (edit.edit_text, self._vcard['EMAIL'][i][1])
        if(hasattr(self, '_status')):
            status = self._status
        else:
            status = pycarddav.backend.NEW
        self._db.update(self._vcard,
                        self._account,
                        self._vcard.href,
                        etag=self._vcard.etag,
                        status=status)


class Window(urwid.Frame):
    """The main user interface frame.

    A window is a frame which displays a header, a footer and a body.
    The header and the footer are handled by this object, and the body
    is the space where Panes can be displayed.

    Each Pane is an interface to interact with the database in one
    way: list the VCards, edit one VCard, and so on. The Window
    provides a mechanism allowing the panes to chain themselves, and
    to carry data between them.
    """
    PALETTE = [('header', 'white', 'black'),
               ('footer', 'white', 'black'),
               ('line header', 'black', 'white', 'bold'),
               ('bright', 'dark blue', 'white', ('bold', 'standout')),
               ('list', 'black', 'white'),
               ('list focused', 'white', 'light blue', 'bold'),
               ('edit', 'black', 'white'),
               ('edit focused', 'white', 'light blue', 'bold'),
               ('button', 'black', 'dark cyan'),
               ('button focused', 'white', 'light blue', 'bold')]

    def __init__(self):
        self._track = []
        self._title = u' {0} v{1}'.format(pycarddav.__productname__,
                                          pycarddav.__version__)

        header = urwid.AttrWrap(urwid.Text(self._title), 'header')
        footer = urwid.AttrWrap(urwid.Text(
            u' Use Up/Down/PgUp/PgDown:scroll. Esc: return. ?: help'),
            'footer')
        urwid.Frame.__init__(self, urwid.Text(''),
                             header=header,
                             footer=footer)
        self._original_w = None

    def open(self, pane, callback=None):
        """Open a new pane.

        The given pane is added to the track and opened. If the given
        callback is not None, it will be called when this new pane
        will be closed.
        """
        pane.window = self
        self._track.append((pane, callback))
        self._update(pane)

    def overlay(self, overlay_w, title):
        """put overlay_w as an overlay over the currently active pane
        """
        overlay = Pane(urwid.Overlay(urwid.Filler(overlay_w),
                                     self._get_current_pane(),
                                     'center', 60,
                                     'middle', 5), title)
        self.open(overlay)

    def backtrack(self, data=None):
        """Unstack the displayed pane.

        The current pane is discarded, and the previous one is
        displayed. If the current pane was opened with a callback,
        this callback is called with the given data (if any) before
        the previous pane gets redrawn.
        """
        _, cb = self._track.pop()
        if cb:
            cb(data)

        if self._track:
            self._update(self._get_current_pane())
        else:
            raise urwid.ExitMainLoop()

    def on_key_press(self, key):
        """Handle application-wide key strokes."""
        if key == 'esc':
            self.backtrack()
        elif key in ['f1', '?']:
            self.open(HelpPane(self._get_current_pane()))

    def _update(self, pane):
        self.header.w.set_text(u'%s | %s' % (self._title, pane.title))
        self.set_body(pane)

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None


def start_pane(pane):
    """Open the user interface with the given initial pane."""
    frame = Window()
    frame.open(pane)
    loop = urwid.MainLoop(frame, Window.PALETTE,
                          unhandled_input=frame.on_key_press)
    loop.run()

########NEW FILE########
__FILENAME__ = pycarddav_test
# vim: set fileencoding=utf-8 :
"""these test should test code defined in pycarddav/__init__.py (mainly
the configuration parsing)"""
import os.path
import sys

from pycarddav import ConfigurationParser
from pycarddav import SyncConfigurationParser

# some helper functions

def get_basename():
    """find the base path so we can build proper paths, needed so we can start
    the tests from anywhere"""
    curdir = os.path.basename(os.path.abspath(os.path.curdir))
    if os.path.isdir('tests') and curdir == 'pycarddav':
        basepath = 'tests/'
    elif os.path.isdir('assets') and curdir == 'tests':
        basepath = './'
    elif os.path.isdir('pycarddav') and curdir == 'pycarddav':
        basepath = 'pycarddav/tests/'
    elif curdir == 'local':
        basepath = '../'
    else:
        raise Exception("don't know where I'm")
    return basepath

basepath = get_basename()



def test_basic_config():
    """testing the basic configuration parser
    this rather complicated setup is needed, since py2.6 and py2.7 return
    the accounts list in different orders"""
    sys.argv = ['pycardsyncer', '-c',
                '{0}/assets/configs/base.conf'.format(basepath)]
    conf_parser = ConfigurationParser('let\'s do a test', check_accounts=False)
    conf = conf_parser.parse()

    assert conf.debug == False
    assert conf.sqlite.path == '/home/testman/.pycard/abook.db'
    assert conf.filename.endswith('tests//assets/configs/base.conf') == True
    def assert_work(accounts_conf):
        assert accounts_conf.write_support == False
        assert accounts_conf.resource == 'http://test.com/abook/collection'
        assert accounts_conf.name == 'work'
        assert accounts_conf.passwd == 'foobar'
        assert accounts_conf.verify == False
        assert accounts_conf.auth == 'basic'
        assert accounts_conf.user == 'testman'

    def assert_davical(accounts_conf):
        assert accounts_conf.write_support == True
        assert accounts_conf.resource == 'https://carddavcentral.com:4443/caldav.php/tester/abook/'
        assert accounts_conf.name == 'davical'
        assert accounts_conf.passwd == 'barfoo23'
        assert accounts_conf.verify == '/home/testman/.pycard/cacert.pem'
        assert accounts_conf.auth == 'digest'
        assert accounts_conf.user == 'tester'

    count = 0
    for one in conf.accounts:
        if one.name == 'work':
            assert_work(one)
            count += 1
        elif one.name == 'davical':
            assert_davical(one)
            count += 1
        elif one.name == 'work_no_verify':
            assert one.verify == True
            count += 1
        else:
            assert True == 'this should not be reached'
    assert count == 3


def test_basic_debug():
    """testing the basic configuration parser"""
    sys.argv = ['pycardsyncer', '-c',
                '{0}/assets/configs/base.conf'.format(basepath),
                '--debug']
    conf_parser = ConfigurationParser('let\'s do a test', check_accounts=False)
    conf = conf_parser.parse()
    assert conf.debug == True
    assert conf.sqlite.path == '/home/testman/.pycard/abook.db'
    assert conf.filename.endswith('tests//assets/configs/base.conf') == True
    def assert_work(accounts_conf):
        assert accounts_conf.write_support == False
        assert accounts_conf.resource == 'http://test.com/abook/collection'
        assert accounts_conf.name == 'work'
        assert accounts_conf.passwd == 'foobar'
        assert accounts_conf.verify == False
        assert accounts_conf.auth == 'basic'
        assert accounts_conf.user == 'testman'

    def assert_davical(accounts_conf):
        assert accounts_conf.write_support == True
        assert accounts_conf.resource == 'https://carddavcentral.com:4443/caldav.php/tester/abook/'
        assert accounts_conf.name == 'davical'
        assert accounts_conf.passwd == 'barfoo23'
        assert accounts_conf.verify == '/home/testman/.pycard/cacert.pem'
        assert accounts_conf.auth == 'digest'
        assert accounts_conf.user == 'tester'

    count = 0
    for one in conf.accounts:
        if one.name == 'work':
            assert_work(one)
            count += 1
        elif one.name == 'davical':
            assert_davical(one)
            count += 1
        elif one.name == 'work_no_verify':
            assert one.verify == True
            count += 1
        else:
            assert True == 'this should not be reached'
    assert count == 3


def test_sync_conf_parser():
    """testing the basic configuration parser"""
    sys.argv = ['pycardsyncer', '-c',
                '{0}/assets/configs/base.conf'.format(basepath),
                '-a', 'work',]
    conf_parser = SyncConfigurationParser()
    conf = conf_parser.parse()
    assert conf.debug == False
    assert conf.sqlite.path == '/home/testman/.pycard/abook.db'
    assert conf.filename.endswith('tests//assets/configs/base.conf') == True
    assert conf.sync.accounts == set(['work'])
    def assert_work(accounts_conf):
        assert accounts_conf.write_support == False
        assert accounts_conf.resource == 'http://test.com/abook/collection/'
        assert accounts_conf.name == 'work'
        assert accounts_conf.passwd == 'foobar'
        assert accounts_conf.verify == False
        assert accounts_conf.auth == 'basic'
        assert accounts_conf.user == 'testman'

    def assert_davical(accounts_conf):
        assert accounts_conf.write_support == True
        assert accounts_conf.resource == 'https://carddavcentral.com:4443/caldav.php/tester/abook/'
        assert accounts_conf.name == 'davical'
        assert accounts_conf.passwd == 'barfoo23'
        assert accounts_conf.verify == '/home/testman/.pycard/cacert.pem'
        assert accounts_conf.auth == 'digest'
        assert accounts_conf.user == 'tester'

    count = 0
    for one in conf.accounts:
        if one.name == 'work':
            assert_work(one)
            count += 1
        elif one.name == 'davical':
            assert_davical(one)
            count += 1
        elif one.name == 'work_no_verify':
            assert one.verify == True
            count += 1
        else:
            assert True == 'this should not be reached'
    assert count == 3

########NEW FILE########
__FILENAME__ = pycard_test
# vim: set fileencoding=utf-8 :
import pycarddav.model
import pycarddav.backend as backend
import os.path
import pytest
import random


# some helper functions

def get_basename():
    curdir = os.path.basename(os.path.abspath(os.path.curdir))
    if os.path.isdir('tests') and curdir == 'pycarddav':
        basepath = 'tests/'
    elif os.path.isdir('assets') and curdir == 'tests':
        basepath = './'
    elif os.path.isdir('pycarddav') and curdir == 'pycarddav':
        basepath = 'pycarddav/tests/'
    elif curdir == 'local':
        basepath = '../'
    else:
        raise Exception("don't know where I'm")
    return basepath

basepath = get_basename()


def get_vcard(cardname):
    """gets a vcard from the assets directory"""
    filename = basepath + 'assets/' + cardname + '.vcf'
    with file(filename) as vcard:
            cardstring = vcard.read()
    return pycarddav.model.vcard_from_string(cardstring)


def get_output(function_name):
    with file(basepath + 'local/output/' + function_name + '.out') as output_file:
        output = output_file.readlines()
    return ''.join(output).strip('\n')

# \helper functions


def pytest_funcarg__emptydb(request):
    mydb = backend.SQLiteDb(db_path=':memory:')
    mydb.check_account_table('test', 'http://test.com')
    return mydb

## tests


def test_serialize_to_vcf():
    random.seed(1)
    assert get_vcard('gödel').vcf.encode('utf-8') == get_output('serialize_to_vcf')


def test_broken_nobegin():
    with pytest.raises(Exception) as error:
        get_vcard('broken_nobegin')
        print error

def test_db_init(emptydb):
    assert emptydb._dump('test') == list()


def test_vcard_insert1(emptydb):
    random.seed(1)
    emptydb.check_account_table('test', 'http://test.com')
    emptydb.update(get_vcard('gödel').vcf, 'test', href='/something.vcf')
    assert str(emptydb._dump('test')) == get_output('vcard_insert1')


def test_vcard_insert_with_status(emptydb):
    random.seed(1)
    emptydb.check_account_table('test', 'http://test.com')
    emptydb.update(get_vcard('gödel').vcf,
                   'test',
                   href='/something.vcf',
                   status=backend.NEW)
    assert str(emptydb._dump('test')) == get_output('vcard_insert_with_status')

########NEW FILE########
__FILENAME__ = test_carddav
# vim: set fileencoding=utf-8 :
import vagrant
import pytest
import pycarddav.carddav as carddav

HANZ_BASE = 'http://localhost:8080/davical/caldav.php/hanz/addresses/'
LENNA_BASE = 'http://localhost:8080/davical/caldav.php/lenna/addresses/'


def test_url_does_not_exist():
    vbox = vagrant.Vagrant()
    vbox.up()
    with pytest.raises(carddav.requests.exceptions.HTTPError):
        carddav.PyCardDAV('http://localhost:8080/doesnotexist/')


def test_no_auth():
    vbox = vagrant.Vagrant()
    vbox.up()
    with pytest.raises(Exception):
        carddav.PyCardDAV(HANZ_BASE)


def test_basic_auth():
    vbox = vagrant.Vagrant()
    vbox.up()
    syncer = carddav.PyCardDAV(LENNA_BASE, user='lenna', passwd='test')
    abook = syncer.get_abook()
    assert abook == dict()

########NEW FILE########
