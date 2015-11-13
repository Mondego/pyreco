__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'
distribute_source = 'https://bitbucket.org/pypa/setuptools/raw/f657df1f1ed46596d236376649c99a470662b4ba/distribute_setup.py'

# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.insert(0, 'buildout:accept-buildout-test-releases=true')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
        if sys.version_info[:2] == (2, 4):
            setup_args['version'] = '0.6.32'
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if not find_links and options.accept_buildout_test_releases:
    find_links = 'http://downloads.buildout.org/'
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if distv >= pkg_resources.parse_version('2dev'):
                continue
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version

if version:
    requirement += '=='+version
else:
    requirement += '<2dev'

cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout

# If there isn't already a command in the args, add bootstrap
if not [a for a in args if '=' not in a]:
    args.append('bootstrap')


# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = basic_engine

categories = ['general'] # optional

def request(query, params):
    '''pre-request callback
    params<dict>:
      method  : POST/GET
      headers : {}
      data    : {} # if method == POST
      url     : ''
      category: 'search category'
      pageno  : 1 # number of the requested page
    '''

    params['url'] = 'https://host/%s' % query

    return params


def response(resp):
    '''post-response callback
    resp: requests response object
    '''
    return [{'url': '', 'title': '', 'content': ''}]


########NEW FILE########
__FILENAME__ = autocomplete
from lxml import etree
from requests import get
from json import loads
from urllib import urlencode


def dbpedia(query):
    # dbpedia autocompleter
    autocomplete_url = 'http://lookup.dbpedia.org/api/search.asmx/KeywordSearch?'  # noqa

    response = get(autocomplete_url
                   + urlencode(dict(QueryString=query)))

    results = []

    if response.ok:
        dom = etree.fromstring(response.content)
        results = dom.xpath('//a:Result/a:Label//text()',
                            namespaces={'a': 'http://lookup.dbpedia.org/'})

    return results


def google(query):
    # google autocompleter
    autocomplete_url = 'http://suggestqueries.google.com/complete/search?client=toolbar&'  # noqa

    response = get(autocomplete_url
                   + urlencode(dict(q=query)))

    results = []

    if response.ok:
        dom = etree.fromstring(response.text)
        results = dom.xpath('//suggestion/@data')

    return results


def wikipedia(query):
    # wikipedia autocompleter
    url = 'https://en.wikipedia.org/w/api.php?action=opensearch&{0}&limit=10&namespace=0&format=json'  # noqa

    resp = loads(get(url.format(urlencode(dict(q=query)))).text)
    if len(resp) > 1:
        return resp[1]
    return []


backends = {'dbpedia': dbpedia,
            'google': google,
            'wikipedia': wikipedia
            }

########NEW FILE########
__FILENAME__ = bing
from urllib import urlencode
from cgi import escape
from lxml import html

base_url = 'http://www.bing.com/'
search_string = 'search?{query}&first={offset}'
paging = True
language_support = True


def request(query, params):
    offset = (params['pageno'] - 1) * 10 + 1
    if params['language'] == 'all':
        language = 'en-US'
    else:
        language = params['language'].replace('_', '-')
    search_path = search_string.format(
        query=urlencode({'q': query, 'setmkt': language}),
        offset=offset)

    params['cookies']['SRCHHPGUSR'] = \
        'NEWWND=0&NRSLT=-1&SRCHLANG=' + language.split('-')[0]
    #if params['category'] == 'images':
    #    params['url'] = base_url + 'images/' + search_path
    params['url'] = base_url + search_path
    return params


def response(resp):
    global base_url
    results = []
    dom = html.fromstring(resp.content)
    for result in dom.xpath('//div[@class="sa_cc"]'):
        link = result.xpath('.//h3/a')[0]
        url = link.attrib.get('href')
        title = ' '.join(link.xpath('.//text()'))
        content = escape(' '.join(result.xpath('.//p//text()')))
        results.append({'url': url, 'title': title, 'content': content})

    if results:
        return results

    for result in dom.xpath('//li[@class="b_algo"]'):
        link = result.xpath('.//h2/a')[0]
        url = link.attrib.get('href')
        title = ' '.join(link.xpath('.//text()'))
        content = escape(' '.join(result.xpath('.//p//text()')))
        results.append({'url': url, 'title': title, 'content': content})
    return results

########NEW FILE########
__FILENAME__ = bing_news
from urllib import urlencode
from cgi import escape
from lxml import html

categories = ['news']

base_url = 'http://www.bing.com/'
search_string = 'news/search?{query}&first={offset}'
paging = True
language_support = True


def request(query, params):
    offset = (params['pageno'] - 1) * 10 + 1
    if params['language'] == 'all':
        language = 'en-US'
    else:
        language = params['language'].replace('_', '-')
    search_path = search_string.format(
        query=urlencode({'q': query, 'setmkt': language}),
        offset=offset)

    params['cookies']['SRCHHPGUSR'] = \
        'NEWWND=0&NRSLT=-1&SRCHLANG=' + language.split('-')[0]
    #if params['category'] == 'images':
    # params['url'] = base_url + 'images/' + search_path
    params['url'] = base_url + search_path
    return params


def response(resp):
    global base_url
    results = []
    dom = html.fromstring(resp.content)
    for result in dom.xpath('//div[@class="sa_cc"]'):
        link = result.xpath('.//h3/a')[0]
        url = link.attrib.get('href')
        title = ' '.join(link.xpath('.//text()'))
        content = escape(' '.join(result.xpath('.//p//text()')))
        results.append({'url': url, 'title': title, 'content': content})

    if results:
        return results

    for result in dom.xpath('//li[@class="b_algo"]'):
        link = result.xpath('.//h2/a')[0]
        url = link.attrib.get('href')
        title = ' '.join(link.xpath('.//text()'))
        content = escape(' '.join(result.xpath('.//p//text()')))
        results.append({'url': url, 'title': title, 'content': content})
    return results

########NEW FILE########
__FILENAME__ = currency_convert
from datetime import datetime
import re

categories = []
url = 'http://finance.yahoo.com/d/quotes.csv?e=.csv&f=sl1d1t1&s={query}=X'
weight = 100

parser_re = re.compile(r'^\W*(\d+(?:\.\d+)?)\W*([a-z]{3})\W*(?:in)?\W*([a-z]{3})\W*$', re.I)  # noqa


def request(query, params):
    m = parser_re.match(query)
    if not m:
        # wrong query
        return params
    try:
        ammount, from_currency, to_currency = m.groups()
        ammount = float(ammount)
    except:
        # wrong params
        return params

    q = (from_currency + to_currency).upper()

    params['url'] = url.format(query=q)
    params['ammount'] = ammount
    params['from'] = from_currency
    params['to'] = to_currency

    return params


def response(resp):
    global base_url
    results = []
    try:
        _, conversion_rate, _ = resp.text.split(',', 2)
        conversion_rate = float(conversion_rate)
    except:
        return results

    title = '{0} {1} in {2} is {3}'.format(
        resp.search_params['ammount'],
        resp.search_params['from'],
        resp.search_params['to'],
        resp.search_params['ammount'] * conversion_rate
    )

    content = '1 {0} is {1} {2}'.format(resp.search_params['from'],
                                        conversion_rate,
                                        resp.search_params['to'])
    now_date = datetime.now().strftime('%Y%m%d')
    url = 'http://finance.yahoo.com/currency/converter-results/{0}/{1}-{2}-to-{3}.html'  # noqa
    url = url.format(
        now_date,
        resp.search_params['ammount'],
        resp.search_params['from'].lower(),
        resp.search_params['to'].lower()
    )
    results.append({'title': title, 'content': content, 'url': url})

    return results

########NEW FILE########
__FILENAME__ = dailymotion
from urllib import urlencode
from json import loads
from lxml import html

categories = ['videos']
locale = 'en_US'

# see http://www.dailymotion.com/doc/api/obj-video.html
search_url = 'https://api.dailymotion.com/videos?fields=title,description,duration,url,thumbnail_360_url&sort=relevance&limit=25&page={pageno}&{query}'  # noqa

# TODO use video result template
content_tpl = '<a href="{0}" title="{0}" ><img src="{1}" /></a><br />'

paging = True


def request(query, params):
    params['url'] = search_url.format(
        query=urlencode({'search': query, 'localization': locale}),
        pageno=params['pageno'])
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)
    if not 'list' in search_res:
        return results
    for res in search_res['list']:
        title = res['title']
        url = res['url']
        if res['thumbnail_360_url']:
            content = content_tpl.format(url, res['thumbnail_360_url'])
        else:
            content = ''
        if res['description']:
            description = text_content_from_html(res['description'])
            content += description[:500]
        results.append({'url': url, 'title': title, 'content': content})
    return results


def text_content_from_html(html_string):
    desc_html = html.fragment_fromstring(html_string, create_parent=True)
    return desc_html.text_content()

########NEW FILE########
__FILENAME__ = deviantart
from urllib import urlencode
from urlparse import urljoin
from lxml import html

categories = ['images']

base_url = 'https://www.deviantart.com/'
search_url = base_url+'search?offset={offset}&{query}'

paging = True


def request(query, params):
    offset = (params['pageno'] - 1) * 24
    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'q': query}))
    return params


def response(resp):
    global base_url
    results = []
    if resp.status_code == 302:
        return results
    dom = html.fromstring(resp.text)
    for result in dom.xpath('//div[contains(@class, "tt-a tt-fh")]'):
        link = result.xpath('.//a[contains(@class, "thumb")]')[0]
        url = urljoin(base_url, link.attrib.get('href'))
        title_links = result.xpath('.//span[@class="details"]//a[contains(@class, "t")]')  # noqa
        title = ''.join(title_links[0].xpath('.//text()'))
        img_src = link.xpath('.//img')[0].attrib['src']
        results.append({'url': url,
                        'title': title,
                        'img_src': img_src,
                        'template': 'images.html'})
    return results

########NEW FILE########
__FILENAME__ = duckduckgo
from urllib import urlencode
from lxml.html import fromstring
from searx.utils import html_to_text

url = 'https://duckduckgo.com/html?{query}&s={offset}'
locale = 'us-en'


def request(query, params):
    offset = (params['pageno'] - 1) * 30
    q = urlencode({'q': query,
                   'l': locale})
    params['url'] = url.format(query=q, offset=offset)
    return params


def response(resp):
    result_xpath = '//div[@class="results_links results_links_deep web-result"]'  # noqa
    url_xpath = './/a[@class="large"]/@href'
    title_xpath = './/a[@class="large"]//text()'
    content_xpath = './/div[@class="snippet"]//text()'
    results = []

    doc = fromstring(resp.text)

    for r in doc.xpath(result_xpath):
        try:
            res_url = r.xpath(url_xpath)[-1]
        except:
            continue
        if not res_url:
            continue
        title = html_to_text(''.join(r.xpath(title_xpath)))
        content = html_to_text(''.join(r.xpath(content_xpath)))
        results.append({'title': title,
                        'content': content,
                        'url': res_url})

    return results


#from json import loads
#search_url = url + 'd.js?{query}&p=1&s={offset}'
#
#paging = True
#
#
#def request(query, params):
#    offset = (params['pageno'] - 1) * 30
#    q = urlencode({'q': query,
#                   'l': locale})
#    params['url'] = search_url.format(query=q, offset=offset)
#    return params
#
#
#def response(resp):
#    results = []
#    search_res = loads(resp.text[resp.text.find('[{'):-2])[:-1]
#    for r in search_res:
#        if not r.get('t'):
#            continue
#        results.append({'title': r['t'],
#                       'content': html_to_text(r['a']),
#                       'url': r['u']})
#    return results

########NEW FILE########
__FILENAME__ = duckduckgo_definitions
import json
from urllib import urlencode

url = 'http://api.duckduckgo.com/?{query}&format=json&pretty=0&no_redirect=1'


def request(query, params):
    params['url'] = url.format(query=urlencode({'q': query}))
    return params


def response(resp):
    search_res = json.loads(resp.text)
    results = []
    if 'Definition' in search_res:
        if search_res.get('AbstractURL'):
            res = {'title': search_res.get('Heading', ''),
                   'content': search_res.get('Definition', ''),
                   'url': search_res.get('AbstractURL', ''),
                   'class': 'definition_result'}
            results.append(res)

    return results

########NEW FILE########
__FILENAME__ = dummy
def request(query, params):
    return params


def response(resp):
    return []

########NEW FILE########
__FILENAME__ = filecrop
from urllib import urlencode
from HTMLParser import HTMLParser

url = 'http://www.filecrop.com/'
search_url = url + '/search.php?{query}&size_i=0&size_f=100000000&engine_r=1&engine_d=1&engine_e=1&engine_4=1&engine_m=1&pos={index}'  # noqa

paging = True


class FilecropResultParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.__start_processing = False

        self.results = []
        self.result = {}

        self.tr_counter = 0
        self.data_counter = 0

    def handle_starttag(self, tag, attrs):

        if tag == 'tr':
            if ('bgcolor', '#edeff5') in attrs or\
               ('bgcolor', '#ffffff') in attrs:
                self.__start_processing = True

        if not self.__start_processing:
            return

        if tag == 'label':
            self.result['title'] = [attr[1] for attr in attrs
                                    if attr[0] == 'title'][0]
        elif tag == 'a' and ('rel', 'nofollow') in attrs\
                and ('class', 'sourcelink') in attrs:
            if 'content' in self.result:
                self.result['content'] += [attr[1] for attr in attrs
                                           if attr[0] == 'title'][0]
            else:
                self.result['content'] = [attr[1] for attr in attrs
                                          if attr[0] == 'title'][0]
            self.result['content'] += ' '
        elif tag == 'a':
            self.result['url'] = url + [attr[1] for attr in attrs
                                        if attr[0] == 'href'][0]

    def handle_endtag(self, tag):
        if self.__start_processing is False:
            return

        if tag == 'tr':
            self.tr_counter += 1

            if self.tr_counter == 2:
                self.__start_processing = False
                self.tr_counter = 0
                self.data_counter = 0
                self.results.append(self.result)
                self.result = {}

    def handle_data(self, data):
        if not self.__start_processing:
            return

        if 'content' in self.result:
            self.result['content'] += data + ' '
        else:
            self.result['content'] = data + ' '

        self.data_counter += 1


def request(query, params):
    index = 1 + (params['pageno'] - 1) * 30
    params['url'] = search_url.format(query=urlencode({'w': query}),
                                      index=index)
    return params


def response(resp):
    parser = FilecropResultParser()
    parser.feed(resp.text)

    return parser.results

########NEW FILE########
__FILENAME__ = flickr
#!/usr/bin/env python

from urllib import urlencode
#from json import loads
from urlparse import urljoin
from lxml import html
from time import time

categories = ['images']

url = 'https://secure.flickr.com/'
search_url = url+'search/?{query}&page={page}'
results_xpath = '//div[@class="view display-item-tile"]/figure/div'

paging = True


def request(query, params):
    params['url'] = search_url.format(query=urlencode({'text': query}),
                                      page=params['pageno'])
    time_string = str(int(time())-3)
    params['cookies']['BX'] = '3oqjr6d9nmpgl&b=3&s=dh'
    params['cookies']['xb'] = '421409'
    params['cookies']['localization'] = 'en-us'
    params['cookies']['flrbp'] = time_string +\
        '-3a8cdb85a427a33efda421fbda347b2eaf765a54'
    params['cookies']['flrbs'] = time_string +\
        '-ed142ae8765ee62c9ec92a9513665e0ee1ba6776'
    params['cookies']['flrb'] = '9'
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)
    for result in dom.xpath(results_xpath):
        img = result.xpath('.//img')

        if not img:
            continue

        img = img[0]
        img_src = 'https:'+img.attrib.get('src')

        if not img_src:
            continue

        href = urljoin(url, result.xpath('.//a')[0].attrib.get('href'))
        title = img.attrib.get('alt', '')
        results.append({'url': href,
                        'title': title,
                        'img_src': img_src,
                        'template': 'images.html'})
    return results

########NEW FILE########
__FILENAME__ = github
from urllib import urlencode
from json import loads
from cgi import escape

categories = ['it']

search_url = 'https://api.github.com/search/repositories?sort=stars&order=desc&{query}'  # noqa

accept_header = 'application/vnd.github.preview.text-match+json'


def request(query, params):
    global search_url
    params['url'] = search_url.format(query=urlencode({'q': query}))
    params['headers']['Accept'] = accept_header
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)
    if not 'items' in search_res:
        return results
    for res in search_res['items']:
        title = res['name']
        url = res['html_url']
        if res['description']:
            content = escape(res['description'][:500])
        else:
            content = ''
        results.append({'url': url, 'title': title, 'content': content})
    return results

########NEW FILE########
__FILENAME__ = google
#!/usr/bin/env python

from urllib import urlencode
from json import loads

categories = ['general']

url = 'https://ajax.googleapis.com/'
search_url = url + 'ajax/services/search/web?v=2.0&start={offset}&rsz=large&safe=off&filter=off&{query}&hl={language}'  # noqa

paging = True
language_support = True


def request(query, params):
    offset = (params['pageno'] - 1) * 8
    language = 'en-US'
    if params['language'] != 'all':
        language = params['language'].replace('_', '-')
    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'q': query}),
                                      language=language)
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)

    if not search_res.get('responseData', {}).get('results'):
        return []

    for result in search_res['responseData']['results']:
        results.append({'url': result['unescapedUrl'],
                        'title': result['titleNoFormatting'],
                        'content': result['content']})
    return results

########NEW FILE########
__FILENAME__ = google_images
#!/usr/bin/env python

from urllib import urlencode
from json import loads

categories = ['images']

url = 'https://ajax.googleapis.com/'
search_url = url + 'ajax/services/search/images?v=1.0&start={offset}&rsz=large&safe=off&filter=off&{query}'  # noqa


def request(query, params):
    offset = (params['pageno'] - 1) * 8
    params['url'] = search_url.format(query=urlencode({'q': query}),
                                      offset=offset)
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)
    if not search_res.get('responseData'):
        return []
    if not search_res['responseData'].get('results'):
        return []
    for result in search_res['responseData']['results']:
        href = result['originalContextUrl']
        title = result['title']
        if not result['url']:
            continue
        results.append({'url': href,
                        'title': title,
                        'content': '',
                        'img_src': result['url'],
                        'template': 'images.html'})
    return results

########NEW FILE########
__FILENAME__ = google_news
#!/usr/bin/env python

from urllib import urlencode
from json import loads
from dateutil import parser

categories = ['news']

url = 'https://ajax.googleapis.com/'
search_url = url + 'ajax/services/search/news?v=2.0&start={offset}&rsz=large&safe=off&filter=off&{query}&hl={language}'  # noqa

paging = True
language_support = True


def request(query, params):
    offset = (params['pageno'] - 1) * 8
    language = 'en-US'
    if params['language'] != 'all':
        language = params['language'].replace('_', '-')
    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'q': query}),
                                      language=language)
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)

    if not search_res.get('responseData', {}).get('results'):
        return []

    for result in search_res['responseData']['results']:

# Mon, 10 Mar 2014 16:26:15 -0700
        publishedDate = parser.parse(result['publishedDate'])

        results.append({'url': result['unescapedUrl'],
                        'title': result['titleNoFormatting'],
                        'publishedDate': publishedDate,
                        'content': result['content']})
    return results

########NEW FILE########
__FILENAME__ = json_engine
from urllib import urlencode
from json import loads
from collections import Iterable

search_url = None
url_query = None
content_query = None
title_query = None
#suggestion_xpath = ''


def iterate(iterable):
    if type(iterable) == dict:
        it = iterable.iteritems()

    else:
        it = enumerate(iterable)
    for index, value in it:
        yield str(index), value


def is_iterable(obj):
    if type(obj) == str:
        return False
    if type(obj) == unicode:
        return False
    return isinstance(obj, Iterable)


def parse(query):
    q = []
    for part in query.split('/'):
        if part == '':
            continue
        else:
            q.append(part)
    return q


def do_query(data, q):
    ret = []
    if not q:
        return ret

    qkey = q[0]

    for key, value in iterate(data):

        if len(q) == 1:
            if key == qkey:
                ret.append(value)
            elif is_iterable(value):
                ret.extend(do_query(value, q))
        else:
            if not is_iterable(value):
                continue
            if key == qkey:
                ret.extend(do_query(value, q[1:]))
            else:
                ret.extend(do_query(value, q))
    return ret


def query(data, query_string):
    q = parse(query_string)

    return do_query(data, q)


def request(query, params):
    query = urlencode({'q': query})[2:]
    params['url'] = search_url.format(query=query)
    params['query'] = query
    return params


def response(resp):
    results = []

    json = loads(resp.text)

    urls = query(json, url_query)
    contents = query(json, content_query)
    titles = query(json, title_query)
    for url, title, content in zip(urls, titles, contents):
        results.append({'url': url, 'title': title, 'content': content})
    return results

########NEW FILE########
__FILENAME__ = mediawiki
from json import loads
from urllib import urlencode, quote

url = 'https://en.wikipedia.org/'

search_url = url + 'w/api.php?action=query&list=search&{query}&srprop=timestamp&format=json&sroffset={offset}'  # noqa

number_of_results = 10


def request(query, params):
    offset = (params['pageno'] - 1) * 10
    params['url'] = search_url.format(query=urlencode({'srsearch': query}),
                                      offset=offset)
    return params


def response(resp):
    search_results = loads(resp.text)
    res = search_results.get('query', {}).get('search', [])
    return [{'url': url + 'wiki/' + quote(result['title'].replace(' ', '_').encode('utf-8')),  # noqa
        'title': result['title']} for result in res[:int(number_of_results)]]

########NEW FILE########
__FILENAME__ = piratebay
from urlparse import urljoin
from cgi import escape
from urllib import quote
from lxml import html
from operator import itemgetter

categories = ['videos', 'music']

url = 'https://thepiratebay.se/'
search_url = url + 'search/{search_term}/{pageno}/99/{search_type}'
search_types = {'videos': '200',
                'music': '100',
                'files': '0'}

magnet_xpath = './/a[@title="Download this torrent using magnet"]'
content_xpath = './/font[@class="detDesc"]//text()'

paging = True


def request(query, params):
    search_type = search_types.get(params['category'], '200')
    params['url'] = search_url.format(search_term=quote(query),
                                      search_type=search_type,
                                      pageno=params['pageno'] - 1)
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)
    search_res = dom.xpath('//table[@id="searchResult"]//tr')

    if not search_res:
        return results

    for result in search_res[1:]:
        link = result.xpath('.//div[@class="detName"]//a')[0]
        href = urljoin(url, link.attrib.get('href'))
        title = ' '.join(link.xpath('.//text()'))
        content = escape(' '.join(result.xpath(content_xpath)))
        seed, leech = result.xpath('.//td[@align="right"]/text()')[:2]

        if seed.isdigit():
            seed = int(seed)
        else:
            seed = 0

        if leech.isdigit():
            leech = int(leech)
        else:
            leech = 0

        magnetlink = result.xpath(magnet_xpath)[0]
        results.append({'url': href,
                        'title': title,
                        'content': content,
                        'seed': seed,
                        'leech': leech,
                        'magnetlink': magnetlink.attrib['href'],
                        'template': 'torrent.html'})

    return sorted(results, key=itemgetter('seed'), reverse=True)

########NEW FILE########
__FILENAME__ = soundcloud
from json import loads
from urllib import urlencode

categories = ['music']

guest_client_id = 'b45b1aa10f1ac2941910a7f0d10f8e28'
url = 'https://api.soundcloud.com/'
search_url = url + 'search?{query}&facet=model&limit=20&offset={offset}&linked_partitioning=1&client_id='+guest_client_id  # noqa

paging = True


def request(query, params):
    offset = (params['pageno'] - 1) * 20
    params['url'] = search_url.format(query=urlencode({'q': query}),
                                      offset=offset)
    return params


def response(resp):
    global base_url
    results = []
    search_res = loads(resp.text)
    for result in search_res.get('collection', []):
        if result['kind'] in ('track', 'playlist'):
            title = result['title']
            content = result['description']
            results.append({'url': result['permalink_url'],
                            'title': title,
                            'content': content})
    return results

########NEW FILE########
__FILENAME__ = stackoverflow
from urlparse import urljoin
from cgi import escape
from urllib import urlencode
from lxml import html

categories = ['it']

url = 'http://stackoverflow.com/'
search_url = url+'search?{query}&page={pageno}'
result_xpath = './/div[@class="excerpt"]//text()'

paging = True


def request(query, params):
    params['url'] = search_url.format(query=urlencode({'q': query}),
                                      pageno=params['pageno'])
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)
    for result in dom.xpath('//div[@class="question-summary search-result"]'):
        link = result.xpath('.//div[@class="result-link"]//a')[0]
        href = urljoin(url, link.attrib.get('href'))
        title = escape(' '.join(link.xpath('.//text()')))
        content = escape(' '.join(result.xpath(result_xpath)))
        results.append({'url': href, 'title': title, 'content': content})
    return results

########NEW FILE########
__FILENAME__ = startpage
from urllib import urlencode
from lxml import html

base_url = None
search_url = None

# TODO paging
paging = False
# TODO complete list of country mapping
country_map = {'en_US': 'eng',
               'en_UK': 'uk',
               'nl_NL': 'ned'}


def request(query, params):
    query = urlencode({'q': query})[2:]
    params['url'] = search_url
    params['method'] = 'POST'
    params['data'] = {'query': query,
                      'startat': (params['pageno'] - 1) * 10}  # offset
    country = country_map.get(params['language'], 'eng')
    params['cookies']['preferences'] = \
        'lang_homepageEEEs/air/{country}/N1NsslEEE1N1Nfont_sizeEEEmediumN1Nrecent_results_filterEEE1N1Nlanguage_uiEEEenglishN1Ndisable_open_in_new_windowEEE0N1Ncolor_schemeEEEnewN1Nnum_of_resultsEEE10N1N'.format(country=country)  # noqa
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.content)
    # ads xpath //div[@id="results"]/div[@id="sponsored"]//div[@class="result"]
    # not ads: div[@class="result"] are the direct childs of div[@id="results"]
    for result in dom.xpath('//div[@class="result"]'):
        link = result.xpath('.//h3/a')[0]
        url = link.attrib.get('href')
        if url.startswith('http://www.google.')\
           or url.startswith('https://www.google.'):
            continue
        title = link.text_content()

        content = ''
        if result.xpath('./p[@class="desc"]'):
            content = result.xpath('./p[@class="desc"]')[0].text_content()

        results.append({'url': url, 'title': title, 'content': content})

    return results

########NEW FILE########
__FILENAME__ = twitter
from urlparse import urljoin
from urllib import urlencode
from lxml import html
from cgi import escape

categories = ['social media']

base_url = 'https://twitter.com/'
search_url = base_url+'search?'
title_xpath = './/span[@class="username js-action-profile-name"]//text()'
content_xpath = './/p[@class="js-tweet-text tweet-text"]//text()'


def request(query, params):
    global search_url
    params['url'] = search_url + urlencode({'q': query})
    return params


def response(resp):
    global base_url
    results = []
    dom = html.fromstring(resp.text)
    for tweet in dom.xpath('//li[@data-item-type="tweet"]'):
        link = tweet.xpath('.//small[@class="time"]//a')[0]
        url = urljoin(base_url, link.attrib.get('href'))
        title = ''.join(tweet.xpath(title_xpath))
        content = escape(''.join(tweet.xpath(content_xpath)))
        results.append({'url': url,
                        'title': title,
                        'content': content})
    return results

########NEW FILE########
__FILENAME__ = vimeo
from urllib import urlencode
from HTMLParser import HTMLParser
from lxml import html
from searx.engines.xpath import extract_text
from dateutil import parser

base_url = 'http://vimeo.com'
search_url = base_url + '/search?{query}'
url_xpath = None
content_xpath = None
title_xpath = None
results_xpath = ''
content_tpl = '<a href="{0}">  <img src="{2}"/> </a>'
publishedDate_xpath = './/p[@class="meta"]//attribute::datetime'

# the cookie set by vimeo contains all the following values,
# but only __utma seems to be requiered
cookie = {
    #'vuid':'918282893.1027205400'
    # 'ab_bs':'%7B%223%22%3A279%7D'
     '__utma': '00000000.000#0000000.0000000000.0000000000.0000000000.0'
    # '__utmb':'18302654.1.10.1388942090'
    #, '__utmc':'18302654'
    #, '__utmz':'18#302654.1388942090.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'  # noqa
    #, '__utml':'search'
}


def request(query, params):
    params['url'] = search_url.format(query=urlencode({'q': query}))
    params['cookies'] = cookie
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    p = HTMLParser()

    for result in dom.xpath(results_xpath):
        url = base_url + result.xpath(url_xpath)[0]
        title = p.unescape(extract_text(result.xpath(title_xpath)))
        thumbnail = extract_text(result.xpath(content_xpath)[0])
        publishedDate = parser.parse(extract_text(
            result.xpath(publishedDate_xpath)[0]))

        results.append({'url': url,
                        'title': title,
                        'content': content_tpl.format(url, title, thumbnail),
                        'template': 'videos.html',
                        'publishedDate': publishedDate,
                        'thumbnail': thumbnail})
    return results

########NEW FILE########
__FILENAME__ = wikipedia
from json import loads
from urllib import urlencode, quote

url = 'https://{language}.wikipedia.org/'

search_url = url + 'w/api.php?action=query&list=search&{query}&srprop=timestamp&format=json&sroffset={offset}'  # noqa

number_of_results = 10

language_support = True


def request(query, params):
    offset = (params['pageno'] - 1) * 10
    if params['language'] == 'all':
        language = 'en'
    else:
        language = params['language'].split('_')[0]
    params['language'] = language
    params['url'] = search_url.format(query=urlencode({'srsearch': query}),
                                      offset=offset,
                                      language=language)
    return params


def response(resp):
    search_results = loads(resp.text)
    res = search_results.get('query', {}).get('search', [])
    return [{'url': url.format(language=resp.search_params['language']) + 'wiki/' + quote(result['title'].replace(' ', '_').encode('utf-8')),  # noqa
        'title': result['title']} for result in res[:int(number_of_results)]]

########NEW FILE########
__FILENAME__ = xpath
from lxml import html
from urllib import urlencode, unquote
from urlparse import urlparse, urljoin
from lxml.etree import _ElementStringResult, _ElementUnicodeResult
from searx.utils import html_to_text

search_url = None
url_xpath = None
content_xpath = None
title_xpath = None
suggestion_xpath = ''
results_xpath = ''


'''
if xpath_results is list, extract the text from each result and concat the list
if xpath_results is a xml element, extract all the text node from it
   ( text_content() method from lxml )
if xpath_results is a string element, then it's already done
'''


def extract_text(xpath_results):
    if type(xpath_results) == list:
        # it's list of result : concat everything using recursive call
        if not xpath_results:
            raise Exception('Empty url resultset')
        result = ''
        for e in xpath_results:
            result = result + extract_text(e)
        return result
    elif type(xpath_results) in [_ElementStringResult, _ElementUnicodeResult]:
        # it's a string
        return ''.join(xpath_results)
    else:
        # it's a element
        return html_to_text(xpath_results.text_content())


def extract_url(xpath_results, search_url):
    url = extract_text(xpath_results)

    if url.startswith('//'):
        # add http or https to this kind of url //example.com/
        parsed_search_url = urlparse(search_url)
        url = parsed_search_url.scheme+url
    elif url.startswith('/'):
        # fix relative url to the search engine
        url = urljoin(search_url, url)

    # normalize url
    url = normalize_url(url)

    return url


def normalize_url(url):
    parsed_url = urlparse(url)

    # add a / at this end of the url if there is no path
    if not parsed_url.netloc:
        raise Exception('Cannot parse url')
    if not parsed_url.path:
        url += '/'

    # FIXME : hack for yahoo
    if parsed_url.hostname == 'search.yahoo.com'\
       and parsed_url.path.startswith('/r'):
        p = parsed_url.path
        mark = p.find('/**')
        if mark != -1:
            return unquote(p[mark+3:]).decode('utf-8')

    return url


def request(query, params):
    query = urlencode({'q': query})[2:]
    params['url'] = search_url.format(query=query)
    params['query'] = query
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)
    if results_xpath:
        for result in dom.xpath(results_xpath):
            url = extract_url(result.xpath(url_xpath), search_url)
            title = extract_text(result.xpath(title_xpath)[0])
            content = extract_text(result.xpath(content_xpath)[0])
            results.append({'url': url, 'title': title, 'content': content})
    else:
        for url, title, content in zip(
            (extract_url(x, search_url) for
             x in dom.xpath(url_xpath)),
            map(extract_text, dom.xpath(title_xpath)),
            map(extract_text, dom.xpath(content_xpath))
        ):
            results.append({'url': url, 'title': title, 'content': content})

    if not suggestion_xpath:
        return results
    for suggestion in dom.xpath(suggestion_xpath):
        results.append({'suggestion': extract_text(suggestion)})
    return results

########NEW FILE########
__FILENAME__ = yacy
from json import loads
from urllib import urlencode

url = 'http://localhost:8090'
search_url = '/yacysearch.json?{query}&maximumRecords=10'


def request(query, params):
    params['url'] = url + search_url.format(query=urlencode({'query': query}))
    return params


def response(resp):
    raw_search_results = loads(resp.text)

    if not raw_search_results:
        return []

    search_results = raw_search_results.get('channels', {})[0].get('items', [])

    results = []

    for result in search_results:
        tmp_result = {}
        tmp_result['title'] = result['title']
        tmp_result['url'] = result['link']
        tmp_result['content'] = ''

        if result['description']:
            tmp_result['content'] += result['description'] + "<br/>"

        if result['pubDate']:
            tmp_result['content'] += result['pubDate'] + "<br/>"

        if result['size'] != '-1':
            tmp_result['content'] += result['sizename']

        results.append(tmp_result)

    return results

########NEW FILE########
__FILENAME__ = yahoo
#!/usr/bin/env python

from urllib import urlencode
from urlparse import unquote
from lxml import html
from searx.engines.xpath import extract_text, extract_url

categories = ['general']
search_url = 'http://search.yahoo.com/search?{query}&b={offset}'
results_xpath = '//div[@class="res"]'
url_xpath = './/h3/a/@href'
title_xpath = './/h3/a'
content_xpath = './/div[@class="abstr"]'
suggestion_xpath = '//div[@id="satat"]//a'

paging = True


def parse_url(url_string):
    endings = ['/RS', '/RK']
    endpositions = []
    start = url_string.find('http', url_string.find('/RU=')+1)
    for ending in endings:
        endpos = url_string.rfind(ending)
        if endpos > -1:
            endpositions.append(endpos)

    end = min(endpositions)
    return unquote(url_string[start:end])


def request(query, params):
    offset = (params['pageno'] - 1) * 10 + 1
    if params['language'] == 'all':
        language = 'en'
    else:
        language = params['language'].split('_')[0]
    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'p': query}))
    params['cookies']['sB'] = 'fl=1&vl=lang_{lang}&sh=1&rw=new&v=1'\
        .format(lang=language)
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in dom.xpath(results_xpath):
        try:
            url = parse_url(extract_url(result.xpath(url_xpath), search_url))
            title = extract_text(result.xpath(title_xpath)[0])
        except:
            continue
        content = extract_text(result.xpath(content_xpath)[0])
        results.append({'url': url, 'title': title, 'content': content})

    if not suggestion_xpath:
        return results

    for suggestion in dom.xpath(suggestion_xpath):
        results.append({'suggestion': extract_text(suggestion)})

    return results

########NEW FILE########
__FILENAME__ = yahoo_news
#!/usr/bin/env python

from urllib import urlencode
from lxml import html
from searx.engines.xpath import extract_text, extract_url
from searx.engines.yahoo import parse_url
from datetime import datetime, timedelta
import re
from dateutil import parser

categories = ['news']
search_url = 'http://news.search.yahoo.com/search?{query}&b={offset}'
results_xpath = '//div[@class="res"]'
url_xpath = './/h3/a/@href'
title_xpath = './/h3/a'
content_xpath = './/div[@class="abstr"]'
publishedDate_xpath = './/span[@class="timestamp"]'
suggestion_xpath = '//div[@id="satat"]//a'

paging = True


def request(query, params):
    offset = (params['pageno'] - 1) * 10 + 1
    if params['language'] == 'all':
        language = 'en'
    else:
        language = params['language'].split('_')[0]
    params['url'] = search_url.format(offset=offset,
                                      query=urlencode({'p': query}))
    params['cookies']['sB'] = 'fl=1&vl=lang_{lang}&sh=1&rw=new&v=1'\
        .format(lang=language)
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in dom.xpath(results_xpath):
        url = parse_url(extract_url(result.xpath(url_xpath), search_url))
        title = extract_text(result.xpath(title_xpath)[0])
        content = extract_text(result.xpath(content_xpath)[0])
        publishedDate = extract_text(result.xpath(publishedDate_xpath)[0])

        if re.match("^[0-9]+ minute(s|) ago$", publishedDate):
            publishedDate = datetime.now() - timedelta(minutes=int(re.match(r'\d+', publishedDate).group()))  # noqa
        else:
            if re.match("^[0-9]+ hour(s|), [0-9]+ minute(s|) ago$",
                        publishedDate):
                timeNumbers = re.findall(r'\d+', publishedDate)
                publishedDate = datetime.now()\
                    - timedelta(hours=int(timeNumbers[0]))\
                    - timedelta(minutes=int(timeNumbers[1]))
            else:
                publishedDate = parser.parse(publishedDate)

        if publishedDate.year == 1900:
            publishedDate = publishedDate.replace(year=datetime.now().year)

        results.append({'url': url,
                        'title': title,
                        'content': content,
                        'publishedDate': publishedDate})

    if not suggestion_xpath:
        return results

    for suggestion in dom.xpath(suggestion_xpath):
        results.append({'suggestion': extract_text(suggestion)})

    return results

########NEW FILE########
__FILENAME__ = youtube
from json import loads
from urllib import urlencode
from dateutil import parser

categories = ['videos']

search_url = ('https://gdata.youtube.com/feeds/api/videos'
              '?alt=json&{query}&start-index={index}&max-results=25')  # noqa

paging = True


def request(query, params):
    index = (params['pageno'] - 1) * 25 + 1
    params['url'] = search_url.format(query=urlencode({'q': query}),
                                      index=index)
    return params


def response(resp):
    results = []
    search_results = loads(resp.text)
    if not 'feed' in search_results:
        return results
    feed = search_results['feed']

    for result in feed['entry']:
        url = [x['href'] for x in result['link'] if x['type'] == 'text/html']
        if not url:
            return
        # remove tracking
        url = url[0].replace('feature=youtube_gdata', '')
        if url.endswith('&'):
            url = url[:-1]
        title = result['title']['$t']
        content = ''
        thumbnail = ''

#"2013-12-31T15:22:51.000Z"
        pubdate = result['published']['$t']
        publishedDate = parser.parse(pubdate)

        if result['media$group']['media$thumbnail']:
            thumbnail = result['media$group']['media$thumbnail'][0]['url']
            content += '<a href="{0}" title="{0}" ><img src="{1}" /></a>'.format(url, thumbnail)  # noqa

        if content:
            content += '<br />' + result['content']['$t']
        else:
            content = result['content']['$t']

        results.append({'url': url,
                        'title': title,
                        'content': content,
                        'template': 'videos.html',
                        'publishedDate': publishedDate,
                        'thumbnail': thumbnail})

    return results

########NEW FILE########
__FILENAME__ = languages
language_codes = (
    ("ar_XA", "Arabic", "Arabia"),
    ("bg_BG", "Bulgarian", "Bulgaria"),
    ("cs_CZ", "Czech", "Czech Republic"),
    ("de_DE", "German", "Germany"),
    ("da_DK", "Danish", "Denmark"),
    ("de_AT", "German", "Austria"),
    ("de_CH", "German", "Switzerland"),
    ("el_GR", "Greek", "Greece"),
    ("en_AU", "English", "Australia"),
    ("en_CA", "English", "Canada"),
    ("en_GB", "English", "United Kingdom"),
    ("en_ID", "English", "Indonesia"),
    ("en_IE", "English", "Ireland"),
    ("en_IN", "English", "India"),
    ("en_MY", "English", "Malaysia"),
    ("en_NZ", "English", "New Zealand"),
    ("en_PH", "English", "Philippines"),
    ("en_SG", "English", "Singapore"),
    ("en_US", "English", "United States"),
    ("en_XA", "English", "Arabia"),
    ("en_ZA", "English", "South Africa"),
    ("es_AR", "Spanish", "Argentina"),
    ("es_CL", "Spanish", "Chile"),
    ("es_ES", "Spanish", "Spain"),
    ("es_MX", "Spanish", "Mexico"),
    ("es_US", "Spanish", "United States"),
    ("es_XL", "Spanish", "Latin America"),
    ("et_EE", "Estonian", "Estonia"),
    ("fi_FI", "Finnish", "Finland"),
    ("fr_BE", "French", "Belgium"),
    ("fr_CA", "French", "Canada"),
    ("fr_CH", "French", "Switzerland"),
    ("fr_FR", "French", "France"),
    ("he_IL", "Hebrew", "Israel"),
    ("hr_HR", "Croatian", "Croatia"),
    ("hu_HU", "Hungarian", "Hungary"),
    ("it_IT", "Italian", "Italy"),
    ("ja_JP", "Japanese", "Japan"),
    ("ko_KR", "Korean", "Korea"),
    ("lt_LT", "Lithuanian", "Lithuania"),
    ("lv_LV", "Latvian", "Latvia"),
    ("nb_NO", "Norwegian", "Norway"),
    ("nl_BE", "Dutch", "Belgium"),
    ("nl_NL", "Dutch", "Netherlands"),
    ("pl_PL", "Polish", "Poland"),
    ("pt_BR", "Portuguese", "Brazil"),
    ("pt_PT", "Portuguese", "Portugal"),
    ("ro_RO", "Romanian", "Romania"),
    ("ru_RU", "Russian", "Russia"),
    ("sk_SK", "Slovak", "Slovak Republic"),
    ("sl_SL", "Slovenian", "Slovenia"),
    ("sv_SE", "Swedish", "Sweden"),
    ("th_TH", "Thai", "Thailand"),
    ("tr_TR", "Turkish", "Turkey"),
    ("uk_UA", "Ukrainian", "Ukraine"),
    ("zh_CN", "Chinese", "China"),
    ("zh_HK", "Chinese", "Hong Kong SAR"),
    ("zh_TW", "Chinese", "Taiwan"))

########NEW FILE########
__FILENAME__ = search
from searx.engines import (
    categories, engines, engine_shortcuts
)
from searx.languages import language_codes


class Search(object):

    """Search information container"""

    def __init__(self, request):
        super(Search, self).__init__()
        self.query = None
        self.engines = []
        self.categories = []
        self.paging = False
        self.pageno = 1
        self.lang = 'all'
        if request.cookies.get('blocked_engines'):
            self.blocked_engines = request.cookies['blocked_engines'].split(',')  # noqa
        else:
            self.blocked_engines = []
        self.results = []
        self.suggestions = []
        self.request_data = {}

        if request.cookies.get('language')\
           and request.cookies['language'] in (x[0] for x in language_codes):
            self.lang = request.cookies['language']

        if request.method == 'POST':
            self.request_data = request.form
        else:
            self.request_data = request.args

        # TODO better exceptions
        if not self.request_data.get('q'):
            raise Exception('noquery')

        self.query = self.request_data['q']

        pageno_param = self.request_data.get('pageno', '1')
        if not pageno_param.isdigit() or int(pageno_param) < 1:
            raise Exception('wrong pagenumber')

        self.pageno = int(pageno_param)

        self.parse_query()

        self.categories = []

        if self.engines:
            self.categories = list(set(engine['category']
                                       for engine in self.engines))
        else:
            for pd_name, pd in self.request_data.items():
                if pd_name.startswith('category_'):
                    category = pd_name[9:]
                    if not category in categories:
                        continue
                    self.categories.append(category)
            if not self.categories:
                cookie_categories = request.cookies.get('categories', '')
                cookie_categories = cookie_categories.split(',')
                for ccateg in cookie_categories:
                    if ccateg in categories:
                        self.categories.append(ccateg)
            if not self.categories:
                self.categories = ['general']

            for categ in self.categories:
                self.engines.extend({'category': categ,
                                     'name': x.name}
                                    for x in categories[categ]
                                    if not x.name in self.blocked_engines)

    def parse_query(self):
        query_parts = self.query.split()
        modified = False
        if query_parts[0].startswith(':'):
            lang = query_parts[0][1:].lower()

            for lc in language_codes:
                lang_id, lang_name, country = map(str.lower, lc)
                if lang == lang_id\
                   or lang_id.startswith(lang)\
                   or lang == lang_name\
                   or lang == country:
                    self.lang = lang
                    modified = True
                    break

        elif query_parts[0].startswith('!'):
            prefix = query_parts[0][1:].replace('_', ' ')

            if prefix in engine_shortcuts\
               and not engine_shortcuts[prefix] in self.blocked_engines:
                modified = True
                self.engines.append({'category': 'none',
                                     'name': engine_shortcuts[prefix]})
            elif prefix in engines\
                    and not prefix in self.blocked_engines:
                modified = True
                self.engines.append({'category': 'none',
                                    'name': prefix})
            elif prefix in categories:
                modified = True
                self.engines.extend({'category': prefix,
                                    'name': engine.name}
                                    for engine in categories[prefix]
                                    if not engine in self.blocked_engines)
        if modified:
            self.query = self.query.replace(query_parts[0], '', 1).strip()
            self.parse_query()

########NEW FILE########
__FILENAME__ = testing
# -*- coding: utf-8 -*-
"""Shared testing code."""

from plone.testing import Layer
from unittest2 import TestCase


import os
import subprocess


class SearxTestLayer:
    """Base layer for non-robot tests."""

    __name__ = u'SearxTestLayer'

    def setUp(cls):
        pass
    setUp = classmethod(setUp)

    def tearDown(cls):
        pass
    tearDown = classmethod(tearDown)

    def testSetUp(cls):
        pass
    testSetUp = classmethod(testSetUp)

    def testTearDown(cls):
        pass
    testTearDown = classmethod(testTearDown)


class SearxRobotLayer(Layer):
    """Searx Robot Test Layer"""

    def setUp(self):
        os.setpgrp()  # create new process group, become its leader

        # get program paths
        webapp = os.path.join(
            os.path.abspath(os.path.dirname(os.path.realpath(__file__))),
            'webapp.py'
        )
        exe = os.path.abspath(os.path.dirname(__file__) + '/../bin/py')

        # set robot settings path
        os.environ['SEARX_SETTINGS_PATH'] = os.path.abspath(
            os.path.dirname(__file__) + '/settings_robot.yml')

        # run the server
        self.server = subprocess.Popen(
            [exe, webapp],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

    def tearDown(self):
        # send TERM signal to all processes in my group, to stop subprocesses
        os.killpg(os.getpgid(self.server.pid), 15)

        # remove previously set environment variable
        del os.environ['SEARX_SETTINGS_PATH']


SEARXROBOTLAYER = SearxRobotLayer()


class SearxTestCase(TestCase):
    """Base test case for non-robot tests."""

    layer = SearxTestLayer

########NEW FILE########
__FILENAME__ = test_robot
# -*- coding: utf-8 -*-

import os
import unittest2 as unittest
from plone.testing import layered
from robotsuite import RobotTestSuite
from searx.testing import SEARXROBOTLAYER


def test_suite():
    suite = unittest.TestSuite()
    current_dir = os.path.abspath(os.path.dirname(__file__))
    robot_dir = os.path.join(current_dir, 'robot')
    tests = [
        os.path.join('robot', f) for f in
        os.listdir(robot_dir) if f.endswith('.robot') and
        f.startswith('test_')
    ]
    for test in tests:
        suite.addTests([
            layered(RobotTestSuite(test), layer=SEARXROBOTLAYER),
        ])
    return suite

########NEW FILE########
__FILENAME__ = test_webapp
# -*- coding: utf-8 -*-

import json
from urlparse import ParseResult
from mock import patch
from searx import webapp
from searx.testing import SearxTestCase


class ViewsTestCase(SearxTestCase):

    def setUp(self):
        webapp.app.config['TESTING'] = True  # to get better error messages
        self.app = webapp.app.test_client()

        # set some defaults
        self.test_results = [
            {
                'content': 'first test content',
                'title': 'First Test',
                'url': 'http://first.test.xyz',
                'engines': ['youtube', 'startpage'],
                'engine': 'startpage',
                'parsed_url': ParseResult(scheme='http', netloc='first.test.xyz', path='/', params='', query='', fragment=''),  # noqa
            }, {
                'content': 'second test content',
                'title': 'Second Test',
                'url': 'http://second.test.xyz',
                'engines': ['youtube', 'startpage'],
                'engine': 'youtube',
                'parsed_url': ParseResult(scheme='http', netloc='second.test.xyz', path='/', params='', query='', fragment=''),  # noqa
            },
        ]

        self.maxDiff = None  # to see full diffs

    def test_index_empty(self):
        result = self.app.post('/')
        self.assertEqual(result.status_code, 200)
        self.assertIn('<div class="title"><h1>searx</h1></div>', result.data)

    @patch('searx.webapp.do_search')
    def test_index_html(self, search):
        search.return_value = (
            self.test_results,
            set()
        )
        result = self.app.post('/', data={'q': 'test'})
        self.assertIn(
            '<h3 class="result_title"><a href="http://first.test.xyz">First <span class="highlight">Test</span></a></h3>',  # noqa
            result.data
        )
        self.assertIn(
            '<p class="content">first <span class="highlight">test</span> content<br /></p>',  # noqa
            result.data
        )

    @patch('searx.webapp.do_search')
    def test_index_json(self, search):
        search.return_value = (
            self.test_results,
            set()
        )
        result = self.app.post('/', data={'q': 'test', 'format': 'json'})

        result_dict = json.loads(result.data)

        self.assertEqual('test', result_dict['query'])
        self.assertEqual(
            result_dict['results'][0]['content'], 'first test content')
        self.assertEqual(
            result_dict['results'][0]['url'], 'http://first.test.xyz')

    @patch('searx.webapp.do_search')
    def test_index_csv(self, search):
        search.return_value = (
            self.test_results,
            set()
        )
        result = self.app.post('/', data={'q': 'test', 'format': 'csv'})

        self.assertEqual(
            'title,url,content,host,engine,score\r\n'
            'First Test,http://first.test.xyz,first test content,first.test.xyz,startpage,\r\n'  # noqa
            'Second Test,http://second.test.xyz,second test content,second.test.xyz,youtube,\r\n',  # noqa
            result.data
        )

    @patch('searx.webapp.do_search')
    def test_index_rss(self, search):
        search.return_value = (
            self.test_results,
            set()
        )
        result = self.app.post('/', data={'q': 'test', 'format': 'rss'})

        self.assertIn(
            '<description>Search results for "test" - searx</description>',
            result.data
        )

        self.assertIn(
            '<opensearch:totalResults>2</opensearch:totalResults>',
            result.data
        )

        self.assertIn(
            '<title>First Test</title>',
            result.data
        )

        self.assertIn(
            '<link>http://first.test.xyz</link>',
            result.data
        )

        self.assertIn(
            '<description>first test content</description>',
            result.data
        )

    def test_about(self):
        result = self.app.get('/about')
        self.assertEqual(result.status_code, 200)
        self.assertIn('<h1>About <a href="/">searx</a></h1>', result.data)

    def test_preferences(self):
        result = self.app.get('/preferences')
        self.assertEqual(result.status_code, 200)
        self.assertIn(
            '<form method="post" action="/preferences" id="search_form">',
            result.data
        )
        self.assertIn(
            '<legend>Default categories</legend>',
            result.data
        )
        self.assertIn(
            '<legend>Interface language</legend>',
            result.data
        )

    def test_stats(self):
        result = self.app.get('/stats')
        self.assertEqual(result.status_code, 200)
        self.assertIn('<h2>Engine stats</h2>', result.data)

    def test_robots_txt(self):
        result = self.app.get('/robots.txt')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Allow: /', result.data)

    def test_opensearch_xml(self):
        result = self.app.get('/opensearch.xml')
        self.assertEqual(result.status_code, 200)
        self.assertIn('<Description>Search searx</Description>', result.data)

    def test_favicon(self):
        result = self.app.get('/favicon.ico')
        self.assertEqual(result.status_code, 200)

########NEW FILE########
__FILENAME__ = utils
from HTMLParser import HTMLParser
#import htmlentitydefs
import csv
from codecs import getincrementalencoder
import cStringIO
import re
from random import choice

ua_versions = ('26.0', '27.0', '28.0')
ua_os = ('Windows NT 6.3; WOW64',
         'X11; Linux x86_64',
         'X11; Linux x86')
ua = "Mozilla/5.0 ({os}) Gecko/20100101 Firefox/{version}"


def gen_useragent():
    # TODO
    return ua.format(os=choice(ua_os), version=choice(ua_versions))


def highlight_content(content, query):

    if not content:
        return None
    # ignoring html contents
    # TODO better html content detection
    if content.find('<') != -1:
        return content

    query = query.decode('utf-8')
    if content.lower().find(query.lower()) > -1:
        query_regex = u'({0})'.format(re.escape(query))
        content = re.sub(query_regex, '<span class="highlight">\\1</span>',
                         content, flags=re.I | re.U)
    else:
        regex_parts = []
        for chunk in query.split():
            if len(chunk) == 1:
                regex_parts.append(u'\W+{0}\W+'.format(re.escape(chunk)))
            else:
                regex_parts.append(u'{0}'.format(re.escape(chunk)))
        query_regex = u'({0})'.format('|'.join(regex_parts))
        content = re.sub(query_regex, '<span class="highlight">\\1</span>',
                         content, flags=re.I | re.U)

    return content


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        if number[0] in (u'x', u'X'):
            codepoint = int(number[1:], 16)
        else:
            codepoint = int(number)
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        #codepoint = htmlentitydefs.name2codepoint[name]
        #self.result.append(unichr(codepoint))
        self.result.append(name)

    def get_text(self):
        return u''.join(self.result)


def html_to_text(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = getincrementalencoder(encoding)()

    def writerow(self, row):
        unicode_row = []
        for col in row:
            if type(col) == str or type(col) == unicode:
                unicode_row.append(col.encode('utf-8').strip())
            else:
                unicode_row.append(col)
        self.writer.writerow(unicode_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

########NEW FILE########
__FILENAME__ = webapp
#!/usr/bin/env python

'''
searx is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

searx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with searx. If not, see < http://www.gnu.org/licenses/ >.

(C) 2013- by Adam Tauber, <asciimoo@gmail.com>
'''

if __name__ == '__main__':
    from sys import path
    from os.path import realpath, dirname
    path.append(realpath(dirname(realpath(__file__))+'/../'))

import json
import cStringIO
import os

from datetime import datetime, timedelta
from itertools import chain
from flask import (
    Flask, request, render_template, url_for, Response, make_response,
    redirect, send_from_directory
)
from flask.ext.babel import Babel, gettext, format_date
from searx import settings, searx_dir
from searx.engines import (
    search as do_search, categories, engines, get_engines_stats,
    engine_shortcuts
)
from searx.utils import UnicodeWriter, highlight_content, html_to_text
from searx.languages import language_codes
from searx.search import Search
from searx.autocomplete import backends as autocomplete_backends


app = Flask(
    __name__,
    static_folder=os.path.join(searx_dir, 'static'),
    template_folder=os.path.join(searx_dir, 'templates')
)

app.secret_key = settings['server']['secret_key']

babel = Babel(app)

#TODO configurable via settings.yml
favicons = ['wikipedia', 'youtube', 'vimeo', 'soundcloud',
            'twitter', 'stackoverflow', 'github']

cookie_max_age = 60 * 60 * 24 * 365 * 23  # 23 years


@babel.localeselector
def get_locale():
    locale = request.accept_languages.best_match(settings['locales'].keys())

    if request.cookies.get('locale', '') in settings['locales']:
        locale = request.cookies.get('locale', '')

    if 'locale' in request.args\
       and request.args['locale'] in settings['locales']:
        locale = request.args['locale']

    if 'locale' in request.form\
       and request.form['locale'] in settings['locales']:
        locale = request.form['locale']

    return locale


def get_base_url():
    if settings['server']['base_url']:
        hostname = settings['server']['base_url']
    else:
        scheme = 'http'
        if request.is_secure:
            scheme = 'https'
        hostname = url_for('index', _external=True, _scheme=scheme)
    return hostname


def render(template_name, **kwargs):
    blocked_engines = request.cookies.get('blocked_engines', '').split(',')

    autocomplete = request.cookies.get('autocomplete')

    if autocomplete not in autocomplete_backends:
        autocomplete = None

    nonblocked_categories = (engines[e].categories
                             for e in engines
                             if e not in blocked_engines)

    nonblocked_categories = set(chain.from_iterable(nonblocked_categories))

    if not 'categories' in kwargs:
        kwargs['categories'] = ['general']
        kwargs['categories'].extend(x for x in
                                    sorted(categories.keys())
                                    if x != 'general'
                                    and x in nonblocked_categories)

    if not 'selected_categories' in kwargs:
        kwargs['selected_categories'] = []
        cookie_categories = request.cookies.get('categories', '').split(',')
        for ccateg in cookie_categories:
            if ccateg in categories:
                kwargs['selected_categories'].append(ccateg)
        if not kwargs['selected_categories']:
            kwargs['selected_categories'] = ['general']

    if not 'autocomplete' in kwargs:
        kwargs['autocomplete'] = autocomplete

    kwargs['method'] = request.cookies.get('method', 'POST')

    return render_template(template_name, **kwargs)


@app.route('/search', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def index():
    """Render index page.

    Supported outputs: html, json, csv, rss.
    """

    if not request.args and not request.form:
        return render(
            'index.html',
        )

    try:
        search = Search(request)
    except:
        return render(
            'index.html',
        )

    # TODO moar refactor - do_search integration into Search class
    search.results, search.suggestions = do_search(search.query,
                                                   request,
                                                   search.engines,
                                                   search.pageno,
                                                   search.lang)

    for result in search.results:
        if not search.paging and engines[result['engine']].paging:
            search.paging = True
        if search.request_data.get('format', 'html') == 'html':
            if 'content' in result:
                result['content'] = highlight_content(result['content'],
                                                      search.query.encode('utf-8'))  # noqa
            result['title'] = highlight_content(result['title'],
                                                search.query.encode('utf-8'))
        else:
            if 'content' in result:
                result['content'] = html_to_text(result['content']).strip()
            # removing html content and whitespace duplications
            result['title'] = ' '.join(html_to_text(result['title'])
                                       .strip().split())
        if len(result['url']) > 74:
            url_parts = result['url'][:35], result['url'][-35:]
            result['pretty_url'] = u'{0}[...]{1}'.format(*url_parts)
        else:
            result['pretty_url'] = result['url']

        for engine in result['engines']:
            if engine in favicons:
                result['favicon'] = engine

        # TODO, check if timezone is calculated right
        if 'publishedDate' in result:
            if result['publishedDate'].replace(tzinfo=None)\
               >= datetime.now() - timedelta(days=1):
                timedifference = datetime.now() - result['publishedDate']\
                    .replace(tzinfo=None)
                minutes = int((timedifference.seconds / 60) % 60)
                hours = int(timedifference.seconds / 60 / 60)
                if hours == 0:
                    result['publishedDate'] = gettext(u'{minutes} minute(s) ago').format(minutes=minutes)  # noqa
                else:
                    result['publishedDate'] = gettext(u'{hours} hour(s), {minutes} minute(s) ago').format(hours=hours, minutes=minutes)  # noqa
            else:
                result['pubdate'] = result['publishedDate']\
                    .strftime('%a, %d %b %Y %H:%M:%S %z')
                result['publishedDate'] = format_date(result['publishedDate'])

    if search.request_data.get('format') == 'json':
        return Response(json.dumps({'query': search.query,
                                    'results': search.results}),
                        mimetype='application/json')
    elif search.request_data.get('format') == 'csv':
        csv = UnicodeWriter(cStringIO.StringIO())
        keys = ('title', 'url', 'content', 'host', 'engine', 'score')
        if search.results:
            csv.writerow(keys)
            for row in search.results:
                row['host'] = row['parsed_url'].netloc
                csv.writerow([row.get(key, '') for key in keys])
            csv.stream.seek(0)
        response = Response(csv.stream.read(), mimetype='application/csv')
        cont_disp = 'attachment;Filename=searx_-_{0}.csv'.format(search.query)
        response.headers.add('Content-Disposition', cont_disp)
        return response
    elif search.request_data.get('format') == 'rss':
        response_rss = render(
            'opensearch_response_rss.xml',
            results=search.results,
            q=search.request_data['q'],
            number_of_results=len(search.results),
            base_url=get_base_url()
        )
        return Response(response_rss, mimetype='text/xml')

    return render(
        'results.html',
        results=search.results,
        q=search.request_data['q'],
        selected_categories=search.categories,
        paging=search.paging,
        pageno=search.pageno,
        base_url=get_base_url(),
        suggestions=search.suggestions
    )


@app.route('/about', methods=['GET'])
def about():
    """Render about page"""
    return render(
        'about.html',
    )


@app.route('/autocompleter', methods=['GET', 'POST'])
def autocompleter():
    """Return autocompleter results"""
    request_data = {}

    if request.method == 'POST':
        request_data = request.form
    else:
        request_data = request.args

    # TODO fix XSS-vulnerability
    query = request_data.get('q', '').encode('utf-8')

    if not query:
        return

    completer = autocomplete_backends.get(request.cookies.get('autocomplete'))

    if not completer:
        return

    results = completer(query)

    if request_data.get('format') == 'x-suggestions':
        return Response(json.dumps([query, results]),
                        mimetype='application/json')
    else:
        return Response(json.dumps(results),
                        mimetype='application/json')


@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Render preferences page.

    Settings that are going to be saved as cookies."""
    lang = None

    if request.cookies.get('language')\
       and request.cookies['language'] in (x[0] for x in language_codes):
        lang = request.cookies['language']

    blocked_engines = []

    if request.method == 'GET':
        blocked_engines = request.cookies.get('blocked_engines', '').split(',')
    else:
        selected_categories = []
        locale = None
        autocomplete = ''
        method = 'POST'
        for pd_name, pd in request.form.items():
            if pd_name.startswith('category_'):
                category = pd_name[9:]
                if not category in categories:
                    continue
                selected_categories.append(category)
            elif pd_name == 'locale' and pd in settings['locales']:
                locale = pd
            elif pd_name == 'autocomplete':
                autocomplete = pd
            elif pd_name == 'language' and (pd == 'all' or
                                            pd in (x[0] for
                                                   x in language_codes)):
                lang = pd
            elif pd_name == 'method':
                method = pd
            elif pd_name.startswith('engine_'):
                engine_name = pd_name.replace('engine_', '', 1)
                if engine_name in engines:
                    blocked_engines.append(engine_name)

        resp = make_response(redirect(url_for('index')))

        user_blocked_engines = request.cookies.get('blocked_engines', '').split(',')  # noqa

        if sorted(blocked_engines) != sorted(user_blocked_engines):
            resp.set_cookie(
                'blocked_engines', ','.join(blocked_engines),
                max_age=cookie_max_age
            )

        if locale:
            resp.set_cookie(
                'locale', locale,
                max_age=cookie_max_age
            )

        if lang:
            resp.set_cookie(
                'language', lang,
                max_age=cookie_max_age
            )

        if selected_categories:
            # cookie max age: 4 weeks
            resp.set_cookie(
                'categories', ','.join(selected_categories),
                max_age=cookie_max_age
            )

            resp.set_cookie(
                'autocomplete', autocomplete,
                max_age=cookie_max_age
            )

        resp.set_cookie('method', method, max_age=cookie_max_age)

        return resp
    return render('preferences.html',
                  locales=settings['locales'],
                  current_locale=get_locale(),
                  current_language=lang or 'all',
                  language_codes=language_codes,
                  categs=categories.items(),
                  blocked_engines=blocked_engines,
                  autocomplete_backends=autocomplete_backends,
                  shortcuts={y: x for x, y in engine_shortcuts.items()})


@app.route('/stats', methods=['GET'])
def stats():
    """Render engine statistics page."""
    global categories
    stats = get_engines_stats()
    return render(
        'stats.html',
        stats=stats,
    )


@app.route('/robots.txt', methods=['GET'])
def robots():
    return Response("""User-agent: *
Allow: /
Allow: /about
Disallow: /stats
Disallow: /preferences
""", mimetype='text/plain')


@app.route('/opensearch.xml', methods=['GET'])
def opensearch():
    method = 'post'
    # chrome/chromium only supports HTTP GET....
    if request.headers.get('User-Agent', '').lower().find('webkit') >= 0:
        method = 'get'

    ret = render('opensearch.xml',
                 opensearch_method=method,
                 host=get_base_url())

    resp = Response(response=ret,
                    status=200,
                    mimetype="application/xml")
    return resp


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img'),
                               'favicon.png',
                               mimetype='image/vnd.microsoft.icon')


def run():
    from gevent import monkey
    monkey.patch_all()

    app.run(
        debug=settings['server']['debug'],
        use_debugger=settings['server']['debug'],
        port=settings['server']['port']
    )


if __name__ == "__main__":
    run()

########NEW FILE########
