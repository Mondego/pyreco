__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

_MAX_RESULTS_DEFAULT = 9
UNESCAPE_CHARACTERS = u"""\\ ()[]{};`'"$"""

preferences = plistlib.readPlist('info.plist')
bundleid = preferences['bundleid']

class Item(object):
    @classmethod
    def unicode(cls, value):
        try:
            items = value.iteritems()
        except AttributeError:
            return unicode(value)
        else:
            return dict(map(unicode, item) for item in items)

    def __init__(self, attributes, title, subtitle, icon=None):
        self.attributes = attributes
        self.title = title
        self.subtitle = subtitle
        self.icon = icon

    def __str__(self):
        return tostring(self.xml(), encoding='utf-8')

    def xml(self):
        item = Element(u'item', self.unicode(self.attributes))
        for attribute in (u'title', u'subtitle', u'icon'):
            value = getattr(self, attribute)
            if value is None:
                continue
            try:
                (value, attributes) = value
            except:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFC', s.decode('utf-8'))

def uid(uid):
    return u'-'.join(map(unicode, (bundleid, uid)))

def unescape(query, characters=None):
    for character in (UNESCAPE_CHARACTERS if (characters is None) else characters):
        query = query.replace('\\%s' % character, character)
    return query

def work(volatile):
    path = {
        True: '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data',
        False: '~/Library/Application Support/Alfred 2/Workflow Data'
    }[bool(volatile)]
    return _create(os.path.join(os.path.expanduser(path), bundleid))

def write(text):
    sys.stdout.write(text)

def xml(items, maxresults=_MAX_RESULTS_DEFAULT):
    root = Element('items')
    for item in itertools.islice(items, maxresults):
        root.append(item.xml())
    return tostring(root, encoding='utf-8')

def _create(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.access(path, os.W_OK):
        raise IOError('No write access: %s' % path)
    return path

########NEW FILE########
__FILENAME__ = alfredman
# -*- coding: utf-8 -*-
# man.alfredworkflow, v1.1
# Robin Breathe, 2013

import alfred
import json
import re
import subprocess

from fnmatch import fnmatch
from os import path
from time import time

_MAX_RESULTS=36

def clean_ascii(string):
    return ''.join(i for i in string if ord(i)<128)

def fetch_whatis(max_age=604800):
    cache = path.join(alfred.work(volatile=True), u'whatis.1.json')
    if path.isfile(cache) and (time() - path.getmtime(cache) < max_age):
        return json.load(open(cache, 'r'))
    raw_pages = subprocess.check_output(['/usr/bin/man', '-k', '-Pcat', '.'])
    pagelist  = map(
        lambda x: map(lambda y: y.strip(), x.split(' - ', 1)),
        clean_ascii(raw_pages).splitlines()
    )
    whatis = {}
    for (pages, description) in pagelist:
        for page in pages.split(', '):
            whatis[page] = description
    json.dump(whatis, open(cache, 'w'))
    return whatis

def fetch_sections(whatis, max_age=604800):
    cache = path.join(alfred.work(volatile=True), u'sections.1.json')
    if path.isfile(cache) and (time() - path.getmtime(cache) < max_age):
        return set(json.load(open(cache, 'r')))
    sections = set([])
    pattern = re.compile(r'\(([^()]+)\)$')
    for page in whatis.iterkeys():
        sre = pattern.search(page)
        if sre:
            sections.add(sre.group(1))
    json.dump(list(sections), open(cache, 'w'))
    return sections

def man_arg(manpage):
    pattern = re.compile(r'(.*)\((.+)\)')
    sre = pattern.match(manpage)
    (title, section) = (sre.group(1), sre.group(2))
    return u'%s/%s' % (section, title)
    
def man_uri(manpage, protocol='x-man-page'):
    return u'%s://%s' % (protocol, man_arg(manpage))

def filter_whatis_name(_filter, whatis):
    return {k: v for (k, v) in whatis.iteritems() if _filter(k)}

def filter_whatis_description(_filter, whatis):
    return {k: v for (k, v) in whatis.iteritems() if _filter(v)}

def result_list(query, whatis=None):
    results = []
    if whatis is None:
        return results
    for (page, description) in whatis.iteritems():
        if fnmatch(page, '%s*' % query):
            _arg = man_arg(page)
            _uri = man_uri(page)
            results.append(alfred.Item(
                attributes = {'uid': _uri, 'arg': _arg},
                title = page,
                subtitle = description,
                icon = 'icon.png'
            ))
    return results

def complete(query, maxresults=_MAX_RESULTS):
    whatis = fetch_whatis()
    sections = fetch_sections(whatis)
        
    results = []
    
    # direct hit
    if query in whatis:
        _arg = man_arg(query)
        _uri = man_uri(query)
        results.append(alfred.Item(
            attributes = {'uid': _uri, 'arg': _arg},
            title = query,
            subtitle = whatis[query],
            icon = 'icon.png'
        ))
    
    # section filtering
    elif query in sections:
        _uri = man_uri('(%s)' % query)
        results.append(alfred.Item(
            attributes = {'uid': _uri, 'arg': _uri, 'valid': 'no'},
            title = 'Open man page',
            subtitle = 'Scope restricted to section %s' % query,
            icon = 'icon.png'
        ))
    elif ' ' in query:
        (_section, _title) = query.split()
        pattern = re.compile(r'^.+\(%s\)$' % _section)
        _whatis = filter_whatis_name(pattern.match, whatis)
        results.extend(result_list(_title, _whatis))
    
    # substring matching
    elif query.startswith('~'):
        results.extend(result_list('*%s*' % query, whatis))
    # standard filtering
    else:
        results.extend(result_list(query, whatis))
    
    # no matches
    if results == []:
        results.append(alfred.Item(
            attributes = {'uid': 'x-man-page://404', 'valid': 'no'},
            title = '404 Page Not Found',
            subtitle = 'No man page was found for %s' % query,
            icon = 'icon.png'
        ))

    return alfred.xml(results, maxresults=maxresults)

########NEW FILE########
__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

_MAX_RESULTS_DEFAULT = 9
UNESCAPE_CHARACTERS = u"""\\ ()[]{};`'"$"""

preferences = plistlib.readPlist('info.plist')
bundleid = preferences['bundleid']

class Item(object):
    @classmethod
    def unicode(cls, value):
        try:
            items = value.iteritems()
        except AttributeError:
            return unicode(value)
        else:
            return dict(map(unicode, item) for item in items)

    def __init__(self, attributes, title, subtitle, icon=None):
        self.attributes = attributes
        self.title = title
        self.subtitle = subtitle
        self.icon = icon

    def __str__(self):
        return tostring(self.xml(), encoding='utf-8')

    def xml(self):
        item = Element(u'item', self.unicode(self.attributes))
        for attribute in (u'title', u'subtitle', u'icon'):
            value = getattr(self, attribute)
            if value is None:
                continue
            try:
                (value, attributes) = value
            except:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFC', s.decode('utf-8'))

def uid(uid):
    return u'-'.join(map(unicode, (bundleid, uid)))

def unescape(query, characters=None):
    for character in (UNESCAPE_CHARACTERS if (characters is None) else characters):
        query = query.replace('\\%s' % character, character)
    return query

def work(volatile):
    path = {
        True: '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data',
        False: '~/Library/Application Support/Alfred 2/Workflow Data'
    }[bool(volatile)]
    return _create(os.path.join(os.path.expanduser(path), bundleid))

def write(text):
    sys.stdout.write(text)

def xml(items, maxresults=_MAX_RESULTS_DEFAULT):
    root = Element('items')
    for item in itertools.islice(items, maxresults):
        root.append(item.xml())
    return tostring(root, encoding='utf-8')

def _create(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.access(path, os.W_OK):
        raise IOError('No write access: %s' % path)
    return path

########NEW FILE########
__FILENAME__ = pipe
#-*- coding: utf-8 -*-
# pipe.alfredworkflow, v1.0
# Robin Breathe, 2013

import alfred
import json

from fnmatch import fnmatch
from os import path
from time import strftime

_MAX_RESULTS=9
_ALIASES_FILE=u'aliases.json'
_BUILTINS_FILE=u'builtins.json'
_TIMESTAMP=u'%Y-%m-%d @ %H:%M'

def fetch_aliases(_path=_ALIASES_FILE):
    file = path.join(alfred.work(volatile=False), _path)
    if not path.isfile(file):
        return {}
    return json.load(open(file, 'r'))

def write_aliases(_dict, _path=_ALIASES_FILE):
    file = path.join(alfred.work(volatile=False), _path)
    json.dump(_dict, open(file, 'w'), indent=4, separators=(',', ': '))

def define_alias(_dict, definition):
    if u'=' in definition:
        (alias, pipe) = definition.split(u'=', 1)
    else:
        (alias, pipe) = (definition, u'')

    if not alias:
        return alfred.xml([alfred.Item(
            attributes = {'uid': u'pipe:help', 'valid': u'no'},
            title = u"alias NAME=VALUE",
            subtitle = u'Terminate VALUE with @@ to save',
            icon = u'icon.png'
        )])

    if pipe and pipe.endswith('@@'):
        pipe = pipe[:-2]
        _dict[alias] = pipe
        write_aliases(_dict)
        return alfred.xml([alfred.Item(
            attributes = {'uid': u'pipe:{}'.format(pipe) , 'valid': u'no', 'autocomplete': alias},
            title = u"alias {}={}".format(alias, pipe),
            subtitle = u'Alias saved! TAB to continue',
            icon = u'icon.png'
        )])
    
    return alfred.xml([alfred.Item(
        attributes = {'uid': u'pipe:{}'.format(pipe) , 'valid': u'no'},
        title = u"alias {}={}".format(alias, pipe or 'VALUE'),
        subtitle = u'Terminate with @@ to save',
        icon = u'icon.png'
    )])

def exact_alias(_dict, query):
    pipe = _dict[query]
    return alfred.xml([alfred.Item(
        attributes = {'uid': u'pipe:{}'.format(pipe), 'arg': pipe},
        title = pipe,
        subtitle = u'(expanded alias)',
        icon = u'icon.png'
    )])

def match_aliases(_dict, query):
    results = []
    for (alias, pipe) in _dict.iteritems():
        if (pipe != query) and fnmatch(alias, u'{}*'.format(query)):
            results.append(alfred.Item(
                attributes = {'uid': u'pipe:{}'.format(pipe) , 'arg': pipe, 'autocomplete': pipe},
                title = pipe,
                subtitle = u'(alias: {})'.format(alias),
                icon = u'icon.png'
            ))
    return results

def fetch_builtins(_path=_BUILTINS_FILE):
    return json.load(open(_path, 'r'))

def match_builtins(_dict, query):
    results = []
    for (pipe, desc) in _dict.iteritems():
        if fnmatch(pipe, u'*{}*'.format(query)) or fnmatch(desc, u'*{}*'.format(query)):
            results.append(alfred.Item(
                attributes = {'uid': u'pipe:{}'.format(pipe) , 'arg': pipe, 'autocomplete': pipe},
                title = pipe,
                subtitle = u'(builtin: {})'.format(desc),
                icon = u'icon.png'
            ))
    return results

def verbatim(query):
    return alfred.Item(
        attributes = {'uid': u'pipe:{}'.format(query), 'arg': query},
        title = query,
        subtitle = None,
        icon = u'icon.png'
    )

def complete(query, maxresults=_MAX_RESULTS):
    aliases = fetch_aliases()
    builtins = fetch_builtins()

    if query.startswith('alias '):
        return define_alias(aliases, query[6:])

    results = []

    if query not in builtins:
        results.append(verbatim(query))

    for matches in (
        match_aliases(aliases, query),
        match_builtins(builtins, query)
    ):
        results.extend(matches)

    return alfred.xml(results, maxresults=maxresults)

########NEW FILE########
__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

_MAX_RESULTS_DEFAULT = 9
UNESCAPE_CHARACTERS = u"""\\ ()[]{};`'"$"""

preferences = plistlib.readPlist('info.plist')
bundleid = preferences['bundleid']

class Item(object):
    @classmethod
    def unicode(cls, value):
        try:
            items = value.iteritems()
        except AttributeError:
            return unicode(value)
        else:
            return dict(map(unicode, item) for item in items)

    def __init__(self, attributes, title, subtitle, icon=None):
        self.attributes = attributes
        self.title = title
        self.subtitle = subtitle
        self.icon = icon

    def __str__(self):
        return tostring(self.xml(), encoding='utf-8')

    def xml(self):
        item = Element(u'item', self.unicode(self.attributes))
        for attribute in (u'title', u'subtitle', u'icon'):
            value = getattr(self, attribute)
            if value is None:
                continue
            try:
                (value, attributes) = value
            except:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFC', s.decode('utf-8'))

def uid(uid):
    return u'-'.join(map(unicode, (bundleid, uid)))

def unescape(query, characters=None):
    for character in (UNESCAPE_CHARACTERS if (characters is None) else characters):
        query = query.replace('\\%s' % character, character)
    return query

def work(volatile):
    path = {
        True: '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data',
        False: '~/Library/Application Support/Alfred 2/Workflow Data'
    }[bool(volatile)]
    return _create(os.path.join(os.path.expanduser(path), bundleid))

def write(text):
    sys.stdout.write(text)

def xml(items, maxresults=_MAX_RESULTS_DEFAULT):
    root = Element('items')
    for item in itertools.islice(items, maxresults):
        root.append(item.xml())
    return tostring(root, encoding='utf-8')

def _create(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.access(path, os.W_OK):
        raise IOError('No write access: %s' % path)
    return path

########NEW FILE########
__FILENAME__ = alfredssh
#-*- coding: utf-8 -*-
# ssh.alfredworkflow, v1.2
# Robin Breathe, 2013

import alfred
import json
import re

from os import path
from time import time

_MAX_RESULTS=36

class Hosts(object):
    def __init__(self, original, user=None):
        self.original = original
        self.hosts = {original: ['input']}
        self.user = user

    def add(self, host, source):
        if host in self.hosts:
            self.hosts[host].append(source)
        else:
            self.hosts[host] = [source]

    def update(self, _list):
        if not _list:
            return
        (hosts, source) = _list
        for host in hosts:
            self.add(host, source)

    def item(self, host, source):
        _arg = self.user and '@'.join([self.user, host]) or host
        _uri = 'ssh://%s' % _arg
        _sub = 'Connect to %s (source: %s)' % (_uri, ', '.join(source))
        return alfred.Item(
            attributes={'uid': _uri, 'arg': _arg, 'autocomplete': _arg},
            title=_uri, subtitle=_sub, icon='icon.png'
        )

    def xml(self, _filter=(lambda x: True), maxresults=_MAX_RESULTS):
        items = [self.item(host=self.original, source=self.hosts[self.original])]
        for (host, source) in (
            (x, y) for (x, y) in self.hosts.iteritems()
            if ((x != self.original) and _filter(x))
        ):
            items.append(self.item(host, source))
        return alfred.xml(items, maxresults=maxresults)

def fetch_ssh_config(_path, alias='~/.ssh/ssh_config'):
    master = path.expanduser(_path)
    if not path.isfile(master):
        return
    cache = path.join(alfred.work(volatile=True), 'ssh_config.1.json')
    if path.isfile(cache) and path.getmtime(cache) > path.getmtime(master):
        return (json.load(open(cache, 'r')), alias)
    results = set()
    try:
        with open(path.expanduser(_path), 'r') as ssh_config:
            results.update(
                x for line in ssh_config
                if line[:5].lower() == 'host '
                for x in line.split()[1:]
                if not ('*' in x or '?' in x or '!' in x)
            )
    except IOError:
        pass
    json.dump(list(results), open(cache, 'w'))
    return (results, alias)

def fetch_known_hosts(_path, alias='~/.ssh/known_hosts'):
    master = path.expanduser(_path)
    if not path.isfile(master):
        return
    cache = path.join(alfred.work(volatile=True), 'known_hosts.1.json')
    if path.isfile(cache) and path.getmtime(cache) > path.getmtime(master):
        return (json.load(open(cache, 'r')), alias)
    results = set()
    try:
        with open(path.expanduser(_path), 'r') as known_hosts:
            for line in known_hosts:
                results.update(line.split()[0].split(','))
    except IOError:
        pass
    json.dump(list(results), open(cache, 'w'))
    return (results, alias)

def fetch_hosts(_path, alias='/etc/hosts'):
    master = path.expanduser(_path)
    if not path.isfile(master):
        return
    cache = path.join(alfred.work(volatile=True), 'hosts.1.json')
    if path.isfile(cache) and path.getmtime(cache) > path.getmtime(master):
        return (json.load(open(cache, 'r')), alias)
    results = set()
    try:
        with open(_path, 'r') as etc_hosts:
            for line in (x for x in etc_hosts if not x.startswith('#')):
                results.update(line.split()[1:])
        results.discard('broadcasthost')
    except IOError:
        pass
    json.dump(list(results), open(cache, 'w'))
    return (results, alias)

def fetch_bonjour(_service, alias='Bonjour', timeout=0.1):
    cache = path.join(alfred.work(volatile=True), 'bonjour.1.json')
    if path.isfile(cache) and (time() - path.getmtime(cache) < 60):
        return (json.load(open(cache, 'r')), alias)
    results = set()
    try:
        from pybonjour import DNSServiceBrowse, DNSServiceProcessResult
        from select import select
        bj_callback = lambda s, f, i, e, n, t, d: results.add('%s.%s' % (n.lower(), d[:-1]))
        bj_browser = DNSServiceBrowse(regtype=_service, callBack=bj_callback)
        select([bj_browser], [], [], timeout)
        DNSServiceProcessResult(bj_browser)
        bj_browser.close()
    except ImportError:
        pass
    json.dump(list(results), open(cache, 'w'))
    return (results, alias)

def complete(query, maxresults=_MAX_RESULTS):
    if '@' in query:
        (user, host) = query.split('@', 1)
    else:
        (user, host) = (None, query)

    host_chars = (('\\.' if x is '.' else x) for x in list(host))
    pattern = re.compile('.*?\b?'.join(host_chars), flags=re.IGNORECASE)

    hosts = Hosts(original=host, user=user)
    for results in (
        fetch_ssh_config('~/.ssh/config'),
        fetch_known_hosts('~/.ssh/known_hosts'),
        fetch_hosts('/etc/hosts'),
        fetch_bonjour('_ssh._tcp')
    ):
        hosts.update(results)

    return hosts.xml(pattern.search, maxresults=maxresults)

########NEW FILE########
__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

_MAX_RESULTS_DEFAULT = 9
UNESCAPE_CHARACTERS = u"""\\ ()[]{};`'"$"""

preferences = plistlib.readPlist('info.plist')
bundleid = preferences['bundleid']

class Item(object):
    @classmethod
    def unicode(cls, value):
        try:
            items = value.iteritems()
        except AttributeError:
            return unicode(value)
        else:
            return dict(map(unicode, item) for item in items)

    def __init__(self, attributes, title, subtitle, icon=None):
        self.attributes = attributes
        self.title = title
        self.subtitle = subtitle
        self.icon = icon

    def __str__(self):
        return tostring(self.xml(), encoding='utf-8')

    def xml(self):
        item = Element(u'item', self.unicode(self.attributes))
        for attribute in (u'title', u'subtitle', u'icon'):
            value = getattr(self, attribute)
            if value is None:
                continue
            try:
                (value, attributes) = value
            except:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFC', s.decode('utf-8'))

def uid(uid):
    return u'-'.join(map(unicode, (bundleid, uid)))

def unescape(query, characters=None):
    for character in (UNESCAPE_CHARACTERS if (characters is None) else characters):
        query = query.replace('\\%s' % character, character)
    return query

def work(volatile):
    path = {
        True: '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data',
        False: '~/Library/Application Support/Alfred 2/Workflow Data'
    }[bool(volatile)]
    return _create(os.path.join(os.path.expanduser(path), bundleid))

def write(text):
    sys.stdout.write(text)

def xml(items, maxresults=_MAX_RESULTS_DEFAULT):
    root = Element('items')
    for item in itertools.islice(items, maxresults):
        root.append(item.xml())
    return tostring(root, encoding='utf-8')

def _create(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.access(path, os.W_OK):
        raise IOError('No write access: %s' % path)
    return path

########NEW FILE########
__FILENAME__ = terminology
#-*- coding: utf-8 -*-
# terminology.alfredworkflow, v0.1
# Robin Breathe, 2013

import alfred
import json
import urllib2

from urllib import quote, urlencode
from os import path
from time import time

_MAX_RESULTS = 9
_TIMEOUT = 1.0
_BASE_URL = u'http://term.ly'
_MATCH_API = u'/api/matches.json'

def fetch_terms(query):
    req = urllib2.Request(u'%s?%s' % (u''.join((_BASE_URL, _MATCH_API)), urlencode({'q': query})))
    try:
        f = urllib2.urlopen(req, None, _TIMEOUT)
    except URLError:
        return []
    if f.getcode() != 200:
        return []
    return json.load(f)

def search_results(query, maxresults=_MAX_RESULTS):
    response = fetch_terms(query)

    results = []
    for r in response[:maxresults]:
        address = u'/'.join((_BASE_URL, quote(r)))
        results.append(alfred.Item(
            attributes = {'uid': address, 'arg': address, 'autocomplete': r},
            title = r,
            subtitle = u"Open %s on term.ly" % r,
            icon = u'icon.png'
        ))

    # no matches
    if results == []:
        results.append(alfred.Item(
            attributes = {'valid': u'no'},
            title = u'404 Term Not Found: %s' % query,
            subtitle = u"Sorry, term '%s' was not found on term.ly" % r,
            icon = u'icon.png'
        ))

    return results

def complete(query, maxresults=_MAX_RESULTS):
    results = search_results(query)

    return alfred.xml(results, maxresults=_MAX_RESULTS)


########NEW FILE########
__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

_MAX_RESULTS_DEFAULT = 9
UNESCAPE_CHARACTERS = u"""\\ ()[]{};`'"$"""

preferences = plistlib.readPlist('info.plist')
bundleid = preferences['bundleid']

class Item(object):
    @classmethod
    def unicode(cls, value):
        try:
            items = value.iteritems()
        except AttributeError:
            return unicode(value)
        else:
            return dict(map(unicode, item) for item in items)

    def __init__(self, attributes, title, subtitle, icon=None):
        self.attributes = attributes
        self.title = title
        self.subtitle = subtitle
        self.icon = icon

    def __str__(self):
        return tostring(self.xml(), encoding='utf-8')

    def xml(self):
        item = Element(u'item', self.unicode(self.attributes))
        for attribute in (u'title', u'subtitle', u'icon'):
            value = getattr(self, attribute)
            if value is None:
                continue
            try:
                (value, attributes) = value
            except:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFC', s.decode('utf-8'))

def uid(uid):
    return u'-'.join(map(unicode, (bundleid, uid)))

def unescape(query, characters=None):
    for character in (UNESCAPE_CHARACTERS if (characters is None) else characters):
        query = query.replace('\\%s' % character, character)
    return query

def work(volatile):
    path = {
        True: '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data',
        False: '~/Library/Application Support/Alfred 2/Workflow Data'
    }[bool(volatile)]
    return _create(os.path.join(os.path.expanduser(path), bundleid))

def write(text):
    sys.stdout.write(text)

def xml(items, maxresults=_MAX_RESULTS_DEFAULT):
    root = Element('items')
    for item in itertools.islice(items, maxresults):
        root.append(item.xml())
    return tostring(root, encoding='utf-8')

def _create(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    if not os.access(path, os.W_OK):
        raise IOError('No write access: %s' % path)
    return path

########NEW FILE########
__FILENAME__ = trailer
#-*- coding: utf-8 -*-
# trailer.alfredworkflow, v0.1
# Robin Breathe, 2013

import alfred
try:
    import requests
except ImportError:
    import sys
    sys.path.append('./requests-1.1.0-py2.7.egg')
    import requests

from os import path
from time import time

_MAX_RESULTS = 9
SEARCH_TIMEOUT = 1.0
POSTER_TIMEOUT = 0.2
_BASE_URL = u'http://trailers.apple.com'
_QUICKFIND = u'/trailers/home/scripts/quickfind.php'
_JUSTADDED = u'/trailers/home/feeds/just_added.json'

def fetch_quickfind(query):
    r = requests.get(u''.join((_BASE_URL, _QUICKFIND)), params={'q': query}, timeout=SEARCH_TIMEOUT)
    if r.status_code != 200:
        return
    return r.json()

def fetch_justadded():
    r = requests.get(u''.join((_BASE_URL, _JUSTADDED)), timeout=SEARCH_TIMEOUT)
    if r.status_code != 200:
        return
    return r.json()

def fetch_poster(poster_uri):
    poster_name = u'_%s.%s' % (
        u'_'.join(poster_uri.split('/')[4:6]),
        poster_uri.split('.')[-1]
    )
    cache = path.join(alfred.work(volatile=True), poster_name)
    if path.isfile(cache):
        return cache
    try:
        r = requests.get(poster_uri, timeout=POSTER_TIMEOUT)
    except requests.exceptions.Timeout:
        return 'icon.png'
    if r.status_code != 200 or not r.headers['Content-Type'].startswith('image/'):
        return 'icon.png'
    with open(cache, 'wb') as cache_file:
        cache_file.write(r.content)
    return cache

def search_results(query, maxresults=_MAX_RESULTS):
    response = fetch_quickfind(query)

    if not response or response['error']:
        return alfred.xml([alfred.Item(
            attributes = {'uid': u'trailer://404', 'valid': u'no'},
            title = u'404 Trailer Not Found',
            subtitle = u'Sorry, the iTunes Movie Trailers server returned an error',
            icon = u'icon.png'
        )])

    results = []
    for r in response['results'][:maxresults]:
        address = u''.join((_BASE_URL, r['location']))
        results.append(alfred.Item(
            attributes = {'uid': u'trailer://%s' % r['location'], 'arg': address, 'autocomplete': r['title']},
            title = r['title'],
            subtitle = u'Rating: %(rating)s; Studio: %(studio)s' % r,
            icon = fetch_poster(u''.join((_BASE_URL, r['poster'])))
        ))

    # no matches
    if results == []:
        results.append(alfred.Item(
            attributes = {'uid': u'trailer://404', 'valid': u'no'},
            title = u'404 Trailer Not Found',
            subtitle = u'No trailers matching the query were found',
            icon = u'icon.png'
        ))

    return results

def latest_results(maxresults=_MAX_RESULTS):
    response = fetch_justadded()
    
    if not response:
        return alfred.xml([alfred.Item(
            attributes = {'uid': u'trailer://404', 'valid': u'no'},
            title = u'404 Latest Movies Not Found',
            subtitle = u'Sorry, the iTunes Movie Trailers server isn\'t responding',
            icon = u'icon.png'
        )])
    
    results = []
    for r in response[:maxresults]:
        address = u''.join((_BASE_URL, r['location']))
        results.append(alfred.Item(
            attributes = {'uid': u'trailer://%s' % r['location'], 'arg': address, 'autocomplete': r['title']},
            title = r['title'],
            subtitle = u'Studio: %(studio)s' % r,
            icon = fetch_poster(r['poster'])
        ))

    return results

def complete(query, maxresults=_MAX_RESULTS):
    if query == 'latest':
        results = latest_results()
    else:
        results = search_results(query)

    return alfred.xml(results, maxresults=_MAX_RESULTS)
########NEW FILE########
