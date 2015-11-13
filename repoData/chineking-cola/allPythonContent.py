__FILENAME__ = coca
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-13

@author: Chine
'''

import argparse
import socket
import threading
import os
import tempfile
import shutil

from cola.core.logs import get_logger, LogRecordSocketReceiver
from cola.core.rpc import client_call, FileTransportClient, ColaRPCServer
from cola.core.utils import import_job, get_ip
from cola.core.zip import ZipHandler
from cola.core.config import main_conf

logger = get_logger(name='coca')
parser = argparse.ArgumentParser('Coca')
registered_func = {}

def _client_call(*args):
    try:
        return client_call(*args)
    except socket.error:
        logger.error('Cannot connect to cola master')

def register(func):
    func_name = func.__name__
    name = '-%s' % func_name.replace('_', '-').strip('-')
    help_ = func.__doc__.strip()
    
    registered_func[func_name] = func
    parser.add_argument(name, nargs='*', dest=func_name,
                        default=argparse.SUPPRESS, help=help_)
    
    def inner(master, *args, **kwargs):
        return func(master, *args, **kwargs)
    return inner

log_server = None
log_server_port = 9120
client = '%s:%s' % (get_ip(), log_server_port)
def start_log_server():
    global log_server
    global log_server_port
    
    if log_server is not None:
        return
    log_server = LogRecordSocketReceiver(logger=logger, host=get_ip(), 
                                         port=log_server_port)
    threading.Thread(target=log_server.serve_forever).start()
    
def stop_log_server():
    global log_server
    
    if log_server is None:
        return
    
    log_server.shutdown()
    log_server = None
    
rpc_server = None
rpc_server_thread = None
def start_rpc_server():
    global rpc_server
    global rpc_server_thread
    
    if rpc_server is not None and \
        rpc_server_thread is not None:
        return rpc_server_thread
    
    rpc_server = ColaRPCServer((get_ip(), main_conf.client.port))
    rpc_server.register_function(stop)
    
    thd = threading.Thread(target=rpc_server.serve_forever)
    thd.setDaemon(True)
    thd.start()
    rpc_server_thread = thd
    return rpc_server_thread

def stop_rpc_server():
    global rpc_server
    global rpc_server_thread
    
    if rpc_server is None:
        return
    
    rpc_server.shutdown()
    rpc_server = None
    rpc_server_thread = None
    
def stop():
    stop_log_server()
    stop_rpc_server()

@register
def stopAll(master):
    '''
    stop cola cluster
    '''
    
    logger.info('Stopping cola cluster.')
    _client_call(master, 'stop')
    logger.info('Cola cluster is shutting down, '
                'and it will take a few seconds to complete.')
    
@register
def runLocalJob(master, job_path):
    '''
    push local job to cola cluster and run
    '''
    
    if not os.path.exists(job_path):
        logger.error('Job path not exists!')
        return
    
    try:
        import_job(job_path)
    except (ImportError, AttributeError):
        logger.error('Job path is illegal!')
        return
    
    start_log_server()
    thread = start_rpc_server()
        
    logger.info('Pushing job to cola cluster...')
    dir_ = tempfile.mkdtemp()
    try:
        zip_filename = os.path.split(job_path)[1].replace(' ', '_') + '.zip'
        zip_file = os.path.join(dir_, zip_filename)
        
        ZipHandler.compress(zip_file, job_path, type_filters=("pyc", ))
        FileTransportClient(master, zip_file).send_file()
        
        logger.info('Push finished.')
    finally:
        shutil.rmtree(dir_)
    
    logger.info('Start to run job.')    
    _client_call(master, 'start_job', zip_filename, True, client)
    thread.join()
    
@register
def showRemoteJobs(master):
    '''
    show the jobs that exists in the cola server
    '''
    
    logger.info('Quering the cola cluster...')
    
    print 'Available jobs: '
    for dir_ in _client_call(master, 'list_job_dirs'):
        print dir_
    
@register
def runRemoteJob(master, job_dir_name):
    '''
    run the job that exists in the cola server
    '''
    
    logger.info('Checking if job dir name exists...')
    if job_dir_name not in _client_call(master, 'list_job_dirs'):
        logger.error('Remote job dir not exists!')
    else:
        logger.info('Start to run job.')
        
        start_log_server()
        thread = start_rpc_server()
        
        _client_call(master, 'start_job', job_dir_name, False, client)
        thread.join()
        
@register
def showRunningJobsNames(master):
    '''
    show the running jobs' names
    '''
    
    logger.info('Querying the cola cluster...')
    
    print 'Running jobs\' names: '
    for job_name in _client_call(master, 'list_jobs'):
        print job_name
        
@register
def stopRunningJobByName(master, job_name):
    '''
    stop running job by its name
    '''
    
    if job_name not in _client_call(master, 'list_jobs'):
        logger.error('The job with name(%s) not running in cola cluster' % job_name)
        logger.info('Please run command `python coca.py --showRunningJobsNames` to check job names.')
    else:
        logger.info('Trying to stop job with name(%s).' % job_name)
        
        _client_call(master, 'stop_job', job_name)
        
        logger.info('Job with name(%s) is shutting down, '
                    'and it will take a few seconds to complete.')
        
@register
def showVisitedPages(master):
    '''
    show all visited pages' size
    '''
    
    logger.info('Querying the cola cluster...')
    
    print 'All vistied page size\' size: %s' % _client_call(master, 'pages')
        
if __name__ == "__main__":
    parser.add_argument('-m', '--master', metavar='master watcher', nargs='?',
                        default=None, const=None,
                        help='master connected to(in the former of `ip:port` or `ip`)')
    args = parser.parse_args()
    
    master = args.master
    if master is None:
        connect_to_localhost = raw_input("Connect to localhost? (yes or no) ")
        conn = connect_to_localhost.lower().strip()
        if conn == 'yes' or conn == 'y':
            master = '%s:%s' % (get_ip(), main_conf.master.port)
        elif conn == 'no' or conn == 'n':
            master = raw_input("Please input the master(form: \"ip:port\" or \"ip\") ")
            if ':' not in master:
                master += ':%s' % main_conf.master.port
        else:
            logger.error('Input illegal!')
    else:
        if ':' not in master:
            master += ':%s' % main_conf.master.port
            
    if master is None:
        logger.error('Master cannot be null.')
    else:
        try:
            runned = False
            
            for name, func in registered_func.iteritems():
                if hasattr(args, name):
                    runned = True
                    params = tuple(getattr(args, name))
                    func(master, *params)
                    
            if not runned:
                logger.info('Nothing to run!')
                    
        except KeyboardInterrupt:
            logger.error('interuptted')
            stop()
        except Exception, e:
            logger.exception(e)
            stop()
########NEW FILE########
__FILENAME__ = start_master
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-6

@author: Chine
'''

import subprocess
import os

from cola.core.utils import root_dir, get_ip
from cola.core.config import main_conf

def start_master(ip=None, data_path=None, force=False):
    path = os.path.join(root_dir(), 'cola', 'master', 'watcher.py')
    
    ip_str = ip if ip is not None else get_ip()
    print 'Start master at %s:%s' % (ip_str, main_conf.master.port)
    print 'Master will run in background. Please do not shut down the terminal.'
    
    cmds = ['python', path]
    if ip is not None:
        cmds.extend(['-i', ip])
    if data_path is not None:
        cmds.extend(['-d', data_path])
    if force is True:
        cmds.append('-f')
    subprocess.Popen(cmds)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Cola master')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-i', '--ip', metavar='IP address', nargs='?',
                        default=None, const=None, 
                        help='IP Address to start')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()
    
    start_master(args.ip, args.data, args.force)
########NEW FILE########
__FILENAME__ = start_worker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-7

@author: Chine
'''

import subprocess
import os

from cola.core.utils import root_dir, get_ip
from cola.core.config import main_conf

def start_worker(master, data_path=None, force=False):
    path = os.path.join(root_dir(), 'cola', 'worker', 'watcher.py')
    
    print 'Start worker at %s:%s' % (get_ip(), main_conf.worker.port)
    print 'Worker will run in background. Please do not shut down the terminal.'
    
    cmds = ['python', path, '-m', master]
    if data_path is not None:
        cmds.extend(['-d', data_path])
    if force is True:
        cmds.append('-f')
    subprocess.Popen(cmds)
    
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Cola worker')
    parser.add_argument('-m', '--master', metavar='master watcher', nargs='?',
                        default=None, const=None,
                        help='master connected to(in the former of `ip:port` or `ip`)')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()
    
    master = args.master
    if master is None:
        connect_to_localhost = raw_input("Connect to localhost? (yes or no) ")
        conn = connect_to_localhost.lower().strip()
        if conn == 'yes' or conn == 'y':
            master = '%s:%s' % (get_ip(), main_conf.master.port)
        elif conn == 'no' or conn == 'n':
            master = raw_input("Please input the master(form: \"ip:port\" or \"ip\") ")
            if ':' not in master:
                master += ':%s' % main_conf.master.port
        else:
            print 'Input illegal!'
    else:
        if ':' not in master:
            master += ':%s' % main_conf.master.port
    
    if master is not None: 
        start_worker(master, data_path=args.data, force=args.force)
########NEW FILE########
__FILENAME__ = hashtype
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Base class from which hash types can be created.

Modified from part of python-hashes by sangelone.
"""

default_hashbits = 96

class HashType(object):
    def __init__(self, value='', hashbits=default_hashbits, hash_=None):
        "Relies on create_hash() provided by subclass"
        self.hashbits = hashbits
        if hash_:
            self.hash = hash_
        else:
            self.create_hash(value)

    def __trunc__(self):
        return self.hash

    def __str__(self):
        return str(self.hash)
    
    def __long__(self):
        return long(self.hash)

    def __float__(self):
        return float(self.hash)
        
    def __cmp__(self, other):
        if self.hash < long(other): return -1
        if self.hash > long(other): return 1
        return 0
    
    def hex(self):
        return hex(self.hash)

    def hamming_distance(self, other_hash):
        x = (self.hash ^ other_hash.hash) & ((1 << self.hashbits) - 1)
        tot = 0
        while x:
            tot += 1
            x &= x-1
        return tot

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-16

@author: Chine
'''

import os

from cola.core.errors import DependencyNotInstalledError

try:
    import yaml
except ImportError:
    raise DependencyNotInstalledError('pyyaml')

class PropertyObject(dict):
    def __init__(self, d):
        super(PropertyObject, self).__init__()
        self._update(d)
        
    def _update(self, d):
        for k, v in d.iteritems():
            if not k.startswith('_'):
                self[k] = v
                
                if isinstance(v, dict):
                    setattr(self, k, PropertyObject(v))
                elif isinstance(v, list):
                    setattr(self, k, [PropertyObject(itm) for itm in v])
                else:
                    setattr(self, k, v)
                    
    def update(self, config=None, **kwargs):
        self._update(kwargs)
        if config is not None:
            if isinstance(config, dict):
                self._update(config)
            else:
                self._update(config.conf)

class Config(object):
    def __init__(self, yaml_file):
        if isinstance(yaml_file, str):
            f = open(yaml_file)
        else:
            f = yaml_file
        try:
            self.conf = PropertyObject(yaml.load(f))
        finally:
            f.close()
            
        for k, v in self.conf.iteritems():
            if not k.startswith('_'):
                if isinstance(v, dict):
                    v = PropertyObject(v)
                setattr(self, k, v)
    
    def __getitem__(self, name):
        return getattr(self, name)
    
conf_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'conf')
main_conf = Config(os.path.join(conf_dir, 'main.yaml'))
########NEW FILE########
__FILENAME__ = dedup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-8-29

@author: Chine
'''

from cola.core.bloomfilter import FileBloomFilter

class Deduper(object):
    def exist(self, key):
        raise NotImplementedError
    
class FileBloomFilterDeduper(Deduper):
    def __init__(self, sync_file, capacity):
        self.filter = FileBloomFilter(sync_file, capacity)
        
    def exist(self, key):
        return self.filter.verify(key)
    
    def __del__(self):
        try:
            self.filter.sync()
        finally:
            self.filter.close()
########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-17

@author: Chine
'''

class DependencyNotInstalledError(Exception):
    def __init__(self, dep):
        self.dep = dep
        
    def __str__(self):
        return 'Error because lacking of dependency: %s' % self.dep
    
class ConfigurationError(Exception): pass

class LoginFailure(Exception): pass
########NEW FILE########
__FILENAME__ = preprocess
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-16

@author: Chine
'''

import re

from cola.core.logs import get_logger
from cola.core.utils import beautiful_soup

from cola.core.extractor.utils import absolute_url

__all__ = ['PreProcessor']

class Replacement(object):
    def __init__(self, desc, regex, replacement):
        self.desc = desc
        self.regex = regex
        self.replacement = replacement
    
    def apply(self, content):
        return self.regex.sub(self.replacement, content)
    
# a bunch of regexes to hack around lousy html
dodgy_regexes = (
    Replacement('javascript',
        regex=re.compile('<script.*?</script[^>]*>', re.DOTALL | re.IGNORECASE),
        replacement=''),

    Replacement('double double-quoted attributes',
        regex=re.compile('(="[^"]+")"+'),
        replacement='\\1'),

    Replacement('unclosed tags',
        regex = re.compile('(<[a-zA-Z]+[^>]*)(<[a-zA-Z]+[^<>]*>)'),
        replacement='\\1>\\2'),

    Replacement('unclosed (numerical) attribute values',
        regex = re.compile('(<[^>]*[a-zA-Z]+\s*=\s*"[0-9]+)( [a-zA-Z]+="\w+"|/?>)'),
        replacement='\\1"\\2'),
                 
    Replacement('comment', regex=re.compile(r'<!--[^-]+-->', re.DOTALL),
        replacement=''),
    )

# strip out a set of nuisance html attributes that can mess up rendering in RSS feeds
bad_attrs = ['width','height','style','[-a-z]*color','background[-a-z]*']
single_quoted = "'[^']+'"
double_quoted = '"[^"]+"'
non_space = '[^ "\'>]+'
htmlstrip = re.compile("<" # open
    "([^>]+) " # prefix
    "(?:%s) *" % ('|'.join(bad_attrs),) + # undesirable attributes
    '= *(?:%s|%s|%s)' % (non_space, single_quoted, double_quoted) + # value
    "([^>]*)"  # postfix
    ">"        # end
, re.I)

class PreProcessor(object):
    
    def __init__(self, html, base_url=None, logger=None):
        self.logger = logger
        if logger is None:
            self.logger = get_logger(name='cola_extractor')
        self.html = html
        self.base_url = base_url
        
    def _remove_crufy_html(self, html):
        for replacement in dodgy_regexes:
            html = replacement.apply(html)
        return html
            
    def _fix_absolute_links(self, base_url):
        for link in self.soup.find_all('a', href=True):
            link['href'] = absolute_url(link['href'], base_url)
    
    def _fix_absolute_images(self, base_url):
        for image in self.soup.find_all('img', src=True):
            image['src'] = absolute_url(image['src'], base_url)
            
    def _fix_references(self, base_url):
        self._fix_absolute_links(base_url)
        self._fix_absolute_images(base_url)
        
    def _normalize_space(self, s):
        return ' '.join(s.split())
    
    def get_title(self, soup):
        if soup.head is None or soup.head.title is None:
            title = ''
        else:
            title = soup.head.title.text
            title = self._normalize_space(title)
        return title
    
    def _clean_attributes(self, html):
        while htmlstrip.search(html):
            html = htmlstrip.sub('<\\1\\2>', html)
        return html
    
    def get_body(self, soup):
        for elem in soup.find_all(['script', 'link', 'style']):
            elem.extract()
        raw_html = unicode(soup.body or soup)
        cleaned = self._clean_attributes(raw_html)
        return beautiful_soup(cleaned)
    
    def process(self, base_url=None):
        self.html = self._remove_crufy_html(self.html)
        
        self.soup = beautiful_soup(self.html, self.logger)
        
        base_url = self.base_url or base_url
        if base_url is not None:
            self._fix_references(base_url)
            
        title = self.get_title(self.soup)
        body = self.get_body(self.soup)
        
        return title, body
########NEW FILE########
__FILENAME__ = readability
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-7-15

@author: Chine
'''

import re

from cola.core.logs import get_logger
from cola.core.errors import DependencyNotInstalledError
from cola.core.utils import beautiful_soup

try:
    from bs4 import NavigableString
except ImportError:
    raise DependencyNotInstalledError("BeautifulSoup4")

from cola.core.extractor.preprocess import PreProcessor

__all__ = ['Extractor']

REGEXES = { 
    'unlikelyCandidatesRe': re.compile('combx|comment|disqus|foot|header|menu|meta|nav|rss|shoutbox|sidebar|aside|sponsor',re.I),
    'okMaybeItsACandidateRe': re.compile('and|article|body|column|main',re.I),
    'positiveRe': re.compile('article|body|content|entry|hentry|page|pagination|post|text',re.I),
    'negativeRe': re.compile('combx|comment|contact|foot|footer|footnote|link|media|meta|promo|related|scroll|shoutbox|sponsor|tags|widget',re.I),
    'divToPElementsRe': re.compile('<(a|blockquote|dl|div|img|ol|p|pre|table|ul)',re.I),
    'replaceBrsRe': re.compile('(<br[^>]*>[ \n\r\t]*){2,}',re.I),
    'replaceFontsRe': re.compile('<(\/?)font[^>]*>',re.I),
    'trimRe': re.compile('^\s+|\s+$/'),
    'normalizeRe': re.compile('\s{2,}/'),
    'killBreaksRe': re.compile('(<br\s*\/?>(\s|&nbsp;?)*){1,}/'),
    'videoRe': re.compile('http:\/\/(www\.)?(youtube|vimeo)\.com', re.I),
}

class HashableElement():
    def __init__(self, node):
        self.node = node
        self._path = None

    def _get_path(self):
        if self._path is None:
            reverse_path = []
            node = self.node
            while node:
                node_id = (node.name, tuple(node.attrs), node.string)
                reverse_path.append(node_id)
                node = node.parent
            self._path = tuple(reverse_path)
        return self._path
    path = property(_get_path)

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other.path

    def __getattr__(self, name):
        return getattr(self.node, name)

class Extractor(object):
    TEXT_LENGTH_THRESHOLD = 25
    RETRY_LENGTH = 250
    
    def __init__(self, content, base_url=None, logger=None, debug=False, **options):
        self._content = content
        self.logger = logger
        self.base_url = base_url
        if self.logger is None:
            self.logger = get_logger('cola_extractor')
        self.on_debug = debug
        self.debug = self.logger.info if debug else (lambda s: None)
        self.options = options
            
        self._title = None
        self._html = None
            
    def preprocess(self, force=False):
        if force is True or self._html is None:
            preprocessor = PreProcessor(self._content, base_url=self.base_url)
            self._title, self._html = preprocessor.process()
            
    def title(self, force=False):
        self.preprocess(force=force)
        return self._title
    
    def content(self, force=False):
        self.preprocess(force=force)
        return self._html
    
    def _tags(self, node, *tag_names):
        for tag_name in tag_names:
            for n in node.find_all(tag_name):
                yield n
                
    def _text(self, node):
        return ''.join(node.find_all(text=True))
    
    def _describe(self, node):
        if not hasattr(node, 'name'):
            return "[text]"
        return "%s#%s.%s" % (
            node.name, node.get('id', ''), node.get('class',''))
                
    def _remove_unlikely_candidates(self):
        for elem in self._html.find_all():
            s = '%s%s%s' % (
                elem.name, elem.get('class', ''), elem.get('id', '')
            )
            if REGEXES['unlikelyCandidatesRe'].search(s) and \
                (not REGEXES['okMaybeItsACandidateRe'].search(s)) and \
                elem.name != 'body':
                self.debug("Removing unlikely candidate - %s" % (s,))
                elem.extract()
                
    def _transform_misused_divs_into_p(self):
        for elem in self._html.find_all('div'):
            if not REGEXES['divToPElementsRe'].search(''.join(map(unicode, elem.contents))):
                self.debug("Altering div(#%s.%s) to p" % (elem.get('id', ''), elem.get('class', '')))
                elem.name = 'p'
                
    def _get_link_density(self, node):
        link_length = len("".join([i.text or "" for i in node.find_all("a")]))
        text_length = len(self._text(node))
        return float(link_length) / max(text_length, 1)
                
    def _weight_node(self, node):
        weight = 0
        if node.get('class', None):
            cls = ''.join(node['class'])
            
            if REGEXES['negativeRe'].search(cls):
                weight -= 25

            if REGEXES['positiveRe'].search(cls):
                weight += 25

        if node.get('id', None):
            if REGEXES['negativeRe'].search(node['id']):
                weight -= 25

            if REGEXES['positiveRe'].search(node['id']):
                weight += 25

        return weight
                
    def _score_node(self, node):
        content_score = self._weight_node(node)
        name = node.name.lower()
        if name in ("div", "article"):
            content_score += 5
        elif name == "blockquote":
            content_score += 3
        elif name == "form":
            content_score -= 3
        elif name == "th":
            content_score -= 5
        return { 'content_score': content_score, 'elem': node }
                
    def _score_paragraphs(self, min_text_length=None):
        if min_text_length is None:
            min_text_length = self.TEXT_LENGTH_THRESHOLD
            
        candidates = {}
        elems = self._tags(self._html, 'p', 'td')
        
        for elem in elems:
            parent_node = elem.parent
            grand_parent_node = parent_node.parent
            parent_key = HashableElement(parent_node)
            grand_parent_key = HashableElement(grand_parent_node)

            inner_text = self._text(elem)
            
            # If this paragraph is less than 25 characters, don't even count it.
            if (not inner_text) or len(inner_text) < min_text_length:
                continue
            
            if parent_key not in candidates:
                candidates[parent_key] = self._score_node(parent_node)
            if grand_parent_node and grand_parent_key not in candidates:
                candidates[grand_parent_key] = self._score_node(grand_parent_node)
                
            content_score = 1
            content_score += len(re.split(ur',|，', inner_text))
            content_score += min([(len(inner_text) / 100), 3])

            candidates[parent_key]['content_score'] += content_score
            if grand_parent_node:
                candidates[grand_parent_key]['content_score'] += content_score / 2.0
                
        # Scale the final candidates score based on link density. Good content should have a
        # relatively small link density (5% or less) and be mostly unaffected by this operation.
        for elem, candidate in candidates.items():
            candidate['content_score'] *= (1 - self._get_link_density(elem))
            self.debug("candidate %s scored %s" % (self._describe(elem), candidate['content_score']))

        return candidates
    
    def _select_best_candidate(self, candidates):
        sorted_candidates = sorted(candidates.values(), 
                                   key=lambda x: x['content_score'], 
                                   reverse=True)
        self.debug("Top 5 candidates:")
        for candidate in sorted_candidates[:5]:
            elem = candidate['elem']
            self.debug("Candidate %s with score %s" % \
                       (self._describe(elem), candidate['content_score']))

        if len(sorted_candidates) == 0:
            return None
        best_candidate = sorted_candidates[0]
        self.debug("Best candidate %s with score %s" % \
                   (self._describe(best_candidate['elem']), best_candidate['content_score']))
        return best_candidate
    
    def _get_article(self, candidates, best_candidate):
        # Now that we have the top candidate, look through its siblings for content that might also be related.
        # Things like preambles, content split by ads that we removed, etc.
        
        sibling_score_threshold = max([10, best_candidate['content_score'] * 0.2])
        output = beautiful_soup("<div/>")
        for sibling in best_candidate['elem'].parent.contents:
            if isinstance(sibling, NavigableString): continue
            append = False
            if sibling is best_candidate['elem']:
                append = True
            sibling_key = HashableElement(sibling)
            if sibling_key in candidates and \
                candidates[sibling_key]['content_score'] >= sibling_score_threshold:
                append = True

            if sibling.name == "p":
                link_density = self._get_link_density(sibling)
                node_content = sibling.string or ""
                node_length = len(node_content)

                if node_length > 80 and link_density < 0.25:
                    append = True
                elif node_length < 80 and link_density == 0 and re.search('\.( |$)', node_content):
                    append = True

            if append:
                output.div.append(sibling)
                
        return output
    
    def _sanitize(self, node, candidates):
        for header in self._tags(node, "h1", "h2", "h3", "h4", "h5", "h6"):
            if self._weight_node(header) < 0 or \
                self._get_link_density(header) > 0.33: 
                header.extract()

        for elem in self._tags(node, "form", "iframe"):
            elem.extract()

        # Conditionally clean <table>s, <ul>s, and <div>s
        for el in self._tags(node, "table", "ul", "div"):
            weight = self._weight_node(el)
            el_key = HashableElement(el)
            if el_key in candidates:
                content_score = candidates[el_key]['content_score']
            else:
                content_score = 0
            name = el.name

            if weight + content_score < 0:
                el.extract()
                self.debug("Conditionally cleaned %s with weight %s and content score %s because score + content score was less than zero." %
                    (self._describe(el), weight, content_score))
            elif len(re.split(ur',|，', self._text(el))) < 10:
                counts = {}
                for kind in ['p', 'img', 'li', 'a', 'embed', 'input']:
                    counts[kind] = len(el.find_all(kind))
                counts["li"] -= 100

                content_length = len(self._text(el)) # Count the text length excluding any surrounding whitespace
                link_density = self._get_link_density(el)
                to_remove = False
                reason = ""

                if counts["img"] > counts["p"]:
                    reason = "too many images"
                    to_remove = True
                elif counts["li"] > counts["p"] and name != "ul" and name != "ol":
                    reason = "more <li>s than <p>s"
                    to_remove = True
                elif counts["input"] > (counts["p"] / 3):
                    reason = "less than 3x <p>s than <input>s"
                    to_remove = True
                elif content_length < (self.options.get('min_text_length', self.TEXT_LENGTH_THRESHOLD)) and (counts["img"] == 0 or counts["img"] > 2):
                    reason = "too short a content length without a single image"
                    to_remove = True
                elif weight < 25 and link_density > 0.2:
                    reason = "too many links for its weight (#{weight})"
                    to_remove = True
                elif weight >= 25 and link_density > 0.5:
                    reason = "too many links for its weight (#{weight})"
                    to_remove = True
                elif (counts["embed"] == 1 and content_length < 75) or counts["embed"] > 1:
                    reason = "<embed>s with too short a content length, or too many <embed>s"
                    to_remove = True

                if to_remove:
                    self.debug("Conditionally cleaned %s#%s.%s with weight %s and content score %s because it has %s." %
                        (el.name, el.get('id',''), el.get('class', ''), weight, content_score, reason))
                    el.extract()

        for el in ([node] + node.find_all()):
            if not (self.options.get('attributes')):
                el.attrMap = {}

        return unicode(node)
            
    def extract(self):
        try:
            ruthless = True
            while True:
                self.preprocess(force=True)
                for tag in self._tags(self._html, 'script', 'style'):
                    tag.extract()
                    
                if ruthless:
                    self._remove_unlikely_candidates()
                self._transform_misused_divs_into_p()
                candidates = self._score_paragraphs(self.options.get('min_text_length'))
                best_candidate = self._select_best_candidate(candidates)
                if best_candidate:
                    article = self._get_article(candidates, best_candidate)
                else:
                    if ruthless:
                        ruthless = False
                        self.debug("ended up stripping too much - going for a safer parse")
                        # try again
                        continue
                    else:
                        article = self._html.find('body') or self._html
                        
                cleaned_article = self._sanitize(article, candidates)
                retry_length = self.options.get('retry_length') or self.RETRY_LENGTH
                of_acceptable_length = len(cleaned_article or '') >= retry_length
                if ruthless and not of_acceptable_length:
                    ruthless = False
                    continue # try again
                else:
                    return cleaned_article
                
        except Exception, e:
            self.logger.exception(e)
            if self.on_debug:
                raise e
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-16

@author: Chine
'''

from urlparse import urlparse

def host_for_url(url):
    """
    >>> host_for_url('http://base/whatever/fdsh')
    'base'
    >>> host_for_url('invalid')
    """
    host = urlparse(url)[1]
    if not host:
#         raise ValueError("could not extract host from URL: %r" % (url,))
        return None
    return host

def absolute_url(url, base_href):
    """
    >>> absolute_url('foo', 'http://base/whatever/ooo/fdsh')
    'http://base/whatever/ooo/foo'

    >>> absolute_url('foo/bar/', 'http://base')
    'http://base/foo/bar/'

    >>> absolute_url('/foo/bar', 'http://base/whatever/fdskf')
    'http://base/foo/bar'

    >>> absolute_url('\\n/foo/bar', 'http://base/whatever/fdskf')
    'http://base/foo/bar'

    >>> absolute_url('http://localhost/foo', 'http://base/whatever/fdskf')
    'http://localhost/foo'
    """
    url = url.strip()
    proto = urlparse(url)[0]
    if proto:
        return url

    base_url_parts = urlparse(base_href)
    base_server = '://'.join(base_url_parts[:2])
    if url.startswith('/'):
        return base_server + url
    else:
        path = base_url_parts[2]
        if '/' in path:
            path = path.rsplit('/', 1)[0] + '/'
        else:
            path = '/'
        return base_server + path + url

if __name__ == '__main__':
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = logs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-31

@author: Chine
'''

import socket
import logging.handlers
import SocketServer
import struct
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class Log(object):
    def __init__(self, name, default_level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(default_level)
        self.formatter = logging.Formatter(
            '%(asctime)s - %(module)s.%(funcName)s.%(lineno)d - %(levelname)s - %(message)s')
        
    def add_stream_log(self, level=logging.DEBUG):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        self.logger.addHandler(stream_handler)
        
    def add_file_log(self, filename, level=logging.INFO):
        handler = logging.FileHandler(filename)
        handler.setFormatter(self.formatter)
        handler.setLevel(level)
        self.logger.addHandler(handler)
        
    def add_remote_log(self, server, level=logging.INFO):
        if ':' in server:
            server, port = tuple(server.split(':', 1))
            port = int(port)
        else:
            port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
            
        socket_handler = logging.handlers.SocketHandler(server, port)
        socket_handler.setLevel(level)
        self.logger.addHandler(socket_handler)
        
    def get_logger(self):
        return self.logger

def get_logger(name='cola', filename=None, server=None, is_master=False, 
               basic_level=logging.INFO):
    log = Log(name, basic_level)
    log.add_stream_log(basic_level)
    
    if filename is not None:
        level = basic_level
        if is_master:
            level = logging.ERROR
        log.add_file_log(filename, level)
    
    if server is not None:
        log.add_remote_log(server, logging.INFO)
        
    return log.get_logger()

def add_log_client(logger, client):
    if ':' in client:
        client, port = tuple(client.split(':', 1))
        port = int(port)
    else:
        port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
        
    socket_handler = logging.handlers.SocketHandler(client, port)
    socket_handler.setLevel(logging.INFO)
    logger.addHandler(socket_handler)
    
    return socket_handler

class LogRecordStreamHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        self.connection.setblocking(0)
        while not self.server.abort:
            try:
                chunk = self.connection.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.connection.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.connection.recv(slen - len(chunk))
                obj = self.unPickle(chunk)
                record = logging.makeLogRecord(obj)
                self.handleLogRecord(record)
            except socket.error:
                return
            
    def unPickle(self, data):
        return pickle.loads(data)
    
    def handleLogRecord(self, record):
        if self.server.logger is not None:
            logger = self.server.logger
        else:
            logger = logging.getLogger(record.name)
        logger.handle(record)
        
class LogRecordSocketReceiver(SocketServer.ThreadingTCPServer):
    
    allow_reuse_address = 1
    
    def __init__(self, logger=None, host='localhost', 
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = False
        self.timeout = 1
        self.logger = logger
        
    def shutdown(self):
        SocketServer.ThreadingTCPServer.shutdown(self)
        self.abort = True
########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-28

@author: Chine
'''

from cola.core.mq.hash_ring import HashRing
from cola.core.mq import MessageQueue

class MessageQueueClient(object):
    
    def __init__(self, nodes, copies=1):
        self.nodes = nodes
        self.hash_ring = HashRing(self.nodes)
        self.copies = max(min(len(self.nodes)-1, copies), 0)
        self.mq = MessageQueue(nodes, copies=copies)
        
    def put(self, objs):
        self.mq.put(objs)
        
    def get(self):
        for n in self.nodes:
            obj = self.mq._get(n)
            if obj is not None:
                return obj
########NEW FILE########
__FILENAME__ = hash_ring
# -*- coding: utf-8 -*-
"""
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

    hash_ring
    ~~~~~~~~~~~~~~
    Implements consistent hashing that can be used when
    the number of server nodes can increase or decrease (like in memcached).

    Consistent hashing is a scheme that provides a hash table functionality
    in a way that the adding or removing of one slot
    does not significantly change the mapping of keys to slots.

    More information about consistent hashing can be read in these articles:

        "Web Caching with Consistent Hashing":
            http://www8.org/w8-papers/2a-webserver/caching/paper2.html

        "Consistent hashing and random trees:
        Distributed caching protocols for relieving hot spots on the World Wide Web (1997)":
            http://citeseerx.ist.psu.edu/legacymapper?did=38148


    Example of usage::

        memcache_servers = ['192.168.0.246:11212',
                            '192.168.0.247:11212',
                            '192.168.0.249:11212']

        ring = HashRing(memcache_servers)
        server = ring.get_node('my_key')

    :copyright: 2008 by Amir Salihefendic.
    :license: BSD
"""

import math
import sys
from bisect import bisect

if sys.version_info >= (2, 5):
    import hashlib
    md5_constructor = hashlib.md5
else:
    import md5
    md5_constructor = md5.new

class HashRing(object):

    def __init__(self, nodes=None, weights=None):
        """`nodes` is a list of objects that have a proper __str__ representation.
        `weights` is dictionary that sets weights to the nodes.  The default
        weight is that all nodes are equal.
        """
        self.ring = dict()
        self._sorted_keys = []

        self.nodes = nodes

        if not weights:
            weights = {}
        self.weights = weights

        self._generate_circle()

    def _generate_circle(self):
        """Generates the circle.
        """
        total_weight = 0
        for node in self.nodes:
            total_weight += self.weights.get(node, 1)

        for node in self.nodes:
            weight = 1

            if node in self.weights:
                weight = self.weights.get(node)

            factor = math.floor((40*len(self.nodes)*weight) / total_weight);

            for j in xrange(0, int(factor)):
                b_key = self._hash_digest( '%s-%s' % (node, j) )

                for i in xrange(0, 3):
                    key = self._hash_val(b_key, lambda x: x+i*4)
                    self.ring[key] = node
                    self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def get_node(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned.

        If the hash ring is empty, `None` is returned.
        """
        pos = self.get_node_pos(string_key)
        if pos is None:
            return None
        return self.ring[ self._sorted_keys[pos] ]

    def get_node_pos(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned
        along with it's position in the ring.

        If the hash ring is empty, (`None`, `None`) is returned.
        """
        if not self.ring:
            return None

        key = self.gen_key(string_key)

        nodes = self._sorted_keys
        pos = bisect(nodes, key)

        if pos == len(nodes):
            return 0
        else:
            return pos

    def iterate_nodes(self, string_key, distinct=True):
        """Given a string key it returns the nodes as a generator that can hold the key.

        The generator iterates one time through the ring
        starting at the correct position.

        if `distinct` is set, then the nodes returned will be unique,
        i.e. no virtual copies will be returned.
        """
        if not self.ring:
            yield None, None

        returned_values = set()
        def distinct_filter(value):
            if str(value) not in returned_values:
                returned_values.add(str(value))
                return value

        pos = self.get_node_pos(string_key)
        for key in self._sorted_keys[pos:]:
            val = distinct_filter(self.ring[key])
            if val:
                yield val

        for i, key in enumerate(self._sorted_keys):
            if i < pos:
                val = distinct_filter(self.ring[key])
                if val:
                    yield val

    def gen_key(self, key):
        """Given a string key it returns a long value,
        this long value represents a place on the hash ring.

        md5 is currently used because it mixes well.
        """
        b_key = self._hash_digest(key)
        return self._hash_val(b_key, lambda x: x)

    def _hash_val(self, b_key, entry_fn):
        return (( b_key[entry_fn(3)] << 24)
                |(b_key[entry_fn(2)] << 16)
                |(b_key[entry_fn(1)] << 8)
                | b_key[entry_fn(0)] )

    def _hash_digest(self, key):
        m = md5_constructor()
        m.update(key)
        return map(ord, m.digest())

########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-23

@author: Chine
'''

import os
import threading
import mmap
import platform

class NodeExistsError(Exception): pass

class NodeNotSafetyShutdown(Exception): pass

class NodeNoSpaceForPut(Exception): pass

NODE_FILE_SIZE = 4 * 1024 * 1024 # single node store file must be less than 4M.

class Node(object):
    def __init__(self, dir_, size=NODE_FILE_SIZE, verify_exists_hook=None):
        self.lock = threading.Lock()
        self.NODE_FILE_SIZE = size
        self.verify_exists_hook = verify_exists_hook
        
        self.dir_ = dir_
        self.lock_file = os.path.join(dir_, 'lock')
        with self.lock:
            if os.path.exists(self.lock_file):
                raise NodeExistsError('Directory is being used by another node.')
            else:
                open(self.lock_file, 'w').close()
            
        self.old_files = []
        self.map_files = []
        self.file_handles = {}
        self.map_handles = {}
        self.stopped = False
        self.check()
        self.map()
            
    def shutdown(self):
        if self.stopped: return
        self.stopped = True
        
        try:
            self.merge()
            
            for handle in self.map_handles.values():
                handle.close()
            for handle in self.file_handles.values():
                handle.close()
                
            # Move a store to an old one.
            for f in self.old_files:
                os.remove(f)
            for f in self.map_files:
                os.rename(f, f + '.old')
                
            if self.verify_exists_hook is not None:
                self.verify_exists_hook.sync()
                self.verify_exists_hook.close()
        finally:
            with self.lock:
                os.remove(self.lock_file)
        
    def check(self):
        files = os.listdir(self.dir_)
        for fi in files:
            if fi == 'lock': continue
            
            file_path = os.path.join(self.dir_, fi)
            if not os.path.isfile(file_path) or \
                not fi.endswith('.old'):
                raise NodeNotSafetyShutdown('Node did not shutdown safety last time.')
            else:
                self.old_files.append(file_path)
                
        self.old_files = sorted(self.old_files, key=lambda k: int(os.path.split(k)[1].rsplit('.', 1)[0]))
        self.map_files = [f.rsplit('.', 1)[0] for f in self.old_files]
        
    def map(self):
        for (old, new) in zip(self.old_files, self.map_files):
            with open(old) as old_fp:
                fp = open(new, 'w+')
                self.file_handles[new] = fp
                content = old_fp.read()
                fp.write(content)
                fp.flush()
                
                if len(content) > 0:
                    m = mmap.mmap(fp.fileno(), self.NODE_FILE_SIZE)
                    self.map_handles[new] = m
                    
        if len(self.map_files) == 0:
            path = os.path.join(self.dir_, '1')
            self.map_files.append(path)
            self.file_handles[path] = open(path, 'w+')
            
    def _write_obj(self, fp, obj):
        if platform.system() == "Windows":
            fp.write(obj)
        else:
            length = len(obj)
            rest_length = self.NODE_FILE_SIZE - length
            fp.write(obj + '\x00' * rest_length)
            
        fp.flush()
        
    def _get_obj(self, obj, force=False):
        if isinstance(obj, (tuple, list)):
            if self.verify_exists_hook is None or force is True:
                src_obj = obj
                obj = '\n'.join(obj) + '\n'
            else:
                src_obj = list()
                for itm in obj:
                    if not self.verify_exists_hook.verify(itm):
                        src_obj.append(itm)
                obj = '\n'.join(src_obj) + '\n'
        else:
            if self.verify_exists_hook is None or force is True:
                src_obj = obj
                obj = obj + '\n'
            else:
                if not self.verify_exists_hook.verify(obj):
                    src_obj = obj
                    obj = obj + '\n'
                else:
                    return '', ''
        
        return src_obj, obj
                    
    def put(self, obj, force=False):
        if self.stopped: return ''
        
        src_obj, obj = self._get_obj(obj, force=force)
                
        if len(obj.replace('\n', '')) == 0:
            return ''
            
        # If no file has enough space
        if len(obj) > self.NODE_FILE_SIZE:
            raise NodeNoSpaceForPut('No enouph space for this put.')
        
        for f in self.map_files:
            with self.lock:
                # check if mmap created
                if f not in self.map_handles:
                    fp = self.file_handles[f]
                    self._write_obj(fp, obj)
                    
                    m = mmap.mmap(fp.fileno(), self.NODE_FILE_SIZE)
                    self.map_handles[f] = m
                else:
                    m = self.map_handles[f]
                    size = m.rfind('\n')
                    new_size = size + 1 + len(obj)
                    
                    if new_size >= self.NODE_FILE_SIZE:
                        continue
                    
                    m[:new_size] = m[:size+1] + obj
                    m.flush()
                
            return src_obj
        
        name = str(int(os.path.split(self.map_files[-1])[1]) + 1)
        path = os.path.join(self.dir_, name)
        self.map_files.append(path)
        fp = open(path, 'w+')
        self.file_handles[path] = fp
        self._write_obj(fp, obj)
        self._add_handles(path)
        
        return src_obj
            
    def get(self):
        if self.stopped: return
        
        for m in self.map_handles.values():
            with self.lock:
                pos = m.find('\n')
                while pos >= 0:
                    obj = m[:pos]
                    m[:] = m[pos+1:] + '\x00' * (pos+1)
                    m.flush()
                    if len(obj.strip()) != 0:
                        return obj.strip()
                    pos = m.find('\n')
        
    def _remove_handles(self, path):
        if path in self.map_handles:
            self.map_handles[path].close()
            del self.map_handles[path]
        if path in self.file_handles:
            self.file_handles[path].close()
            del self.file_handles[path]
            
    def _add_handles(self, path):
        if path not in self.file_handles:
            self.file_handles[path] = open(path, 'w+')
        if path not in self.map_handles and \
            os.path.getsize(path) > 0:
            self.map_handles[path] = mmap.mmap(
                self.file_handles[path].fileno(), self.NODE_FILE_SIZE)
        
    def merge(self):
        if len(self.map_files) > 1:
            for i in range(len(self.map_files)-1, 0, -1):
                f_path1 = self.map_files[i-1]
                f_path2 = self.map_files[i]
                m1 = self.map_handles[f_path1]
                m2 = self.map_handles[f_path2]
                pos1 = m1.rfind('\n')
                pos2 = m2.rfind('\n')
                
                if pos1 + pos2 + 2 < self.NODE_FILE_SIZE:
                    m1[:pos1+pos2+2] = m1[:pos1+1] + m2[:pos2+1]
                    m1.flush()
                            
                    self._remove_handles(f_path2)
                    self.map_files.remove(f_path2)
                    os.remove(f_path2)
                    
        for idx, f in enumerate(self.map_files):
            if not f.endswith(str(idx+1)):
                dir_ = os.path.dirname(f)
                self._remove_handles(f)
                self.map_files.remove(f)
                
                new_f = os.path.join(dir_, str(idx+1))
                os.rename(f, new_f)
                self.map_files.append(new_f)
                self._add_handles(new_f)
        self.map_files = sorted(self.map_files, key=lambda f: int(os.path.split(f)[1]))
        
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.shutdown()
########NEW FILE########
__FILENAME__ = opener
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-17

@author: Chine
'''

import urllib2
import cookielib
import gzip

from cola.core.errors import DependencyNotInstalledError

class Opener(object):
    def open(self, url):
        raise NotImplementedError
    
    def ungzip(self, fileobj):
        gz = gzip.GzipFile(fileobj=fileobj, mode='rb')
        try:
            return gz.read()
        finally:
            gz.close()

class BuiltinOpener(Opener):
    def __init__(self, cookie_filename=None):
        self.cj = cookielib.LWPCookieJar()
        if cookie_filename is not None:
            self.cj.load(cookie_filename)
        self.cookie_processor = urllib2.HTTPCookieProcessor(self.cj)
        self.opener = urllib2.build_opener(self.cookie_processor, urllib2.HTTPHandler)
        urllib2.install_opener(self.opener)
    
    def open(self, url):
        resp = urllib2.urlopen(url)
        is_gzip = resp.headers.dict.get('content-encoding') == 'gzip'
        if is_gzip:
            return self.ungzip(resp)
        return resp.read()
        
    
class MechanizeOpener(Opener):
    def __init__(self, cookie_filename=None, user_agent=None, timeout=None):
        try:
            import mechanize
        except ImportError:
            raise DependencyNotInstalledError('mechanize')
        
        if user_agent is None:
            user_agent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
        
        self.browser = mechanize.Browser()
        
        self.cj = cookielib.LWPCookieJar()
        if cookie_filename is not None:
            self.cj.load(cookie_filename)
        self.browser.set_cookiejar(self.cj)
        self.browser.set_handle_equiv(True)
        self.browser.set_handle_gzip(True)
        self.browser.set_handle_redirect(True)
        self.browser.set_handle_referer(True)
        self.browser.set_handle_robots(False)
        self.browser.addheaders = [
            ('User-agent', user_agent)]
        
        if timeout is None:
            self._default_timout = mechanize._sockettimeout._GLOBAL_DEFAULT_TIMEOUT
        else:
            self._default_timout = timeout
            
    def set_default_timeout(self, timeout):
        self._default_timout = timeout
        
    def open(self, url, data=None, timeout=None):
        # check if gzip by
        # br.response().info().dict.get('content-encoding') == 'gzip'
        # experimently add `self.br.set_handle_gzip(True)` to handle
        if timeout is None:
            timeout = self._default_timout
        return self.browser.open(url, data=data, timeout=timeout).read()
    
    def browse_open(self, url, data=None, timeout=None):
        if timeout is None:
            timeout = self._default_timout
        self.browser.open(url, data=data, timeout=timeout)
        return self.browser
    
    def close(self):
        resp = self.browser.response()
        if resp is not None:
            resp.close()
        self.browser.clear_history()
    
class SpynnerOpener(Opener):
    def __init__(self, user_agent=None, **kwargs):
        try:
            import spynner
        except ImportError:
            raise DependencyNotInstalledError('spynner')
        
        if user_agent is None:
            user_agent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
        
        self.br = spynner.Browser(user_agent=user_agent, **kwargs)
        
    def spynner_open(self, url, data=None, headers=None, method='GET', 
                     wait_for_text=None, wait_for_selector=None, tries=None):
        try:
            from PyQt4.QtNetwork import QNetworkAccessManager
        except ImportError:
            raise DependencyNotInstalledError('PyQt4')
        
        if wait_for_text is not None:
            def wait_callback(br):
                return wait_for_text in br.html
        elif wait_for_selector is not None:
            def wait_callback(br):
                return not br.webframe.findFirstElement(wait_for_selector).isNull()
        else:
            wait_callback = None
        
        operation = QNetworkAccessManager.GetOperation
        if method == 'POST':
            operation = QNetworkAccessManager.PostOperation
        self.br.load(url, wait_callback=wait_callback, tries=tries, 
                     operation=operation, body=data, headers=headers)
        
        return self.br
        
    def open(self, url, data=None, headers=None, method='GET', 
             wait_for_text=None, wait_for_selector=None, tries=None):
        br = self.spynner_open(url, data=data, headers=headers, method=method, 
                               wait_for_text=wait_for_text, tries=tries)
        return br.contents
    
    def wait_for_selector(self, selector, **kwargs):
        self.br.wait_for_content(
            lambda br: not br.webframe.findFirstElement(selector).isNull(), 
            **kwargs)
########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-21

@author: Chine
'''

class Parser(object):
    def __init__(self, opener=None, url=None, **kwargs):
        self.opener = opener
        if url is not None:
            self.url = url
            
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        
    def parse(self, url=None):
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = rpc
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-23

@author: Chine
'''

import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib
import os
import socket

RETRY_TIMES = 10

class ColaRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):
    
    def __init__(self, *args, **kwargs):
        SimpleXMLRPCServer.__init__(self, *args, **kwargs)
        self.allow_none = True
    
        
def client_call(server, func_name, *args, **kwargs):
    serv = xmlrpclib.ServerProxy('http://%s' % server)
    ignore = kwargs.get('ignore', False)
    if not ignore:
        err = None
        retry_times = 0
        while retry_times <= RETRY_TIMES:
            try:
                return getattr(serv, func_name)(*args)
            except socket.error, e:
                retry_times += 1
                err = e
        raise err
    else:
        try:
            return getattr(serv, func_name)(*args)
        except socket.error:
            pass

class FileTransportServer(object):
    def __init__(self, rpc_server, dirname):
        self.rpc_server = rpc_server
        self.dirname = dirname
        self.rpc_server.register_function(self.receive_file)
        
    def receive_file(self, name, args):
        path = os.path.join(self.dirname, name)
        with open(path, 'wb') as handle:
            handle.write(args.data)
            return True
        
class FileTransportClient(object):
    def __init__(self, server, path):
        self.server = server
        self.path = path
        
    def send_file(self):
        name = os.path.split(self.path)[1]
        with open(self.path, 'rb') as handle:
            binary_data = xmlrpclib.Binary(handle.read())
            client_call(self.server, 'receive_file', name, binary_data)
########NEW FILE########
__FILENAME__ = unit
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-23

@author: Chine
'''

class Url(object):
    def __init__(self, url, force=False):
        self.url = url
        self.force = force
        
    def __str__(self):
        return self.url

class Bundle(object):
    '''
    Sometimes the target is all the urls about a user.
    Then the urls compose the bundle.
    So a bundle can generate several urls.
    '''
    
    def __init__(self, label, force=False):
        if not isinstance(label, str):
            raise ValueError("Bundle's label must a string.")
        self.label = label
        self.force = force
        
    def urls(self):
        raise NotImplementedError
    
    def __str__(self):
        return self.label
########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-21

@author: Chine
'''

import re

class Url(object):
    def __init__(self, url_re, name, parser, **kw):
        self.url_re = re.compile(url_re, re.IGNORECASE)
        self.name = name
        self.parser = parser
        self.options = kw
        
    def match(self, url):
        return self.url_re.match(url) is not None
        
class UrlPatterns(object):
    def __init__(self, *urls):
        for url in urls:
            if not isinstance(url, Url):
                raise ValueError('urls must be Url instances')
        self.url_patterns = list(urls)
        
    def __add__(self, url_obj):
        if not isinstance(url_obj, Url):
            raise ValueError('url_obj must be an instance of Url')
        self.url_patterns.append(url_obj)
        return self
    
    def matches(self, urls, pattern_names=None):
        for url in urls:
            if isinstance(url, basestring):
                url_str = url
            else:
                url_str = str(url)
            for pattern in self.url_patterns:
                if pattern_names is not None and \
                    pattern.name not in pattern_names:
                    continue
                if pattern.match(url_str):
                    yield url
                    break
                
    def get_parser(self, url, pattern_names=None, options=False):
        for pattern in self.url_patterns:
            if pattern.match(str(url)):
                if pattern_names is not None and \
                    pattern.name not in pattern_names:
                    continue
                
                if options is True:
                    return pattern.parser, pattern.options
                return pattern.parser
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-24

@author: Chine
'''

import socket
import os
import sys
import urllib

from cola.core.errors import DependencyNotInstalledError

def add_localhost(func):
    def inner(*args, **kwargs):
        ips = func(*args, **kwargs)
        localhost = '127.0.0.1'
        if localhost not in ips:
            ips.append(localhost)
        return ips
    return inner

@add_localhost
def get_ips():
    localIP = socket.gethostbyname(socket.gethostname())
    ex = socket.gethostbyname_ex(socket.gethostname())[2]
    if len(ex) == 1:
        return [ex[0]]
    return [ip for ip in ex if ip != localIP]

def get_ip():
    localIP = socket.gethostbyname(socket.gethostname())
    ex = socket.gethostbyname_ex(socket.gethostname())[2]
    if len(ex) == 1:
        return ex[0]
    for ip in ex:
        if ip != localIP:
            return ip
        
def root_dir():
    def _get_dir(f):
        return os.path.dirname(f)
    f = os.path.abspath(__file__)
    for _ in range(3):
        f = _get_dir(f)
    return f

def import_job(path):
    dir_, name = os.path.split(path)
    if os.path.isfile(path):
        name = name.rstrip('.py')
    else:
        sys.path.insert(0, os.path.dirname(dir_))
    sys.path.insert(0, dir_)
    job_module = __import__(name)
    job = job_module.get_job()
    
    return job

def urldecode(link):
    decodes = {}
    if '?' in link:
        params = link.split('?')[1]
        for param in params.split('&'):
            k, v = tuple(param.split('='))
            decodes[k] = urllib.unquote(v)
    return decodes

def beautiful_soup(html, logger=None):
    try:
        from bs4 import BeautifulSoup, FeatureNotFound
    except ImportError:
        raise DependencyNotInstalledError("BeautifulSoup4")
    
    try:
        return BeautifulSoup(html, 'lxml')
    except FeatureNotFound:
        if logger is not None:
            logger.info('lxml not installed')
        return BeautifulSoup(html)
########NEW FILE########
__FILENAME__ = zip
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-6

@author: Chine
'''

import os
import zipfile

class FixedZipFile(zipfile.ZipFile):
    '''
    Fixed for Python 2.6 when ZipFile doesn't support with statement
    '''
    
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.close()

class ZipHandler(object):
    
    @classmethod
    def compress(cls, zip_file, src_dir, type_filters=None):
        root_len = len(os.path.abspath(src_dir))
        dir_name = os.path.split(src_dir)[1].replace(' ', '_')
        
        with FixedZipFile(zip_file, 'w') as zf:
            if os.path.isfile(src_dir):
                zf.write(src_dir, dir_name)
            else:
                for root, _, files in os.walk(src_dir):
                    archive_root = os.path.abspath(root)[root_len:].strip(os.sep)
                    for f in files:
                        if type_filters is not None and '.' in f and \
                            f.rsplit('.', 1)[1] in type_filters:
                            continue
                        
                        full_path = os.path.join(root, f)
                        archive_name = os.path.join(dir_name, archive_root, f)
                        zf.write(full_path, archive_name)
                    
        return zip_file
    
    @classmethod
    def uncompress(cls, zip_file, dest_dir):
        dir_name = None
        with FixedZipFile(zip_file) as zf:
            for f in zf.namelist():
                zf.extract(f, dest_dir)
                if dir_name is None:
                    if '/' in f.strip('/'):
                        dir_name = f.strip('/').split('/')[0]
                    else:
                        dir_name = f.strip('/')
                    
        return os.path.join(dest_dir, dir_name)
########NEW FILE########
__FILENAME__ = context
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-22

@author: Chine
'''

from cola.core.config import PropertyObject, Config
from cola.core.config import main_conf

class Context(object):
    def __init__(self, user_conf=None, **user_defines):
        self.main_conf = main_conf
        if user_conf is not None:
            if isinstance(user_conf, str):
                self.user_conf = Config(user_conf)
            else:
                self.user_conf = user_conf
        else:
            self.user_conf = PropertyObject(dict())
        self.user_defines = PropertyObject(user_defines)
         
        dicts = PropertyObject({})
        for obj in (self.main_conf, self.user_conf, self.user_defines):
            dicts.update(obj)
        for k in dicts:
            if not k.startswith('_'):
                setattr(self, k, getattr(dicts, k))
########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-11

@author: Chine
'''

import threading
import os
import time

from cola.core.rpc import ColaRPCServer

class JobLoader(object):
    
    def __init__(self, job, dir_, local, 
                 context=None, copies=1, force=False):
        self.job = job
        self.ctx = context or job.context
        
        self.root = dir_
        self.host, self.port = tuple(local.split(':', 1))
        self.port = int(self.port)
        self.copies = copies
        self.force = force
        
        # status
        self.stopped = False
        
    def check_env(self, force=False):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f) and not force:
            return False
        if os.path.exists(lock_f) and force:
            try:
                os.remove(lock_f)
            except:
                return False
            
        open(lock_f, 'w').close()
        return True
        
    def init_rpc_server(self):
        rpc_server = ColaRPCServer((self.host, self.port))
        thd = threading.Thread(target=rpc_server.serve_forever)
        thd.setDaemon(True)
        thd.start()
        self.rpc_server = rpc_server
        
    def finish(self):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f):
            os.remove(lock_f)
        self.rpc_server.shutdown()
        
    def stop(self):
        self.stopped = True
        self.finish()
        
    def require(self, count):
        raise NotImplementedError
    
    def apply(self):
        raise NotImplementedError
    
    def complete(self, obj):
        raise NotImplementedError
        
class LimitionJobLoader(object):
    def __init__(self, job, context=None):
        self.job = job
        self.ctx = context or job.context
        # status
        self.stopped = False
        
        self.size = self.ctx.job.size
        self.size_limit = self.size > 0
        self.started = 0
        self.completed = 0
        
        self.rate = self.ctx.job.limit
        self.rate_limit = self.rate > 0
        self.current_rate = 0
        
        # locks
        self.op_lock = threading.Lock()
        self.size_lock = threading.Lock()
        self.size_lock_acquire = self.size_lock.acquire
        self.size_lock_release = self._size_lock_release
        
    def init_rate_clear(self):
        if self.rate_limit:
            def _clear():
                self.current_rate = 0
                time.sleep(60)
                if not self.stopped:
                    _clear()
            thd = threading.Thread(target=_clear)
            thd.setDaemon(True)
            thd.start()
            
    def _size_lock_release(self):
        try:
            self.size_lock.release()
        except:
            pass
        
    def finish(self):
        self.size_lock_release()
        
    def stop(self):
        self.stopped = True
        self.finish()
        
    def _apply(self):
        if self.completed >= self.size or \
            self.stopped:
            return False
        
        if self.started >= self.size:
            self.size_lock_acquire()
            return self._apply()
            
        return True
            
    def apply(self):
        if not self.size_limit and not self.stopped:
            return True
        
        if self.completed >= self.size or \
            self.stopped:
            return False
            
        self.op_lock.acquire()
        try:
            if self.started < self.size:
                self.started += 1
                if self.started >= self.size:
                    self.size_lock_acquire()
                return True
        finally:
            self.op_lock.release()
            
        if self.started >= self.size:
            self.size_lock_acquire()
            return self._apply()
            
        return True
    
    def error(self, obj):
        self.started -= 1
        self.size_lock_release()
        
    def complete(self, obj):
        if not self.size_limit: return False
        
        self.completed += 1
        if self.completed >= self.size:
            self.stopped = True
        self.size_lock_release()
        
        return self.completed >= self.size
        
    def require(self, count):
        if not self.rate_limit:
            if not self.stopped:
                return count
            else:
                return 0
        
        size = max(min(self.rate - self.current_rate, count), 0)
        self.current_rate += size
        return size
########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-27

@author: Chine
'''

import threading
import signal
import os

from cola.core.rpc import client_call
from cola.core.mq.client import MessageQueueClient
from cola.core.utils import get_ip, get_ips, root_dir, import_job
from cola.core.logs import LogRecordSocketReceiver, get_logger, \
                            add_log_client
from cola.core.config import main_conf
from cola.job.loader import JobLoader, LimitionJobLoader

class JobMasterRunning(Exception): pass

TIME_SLEEP = 10

class MasterJobLoader(LimitionJobLoader, JobLoader):
    def __init__(self, job, data_dir, nodes, local_ip=None, client=None,
                 context=None, copies=1, force=False):
        ctx = context or job.context
        master_port = ctx.job.master_port
        if local_ip is None:
            local_ip = get_ip()
        else:
            choices_ips = get_ips()
            if local_ip not in choices_ips:
                raise ValueError('IP address must be one of (%s)' % ','.join(choices_ips))
        local = '%s:%s' % (local_ip, master_port)
        
        JobLoader.__init__(self, job, data_dir, local, 
                           context=ctx, copies=copies, force=force)
        LimitionJobLoader.__init__(self, job, context=ctx)
        
        # check
        self.check()
        
        self.nodes = nodes
        self.not_registered = self.nodes[:]
        self.not_finished = self.nodes[:]
        
        # mq
        self.mq_client = MessageQueueClient(self.nodes, copies=copies)
        
        # lock
        self.ready_lock = threading.Lock()
        self.ready_lock.acquire()
        self.finish_lock = threading.Lock()
        self.finish_lock.acquire()
        
        # logger
        self.logger = get_logger(
            name='cola_master_%s'%self.job.real_name,
            filename=os.path.join(self.root, 'job.log'),
            is_master=True)
        self.client = client
        self.client_handler = None
        if self.client is not None:
            self.client_handler = add_log_client(self.logger, self.client)
        
        self.init_rpc_server()
        self.init_rate_clear()
        self.init_logger_server(self.logger)
        
        # register rpc server
        self.rpc_server.register_function(self.client_stop, 'client_stop')
        self.rpc_server.register_function(self.ready, 'ready')
        self.rpc_server.register_function(self.worker_finish, 'worker_finish')
        self.rpc_server.register_function(self.complete, 'complete')
        self.rpc_server.register_function(self.error, 'error')
        self.rpc_server.register_function(self.get_nodes, 'get_nodes')
        self.rpc_server.register_function(self.apply, 'apply')
        self.rpc_server.register_function(self.require, 'require')
        self.rpc_server.register_function(self.stop, 'stop')
        self.rpc_server.register_function(self.add_node, 'add_node')
        self.rpc_server.register_function(self.remove_node, 'remove_node')
        self.rpc_server.register_function(self.pages, 'pages')
        
        # register signal
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def init_logger_server(self, logger):
        self.log_server = LogRecordSocketReceiver(host=get_ip(), logger=logger)
        threading.Thread(target=self.log_server.serve_forever).start()
        
    def stop_logger_server(self):
        if hasattr(self, 'log_server'):
            self.log_server.shutdown()
            
    def client_stop(self):
        if self.client_handler is not None:
            self.logger.removeHandler(self.client_handler)
                
    def check(self):
        env_legal = self.check_env(force=self.force)
        if not env_legal:
            raise JobMasterRunning('There has been a running job master.')
        
    def release_lock(self, lock):
        try:
            lock.release()
        except:
            pass
        
    def finish(self):
        all_pages = self.pages()
        
        self.release_lock(self.ready_lock)
        self.release_lock(self.finish_lock)
        
        LimitionJobLoader.finish(self)
        JobLoader.finish(self)
        self.stop_logger_server()
        
        try:
            for handler in self.logger.handlers:
                handler.close()
        except:
            pass
            
        if self.client is not None:
            rpc_client = '%s:%s' % (
                self.client.split(':')[0], 
                main_conf.client.port
            )
            client_call(rpc_client, 'stop', ignore=True)
            
        self.logger.info('All nodes finishes visiting pages size: %s' % all_pages)
        self.stopped = True
        
    def stop(self):
        for node in self.nodes:
            client_call(node, 'stop', ignore=True)
        self.finish()
        
    def signal_handler(self, signum, frame):
        self.stop()
        
    def get_nodes(self):
        return self.nodes
        
    def ready(self, node):
        if node in self.not_registered:
            self.not_registered.remove(node)
            if len(self.not_registered) == 0:
                self.ready_lock.release()
                
    def worker_finish(self, node):
        if node in self.not_finished:
            self.not_finished.remove(node)
            if len(self.not_finished) == 0:
                self.finish_lock.release()
                
    def add_node(self, node):
        for node in self.nodes:
            client_call(node, 'add_node', node, ignore=True)
        self.nodes.append(node)
        client_call(node, 'run', ignore=True)
        
    def remove_node(self, node):
        for node in self.nodes:
            client_call(node, 'remove_node', node, ignore=True)
        if node in self.nodes:
            self.nodes.remove(node)
            
    def pages(self):
        all_pages = 0
        for node in self.nodes:
            pages = client_call(node, 'pages', ignore=True)
            if pages is not None:
                all_pages += int(pages)
        return all_pages
        
    def run(self):
        self.ready_lock.acquire()
        
        if not self.stopped and len(self.not_registered) == 0:
            self.mq_client.put(self.job.starts)
            for node in self.nodes:
                client_call(node, 'run')
            
        self.finish_lock.acquire()
        
        master_watcher = '%s:%s' % (get_ip(), main_conf.master.port)
        client_call(master_watcher, 'finish_job', self.job.real_name, ignore=True)
        
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.finish()

def load_job(job_path, nodes, ip_address=None, data_path=None, 
             client=None, context=None, force=False):
    if not os.path.exists(job_path):
        raise ValueError('Job definition does not exist.')
        
    job = import_job(job_path)
    
    if data_path is None:
        data_path = os.path.join(root_dir(), 'data')
    root = os.path.join(data_path, 'master', 'jobs', job.real_name)
    if not os.path.exists(root):
        os.makedirs(root)
    
    with MasterJobLoader(job, root, nodes, local_ip=ip_address, client=client, 
                         context=context, force=force) as job_loader:
        job_loader.run()
    
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser('Cola job loader')
    parser.add_argument('-j', '--job', metavar='job directory', required=True,
                        help='job directory to run')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-i', '--ip', metavar='IP address', nargs='?',
                        default=None, const=None, 
                        help='IP Address to start')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    parser.add_argument('-n', '--nodes', metavar='worker job loaders', required=True, nargs='+',
                        help='worker connected(each in the former of `ip:port`)')
    parser.add_argument('-c', '--client', metavar='client', nargs='?',
                        default=None, const=None,
                        help='client which starts the job')
    args = parser.parse_args()
    
    path = args.job
    data_path = args.data
    ip_address = args.ip
    nodes = args.nodes
    if len(nodes) == 1:
        nodes = nodes[0].split(' ')
    force = args.force
    client = args.client
    load_job(path, nodes, ip_address=ip_address, 
             data_path=data_path, 
             client=client, force=force)
########NEW FILE########
__FILENAME__ = watcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-5

@author: Chine
'''

import time
import threading
import os
import subprocess
import shutil

from cola.core.rpc import client_call, ColaRPCServer, \
    FileTransportServer, FileTransportClient
from cola.core.zip import ZipHandler
from cola.core.utils import get_ip, get_ips, \
                            import_job, root_dir
from cola.core.config import main_conf

RUNNING, HANGUP, STOPPED = range(3)
CONTINOUS_HEARTBEAT = 90
HEARTBEAT_INTERVAL = 20
HEARTBEAT_CHECK_INTERVAL = 3*HEARTBEAT_INTERVAL

class MasterWatcherRunning(Exception): pass

class MasterJobInfo(object):
    def __init__(self, port, nodes_ip_addresses, worker_port, popen=None):
        self.job_master = '%s:%s' % (get_ip(), port)
        self.nodes = [
            '%s:%s'%(node_ip, worker_port) for node_ip in nodes_ip_addresses
        ]
        self.worker_port = worker_port
        self.popen = None
        
    def add_worker(self, node):
        if ':' not in node:
            node = '%s:%s' % (node, self.worker_port)
        self.nodes.append(node)
        client_call(self.job_master, 'add_node', node, ignore=True)
        
    def remove_worker(self, node):
        if ':' not in node:
            node = '%s:%s' % (node, self.worker_port)
        self.nodes.remove(node)
        client_call(self.job_master, 'remove_node', node, ignore=True)
        
    def has_worker(self, node):
        if ':' not in node:
            node = '%s:%s' % (node, self.worker_port)
        return node in self.nodes
        
class WatcherInfo(object):
    def __init__(self, watcher):
        self.status = RUNNING
        self.continous_register = 1
        self.last_update = int(time.time())
        
    def register(self):
        self.continous_register += 1
        self.last_update = int(time.time())

class MasterWatcher(object):
    def __init__(self, root, zip_dir, job_dir, 
                 ip_address=None, data_path=None, force=False):
        self.root = root
        self.zip_dir = zip_dir
        self.job_dir = job_dir
        self.data_path = data_path
        self.force = force
        
        self.nodes_watchers = {}
        self.running_jobs = {}
        self.black_list = []
        if ip_address is None:
            ip_address = get_ip()
        else:
            choices_ips = get_ips()
            if ip_address not in choices_ips:
                raise ValueError('IP address must be one of (%s)' % ','.join(choices_ips))
        self.ip_address = ip_address
        self.port = main_conf.master.port
        
        self.stopped = False
        
        self.check(force=force)
        self.init_rpc_server()
        
        self.rpc_server.register_function(self.register_watcher_heartbeat, 
                                          'register_heartbeat')
        self.rpc_server.register_function(self.stop, 'stop')
        self.rpc_server.register_function(self.list_jobs, 'list_jobs')
        self.rpc_server.register_function(self.start_job, 'start_job')
        self.rpc_server.register_function(self.stop_job, 'stop_job')
        self.rpc_server.register_function(self.finish_job, 'finish_job')
        self.rpc_server.register_function(self.clear_job, 'clear_job')
        self.rpc_server.register_function(self.list_job_dirs, 'list_job_dirs')
        self.rpc_server.register_function(self.list_workers, 'list_workers')
        
        self.set_receiver(zip_dir)
        
    def init_rpc_server(self):
        rpc_server = ColaRPCServer((self.ip_address, self.port))
        thd = threading.Thread(target=rpc_server.serve_forever)
        thd.setDaemon(True)
        thd.start()
        self.rpc_server = rpc_server
        
    def check(self, force=False):
        if not self.check_env(force=force):
            raise MasterWatcherRunning('There has been a running master watcher.')
        
    def check_env(self, force=False):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f) and not force:
            return False
        if os.path.exists(lock_f) and force:
            try:
                os.remove(lock_f)
            except:
                return False
            
        open(lock_f, 'w').close()
        return True
    
    def finish(self):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f):
            os.remove(lock_f)
        self.rpc_server.shutdown()
        self.stopped = True
        
    def register_watcher_heartbeat(self, node_watcher):
        if node_watcher not in self.nodes_watchers:
            watcher_info = WatcherInfo(node_watcher)
            self.nodes_watchers[node_watcher] = watcher_info
        else:
            watcher_info = self.nodes_watchers[node_watcher]
            watcher_info.register()
            
    def start_check_worker(self):
        def _check():
            for watcher, watcher_info in self.nodes_watchers.iteritems():
                ip_addr = watcher.split(':')[0]
                
                # if loose connection
                if int(time.time()) - watcher_info.last_update \
                    > HEARTBEAT_CHECK_INTERVAL:
                    
                    watcher_info.continous_register = 0
                    if watcher_info.status == RUNNING:
                        watcher_info.status = HANGUP
                    elif watcher_info.status == HANGUP:
                        watcher_info.status = STOPPED
                        self.black_list.append(watcher)
                        
                        for job_info in self.running_jobs.values():
                            if job_info.has_worker(ip_addr):
                                job_info.remove_worker(ip_addr)
                        
                # if continously connect for more than 10 min
                elif watcher_info.continous_register >= CONTINOUS_HEARTBEAT:
                    if watcher_info.status != RUNNING:
                        watcher_info.status = RUNNING
                    if watcher in self.black_list:
                        self.black_list.remove(watcher)
                        
                    for job_info in self.running_jobs.values():
                        if not job_info.has_worker(ip_addr):
                            job_info.add_worker(ip_addr)
                
        def _start():
            while not self.stopped:
                _check()
                time.sleep(HEARTBEAT_CHECK_INTERVAL)
        
        thread = threading.Thread(target=_start)
        thread.setDaemon(True)
        thread.start()
        return thread
    
    def list_workers(self):
        return self.nodes_watchers.keys()
        
    def list_jobs(self):
        return self.running_jobs.keys()
    
    def list_job_dirs(self):
        return os.listdir(self.job_dir)
    
    def set_receiver(self, base_dir):
        serv = FileTransportServer(self.rpc_server, base_dir)
        return serv
    
    def start_job(self, zip_filename, uncompress=True, client=None):
        if uncompress:
            zip_file = os.path.join(self.zip_dir, zip_filename)
            
            # transfer zip file to workers
            for watcher in self.nodes_watchers:
                if watcher.split(':')[0] == self.ip_address:
                    continue
                file_trans_client = FileTransportClient(watcher, zip_file)
                file_trans_client.send_file()
            
            job_dir = ZipHandler.uncompress(zip_file, self.job_dir)
        else:
            job_dir = os.path.join(self.job_dir, zip_filename.rsplit('.', 1)[0])
            
        job = import_job(job_dir)
        
        worker_port = job.context.job.port
        port = job.context.job.master_port
        nodes = [watcher.split(':')[0] for watcher in self.nodes_watchers]
        
        if len(nodes) > 0:
            info = MasterJobInfo(port, nodes, worker_port)
            self.running_jobs[job.real_name] = info
            
            dirname = os.path.dirname(os.path.abspath(__file__))
            f = os.path.join(dirname, 'loader.py')
            workers = ['%s:%s'%(node, worker_port) for node in nodes]
            
            cmds = ['python', f, '-j', job_dir, '-i', self.ip_address, 
                    '-n', ' '.join(workers)]
            if self.data_path is not None:
                cmds.extend(['-d', self.data_path])
            if self.force:
                cmds.append('-f')
            if client is not None:
                cmds.extend(['-c', client])
            popen = subprocess.Popen(cmds)
            info.popen = popen
            
            # call workers to start job
            for worker_watcher in self.nodes_watchers:
                client_call(worker_watcher, 'start_job', zip_filename, uncompress, ignore=True)
    
    def stop_job(self, job_real_name):
        if job_real_name not in self.running_jobs:
            return False
        job_info = self.running_jobs[job_real_name]
        
        try:
            client_call(job_info.job_master, 'stop', ignore=True)
        finally:
            for watcher in self.nodes_watchers.keys():
                client_call(watcher, 'kill', job_real_name, ignore=True)
            self.kill(job_real_name)
        
        return True
    
    def finish_job(self, job_real_name):
        del self.running_jobs[job_real_name]
    
    def clear_job(self, job_name):
        job_name = job_name.replace(' ', '_')
        path = os.path.join(self.job_dir, job_name)
        shutil.rmtree(path)
        
        for watcher in self.nodes_watchers:
            client_call(watcher, 'clear_job', ignore=True)
    
    def stop(self):
        # stop all jobs
        for job_name in self.running_jobs.keys():
            self.stop_job(job_name)
            
        for watcher in self.nodes_watchers:
            client_call(watcher, 'stop', ignore=True)
        self.finish()
        
    def kill(self, job_realname):
        if job_realname in self.running_jobs.keys():
            self.running_jobs[job_realname].popen.kill()
        
    def run(self):
        thread = self.start_check_worker()
        thread.join()
        
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.finish()
        
def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)
        
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Cola master watcher')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-i', '--ip', metavar='IP address', nargs='?',
                        default=None, const=None, 
                        help='IP Address to start')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()
    
    data_path = args.data
    if data_path is None:
        data_path = os.path.join(root_dir(), 'data')
    ip = args.ip
    force = args.force
        
    root = os.path.join(data_path, 'master', 'watcher')
    zip_dir = os.path.join(data_path, 'zip')
    job_dir = os.path.join(data_path, 'jobs')
    for dir_ in (root, zip_dir, job_dir):
        makedirs(dir_)
    
    with MasterWatcher(root, zip_dir, job_dir, ip_address=ip,
                       data_path=data_path, force=force) \
        as master_watcher:
        master_watcher.run()
########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-28

@author: Chine
'''

import os
import time
import threading
import signal
import random
import socket
import logging

from cola.core.mq import MessageQueue
from cola.core.bloomfilter import FileBloomFilter
from cola.core.rpc import client_call
from cola.core.utils import get_ip, root_dir
from cola.core.errors import ConfigurationError
from cola.core.logs import get_logger
from cola.core.utils import import_job
from cola.core.errors import LoginFailure
from cola.job.loader import JobLoader, LimitionJobLoader

MAX_THREADS_SIZE = 10
TIME_SLEEP = 10
BUDGET_REQUIRE = 10
MAX_ERROR_TIMES = 5

UNLIMIT_BLOOM_FILTER_CAPACITY = 1000000

class JobWorkerRunning(Exception): pass

class BasicWorkerJobLoader(JobLoader):
    def __init__(self, job, data_dir, context=None, logger=None,
                 local=None, nodes=None, copies=1, force=False):
        self.job = job
        ctx = context or self.job.context
        
        self.local = local
        if self.local is None:
            host, port = get_ip(), ctx.job.port
            self.local = '%s:%s' % (host, port)
        else:
            host, port = tuple(self.local.split(':', 1))
        self.nodes = nodes
        if self.nodes is None:
            self.nodes = [self.local]
            
        self.logger = logger
        self.info_logger = get_logger(
            name='cola_worker_info_%s'%self.job.real_name)
            
        super(BasicWorkerJobLoader, self).__init__(
            self.job, data_dir, self.local, 
            context=ctx, copies=copies, force=force)
        
        # instances count that run at the same time
        self.instances = max(min(self.ctx.job.instances, MAX_THREADS_SIZE), 1)
        # excecutings
        self.executings = []
        # exception times that continously throw
        self.error_times = 0
        # budget
        self.budget = 0
        
        # counter
        self.pages_size = 0
        
        # lock when not stopped
        self.stop_lock = threading.Lock()
        self.stop_lock.acquire()
        
        self.check()
        # init rpc server
        self.init_rpc_server()
        # init message queue
        self.init_mq()
        
        # register signal
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.rpc_server.register_function(self.stop, name='stop')
        self.rpc_server.register_function(self.add_node, name='add_node')
        self.rpc_server.register_function(self.remove_node, name='remove_node')
        self.rpc_server.register_function(self.run, name='run')
        self.rpc_server.register_function(self.pages, name='pages')
            
    def _init_bloom_filter(self):
        size = self.job.context.job.size
        base = 1 if not self.job.is_bundle else 1000 
        bloom_filter_file = os.path.join(self.root, 'bloomfilter')
        
        if not os.path.exists(bloom_filter_file):
            if size > 0:
                bloom_filter_size = size*10*base
            else:
                bloom_filter_size = UNLIMIT_BLOOM_FILTER_CAPACITY
        else:
            if size > 0:
                bloom_filter_size = size*2*base
            else:
                bloom_filter_size = UNLIMIT_BLOOM_FILTER_CAPACITY
        return FileBloomFilter(bloom_filter_file, bloom_filter_size)
            
    def init_mq(self):
        mq_store_dir = os.path.join(self.root, 'store')
        mq_backup_dir = os.path.join(self.root, 'backup')
        if not os.path.exists(mq_store_dir):
            os.makedirs(mq_store_dir)
        if not os.path.exists(mq_backup_dir):
            os.makedirs(mq_backup_dir)
            
        self.mq = MessageQueue(self.nodes, self.local, self.rpc_server,
            copies=self.copies)
        self.mq.init_store(mq_store_dir, mq_backup_dir, 
                           verify_exists_hook=self._init_bloom_filter())
    
    def _release_stop_lock(self):
        try:
            self.stop_lock.release()
        except:
            pass
        
    def check(self):
        env_legal = self.check_env(force=self.force)
        if not env_legal:
            raise JobWorkerRunning('There has been a running job worker.')
        
    def finish(self):
        if self.logger is not None:
            self.logger.info('Finish visiting pages count: %s' % self.pages_size)
        self.stopped = True
        self.mq.shutdown()
        try:
            for handler in self.logger.handlers:
                handler.close()
        finally:
            super(BasicWorkerJobLoader, self).finish()
        
    def complete(self, obj):
        if self.logger is not None:
            self.logger.info('Finish %s' % obj)
        if obj in self.executings:
            self.executings.remove(obj)
        
        if self.ctx.job.size <= 0:
            return True
        return False
            
    def error(self, obj):
        if obj in self.executings:
            self.executings.remove(obj)
        
    def stop(self):
        try:
            self.mq.put(self.executings, force=True)
            super(BasicWorkerJobLoader, self).stop()
        finally:
            self._release_stop_lock()
        
    def signal_handler(self, signum, frame):
        self.stop()
        
    def _login(self, opener):
        if self.job.login_hook is not None:
            if 'login' not in self.ctx.job or \
                not isinstance(self.ctx.job.login, list):
                raise ConfigurationError('If login_hook set, config files must contains `login`')
            kw = random.choice(self.ctx.job.login)
            login_result = self.job.login_hook(opener, **kw)
            if isinstance(login_result, tuple) and len(login_result) == 2:
                self.logger.error('login fail, reason: %s' % login_result[1])
                return login_result[0]
            elif not login_result:
                self.logger.error('login fail')
            return login_result
        return True
        
    def _log_error(self, obj, err):
        if self.logger is not None:
            self.logger.error('Error when get bundle: %s' % obj)
            self.logger.exception(err)
            
        if self.job.debug:
            raise err
        
    def _require_budget(self, count):
        raise NotImplementedError
    
    def pages(self):
        return self.pages_size
    
    def apply(self):
        raise NotImplementedError
    
    def _execute_bundle(self, obj, opener=None):
        bundle = self.job.unit_cls(obj)
        urls = bundle.urls()
        
        url = None
        try:
            while len(urls) > 0 and not self.stopped:
                url = urls.pop(0)
                self.info_logger.info('get %s url: %s' % (bundle.label, url))
                
                parser_cls, options = self.job.url_patterns.get_parser(url, options=True)
                if parser_cls is not None:
                    self._require_budget()
                    self.pages_size += 1
                    next_urls, bundles = parser_cls(opener, url, bundle=bundle, logger=self.logger, 
                                                    **options).parse()
                    next_urls = list(self.job.url_patterns.matches(next_urls))
                    next_urls.extend(urls)
                    urls = next_urls
                    if bundles:
                        self.mq.put([str(b) for b in bundles if b.force is False])
                        self.mq.put([str(b) for b in bundles if b.force is True], force=True)
                    if hasattr(opener, 'close'):
                        opener.close()
                        
            self.error_times = 0
        except LoginFailure, e:
            if not self._login(opener):
                self.error_times += 1
                self._log_error(obj, e)
                self.error(obj)
        except Exception, e:
            self.error_times += 1
            if self.logger is not None and url is not None:
                self.logger.error('Error when fetch url: %s' % url)
            self._log_error(obj, e)
            self.error(obj)
            
    def _execute_url(self, obj, opener=None):
        self._require_budget()
        try:
            parser_cls, options = self.job.url_patterns.get_parser(obj, options=True)
            if parser_cls is not None:
                self.pages_size += 1
                next_urls = parser_cls(opener, obj, logger=self.logger, **options).parse()
                next_urls = list(self.job.url_patterns.matches(next_urls))
                
                puts = []
                forces = []
                for url in next_urls:
                    if isinstance(url, basestring) or url.force is False:
                        puts.append(url)
                    else:
                        forces.append(url)
                self.mq.put(puts)
                self.mq.put(forces, force=True)
                if hasattr(opener, 'close'):
                    opener.close()
                
            self.error_times = 0
        except LoginFailure, e:
            if not self._login(opener):
                self.error_times += 1
                self._log_error(obj, e)
                self.error(obj)
        except Exception, e:
            self.error_times += 1
            self._log_error(obj, e)
            self.error(obj)
            
    def execute(self, obj, opener=None):
        '''
        return True means all finished
        '''
        # If reaches continous erros maxium
        if self.error_times >= MAX_ERROR_TIMES:
            return True
        
        if opener is None:
            opener = self.job.opener_cls()
            
        if self.job.is_bundle:
            self._execute_bundle(obj, opener=opener)
        else:
            self._execute_url(obj, opener=opener)
            
        return self.complete(obj)
        
    def remove_node(self, node):
        if self.mq is not None:
            self.mq.remove_node(node)
            
    def add_node(self, node):
        if self.mq is not None:
            self.mq.add_node(node)
            
    def _run(self, stop_when_finish=False):
        def _call(opener=None):
            if opener is None:
                opener = self.job.opener_cls()
            if not self._login(opener):
                return
            
            stopped = False
            while not self.stopped and not stopped:
                obj = self.mq.get()
                self.info_logger.info('start to get %s' % obj)
                if obj is None:
                    time.sleep(TIME_SLEEP)
                    continue
                
                if not self.apply():
                    return True
                
                self.executings.append(obj)
                stopped = self.execute(obj, opener=opener)
                
        try:
            threads = [threading.Thread(target=_call) for _ in range(self.instances)]
            if not stop_when_finish:
                threads.append(threading.Thread(target=self.stop_lock.acquire))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        finally:
            self.finish()
            
    def run(self):
        raise NotImplementedError
    
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.finish()
        
class StandaloneWorkerJobLoader(LimitionJobLoader, BasicWorkerJobLoader):
    def __init__(self, job, data_dir, master=None, local=None, nodes=None, 
                 context=None, logger=None, copies=1, force=False):
        BasicWorkerJobLoader.__init__(self, job, data_dir, context=context, logger=logger,
                                      local=local, nodes=nodes, copies=copies, force=force)
        LimitionJobLoader.__init__(self, self.job, context=context)
        
        log_level = logging.INFO if not job.debug else logging.DEBUG
        if self.logger is None:
            self.logger = get_logger(
                name='cola_worker_%s'%self.job.real_name,
                filename=os.path.join(self.root, 'job.log'),
                basic_level=log_level)
            
        self.init_rate_clear()
        
    def finish(self):
        LimitionJobLoader.finish(self)
        BasicWorkerJobLoader.finish(self)
                    
    def stop(self):
        LimitionJobLoader.stop(self)
        BasicWorkerJobLoader.stop(self)
        
    def complete(self, obj):
        BasicWorkerJobLoader.complete(self, obj)
        return LimitionJobLoader.complete(self, obj)
    
    def error(self, obj):
        LimitionJobLoader.error(self, obj)
        BasicWorkerJobLoader.error(self, obj)
            
    def _require_budget(self):
        if not self.rate_limit or self.stopped:
            return
        
        if self.budget > 0:
            self.budget -= 1
            return
        
        while self.budget == 0 and not self.stopped:
            self.budget = self.require(BUDGET_REQUIRE)
            if self.budget > 0:
                self.budget -= 1
                return
            
    def run(self, put_starts=True):
        if put_starts:
            self.mq.put(self.job.starts)
        self._run(stop_when_finish=True)
        
class WorkerJobLoader(BasicWorkerJobLoader):
    def __init__(self, job, data_dir, master, local=None, nodes=None, 
                 context=None, logger=None, copies=1, force=False):
        super(WorkerJobLoader, self).__init__(job, data_dir, context=context, logger=logger, 
                                              local=local, nodes=nodes, copies=copies, force=force)
        log_level = logging.INFO if not job.debug else logging.DEBUG
        if self.logger is None:
            self.logger = get_logger(
                name='cola_worker_%s'%self.job.real_name,
                filename=os.path.join(self.root, 'job.log'),
                server=master.split(':')[0],
                basic_level=log_level)
            
        self.master = master
        self.run_lock = threading.Lock()
        self.run_lock.acquire()
        
    def apply(self):
        return client_call(self.master, 'apply')
            
    def complete(self, obj):
        super(WorkerJobLoader, self).complete(obj)
        return client_call(self.master, 'complete', obj)
    
    def error(self, obj):
        super(WorkerJobLoader, self).error(obj)
        client_call(self.master, 'error', obj)
        
    def _require_budget(self):
        if self.ctx.job.limit == 0 or self.stopped:
            return
        
        if self.budget > 0:
            self.budget -= 1
            return
        
        while self.budget == 0 and not self.stopped:
            self.budget = client_call(self.master, 'require', BUDGET_REQUIRE)
            if self.budget > 0:
                self.budget -= 1
                return
        
    def ready_for_run(self):
        self.run_lock.acquire()
        self._run()
        
    def run(self):
        self.run_lock.release()
        
    def finish(self):
        super(WorkerJobLoader, self).finish()
        try:
            client_call(self.master, 'worker_finish', self.local)
        except socket.error:
            pass

def load_job(job_path, data_path=None, master=None, force=False):
    if not os.path.exists(job_path):
        raise ValueError('Job definition does not exist.')
        
    job = import_job(job_path)
    
    if data_path is None:
        data_path = os.path.join(root_dir(), 'data')
    root = os.path.join(
        data_path, 'worker', 'jobs', job.real_name)
    if not os.path.exists(root):
        os.makedirs(root)
    
    if master is None:
        with StandaloneWorkerJobLoader(job, root, force=force) as job_loader:
            job_loader.run()
    else:
        nodes = client_call(master, 'get_nodes')
        local = '%s:%s' % (get_ip(), job.context.job.port)
        client_call(master, 'ready', local)
        with WorkerJobLoader(job, root, master, local=local, nodes=nodes, force=force) \
            as job_loader:
            client_call(master, 'ready', local)
            job_loader.ready_for_run()
            
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Cola job loader')
    parser.add_argument('-j', '--job', metavar='job directory', required=True,
                        help='job directory to run')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-m', '--master', metavar='master job loader', nargs='?',
                        default=None, const=None,
                        help='master connected to(in the former of `ip:port`)')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()
    
    path = args.job
    data_path = args.data
    master = args.master
    force = args.force
    load_job(path, data_path=data_path, master=master, force=force)
########NEW FILE########
__FILENAME__ = recover
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Created on 2013-11-24

@author: Chine
'''

import os

from cola.core.utils import root_dir, import_job

def recover(job_path):
    job = import_job(job_path)

    data_path = os.path.join(root_dir(), 'data')
    root = os.path.join(data_path, 'worker', 'jobs', job.real_name)
    if os.path.exists(root):
        lock_path = os.path.join(root, 'lock')
        if os.path.exists(lock_path):
            os.remove(lock_path)

        def _recover_dir(dir_):
            for f in os.listdir(dir_):
                if f.endswith('.old'):
                    f_path = os.path.join(dir_, f)
                    os.remove(f_path)

            for f in os.listdir(dir_):
                if f == 'lock':
                    lock_f = os.path.join(dir_, f)
                    os.remove(lock_f)

                f_path = os.path.join(dir_, f)
                if os.path.isfile(f_path) and not f.endswith('.old'):
                    os.rename(f_path, f_path+'.old')

        mq_store_dir = os.path.join(root, 'store')
        mq_backup_dir = os.path.join(root, 'backup')
        if os.path.exists(mq_store_dir):
            _recover_dir(mq_store_dir)
        if os.path.exists(mq_backup_dir):
            _recover_dir(mq_backup_dir)
########NEW FILE########
__FILENAME__ = watcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-5

@author: Chine
'''

import threading
import time
import os
import subprocess
import shutil

from cola.core.rpc import ColaRPCServer, client_call, FileTransportServer
from cola.core.utils import get_ip, import_job, root_dir
from cola.core.zip import ZipHandler
from cola.core.config import main_conf

TIME_SLEEP = 20

class WorkerWatcherRunning(Exception): pass

class WorkerJobInfo(object):
    def __init__(self, port, popen):
        self.node = '%s:%s' % (get_ip(), port)
        self.popen = popen

class WorkerWatcher(object):
    def __init__(self, master, root, zip_dir, job_dir, 
                 data_path=None, force=False):
        self.master = master
        self.host = get_ip()
        self.port = main_conf.worker.port
        self.node = '%s:%s' % (self.host, self.port)
        
        self.root = root
        self.zip_dir = zip_dir
        self.job_dir = job_dir
        self.data_path = data_path
        self.force = force
        
        self.stopped = False
        
        self.running_jobs = {}
        
        self.check(force=force)
        self.init_rpc_server()
        
        self.rpc_server.register_function(self.stop, 'stop')
        self.rpc_server.register_function(self.kill, 'kill')
        self.rpc_server.register_function(self.start_job, 'start_job')
        self.rpc_server.register_function(self.clear_job, 'clear_job')
        self.set_file_receiver(self.zip_dir)
        
    def init_rpc_server(self):
        rpc_server = ColaRPCServer((self.host, self.port))
        thd = threading.Thread(target=rpc_server.serve_forever)
        thd.setDaemon(True)
        thd.start()
        self.rpc_server = rpc_server
        
    def check(self, force=False):
        if not self.check_env(force=force):
            raise WorkerWatcherRunning('There has been a running master watcher.')
        
    def check_env(self, force=False):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f) and not force:
            return False
        if os.path.exists(lock_f) and force:
            try:
                os.remove(lock_f)
            except:
                return False
            
        open(lock_f, 'w').close()
        return True
    
    def finish(self):
        lock_f = os.path.join(self.root, 'lock')
        if os.path.exists(lock_f):
            os.remove(lock_f)
        self.rpc_server.shutdown()
        self.stopped = True
        
    def set_file_receiver(self, base_dir):
        serv = FileTransportServer(self.rpc_server, base_dir)
        return serv
    
    def register_heartbeat(self):
        client_call(self.master, 'register_heartbeat', self.node)
        
    def start_job(self, zip_filename, uncompress=True):
        if uncompress:
            zip_file = os.path.join(self.zip_dir, zip_filename)
            job_dir = ZipHandler.uncompress(zip_file, self.job_dir)
        else:
            job_dir = os.path.join(self.job_dir, zip_filename.rsplit('.', 1)[0])
            
        job = import_job(job_dir)
        
        master_port = job.context.job.master_port
        master = '%s:%s' % (self.master.split(':')[0], master_port)
        dirname = os.path.dirname(os.path.abspath(__file__))
        f = os.path.join(dirname, 'loader.py')
        
        cmds = ['python', f, '-j', job_dir, '-m', master]
        if self.data_path is not None:
            cmds.extend(['-d', self.data_path])
        if self.force:
            cmds.append('-f')
        popen = subprocess.Popen(cmds)
        self.running_jobs[job.real_name] = WorkerJobInfo(job.context.job.port, popen)
    
    def clear_job(self, job_name):
        job_name = job_name.replace(' ', '_')
        shutil.rmtree(os.path.join(self.job_dir, job_name))
        
    def kill(self, job_name):
        if job_name in self.running_jobs:
            self.running_jobs[job_name].popen.kill()
        
    def run(self):
        def _start():
            while not self.stopped:
                self.register_heartbeat()
                time.sleep(TIME_SLEEP)
        
        thread = threading.Thread(target=_start)
        thread.setDaemon(True)
        thread.start()
        thread.join()
        
    def stop(self):
        self.finish()
        
    def __enter__(self):
        return self
    
    def __exit__(self, type_, value, traceback):
        self.finish()
        
def makedirs(dir_):
    if not os.path.exists(dir_):
        os.makedirs(dir_)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Cola worker watcher')
    parser.add_argument('-m', '--master', metavar='master watcher', required=True,
                        help='master connected to(in the former of `ip:port` or `ip`)')
    parser.add_argument('-d', '--data', metavar='data root directory', nargs='?',
                        default=None, const=None, 
                        help='root directory to put data')
    parser.add_argument('-f', '--force', metavar='force start', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()
    
    data_path = args.data
    if data_path is None:
        data_path = os.path.join(root_dir(), 'data')
    force = args.force
    master = args.master
    if ':' not in master:
        master = '%s:%s' % (master, main_conf.master.port)
        
    root = os.path.join(data_path, 'worker', 'watcher')
    zip_dir = os.path.join(data_path, 'zip')
    job_dir = os.path.join(data_path, 'jobs')
    for dir_ in (root, zip_dir, job_dir):
        makedirs(dir_)
    
    with WorkerWatcher(master, root, zip_dir, job_dir, data_path=data_path, force=force) \
        as master_watcher:
        master_watcher.run()
########NEW FILE########
__FILENAME__ = stop
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-22

@author: Chine
'''

import os
import socket

from cola.core.rpc import client_call
from cola.core.utils import get_ip
from cola.core.config import Config
from cola.core.logs import get_logger
from cola.worker.recover import recover

logger = get_logger(name='generic_stop')

get_user_conf = lambda s: os.path.join(os.path.dirname(os.path.abspath(__file__)), s)
user_conf = get_user_conf('test.yaml')
if not os.path.exists(user_conf):
    user_conf = get_user_conf('generic.yaml')
user_config = Config(user_conf)

if __name__ == '__main__':
    ip, port = get_ip(), getattr(user_config.job, 'port')
    logger.info('Trying to stop single running worker')
    try:
        client_call('%s:%s' % (ip, port), 'stop')
    except socket.error:
        stop = raw_input("Force to stop? (y or n) ").strip()
        if stop == 'y' or stop == 'yes':
            job_path = os.path.split(os.path.abspath(__file__))[0]
            recover()
        else:
            print 'ignore'
    logger.info('Successfully stopped single running worker')
########NEW FILE########
__FILENAME__ = bundle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-8

@author: Chine
'''

import time

from cola.core.unit import Bundle

class WeiboUserBundle(Bundle):
    def __init__(self, uid):
        super(WeiboUserBundle, self).__init__(uid)
        self.uid = uid
        self.exists = True
        
        self.last_error_page = None
        self.last_error_page_times = 0
        
        self.weibo_user = None
        self.last_update = None
        self.newest_mids = []
        self.current_mblog = None
        
    def urls(self):
        start = int(time.time() * (10**6))
        return [
            'http://weibo.com/%s/follow' % self.uid,
            'http://weibo.com/aj/mblog/mbloglist?uid=%s&_k=%s' % (self.uid, start),
            'http://weibo.com/%s/info' % self.uid,
            # remove because some user's link has been http://weibo.com/uid/follow?relate=fans
            # 'http://weibo.com/%s/fans' % self.uid
        ]
########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-9

@author: Chine
'''

import os

from cola.core.config import Config

base = os.path.dirname(os.path.abspath(__file__))
user_conf = os.path.join(base, 'test.yaml')
if not os.path.exists(user_conf):
    user_conf = os.path.join(base, 'weibo.yaml')
user_config = Config(user_conf)

starts = [str(start.uid) for start in user_config.job.starts]

mongo_host = user_config.job.mongo.host
mongo_port = user_config.job.mongo.port
db_name = user_config.job.db

try:
    shard_key = user_config.job.mongo.shard_key
    shard_key = tuple([itm['key'] for itm in shard_key])
except AttributeError:
    shard_key = tuple()

instances = user_config.job.instances

fetch_forward = user_config.job.fetch.forward
fetch_comment = user_config.job.fetch.comment
fetch_like = user_config.job.fetch.like
########NEW FILE########
__FILENAME__ = login
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-8

@author: Chine
'''

import urllib
import base64
import binascii
import re
import json

from cola.core.errors import DependencyNotInstalledError,\
                             LoginFailure

try:
    import rsa
except ImportError:
    raise DependencyNotInstalledError("rsa")

class WeiboLoginFailure(LoginFailure): pass

class WeiboLogin(object):
    def __init__(self, opener, username, passwd):
        self.opener = opener
        
        self.username = username
        self.passwd = passwd
        
    def get_user(self, username):
        username = urllib.quote(username)
        return base64.encodestring(username)[:-1]
    
    def get_passwd(self, passwd, pubkey, servertime, nonce):
        key = rsa.PublicKey(int(pubkey, 16), int('10001', 16))
        message = str(servertime) + '\t' + str(nonce) + '\n' + str(passwd)
        passwd = rsa.encrypt(message, key)
        return binascii.b2a_hex(passwd)
    
    def prelogin(self):
        username = self.get_user(self.username)
        prelogin_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=sso&callback=sinaSSOController.preloginCallBack&su=%s&rsakt=mod&client=ssologin.js(v1.4.5)' % username
        data = self.opener.open(prelogin_url)
        regex = re.compile('\((.*)\)')
        try:
            json_data = regex.search(data).group(1)
            data = json.loads(json_data)
            
            return str(data['servertime']), data['nonce'], \
                data['pubkey'], data['rsakv']
        except:
            raise WeiboLoginFailure
        
    def login(self):
        login_url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.5)'
        
        try:
            servertime, nonce, pubkey, rsakv = self.prelogin()
            postdata = {
                'entry': 'weibo',
                'gateway': '1',
                'from': '',
                'savestate': '7',
                'userticket': '1',
                'ssosimplelogin': '1',
                'vsnf': '1',
                'vsnval': '',
                'su': self.get_user(self.username),
                'service': 'miniblog',
                'servertime': servertime,
                'nonce': nonce,
                'pwencode': 'rsa2',
                'sp': self.get_passwd(self.passwd, pubkey, servertime, nonce),
                'encoding': 'UTF-8',
                'prelt': '115',
                'rsakv' : rsakv,
                'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&amp;callback=parent.sinaSSOController.feedBackUrlCallBack',
                'returntype': 'META'
            }
            postdata = urllib.urlencode(postdata)
            text = self.opener.open(login_url, postdata)

            # Fix for new login changed since about 2014-3-28
            ajax_url_regex = re.compile('location\.replace\(\'(.*)\'\)')
            matches = ajax_url_regex.search(text)
            if matches is not None:
                ajax_url = matches.group(1)
                text = self.opener.open(ajax_url)
            
            regex = re.compile('\((.*)\)')
            json_data = json.loads(regex.search(text).group(1))
            result = json_data['result'] == True
            if result is False and 'reason' in json_data:
                return result, json_data['reason']
            return result
        except WeiboLoginFailure:
            return False

########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-8

@author: Chine
'''

import time
import json
import urllib
import re
from urllib2 import URLError
from datetime import datetime, timedelta
from threading import Lock

from cola.core.parsers import Parser
from cola.core.utils import urldecode, beautiful_soup
from cola.core.errors import DependencyNotInstalledError
from cola.core.logs import get_logger

from login import WeiboLoginFailure
from bundle import WeiboUserBundle
from storage import DoesNotExist, Q, WeiboUser, Friend,\
                    MicroBlog, Geo, UserInfo, WorkInfo, EduInfo,\
                    Comment, Forward, Like, ValidationError
from conf import fetch_forward, fetch_comment, fetch_like

try:
    from dateutil.parser import parse
except ImportError:
    raise DependencyNotInstalledError('python-dateutil')

TIMEOUT = 30.0

class WeiboParser(Parser):
    def __init__(self, opener=None, url=None, bundle=None, **kwargs):
        super(WeiboParser, self).__init__(opener=opener, url=url, **kwargs)
        self.bundle = bundle
        self.uid = bundle.label
        self.opener.set_default_timeout(TIMEOUT)
        if not hasattr(self, 'logger') or self.logger is None:
            self.logger = get_logger(name='weibo_parser')
    
    def _check_url(self, dest_url, src_url):
        return dest_url.split('?')[0] == src_url.split('?')[0]
    
    def check(self, url, br):
        dest_url = br.geturl()
        if not self._check_url(dest_url, url):
            if dest_url.startswith('http://weibo.com/login.php'):
                raise WeiboLoginFailure('Weibo not login or login expired')
            if dest_url.startswith('http://weibo.com/sorry?usernotexists'):
                self.bundle.exists = False
                return False
        return True
    
    def get_weibo_user(self):
        if self.bundle.weibo_user is not None:
            return self.bundle.weibo_user
        
        try:
            self.bundle.weibo_user = getattr(WeiboUser, 'objects').get(uid=self.uid)
        except DoesNotExist:
            self.bundle.weibo_user = WeiboUser(uid=self.uid)
            self.bundle.weibo_user.save()
        return self.bundle.weibo_user
    
    def _error(self, url, e):
        if self.bundle.last_error_page == url:
            self.bundle.last_error_page_times += 1
        else:
            self.bundle.last_error_page = url
            self.bundle.last_error_page_times = 0
            
        if self.bundle.last_error_page_times >= 15:
            raise e
        return [url, ], []

class MicroBlogParser(WeiboParser):
    def parse(self, url=None):
        if self.bundle.exists == False:
            return [], []
        
        url = url or self.url
        params = urldecode(url)
        br = self.opener.browse_open(url)
        self.logger.debug('load %s finish' % url)
        
        if not self.check(url, br):
            return [], []
            
        weibo_user = self.get_weibo_user()
        
        params['_t'] = 0
        params['__rnd'] = str(int(time.time() * 1000))
        page = int(params.get('page', 1))
        pre_page = int(params.get('pre_page', 0))
        count = 15
        if 'pagebar' not in params:
            params['pagebar'] = '0'
            pre_page += 1
        elif params['pagebar'] == '0':
            params['pagebar'] = '1'
        elif params['pagebar'] == '1':
            del params['pagebar']
            pre_page = page
            page += 1
            count = 50
        params['count'] = count
        params['page'] = page
        params['pre_page'] = pre_page
        
        data = json.loads(br.response().read())['data']
        soup = beautiful_soup(data)
        finished = False
        
        divs = soup.find_all('div', attrs={'class': 'WB_feed_type'},  mid=True)
        max_id = None
        next_urls = []
        for div in divs:
            mid = div['mid']
            if len(mid) == 0:
                continue
            max_id = mid
            
            if 'end_id' not in params:
                params['end_id'] = mid
            if mid in weibo_user.newest_mids:
                finished = True
                break
            if len(self.bundle.newest_mids) < 3:
                self.bundle.newest_mids.append(mid)
            
            try:
                mblog = getattr(MicroBlog, 'objects').get(Q(mid=mid)&Q(uid=self.uid))
            except DoesNotExist:
                mblog = MicroBlog(mid=mid, uid=self.uid)
            content_div = div.find('div', attrs={
                'class': 'WB_text', 
                'node-type': 'feed_list_content'
            })
            for img in content_div.find_all("img", attrs={'type': 'face'}):
                img.replace_with(img['title']);
            mblog.content = content_div.text
            is_forward = div.get('isforward') == '1'
            if is_forward:
                mblog.omid = div['omid']
                name_a = div.find('a', attrs={
                    'class': 'WB_name', 
                    'node-type': 'feed_list_originNick'
                })
                text_a = div.find('div', attrs={
                    'class': 'WB_text',
                    'node-type': 'feed_list_reason'
                })
                if name_a is not None and text_a is not None:
                    mblog.forward = '%s: %s' % (
                        name_a.text,
                        text_a.text
                    )
            mblog.created = parse(div.select('a.S_link2.WB_time')[0]['title'])
            
            if self.bundle.last_update is None or mblog.created > self.bundle.last_update:
                self.bundle.last_update = mblog.created
            if weibo_user.last_update is not None and \
                mblog.created <= weibo_user.last_update:
                finished = True
                break

            func_div = div.find_all('div', 'WB_func')[-1]
            action_type_re = lambda t: re.compile("^(feed_list|fl)_%s$" % t)
            
            likes = func_div.find('a', attrs={'action-type': action_type_re("like")}).text
            likes = likes.strip('(').strip(')')
            likes = 0 if len(likes) == 0 else int(likes)
            mblog.n_likes = likes
            forwards = func_div.find('a', attrs={'action-type': action_type_re("forward")}).text
            if '(' not in forwards:
                mblog.n_forwards = 0
            else:
                mblog.n_forwards = int(forwards.strip().split('(', 1)[1].strip(')'))
            comments = func_div.find('a', attrs={'action-type': action_type_re('comment')}).text
            if '(' not in comments:
                mblog.n_comments = 0
            else:
                mblog.n_comments = int(comments.strip().split('(', 1)[1].strip(')'))
                
            # fetch geo info
            map_info = div.find("div", attrs={'class': 'map_data'})
            if map_info is not None:
                geo = Geo()
                geo.location = map_info.text.split('-')[0].strip()
                geo_info = urldecode("?"+map_info.find('a')['action-data'])['geo']
                geo.longtitude, geo.latitude = tuple([float(itm) for itm in geo_info.split(',', 1)])
                mblog.geo = geo
            
            # fetch forwards and comments
            if fetch_forward or fetch_comment or fetch_like:
                query = {'id': mid, '_t': 0, '__rnd': int(time.time()*1000)}
                query_str = urllib.urlencode(query)
                if fetch_forward and mblog.n_forwards > 0:
                    forward_url = 'http://weibo.com/aj/mblog/info/big?%s' % query_str
                    next_urls.append(forward_url)
                if fetch_comment and mblog.n_comments > 0:
                    comment_url = 'http://weibo.com/aj/comment/big?%s' % query_str
                    next_urls.append(comment_url)
                if fetch_like and mblog.n_likes > 0:
                    query = {'mid': mid, '_t': 0, '__rnd': int(time.time()*1000)}
                    query_str = urllib.urlencode(query)
                    like_url = 'http://weibo.com/aj/like/big?%s' % query_str
                    next_urls.append(like_url)
            
            mblog.save()
        
        if 'pagebar' in params:
            params['max_id'] = max_id
        else:
            del params['max_id']
        self.logger.debug('parse %s finish' % url)
                
        # if not has next page
        if len(divs) == 0 or finished:
            weibo_user = self.get_weibo_user()
            for mid in self.bundle.newest_mids:
                if mid not in weibo_user.newest_mids:
                    weibo_user.newest_mids.append(mid)
            while len(weibo_user.newest_mids) > 3:
                weibo_user.newest_mids.pop()
            weibo_user.last_update = self.bundle.last_update
            weibo_user.save()
            return [], []
        
        next_urls.append('%s?%s'%(url.split('?')[0], urllib.urlencode(params)))
        return next_urls, []
    
class ForwardCommentLikeParser(WeiboParser):
    strptime_lock = Lock()
    
    def _strptime(self, string, format_):
        self.strptime_lock.acquire()
        try:
            return datetime.strptime(string, format_)
        finally:
            self.strptime_lock.release()
        
    def parse_datetime(self, dt_str):
        dt = None
        if u'秒' in dt_str:
            sec = int(dt_str.split(u'秒', 1)[0].strip())
            dt = datetime.now() - timedelta(seconds=sec)
        elif u'分钟' in dt_str:
            sec = int(dt_str.split(u'分钟', 1)[0].strip()) * 60
            dt = datetime.now() - timedelta(seconds=sec)
        elif u'今天' in dt_str:
            dt_str = dt_str.replace(u'今天', datetime.now().strftime('%Y-%m-%d'))
            dt = self._strptime(dt_str, '%Y-%m-%d %H:%M')
        elif u'月' in dt_str and u'日' in dt_str:
            this_year = datetime.now().year
            date_str = '%s %s' % (this_year, dt_str)
            if isinstance(date_str, unicode):
                date_str = date_str.encode('utf-8')
            dt = self._strptime(date_str, '%Y %m月%d日 %H:%M')
        else:
            dt = parse(dt_str)
        return dt
    
    def parse(self, url=None):
        if self.bundle.exists == False:
            return [], []
        
        url = url or self.url
        br = None
        jsn = None
        try:
            br = self.opener.browse_open(url)
            self.logger.debug('load %s finish' % url)
            jsn = json.loads(br.response().read())
        except (ValueError, URLError) as e:
            return self._error(url, e)
        
        soup = beautiful_soup(jsn['data']['html'])
        current_page = jsn['data']['page']['pagenum']
        n_pages = jsn['data']['page']['totalpage']
        
        if not self.check(url, br):
            return [], []
        
        decodes = urldecode(url)
        mid = decodes.get('id', decodes.get('mid'))
        
        mblog = self.bundle.current_mblog
        if mblog is None or mblog.mid != mid:
            try:
                mblog = getattr(MicroBlog, 'objects').get(Q(mid=mid)&Q(uid=self.uid))
            except DoesNotExist:
                mblog = MicroBlog(mid=mid, uid=self.uid)
                mblog.save()
        
        def set_instance(instance, dl):
            instance.avatar = dl.find('dt').find('img')['src']
            date = dl.find('dd').find(attrs={'class': 'S_txt2'}).text
            date = date.strip().strip('(').strip(')')
            instance.created = self.parse_datetime(date)
            for div in dl.find_all('div'): div.extract()
            for span in dl.find_all('span'): span.extract()
            instance.content = dl.text.strip()
        
        if url.startswith('http://weibo.com/aj/comment'):
            dls = soup.find_all('dl', mid=True)
            for dl in dls:
                uid = dl.find('a', usercard=True)['usercard'].split("id=", 1)[1]
                comment = Comment(uid=uid)
                set_instance(comment, dl)
                
                mblog.comments.append(comment)
        elif url.startswith('http://weibo.com/aj/mblog/info'):
            dls = soup.find_all('dl', mid=True)
            for dl in dls:
                forward_again_a = dl.find('a', attrs={'action-type': re.compile("^(feed_list|fl)_forward$")})
                uid = urldecode('?%s' % forward_again_a['action-data'])['uid']
                forward = Forward(uid=uid, mid=dl['mid'])
                set_instance(forward, dl)
                
                mblog.forwards.append(forward)
        elif url.startswith('http://weibo.com/aj/like'):
            lis = soup.find_all('li', uid=True)
            for li in lis:
                like = Like(uid=li['uid'])
                like.avatar = li.find('img')['src']
                
                mblog.likes.append(like)
        
        try:
            mblog.save()
            self.logger.debug('parse %s finish' % url)
        except ValidationError, e:
            return self._error(url, e)
        
        if current_page >= n_pages:
            return [], []
        
        params = urldecode(url)
        new_params = urldecode('?page=%s'%(current_page+1))
        params.update(new_params)
        params['__rnd'] = int(time.time()*1000)
        next_page = '%s?%s' % (url.split('?')[0] , urllib.urlencode(params))
        return [next_page, ], []
    
class UserInfoParser(WeiboParser):
    def parse(self, url=None):
        if self.bundle.exists == False:
            return [], []
        
        url = url or self.url
        br = self.opener.browse_open(url)
        self.logger.debug('load %s finish' % url)
        soup = beautiful_soup(br.response().read())
        
        if not self.check(url, br):
            return [], []
        
        weibo_user = self.get_weibo_user()
        info = weibo_user.info
        if info is None:
            weibo_user.info = UserInfo()
            
        profile_div = None
        career_div = None
        edu_div = None
        tags_div = None
        for script in soup.find_all('script'):
            text = script.text
            if text.startswith('FM.view'):
                text = text.strip().replace(';', '').replace('FM.view(', '')[:-1]
                data = json.loads(text)
                domid = data['domid']
                if domid.startswith('Pl_Official_LeftInfo__'):
                    info_soup = beautiful_soup(data['html'])
                    info_div = info_soup.find('div', attrs={'class': 'profile_pinfo'})
                    for block_div in info_div.find_all('div', attrs={'class': 'infoblock'}):
                        block_title = block_div.find('form').text.strip()
                        if block_title == u'基本信息':
                            profile_div = block_div
                        elif block_title == u'工作信息':
                            career_div = block_div
                        elif block_title == u'教育信息':
                            edu_div = block_div
                        elif block_title == u'标签信息':
                            tags_div = block_div
                elif domid == 'Pl_Official_Header__1':
                    header_soup = beautiful_soup(data['html'])
                    weibo_user.info.avatar = header_soup.find('div', attrs={'class': 'pf_head_pic'})\
                                                .find('img')['src']
            elif 'STK' in text:
                text = text.replace('STK && STK.pageletM && STK.pageletM.view(', '')[:-1]
                data = json.loads(text)
                pid = data['pid']
                if pid == 'pl_profile_infoBase':
                    profile_div = beautiful_soup(data['html'])
                elif pid == 'pl_profile_infoCareer':
                    career_div = beautiful_soup(data['html'])
                elif pid == 'pl_profile_infoEdu':
                    edu_div = beautiful_soup(data['html'])
                elif pid == 'pl_profile_infoTag':
                    tags_div = beautiful_soup(data['html'])
                elif pid == 'pl_profile_photo':
                    soup = beautiful_soup(data['html'])
                    weibo_user.info.avatar = soup.find('img')['src']
        
        profile_map = {
            u'昵称': {'field': 'nickname'},
            u'所在地': {'field': 'location'},
            u'性别': {'field': 'sex', 
                    'func': lambda s: True if s == u'男' else False},
            u'生日': {'field': 'birth'},
            u'博客': {'field': 'blog'},
            u'个性域名': {'field': 'site'},
            u'简介': {'field': 'intro'},
            u'邮箱': {'field': 'email'},
            u'QQ': {'field': 'qq'},
            u'MSN': {'field': 'msn'}
        }
        if profile_div is not None:
            for div in profile_div.find_all(attrs={'class': 'pf_item'}):
                k = div.find(attrs={'class': 'label'}).text.strip()
                v = div.find(attrs={'class': 'con'}).text.strip()
                if k in profile_map:
                    if k == u'个性域名' and '|' in v:
                        v = v.split('|')[1].strip()
                    func = (lambda s: s) \
                            if 'func' not in profile_map[k] \
                            else profile_map[k]['func']
                    v = func(v)
                    setattr(weibo_user.info, profile_map[k]['field'], v)
                
        weibo_user.info.work = []
        if career_div is not None:
            for div in career_div.find_all(attrs={'class': 'con'}):
                work_info = WorkInfo()
                ps = div.find_all('p')
                for p in ps:
                    a = p.find('a')
                    if a is not None:
                        work_info.name = a.text
                        text = p.text
                        if '(' in text:
                            work_info.date = text.strip().split('(')[1].strip(')')
                    else:
                        text = p.text
                        if text.startswith(u'地区：'):
                            work_info.location = text.split(u'：', 1)[1]
                        elif text.startswith(u'职位：'):
                            work_info.position = text.split(u'：', 1)[1]
                        else:
                            work_info.detail = text
                weibo_user.info.work.append(work_info)
            
        weibo_user.info.edu = []
        if edu_div is not None:
            for div in edu_div.find_all(attrs={'class': 'con'}):
                edu_info = EduInfo()
                ps = div.find_all('p')
                for p in ps:
                    a = p.find('a')
                    text = p.text
                    if a is not None:
                        edu_info.name = a.text
                        if '(' in text:
                            edu_info.date = text.strip().split('(')[1].strip(')')
                    else:
                        edu_info.detail = text
                weibo_user.info.edu.append(edu_info)
                    
        weibo_user.info.tags = []
        if tags_div is not None:
            for div in tags_div.find_all(attrs={'class': 'con'}):
                for a in div.find_all('a'):
                    weibo_user.info.tags.append(a.text)
                
        weibo_user.save()
        self.logger.debug('parse %s finish' % url)
        return [], []
    
class UserFriendParser(WeiboParser):
    def parse(self, url=None):
        if self.bundle.exists == False:
            return [], []
        
        url = url or self.url
        
        br, soup = None, None
        try:
            br = self.opener.browse_open(url)
            self.logger.debug('load %s finish' % url)
            soup = beautiful_soup(br.response().read())
        except Exception, e:
            return self._error(url, e)
        
        if not self.check(url, br):
            return [], []
        
        weibo_user = self.get_weibo_user()
        
        html = None
        decodes = urldecode(url)
        is_follow = True
        is_new_mode = False
        for script in soup.find_all('script'):
            text = script.text
            if text.startswith('FM.view'):
                text = text.strip().replace(';', '').replace('FM.view(', '')[:-1]
                data = None
                try:
                    data = json.loads(text)
                except ValueError, e:
                    return self._error(url, e)
                domid = data['domid']
                if domid.startswith('Pl_Official_LeftHisRelation__'):
                    html = beautiful_soup(data['html'])
                if 'relate' in decodes and decodes['relate'] == 'fans':
                    is_follow = False
                is_new_mode = True
            elif 'STK' in text:
                text = text.replace('STK && STK.pageletM && STK.pageletM.view(', '')[:-1]
                data = json.loads(text)
                if data['pid'] == 'pl_relation_hisFollow' or \
                    data['pid'] == 'pl_relation_hisFans':
                    html = beautiful_soup(data['html'])
                if data['pid'] == 'pl_relation_hisFans':
                    is_follow = False    
        
        bundles = []
        ul = None
        try:
            ul = html.find(attrs={'class': 'cnfList', 'node-type': 'userListBox'})
        except AttributeError, e:
            if br.geturl().startswith('http://e.weibo.com'):
                return [], []
            return self._error(url, e)
        if ul is None:
            urls = []
            if is_follow is True:
                if is_new_mode:
                    urls.append('http://weibo.com/%s/follow?relate=fans' % self.uid)
                else:
                    urls.append('http://weibo.com/%s/fans' % self.uid)
            return urls, bundles
        
        current_page = decodes.get('page', 1)
        if current_page == 1:
            if is_follow:
                weibo_user.follows = []
            else:
                weibo_user.fans = []
        for li in ul.find_all(attrs={'class': 'S_line1', 'action-type': 'itemClick'}):
            data = dict([l.split('=') for l in li['action-data'].split('&')])
            
            friend = Friend()
            friend.uid = data['uid']
            friend.nickname = data['fnick']
            friend.sex = True if data['sex'] == u'm' else False
            
            bundles.append(WeiboUserBundle(str(friend.uid)))
            if is_follow:
                weibo_user.follows.append(friend)
            else:
                weibo_user.fans.append(friend)
                
        weibo_user.save()
        self.logger.debug('parse %s finish' % url)
        
        urls = []
        pages = html.find('div', attrs={'class': 'W_pages', 'node-type': 'pageList'})
        if pages is not None:
            a = pages.find_all('a')
            if len(a) > 0:
                next_ = a[-1]
                if next_['class'] == ['W_btn_c']:
                    decodes['page'] = int(decodes.get('page', 1)) + 1
                    query_str = urllib.urlencode(decodes)
                    url = '%s?%s' % (url.split('?')[0], query_str)
                    urls.append(url)
                    
                    return urls, bundles
        
        if is_follow is True:
            if is_new_mode:
                urls.append('http://weibo.com/%s/follow?relate=fans' % self.uid)
            else:
                urls.append('http://weibo.com/%s/fans' % self.uid)
        
        return urls, bundles

########NEW FILE########
__FILENAME__ = stop
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-22

@author: Chine
'''

import socket
import os

from cola.core.rpc import client_call
from cola.core.utils import get_ip
from cola.core.logs import get_logger
from cola.worker.recover import recover

from conf import user_config

logger = get_logger(name='sina_stop')

if __name__ == '__main__':
    ip, port = get_ip(), getattr(user_config.job, 'port')
    logger.info('Trying to stop single running worker')
    try:
        client_call('%s:%s' % (ip, port), 'stop')
    except socket.error:
        stop = raw_input("Force to stop? (y or n) ").strip()
        if stop == 'y' or stop == 'yes':
            job_path = os.path.split(os.path.abspath(__file__))[0]
            recover(job_path)
        else:
            print 'ignore'
    logger.info('Successfully stopped single running worker')

########NEW FILE########
__FILENAME__ = storage
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-9

@author: Chine
'''

from cola.core.errors import DependencyNotInstalledError

from conf import mongo_host, mongo_port, db_name, shard_key

try:
    from mongoengine import connect, Document, EmbeddedDocument, \
                            DoesNotExist, Q, \
                            StringField, DateTimeField, EmailField, \
                            BooleanField, URLField, IntField, FloatField, \
                            ListField, EmbeddedDocumentField, \
                            ValidationError
except ImportError:
    raise DependencyNotInstalledError('mongoengine')

connect(db_name, host=mongo_host, port=mongo_port)

DoesNotExist = DoesNotExist
Q = Q
ValidationError = ValidationError

class Forward(EmbeddedDocument):
    mid = StringField(required=True)
    uid = StringField(required=True)
    avatar = URLField()
    content = StringField()
    created = DateTimeField()

class Comment(EmbeddedDocument):
    uid = StringField(required=True)
    avatar = URLField()
    content = StringField()
    created = DateTimeField()
    
class Like(EmbeddedDocument):
    uid = StringField(required=True)
    avatar = URLField()
    
class Geo(EmbeddedDocument):
    longtitude = FloatField()
    latitude = FloatField()
    location = StringField()

class MicroBlog(Document):
    mid = StringField(required=True)
    uid = StringField(required=True)
    content = StringField()
    omid = StringField()
    forward = StringField()
    created = DateTimeField()
    geo = EmbeddedDocumentField(Geo)
    
    n_likes = IntField()
    likes = ListField(EmbeddedDocumentField(Like))
    n_forwards = IntField()
    forwards = ListField(EmbeddedDocumentField(Forward)) 
    n_comments = IntField()
    comments = ListField(EmbeddedDocumentField(Comment))
    
    meta = {
        'indexes': [
            {'fields': ['mid', 'uid']}
        ]
    }
    
class EduInfo(EmbeddedDocument):
    name = StringField()
    date = StringField()
    detail = StringField()
    
class WorkInfo(EmbeddedDocument):
    name = StringField()
    date = StringField()
    location = StringField()
    position = StringField()
    detail = StringField()
    
class UserInfo(EmbeddedDocument):
    nickname = StringField()
    avatar = URLField()
    location = StringField()
    sex = BooleanField()
    birth = StringField()
    blog = URLField()
    site = URLField()
    intro = StringField()
    
    email = EmailField()
    qq = StringField()
    msn = StringField()
    
    edu = ListField(EmbeddedDocumentField(EduInfo))
    work = ListField(EmbeddedDocumentField(WorkInfo))
    tags = ListField(StringField())
    
class Friend(EmbeddedDocument):
    uid = StringField()
    nickname = StringField()
    sex = BooleanField
    
class WeiboUser(Document):
    uid = StringField(required=True)
    last_update = DateTimeField()
    newest_mids = ListField(StringField())
    
    info = EmbeddedDocumentField(UserInfo)
    follows = ListField(EmbeddedDocumentField(Friend))
    fans = ListField(EmbeddedDocumentField(Friend))
    
    meta = {
        'shard_key': shard_key
    }

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-7-6

@author: Chine
'''

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62_encode(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def base62_decode(string, alphabet=ALPHABET):
    """Decode a Base X encoded string into the number

    Arguments:
    - `string`: The encoded string
    - `alphabet`: The alphabet to use for encoding
    """
    base = len(alphabet)
    strlen = len(string)
    num = 0

    idx = 0
    for char in string:
        power = (strlen - (idx + 1))
        num += alphabet.index(char) * (base ** power)
        idx += 1

    return num

def url_to_mid(url):
    '''
    >>> url_to_mid('z0JH2lOMb')
    3501756485200075L
    >>> url_to_mid('z0Ijpwgk7')
    3501703397689247L
    >>> url_to_mid('z0IgABdSn')
    3501701648871479L
    >>> url_to_mid('z08AUBmUe')
    3500330408906190L
    >>> url_to_mid('z06qL6b28')
    3500247231472384L
    >>> url_to_mid('yCtxn8IXR')
    3491700092079471L
    >>> url_to_mid('yAt1n2xRa')
    3486913690606804L
    '''
    url = str(url)[::-1]
    size = len(url) / 4 if len(url) % 4 == 0 else len(url) / 4 + 1
    result = []
    for i in range(size):
        s = url[i * 4: (i + 1) * 4][::-1]
        s = str(base62_decode(str(s)))
        s_len = len(s)
        if i < size - 1 and s_len < 7:
            s = (7 - s_len) * '0' + s
        result.append(s)
    result.reverse()
    return int(''.join(result))

def mid_to_url(midint):
    '''
    >>> mid_to_url(3501756485200075)
    'z0JH2lOMb'
    >>> mid_to_url(3501703397689247)
    'z0Ijpwgk7'
    >>> mid_to_url(3501701648871479)
    'z0IgABdSn'
    >>> mid_to_url(3500330408906190)
    'z08AUBmUe'
    >>> mid_to_url(3500247231472384)
    'z06qL6b28'
    >>> mid_to_url(3491700092079471)
    'yCtxn8IXR'
    >>> mid_to_url(3486913690606804)
    'yAt1n2xRa'
    '''
    midint = str(midint)[::-1]
    size = len(midint) / 7 if len(midint) % 7 == 0 else len(midint) / 7 + 1
    result = []
    for i in range(size):
        s = midint[i * 7: (i + 1) * 7][::-1]
        s = base62_encode(int(s))
        # New fixed
        s_len = len(s)
        if i < size - 1 and len(s) < 4:
            s = '0' * (4 - s_len) + s
        # Fix end
        result.append(s)
    result.reverse()
    return ''.join(result)

def get_avatar_size_url(img_url, size=50):
    assert size == 50 or size == 180
    splits = img_url.split('/')
    current_size = int(splits[-3])
    if current_size == size:
        return img_url
    splits[-3] = str(size)
    return '/'.join(splits)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = bundle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

import urllib

from cola.core.unit import Bundle

class WeiboSearchBundle(Bundle):
    def __init__(self, keyword, force=False):
        super(WeiboSearchBundle, self).__init__(keyword, force=force)
        self.keyword = keyword
        
    def urls(self):
        return ['http://s.weibo.com/weibo/%s' % urllib.quote(self.keyword)]
########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

import os

from cola.core.config import Config

base = os.path.dirname(os.path.abspath(__file__))
user_conf = os.path.join(base, 'test.yaml')
if not os.path.exists(user_conf):
    user_conf = os.path.join(base, 'weibosearch.yaml')
user_config = Config(user_conf)

mongo_host = user_config.job.mongo.host
mongo_port = user_config.job.mongo.port
db_name = user_config.job.db

instances = user_config.job.instances
########NEW FILE########
__FILENAME__ = login
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

class WeiboLogin(object):
    def __init__(self, opener, username, passwd):
        self.opener = opener
        
        self.username = username
        self.passwd = passwd
        
    def login(self):
        br = self.opener.spynner_open('http://weibo.com')
        self.opener.wait_for_selector('div.info_list')
        br.wk_fill('input[name=username]', self.username)
        br.wk_fill('input[name=password]', self.passwd)
        br.click('a.W_btn_g')
        try:
            br.wait_for_content(lambda br: 'WB_feed' in br.html)
            return True
        except:
            return False
########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

import urlparse
import urllib

from cola.core.parsers import Parser
from cola.core.errors import DependencyNotInstalledError

from bundle import WeiboSearchBundle
from storage import MicroBlog, DoesNotExist, Q

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise DependencyNotInstalledError('BeautifulSoup4')

try:
    from dateutil.parser import parse
except ImportError:
    raise DependencyNotInstalledError('python-dateutil')

try:
    from spynner import SpynnerTimeout
except ImportError:
    raise DependencyNotInstalledError('spynner')

class WeiboSearchParser(Parser):
    def __init__(self, opener=None, url=None, bundle=None, **kwargs):
        super(WeiboSearchParser, self).__init__(opener=opener, url=url, **kwargs)
        self.bundle = bundle
        self.keyword = bundle.label
        
    def get_weibo(self, mid, keyword):
        try:
            weibo = getattr(MicroBlog, 'objects').get(Q(mid=mid) & Q(keyword=keyword))
            return weibo, True
        except DoesNotExist:
            weibo = MicroBlog(mid=mid, keyword=keyword)
            weibo.save()
            return weibo, False
        
    def parse(self, url=None):
        url = url or self.url
        
        br = self.opener.spynner_open(url)
        self.opener.wait_for_selector('div#pl_weibo_feedlist')
        try:
            self.opener.wait_for_selector('div.feed_lists', tries=5)
        except SpynnerTimeout:
            bundle = WeiboSearchBundle(self.keyword, force=True)
            return [], [bundle]
            
        html = br.html
        soup = BeautifulSoup(html)
        
        finished = False
        
        dls = soup.find_all('dl', attrs={'class': 'feed_list'}, mid=True)
        for dl in dls:
            mid = dl['mid']
            weibo, finished = self.get_weibo(mid, self.keyword)
            
            if finished:
                break
            
            weibo.content = dl.find('p', attrs={'node-type': 'feed_list_content'}).text.strip()
            is_forward = dl.get('isforward') == '1'
            if is_forward:
                weibo.forward = dl.find(
                    'dt', attrs={'node-type': 'feed_list_forwardContent'}).text.strip()
            p = dl.select('p.info.W_linkb.W_textb')[0]
            weibo.created = parse(p.find('a', attrs={'class': 'date'})['title'])
            likes = p.find('a', attrs={'action-type': 'feed_list_like'}).text
            if '(' not in likes:
                weibo.likes = 0
            else:
                weibo.likes = int(likes.strip().split('(', 1)[1].strip(')'))
            forwards = p.find('a', attrs={'action-type': 'feed_list_forward'}).text
            if '(' not in forwards:
                weibo.forwards = 0
            else:
                weibo.forwards = int(forwards.strip().split('(', 1)[1].strip(')'))
            comments = p.find('a', attrs={'action-type': 'feed_list_comment'}).text
            if '(' not in comments:
                weibo.comments = 0
            else:
                weibo.comments = int(comments.strip().split('(', 1)[1].strip(')'))
                
            weibo.save()
            
        pages = soup.find('div', attrs={'class': 'search_page'})
        if pages is None or len(list(pages.find_all('a'))) == 0:
            finished = True
        else:
            next_page = pages.find_all('a')[-1]
            if next_page.text.strip() == u'下一页':
                next_href = next_page['href']
                if not next_href.startswith('http://'):
                    next_href = urlparse.urljoin('http://s.weibo.com', next_href)
                    url, query = tuple(next_href.split('&', 1))
                    base, key = tuple(url.rsplit('/', 1))
                    key = urllib.unquote(key)
                    url = '/'.join((base, key))
                    next_href = '&'.join((url, query))
                return [next_href], []
            else:
                finished = True
        
        if finished:
            bundle = WeiboSearchBundle(self.keyword, force=True)
            return [], [bundle]
        return [], []
########NEW FILE########
__FILENAME__ = starts
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

import os

from cola.core.mq.client import MessageQueueClient
from cola.core.rpc import client_call
from cola.core.utils import get_ip

from conf import user_config

PUTSIZE = 50
keywords_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keywords.txt')

def put_starts(master=None):
    if master is None:
        nodes = ['%s:%s' % (get_ip(), getattr(user_config.job, 'port'))]
    else:
        nodes = client_call(master, 'get_nodes')
        
    mq_client = MessageQueueClient(nodes)
    with open(keywords_f) as f:
        keys = []
        size = 0
        for keyword in f.xreadlines():
            keys.append(keyword)
            size += 1
            if size >= PUTSIZE:
                mq_client.put(keys)
                size = 0
                keys = []
        if len(keys) > 0:
            mq_client.put(keys)
            
def main(master=None):
    if master is not None:
        if ':' not in master:
            master = '%s:%s' % (master, getattr(user_config.job, 'master_port'))
    put_starts(master)
            
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser('Weibo search')
    parser.add_argument('-m', '--master', metavar='master ip', nargs='?',
                        default=None, const=None,
                        help='master ip connected to')
    args = parser.parse_args()
    
    main(args.master)
########NEW FILE########
__FILENAME__ = stop
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

import socket
import os

from cola.core.rpc import client_call
from cola.core.utils import get_ip
from cola.core.logs import get_logger
from cola.worker.recover import recover

from conf import user_config

logger = get_logger(name='weibosearch_stop')

if __name__ == '__main__':
    ip, port = get_ip(), getattr(user_config.job, 'port')
    logger.info('Trying to stop single running worker')
    try:
        client_call('%s:%s' % (ip, port), 'stop')
    except socket.error:
        stop = raw_input("Force to stop? (y or n) ").strip()
        if stop == 'y' or stop == 'yes':
            job_path = os.path.split(os.path.abspath(__file__))[0]
            recover()
        else:
            print 'ignore'
    logger.info('Successfully stopped single running worker')

########NEW FILE########
__FILENAME__ = storage
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-27

@author: Chine
'''

from cola.core.errors import DependencyNotInstalledError

from conf import mongo_host, mongo_port, db_name

try:
    from mongoengine import connect, Document, Q, DoesNotExist, \
                            StringField, DateTimeField, IntField
except ImportError:
    raise DependencyNotInstalledError('mongoengine')

connect(db_name, host=mongo_host, port=mongo_port)

DoesNotExist = DoesNotExist
Q = Q

class MicroBlog(Document):
    content = StringField()
    forward = StringField()
    created = DateTimeField()
    
    likes = IntField()
    forwards = IntField()
    comments = IntField()
    
    mid = StringField(required=True)
    keyword = StringField(required=True)
########NEW FILE########
__FILENAME__ = stop
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-22

@author: Chine
'''

import os
import socket

from cola.core.rpc import client_call
from cola.core.utils import get_ip
from cola.core.config import Config
from cola.core.logs import get_logger
from cola.worker.recover import recover

logger = get_logger(name='wiki_stop')

get_user_conf = lambda s: os.path.join(os.path.dirname(os.path.abspath(__file__)), s)
user_conf = get_user_conf('test.yaml')
if not os.path.exists(user_conf):
    user_conf = get_user_conf('wiki.yaml')
user_config = Config(user_conf)

if __name__ == '__main__':
    ip, port = get_ip(), getattr(user_config.job, 'port')
    logger.info('Trying to stop single running worker')
    try:
        client_call('%s:%s' % (ip, port), 'stop')
    except socket.error:
        stop = raw_input("Force to stop? (y or n) ").strip()
        if stop == 'y' or stop == 'yes':
            job_path = os.path.split(os.path.abspath(__file__))[0]
            recover()
        else:
            print 'ignore'
    logger.info('Successfully stopped single running worker')
########NEW FILE########
__FILENAME__ = test_weibo
'''
Created on 2013-6-10

@author: Chine
'''
import unittest
import time

from cola.core.opener import MechanizeOpener

from contrib.weibo import login_hook
from contrib.weibo.parsers import MicroBlogParser, ForwardCommentLikeParser, \
                                    UserInfoParser, UserFriendParser
from contrib.weibo.conf import user_config
from contrib.weibo.bundle import WeiboUserBundle

from pymongo import Connection

class Test(unittest.TestCase):


    def setUp(self):
        self.test_uid = '1784725941'
        self.bundle = WeiboUserBundle(self.test_uid)
        self.opener = MechanizeOpener()
        
        self.conn = Connection()
        self.db = self.conn[getattr(user_config.job, 'db')]
        self.users_collection = self.db.weibo_user
        self.weibos_collection = self.db.micro_blog
        
        assert len(user_config.job['login']) > 0
        
        login_hook(self.opener, **user_config.job['login'][0])

    def tearDown(self):
        self.users_collection.remove({'uid': self.test_uid})
        self.weibos_collection.remove({'uid': self.test_uid})
        self.conn.close()
        
    def testMicroBlogParser(self):
        test_url = 'http://weibo.com/aj/mblog/mbloglist?uid=%s&_k=%s' % (
            self.test_uid,
            int(time.time() * (10**6))
        )
        parser = MicroBlogParser(opener=self.opener, 
                                 url=test_url, 
                                 bundle=self.bundle)
        _, bundles = parser.parse()
           
        self.assertEqual(len(bundles), 0)
            
        size = self.weibos_collection.find({'uid': self.test_uid}).count()
        self.assertAlmostEqual(size, 15, delta=1)
        
    def testMicroBlogForwardsParser(self):
        test_url = 'http://weibo.com/aj/mblog/info/big?id=3596988739933218&_t=0&__rnd=1373094212593'
        parser = ForwardCommentLikeParser(opener=self.opener,
                                          url=test_url,
                                          bundle=self.bundle)
        urls, _ = parser.parse()
        
        self.assertEqual(len(urls), 1)
        
        weibo = self.weibos_collection.find_one({'mid': '3596988739933218', 'uid': self.test_uid})
        self.assertLessEqual(len(weibo['forwards']), 20)
        self.assertGreater(len(weibo['forwards']), 0)
        
        parser.parse(urls[0])
        weibo = self.weibos_collection.find_one({'mid': '3596988739933218', 'uid': self.test_uid})
        self.assertLessEqual(len(weibo['forwards']), 40)
        self.assertGreater(len(weibo['forwards']), 20)
        self.assertNotEqual(weibo['forwards'][0], 
                            weibo['forwards'][20])
        
    def testMicroBlogForwardTimeParser(self):
        test_url = 'http://weibo.com/aj/mblog/info/big?_t=0&id=3600369441313426&__rnd=1373977781515'
        parser = ForwardCommentLikeParser(opener=self.opener,
                                          url=test_url,
                                          bundle=self.bundle)
        parser.parse()
        
        weibo = self.weibos_collection.find_one({'mid': '3600369441313426', 'uid': self.test_uid})
        self.assertGreater(len(weibo['forwards']), 0)
        
    def testMicroBlogLikesParser(self):
        test_url = 'http://weibo.com/aj/like/big?mid=3599246068109415&_t=0&__rnd=1373634556882'
        parser = ForwardCommentLikeParser(opener=self.opener,
                                          url=test_url,
                                          bundle=self.bundle)
        urls, _ = parser.parse()
        
        self.assertEqual(len(urls), 1)
        
        weibo = self.weibos_collection.find_one({'mid': '3599246068109415', 'uid': self.test_uid})
        self.assertEqual(len(weibo['likes']), 30)
  
    def testUserInfoParser(self):
        test_url = 'http://weibo.com/%s/info' % self.test_uid
        parser = UserInfoParser(opener=self.opener,
                                url=test_url,
                                bundle=self.bundle)
        parser.parse()
            
        user = self.users_collection.find_one({'uid': self.test_uid})
        self.assertTrue('info' in user)
         
    def testUserInfoParserForSite(self):
        test_uid = '2733272463'
        test_url = 'http://weibo.com/%s/info' % test_uid
        bundle = WeiboUserBundle(test_uid)
        parser = UserInfoParser(opener=self.opener,
                                url=test_url,
                                bundle=bundle)
        parser.parse()
         
    def testFriendParser(self):
        test_url = 'http://weibo.com/%s/follow' % self.test_uid
        parser = UserFriendParser(opener=self.opener,
                                  url=test_url,
                                  bundle=self.bundle)
        urls, bundles = parser.parse()
        self.assertEqual(len(urls), 1)
        self.assertGreater(bundles, 0)
          
        user = self.users_collection.find_one({'uid': self.test_uid})
        self.assertEqual(len(bundles), len(user['follows']))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testParser']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_wiki
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-29

@author: Chine
'''
import unittest
from datetime import datetime

from contrib.wiki import WikiParser, url_patterns, \
                         mongo_host, mongo_port, db_name

class FakeWikiParser(WikiParser):
    def store(self, title, content, last_update):
        self.title, self.content, self.last_update = title, content, last_update

class Test(unittest.TestCase):


    def testWikiParser(self):
        parser = FakeWikiParser()
        
        for url in ('http://en.wikipedia.org/wiki/Python',
                    'http://zh.wikipedia.org/wiki/Python'):
            parser.parse(url)
            lang = url.strip('http://').split('.', 1)[0]
            self.assertEqual(parser.title, 'Python '+lang)
            self.assertGreater(len(parser.content), 0)
            self.assertTrue(isinstance(parser.last_update, datetime))
            
            self.assertIsNotNone(url_patterns.get_parser(url))
            
        parser = WikiParser()
        url = 'http://en.wikipedia.org/wiki/Python'
        parser.parse(url)
        
        from pymongo import Connection
        conn = Connection(mongo_host, mongo_port)
        db = getattr(conn, db_name)
        wiki = db.wiki_document.find_one({'title': 'Python en'})
        self.assertIsNotNone(wiki)
        
        db.wiki_document.remove({'title': 'Python en'})

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_bloomfilter
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-31

@author: Chine
'''
import unittest
import random

from cola.core.bloomfilter import BloomFilter


class Test(unittest.TestCase):

    def get_random(self):
        size = random.randint(2, 10)
        return ''.join([str(random.randint(1, 9)) for _ in range(size)])

    def testBloomFilter(self):
        bf = BloomFilter(capacity=10000)
        self.assertFalse('apple' in bf)
        bf.add('apple')
        self.assertTrue('apple' in bf)
        self.assertFalse('banana' in bf)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testBloomFilter']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_bloom_filter_mq
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-1

@author: Chine
'''

import unittest
import tempfile
import shutil
import os

from cola.core.mq.node import Node
from cola.core.bloomfilter import FileBloomFilter

class Test(unittest.TestCase):


    def setUp(self):
        self.dir_ = tempfile.mkdtemp()
        self.node_dir = os.path.join(self.dir_, 'node')
        os.mkdir(self.node_dir)
        bloom_filter_hook = FileBloomFilter(
            os.path.join(self.dir_, 'bloomfilter'), 10
        )
        self.node = Node(self.node_dir, verify_exists_hook=bloom_filter_hook)

    def tearDown(self):
        self.node.shutdown()
        shutil.rmtree(self.dir_)
          
    def testPutGet(self):
        num = str(12345)
        
        self.assertEqual(self.node.put(num), num)
        self.assertEqual(self.node.put(num), '')
        
        num2 = str(67890)
        nums = [num, num2]
        self.assertEqual(self.node.put(nums), [num2])
        
        self.node.shutdown()
        self.assertGreater(os.path.getsize(os.path.join(self.dir_, 'bloomfilter')), 0)
        
        bloom_filter_hook = FileBloomFilter(
            os.path.join(self.dir_, 'bloomfilter'), 5
        )
        self.node = Node(self.node_dir, verify_exists_hook=bloom_filter_hook)
        
        num3 = str(13579)
        nums = [num, num2, num3]
        self.assertEqual(self.node.put(nums), [num3])

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_config
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-21

@author: Chine
'''
import unittest
import pickle

from cola.core.config import PropertyObject, main_conf

class Test(unittest.TestCase):


    def setUp(self):
        self.obj = PropertyObject({
            'name': 'cola',
            'list': [
                { 'count': 1 },
                { 'count': 2 },
            ]
        })


    def testPropertyObject(self):
        assert 'name' in self.obj
        assert self.obj['name'] == 'cola'
        assert self.obj.name == 'cola'
        assert isinstance(self.obj.list, list)
        assert self.obj.list[0].count == 1
        
    def testPickle(self):
        c = pickle.dumps(main_conf)
        new_conf = pickle.loads(c)
        self.assertEqual(new_conf.master.port, 11103)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_context
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-25

@author: Chine
'''
import unittest
try:
    from StringIO import StringIO
except ImportError:
    from cStringIO import StringIO

from cola.core.config import Config
from cola.job.context import Context

class Test(unittest.TestCase):


    def setUp(self):
        self.simulate_user_conf = Config(StringIO('name: cola-unittest'))


    def testContext(self):
        context = Context(user_conf=self.simulate_user_conf, 
                          description='This is a just unittest')
        self.assertEqual(context.name, 'cola-unittest')
        self.assertEqual(context.description, 'This is a just unittest')
        self.assertEqual(context.job.db, 'cola')
        self.assertEqual(context.job.port, 12103)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_extractor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2013-6-16

@author: Chine
'''
import unittest

from cola.core.opener import MechanizeOpener
from cola.core.extractor.preprocess import PreProcessor
from cola.core.extractor import Extractor

class Test(unittest.TestCase):
    
    def setUp(self):
        self.base_url = 'http://zhidao.baidu.com'
        self.url = 'http://zhidao.baidu.com/question/559110619.html'
        self.html = MechanizeOpener().open(self.url)

    def testPreprocess(self):
        pre_process = PreProcessor(self.html, self.base_url)
        title, body = pre_process.process()
         
        self.assertTrue(u'百度' in title)
        self.assertGreater(len(body.text), 0)

    def testExtractor(self):
        extractor = Extractor(self.html, self.base_url)
        content = extractor.extract()
        self.assertGreater(len(content), 0)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testExtractor']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_loader_log
'''
Created on 2013-6-14

@author: Chine
'''
import unittest
import tempfile
import shutil
import os

from cola.job import Job
from cola.core.urls import UrlPatterns
from cola.core.opener import BuiltinOpener
from cola.core.utils import get_ip
from cola.master.loader import MasterJobLoader
from cola.worker.loader import WorkerJobLoader

class Test(unittest.TestCase):


    def setUp(self):
        self.job = Job('test job', UrlPatterns(), BuiltinOpener, [])
        self.root = tempfile.mkdtemp()
        
        master_root = os.path.join(self.root, 'master')
        worker_root = os.path.join(self.root, 'worker')
        os.makedirs(master_root)
        os.makedirs(worker_root)
        
        node = '%s:%s' % (get_ip(), self.job.context.job.port)
        nodes = [node]
        master = '%s:%s' % (get_ip(), self.job.context.job.master_port)
        
        
        self.master_loader = MasterJobLoader(self.job, master_root, nodes)
        self.worker_loader = WorkerJobLoader(self.job, worker_root, master)

    def tearDown(self):
        try:
            self.worker_loader.finish()
            self.master_loader.finish()
        finally:
            shutil.rmtree(self.root)


    def testLog(self):
        self.worker_loader.logger.info('here is the msg')
        self.worker_loader.logger.error('sth error')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_log
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-11

@author: Chine
'''
import unittest
import threading

from cola.core.logs import get_logger, LogRecordSocketReceiver

class Test(unittest.TestCase):


    def setUp(self):
        self.client_logger = get_logger(name='cola_test_client', server='localhost')
        self.server_logger = get_logger(name='cola_test_server')
        
        self.log_server = LogRecordSocketReceiver(logger=self.server_logger)
        threading.Thread(target=self.log_server.serve_forever).start()

    def tearDown(self):
        self.log_server.shutdown()

    def testLog(self):
        self.client_logger.error('Sth happens here')
        self.client_logger.info('sth info here')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testLog']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_master_watcher
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-7

@author: Chine
'''
import unittest
import tempfile
import os
import shutil

from cola.core.zip import ZipHandler
from cola.core.utils import root_dir
from cola.master.watcher import MasterWatcher

class Test(unittest.TestCase):


    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, 'watch')
        if not os.path.exists(self.root):
            os.mkdir(self.root)
        self.zip_dir = os.path.join(self.dir, 'zip')
        if not os.path.exists(self.zip_dir):
            os.mkdir(self.zip_dir)
        self.job_dir = os.path.join(self.dir, 'job')
        if not os.path.exists(self.job_dir):
            os.mkdir(self.job_dir)
            
        zip_file = os.path.join(self.zip_dir, 'wiki.zip')
        src_dir = os.path.join(root_dir(), 'contrib', 'wiki')
        self.zip_file = ZipHandler.compress(zip_file, src_dir, type_filters=('pyc', ))
        
        self.master_watcher = MasterWatcher(self.root, self.zip_dir, self.job_dir)
        
    def tearDown(self):
        try:
            self.master_watcher.finish()
        finally:
            shutil.rmtree(self.dir)


    def testMasterWatcher(self):
        self.master_watcher.start_job(self.zip_file)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_mq
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-25

@author: Chine
'''
import unittest
import tempfile
import shutil
import threading
import random

from cola.core.rpc import ColaRPCServer
from cola.core.mq import MessageQueue
from cola.core.mq.client import MessageQueueClient

class Test(unittest.TestCase):


    def setUp(self):
        ports = (11111, 11211, 11311)
        self.nodes = ['localhost:%s'%port for port in ports]
        self.dirs = [tempfile.mkdtemp() for _ in range(2*len(ports))]
        self.size = len(ports)
        
        for i in range(self.size):
            setattr(self, 'rpc_server%s'%i, ColaRPCServer(('localhost', ports[i])))
            setattr(self, 'mq%s'%i, 
                MessageQueue(self.nodes[:], self.nodes[i], getattr(self, 'rpc_server%s'%i))
            )
            getattr(self, 'mq%s'%i).init_store(self.dirs[2*i], self.dirs[2*i+1])
            thd = threading.Thread(target=getattr(self, 'rpc_server%s'%i).serve_forever)
            thd.setDaemon(True)
            thd.start()
            
        self.client = MessageQueueClient(self.nodes)

    def tearDown(self):
        try:
            for i in range(self.size):
                getattr(self, 'rpc_server%s'%i).shutdown()
                getattr(self, 'mq%s'%i).shutdown()
        finally:
            for d in self.dirs:
                shutil.rmtree(d)


    def testMQ(self):
        mq = self.mq0
        data = [str(random.randint(10000, 50000)) for _ in range(20)]
              
        mq.put(data)
        gets = []
        while True:
            get = mq.get()
            if get is None:
                break
            gets.append(get)
              
        self.assertEqual(sorted(data), sorted(gets))
            
        # test mq client
        data = str(random.randint(10000, 50000))
        self.client.put(data)
            
        get = self.client.get()
                 
        self.assertEqual(data, get)
        
    def testAddOrRemoveNode(self):
        mq = self.mq0
        data = [str(i) for i in range(100)]
           
        mq.put(data)
        self.mq2.shutdown()
        self.assertEqual(len(self.nodes), 3)
        self.mq0.remove_node(self.nodes[2])
        self.assertEqual(len(self.nodes), 3)
        self.mq1.remove_node(self.nodes[2])
           
        gets = []
        while True:
            get = mq.get()
            if get is None:
                break
            gets.append(get)
             
        self.assertEqual(sorted(data), sorted(gets))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_mq_node
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-25

@author: Chine
'''
import unittest
import tempfile
import os
import random
import shutil

from cola.core.mq.node import Node, NodeNoSpaceForPut


class Test(unittest.TestCase):


    def setUp(self):
        self.dir_ = tempfile.mkdtemp()
        self.node = Node(self.dir_)

    def tearDown(self):
        self.node.shutdown()
        shutil.rmtree(self.dir_)

    def testLockExists(self):
        self.assertTrue(os.path.exists(os.path.join(self.dir_, 'lock')))
          
    def testPutGet(self):
        get_num = lambda: random.randint(10000, 20000)
          
        num1 = get_num()
        self.assertEqual(self.node.put(str(num1)), str(num1))
        num2 = get_num()
        self.assertEqual(self.node.put(str(num2)), str(num2))
          
        self.assertEqual(self.node.get(), str(num1))
        self.assertEqual(self.node.get(), str(num2))
        
    def testBatchPutGet(self):
        self.node.shutdown()
        
        size = 50
        batch1 = ['1' * 20, '2' * 20]
        batch2 = ['3' * 20, '4' * 20]
        
        self.node = Node(self.dir_, size)
        
        self.assertEqual(self.node.put(batch1), batch1)
        self.assertEqual(self.node.put(batch2), batch2)
        
        self.assertEqual(len(self.node.map_files), 2)
        
        gets = sorted([self.node.get() for _ in range(4)])
        res = batch1
        res.extend(batch2)
        self.assertEqual(gets, res)
        
        self.node.put('5' * 20)
        self.assertEqual(self.node.get(), '5' * 20)
        
        self.node.put('6' * 20)
        
        self.node.merge()
        self.assertEqual(len(self.node.map_files), 1)
        
        self.assertEqual(self.node.get(), '6' * 20)
        self.assertEqual(self.node.get(), None)
        
        self.assertRaises(NodeNoSpaceForPut, lambda: self.node.put('7' * 100))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_opener
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-17

@author: Chine
'''
import unittest

from cola.core.opener import BuiltinOpener, MechanizeOpener, \
                            SpynnerOpener

class Test(unittest.TestCase):


    def testBuiltinOpener(self):
        opener = BuiltinOpener()
        assert 'baidu' in opener.open('http://www.baidu.com')
          
    def testMechanizeOpener(self):
        test_url = 'http://www.baidu.com'
        opener = MechanizeOpener()
          
        assert 'baidu' in opener.open(test_url)
          
        br = opener.browse_open(test_url)
        assert u'百度' in br.title()
        assert 'baidu' in br.response().read()
        
    def testSpynnerOpener(self):
        test_url = 'http://s.weibo.com/'
        opener = SpynnerOpener()
        
        br = opener.spynner_open(test_url)
        br.wk_fill('input.searchInp_form', u'超级月亮')
        br.click('a.searchBtn')
        br.wait_for_content(lambda br: 'feed_lists W_linka W_texta' in br.html)
        
        self.assertIn(u'超级月亮', br.html)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_rpc
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-23

@author: Chine
'''
from __future__ import with_statement
import unittest
import xmlrpclib
import random
import socket
import threading

from cola.core.rpc import ColaRPCServer

def test_plus_one(num):
    return num + 1

class Test(unittest.TestCase):
    
    def client_call(self):
        server = xmlrpclib.ServerProxy('http://localhost:11103')
        num = random.randint(0, 100)
        plus_one_num = server.test_plus_one(num)
        self.assertEqual(plus_one_num, num + 1)
        
    def start_server(self):
        self.server = ColaRPCServer(('localhost', 11103))
        self.server.register_function(test_plus_one)
        self.server.serve_forever()

    def setUp(self):
        self.server_run = threading.Thread(target=self.start_server)
            
    def testRPC(self):
        self.server_run.start()
        self.client_call()
        self.server.shutdown()
        del self.server
        with self.assertRaises(socket.error):
            self.client_call()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_urlpatterns
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-29

@author: Chine
'''
import unittest

from cola.core.parsers import Parser
from cola.core.urls import Url, UrlPatterns

class FakeParser(Parser):
    pass
    
class Test(unittest.TestCase):


    def testUrlPatterns(self):
        url_patterns = UrlPatterns(
            Url(r'^http://zh.wikipedia.org/wiki/[^FILE][^/]+$', 'wiki_item', FakeParser)
        )
        
        urls = ['http://zh.wikipedia.org/wiki/%E6%97%A0%E6%95%8C%E8%88%B0%E9%98%9F',
                ]
        self.assertTrue(list(url_patterns.matches(urls)), urls)
        self.assertEqual(url_patterns.get_parser(urls[0]), FakeParser)
        
        self.assertFalse(Url('^http://zh.wikipedia.org/wiki/[^FILE][^/]+$', None, None).match('http://zh.wikipedia.org/wiki/File:Flag_of_Cross_of_Burgundy.svg'))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testUrlPatterns']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_worker_loader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-5-28

@author: Chine
'''

try:
    from StringIO import StringIO
except ImportError:
    from cStringIO import StringIO
import unittest
import tempfile
import shutil
import urlparse

from cola.core.opener import MechanizeOpener
from cola.core.parsers import Parser
from cola.core.urls import UrlPatterns, Url
from cola.core.config import Config
from cola.job import Job
from cola.worker.loader import StandaloneWorkerJobLoader

f = StringIO()
sep = '---------------------%^&*()---------------------'

class FakeWikiParser(Parser):
    def parse(self, url=None):
        url = url or self.url
        
        def _is_same(out_url):
            return out_url.rsplit('#', 1)[0] == url
        
        br = self.opener.browse_open(url)
        f.write(br.response().read())
        f.write(sep)
        
        links = []
        for link in br.links():
            if link.url.startswith('http://'):
                out_url = link.url
                if not _is_same(out_url):
                    links.append(out_url)
            else:
                out_url = urlparse.urljoin(link.base_url, link.url)
                if not _is_same(out_url):
                    links.append(out_url)
        return links
        
user_conf = '''job:
  db: cola
  mode: url
  size: 10
  limit: 0
  master_port: 12102
  port: 12103
  instances: 1'''

class Test(unittest.TestCase):


    def setUp(self):
        url_patterns = UrlPatterns(
            Url(r'^http://zh.wikipedia.org/wiki/[^(:|/)]+$', 'wiki_item', FakeWikiParser)
        )
        fake_user_conf = Config(StringIO(user_conf))
        
        self.dir = tempfile.mkdtemp()
        
        self.job = Job('fake wiki crawler', url_patterns, MechanizeOpener, 
                       ['http://zh.wikipedia.org/wiki/%E6%97%A0%E6%95%8C%E8%88%B0%E9%98%9F', ],
                       user_conf=fake_user_conf)
        
        self.local_node = 'localhost:%s' % self.job.context.job.port
        self.nodes = [self.local_node, ]

    def tearDown(self):
        shutil.rmtree(self.dir)


    def testJobLoader(self):
        with StandaloneWorkerJobLoader(
            self.job, self.dir, 
            local=self.local_node, nodes=self.nodes) as self.loader:
        
            self.assertEqual(len(self.job.starts), 1)
            
            self.loader.mq.put(self.job.starts)
            self.assertEqual(self.loader.mq.get(), self.job.starts[0])
            
            # put starts into mq again
            self.loader.mq.put(self.job.starts, force=True)
            self.loader.run(put_starts=False)
             
            self.assertEqual(len(f.getvalue().strip(sep).split(sep)), 10)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_zip
'''
Copyright (c) 2013 Qin Xuye <qin@qinxuye.me>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on 2013-6-6

@author: Chine
'''
import unittest
import tempfile
import shutil
import os

from cola.core.zip import ZipHandler

class Test(unittest.TestCase):


    def setUp(self):
        self.f = tempfile.mkdtemp()
        self.content = 'This is a test file!'
        
        self.src_dir = os.path.join(self.f, 'compress')
        os.mkdir(self.src_dir)
        with open(os.path.join(self.src_dir, '1.txt'), 'w') as fp:
            fp.write(self.content)
        dir1 = os.path.join(self.src_dir, 'dir1')
        os.mkdir(dir1)
        with open(os.path.join(dir1, '2.txt'), 'w') as fp:
            fp.write(self.content)
            
        self.dest_dir = os.path.join(self.f, 'uncompress')

    def tearDown(self):
        shutil.rmtree(self.f)


    def testZip(self):
        zip_file = os.path.join(self.f, 'test.zip')
        
        ZipHandler.compress(zip_file, self.src_dir)
        ZipHandler.uncompress(zip_file, self.dest_dir)
        
        dir_ = os.path.join(self.dest_dir, 'compress')
        self.assertTrue(os.path.exists(dir_))
        
        with open(os.path.join(dir_, '1.txt')) as fp:
            self.assertEqual(fp.read(), self.content)
            
        dir1 = os.path.join(dir_, 'dir1')
        self.assertTrue(os.path.exists(dir1))
        
        with open(os.path.join(dir1, '2.txt')) as fp:
            self.assertEqual(fp.read(), self.content)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
