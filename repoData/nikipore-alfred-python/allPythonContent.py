__FILENAME__ = alfred
# -*- coding: utf-8 -*-
import itertools
import os
import plistlib
import unicodedata
import sys

from xml.etree.ElementTree import Element, SubElement, tostring

"""
You should run your script via /bin/bash with all escape options ticked.
The command line should be

python yourscript.py "{query}" arg2 arg3 ...
"""
UNESCAPE_CHARACTERS = u""" ;()"""

_MAX_RESULTS_DEFAULT = 9

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
            if len(value) == 2 and isinstance(value[1], dict):
                (value, attributes) = value
            else:
                attributes = {}
            SubElement(item, attribute, self.unicode(attributes)).text = unicode(value)
        return item

def args(characters=None):
    return tuple(unescape(decode(arg), characters) for arg in sys.argv[1:])

def config():
    return _create('config')

def decode(s):
    return unicodedata.normalize('NFD', s.decode('utf-8'))

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
__FILENAME__ = test
#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2013 deanishe@deanishe.net.
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2013-12-05
#

"""
"""

from __future__ import print_function

import sys
import os
import unittest
import unicodedata

import alfred

class AlfredTests(unittest.TestCase):

    _test_filename = 'üöäéøØÜÄÖÉàÀ.l11n'
    _unicode_test_filename = unicode(_test_filename, 'utf-8')

    def setUp(self):
        with open(self._test_filename, u'wb') as file:
            file.write(u'Testing!')

    def tearDown(self):
        if os.path.exists(self._test_filename):
            os.unlink(self._test_filename)

    def test_unicode_normalisation(self):
        """Ensure args are normalised in line with filesystem names"""
        self.assert_(os.path.exists(self._test_filename))
        filenames = [f for f in os.listdir(u'.') if f.endswith('.l11n')]
        self.assert_(len(filenames) == 1)
        print(u'{!r}'.format(filenames))
        fs_filename = filenames[0]
        self.assert_(fs_filename != self._test_filename)  # path has been NFD normalised by filesystem
        alfred_filename = alfred.decode(self._test_filename)
        self.assert_(alfred_filename == fs_filename)


if __name__ == u'__main__':
    unittest.main()

########NEW FILE########
