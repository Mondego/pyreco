__FILENAME__ = Config
#-*- coding: utf-8 -*-
# 
# Config.py
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import ConfigParser
import os

from os.path import dirname, exists

class Config(object):
    def __init__(self, configfile):
        self._configfile = configfile

        if not exists(configfile):
            self.set_default()
        else:
            self._config = ConfigParser.RawConfigParser()
            self._config.read(self._configfile)

    def __getattr__(self, name):
        value = self._config.get('Settings', name)
        return self.parseBool(value)

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self._config.set('Settings', name, value)
            self.store_config()
        self.__dict__[name] = self.parseBool(value)

    def set_default(self):
        """Set config to default."""
        try:
            os.makedirs(dirname(self._configfile))
        except: pass

        self._config = ConfigParser.RawConfigParser()
        self._config.add_section('Settings')
        self._config.set('Settings', 'UpdateManPath', 'false')
        self._config.set('Settings', 'Pager', 'system')

        with open(self._configfile, 'w') as f:
            self._config.write(f)

    def store_config(self):
        """Store config back to file."""
        try:
            os.makedirs(dirname(self._configfile))
        except: pass

        with open(self._configfile, 'w') as f:
            self._config.write(f)

    def parseBool(self, val):
        if type(val) == str:
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
        return val

########NEW FILE########
__FILENAME__ = cppman
#-*- coding: utf-8 -*-
# 
# cppman.py 
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import gzip
import os
import os.path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib

import Environ
import Formatter
from Crawler import Crawler

class cppman(Crawler):
    """Manage cpp man pages, indexes"""
    def __init__(self, forced=False):
        Crawler.__init__(self)
        self.results = set()
        self.forced = forced
        self.success_count = None
        self.failure_count = None

        self.blacklist = [
        ]
        self.name_exceptions = [
            'http://www.cplusplus.com/reference/string/swap/'
        ]

    def extract_name(self, data):
        """Extract man page name from cplusplus web page."""
        name = re.search('<h1>(.+?)</h1>', data).group(1)
        name = re.sub(r'<([^>]+)>', r'', name)
        name = re.sub(r'&gt;', r'>', name)
        name = re.sub(r'&lt;', r'<', name)
        return name

    def rebuild_index(self):
        """Rebuild index database from cplusplus.com."""
        try:
            os.remove(Environ.index_db_re)
        except: pass
        self.db_conn = sqlite3.connect(Environ.index_db_re)
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.execute('CREATE TABLE CPPMAN (name VARCHAR(255), '
                               'url VARCHAR(255))')
        try:
            self.add_url_filter('\.(jpg|jpeg|gif|png|js|css|swf)$')
            self.set_follow_mode(Crawler.F_SAME_PATH)
            self.crawl('http://www.cplusplus.com/reference/')
            for name, url in self.results:
                self.insert_index(name, url)
            self.db_conn.commit()

            # Rename dumplicate entries
            dumplicates = self.db_cursor.execute('SELECT name, COUNT(name) '
                                                 'AS NON '
                                                 'FROM CPPMAN '
                                                 'GROUP BY NAME '
                                                 'HAVING (NON > 1)').fetchall()
            for name, num in dumplicates:
                dump = self.db_cursor.execute('SELECT name, url FROM CPPMAN '
                                              'WHERE name="%s"'
                                              % name).fetchall()
                for n, u in dump:
                    if u not in self.name_exceptions:
                        n2 = n[5:] if n.startswith('std::') else n
                        try:
                            group = re.search('/([^/]+)/%s/$' % n2, u).group(1)
                        except Exception:
                            group = re.search('/([^/]+)/[^/]+/$', u).group(1)

                        new_name = '%s (%s)' % (n, group)
                        self.db_cursor.execute('UPDATE CPPMAN '
                                               'SET name="%s", url="%s" '
                                               'WHERE url="%s"' %
                                               (new_name, u, u))
            self.db_conn.commit()
        except KeyboardInterrupt:
            os.remove(Environ.index_db_re)
            raise KeyboardInterrupt
        finally:
            self.db_conn.close()

    def process_document(self, doc):
        """callback to insert index"""
        if doc.url not in self.blacklist:
            print "Indexing '%s' ..." % doc.url
            name = self.extract_name(doc.text)
            self.results.add((name, doc.url))
        else:
            print "Skipping blacklisted page '%s' ..." % doc.url
            return None

    def insert_index(self, name, url):
        """callback to insert index"""
        self.db_cursor.execute('INSERT INTO CPPMAN (name, url) VALUES '
                               '("%s", "%s")' % (name, url))

    def cache_all(self):
        """Cache all available man pages from cplusplus.com"""
        print 'By defualt, cppman fetch pages on the fly if coressponding '\
            'page is not found in the cache. The "cache-all" option is only '\
            'useful if you want to view man pages offline. ' \
            'Caching all contents from cplusplus.com will serveral'\
            'minutes, do you want to continue [Y/n]?',

        respond = raw_input()
        if respond.lower() not in ['y', 'ye', 'yes']:
            raise KeyboardInterrupt

        try:
            os.makedirs(Environ.man_dir)
        except: pass

        self.success_count = 0
        self.failure_count = 0

        if not os.path.exists(Environ.index_db):
            raise RuntimeError("can't find index.db")

        conn = sqlite3.connect(Environ.index_db)
        cursor = conn.cursor()

        data = cursor.execute('SELECT name, url FROM CPPMAN').fetchall()

        for name, url in data:
            try:
                print 'Caching %s ...' % name
                self.cache_man_page(url, name)
            except Exception, e:
                print 'Error caching %s ...', name
                self.failure_count += 1
            else:
                self.success_count += 1
        conn.close()

        print '\n%d manual pages cached successfully.' % self.success_count
        print '%d manual pages failed to cache.' % self.failure_count
        self.update_mandb(False)

    def cache_man_page(self, url, name=None):
        """callback to cache new man page"""
        data = urllib.urlopen(url).read()
        groff_text = Formatter.cplusplus2groff(data)
        if not name:
            name = self.extract_name(data).replace('/', '_')

        # Skip if already exists, override if forced flag is true
        outname = Environ.man_dir + name + '.3.gz'
        if os.path.exists(outname) and not self.forced:
            return
        f = gzip.open(outname, 'w')
        f.write(groff_text)
        f.close()

    def clear_cache(self):
        """Clear all cache in man3"""
        shutil.rmtree(Environ.man_dir)

    def man(self, pattern):
        """Call viewer.sh to view man page"""
        try:
            os.makedirs(Environ.man_dir)
        except: pass

        avail = os.listdir(Environ.man_dir)

        if not os.path.exists(Environ.index_db):
            raise RuntimeError("can't find index.db")

        conn = sqlite3.connect(Environ.index_db)
        cursor = conn.cursor()

        # Try direct match
        try:
            page_name, url = cursor.execute('SELECT name,url FROM CPPMAN WHERE'
                    ' name="%s" ORDER BY LENGTH(name)' % pattern).fetchone()
        except TypeError:
            # Try standard library
            try:
                page_name, url = cursor.execute('SELECT name,url FROM CPPMAN'
                        ' WHERE name="std::%s" ORDER BY LENGTH(name)'
                        % pattern).fetchone()
            except TypeError:
                try:
                    page_name, url = cursor.execute('SELECT name,url FROM '
                        'CPPMAN WHERE name LIKE "%%%s%%" ORDER BY LENGTH(name)'
                        % pattern).fetchone()
                except TypeError:
                    raise RuntimeError('No manual entry for ' + pattern)
        finally:
            conn.close()

        page_name = page_name.replace('/', '_')
        if page_name + '.3.gz' not in avail or self.forced:
            self.cache_man_page(url, page_name)
            self.update_mandb()

        pager = Environ.pager if sys.stdout.isatty() else Environ.renderer

        # Call viewer
        pid = os.fork()
        if pid == 0:
            os.execl('/bin/sh', '/bin/sh', pager,
                     Environ.man_dir + page_name + '.3.gz',
                     str(Formatter.get_width()), Environ.pager_config,
                     page_name)
        return pid

    def find(self, pattern):
        """Find pages in database."""

        if not os.path.exists(Environ.index_db):
            raise RuntimeError("can't find index.db")

        conn = sqlite3.connect(Environ.index_db)
        cursor = conn.cursor()
        selected = cursor.execute('SELECT name,url FROM CPPMAN WHERE name '
                'LIKE "%%%s%%" ORDER BY LENGTH(name)' % pattern).fetchall()

        pat = re.compile('(%s)' % pattern, re.I)

        if selected:
            for name, url in selected:
                if os.isatty(sys.stdout.fileno()):
                    print pat.sub(r'\033[1;31m\1\033[0m', name)
                else:
                    print name
        else:
            raise RuntimeError('%s: nothing appropriate.' % pattern)

    def update_mandb(self, quiet=True):
        """Update mandb."""
        if not Environ.config.UpdateManPath:
            return
        print '\nrunning mandb...'
        cmd = 'mandb %s' % (' -q' if quiet else '')
        handle = subprocess.Popen(cmd, shell=True).wait()

########NEW FILE########
__FILENAME__ = Crawler
#-*- coding: utf-8 -*-
# 
# Crawler.py
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import httplib
import re
import sys

from os.path import join, dirname, normpath
from threading import Thread, Lock
from urllib import quote

class Document(object):
    def __init__(self, res, url):
        self.url = url
        self.query = '' if not '?' in url else url.split('?')[-1]
        self.status = res.status
        self.text = res.read()

class Crawler(object):
    '''
    A Crawler that crawls through cplusplus.com
    '''
    F_ANY, F_SAME_DOMAIN, F_SAME_HOST, F_SAME_PATH = range(4)
    def __init__(self):
        self.host = None
        self.visited = {}
        self.targets = set()
        self.threads = []
        self.concurrency = 0
        self.max_outstanding = 16

        self.follow_mode = self.F_SAME_HOST
        self.content_type_filter = '(text/html)'
        self.url_filters = []
        self.prefix_filter = '^(#|javascript:|mailto:)'

        self.targets_lock = Lock()
        self.concurrency_lock = Lock()
        self.process_lock = Lock()

    def set_content_type_filter(self, cf):
        self.content_type_filter = '(%s)' % ('|'.join(cf))

    def add_url_filter(self, uf):
        self.url_filters.append(uf)

    def set_follow_mode(self, mode):
        if mode > 5:
            raise RuntimeError('invalid follow mode.')
        self.follow_mode = mode

    def set_concurrency_level(self, level):
        self.max_outstanding = level

    def follow_link(self, url, link):
        # Skip prefix
        if re.search(self.prefix_filter, link):
            return None

        # Filter url
        for f in self.url_filters:
            if re.search(f, link):
                return None

        rx = re.match('(https?://)([^/]+)([^\?]*)(\?.*)?', url)
        url_proto = rx.group(1)
        url_host = rx.group(2)
        url_path = rx.group(3) if len(rx.group(3)) > 0 else '/'
        url_dir_path = dirname(url_path)

        rx = re.match('((https?://)([^/]+))?([^\?]*)(\?.*)?', link)
        link_full_url = rx.group(1) != None
        link_proto = rx.group(2) if rx.group(2) else url_proto
        link_host = rx.group(3) if rx.group(3) else url_host
        link_path = quote(rx.group(4)) if rx.group(4) else url_path
        link_query = rx.group(5) if rx.group(5) else ''
        link_dir_path = dirname(link_path)

        if not link_full_url and not link.startswith('/'):
            link_path = normpath(join(url_dir_path, link_path))

        link_url = link_proto + link_host + link_path + link_query

        if self.follow_mode == self.F_ANY:
            return link_url
        elif self.follow_mode == self.F_SAME_DOMAIN:
            return link_url if self.host == link_host else None
        elif self.follow_mode == self.F_SAME_HOST:
            return link_url if self.host == link_host else None
        elif self.follow_mode == self.F_SAME_PATH:
            if self.host == link_host and \
                    link_dir_path.startswith(self.dir_path):
                return link_url
            else:
                return None

    def add_target(self, target):
        if not target:
            return

        self.targets_lock.acquire()
        if self.visited.has_key(target):
            self.targets_lock.release()
            return
        self.targets.add(target)
        self.targets_lock.release()

    def crawl(self, url):
        self.root_url = url

        rx = re.match('(https?://)([^/]+)([^\?]*)(\?.*)?', url)
        self.proto = rx.group(1)
        self.host = rx.group(2)
        self.path = rx.group(3)
        self.dir_path = dirname(self.path)
        self.query = rx.group(4)

        self.targets.add(url)
        self.spawn_new_worker()

        while self.threads:
            try:
                for t in self.threads:
                    t.join(1)
                    if not t.isAlive():
                        self.threads.remove(t)
            except KeyboardInterrupt, e:
                sys.exit(1)

    def spawn_new_worker(self):
        self.concurrency_lock.acquire()
        if self.concurrency >= self.max_outstanding:
            self.concurrency_lock.release()
            return
        self.concurrency += 1
        t = Thread(target=self.worker, args=(self.concurrency,))
        t.daemon = True
        self.threads.append(t)
        t.start()
        self.concurrency_lock.release()

    def worker(self, sid):
        while self.targets:
            try:
                self.targets_lock.acquire()
                url = self.targets.pop()
                self.visited[url] = True
                self.targets_lock.release()

                rx = re.match('https?://([^/]+)(.*)', url)
                host = rx.group(1)
                path = rx.group(2)

                conn = httplib.HTTPConnection(host)
                conn.request('GET', path)
                res = conn.getresponse()

                if res.status == 301 or res.status == 302:
                    rlink = self.follow_link(url, res.getheader('location'))
                    self.add_target(rlink)
                    continue

                # Check content type
                if not re.search(self.content_type_filter,
                        res.getheader('Content-Type')):
                    continue

                doc = Document(res, url)
                self.process_lock.acquire()
                self.process_document(doc)
                self.process_lock.release()

                # Make unique list
                links = re.findall('''href\s*=\s*['"]\s*([^'"]+)['"]''',
                        doc.text, re.S)
                links = list(set(links))

                for link in links:
                    rlink = self.follow_link(url, link.strip())
                    self.add_target(rlink)

                if self.concurrency < self.max_outstanding:
                    self.spawn_new_worker()
            except KeyError as e:
                # Pop from an empty set
                break
            except (httplib.HTTPException, EnvironmentError) as e:
                #print '%s, retrying' % str(e)
                self.targets_lock.acquire()
                self.targets.add(url)
                self.targets_lock.release()

        self.concurrency_lock.acquire()
        self.concurrency -= 1
        self.concurrency_lock.release()

    def process_document(self, doc):
        print 'GET', doc.status, doc.url

########NEW FILE########
__FILENAME__ = Environ
#-*- coding: utf-8 -*-
# 
# Environ.py
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import os
import platform
import sys

from os.path import expanduser, abspath, normpath, dirname, exists, join

import Config
from . import get_lib_path

HOME = expanduser('~')

man_dir = HOME + '/.local/share/man/man3/'
config_dir = HOME + '/.config/cppman/'
config_file = config_dir + 'cppman.cfg'

config = Config.Config(config_file)

try:
    os.makedirs(config_dir)
except: pass

index_db_re = normpath(join(config_dir, 'index.db'))

index_db = index_db_re if exists(index_db_re) else get_lib_path('lib/index.db')

pager_config = get_lib_path('lib/cppman.vim')

if config.pager == 'vim':
    pager = get_lib_path('lib/pager_vim.sh')
elif config.pager == 'less':
    pager = get_lib_path('lib/pager_less.sh')
else:
    pager = get_lib_path('lib/pager_system.sh')

renderer = get_lib_path('lib/render.sh')

# Add ~/.local/share/man to $HOME/.manpath
def mandb_changed():
    manpath_file = normpath(join(HOME, '.manpath'))
    manpath = '.local/share/man'
    lines = []
    try:
        with open(manpath_file, 'r') as f:
            lines = f.readlines()
    except IOError:
        if not config.UpdateManPath:
            return

    has_path = any([manpath in l for l in lines])

    with open(manpath_file, 'w') as f:
        if config.UpdateManPath:
            if not has_path:
                lines.append('MANDATORY_MANPATH\t%s\n' %
                             normpath(join(HOME, manpath)))
        else:
            new_lines = []
            for line in lines:
                if manpath not in line:
                    new_lines.append(line)
            lines = new_lines

        for line in lines:
            f.write(line)

########NEW FILE########
__FILENAME__ = Formatter
#-*- coding: utf-8 -*-
# 
# Formatter.py - format html from cplusplus.com to groff syntax
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import datetime
import fcntl
import re
import struct
import subprocess
import sys
import termios
import urllib

from TableParser import parse_table

# Format replacement RE list
# The '.SE' pseudo macro is described in the function: cplusplus2groff
pre_rps = [
        # Snippet, ugly hack: we don't want to treat code listing as table
        (r'<table class="snippet">(.*?)</table>',
         r'\n.in +2n\n\1\n.in\n.sp\n', re.S),
]

rps = [
        # Header, Name
        (r'\s*<div id="I_type"[^>]*>(.*?)\s*</div>\s*'
         r'<div id="I_file"[^>]*>(.*?)</div>\s*'
         r'<h1>(.*?)</h1>\s*<div class="C_prototype"[^>]*>'
         r'(.*?)</div>\s*<div id="I_description"[^>]*>(.*?)</div>',
         r'.TH "\3" 3 "%s" "cplusplus.com" "C++ Programmer\'s Manual"\n'
         r'\n.SH NAME\n\3 - \5\n'
         r'\n.SE\n.SH TYPE\n\1\n'
         r'\n.SE\n.SH SYNOPSIS\n#include \2\n.sp\n\4\n'
         r'\n.SE\n.SH DESCRIPTION\n' % datetime.date.today(), re.S),
        (r'\s*<div id="I_type"[^>]*>(.*?)\s*</div>\s*'
         r'<div id="I_file"[^>]*>(.*?)</div>\s*'
         r'<h1>(.*?)</h1>\s*'
         r'<div id="I_description"[^>]*>(.*?)</div>',
         r'.TH "\3" 3 "%s" "cplusplus.com" "C++ Programmer\'s Manual"\n'
         r'\n.SH NAME\n\3 - \4\n'
         r'\n.SE\n.SH TYPE\n\1\n'
         r'\n.SE\n.SH SYNOPSIS\n#include \2\n.sp\n'
         r'\n.SE\n.SH DESCRIPTION\n' % datetime.date.today(), re.S),
        (r'\s*<div id="I_type"[^>]*>(.*?)\s*</div>\s*<h1>(.*?)</h1>\s*'
         r'<div id="I_description"[^>]*>(.*?)</div>',
         r'.TH "\2" 3 "%s" "cplusplus.com" "C++ Programmer\'s Manual"\n'
         r'\n.SH NAME\n\2 - \3\n'
         r'\n.SE\n.SH TYPE\n\1\n'
         r'\n.SE\n.SH DESCRIPTION\n' % datetime.date.today(), re.S),
        (r'\s*<div id="I_type"[^>]*>(.*?)\s*</div>\s*<h1>(.*?)</h1>\s*'
         r'<div id="I_file"[^>]*>(.*?)</div>\s*<div id="I_description"[^>]*>'
         '(.*?)</div>',
         r'.TH "\2" 3 "%s" "cplusplus.com" "C++ Programmer\'s Manual"\n'
         r'\n.SH NAME\n\2 - \4\n'
         r'\n.SE\n.SH TYPE\n\1\n'
         r'\n.SE\n.SH DESCRIPTION\n' % datetime.date.today(), re.S),
        (r'\s*<div id="I_type"[^>]*>(.*?)\s*</div>\s*<h1>(.*?)</h1>\s*'
         r'<div class="C_prototype"[^>]*>(.*?)</div>\s*'
         r'<div id="I_description"[^>]*>(.*?)</div>',
         r'.TH "\2" 3 "%s" "cplusplus.com" "C++ Programmer\'s Manual"\n'
         r'\n.SH NAME\n\2 - \4\n'
         r'\n.SE\n.SH TYPE\n\1\n'
         r'\n.SE\n.SH SYNOPSIS\n\3\n'
         r'\n.SE\n.SH DESCRIPTION\n' % datetime.date.today(), re.S),
        (r'<span class="C_ico cpp11warning".*?>', r' [C++11]', re.S),
        # Remove empty #include
        (r'#include \n.sp\n', r'', 0),
        # Remove empty sections
        (r'\n.SH (.+?)\n+.SE', r'', 0),
        # Section headers
        (r'.*<h3>(.+?)</h3>', r'\n.SE\n.SH "\1"\n', 0),
        # 'ul' tag
        (r'<ul>', r'\n.in +2n\n.sp\n', 0),
        (r'</ul>', r'\n.in\n', 0),
        # 'li' tag
        (r'<li>(.+?)</li>', r'* \1\n.sp\n', 0),
        # 'pre' tag
        (r'<pre\s*>(.+?)</pre\s*>', r'\n.nf\n\1\n.fi\n', re.S),
        # Subsections
        (r'<b>(.+?)</b>:<br>', r'.SS \1\n', 0),
        # Member functions / See Also table
        ## Without C++11 tag
        (r'<dl class="links"><dt>.*?<b>([^ ]+?)</b>.*?</dt><dd>(.*?)'
         r'<span class="typ">(.*?)</span></dd></dl>',
         r'\n.IP "\1(3)"\n\2 \3\n', 0),
        ## With C++11 tag
        (r'<dl class="links"><dt>.*?<b>([^ ]+?) <b class="C_cpp11" '
         r'title="(.+?)">\W*</b>.*?</dt><dd>(.*?)'
         r'<span class="typ">(.*?)</span></dd></dl>',
         r'\n.IP "\1(3) [\2]"\n\3 \4\n', 0),
        # Footer
        (r'<div id="CH_bb">.*$',
         r'\n.SE\n.SH REFERENCE\n'
         r'cplusplus.com, 2000-2014 - All rights reserved.', re.S),
        # C++ version tag
        (r'<div title="(C\+\+..)".*?>', r'.sp\n\1\n', 0),
        # 'br' tag
        (r'<br>', r'\n.br\n', 0),
        (r'\n.br\n.br\n', r'\n.sp\n', 0),
        # 'dd' 'dt' tag
        (r'<dt>(.+?)</dt>\s*<dd>(.+?)</dd>', r'.IP "\1"\n\2\n', re.S),
        # Bold
        (r'<strong>(.+?)</strong>', r'\n.B \1\n', 0),
        # Remove row number in EXAMPLE
        (r'<td class="rownum">.*?</td>', r'', re.S),
        # Any other tags
        (r'<script[^>]*>[^<]*</script>', r'', 0),
        (r'<.*?>', r'', re.S),
        # Misc
        (r'&lt;', r'<', 0),
        (r'&gt;', r'>', 0),
        (r'&amp;', r'&', 0),
        (r'&nbsp;', r' ', 0),
        (r'\\([^\^nE])', r'\\\\\1', 0),
        #: vector::data SYNOPSIS section has \x0d separting two lines
        (u'\x0d([^)])', r'\n.br\n\1', 0),
        (u'\x0d', r'', 0),
        (r'>/">', r'', 0),
        (r'/">', r'', 0),
        # Remove empty lines
        (r'\n\s*\n+', r'\n', 0),
        (r'\n\n+', r'\n', 0),
        # Preserve \n" in EXAMPLE
        (r'\\n"', r'\en"', 0),
      ]

def cplusplus2groff(data):
    """Convert HTML text from cplusplus.com to Groff-formated text."""
    # Remove sidebar
    try:
        data = data[data.index('<div class="C_doc">'):]
    except ValueError: pass

    # Replace all
    for rp in pre_rps:
        data = re.compile(rp[0], rp[2]).sub(rp[1], data)

    for table in re.findall(r'<table.*?>.*?</table>', data, re.S):
        tbl = parse_table(table)
        # Escape column with '.' as prefix
        tbl = re.compile(r'T{\n(\..*?)\nT}', re.S).sub(r'T{\n\E \1\nT}', tbl)
        data = data.replace(table, tbl)

    # Pre replace all
    for rp in rps:
        data = re.compile(rp[0], rp[2]).sub(rp[1], data)

    # Upper case all section headers
    for st in re.findall(r'.SH .*\n', data):
        data = data.replace(st, st.upper())

    # Add tags to member/inherited member functions
    # e.g. insert -> vector::insert
    #
    # .SE is a pseudo macro I created which means 'SECTION END'
    # The reason I use it is because I need a marker to know where section ends.
    # re.findall find patterns which does not overlap, which means if I do this:
    # secs = re.findall(r'\n\.SH "(.+?)"(.+?)\.SH', data, re.S)
    # re.findall will skip the later .SH tag and thus skip the later section.
    # To fix this, '.SE' is used to mark the end of the section so the next
    # '.SH' can be find by re.findall

    page_type =  re.search(r'\n\.SH TYPE\n(.+?)\n', data)
    if page_type and 'class' in page_type.group(1):
        class_name = re.search(r'\n\.SH NAME\n(?:.*::)?(.+?) ', data).group(1)

        secs = re.findall(r'\n\.SH "(.+?)"(.+?)\.SE', data, re.S)

        for sec, content in secs:
            # Member functions
            if 'MEMBER' in sec and 'INHERITED' not in sec and\
               sec != 'MEMBER TYPES':
                contents = re.sub(r'\n\.IP "([^:]+?)"', r'\n\.IP "%s::\1"'
                                  % class_name, content)
                # Replace (constructor) (destructor)
                contents = re.sub(r'\(constructor\)', r'%s' % class_name,
                                  contents)
                contents = re.sub(r'\(destructor\)', r'~%s' % class_name,
                                  contents)
                data = data.replace(content, contents)
            # Inherited member functions
            elif 'MEMBER' in sec and 'INHERITED' in sec:
                inherit = re.search(r'.+?INHERITED FROM (.+)',
                                    sec).group(1).lower()
                contents = re.sub(r'\n\.IP "(.+)"', r'\n\.IP "%s::\1"'
                                  % inherit, content)
                data = data.replace(content, contents)

    # Remove pseudo macro '.SE'
    data = data.replace('\n.SE', '')

    return data

def groff2man(data):
    """Read groff-formated text and output man pages."""
    width = get_width()

    cmd = 'groff -t -Tascii -m man -rLL=%dn -rLT=%dn' % (width, width)
    handle = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
    man_text, stderr = handle.communicate(data)
    return man_text

def cplusplus2man(data):
    """Convert HTML text from cplusplus.com to man pages."""
    groff_text = cplusplus2groff(data)
    man_text = groff2man(groff_text)
    return man_text

def get_width():
    """Get terminal width"""
    # Get terminal size
    ws = struct.pack("HHHH", 0, 0, 0, 0)
    ws = fcntl.ioctl(0, termios.TIOCGWINSZ, ws)
    lines, columns, x, y = struct.unpack("HHHH", ws)
    width = columns * 39 / 40
    if width >= columns -2: width = columns -2
    return width

def func_test():
    """Test if there is major format changes in cplusplus.com"""
    ifs = urllib.urlopen('http://www.cplusplus.com/printf')
    result = cplusplus2groff(ifs.read())
    assert '.SH NAME' in result
    assert '.SH TYPE' in result
    assert '.SH DESCRIPTION' in result

def test():
    """Simple Text"""
    name = raw_input('What manual page do you want? ')
    ifs = urllib.urlopen('http://www.cplusplus.com/' + name)
    print cplusplus2man(ifs.read()),
    #with open('test.txt') as ifs:
    #    print cplusplus2groff(ifs.read()),

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = TableParser
#-*- coding: utf-8 -*-
# 
# TableParser.py - format html from cplusplus.com to groff syntax
#
# Copyright (C) 2010 - 2014  Wei-Ning Huang (AZ) <aitjcize@gmail.com>
# All Rights reserved.
#
# This file is part of cppman.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import re
import sys
import StringIO

NODE = re.compile(r'<\s*([^/]\w*)\s?(.*?)>(.*?)<\s*/\1.*?>', re.S)
ATTR = re.compile(r'\s*(\w+?)\s*=\s*([\'"])((?:\\.|(?!\2).)*)\2')

class Node(object):
    def __init__(self, parent, name, attr_list, body):
        self.parent = parent
        self.name = name
        self.body = body
        self.attr = dict((x[0], x[2]) for x in ATTR.findall(attr_list))

        if self.name in ['th', 'td']:
            self.text = self.strip_tags(self.body)
            self.children = []
        else:
            self.text = ''
            self.children = [Node(self, *g) for g in NODE.findall(self.body)]

    def __repr__(self):
        return "<Node('%s')>" % self.name

    def strip_tags(self, html):
        if type(html) != str:
            html = html.group(3)
        return NODE.sub(self.strip_tags, html)

    def traverse(self, depth=0):
        print '%s%s: %s' % (' ' * depth, self.name, self.text)

        for c in self.children:
            c.traverse(depth + 2)

    def scan_format(self, index=0, total=0, rowspan={}):
        format_str = ''

        if self.name in ['th', 'td']:
            if self.attr.has_key('colspan'):
                total += int(self.attr['colspan']) - 1

            extend = ((total == 3 and index == 1) or
                      (total != 3 and total < 5 and index == total -1))

            if self.name == 'th':
                format_str += 'c%s ' % ('x' if extend else '')
            else:
                format_str += 'l%s ' % ('x' if extend else '')

            if self.attr.has_key('colspan'):
                for i in range(int(self.attr['colspan']) - 1):
                    format_str += 's '

            if self.attr.has_key('rowspan'):
                rowspan[index] = int(self.attr['rowspan']) - 1

        if self.name == 'tr' and len(rowspan) > 0:
            total = len(rowspan) + len(self.children)
            ci = 0
            for i in range(total):
                if rowspan.has_key(i):
                    format_str += '^ '
                    if rowspan[i] == 1:
                        del rowspan[i]
                    else:
                        rowspan[i] -= 1
                else:
                    format_str += self.children[ci].scan_format(i,
                            total, rowspan)
                    ci += 1
        else:
            for i, c in enumerate(self.children):
                format_str += c.scan_format(i, len(self.children), rowspan)

        if self.name == 'table':
            format_str += '.\n'
        elif self.name == 'tr':
            format_str += '\n'

        return format_str

    def gen(self, fd, index=0, last=False, rowspan={}):
        if self.name == 'table':
            fd.write('.TS\n')
            fd.write('allbox tab(|);\n')
            fd.write(self.scan_format())
        elif self.name in ['th', 'td']:
            fd.write('T{\n%s' % self.text)
            if self.attr.has_key('rowspan'):
                rowspan[index] = int(self.attr['rowspan']) - 1
        else:
            fd.write(self.text)

        if self.name == 'tr' and len(rowspan) > 0:
            total = len(rowspan) + len(self.children)
            ci = 0
            for i in range(total):
                if rowspan.has_key(i):
                    fd.write('\^%s' % ('|' if i < total - 1 else ''))
                    if rowspan[i] == 1:
                        del rowspan[i]
                    else:
                        rowspan[i] -= 1
                else:
                    self.children[ci].gen(fd, i, i == total - 1, rowspan)
                    ci += 1
        else:
            for i, c in enumerate(self.children):
                c.gen(fd, i, i == len(self.children) - 1, rowspan)

        if self.name == 'table':
            fd.write('.TE\n')
            fd.write('.sp\n.sp\n')
        elif self.name == 'tr':
            fd.write('\n')
        elif self.name in ['th', 'td']:
            fd.write('\nT}%s' % ('|' if not last else ''))


def parse_table(html):
    root = Node(None, 'root', '', html)
    fd = StringIO.StringIO()
    root.gen(fd)
    return fd.getvalue()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import sys
import os
import os.path
sys.path.insert(0, os.path.normpath(os.getcwd()))

from cppman import Formatter

Formatter.func_test()

########NEW FILE########
