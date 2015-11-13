__FILENAME__ = xmlwitch_tests
from __future__ import with_statement

import sys
import os

ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..'
    )
)
sys.path.append(ROOT)

import unittest
import xmlwitch

class XMLWitchTestCase(unittest.TestCase):
    
    def expected_document(self, filename):
        expected = os.path.join(ROOT, 'tests',  'expected',  filename)
        with open(expected) as document:
            return document.read()
            
    def test_simple_document(self):
            xml = xmlwitch.Builder(version='1.0', encoding='utf-8')
            with xml.person:
                xml.name("Bob")
                xml.city("Qusqu")
            self.assertEquals(
                str(xml), 
                self.expected_document('simple_document.xml')
            )
    
    def test_utf8_document(self):
        string = u"""An animated fantasy film from 1978 based on the first """ \
                 u"""half of J.R.R Tolkien\u2019s Lord of the Rings novel. The """ \
                 u"""film was mainly filmed using rotoscoping, meaning it was """ \
                 u"""filmed in live action sequences with real actors and then """ \
                 u"""each frame was individually animated."""
        xml = xmlwitch.Builder(version='1.0', encoding='utf-8')
        with xml.test:
             xml.description(string)
        
        self.assertEquals(
            str(xml),
            self.expected_document('utf8_document.xml')
        )
    
    def test_nested_elements(self):
        xml = xmlwitch.Builder()
        with xml.feed(xmlns='http://www.w3.org/2005/Atom'):
            xml.title('Example Feed')
            xml.updated('2003-12-13T18:30:02Z')
            with xml.author:
                xml.name('John Doe')
            xml.id('urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6')
            with xml.entry:
                xml.title('Atom-Powered Robots Run Amok')
                xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
                xml.updated('2003-12-13T18:30:02Z')
                xml.summary('Some text.')
        self.assertEquals(
            str(xml), 
            self.expected_document('nested_elements.xml')
        )
    
    def test_rootless_fragment(self):
        xml = xmlwitch.Builder()
        xml.data(None, value='Just some data')
        self.assertEquals(
            str(xml), 
            self.expected_document('rootless_fragment.xml')
        )
    
    def test_content_escaping(self):
        xml = xmlwitch.Builder()
        with xml.doc:
            xml.item('Text&to<escape', some_attr='attribute&value>to<escape')
        self.assertEquals(
            str(xml), 
            self.expected_document('content_escaping.xml')
        )
    
    def test_namespaces(self):
        xml = xmlwitch.Builder()
        with xml.parent(**{'xmlns:my':'http://example.org/ns/'}):
            xml.my__child(None, my__attr='foo')
        self.assertEquals(
            str(xml), 
            self.expected_document('namespaces.xml')
        )        
    
    def test_atom_feed(self):
        xml = xmlwitch.Builder(version="1.0", encoding="utf-8")
        with xml.feed(xmlns='http://www.w3.org/2005/Atom'):
            xml.title('Example Feed')
            xml.link(None, href='http://example.org/')
            xml.updated('2003-12-13T18:30:02Z')
            with xml.author:
                xml.name('John Doe')
                xml.id('urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6')
                xml.title('Atom-Powered Robots Run Amok')
                xml.link(None, href='http://example.org/2003/12/13/atom03')
                xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
                xml.updated('2003-12-13T18:30:02Z')
                xml.summary('Some text.')
                with xml.content(type='xhtml'):
                    with xml.div(xmlns='http://www.w3.org/1999/xhtml'):
                        xml.label('Some label', for_='some_field')
                        xml.input(None, type='text', value='')
        self.assertEquals(
            str(xml), 
            self.expected_document('atom_feed.xml')
        )

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = xmlwitch
from __future__ import with_statement
from StringIO import StringIO
from xml.sax import saxutils
from keyword import kwlist as PYTHON_KWORD_LIST

__all__ = ['Builder', 'Element']
__license__ = 'BSD'
__version__ = '0.2.1'
__author__ = "Jonas Galvez <http://jonasgalvez.com.br/>"
__contributors__ = ["bbolli <http://github.com/bbolli/>",
                    "masklinn <http://github.com/masklinn/>"]

class Builder:
    
    def __init__(self, encoding='utf-8', indent=' '*2, version=None):
        self._document = StringIO()
        self._encoding = encoding
        self._indent = indent
        self._indentation = 0
        if version is not None:
            self.write('<?xml version="%s" encoding="%s"?>\n' % (
                version, encoding
            ))
    
    def __getattr__(self, name):
        return Element(name, self)
        
    def __getitem__(self, name):
        return Element(name, self)
    
    def __str__(self):
        return self._document.getvalue().encode(self._encoding).strip()
        
    def __unicode__(self):
        return self._document.getvalue().decode(self._encoding).strip()
        
    def write(self, content):
        """Write raw content to the document"""
        if type(content) is not unicode:
            content = content.decode(self._encoding)
        self._document.write('%s' % content)

    def write_escaped(self, content):
        """Write escaped content to the document"""
        self.write(saxutils.escape(content))
        
    def write_indented(self, content):
        """Write indented content to the document"""
        self.write('%s%s\n' % (self._indent * self._indentation, content))

builder = Builder # 0.1 backward compatibility

class Element:
    
    PYTHON_KWORD_MAP = dict([(k + '_', k) for k in PYTHON_KWORD_LIST])
    
    def __init__(self, name, builder):
        self.name = self._nameprep(name)
        self.builder = builder
        self.attributes = {}
        
    def __enter__(self):
        """Add a parent element to the document"""
        self.builder.write_indented('<%s%s>' % (
            self.name, self._serialized_attrs()
        ))
        self.builder._indentation += 1
        return self
        
    def __exit__(self, type, value, tb):
        """Add close tag to current parent element"""
        self.builder._indentation -= 1
        self.builder.write_indented('</%s>' % self.name)
        
    def __call__(*args, **kargs):
        """Add a child element to the document"""
        self = args[0]
        self.attributes.update(kargs)
        if len(args) > 1:
            value = args[1]
            if value is None:
                self.builder.write_indented('<%s%s />' % (
                    self.name, self._serialized_attrs()
                ))
            else:
                value = saxutils.escape(value)
                self.builder.write_indented('<%s%s>%s</%s>' % (
                    self.name, self._serialized_attrs(), value, self.name
                ))
        return self

    def _serialized_attrs(self):
        """Serialize attributes for element insertion"""
        serialized = []
        for attr, value in self.attributes.items():
            serialized.append(' %s=%s' % (
                self._nameprep(attr), saxutils.quoteattr(value)
            ))
        return ''.join(serialized)

    def _nameprep(self, name):
        """Undo keyword and colon mangling"""
        name = Element.PYTHON_KWORD_MAP.get(name, name)
        return name.replace('__', ':')

########NEW FILE########
