__FILENAME__ = banz_scraper
# -*- encoding: utf-8 -*-
"""BAnz-Scraper.

Usage:
  banz_scaper.py <outputfile> [<minyear> [<maxyear>]]
  banz_scaper.py -h | --help
  banz_scaper.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
import os
import re
import json

import lxml.html
import requests


class BAnzScraper(object):
    BASE_URL = 'https://www.bundesanzeiger.de/ebanzwww/wexsservlet?'
    BASE = 'page.navid=to_official_part&global_data.designmode=eb'
    YEAR = ('page.navid=official_starttoofficial_start_changeyear'
            '&genericsearch_param.year=%s&genericsearch_param.edition='
            '&genericsearch_param.sort_type=')
    LIST = ('genericsearch_param.edition=%s&genericsearch_param.sort_type='
            '&%%28page.navid%%3Dofficial_starttoofficial_start_update%%29='
            'Veröffentlichungen+anzeigen')

    MONTHS = [u'Januar', u'Februar', u'März', u'April', u'Mai', u'Juni', u'Juli',
            u'August', u'September', u'Oktober', u'November', u'Dezember']

    def get(self, url):
        return requests.get(url)

    def scrape(self, low=0, high=10000):
        collection = {}
        years = self.get_years()
        for year in years:
            if not (low <= year <= high):
                continue
            dates = self.get_dates(year)
            for date in dates:
                print year, date
                collection.update(self.get_items(year, date))
        return collection

    def get_years(self):
        url = self.BASE_URL + self.BASE
        response = self.get(url)
        years = []
        root = lxml.html.fromstring(response.text)
        selector = '#td_sub_menu_v li'
        for li in root.cssselect(selector):
            try:
                year = int(li.text_content())
            except ValueError:
                continue
            years.append(year)
        return years

    def get_dates(self, year):
        url = self.BASE_URL + self.YEAR % year
        response = self.get(url)
        dates = []
        root = lxml.html.fromstring(response.text)
        selector = 'select[name="genericsearch_param.edition"] option'
        for option in root.cssselect(selector):
            dates.append((option.attrib['value'], option.text_content().strip()))
        return dates

    def get_items(self, year, date):
        url = self.BASE_URL + self.LIST % date[0]
        response = self.get(url)
        items = {}
        root = lxml.html.fromstring(response.text)
        selector = 'table[summary="Trefferliste"] tr'
        for tr in root.cssselect(selector):
            tds = tr.cssselect('td')
            if len(tds) != 3:
                continue
            public_body = tds[0].text_content().strip()
            link = tds[1].cssselect('a')[0]
            additional = []
            for c in tds[1].getchildren()[1:]:
                if c.tail is not None and c.tail.strip():
                    additional.append(c.tail.strip())
            orig_date = None
            for a in additional:
                match = re.search('[Vv]om (\d+)\. (\w+) (\d{4})', a, re.U)
                if match is not None:
                    day = int(match.group(1))
                    month = self.MONTHS.index(match.group(2)) + 1
                    year = int(match.group(3))
                    orig_date = '%02d.%02d.%d' % (day, month, year)
                    break
            name = link.text_content()[1:]
            name = re.sub('\s+', ' ', name)
            ident = tds[2].text_content().strip()
            items[ident] = {
                'ident': ident,
                'public_body': public_body,
                'name': name,
                'date': date[1],
                'original_date': orig_date,
                'additional': additional
            }
        return items


def main(arguments):
    minyear = arguments['<minyear>'] or 0
    maxyear = arguments['<maxyear>'] or 10000
    minyear = int(minyear)
    maxyear = int(maxyear)
    banz = BAnzScraper()
    data = {}
    if os.path.exists(arguments['<outputfile>']):
        with file(arguments['<outputfile>']) as f:
            data = json.load(f)
    data.update(banz.scrape(minyear, maxyear))
    with file(arguments['<outputfile>'], 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    from docopt import docopt
    arguments = docopt(__doc__, version='BAnz-Scraper 0.0.1')
    main(arguments)

########NEW FILE########
__FILENAME__ = bgbl_scraper
# -*- encoding: utf-8 -*-
"""BGBl-Scraper.

Usage:
  bgbl_scaper.py <outputfile> [<minyear> [<maxyear>]]
  bgbl_scaper.py -h | --help
  bgbl_scaper.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""
import os
import re
import json
from collections import defaultdict

import lxml.html
import requests


class BGBLScraper(object):
    BASE_URL = 'http://www.bgbl.de/Xaver/'
    START = 'start.xav?startbk=Bundesanzeiger_BGBl'
    BASE_TOC = ('toc.xav?tocf=xaver.component.TOC_0'
                '&tf=xaver.component.Text_0&qmf=&hlf='
                '&bk=Bundesanzeiger_BGBl&dir=center'
                '&start=1&cur=1&op=1')
    MAIN_TOC = ('toc.xav?tocf=xaver.component.TOC_0'
                '&tf=xaver.component.Text_0&qmf=&hlf='
                '&bk=Bundesanzeiger_BGBl&dir=center'
                '&op=%s')
    YEAR_TOC = ('toc.xav?tocf=xaver.component.TOC_0'
                '&tf=xaver.component.Text_0&qmf=&hlf='
                '&bk=Bundesanzeiger_BGBl&dir=center'
                '&op=%(tocid)s&cur=%(tocid)s&start=%(tocid)s')
    TEXT = ('text.xav?tf=xaver.component.Text_0&tocf='
            '&qmf=&hlf=xaver.component.Hitlist_0'
            '&bk=Bundesanzeiger_BGBl&start=%2F%2F*%5B%40node_id%3D%27__docid__%27%5D')

    year_toc = defaultdict(dict)
    year_docs = defaultdict(dict)
    toc = {}

    def __init__(self, part_count=2):
        self.sid = None
        self.part_count = part_count

    def login(self):
        response = requests.get(self.BASE_URL + self.START)
        self.sid = response.headers['XaverSID']

    def sessionify(self, url):
        if not self.sid:
            self.login()
        return '%s&SID=%s' % (url, self.sid)

    def get(self, url):
        while True:
            response = requests.get(self.sessionify(url))
            if 'Session veraltet' in response.text:
                self.sid = None
                continue
            return response

    def scrape(self, low=0, high=10000):
        collection = {}
        self.toc_offsets = self.get_base_toc()
        # import pdb; pdb.set_trace()
        for part in range(1, self.part_count + 1):
            print part
            self.get_main_toc(part)
            self.get_all_year_tocs(part, low, high)
            collection.update(self.get_all_tocs(part, low, high))
        return collection

    def parse(self, response):
        response.encoding = 'utf-8'
        html = re.sub('([,\{])(\w+):', '\\1"\\2":', response.text)
        html = json.loads(html)['innerhtml']
        return lxml.html.fromstring(html)

    def get_base_toc(self):
        url = self.BASE_URL + self.BASE_TOC
        response = self.get(url)
        root = self.parse(response)
        selector = 'a.tocEntry'
        toc_offsets = []
        for a in root.cssselect(selector):
            if not 'Bundesgesetzblatt Teil' in a.attrib.get('title', ''):
                continue
            link_href = a.attrib['href']
            match = re.search('tocid=(\d+)&', link_href)
            if match:
                toc_offsets.append(match.group(1))
        return toc_offsets

    def get_main_toc(self, part=1):
        self.get_main_toc_part(part)

    def get_main_toc_part(self, part):
        offset = self.toc_offsets[part - 1]
        url = self.BASE_URL + (self.MAIN_TOC % offset)
        response = self.get(url)
        root = self.parse(response)
        selector = 'a.tocEntry'
        for a in root.cssselect(selector):
            try:
                year = int(a.text_content())
            except ValueError:
                continue
            doc_id = re.search('tocid=(\d+)&', a.attrib['href'])
            if doc_id is not None:
                self.year_toc[part][year] = doc_id.group(1)

    def get_all_year_tocs(self, part=1, low=0, high=10000):
        for year in self.year_toc[part]:
            if not (low <= year <= high):
                continue
            print "Getting Year TOC %d for %d" % (year, part)
            self.get_year_toc(part, year)

    def get_year_toc(self, part, year):
        year_doc_id = self.year_toc[part][year]
        # import pdb; pdb.set_trace()
        url = self.BASE_URL + self.YEAR_TOC % {'tocid': year_doc_id}
        response = self.get(url)
        root = self.parse(response)
        selector = 'a.tocEntry'
        for a in root.cssselect(selector):
            match = re.search('Nr\. (\d+) vom (\d{2}\.\d{2}\.\d{4})',
                              a.text_content())
            if match is None:
                continue
            print a.text_content()
            number = int(match.group(1))
            date = match.group(2)
            doc_id = re.search('start=%2f%2f\*%5B%40node_id%3D%27(\d+)%27%5D',
                               a.attrib['href'])
            doc_id = doc_id.group(1)
            self.year_docs[part].setdefault(year, {})
            self.year_docs[part][year][number] = {
                'date': date,
                'doc_id': doc_id
            }

    def get_all_tocs(self, part=1, low=0, high=10000):
        collection = {}
        for year in self.year_docs[part]:
            if not (low <= year <= high):
                continue
            for number in self.year_docs[part][year]:
                try:
                    data = self.get_toc(part, year, number)
                    collection['%d_%d_%d' % (part, year, number)] = data
                except:
                    print '%d %d' % (year, number)
                    json.dump(collection, file('temp.json', 'w'))
                    raise
                print '%d %d' % (year, number)
        return collection

    def get_toc(self, part, year, number):
        year_doc = self.year_docs[part][year][number]
        doc_id = year_doc['doc_id']
        url = self.BASE_URL + self.TEXT.replace('__docid__', doc_id)
        response = self.get(url)
        root = self.parse(response)
        toc = []
        for tr in root.cssselect('tr'):
            td = tr.cssselect('td')[1]
            divs = td.cssselect('div')
            law_date = None
            if not len(divs):
                continue
            if len(divs) == 2:
                divs = [None] + divs
            else:
                law_date = divs[0].text_content().strip()
            link = divs[1].cssselect('a')[0]
            name = link.text_content().strip()
            href = link.attrib['href']
            href = re.sub('SID=[^&]+&', '', href)
            text = divs[2].text_content().strip()
            print text
            match = re.search('aus +Nr. +(\d+) +vom +(\d{1,2}\.\d{1,2}\.\d{4}),'
                              ' +Seite *(\d*)\w?\.?$', text)
            page = None
            date = match.group(2)
            if match.group(3):
                page = int(match.group(3))
            kind = 'entry'
            if name in ('Komplette Ausgabe', 'Inhaltsverzeichnis'):
                # FIXME: there are sometimes more meta rows
                kind = 'meta'
            d = {
                'part': part,
                'year': year, 'toc_doc_id': doc_id,
                'number': number, 'date': date,
                'law_date': law_date, 'kind': kind,
                'name': name, 'href': href, 'page': page
            }
            toc.append(d)
        return toc


def main(arguments):
    minyear = arguments['<minyear>'] or 0
    maxyear = arguments['<maxyear>'] or 10000
    minyear = int(minyear)
    maxyear = int(maxyear)
    bgbl = BGBLScraper()
    data = {}
    if os.path.exists(arguments['<outputfile>']):
        with file(arguments['<outputfile>']) as f:
            data = json.load(f)
    data.update(bgbl.scrape(minyear, maxyear))
    with file(arguments['<outputfile>'], 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    from docopt import docopt
    arguments = docopt(__doc__, version='BGBl-Scraper 0.0.1')
    main(arguments)

########NEW FILE########
__FILENAME__ = lawde
"""LawDe.

Usage:
  lawde.py load [--path=<path>] <law>...
  lawde.py loadall [--path=<path>]
  lawde.py updatelist
  lawde.py -h | --help
  lawde.py --version

Options:
  --path=<path>  Path to laws dir [default: laws].
  -h --help     Show this screen.
  --version     Show version.

"""
import os
import re
from StringIO import StringIO
import json
import shutil
import time

from docopt import docopt
import requests
import zipfile
from xml.dom.minidom import parseString


class Lawde(object):
    BASE_URL = 'http://www.gesetze-im-internet.de'
    BASE_PATH = 'laws/'
    INDENT_CHAR = ' '
    INDENT = 2

    def __init__(self, path=BASE_PATH, lawlist='data/laws.json',
                **kwargs):
        self.indent = self.INDENT_CHAR * self.INDENT
        self.path = path
        self.lawlist = lawlist

    def build_zip_url(self, law):
        return '%s/%s/xml.zip' % (self.BASE_URL, law)

    def download_law(self, law):
        tries = 0
        while True:
            try:
                res = requests.get(self.build_zip_url(law))
                file('test.zip', 'w').write(res.content)
            except Exception as e:
                tries += 1
                print e
                if tries > 3:
                    raise e
                else:
                    print "Sleeping %d" % tries * 3
                    time.sleep(tries * 3)
            else:
                break
        try:
            zipf = zipfile.ZipFile(StringIO(res.content))
        except zipfile.BadZipfile:
            print "Removed %s" % law
            self.remove_law(law)
            return None
        return zipf

    def load(self, laws):
        total = float(len(laws))
        for i, law in enumerate(laws):
            if i % 10 == 0:
                print '%d%%' % (i / total * 100)
            zipfile = self.download_law(law)
            if zipfile is not None:
                self.store(law, zipfile)

    def build_law_path(self, law):
        prefix = law[0]
        return os.path.join(self.path, prefix, law)

    def remove_law(self, law):
        law_path = self.build_law_path(law)
        shutil.rmtree(law_path, ignore_errors=True)

    def store(self, law, zipf):
        self.remove_law(law)
        law_path = self.build_law_path(law)
        norm_date_re = re.compile('<norm builddate="\d+"')
        os.makedirs(law_path)
        for name in zipf.namelist():
            if name.endswith('.xml'):
                xml = zipf.open(name).read()
                xml = norm_date_re.sub('<norm', xml)
                dom = parseString(xml)
                xml = dom.toprettyxml(encoding='utf-8',
                    indent=self.indent)
                if not name.startswith('_'):
                    law_filename = os.path.join(law_path, '%s.xml' % law)
                else:
                    law_filename = name
                file(law_filename, 'w').write(xml)
            else:
                zipf.extract(name, law_path)

    def get_all_laws(self):
        return [l['slug'] for l in json.load(file(self.lawlist))]

    def loadall(self):
        self.load(self.get_all_laws())

    def update_list(self):
        BASE_URL = 'http://www.gesetze-im-internet.de/Teilliste_%s.html'
        CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'
        # Evil parsing of HTML with regex'
        REGEX = re.compile('href="\./([^\/]+)/index.html"><abbr title="([^"]*)">([^<]+)</abbr>')

        laws = []

        for char in CHARS:
            print "Loading part list %s" % char
            try:
                response = requests.get(BASE_URL % char.upper())
                html = response.content
            except Exception:
                continue
            html = html.decode('iso-8859-1')
            matches = REGEX.findall(html)
            for match in matches:
                laws.append({
                    'slug': match[0],
                    'name': match[1].replace('&quot;', '"'),
                    'abbreviation': match[2].strip()
                })
        json.dump(laws, file(self.lawlist, 'w'))


def main(arguments):
    nice_arguments = {}
    for k in arguments:
        if k.startswith('--'):
            nice_arguments[k[2:]] = arguments[k]
        else:
            nice_arguments[k] = arguments[k]
    lawde = Lawde(**nice_arguments)
    if arguments['load']:
        lawde.load(arguments['<law>'])
    elif arguments['loadall']:
        lawde.loadall()
    elif arguments['updatelist']:
        lawde.update_list()

if __name__ == '__main__':
    arguments = docopt(__doc__, version='LawDe 0.0.1')
    main(arguments)

########NEW FILE########
__FILENAME__ = lawdown
# -*- coding: utf-8 -*-
"""LawDown - Law To Markdown.

Usage:
  lawdown.py convert --name=<name>
  lawdown.py convert <inputpath> <outputpath>
  lawdown.py -h | --help
  lawdown.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --no-yaml

"""
import os
import sys
import shutil
import re
from glob import glob
from xml import sax
from collections import defaultdict
from textwrap import wrap
from StringIO import StringIO

import yaml


DEFAULT_YAML_HEADER = {
    'layout': 'default'
}


class LawToMarkdown(sax.ContentHandler):
    state = None
    text = ''
    current_text = ''
    indent_by = ' ' * 4
    list_index = ''
    first_meta = True
    ignore_until = None
    indent_level = 0
    in_list_item = 0
    in_list_index = False
    no_tag = True
    last_list_index = None
    entry_count = 0
    footnotes = {}
    current_heading_num = 1
    current_footnote = None
    no_emph_re = [
        re.compile('(\S?|^)([\*_])(\S)'),
        re.compile('([^\\\s])([\*_])(\S?|$)')
    ]
    list_start_re = re.compile('^(\d+)\.')

    def __init__(self, fileout,
            yaml_header=DEFAULT_YAML_HEADER,
            heading_anchor=False,
            orig_slug=None):
        self.fileout = fileout
        self.yaml_header = yaml_header
        self.heading_anchor = heading_anchor
        self.orig_slug = orig_slug

    def out(self, content):
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        self.fileout.write(content)
        return self

    def out_indented(self, content, indent=None):
        if indent is None:
            indent = self.indent_level
        self.out(self.indent_by * indent)
        self.out(content)

    def write(self, content='', nobreak=False):
        self.out(content + (u'\n' if not nobreak else ''))
        return self

    def write_wrapped(self, text, indent=None):
        if indent is None:
            indent = self.indent_level
        first_indent = ''
        if self.last_list_index is not None:
            space_count = max(0, len(self.indent_by) - (len(self.last_list_index) + 1))
            first_indent = ' ' + self.indent_by[0:space_count]
            self.last_list_index = None
        for line in wrap(text):
            if first_indent:
                self.out(first_indent)
            else:
                self.out(self.indent_by * indent)
                line = self.list_start_re.sub('\\1\\.', line)
            first_indent = ''
            self.write(line)

    def flush_text(self):
        if self.text.strip():
            self.write_wrapped(self.text)
        self.text = ''

    def startElement(self, name, attrs):
        name = name.lower()
        self.no_tag = False
        if self.ignore_until is not None:
            return
        if name == 'fnr':
            if self.state == 'meta':
                self.ignore_until = 'fnr'
                return
            else:
                if not attrs['ID'] in self.footnotes:
                    self.footnotes[attrs['ID']] = None
                    self.write('[^%s]' % attrs['ID'])
        if name == 'fussnoten':
            self.ignore_until = 'fussnoten'
        if name == "metadaten":
            self.meta = defaultdict(list)
            self.state = 'meta'
            return
        if name == "text":
            self.indent_level = 0
            self.state = 'text'
        if name == 'footnotes':
            self.state = 'footnotes'
        if self.state == 'footnotes':
            if name == 'footnote':
                self.indent_level += 1
                self.current_footnote = attrs['ID']
            return

        self.text += self.current_text
        self.text = self.text.replace('\n', ' ').strip()
        self.current_text = ''

        if name == 'table':
            self.flush_text()
            self.write()
        elif name == 'dl':
            self.flush_text()
            self.write()
            self.indent_level += 1
        elif name == 'row' or name == 'dd':
            if name == 'row':
                self.indent_level += 1
                self.list_index = '*'
                self.write_list_item()
            self.in_list_item += 1
        elif name == 'entry':
            self.indent_level += 1
            self.in_list_item += 1
            self.list_index = '*'
            self.write_list_item()
        elif name == 'img':
            self.flush_text()
            self.out_indented('![%s](%s)' % (attrs.get('ALT', attrs['SRC']), attrs['SRC']))
        elif name == 'dt':
            self.in_list_index = True
        elif name in ('u', 'b', 'f'):
            pass
        else:
            self.flush_text()

    def endElement(self, name):
        name = name.lower()
        self.no_tag = False
        if self.ignore_until is not None:
            if self.ignore_until == name:
                self.ignore_until = None
            return

        if name == 'u':
            self.current_text = u' *%s* ' % self.current_text.strip()
        elif name == 'f':
            self.current_text = u'*'
        elif name == 'b':
            self.current_text = u' **%s** ' % self.current_text.strip()

        self.text += self.current_text
        self.text = self.text.replace('\n', ' ').strip()
        self.current_text = ''

        if name == "metadaten":
            self.state = None
            if self.first_meta:
                self.first_meta = False
                self.write_big_header()
            else:
                self.write_norm_header()
            self.text = ''
            return
        if self.state == 'meta':
            if name == 'enbez' and self.text == u'Inhaltsübersicht':
                self.ignore_until = 'textdaten'
            else:
                self.meta[name].append(self.text)
            self.text = ''
            return
        elif self.state == 'footnotes':
            if name == 'footnote':
                self.flush_text()
                self.indent_level -= 1
            if name == 'footnotes':
                self.state = None
                self.write()
        if self.current_footnote:
            self.out('[^%s]: ' % self.current_footnote)
            self.current_footnote = None

        if self.in_list_index:
            self.list_index += self.text
            self.text = ''
            if name == 'dt':
                if not self.list_index:
                    self.list_index = '*'
                self.write_list_item()
                self.in_list_index = False
            return

        if name == 'br':
            self.text += '\n'
        elif name == 'table':
            self.write()
        elif name == 'dl':
            self.indent_level -= 1
            self.write()
        elif name == 'dd' or name == 'entry':
            self.in_list_item -= 1
            if name == 'entry':
                self.flush_text()
                self.indent_level -= 1
            self.write()
        elif name == 'la' or name == 'row':
            self.flush_text()
            self.write()
            if name == 'row':
                self.indent_level -= 1
                self.in_list_item -= 1
        elif name == 'p':
            self.flush_text()
            self.write()
        elif name == 'title':
            self.text = self.text.replace('\n', ' ')
            self.text = u'## %s' % self.text
            self.flush_text()
            self.write()
        elif name == 'subtitle':
            self.text = self.text.replace('\n', ' ')
            self.text = u'### %s' % self.text
            self.flush_text()
            self.write()

    def characters(self, text):
        if self.ignore_until is not None:
            return
        for no_emph_re in self.no_emph_re:
            text = no_emph_re.sub(r'\1\\\2\3', text)
        self.current_text += text
        self.no_tag = True

    def endDocument(self):
        pass

    def write_list_item(self):
        self.last_list_index = self.list_index
        self.out_indented(self.list_index, indent=self.indent_level - 1)
        self.list_index = ''

    def clean_title(self, title):
        title = title.replace(' \\*)', '').strip()
        title = re.sub(r'\\\*', '*', title)
        return title

    def write_big_header(self):
        self.store_filename(self.meta['jurabk'][0])

        title = self.clean_title(self.meta['langue'][0])

        meta = {
            'Title': title,
            'origslug': self.orig_slug,
            'jurabk': self.meta['jurabk'][0],
            'slug': self.filename
        }

        if self.yaml_header:
            meta.update(self.yaml_header)
            self.out(yaml.safe_dump(meta,
                explicit_start=True,
                explicit_end=False,
                allow_unicode=True,
                default_flow_style=False
            ))
            # Blank line ensures meta doesn't become headline
            self.write('\n---')
        else:
            for kv in meta.items():
                self.write('%s: %s' % kv)
        self.write()
        heading = '# %s (%s)' % (title, self.meta['jurabk'][0])
        self.write(heading)
        self.write()
        if 'ausfertigung-datum' in self.meta:
            self.write(u'Ausfertigungsdatum\n:   %s\n' % self.meta['ausfertigung-datum'][0])
        if 'periodikum' in self.meta and 'zitstelle' in self.meta:
            self.write(u'Fundstelle\n:   %s: %s\n' % (
                self.meta['periodikum'][0], self.meta['zitstelle'][0]))

        for text in self.meta.get('standkommentar', []):
            try:
                k, v = text.split(u' durch ', 1)
            except ValueError:
                self.write('Stand: %s' % text)
            else:
                k = k.capitalize()
                self.write(u'%s durch\n:   %s\n' % (k, v))
        self.text = ''

    def write_norm_header(self):
        hn = '#'
        if 'gliederungskennzahl' in self.meta:
            heading_num = len(self.meta['gliederungskennzahl'][0]) / 3 + 1
            self.current_heading_num = heading_num
        else:
            heading_num = self.current_heading_num + 1
        title = ''
        link = ''
        if 'gliederungsbez' in self.meta:
            title = self.meta['gliederungsbez'][0]
            link = title
        if 'gliederungstitel' in self.meta:
            if title:
                title = u'%s - %s' % (title, self.meta['gliederungstitel'][0])
            else:
                title = self.meta['gliederungstitel'][0]
        if 'enbez' in self.meta:
            title = self.meta['enbez'][0]
            link = title
        if 'titel' in self.meta:
            if title:
                title = u'%s %s' % (title, self.meta['titel'][0])
            else:
                title = self.meta['titel'][0]
        if not title:
            return
        hn = hn * min(heading_num, 6)
        if self.heading_anchor:
            if link:
                link = re.sub('\(X+\)', '', link).strip()
                link = link.replace(u'§', 'P')
                link = u' [%s]' % link
        else:
            link = ''
        heading = u'%s %s%s' % (hn, title, link)
        self.write()
        self.write(heading)
        self.write()

    def store_filename(self, abk):
        abk = abk.lower()
        abk = abk.strip()
        replacements = {
            u'ä': u'ae',
            u'ö': u'oe',
            u'ü': u'ue',
            u'ß': u'ss'
        }
        for k, v in replacements.items():
            abk = abk.replace(k, v)
        abk = re.sub('[^\w-]', '_', abk)
        self.filename = abk


def law_to_markdown(filein, fileout=None, name=None):
    ret = False
    if fileout is None:
        fileout = StringIO()
        ret = True
    parser = sax.make_parser()
    if name is None:
        orig_slug = filein.name.split('/')[-1].split('.')[0]
    else:
        orig_slug = name
    handler = LawToMarkdown(fileout, orig_slug=orig_slug)
    parser.setFeature(sax.handler.feature_external_ges, False)
    parser.setContentHandler(handler)
    parser.parse(filein)
    if ret:
        fileout.filename = handler.filename
        return fileout


def main(arguments):
    if arguments['<inputpath>'] is None and arguments['<outputpath>'] is None:
        law_to_markdown(sys.stdin, sys.stdout, name=arguments['--name'])
        return
    paths = set()
    for filename in glob(os.path.join(arguments['<inputpath>'], '*/*/*.xml')):
        inpath = os.path.dirname(os.path.abspath(filename))
        if inpath in paths:
            continue
        paths.add(inpath)
        law_name = inpath.split('/')[-1]
        with file(filename) as infile:
            out = law_to_markdown(infile)
        slug = out.filename
        outpath = os.path.abspath(os.path.join(arguments['<outputpath>'], slug[0], slug))
        print outpath
        assert outpath.count('/') > 2  # um, better be safe
        outfilename = os.path.join(outpath, 'index.md')
        shutil.rmtree(outpath, ignore_errors=True)
        os.makedirs(outpath)
        for part in glob(os.path.join(inpath, '*')):
            if part.endswith('%s.xml' % law_name):
                continue
            part_filename = os.path.basename(part)
            shutil.copy(part, os.path.join(outpath, part_filename))
        with file(outfilename, 'w') as outfile:
            outfile.write(out.getvalue())
        out.close()


if __name__ == '__main__':
    from docopt import docopt
    arguments = docopt(__doc__, version='LawDown 0.0.1')
    main(arguments)

########NEW FILE########
__FILENAME__ = lawgit
# -*- encoding: utf-8 -*-
"""LawGit - Semi-automatic law change commits.

Usage:
  lawgit.py autocommit <repopath> [--dry-run] [--consider-old] [--grep=<grep>]
  lawgit.py -h | --help
  lawgit.py --version

Options:
  --dry-run         Make a dry run.
  --consider-old    Consider old laws for commits.
  -h --help         Show this screen.
  --version         Show version.

"""
import re
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

from git import Repo
from git.exc import GitCommandError


class TransientState(Exception):
    pass


class BGBlSource(object):
    """BGBl as a source for law change"""

    change_re = [
        re.compile(u'BGBl +(?P<part>I+):? *(?P<year>\d{4}), +(?:S\. )?(?P<page>\d+)'),
        re.compile(u'BGBl +(?P<part>I+):? *(?P<year>\d{4}), \d \((?P<page>\d+)\)'),
        re.compile(u'BGBl +(?P<part>I+):? *(?P<year>\d{4}), (?P<page>\d+)'),
        re.compile('\d{1,2}\.\.?\d{1,2}\.\.?(?P<year>\d{4}) (?P<part>I+) (?:S\. )?(?P<page>\d+)'),
        re.compile(u'(?P<year>\d{4}).{,8}?BGBl\.? +(?P<part>I+):? +(?:S\. )?(?P<page>\d+)'),
        # re.compile(u'Art. \d+ G v. (?P<day>\d{1,2}).(?P<month>\d{1,2}).(?P<year>\d{4})')
    ]

    transient = (
        u"noch nicht berücksichtigt",
        u"noch nicht abschließend bearbeitet"
    )

    def __init__(self, source):
        self.load(source)

    def __str__(self):
        return self.__class__.__name__

    def load(self, source):
        self.data = {}
        data = json.load(file(source))
        for key, toc_list in data.iteritems():
            for toc in toc_list:
                if toc['kind'] == 'meta':
                    continue
                toc['part_i'] = 'I' * toc['part']
                self.data[(toc['year'], toc['page'], toc['part'])] = toc

    def find_candidates(self, lines):
        candidates = []
        for line in lines:
            for c_re in self.change_re:
                for match in c_re.finditer(line):
                    if any(t in line for t in self.transient):
                        raise TransientState
                    matchdict = match.groupdict()
                    if 'page' in matchdict:
                        key = (
                            int(matchdict['year']),
                            int(matchdict['page']),
                            len(matchdict['part'])
                        )
                        if key in self.data:
                            candidates.append(key)
                    # elif 'month' in matchdict:
                    #     for key, toc in self.data.iteritems():
                    #         if toc['date'] == '{day:0>2}.{month:0>2}.{year}'.format(**matchdict):
                    #             candidates.append(key)
        return candidates

    def get_order_key(self, key):
        return self.get_date(key)

    def get_date(self, key):
        bgbl_entry = self.data[key]
        return datetime.strptime(bgbl_entry['date'], '%d.%m.%Y')

    def get_branch_name(self, key):
        bgbl_entry = self.data[key]
        return 'bgbl/%s/%s-%s' % (
            bgbl_entry['year'],
            bgbl_entry['part'],
            bgbl_entry['number']
        )

    def get_ident(self, key):
        bgbl_entry = self.data[key]
        return bgbl_entry['href']

    def get_message(self, key):
        bgbl_entry = self.data[key]
        return ('%(name)s\n\n%(date)s: BGBl %(part_i)s: %(year)s, '
                '%(page)s (Nr. %(number)s)' % bgbl_entry)


class BAnzSource(object):
    """BAnz as a source for law change"""

    def __init__(self, source):
        self.load(source)

    def __str__(self):
        return self.__class__.__name__

    def load(self, source):
        self.data = json.load(file(source))

    def find_candidates(self, lines):
        candidates = []
        for line in lines:
            line = re.sub('[^\w \.]', '', line)
            line = re.sub(' \d{4} ', ' ', line)
            for key in self.data:
                if key in line:
                    if u"noch nicht berücksichtigt" in line:
                        raise TransientState
                    candidates.append(key)
        return candidates

    def get_order_key(self, key):
        return self.get_date(key)

    def get_date(self, key):
        entry = self.data[key]
        return datetime.strptime(entry['date'], '%d.%m.%Y')

    def get_branch_name(self, key):
        entry = self.data[key]
        return 'banz/%s/%s' % (
            entry['date'].split('.')[2],
            '-'.join(reversed(entry['date'].split('.')[:2]))
        )

    def get_ident(self, key):
        return key

    def get_message(self, key):
        entry = dict(self.data[key])
        additional_str = ', '.join(entry['additional'])
        if additional_str:
            entry['additional_str'] = ', %s' % additional_str
        else:
            entry['additional_str'] = ''
        return ('%(name)s\n\n%(date)s: %(ident)s, %(public_body)s'
                '%(additional_str)s' % entry)


class VkblSource(object):
    """VkBl as a source for law change"""

    transient = (
        u"noch nicht berücksichtigt",
        u"noch nicht abschließend bearbeitet"
    )

    change_re = [
        re.compile(u'VkBl: *(?P<year>\d{4}),? +(?:S\. )?(?P<page>\d+)')
    ]

    def __init__(self, source):
        self.load(source)

    def __str__(self):
        return self.__class__.__name__

    def load(self, source):
        self.data = {}
        data = json.load(file(source))
        for key, value in data.iteritems():
            if value['jahr'] and value['seite']:
                ident = (int(value['jahr']), int(value['seite']))
                value['date'] = value['verffentlichtam']
                self.data[ident] = value

    def find_candidates(self, lines):
        candidates = []
        for line in lines:
            for c_re in self.change_re:
                for match in c_re.finditer(line):
                    if any(t in line for t in self.transient):
                        raise TransientState
                    matchdict = match.groupdict()
                    key = (
                        int(matchdict['year']),
                        int(matchdict['page']),
                    )
                    if key in self.data:
                        candidates.append(key)
        return candidates

    def get_order_key(self, key):
        return self.get_date(key)

    def get_date(self, key):
        entry = self.data[key]
        return datetime.strptime(entry['verffentlichtam'], '%d.%m.%Y')

    def get_branch_name(self, key):
        entry = self.data[key]
        return 'vkbl/%s/%s' % (
            entry['verffentlichtam'].split('.')[2],
            '-'.join(reversed(entry['date'].split('.')[:2]))
        )

    def get_ident(self, key):
        return key

    def get_message(self, key):
        """
        {u'description': u'', u'vid': u'19463', u'seite': u'945', u'price': 3.4, u'edition': u'23/2012', u'aufgehobenam': u'', 'date': u'15.12.2012', u'verffentlichtam': u'15.12.2012', u'pages': 9, u'title': u'Verordnung \xfcber die Betriebszeiten der Schleusen und Hebewerke an den Bundeswasserstra\xdfen im Zust\xe4ndigkeitsbereich der Wasser- und Schifffahrtsdirektion Ost', u'jahr': u'2012', u'inkraftab': u'01.01.2013', u'verkndetam': u'22.11.2012', u'link': u'../shop/in_basket.php?vID=19463', u'aktenzeichen': u'', u'genre': u'Wasserstra\xdfen, Schifffahrt', u'vonummer': u'215'}"
        """
        entry = dict(self.data[key])
        return ('%(title)s\n\n%(verkndetam)s: %(edition)s S. %(seite)s (%(vonummer)s)' % entry)


class LawGit(object):
    laws = defaultdict(list)
    law_changes = {}
    bgbl_changes = defaultdict(list)

    def __init__(self, path, dry_run=False, consider_old=False, grep=None):
        self.path = path
        self.dry_run = dry_run
        self.grep = grep
        self.consider_old = consider_old
        self.repo = Repo(path)
        self.sources = [
            BGBlSource('data/bgbl.json'),
            BAnzSource('data/banz.json'),
            VkblSource('data/vkbl.json')
        ]

    def prepare_commits(self):
        branches = defaultdict(dict)
        self.collect_laws()
        for law in self.laws:
            result = self.determine_source(law)
            if result is None:
                continue
            source, key = result
            date = source.get_date(key)
            if not self.consider_old and date + timedelta(days=30 * 12) < datetime.now():
                print "Skipped %s %s (too old)" % (law, result)
                continue
            branch_name = source.get_branch_name(key)
            ident = source.get_ident(key)
            branches[branch_name].setdefault(ident, [])
            branches[branch_name][ident].append((law, source, key))
        return branches

    def collect_laws(self):
        hcommit = self.repo.head.commit
        wdiff = hcommit.diff(None, create_patch=True)
        for diff in wdiff:
            law_name = diff.b_blob.path.split('/')[1]
            if self.grep and not self.grep in law_name:
                continue
            filename = '/'.join(diff.b_blob.path.split('/')[:2] + ['index.md'])
            filename = os.path.join(self.path, filename)
            if os.path.exists(filename):
                self.laws[law_name].append(diff.b_blob.path)
                self.law_changes[law_name] = (False, diff.diff, filename)

        for filename in self.repo.untracked_files:
            law_name = filename.split('/')[1]
            if self.grep and not self.grep in law_name:
                continue
            self.laws[law_name].append(filename)
            filename = '/'.join(filename.split('/')[:2] + ['index.md'])
            filename = os.path.join(self.path, filename)
            with file(filename) as f:
                self.law_changes[law_name] = (True, f.read(), filename)

    def determine_source(self, law_name):
        new_file, lines, filename = self.law_changes[law_name]
        lines = [line.decode('utf-8') for line in lines.splitlines()]
        candidates = self.find_in_sources(lines)
        if not candidates:
            with file(filename) as f:
                lines = [line.decode('utf-8') for line in f.read().splitlines()]
            candidates.extend(self.find_in_sources(lines))
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: x[0].get_order_key(x[1]))[-1]

    def find_in_sources(self, lines):
        candidates = []
        for source in self.sources:
            try:
                candidates.extend([(source, c) for c in source.find_candidates(lines)])
            except TransientState:
                return []
        return candidates

    def autocommit(self):
        branches = self.prepare_commits()
        for branch in sorted(branches.keys()):
            self.commit_branch(branch, branches[branch])

    def commit_branch(self, branch, commits):
        if not self.dry_run:
            self.repo.git.stash()
        try:
            print "git checkout -b %s" % branch
            if not self.dry_run:
                self.repo.git.checkout(b=branch)
        except GitCommandError:
            print "git checkout %s" % branch
            if not self.dry_run:
                self.repo.git.checkout(branch)
        if not self.dry_run:
            self.repo.git.merge('master')
            self.repo.git.stash('pop')
        for ident in commits:
            for law_name, source, key in commits[ident]:
                for filename in self.laws[law_name]:
                    if os.path.exists(os.path.join(self.path, filename)):
                        print "git add %s" % filename
                        if not self.dry_run:
                            self.repo.index.add([filename])
                    else:
                        print "git rm %s" % filename
                        if not self.dry_run:
                            self.repo.index.remove([filename])
            msg = source.get_message(key)
            print 'git commit -m"%s"' % msg
            if not self.dry_run:
                self.repo.index.commit(msg.encode('utf-8'))
            print ""
        print "git checkout master"
        if not self.dry_run:
            self.repo.heads.master.checkout()
        print "git merge %s --no-ff" % branch
        if not self.dry_run:
            self.repo.git.merge(branch, no_ff=True)


def main(arguments):
    kwargs = {
        'dry_run': arguments['--dry-run'],
        'consider_old': arguments['--consider-old'],
        'grep': arguments['--grep']
    }

    lg = LawGit(arguments['<repopath>'], **kwargs)

    if arguments['autocommit']:
        lg.autocommit()

if __name__ == '__main__':
    from docopt import docopt
    arguments = docopt(__doc__, version='LawGit 0.0.2')
    main(arguments)

########NEW FILE########
__FILENAME__ = vkbl_scraper
# -*- encoding: utf-8 -*-
"""VkBl-Scraper.

Usage:
  vkbl_scaper.py <outputfile> [<minyear> [<maxyear>]]
  vkbl_scaper.py -h | --help
  vkbl_scaper.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""

import re
import os
import json
import time
import datetime
import requests

import lxml.html


def get_url(url):
    response = requests.get(url)
    response.encoding = 'latin1'
    return response.text


def ctext(el):
    result = []
    if el.text:
        result.append(el.text)
    for sel in el:
        if sel.tag in ["br"]:
            result.append(ctext(sel))
            result.append('\n')
        else:
            result.append(ctext(sel))
        if sel.tail:
            result.append(sel.tail)
    return "".join(result)

slugify_re = re.compile('[^a-z]')


def slugify(key):
    return slugify_re.sub('', key.lower())


class VkblScraper(object):
    URL = 'http://www.verkehr-data.com/docs/artikelsuche.php?seitenzahl=1&anzahl=10000&start=0&Titel=&Datum=&Muster=&Muster2=&Jahrgang=%d&VerordnungsNr=&Seite=&Bereichsname=&DB=&Aktenzeichen='
    PRICE_RE = re.compile('Preis: (\d+,\d+) \((\d+) Seite')

    def scrape(self, low=1947, high=datetime.datetime.now().year):
        items = {}
        total_sum = 0
        for year in range(low, high + 1):
            tries = 0
            while True:
                try:
                    response = get_url(self.URL % year)
                except Exception:
                    tries += 1
                    if tries > 10:
                        raise
                    time.sleep(2 * tries)
                    continue
                else:
                    break
            root = lxml.html.fromstring(response)
            total_sum += len(root.cssselect(".tabelle2"))
            print year, len(root.cssselect(".tabelle2"))
            for i, table in enumerate(root.cssselect(".tabelle2")):
                trs = table.cssselect('tr')
                header = trs[0].cssselect('td')[0].text_content().strip()
                print i, header
                try:
                    genre, edition = header.split(u'\xa0 ')
                    edition = edition.split(' ')[2]
                except ValueError:
                    genre = header
                    edition = ''
                title = ctext(trs[1].cssselect('td')[0]).replace('Titel:', '').strip().splitlines()
                title = [t.strip() for t in title if t.strip()]
                title, description = title[0], '\n'.join(title[1:])
                extra = {}
                for tr in trs[2:]:
                    tds = tr.cssselect('td')
                    if len(tds) == 2:
                        key = tds[0].text_content().replace(':', '').strip()
                        value = tds[1].text_content().strip()
                        extra[slugify(key)] = value
                    elif len(tds) == 1:
                        if tds[0].cssselect('img[src="../images/orange.gif"]'):
                            extra['link'] = tds[0].cssselect('a')[0].attrib['href']
                            extra['vid'] = extra['link'].split('=')[-1]
                            match = self.PRICE_RE.search(tds[0].text_content())
                            extra['price'] = float(match.group(1).replace(',', '.'))
                            extra['pages'] = int(match.group(2))
                data = dict(extra)
                data.update({
                    'genre': genre,
                    'edition': edition,
                    'title': title,
                    'description': description
                })
                ident = '%s.%s.%s.%s' % (
                    data.get('jahr', ''),
                    data.get('vonummer', ''),
                    data.get('seite', ''),
                    data.get('aktenzeichen', '')
                )
                items[ident] = data
        print total_sum, len(items)
        return items


def main(arguments):
    current_year = datetime.datetime.now().year
    minyear = arguments['<minyear>'] or 1947
    maxyear = arguments['<maxyear>'] or current_year
    minyear = int(minyear)
    maxyear = int(maxyear)
    vkbl = VkblScraper()
    data = {}
    if os.path.exists(arguments['<outputfile>']):
        with file(arguments['<outputfile>']) as f:
            data = json.load(f)
    data.update(vkbl.scrape(minyear, maxyear))
    with file(arguments['<outputfile>'], 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    from docopt import docopt
    arguments = docopt(__doc__, version='VkBl-Scraper 0.0.1')
    main(arguments)

########NEW FILE########
