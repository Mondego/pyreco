__FILENAME__ = base
import errno
import logging
import os
import sys
from collections import defaultdict, namedtuple

from bs4 import BeautifulSoup


log = logging.getLogger(__name__)


Entry = namedtuple('Entry', ['name', 'type', 'anchor'])


def coroutine(func):
    def start(*args, **kwargs):
        g = func(*args, **kwargs)
        if sys.version_info.major > 2:
            g.__next__()  # pragma: no cover
        else:
            g.next()  # pragma: no cover
        return g
    return start


class _BaseParser:

    """Abstract parser base class."""

    APPLE_REF = '//apple_ref/cpp/{}/{}'

    def __init__(self, docpath):
        self.docpath = docpath

    @classmethod
    def detect(cl, path):
        """Detect whether *path* is pydoctor documentation."""
        try:
            with open(os.path.join(path, cl.DETECT_FILE)) as f:
                return cl.DETECT_PATTERN in f.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
            else:
                raise

    @coroutine
    def add_toc(self):
        """Consume tuples as returned by parse(), then patch docs for TOCs."""
        files = defaultdict(list)
        try:
            while True:
                entry = (yield)
                try:
                    fname, anchor = entry[2].split('#')
                    files[fname].append(
                        Entry(entry[0], entry[1], anchor)
                    )
                except ValueError:
                    # pydoctor has no anchors for e.g. classes
                    pass
        except GeneratorExit:
            pass

        for fname, entries in files.items():
            full_path = os.path.join(self.docpath, fname)
            with open(full_path) as fp:
                soup = BeautifulSoup(fp, 'lxml')
                for entry in entries:
                    if not self.find_and_patch_entry(soup, entry):
                        log.debug("Can't find anchor {} in {}."
                                  .format(entry.anchor, fname))
            with open(full_path, 'w') as fp:
                fp.write(str(soup))

########NEW FILE########
__FILENAME__ = pydoctor
import logging
import os

from bs4 import BeautifulSoup

from . import types
from .base import _BaseParser


log = logging.getLogger(__name__)


class PyDoctorParser(_BaseParser):

    """Parser for pydoctor-based documentation: mainly Twisted."""

    name = 'pydoctor'

    DETECT_FILE = 'index.html'
    DETECT_PATTERN = '''\
      This documentation was automatically generated by
      <a href="http://codespeak.net/~mwh/pydoctor/">pydoctor</a>'''

    def parse(self):
        """Parse pydoctor docs at *docpath*.

        yield tuples of symbol name, type and path

        """
        soup = BeautifulSoup(
            open(os.path.join(self.docpath, 'nameIndex.html')),
            'lxml'
        )
        log.info('Creating database...')
        for tag in soup.body.find_all('a'):
            path = tag.get('href')
            if path and not path.startswith('#'):
                name = tag.string
                yield name, _guess_type(name, path), path

    def find_and_patch_entry(self, soup, entry):
        link = soup.find('a', attrs={'name': entry.anchor})
        if link:
            tag = soup.new_tag('a')
            tag['name'] = self.APPLE_REF.format(entry.type, entry.name)
            link.insert_before(tag)
            return True
        else:
            return False


def _guess_type(name, path):
    """Employ voodoo magic to guess the type of *name* in *path*."""
    if name.rsplit('.', 1)[-1][0].isupper() and '#' not in path:
        return types.CLASS
    elif name.islower() and '#' not in path:
        return types.PACKAGE
    else:
        return types.METHOD

########NEW FILE########
__FILENAME__ = sphinx
import errno
import logging
import os
import re

from bs4 import BeautifulSoup

from . import types
from .base import _BaseParser


log = logging.getLogger(__name__)


class SphinxParser(_BaseParser):

    """Parser for Sphinx-based documenation: Python, Django, Pyramid..."""

    name = 'sphinx'

    DETECT_FILE = '_static/searchtools.js'
    DETECT_PATTERN = '* Sphinx JavaScript util'

    def parse(self):
        """Parse sphinx docs at *path*.

        yield tuples of symbol name, type and path

        """
        for idx in POSSIBLE_INDEXES:
            try:
                soup = BeautifulSoup(open(os.path.join(self.docpath, idx)),
                                     'lxml')
                break
            except IOError:
                pass
        else:
            raise IOError(errno.ENOENT, 'Essential index file not found.')

        for t in _parse_soup(soup):
            yield t

    def find_and_patch_entry(self, soup, entry):
        """Modify soup so dash can generate TOCs on the fly."""
        link = soup.find('a', {'class': 'headerlink'}, href='#' + entry.anchor)
        tag = soup.new_tag('a')
        tag['name'] = self.APPLE_REF.format(entry.type, entry.name)
        if link:
            link.parent.insert(0, tag)
            return True
        elif entry.anchor.startswith('module-'):
            soup.h1.parent.insert(0, tag)
            return True
        else:
            return False


POSSIBLE_INDEXES = [
    'genindex-all.html',
    'genindex.html',
]


def _parse_soup(soup):
    log.info('Creating database...')
    for table in soup('table', {'class': 'genindextable'}):
        for td in table('td'):
            for dl in td('dl', recursive=False):
                for dt in dl('dt', recursive=False):
                    if not dt.a:
                        continue
                    type_, name = _get_type_and_name(dt.a.string)
                    if name:
                        href = dt.a['href']
                        tmp_name = _url_to_name(href, type_)
                        if not tmp_name.startswith('index-'):
                            yield tmp_name, type_, href
                    else:
                        name = _strip_annotation(dt.a.string)
                    dd = dt.next_sibling.next_sibling
                    if dd and dd.name == 'dd':
                        for y in _process_dd(name, dd):
                            yield y


RE_ANNO = re.compile(r'(.+) \(.*\)')


def _strip_annotation(text):
    """Transforms 'foo (class in bar)' to 'foo'."""
    m = RE_ANNO.match(text)
    if m:
        return m.group(1)
    else:
        return text.strip()


def _url_to_name(url, type_):
    """Certain types have prefixes in names we have to strip before adding."""
    if type_ == types.PACKAGE or type_ == types.CONSTANT and 'opcode-' in url:
        return url.split('#')[1][7:]
    else:
        return url.split('#')[1]


def _process_dd(name, dd):
    """Process a <dd> block as used by Sphinx on multiple symbols/name.

    All symbols inherit the *name* of the first.

    """
    for dt in dd('dt'):
        text = dt.text.strip()
        type_ = _get_type(text)
        if type_:
            if type_ == _IN_MODULE:
                type_ = _guess_type_by_name(name)
            full_name = _url_to_name(dt.a['href'], type_)
            if not full_name.startswith('index-'):
                yield full_name, type_, dt.a['href']


def _guess_type_by_name(name):
    """Module level functions and constants are not distinguishable."""
    if name.endswith('()'):
        return types.FUNCTION
    else:
        return types.CONSTANT


def _get_type(text):
    return _get_type_and_name(text)[0]


_IN_MODULE = '_in_module'
TYPE_MAPPING = [
    (re.compile(r'(.*)\(\S+ method\)$'), types.METHOD),
    (re.compile(r'(.*)\(.*function\)$'), types.FUNCTION),
    (re.compile(r'(.*)\(\S+ attribute\)$'), types.ATTRIBUTE),
    (re.compile(r'(.*)\(\S+ member\)$'), types.ATTRIBUTE),
    (re.compile(r'(.*)\(class in \S+\)$'), types.CLASS),
    (re.compile(r'(.*)\(built-in class\)$'), types.CLASS),
    (re.compile(r'(.*)\(built-in variable\)$'), types.CONSTANT),
    (re.compile(r'(.*)\(module\)$'), types.PACKAGE),
    (re.compile(r'(.*)\(opcode\)$'), types.CONSTANT),
    (re.compile(r'(.*)\(in module \S+\)$'), _IN_MODULE),
]


def _get_type_and_name(text):
    for mapping in TYPE_MAPPING:
        match = mapping[0].match(text)
        if match:
            name = match.group(1).strip()
            type_ = mapping[1]
            if type_ == _IN_MODULE and name:
                type_ = _guess_type_by_name(name)
            return type_, name
    else:
        return None, None

########NEW FILE########
__FILENAME__ = types
CLASS = 'cl'
PACKAGE = 'Module'
METHOD = 'clm'
FUNCTION = 'func'
ATTRIBUTE = 'Attribute'
CONSTANT = 'clconst'

########NEW FILE########
__FILENAME__ = __main__
from __future__ import absolute_import, division, print_function

import argparse
import errno
import logging
import os
import plistlib
import shutil
import sqlite3
import sys

from . import __version__, __doc__, parsers


log = logging.getLogger(__name__)

DEFAULT_DOCSET_PATH = os.path.expanduser(
    '~/Library/Application Support/doc2dash/DocSets'
)


def entry_point():
    """
    setuptools entry point that calls the real main with arguments.
    """
    main(sys.argv[1:])  # pragma: nocover


def main(argv):
    """
    Main cli entry point.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'source',
        help='Source directory containing API documentation in a supported'
             ' format.'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='force overwriting if destination already exists',
    )
    parser.add_argument(
        '--name', '-n',
        help='name docset explicitly',
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {}'.format(__version__),
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='limit output to errors and warnings'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='be verbose'
    )
    parser.add_argument(
        '--destination', '-d',
        help='destination directory for docset (default is current), '
             'ignored if -A is specified',
    )
    parser.add_argument(
        '--add-to-dash', '-a',
        action='store_true',
        help='automatically add resulting docset to dash',
    )
    parser.add_argument(
        '-A',
        action='store_true',
        help="create docset in doc2dash's default directory and add resulting "
             "docset to dash",
    )
    parser.add_argument(
        '--icon', '-i',
        help='add PNG icon to docset'
    )
    parser.add_argument(
        '--index-page', '-I',
        help='set index html file for docset'
    )
    args = parser.parse_args(args=argv)

    if args.icon and not args.icon.endswith('.png'):
        print('Please supply a PNG icon.')
        sys.exit(1)

    try:
        level = determine_log_level(args)
        logging.basicConfig(format='%(message)s', level=level)
    except ValueError as e:
        print(e.args[0], '\n')
        parser.print_help()
        sys.exit(1)

    source, dest = setup_paths(args)
    dt = parsers.get_doctype(source)
    if dt is None:
        log.error('"{}" does not contain a known documentation format.'
                  .format(source))
        sys.exit(errno.EINVAL)
    docs, db_conn = prepare_docset(args, dest)
    doc_parser = dt(docs)
    log.info('Converting {} docs from "{}" to "{}".'
             .format(dt.name, source, dest))

    with db_conn:
        log.info('Parsing HTML...')
        toc = doc_parser.add_toc()
        for entry in doc_parser.parse():
            db_conn.execute(
                'INSERT INTO searchIndex VALUES (NULL, ?, ?, ?)',
                entry
            )
            toc.send(entry)
        log.info('Added {0:,} index entries.'.format(
            db_conn.execute('SELECT COUNT(1) FROM searchIndex')
                   .fetchone()[0]))
        log.info('Adding table of contents meta data...')
        toc.close()

    if args.icon:
        add_icon(args.icon, dest)

    if args.add_to_dash:
        log.info('Adding to dash...')
        os.system('open -a dash "{}"'.format(dest))


def determine_log_level(args):
    """
    We use logging's levels as an easy-to-use verbosity controller.
    """
    if args.verbose and args.quiet:
        raise ValueError("Supplying both --quiet and --verbose doesn't make "
                         "sense.")
    elif args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    return level


def setup_paths(args):
    """
    Determine source and destination using the results of argparse.
    """
    source = args.source
    if not args.name:
        args.name = os.path.split(source)[-1]
    elif args.name.endswith('.docset'):
        args.name = args.name.replace('.docset', '')
    if args.A:
        args.destination = DEFAULT_DOCSET_PATH
        args.add_to_dash = True
    dest = os.path.join(args.destination or '', args.name + '.docset')
    if not os.path.exists(source):
        log.error('Source directory "{}" does not exist.'.format(source))
        sys.exit(errno.ENOENT)
    if not os.path.isdir(source):
        log.error('Source "{}" is not a directory.'.format(source))
        sys.exit(errno.ENOTDIR)
    dst_exists = os.path.lexists(dest)
    if dst_exists and args.force:
        shutil.rmtree(dest)
    elif dst_exists:
        log.error('Destination path "{}" already exists.'.format(dest))
        sys.exit(errno.EEXIST)
    return source, dest


def prepare_docset(args, dest):
    """
    Create boilerplate files & directories and copy vanilla docs inside.

    Return a tuple of path to resources and connection to sqlite db.
    """
    resources = os.path.join(dest, 'Contents/Resources/')
    docs = os.path.join(resources, 'Documents')
    os.makedirs(resources)

    db_conn = sqlite3.connect(os.path.join(resources, 'docSet.dsidx'))
    db_conn.row_factory = sqlite3.Row
    db_conn.execute(
        'CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, '
        'type TEXT, path TEXT)'
    )
    db_conn.commit()

    plist_cfg = {
        'CFBundleIdentifier': args.name,
        'CFBundleName': args.name,
        'DocSetPlatformFamily': args.name.lower(),
        'DashDocSetFamily': 'python',
        'isDashDocset': True,
    }
    if args.index_page is not None:
        plist_cfg['dashIndexFilePath'] = args.index_page

    plistlib.writePlist(
        plist_cfg,
        os.path.join(dest, 'Contents/Info.plist')
    )

    shutil.copytree(args.source, docs)
    return docs, db_conn


def add_icon(icon, dest):
    """
    Add icon to docset
    """
    shutil.copy2(icon, os.path.join(dest, 'icon.png'))


if __name__ == '__main__':
    main(sys.argv[1:])  # pragma: nocover

########NEW FILE########
__FILENAME__ = test_pydoctor
import os

from bs4 import BeautifulSoup
from mock import patch, mock_open

from doc2dash.parsers import types
from doc2dash.parsers.base import Entry
from doc2dash.parsers.pydoctor import PyDoctorParser, _guess_type


HERE = os.path.dirname(__file__)


def test_guess_type():
    ts = [
        ('startServer',
         'twisted.conch.test.test_cftp.CFTPClientTestBase.html#startServer',
         types.METHOD),
        ('A', 'twisted.test.myrebuilder1.A.html', types.CLASS),
        ('epollreactor', 'twisted.internet.epollreactor.html',
         types.PACKAGE)
    ]

    for t in ts:
        assert _guess_type(t[0], t[1]) == t[2]


EXAMPLE_PARSE_RESULT = [
    ('twisted.conch.insults.insults.ServerProtocol'
     '.ControlSequenceParser.A', types.METHOD,
     'twisted.conch.insults.insults.ServerProtocol'
     '.ControlSequenceParser.html#A'),
    ('twisted.test.myrebuilder1.A', types.CLASS,
     'twisted.test.myrebuilder1.A.html'),
    ('twisted.test.myrebuilder2.A', types.CLASS,
     'twisted.test.myrebuilder2.A.html'),
    ('twisted.test.test_jelly.A', types.CLASS,
     'twisted.test.test_jelly.A.html'),
    ('twisted.test.test_persisted.A', types.CLASS,
     'twisted.test.test_persisted.A.html'),
    ('twisted.test.myrebuilder1.A.a', types.METHOD,
     'twisted.test.myrebuilder1.A.html#a'),
    ('twisted.test.myrebuilder1.Inherit.a', types.METHOD,
     'twisted.test.myrebuilder1.Inherit.html#a'),
    ('twisted.test.myrebuilder2.A.a', types.METHOD,
     'twisted.test.myrebuilder2.A.html#a'),
    ('twisted.test.myrebuilder2.Inherit.a', types.METHOD,
     'twisted.test.myrebuilder2.Inherit.html#a'),
    ('twisted.web._newclient.HTTP11ClientProtocol.abort', types.METHOD,
     'twisted.web._newclient.HTTP11ClientProtocol.html#abort')
]


def test_parse():
    example = open(os.path.join(HERE, 'pydoctor_example.html')).read()
    with patch('doc2dash.parsers.pydoctor.open', mock_open(read_data=example),
               create=True):
        assert list(PyDoctorParser('foo').parse()) == EXAMPLE_PARSE_RESULT


def test_patcher():
    p = PyDoctorParser('foo')
    soup = BeautifulSoup(open(os.path.join(HERE, 'function_example.html')))
    assert p.find_and_patch_entry(
        soup,
        Entry('twisted.application.app.ApplicationRunner.startReactor',
              'clm', 'startReactor')
    )
    toc_link = soup(
        'a',
        attrs={'name': '//apple_ref/cpp/clm/twisted.application.app.'
                       'ApplicationRunner.startReactor'}
    )
    assert toc_link
    next_tag = toc_link[0].next_sibling
    assert next_tag.name == 'a'
    assert (next_tag['name'] == 'startReactor')
    assert not p.find_and_patch_entry(soup, Entry('invented', 'cl', 'nonex'))

########NEW FILE########
__FILENAME__ = test_sphinx
import errno
import os

from bs4 import BeautifulSoup
from mock import patch
from pytest import raises

from doc2dash.parsers import sphinx, types
from doc2dash.parsers.base import Entry


HERE = os.path.dirname(__file__)


def test_index_detection(tmpdir):
    """
    TODO: This is a terrible way to big test that need to get refactored.
    """
    parser = sphinx.SphinxParser(str(tmpdir))
    with raises(IOError) as e:
        list(parser.parse())
    assert e.value.errno == errno.ENOENT

    idx_all = tmpdir.join('genindex-all.html')
    idx = tmpdir.join('genindex.html')
    idx_all.write('all')
    idx.write('reg')

    with patch('doc2dash.parsers.sphinx._parse_soup') as mock:
        list(parser.parse())
        assert 'all' in str(mock.call_args[0][0])
        idx_all.remove()
        list(parser.parse())
        assert 'reg' in str(mock.call_args[0][0])


DD_EXAMPLE_PARSE_RESULT = [
    ('pyramid.interfaces.IRoutePregenerator.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IRoutePregenerator.__call__'),
    ('pyramid.interfaces.ISessionFactory.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.ISessionFactory.__call__'),
    ('pyramid.interfaces.IViewMapper.__call__', types.FUNCTION,
     'api/interfaces.html#pyramid.interfaces.IViewMapper.__call__'),
    ('pyramid.interfaces.IViewMapperFactory.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IViewMapperFactory.__call__'),
]


def test_process_dd():
    soup = BeautifulSoup(open(os.path.join(HERE, 'dd_example.html')))
    assert (list(sphinx._process_dd('__call__()', soup)) ==
            DD_EXAMPLE_PARSE_RESULT)
    assert list(sphinx._process_dd(
        'foo()',
        BeautifulSoup('<dd><dl><dt>doesntmatchanything</dt></dl><dd>'))) == []


def test_guess_type_by_name():
    assert sphinx._guess_type_by_name('foo()') == types.FUNCTION
    assert sphinx._guess_type_by_name('foo') == types.CONSTANT


EXAMPLE_PARSE_RESULT = [
    ('pyramid.interfaces.IResponse.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IResponse.__call__'),
    ('pyramid.interfaces.IRoutePregenerator.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IRoutePregenerator.__call__'),
    ('pyramid.interfaces.ISessionFactory.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.ISessionFactory.__call__'),
    ('pyramid.interfaces.IViewMapper.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IViewMapper.__call__'),
    ('pyramid.interfaces.IViewMapperFactory.__call__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IViewMapperFactory.__call__'),
    ('pyramid.interfaces.IDict.__contains__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IDict.__contains__'),
    ('pyramid.interfaces.IDict.__delitem__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IDict.__delitem__'),
    ('pyramid.interfaces.IDict.__getitem__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IDict.__getitem__'),
    ('pyramid.interfaces.IIntrospectable.__hash__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IIntrospectable.__hash__'),
    ('pyramid.interfaces.IDict.__iter__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IDict.__iter__'),
    ('pyramid.interfaces.IDict.__setitem__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IDict.__setitem__'),
    ('pyramid.interfaces.IActionInfo.__str__', types.METHOD,
     'api/interfaces.html#pyramid.interfaces.IActionInfo.__str__'),
    ('dict', types.CLASS, 'library/stdtypes.html#dict'),
    ('ftplib.FTP.abort', types.METHOD,
     'library/ftplib.html#ftplib.FTP.abort'),
    ('os.abort', types.FUNCTION, 'library/os.html#os.abort'),
    ('qux', types.CONSTANT, 'api/foo#qux'),
    ('abc', types.PACKAGE, 'library/abc.html#module-abc'),
    ('BINARY_AND', types.CONSTANT, 'library/dis.html#opcode-BINARY_AND'),
]


def test_parse_soup(monkeypatch):
    monkeypatch.setattr(sphinx, 'POSSIBLE_INDEXES', ['sphinx_example.html'])
    res = list(sphinx.SphinxParser(HERE).parse())
    soup = BeautifulSoup(open(os.path.join(HERE, 'sphinx_example.html')))
    assert res == list(sphinx._parse_soup(soup))
    assert res == EXAMPLE_PARSE_RESULT


def test_strip_annotation():
    assert sphinx._strip_annotation('Foo') == 'Foo'
    assert sphinx._strip_annotation('foo()') == 'foo()'
    assert sphinx._strip_annotation('Foo (bar)') == 'Foo'
    assert sphinx._strip_annotation('foo() (bar baz)') == 'foo()'
    assert sphinx._strip_annotation('foo() ()') == 'foo()'


def test_patcher():
    p = sphinx.SphinxParser('foo')
    soup = BeautifulSoup(open(os.path.join(HERE, 'function_example.html')))
    assert p.find_and_patch_entry(
        soup,
        Entry(
            'pyramid.config.Configurator.add_route',
            'clm',
            'pyramid.config.Configurator.add_route'
        )
    )
    toc_link = soup(
        'a',
        attrs={'name': '//apple_ref/cpp/clm/pyramid.config.Configurator.'
                       'add_route'}
    )
    assert toc_link
    assert not p.find_and_patch_entry(soup, Entry('invented', 'cl', 'nonex'))
    assert p.find_and_patch_entry(soup, Entry('somemodule', 'cl', 'module-sm'))

########NEW FILE########
__FILENAME__ = test_base
import os

from mock import patch

from doc2dash.parsers.base import _BaseParser


class TestParser(_BaseParser):
    pass


def test_toc_with_empty_db():
    p = TestParser('foo')
    toc = p.add_toc()
    toc.close()


def test_add_toc_single_entry(monkeypatch, tmpdir):
    entries = [
        ('foo', 'clm', 'bar.html#foo'),
        ('qux', 'cl', 'bar.html'),
    ]
    monkeypatch.chdir(tmpdir)
    p = TestParser('foo')
    os.mkdir('foo')
    with open('foo/bar.html', 'w') as fp:
        fp.write('docs!')
    p.find_and_patch_entry = lambda x, y: True
    toc = p.add_toc()
    for e in entries:
        toc.send(e)
    toc.close()

    p.find_and_patch_entry = lambda x, y: False
    toc = p.add_toc()
    for e in entries:
        toc.send(e)
    with patch('doc2dash.parsers.base.log.debug') as mock:
        toc.close()
        assert mock.call_count == 1

########NEW FILE########
__FILENAME__ = test_detectors
import os

import pytest
from mock import MagicMock

import doc2dash
from doc2dash.parsers import DOCTYPES


def test_get_doctype(monkeypatch):
    monkeypatch.setattr(doc2dash.parsers, 'DOCTYPES', [])
    assert doc2dash.parsers.get_doctype('foo') is None
    dt = MagicMock('testtype', detect=lambda _: True)
    monkeypatch.setattr(doc2dash.parsers, 'DOCTYPES', [dt])
    assert doc2dash.parsers.get_doctype('foo') is dt


if not os.path.exists('test_data'):
    print('Skipping detector tests since no test_data is present.')
else:
    def test_detectors_detect_no_false_positives():
        for dt in DOCTYPES:
            others = set(os.listdir('test_data')) - {dt.name}
            for t in others:
                type_path = os.path.join('test_data', t)
                for d in os.listdir(type_path):
                    assert not dt.detect(os.path.join(type_path, d))

    def test_detectors_detect():
        for dt in DOCTYPES:
            type_dir = os.path.join('test_data', dt.name)
            for d in os.listdir(type_dir):
                assert dt.detect(os.path.join(type_dir, d))


def test_detect_reraises_everything_except_enoent(monkeypatch):
    def raiser(exc):
        def _raiser(*args, **kwargs):
            raise exc()
        return _raiser

    for dt in DOCTYPES:
        for exc in IOError, ValueError:
            with pytest.raises(exc):
                monkeypatch.setattr(os.path, 'join', raiser(exc))
                dt.detect('foo')


def test_detect_handles_enoent_gracefully():
    for dt in DOCTYPES:
        assert not dt.detect('foo')

########NEW FILE########
__FILENAME__ = test_main
from __future__ import absolute_import, division, print_function

import errno
import logging
import os
import plistlib
import shutil
import sqlite3

import pytest

from mock import MagicMock, patch

import doc2dash

from doc2dash import __main__ as main


log = logging.getLogger(__name__)


@pytest.fixture
def args():
    """
    Return a mock of an argument object.
    """
    return MagicMock(name='args', A=False)


class TestArguments(object):
    def test_fails_without_source(self, capsys):
        """
        Fail If no source is passed.
        """
        with pytest.raises(SystemExit):
            main.main([])

        out, err = capsys.readouterr()
        assert out == ''
        assert (
            'error: too few arguments' in err
            or 'error: the following arguments are required: source' in err
        )

    def test_fails_with_unknown_icon(self, capsys):
        """
        Fail if icon is not PNG.
        """
        with pytest.raises(SystemExit):
            main.main(['foo', '-i', 'bar.bmp'])

        out, err = capsys.readouterr()
        assert err == ''
        assert 'Please supply a PNG icon.' in out

    def test_handles_unknown_doc_types(self, monkeypatch, tmpdir):
        """
        If docs are passed but are unknown, exit with EINVAL.
        """
        monkeypatch.chdir(tmpdir)
        os.mkdir('foo')
        with pytest.raises(SystemExit) as e:
            main.main(['foo'])
        assert e.value.code == errno.EINVAL


def test_normal_flow(monkeypatch, tmpdir):
    """
    Integration test with a mocked out parser.
    """
    def _fake_prepare(args, dest):
        db_conn = sqlite3.connect(':memory:')
        db_conn.row_factory = sqlite3.Row
        db_conn.execute(
            'CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, '
            'type TEXT, path TEXT)'
        )
        return 'data', db_conn

    def _yielder():
        yield 'testmethod', 'testpath', 'cm'

    monkeypatch.chdir(tmpdir)
    os.mkdir('foo')
    monkeypatch.setattr(main, 'prepare_docset', _fake_prepare)
    dt = MagicMock(detect=lambda _: True)
    dt.name = 'testtype'
    dt.return_value = MagicMock(parse=_yielder)
    monkeypatch.setattr(doc2dash.parsers, 'get_doctype', lambda _: dt)
    with patch('doc2dash.__main__.log.info') as info, \
            patch('os.system') as system, \
            patch('shutil.copy2') as cp:
        main.main(['foo', '-n', 'bar', '-a', '-i', 'qux.png'])
        # assert mock.call_args_list is None
        out = '\n'.join(call[0][0] for call in info.call_args_list) + '\n'
        assert system.call_args[0] == ('open -a dash "bar.docset"', )
        assert cp.call_args[0] == ('qux.png', 'bar.docset/icon.png')

    assert out == '''\
Converting testtype docs from "foo" to "bar.docset".
Parsing HTML...
Added 1 index entries.
Adding table of contents meta data...
Adding to dash...
'''


class TestSetupPaths(object):
    def test_works(self, args, monkeypatch, tmpdir):
        """
        Integration test with mocked-out parser.
        """
        foo_path = str(tmpdir.join('foo'))
        os.mkdir(foo_path)
        args.configure_mock(
            source=foo_path, name=None, destination=str(tmpdir)
        )
        assert (
            (foo_path, str(tmpdir.join('foo.docset')))
            == main.setup_paths(args)
        )
        abs_foo = os.path.abspath(foo_path)
        args.source = abs_foo
        assert ((abs_foo, str(tmpdir.join('foo.docset')) ==
                main.setup_paths(args)))
        assert args.name == 'foo'
        args.name = 'baz.docset'
        assert ((abs_foo, str(tmpdir.join('baz.docset')) ==
                main.setup_paths(args)))
        assert args.name == 'baz'

    def test_A_overrides_destination(self, args, monkeypatch):
        """
        Passing A computes the destination and overrides an argument.
        """
        assert '~' not in main.DEFAULT_DOCSET_PATH  # resolved?
        args.configure_mock(source='doc2dash', name=None, destination='foobar',
                            A=True)
        assert ('foo', os.path.join(main.DEFAULT_DOCSET_PATH, 'foo.docset') ==
                main.setup_paths(args))

    def test_detects_missing_source(self, args):
        """
        Exit wie ENOENT if source doesn't exist.
        """
        args.configure_mock(source='doesnotexist', name=None)
        with pytest.raises(SystemExit) as e:
            main.setup_paths(args)
        assert e.value.code == errno.ENOENT

    def test_detects_source_is_file(self, args):
        """
        Exit with ENOTDIR if a file is passed as source.
        """
        args.configure_mock(source='setup.py', name=None)
        with pytest.raises(SystemExit) as e:
            main.setup_paths(args)
        assert e.value.code == errno.ENOTDIR

    def test_detects_existing_dest(self, args, tmpdir, monkeypatch):
        """
        Exit with EEXIST if the selected destination already exists.
        """
        monkeypatch.chdir(tmpdir)
        os.mkdir('foo')
        os.mkdir('foo.docset')
        args.configure_mock(source='foo', force=False, name=None,
                            destination=None, A=False)
        with pytest.raises(SystemExit) as e:
            main.setup_paths(args)
        assert e.value.code == errno.EEXIST

        args.force = True
        main.setup_paths(args)
        assert not os.path.lexists('foo.docset')


class TestPrepareDocset(object):
    def test_plist_creation(self, args, monkeypatch, tmpdir):
        """
        All arguments should be reflected in the plist.
        """
        monkeypatch.chdir(tmpdir)
        m_ct = MagicMock()
        monkeypatch.setattr(shutil, 'copytree', m_ct)
        os.mkdir('bar')
        args.configure_mock(
            source='some/path/foo', name='foo', index_page=None)
        main.prepare_docset(args, 'bar')
        m_ct.assert_called_once_with(
            'some/path/foo',
            'bar/Contents/Resources/Documents',
        )
        assert os.path.isfile('bar/Contents/Resources/docSet.dsidx')
        p = plistlib.readPlist('bar/Contents/Info.plist')
        assert p == {
            'CFBundleIdentifier': 'foo',
            'CFBundleName': 'foo',
            'DocSetPlatformFamily': 'foo',
            'DashDocSetFamily': 'python',
            'isDashDocset': True,
        }
        with sqlite3.connect('bar/Contents/Resources/docSet.dsidx') as db_conn:
            cur = db_conn.cursor()
            # ensure table exists and is empty
            cur.execute('select count(1) from searchIndex')
            assert cur.fetchone()[0] == 0

    def test_with_index_page(self, args, monkeypatch, tmpdir):
        """
        If an index page is passed, it is added to the plist.
        """
        monkeypatch.chdir(tmpdir)
        m_ct = MagicMock()
        monkeypatch.setattr(shutil, 'copytree', m_ct)
        os.mkdir('bar')
        args.configure_mock(
            source='some/path/foo', name='foo', index_page='foo.html')
        main.prepare_docset(args, 'bar')
        p = plistlib.readPlist('bar/Contents/Info.plist')
        assert p == {
            'CFBundleIdentifier': 'foo',
            'CFBundleName': 'foo',
            'DocSetPlatformFamily': 'foo',
            'DashDocSetFamily': 'python',
            'isDashDocset': True,
            'dashIndexFilePath': 'foo.html',
        }


class TestSetupLogging(object):
    @pytest.mark.parametrize(
        "verbose, quiet, expected", [
            (False, False, logging.INFO),
            (True, False, logging.DEBUG),
            (False, True, logging.ERROR),
        ]
    )
    def test_logging(self, args, verbose, quiet, expected):
        """
        Ensure verbosity options cause the correct log level.
        """
        args.configure_mock(verbose=verbose, quiet=quiet)
        assert main.determine_log_level(args) is expected

    def test_quiet_and_verbose(self, args):
        """
        Fail if both -q and -v are passed.
        """
        args.configure_mock(verbose=True, quiet=True)
        with pytest.raises(ValueError):
            main.determine_log_level(args)

    def test_quiet_and_verbose_integration(self):
        """
        Ensure main() exists on -q + -v
        """
        with pytest.raises(SystemExit):
            main.main(['foo', '-q', '-v'])

########NEW FILE########