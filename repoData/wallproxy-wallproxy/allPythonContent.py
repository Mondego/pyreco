__FILENAME__ = gen_cacert
#!/usr/bin/env python
# Lib\site-packages\pip\_vendor\requests\cacert.pem

import base64, hashlib, re, sys
try: from OpenSSL import crypto
except ImportError: crypto = None

PY3 = sys.version_info[0] >= 3

print('read CA.crt')
with open('CA.crt', 'U') as fp:
    data = fp.read().strip()

if crypto:
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, data)
    issuer = cert.get_issuer(); subj = cert.get_subject()
    info = '''\
# Issuer: CN=%s O=%s OU=%s
# Subject: CN=%s O=%s OU=%s
# Label: "%s"
# Serial: %d''' % (issuer.CN, issuer.O, issuer.OU,
        subj.CN, subj.O, subj.OU, subj.CN, cert.get_serial_number())
else:
    info = '''\
# Issuer: CN=WallProxy CA O=WallProxy OU=WallProxy Root
# Subject: CN=WallProxy CA O=WallProxy OU=WallProxy Root
# Label: "WallProxy CA"
# Serial: 0'''

hexf = lambda s:':'.join('%02x'%i for i in bytearray(s))
d = re.compile(r'(?ms)BEGIN CERTIFICATE[^\n]+\n(.+?)\n[^\n]+END CERTIFICATE')
d = base64.b64decode(d.search(data).group(1))
data = '''%s
# MD5 Fingerprint: %s
# SHA1 Fingerprint: %s
# SHA256 Fingerprint: %s
%s
''' % (info,
       hexf(hashlib.md5(d).digest()),
       hexf(hashlib.sha1(d).digest()),
       hexf(hashlib.sha256(d).digest()),
       data)

print('write cacert.pem')
with open('cacert.pem', 'wb') as fp:
    fp.write(data.encode('latin-1') if PY3 else data)

########NEW FILE########
__FILENAME__ = make_config
# -*- coding: utf-8 -*-
from __future__ import with_statement

PUBLIC_APPIDS = '''
smartladder8|sandaojushi3|ftencentuck|baidufirefoxtieba|chromeichi|aitaiyokani|smartladder3|smartladder4|chrome360q|smartladder6|goagent-dup001|kawaiiushioplus|smartladdercanada|gongongid02|goagent-dup003|goagent-dup002|gonggongid03|ippotsukobeta|gonggongid01|gonggongid07|gonggongid06|kawaiiushionoserve|gonggongid04|kawaiiushio2|chromelucky|gonggongid09|yanlun001|smartladderchina|smartladder1|kawaiiushio1|kawaiiushio6|kawaiiushio7|saosaiko|kawaiiushio5|smartladderjapan|bakajing600|sekaiwakerei|yugongxisaiko|gonggongid08|smartladder2|baiduchrometieba|kawaiiushio4|gonggongid05|bakabaka300|fangbingxingtodie|f360uck|chromesaiko|chromeqq|kawaiiushio|ilovesmartladder|smartladder7|gongmin700|qq325862401|kawaiiushio8|smartladderkoera|gonggongid10|kawaiiushio9|smartladderuk|smartladderhongkong|chrometieba|flowerwakawaii|feijida600|window8saiko|gfwdies|smartladdertaiwan|akb48daisukilove|smartladderus|diaoyudaobelongtochinasaiko|jianiwoxiangni|freegoagent160|freegoagent198|freegoagent205|freegoagent292|freegoagent334|freegoagent358|freegoagent494|freegoagent526|freegoagent547|freegoagent553|freegoagent576|freegoagent577|freegoagent578|freegoagent583|freegoagent585|freegoagent586|freegoagent591|freegoagent599|freegoagent603|freegoagent607|freegoagent616|freegoagent623|freegoagent624|freegoagent625|freegoagent628|freegoagent631|freegoagent633|freegoagent638|freegoagent641|freegoagent644|freegoagent650|freegoagent654|freegoagent655|freegoagent657|freegoagent666|freegoagent670|freegoagent671|freegoagent674|freegoagent685|freegoagent686|freegoagent698|freegoagent699|freegoagent701|freegoagent702|freegoagent703|freegoagent707|freegoagent710|freegoagent718|freegoagent730|freegoagent734|freegoagent737|freegoagent742|freegoagent744|freegoagent746|freegoagent753|freegoagent758|freegoagent760|freegoagent762|freegoagent766|freegoagent771|freegoagent773|freegoagent774|freegoagent777|freegoagent780|freegoagent781|freegoagent784|freegoagent785|freegoagent786|freegoagent789|freegoagent791|freegoagent793|freegoagent794|freegoagent799|freegoagent802|freegoagent807|freegoagent809|freegoagent810|freegoagent811|freegoagent812|freegoagent813|freegoagent818|freegoagent822|freegoagent825|freegoagent827|freegoagent828|freegoagent830|freegoagent831|freegoagent832|freegoagent836|freegoagent837|freegoagent840|freegoagent847|freegoagent851|freegoagent852|freegoagent855|freegoagent859|freegoagent861|freegoagent863|freegoagent866|freegoagent867|freegoagent870|freegoagent872|freegoagent874|freegoagent875|freegoagent876|freegoagent877|freegoagent879|freegoagent881|freegoagent889|freegoagent894|freegoagent898|freegoagent900|freegoagent905|freegoagent909|freegoagent910|freegoagent914|freegoagent915|freegoagent919|freegoagent923|freegoagent926|freegoagent927|freegoagent928|freegoagent929|freegoagent932|freegoagent934|freegoagent945|freegoagent949|freegoagent950|freegoagent951|freegoagent954|freegoagent956|freegoagent957|freegoagent958|freegoagent963|freegoagent965|freegoagent966|freegoagent968|freegoagent971|freegoagent972|freegoagent973|freegoagent974|freegoagent975|freegoagent976|freegoagent978|freegoagent981|freegoagent987|freegoagent993|freegoagent994|freegoagent998
'''

import ConfigParser, os, re, urlparse, os.path as ospath, random
from cStringIO import StringIO

def rulefiles(v):
    v = v.strip()
    i = v.find('string://')
    if i < 0:
        return v.split('|')
    if i == 0:
        return [v.replace(r'\n', '\n')]
    return v[:i-1].split('|') + [v[i:].replace(r'\n', '\n')]

class Common(object):
    v = '''def %s(self, *a):
    try:
        return self.CONFIG.%s(*a[:-1])
    except:
        return a[-1]
'''
    for k in ('get', 'getint', 'getfloat', 'getboolean', 'items', 'remove_option'):
        exec(v % (k, k))
    del k, v

    def parse_pac_config(self):
        v = self.get('pac', 'py_default', '') or 'FORWARD'
        self.PY_DEFAULT = (v.split('|') * 3)[:3]
        if self.PAC_FILE:
            v = self.get('pac', 'default', '') or self._PAC_DEFAULT
            self.PAC_DEFAULT = (v.split('|') * 3)[:3]
        else:
            self.PAC_DEFAULT = self.PY_DEFAULT
        def get_rule_cfg(key, default):
            PAC_RULELIST = v = self.get('pac', key, default)
            if v.startswith('!'):
                if self.PAC_FILE:
                    v = self.items(v.lstrip('!').strip(), ())
                    v = [(rulefiles(v),k.upper()) for k,v in v if k and v]
                else:
                    v = self.items('py_'+v.lstrip('!').strip(), ())
                    sp = {'FORBID':'False', 'WEB':'None'}
                    v = [(rulefiles(v),sp.get(k.upper()) or k.upper()) for k,v in v if k and v]
                PAC_RULELIST = v
            elif v:
                TARGET_PAC = self.TARGET_PAAS
                if self.PAC_FILE:
                    TARGET_PAC = self.TARGET_LISTEN
                    if not TARGET_PAC:
                        TARGET_PAC = '*:*'
                    elif ':' not in TARGET_PAC:
                        TARGET_PAC = '*:' + TARGET_PAC
                    TARGET_PAC = 'PROXY %s;DIRECT' % TARGET_PAC
                PAC_RULELIST = [(rulefiles(v), TARGET_PAC)]
            return PAC_RULELIST
        self.PAC_RULELIST = get_rule_cfg('rulelist', '')
        self.PAC_IPLIST = get_rule_cfg('iplist', '')

    def __init__(self, INPUT):
        ConfigParser.RawConfigParser.OPTCRE = re.compile(r'(?P<option>[^=\s][^=]*)\s*(?P<vi>[=])\s*(?P<value>.*)$')
        CONFIG = self.CONFIG = ConfigParser.ConfigParser()
        for file in (INPUT, ospath.join(ospath.dirname(INPUT), 'user.ini')):
            try:
                CONFIG.read(file)
            except ConfigParser.MissingSectionHeaderError:
                with open(file, 'rb') as fp: v = fp.read()
                v = v[v.find('['):]
                try:
                    with open(file, 'wb') as fp: fp.write(v)
                except IOError:
                    pass
                CONFIG.readfp(StringIO(v), file)

        self.LISTEN_IP          = self.get('listen', 'ip', '0.0.0.0')
        self.LISTEN_PORT        = self.getint('listen', 'port', 8086)
        self.USERNAME           = self.get('listen', 'username', None)
        self.WEB_USERNAME       = self.get('listen', 'web_username', 'admin')
        self.WEB_PASSWORD       = self.get('listen', 'web_password', 'admin')
        self.WEB_AUTHLOCAL      = self.getboolean('listen', 'web_authlocal', False)
        if self.USERNAME is not None:
            self.PASSWORD       = self.get('listen', 'password', '')
            self.BASIC_AUTH     = self.getboolean('listen', 'basic_auth', True)
            self.DISABLE_SOCKS4 = self.getboolean('listen', 'disable_socks4', False)
            self.DISABLE_SOCKS5 = self.getboolean('listen', 'disable_socks5', False)
        self.CERT_WILDCARD      = self.getboolean('listen', 'cert_wildcard', True)
        self.TASKS_DELAY        = self.getint('listen', 'tasks_delay', 0)

        self.FETCH_KEEPALIVE    = self.getboolean('urlfetch', 'keep_alive', True)
        self.FETCH_TIMEOUT      = self.getfloat('urlfetch', 'timeout', -1)
        self.FORWARD_TIMEOUT    = self.getfloat('urlfetch', 'fwd_timeout', -1)
        self.FETCH_ARGS = v = {}
        k = self.getfloat('urlfetch', 'gae_timeout', -1)
        if k >= 0: v['timeout'] = k or None
        k = self.getint('urlfetch', 'gae_crlf', 0)
        if k > 0: v['crlf'] = k
        self.DEBUG_LEVEL        = self.getint('urlfetch', 'debug', -1)

        GAE_PROFILE = 'gae'; self.GAE_HANDLER = False
        self.GAE_ENABLE         = self.getboolean('gae', 'enable', CONFIG.has_section('gae'))
        if self.GAE_ENABLE:
            self.GAE_LISTEN     = self.get('gae', 'listen', '8087')
            if self.LISTEN_PORT == 8087 and self.GAE_LISTEN == '8087':
                self.LISTEN_PORT = 8086
            v = self.get('gae', 'appid', '').replace('.appspot.com', '')
            if not v or v == 'appid1|appid2':
                self.GAE_APPIDS = v = re.sub(r'\s+', '', PUBLIC_APPIDS).split('|')
                random.shuffle(v)
            else:
                self.GAE_APPIDS = v.split('|')
            self.GAE_PASSWORD   = self.get('gae', 'password', '')
            self.GAE_PATH       = self.get('gae', 'path', '/fetch.py')
            GAE_PROFILE         = self.get('gae', 'profile', GAE_PROFILE)
            self.GAE_MAXTHREADS = self.getint('gae', 'max_threads', 0)
            v = self.getint('gae', 'fetch_mode', 0)
            self.GAE_FETCHMOD   = 0 if v <= 0 else (2 if v >= 2 else 1)
            self.GAE_PROXY      = self.get('gae', 'proxy', 'default')
            self.GAE_HANDLER    = self.GAE_LISTEN and self.getboolean('gae', 'find_handler', True)

        self.PAAS_ENABLE        = self.getboolean('paas', 'enable', CONFIG.has_section('paas'))
        if self.PAAS_ENABLE:
            self.PAAS_LISTEN        = self.get('paas', 'listen', '')
            self.PAAS_PASSWORD      = self.get('paas', 'password', '')
            self.PAAS_FETCHSERVER   = CONFIG.get('paas', 'fetchserver').split('|')
            self.PAAS_PROXY         = self.get('paas', 'proxy', 'default')

        self.SOCKS5_ENABLE      = self.getboolean('socks5', 'enable', CONFIG.has_section('socks5'))
        if self.SOCKS5_ENABLE:
            self.SOCKS5_LISTEN      = self.get('socks5', 'listen', '')
            self.SOCKS5_PASSWORD    = self.get('socks5', 'password', '')
            self.SOCKS5_FETCHSERVER = CONFIG.get('socks5', 'fetchserver')
            self.SOCKS5_PROXY       = self.get('socks5', 'proxy', 'default')

        OLD_PLUGIN = []
        d = {'gaeproxy':'OGAE', 'forold':'OOLD', 'goagent':'OGA', 'simple':'OSP', 'simple2':'OSP2'}
        for k in d:
            if self.getboolean(k, 'enable', CONFIG.has_section(k)):
                url = self.get(k, 'url', '')
                if url: url = url.split('|')
                else:
                    url = self.get(k, 'appid', '')
                    if not url: continue
                    url = ['https://%s.appspot.com/%s.py' % (i,k) for i in url.split('|')]
                crypto = (self.get(k, 'crypto', '') + '|'*200).split('|')
                key = self.get(k, 'password', '').decode('string-escape')
                key = (key + ('|'+key)*200).split('|')
                proxy = [v.split(',') if ',' in v else v for v in (self.get(k, 'proxy', 'default')+'|'*200).split('|')]
                configs = []
                for url,crypto,key,proxy in zip(url,crypto,key,proxy):
                    config = {'url':url, 'key':key}
                    if crypto: config['crypto'] = crypto
                    if proxy == 'none':
                        config['proxy'] = None
                    elif proxy:
                        config['proxy'] = proxy
                    configs.append(config)
                for v in ('max_threads', 'range0', 'range'):
                    configs[0][v] = self.getint(k, v, 0)
                OLD_PLUGIN.append((d[k], k, configs, self.get(k, 'listen', '')))
        self.OLD_PLUGIN = OLD_PLUGIN or False

        self.TARGET_PAAS        = self.GAE_ENABLE and 'GAE' or self.PAAS_ENABLE and 'PAAS' or self.SOCKS5_ENABLE and 'SOCKS5' or self.OLD_PLUGIN and self.OLD_PLUGIN[0][0]
        self.TARGET_LISTEN = self.GAE_ENABLE and self.GAE_LISTEN or self.PAAS_ENABLE and self.PAAS_LISTEN or self.SOCKS5_ENABLE and self.SOCKS5_LISTEN or self.OLD_PLUGIN and self.OLD_PLUGIN[0][3]

        v = self.getint('proxy', 'enable', 0)
        self._PAC_DEFAULT = 'DIRECT'; self.GLOBAL_PROXY = None
        if v > 0:
            PROXIES = []
            for i in xrange(1,v+1):
                v = self.get('proxy', 'proxy%d'%i, '')
                if not v: break
                PROXIES.append(v)
            if not PROXIES:
                PROXY_HOST      = CONFIG.get('proxy', 'host')
                PROXY_PORT      = CONFIG.getint('proxy', 'port')
                PROXY_USERNAME  = self.get('proxy', 'username', '')
                PROXY_PASSWROD  = self.get('proxy', 'password', '')
                self._PAC_DEFAULT= 'PROXY %s:%s;DIRECT' % (PROXY_HOST, PROXY_PORT)
                if PROXY_USERNAME:
                    PROXY_HOST = '%s:%s@%s' % (PROXY_USERNAME, PROXY_PASSWROD, PROXY_HOST)
                PROXIES.append('http://%s:%s' % (PROXY_HOST, PROXY_PORT))
            self.GLOBAL_PROXY   = PROXIES[0] if len(PROXIES) == 1 else tuple(PROXIES)

        self.HTTPS_TARGET = {}
        if self.getboolean('forward', 'enable', CONFIG.has_section('forward')):
            self.remove_option('forward', 'enable', '')
            for k,v in self.items('forward', ()):
                self.HTTPS_TARGET[k.upper()] = '(%s)'%v if '"' in v or "'" in v else repr(v)

        self.PAC_ENABLE = self.getboolean('pac', 'enable', True)
        v = self.getint('pac', 'https_mode', 2)
        self.PAC_HTTPSMODE = 0 if v <= 0 else (2 if v >= 2 else 1)
        v = self.get('pac', 'file', '').replace('goagent', 'proxy')
        self.PAC_FILE = v and v.split('|')
        self.parse_pac_config()

        self.GOOGLE_MODE        = self.get(GAE_PROFILE, 'mode', 'http')
        v = self.get(GAE_PROFILE, 'hosts', '')
        self.GOOGLE_HOSTS       = ' '.join(v and tuple(v.split('|')) or ())
        v = self.get(GAE_PROFILE, 'sites', '')
        self.GOOGLE_SITES       = v and tuple(v.split('|')) or ()
        v = self.get(GAE_PROFILE, 'forcehttps', ''); v = v and v.split('|') or ()
        GOOGLE_FORCEHTTPS = [(i if '/' in i else ('http://%s/'%('*'+i if i.startswith('.') else i))) for i in v]
        v = self.get(GAE_PROFILE, 'noforcehttps', ''); v = v and v.split('|') or ()
        GOOGLE_FORCEHTTPS.extend(['@@%s'%(i if '/' in i else ('http://%s/'%('*'+i if i.startswith('.') else i))) for i in v])
        self.GOOGLE_FORCEHTTPS = ' \n '.join(GOOGLE_FORCEHTTPS)
        v = self.get(GAE_PROFILE, 'withgae', '')
        GOOGLE_WITHGAE          = v and tuple(v.split('|')) or ()
        self.TRUE_HTTPS = self.TARGET_PAAS and self.get(GAE_PROFILE, 'truehttps', '').replace('|', ' ').strip()
        self.NOTRUE_HTTPS = self.TRUE_HTTPS and self.get(GAE_PROFILE, 'notruehttps', '').replace('|', ' ').strip()

        self.FETCHMAX_LOCAL     = self.getint('fetchmax', 'local', 3)
        self.FETCHMAX_SERVER    = self.getint('fetchmax', 'server', 0)

        self.AUTORANGE_ENABLE   = self.getboolean('autorange', 'enable', False)
        def get_rules(opt, key, d=''):
            v = self.get(opt, key, d)
            if v.startswith('!'):
                v = v.lstrip('!').strip()
                return v and rulefiles(v)
            else:
                return v.replace(r'\n', '\n').strip()
        self.AUTORANGE_RULES = get_rules('autorange', 'rules')
        v = self.get('autorange', 'hosts', ''); v = v and v.split('|') or ()
        v = ' \n '.join([(i if '/' in i else ('||%s'%i.lstrip('.') if i.startswith('.') else 'http*://%s/'%i)) for i in v])
        if isinstance(self.AUTORANGE_RULES, list):
            self.AUTORANGE_RULES.append('string://' + v)
        elif v:
            self.AUTORANGE_RULES = ' \n '.join((v, self.AUTORANGE_RULES))
        self.AUTORANGE_MAXSIZE  = self.getint('autorange', 'maxsize', 1000000)
        self.AUTORANGE_WAITSIZE = self.getint('autorange', 'waitsize', 500000)
        self.AUTORANGE_BUFSIZE  = self.getint('autorange', 'bufsize', 8192)

        assert self.AUTORANGE_BUFSIZE <= self.AUTORANGE_WAITSIZE <= self.AUTORANGE_MAXSIZE

        self.REMOTE_DNS = self.DNS_RESOLVE = self.CRLF_RULES = self.HOSTS_RULES = ''; self.HOSTS = {}
        if self.getboolean('hosts', 'enable', CONFIG.has_section('hosts')):
            self.REMOTE_DNS = v = self.get('hosts', 'dns', '')
            if v: self.REMOTE_DNS = v if ',' in v else repr(v)
            self.DNS_RESOLVE = self.get('hosts', 'resolve', '').replace('|', ' ').strip()
            self.HOSTS_CRLF = self.getint('hosts', 'crlf', 0)
            self.CRLF_RULES = self.HOSTS_CRLF > 0 and get_rules('hosts', 'crlf_rules')
            self.HOSTS_RULES = self.TARGET_PAAS and get_rules('hosts', 'rules')
            for v in ('enable', 'rules', 'crlf', 'crlf_rules', 'dns', 'resolve'):
                self.remove_option('hosts', v, '')
            for k,v in self.items('hosts', ()):
                if v.startswith('profile:'):
                    v = self.get(GAE_PROFILE, v[8:], '')
                else:
                    m = re.match(r'\[(\w+)\](\w+)', v)
                    if m:
                        v = v.replace(m.group(0), self.get(m.group(1), m.group(2), ''))
                v = v.replace('|', ' ').strip()
                if k and v: self.HOSTS[k] = v

        self.THIRD_APPS = []
        if self.getboolean('third', 'enable', CONFIG.has_section('third')):
            self.remove_option('third', 'enable', '')
            self.THIRD_APPS = [(k,v if v[0] in ('"',"'") else repr(v)) for k,v in self.items('third', ()) if v]

        self.USERAGENT_STRING   = self.getboolean('useragent', 'enable', True) and self.get('useragent', 'string', '')
        self.USERAGENT_MATCH    = self.USERAGENT_STRING and self.get('useragent', 'match', '')
        self.USERAGENT_RULES    = self.USERAGENT_MATCH and get_rules('useragent', 'rules')
        self.FALLBACK_RULES     = self.TARGET_PAAS and get_rules('urlfetch', 'nofallback',
            r'/^https?:\/\/(?:[\w-]+|127(?:\.\d+){3}|10(?:\.\d+){3}|192\.168(?:\.\d+){2}|172\.[1-3]\d(?:\.\d+){2}|\[.+?\])(?::\d+)?\//')
        v = self.get('urlfetch', 'redirects', '')
        try:
            if v.startswith('!'):
                with open(ospath.join(ospath.dirname(INPUT), 'misc', v.lstrip('!').strip()), 'U') as fp:
                    v = fp.read()
            for p,r in eval(v): ''+p+r
            self.REDIRECT_RULES = '(%s)'%v
        except:
            self.REDIRECT_RULES = ''

        self.AUTORANGE_RULES    = (self.GAE_ENABLE or self.OLD_PLUGIN) and self.AUTORANGE_ENABLE and self.AUTORANGE_RULES
        self.PAC_ENABLE         = (self.PAC_RULELIST or self.PAC_IPLIST) and self.PAC_ENABLE and 'PAC_ENABLE'
        self.GOOGLE_WITHGAE     = False
        if self.TARGET_PAAS and self.GOOGLE_SITES and not self.GLOBAL_PROXY:
            self.GOOGLE_WITHGAE = ' \n '.join([(i if '/' in i else '||%s'%i.lstrip('.')) for i in GOOGLE_WITHGAE])
            v = ' \n '.join(['||%s'%i.lstrip('.') for i in self.GOOGLE_SITES])
            if isinstance(self.HOSTS_RULES, basestring):
                self.HOSTS_RULES = ' \n '.join((self.HOSTS_RULES, v))
            else:
                self.HOSTS_RULES.append('string://' + v)
        self.NEED_PAC           = self.GOOGLE_FORCEHTTPS or self.USERAGENT_RULES or self.FALLBACK_RULES or self.AUTORANGE_RULES or self.CRLF_RULES or self.HOSTS_RULES or self.GOOGLE_WITHGAE or self.PAC_ENABLE


def tob(s, enc='utf-8'):
    return s.encode(enc) if isinstance(s, unicode) else bytes(s)
def touni(s, enc='utf-8', err='strict'):
    return s.decode(enc, err) if isinstance(s, str) else unicode(s)

class SimpleTemplate(object):
    """SimpleTemplate from bottle"""
    blocks = ('if', 'elif', 'else', 'try', 'except', 'finally', 'for', 'while',
              'with', 'def', 'class')
    dedent_blocks = ('elif', 'else', 'except', 'finally')
    re_pytokens = re.compile(r'''
            (''(?!')|""(?!")|'{6}|"{6}    # Empty strings (all 4 types)
             |'(?:[^\\']|\\.)+?'          # Single quotes (')
             |"(?:[^\\"]|\\.)+?"          # Double quotes (")
             |'{3}(?:[^\\]|\\.|\n)+?'{3}  # Triple-quoted strings (')
             |"{3}(?:[^\\]|\\.|\n)+?"{3}  # Triple-quoted strings (")
             |\#.*                        # Comments
            )''', re.VERBOSE)

    def __init__(self, source, encoding='utf-8'):
        self.source = source
        self.encoding = encoding
        self._str = lambda x: touni(repr(x), encoding)
        self._escape = lambda x: touni(x, encoding)

    @classmethod
    def split_comment(cls, code):
        """ Removes comments (#...) from python code. """
        if '#' not in code: return code
        #: Remove comments only (leave quoted strings as they are)
        subf = lambda m: '' if m.group(0)[0]=='#' else m.group(0)
        return re.sub(cls.re_pytokens, subf, code)

    @property
    def co(self):
        # print self.code
        return compile(self.code, '<string>', 'exec')

    @property
    def code(self):
        stack = [] # Current Code indentation
        lineno = 0 # Current line of code
        ptrbuffer = [] # Buffer for printable strings and token tuple instances
        codebuffer = [] # Buffer for generated python code
        multiline = dedent = oneline = False
        template = self.source

        def yield_tokens(line):
            for i, part in enumerate(re.split(r'\{\{(.*?)\}\}', line)):
                if i % 2:
                    if part.startswith('!'): yield 'RAW', part[1:]
                    else: yield 'CMD', part
                else: yield 'TXT', part

        def flush(): # Flush the ptrbuffer
            if not ptrbuffer: return
            cline = ''
            for line in ptrbuffer:
                for token, value in line:
                    if token == 'TXT': cline += repr(value)
                    elif token == 'RAW': cline += '_str(%s)' % value
                    elif token == 'CMD': cline += '_escape(%s)' % value
                    cline +=  ', '
                cline = cline[:-2] + '\\\n'
            cline = cline[:-2]
            if cline[:-1].endswith('\\\\\\\\\\n'):
                cline = cline[:-7] + cline[-1] # 'nobr\\\\\n' --> 'nobr'
            cline = '_printlist([' + cline + '])'
            del ptrbuffer[:] # Do this before calling code() again
            code(cline)

        def code(stmt):
            for line in stmt.splitlines():
                codebuffer.append('  ' * len(stack) + line.strip())

        for line in template.splitlines(True):
            lineno += 1
            line = touni(line, self.encoding)
            sline = line.lstrip()
            if lineno <= 2:
                m = re.match(r"%\s*#.*coding[:=]\s*([-\w.]+)", sline)
                if m: self.encoding = m.group(1)
                if m: line = line.replace('coding','coding (removed)')
            if sline and sline[0] == '%' and sline[:2] != '%%':
                line = line.split('%',1)[1].lstrip() # Full line following the %
                cline = self.split_comment(line).strip()
                cmd = re.split(r'[^a-zA-Z0-9_]', cline)[0]
                flush() # You are actually reading this? Good luck, it's a mess :)
                if cmd in self.blocks or multiline:
                    cmd = multiline or cmd
                    dedent = cmd in self.dedent_blocks # "else:"
                    if dedent and not oneline and not multiline:
                        cmd = stack.pop()
                    code(line)
                    oneline = not cline.endswith(':') # "if 1: pass"
                    multiline = cmd if cline.endswith('\\') else False
                    if not oneline and not multiline:
                        stack.append(cmd)
                elif cmd == 'end' and stack:
                    code('#end(%s) %s' % (stack.pop(), line.strip()[3:]))
                else:
                    code(line)
            else: # Line starting with text (not '%') or '%%' (escaped)
                if line.strip().startswith('%%'):
                    line = line.replace('%%', '%', 1)
                ptrbuffer.append(yield_tokens(line))
        flush()
        return '\n'.join(codebuffer) + '\n'

    def execute(self, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        env = {}
        env.update({'_stdout': _stdout, '_printlist': _stdout.extend,
               '_str': self._str, '_escape': self._escape, 'get': env.get,
               'setdefault': env.setdefault, 'defined': env.__contains__})
        env.update(kwargs)
        eval(self.co, env)
        return env

    def render(self, *args, **kwargs):
        """ Render the template using keyword arguments as local variables. """
        for dictarg in args: kwargs.update(dictarg)
        stdout = []
        self.execute(stdout, kwargs)
        return ''.join(stdout)


template = r"""# -*- coding: utf-8 -*-
# æ˜¯å¦ä½¿ç”¨iniä½œä¸ºé…ç½®æ–‡ä»¶ï¼Œ0ä¸ä½¿ç”¨
ini_config = {{MTIME}}
# ç›‘å¬ip
listen_ip = '{{LISTEN_IP}}'
# ç›‘å¬ç«¯å£
listen_port = {{LISTEN_PORT}}
# æ˜¯å¦ä½¿ç”¨é€šé…ç¬¦è¯ä¹¦
cert_wildcard = {{int(CERT_WILDCARD)}}
# æ›´æ–°PACæ—¶ä¹Ÿè®¸è¿˜æ²¡è”ç½‘ï¼Œç­‰å¾…tasks_delayç§’åŽæ‰å¼€å§‹æ›´æ–°
tasks_delay = {{!TASKS_DELAY}}
# WEBç•Œé¢æ˜¯å¦å¯¹æœ¬æœºä¹Ÿè¦æ±‚è®¤è¯
web_authlocal = {{int(WEB_AUTHLOCAL)}}
# ç™»å½•WEBç•Œé¢çš„ç”¨æˆ·å
web_username = {{!WEB_USERNAME}}
# ç™»å½•WEBç•Œé¢çš„å¯†ç 
web_password = {{!WEB_PASSWORD}}
# å…¨å±€ä»£ç†
global_proxy = {{!GLOBAL_PROXY}}
# URLFetchå‚æ•°
fetch_keepalive = {{int(FETCH_KEEPALIVE)}}
%if FETCH_TIMEOUT >= 0:
fetch_timeout = {{!FETCH_TIMEOUT or None}}
%end
%if FORWARD_TIMEOUT >= 0:
forward_timeout = {{!FORWARD_TIMEOUT or None}}
%end
%if DEBUG_LEVEL >= 0:
debuglevel = {{!DEBUG_LEVEL}}
%end
check_update = 0

def config():
    Forward, set_dns, set_resolve, set_hosts, check_auth, redirect_https = import_from('util')
%for k,v in HTTPS_TARGET.iteritems():
    {{k}} = Forward({{v}})
%HTTPS_TARGET[k] = k
%end
    RAW_FORWARD = FORWARD = Forward()
%if REMOTE_DNS:
    set_dns({{REMOTE_DNS}})
%end
%if DNS_RESOLVE:
    set_resolve({{!DNS_RESOLVE}})
%end
    google_sites = {{!GOOGLE_SITES}}
    google_hosts = {{!GOOGLE_HOSTS}}
    set_hosts(google_sites, google_hosts)
%for k,v in HOSTS.iteritems():
%if k and v:
    set_hosts({{!k}}, {{repr(v) if v != GOOGLE_HOSTS else 'google_hosts'}})
%end
%end

    from plugins import misc; misc = install('misc', misc)
    PAGE = misc.Page('page.html')
%if REDIRECT_RULES:
    redirect_rules = misc.Redirects({{REDIRECT_RULES}})
%end
%HTTPS_TARGET.update({'FORWARD':'FORWARD', 'RAW_FORWARD':'RAW_FORWARD', 'False':'False', 'None':'None','PAGE':'None'})
%if TARGET_PAAS:

    from plugins import paas; paas = install('paas', paas)
%end #TARGET_PAAS
%if GAE_ENABLE:
%HTTPS_TARGET['GAE'] = 'None'
    GAE = paas.GAE(appids={{!GAE_APPIDS}}\\
%if GAE_LISTEN:
, listen={{!GAE_LISTEN}}\\
%end
%if GAE_PASSWORD:
, password={{!GAE_PASSWORD}}\\
%end
%if GAE_PATH:
, path={{!GAE_PATH}}\\
%end
%if GOOGLE_MODE == 'https':
, scheme='https'\\
%end
%if GAE_PROXY != 'default':
, proxy={{!GAE_PROXY}}\\
%end
, hosts=google_hosts\\
%if AUTORANGE_MAXSIZE and AUTORANGE_MAXSIZE != 1000000:
, maxsize={{!AUTORANGE_MAXSIZE}}\\
%end
%if AUTORANGE_WAITSIZE and AUTORANGE_WAITSIZE != 500000:
, waitsize={{!AUTORANGE_WAITSIZE}}\\
%end
%if AUTORANGE_BUFSIZE and AUTORANGE_BUFSIZE != 8192:
, bufsize={{!AUTORANGE_BUFSIZE}}\\
%end
%if FETCHMAX_LOCAL and FETCHMAX_LOCAL != 3:
, local_times={{!FETCHMAX_LOCAL}}\\
%end
%if FETCHMAX_SERVER and FETCHMAX_SERVER != 3:
, server_times={{!FETCHMAX_SERVER}}\\
%end
%if GAE_MAXTHREADS:
, max_threads={{!GAE_MAXTHREADS}}\\
%end
%if GAE_FETCHMOD:
, fetch_mode={{!GAE_FETCHMOD}}\\
%end
%if FETCH_ARGS:
, fetch_args={{!FETCH_ARGS}}\\
%end
)
%end #GAE_ENABLE
%if PAAS_ENABLE:
%HTTPS_TARGET['PAAS'] = 'None'
%for i,k in enumerate(PAAS_FETCHSERVER):
    PAAS{{i+1 if len(PAAS_FETCHSERVER) > 1 else ''}} = paas.PAAS(url={{!k}}\\
%if PAAS_LISTEN and i == 0:
, listen={{!PAAS_LISTEN}}\\
%end
%if PAAS_PASSWORD:
, password={{!PAAS_PASSWORD}}\\
%end
%if PAAS_PROXY != 'default':
, proxy={{!PAAS_PROXY}}\\
%end
%if FETCH_ARGS:
, fetch_args={{!FETCH_ARGS}}\\
%end
)
%end
%if len(PAAS_FETCHSERVER) > 1:
%k = ['PAAS%d'%i for i in xrange(1, len(PAAS_FETCHSERVER)+1)]
%HTTPS_TARGET.update(dict.fromkeys(k,'None'))
    PAASS = ({{', '.join(k)}})
    from random import choice
    PAAS = lambda req: choice(PAASS)(req)
    server = paas.data.get('PAAS_server')
    if server:
        def find_handler(req):
            if req.proxy_type.endswith('http'):
                return PAAS
        server.find_handler = find_handler
%end
%end #PAAS_ENABLE
%if SOCKS5_ENABLE:
%HTTPS_TARGET['SOCKS5'] = 'SOCKS5'
    SOCKS5 = paas.SOCKS5(url={{!SOCKS5_FETCHSERVER}}\\
%if SOCKS5_LISTEN:
, listen={{!SOCKS5_LISTEN}}\\
%end
%if SOCKS5_PASSWORD:
, password={{!SOCKS5_PASSWORD}}\\
%end
%if SOCKS5_PROXY != 'default':
, proxy={{!SOCKS5_PROXY}}\\
%end
)
%end #SOCKS5_ENABLE
%if OLD_PLUGIN:
    from old import old; old = install('old', old)
%for n,k,c,p in OLD_PLUGIN:
    {{n}} = old.{{k}}({{!c}}, {{!p}})
%HTTPS_TARGET[n] = 'None'
%end
%end #OLD_PLUGIN
%if NEED_PAC:

    PacFile, RuleList, HostList = import_from('pac')
    def apnic_parser(data):
        from re import findall
        return '\n'.join(findall(r'(?i)\|cn\|ipv4\|((?:\d+\.){3}\d+\|\d+)\|', data))
%PAC_IPLIST = [('[%s]'%(', '.join(('(%r, apnic_parser)'%i) if 'delegated-apnic-latest' in i else repr(i) for i in v)),t) for v,t in PAC_IPLIST]
%end #NEED_PAC
%if GOOGLE_FORCEHTTPS:
    forcehttps_sites = RuleList({{!GOOGLE_FORCEHTTPS}})
%end
%if AUTORANGE_RULES:
    autorange_rules = RuleList({{!AUTORANGE_RULES}})
%if GAE_ENABLE:
    _GAE = GAE; GAE = lambda req: _GAE(req, autorange_rules.match(req.url, req.proxy_host[0]))
%end
%if OLD_PLUGIN:
%for n,k,c,p in OLD_PLUGIN:
    _{{n}} = {{n}}; {{n}} = lambda req: _{{n}}(req, autorange_rules.match(req.url, req.proxy_host[0]))
%end
%end #OLD_PLUGIN
%end
%if USERAGENT_RULES:
    import re; useragent_match = re.compile({{!USERAGENT_MATCH}}).search
    useragent_rules = RuleList({{!USERAGENT_RULES}})
%end
%if GOOGLE_WITHGAE:
    withgae_sites = RuleList({{!GOOGLE_WITHGAE}})
%end #GOOGLE_WITHGAE
%if TRUE_HTTPS:
%if NOTRUE_HTTPS:
    notruehttps_sites = HostList({{!NOTRUE_HTTPS}})
%end
    truehttps_sites = HostList({{!TRUE_HTTPS}})
%end #TRUE_HTTPS
%if CRLF_RULES:
    crlf_rules = RuleList({{!CRLF_RULES}})
%end #CRLF_RULES
%if HOSTS_RULES:
    hosts_rules = RuleList({{!HOSTS_RULES}})
%end #HOSTS_RULES
    unparse_netloc = import_from('utils')
    def build_fake_url(scheme, host):
        if scheme == 'https' and host[1] != 80 or host[1] % 1000 == 443:
            scheme, dport = 'https', 443
        else: scheme, dport = 'http', 80
        return '%s://%s/' % (scheme, unparse_netloc(host, dport))
%if TARGET_PAAS:
    _HttpsFallback = ({{TARGET_PAAS}},)
%if FALLBACK_RULES:
    nofallback_rules = RuleList({{!FALLBACK_RULES}})
    def FORWARD(req):
        if req.proxy_type.endswith('http'):
            if nofallback_rules.match(req.url, req.proxy_host[0]):
                return RAW_FORWARD(req)
            return RAW_FORWARD(req, {{TARGET_PAAS}})
        url = build_fake_url(req.proxy_type, req.proxy_host)
        if nofallback_rules.match(url, req.proxy_host[0]):
            return RAW_FORWARD(req)
        return RAW_FORWARD(req, _HttpsFallback)
%else:
    def FORWARD(req):
        if req.proxy_type.endswith('http'):
            return RAW_FORWARD(req, {{TARGET_PAAS}})
        return RAW_FORWARD(req, _HttpsFallback)
%end
%end
%PY_DEFAULT = (([v for v in PY_DEFAULT if v in HTTPS_TARGET] or ['FORWARD']) * 3)[:3]
%if PAC_ENABLE:
%if PAC_FILE:
%NEED_PAC = NEED_PAC != 'PAC_ENABLE'

    rulelist = (
%for k,v in PAC_RULELIST:
        ({{!k}}, {{!v}}),
%end #PAC_RULELIST
    )
    iplist = (
%for k,v in PAC_IPLIST:
        ({{k}}, {{!v}}),
%end #PAC_IPLIST
    )
    PacFile(rulelist, iplist, {{!PAC_FILE}}, {{!PAC_DEFAULT}})
%else:
%PAC_DEFAULT = PY_DEFAULT
%PAC_RULELIST = [(k,v) for k,v in PAC_RULELIST if v in HTTPS_TARGET]
%PAC_IPLIST = [(k,v) for k,v in PAC_IPLIST if v in HTTPS_TARGET]
%PAC_ENABLE = PAC_RULELIST or PAC_IPLIST
%NEED_PAC = NEED_PAC != 'PAC_ENABLE' or PAC_ENABLE
%if PAC_RULELIST:

    rulelist = (
%for k,v in PAC_RULELIST:
        (RuleList({{!k}}), {{v}}),
%end #PAC_RULELIST
    )
%if PAC_HTTPSMODE == 2:
    httpslist = (
%for i,k in enumerate(PAC_RULELIST):
        (rulelist[{{i}}][0], {{HTTPS_TARGET[k[1]]}}),
%end #PAC_RULELIST
    )
%end #PAC_HTTPSMODE
%end #PAC_RULELIST
%if PAC_IPLIST:
    IpList, makeIpFinder = import_from('pac')
    iplist = (
%for k,v in PAC_IPLIST:
        (IpList({{k}}), {{v}}),
%end #PAC_IPLIST
    )
    findHttpProxyByIpList = makeIpFinder(iplist, [{{', '.join(PAC_DEFAULT)}}])
    findHttpsProxyByIpList = makeIpFinder(iplist, [{{', '.join([HTTPS_TARGET[v] for v in PAC_DEFAULT])}}])
%end #PAC_IPLIST
%end #PAC_FILE
%end #PAC_ENABLE
%if THIRD_APPS:

    from plugins import third; third = install('third', third)
%for k,v in THIRD_APPS:
    third.run({{v}}) #{{k}}
%end
%end

%if USERNAME:
    auth_checker = check_auth({{!USERNAME}}, {{!PASSWORD}}\\
%if DISABLE_SOCKS4:
, socks4=False\\
%end
%if DISABLE_SOCKS5 and not SOCKS5_ENABLE:
, socks5=False\\
%end
%if BASIC_AUTH:
, digest=False\\
%end
)
%end #USERNAME
%if GAE_ENABLE:
%if GAE_HANDLER:
%if USERNAME:
    @auth_checker
%end
    def find_gae_handler(req):
        proxy_type = req.proxy_type
        host, port = req.proxy_host
        if proxy_type.endswith('http'):
            url = req.url
%if USERAGENT_RULES:
            if useragent_match(req.headers.get('User-Agent','')) and useragent_rules.match(url, host):
                req.headers['User-Agent'] = {{!USERAGENT_STRING}}
%end
%if GOOGLE_WITHGAE:
            if withgae_sites.match(url, host):
                return GAE
%end
%if GOOGLE_FORCEHTTPS:
            needhttps = req.scheme == 'http' and forcehttps_sites.match(url, host) and req.content_length == 0
            if needhttps and getattr(req, '_r', '') != url:
                req._r = url
                return redirect_https
%end
%if REDIRECT_RULES:
            handler = redirect_rules(req)
            if handler: return handler
%end
%if CRLF_RULES:
            if crlf_rules.match(url, host):
                req.crlf = {{HOSTS_CRLF}}
                return FORWARD
%end
%if HOSTS_RULES:
            if \\
%if GOOGLE_FORCEHTTPS:
not needhttps and \\
%end
hosts_rules.match(url, host):
                return FORWARD
%end
            return GAE
%if TRUE_HTTPS:
%if NOTRUE_HTTPS:
        if notruehttps_sites.match(host): return
%end
        if truehttps_sites.match(host): return FORWARD
%end
%else:
    def find_gae_handler(req):
        if req.proxy_type.endswith('http'): return GAE
%end #GAE_HANDLER
    paas.data['GAE_server'].find_handler = find_gae_handler

%end #GAE_ENABLE
%if USERNAME:
    @auth_checker
%end
    def find_proxy_handler(req):
%if TARGET_PAAS or NEED_PAC:
        proxy_type = req.proxy_type
        host, port = req.proxy_host
        if proxy_type.endswith('http'):
            url = req.url
%if USERAGENT_RULES:
            if useragent_match(req.headers.get('User-Agent','')) and useragent_rules.match(url, host):
                req.headers['User-Agent'] = {{!USERAGENT_STRING}}
%end
%if GOOGLE_WITHGAE:
            if withgae_sites.match(url, host):
                return {{TARGET_PAAS}}
%end
%if GOOGLE_FORCEHTTPS:
            needhttps = req.scheme == 'http' and forcehttps_sites.match(url, host) and req.content_length == 0
            if needhttps and getattr(req, '_r', '') != url:
                req._r = url
                return redirect_https
%end
%if REDIRECT_RULES:
            handler = redirect_rules(req)
            if handler: return handler
%end
%if CRLF_RULES:
            if crlf_rules.match(url, host):
                req.crlf = {{HOSTS_CRLF}}
                return FORWARD
%end
%if HOSTS_RULES:
            if \\
%if GOOGLE_FORCEHTTPS:
not needhttps and \\
%end
hosts_rules.match(url, host):
                return FORWARD
%end
%if PAC_ENABLE and not PAC_FILE:
%if PAC_RULELIST:
            for rule,target in rulelist:
                if rule.match(url, host):
                    return target
%end
%if PAC_IPLIST:
            return findHttpProxyByIpList(host)
%else:
            return {{PY_DEFAULT[0]}}
%end
%elif TARGET_PAAS:
            return {{TARGET_PAAS}}
%else:
            return FORWARD
%end
%if TRUE_HTTPS:
%if NOTRUE_HTTPS:
        if notruehttps_sites.match(host): return
%end
        if truehttps_sites.match(host): return FORWARD
%end
%if PAC_ENABLE and not PAC_FILE and PAC_HTTPSMODE == 2:
%if PAC_RULELIST:
        url = build_fake_url(proxy_type, (host, port))
        for rule,target in httpslist:
            if rule.match(url, host):
                return target
%end
%if PAC_IPLIST:
        return findHttpsProxyByIpList(host)
%else:
        return {{HTTPS_TARGET[PY_DEFAULT[0]]}}
%end
%elif PAC_HTTPSMODE == 0:
        return {{HTTPS_TARGET[PY_DEFAULT[0]]}}
%end
%else:
        return FORWARD
%end
    return find_proxy_handler
"""

def make_config(INPUT=None, OUTPUT=None):
    if not (INPUT and OUTPUT):
        if INPUT:
            OUTPUT = ospath.join(ospath.dirname(INPUT), 'config.py')
        elif OUTPUT:
            INPUT = ospath.join(ospath.dirname(OUTPUT), 'proxy.ini')
        else:
            if globals().get('__loader__'):
                DIR = ospath.dirname(__loader__.archive)
            else:
                DIR = ospath.dirname(__file__)
            INPUT = ospath.join(DIR, 'proxy.ini')
            OUTPUT = ospath.join(DIR, 'config.py')
    config = Common(INPUT).__dict__
    # from pprint import pprint
    # pprint(config)
    config['MTIME'] = 1 #int(os.stat(INPUT).st_mtime)
    code = SimpleTemplate(template).render(**config)
    # print code
    return tob(code), OUTPUT

if __name__ == '__main__':
    code, OUTPUT = make_config()
    with open(OUTPUT, 'wb') as fp:
        fp.write(code)

########NEW FILE########
__FILENAME__ = old
# -*- coding: utf-8 -*-

def old():
    import_from, global_proxy = config.import_from(config)

    # ================================ util.crypto =================================
    import hashlib, itertools

    class XOR:
        '''XOR with pure Python in case no PyCrypto'''
        def __init__(self, key):
            self.key = key

        def encrypt(self, data):
            xorsize = 1024
            key = itertools.cycle(map(ord, self.key))
            dr = xrange(0, len(data), xorsize)
            ss = [None] * len(dr)
            for i,j in enumerate(dr):
                dd = [ord(d)^k for d,k in itertools.izip(data[j:j+xorsize], key)]
                ss[i] = ''.join(map(chr, dd))
            return ''.join(ss)
        decrypt = encrypt

    class NUL:
        def encrypt(self, data):
            return data
        decrypt = encrypt

    class Crypto:
        _BlockSize = {'AES':16, 'ARC2':8, 'ARC4':1, 'Blowfish':8, 'CAST':8,
                      'DES':8, 'DES3':8, 'IDEA':8, 'RC5':8, 'XOR':1}
        _Modes = ['ECB', 'CBC', 'CFB', 'OFB', 'PGP'] #CTR needs 4 args
        _KeySize = {'AES':[16,24,32], 'CAST':xrange(5,17),
                    'DES':[8], 'DES3':[16,24], 'IDEA':[16]}

        def __init__(self, mode='AES-CBC-32'):
            mode = mode.split('-')
            mode += [''] * (3 - len(mode))
            #check cipher
            self.cipher = mode[0] if mode[0] else 'AES'
            if self.cipher not in self._BlockSize:
                raise ValueError('Invalid cipher: '+self.cipher)
            #check ciphermode
            if self._BlockSize[self.cipher] == 1:
                self.ciphermode = ''
            else:
                self.ciphermode = mode[1] if mode[1] in self._Modes else 'CBC'
            #check keysize
            try:
                self.keysize = int(mode[2])
            except ValueError:
                self.keysize = 32
            if self.keysize != 0:
                if self.cipher in self._KeySize:
                    keysize = self._KeySize[self.cipher]
                    if self.keysize not in keysize:
                        self.keysize = keysize[-1]
            #avoid Memmory Error
            if self.cipher=='RC5' and self.keysize in (1, 57): self.keysize=32
            #try to import Crypto.Cipher.xxxx
            try:
                cipherlib = __import__('Crypto.Cipher.'+self.cipher, fromlist='x')
                self._newobj = cipherlib.new
                if self._BlockSize[self.cipher] != 1:
                    self._ciphermode = getattr(cipherlib, 'MODE_'+self.ciphermode)
            except ImportError:
                if self.cipher == 'XOR': self._newobj = XOR
                else: raise

        def paddata(self, data):
            blocksize = self._BlockSize[self.cipher]
            if blocksize != 1:
                padlen = (blocksize - len(data) - 1) % blocksize
                data = '%s%s%s' % (chr(padlen), ' '*padlen, data)
            return data

        def unpaddata(self, data):
            if self._BlockSize[self.cipher] != 1:
                padlen = ord(data[0])
                data = data[padlen+1:]
            return data

        def getcrypto(self, key):
            if self.keysize==0 and key=='':
                return NUL()
            khash = hashlib.sha512(key).digest()
            if self.keysize != 0:
                key = khash[:self.keysize]
            blocksize = self._BlockSize[self.cipher]
            if blocksize == 1:
                return self._newobj(key)
            return self._newobj(key, self._ciphermode, khash[-blocksize:])

        def encrypt(self, data, key):
            crypto = self.getcrypto(key)
            data = self.paddata(data)
            return crypto.encrypt(data)

        def decrypt(self, data, key):
            crypto = self.getcrypto(key)
            data = crypto.decrypt(data)
            return self.unpaddata(data)

        def getmode(self):
            return '%s-%s-%d' % (self.cipher, self.ciphermode, self.keysize)

        def __str__(self):
            return '%s("%s")' % (self.__class__, self.getmode())

        def getsize(self, size):
            blocksize = self._BlockSize[self.cipher]
            return (size + blocksize - 1) // blocksize * blocksize

    class Crypto2(Crypto):
        def paddata(self, data):
            blocksize = self._BlockSize[self.cipher]
            if blocksize != 1:
                padlen = (blocksize - len(data) - 1) % blocksize
                data = '%s%s%s' % (data, ' '*padlen, chr(padlen))
            return data

        def unpaddata(self, data):
            if self._BlockSize[self.cipher] != 1:
                padlen = ord(data[-1])
                data = data[:-(padlen+1)]
            return data

    # =============================== plugins._base ================================
    HeaderDict, Proxy, URLInfo, del_bad_hosts, start_new_server, unparse_netloc = import_from(utils)
    import time, re, random, threading, socket, os, traceback

    class Handler(object):
        _dirty_headers = ('Connection', 'Proxy-Connection', 'Proxy-Authorization',
                         'Content-Length', 'Host', 'Vary', 'Via', 'X-Forwarded-For')
        _range_re = re.compile(r'(\d+)?-(\d+)?')
        _crange_re = re.compile(r'bytes\s+(\d+)-(\d+)/(\d+)')
        crypto = Crypto('XOR--32'); key = ''
        proxy = global_proxy
        headers = HeaderDict('Content-Type: application/octet-stream')
        range0 = 100000; range = 500000; max_threads = 10

        def __init__(self, config):
            dic = {'crypto': Crypto, 'key': lambda v:v, 'headers': HeaderDict,
                   'proxy': lambda v:global_proxy if v=='default' else Proxy(v),
                   'range0': lambda v:v if v>=10000 else self.__class__.range0,
                   'range': lambda v:v if v>=100000 else self.__class__.range,
                   'max_threads': lambda v:v if v>0 else self.__class__.max_threads,}
            self.url = URLInfo(config['url'])
            for k,v in dic.iteritems():
                if k in config:
                    setattr(self.__class__, k, v(config[k]))
                setattr(self, k, getattr(self.__class__, k))

        def __str__(self):
            return ' %s %s %d %d %d' % (self.url.url, self.crypto.getmode(),
                    self.range0, self.range, self.max_threads)

        def dump_data(self, data):
            raise NotImplementedError

        def load_data(self, data):
            raise NotImplementedError

        def process_request(self, req, force_range):
            data, headers = req.read_body(), req.headers
            for k in self._dirty_headers:
                del headers[k]
            if req.command == 'GET':
                rawrange, range = self._process_range(req.headers)
                if force_range:
                    headers['Range'] = range
            else:
                rawrange, range = '', ''
            request = {'url':req.url, 'method':req.command,
                       'headers':headers, 'payload':data, 'range':range}
            return request, rawrange

        def _process_range(self, headers):
            range = headers.get('Range', '')
            m = self._range_re.search(range)
            if m:
                m = m.groups()
                if m[0] is None:
                    if m[1] is None: m = None
                    else:
                        m = 1, int(m[1])
                        if m[1] > self.range0: range = 'bytes=-1024'
                else:
                    if m[1] is None:
                        m = 0, int(m[0])
                        range = 'bytes=%d-%d' % (m[1], m[1]+self.range0-1)
                    else:
                        m = 2, int(m[0]), int(m[1])
                        if m[2]-m[1]+1 > self.range0:
                            range = 'bytes=%d-%d' % (m[1], m[1]+self.range0-1)
            if m is None:
                range = 'bytes=0-%d' % (self.range0 - 1)
            return m, range

        def _fetch(self, data):
            data = self.crypto.encrypt(data, self.key)
            url = self.url
            opener = self.proxy.get_opener(url)
            try:
                resp = opener.open(url, data, 'POST', self.headers, 0)
            except Exception, e:
                return -1, e
            if resp.status != 200:
                opener.close()
                return -1, '%s: %s' % (resp.status, resp.reason)
            return 0, resp

        def fetch(self, data):
            raise NotImplementedError

        def read_data(self, type, data):
            if type == 1: return data
            resp, crypto = data
            data = self.crypto.unpaddata(crypto.decrypt(resp.read()))
            resp.close()
            return data

        def write_data(self, req, type, data):
            sendall = req.socket.sendall
            if type == 1:
                sendall(data)
            else:
                resp, crypto = data
                size = self.crypto.getsize(16384)
                data = crypto.decrypt(resp.read(size))
                sendall(self.crypto.unpaddata(data))
                data = resp.read(size)
                while data:
                    sendall(crypto.decrypt(data))
                    data = resp.read(size)
                resp.close()

        def _need_range_fetch(self, req, res, range):
            headers = res[2]
            m = self._crange_re.search(headers.get('Content-Range', ''))
            if not m: return None
            m = map(int, m.groups())#bytes %d-%d/%d
            if range is None:
                start=0; end=m[2]-1
                code = 200
                del headers['Content-Range']
            else:
                if range[0] == 0: #bytes=%d-
                    start=range[1]; end=m[2]-1
                elif range[0] == 1: #bytes=-%d
                    start=m[2]-range[1]; end=m[2]-1
                else: #bytes=%d-%d
                    start=range[1]; end=range[2]
                code = 206
                headers['Content-Range'] = 'bytes %d-%d/%d' % (start, end, m[2])
            headers['Content-Length'] = str(end-start+1)
            req.start_response(code, headers)
            if start == m[0]: #Valid
                self.write_data(req, res[0], res[3])
                start = m[1] + 1
            return start, end

        def range_fetch(self, req, handler, request, start, end):
            t = time.time()
            if self._range_fetch(req, handler, request, start, end):
                t = time.time() - t
                t = (end - start + 1) / 1000.0 / t
                print '>>>>>>>>>> Range Fetch ended (all @ %sKB/s)' % t
            else:
                req.close_connection = 1
                print '>>>>>>>>>> Range Fetch failed'

        def _range_fetch(self, req, handler, request, start, end):
            request['range'] = '' # disable server auto-range-fetch
            i, s, thread_size, tasks = 0, start, 10, []
            while s <= end:
                e = s + (i < thread_size and self.range0 or self.range) - 1
                if e > end: e = end
                tasks.append((i, s, e))
                i += 1; s = e + 1
            task_size = len(tasks)
            thread_size = min(task_size, len(handler)*2, self.max_threads)
            print ('>>>>>>>>>> Range Fetch started: threads=%d blocks=%d '
                    'bytes=%d-%d' % (thread_size, task_size, start, end))
            if thread_size == 1:
                return self._single_fetch(req, handler, request, tasks)
            handler = list(handler); random.shuffle(handler)
            if thread_size > len(handler): handler *= 2
            results = [None] * task_size
            mutex = threading.Lock()
            threads = {}
            for i in xrange(thread_size):
                t = threading.Thread(target=handler[i]._range_thread,
                        args=(request, tasks, results, threads, mutex))
                threads[t] = set()
                t.setDaemon(True)
            for t in threads: t.start()
            i = 0; t = False
            while i < task_size:
                if results[i] is not None:
                    try:
                        self.write_data(req, 1, results[i])
                        results[i] = None
                        i += 1
                        continue
                    except:
                        mutex.acquire()
                        del tasks[:]
                        mutex.release()
                        break
                if not threads: #All threads failed
                    if t: break
                    t = True; continue
                time.sleep(1)
            else:
                return True
            return False

        def _single_fetch(self, req, handler, request, tasks):
            try:
                for task in tasks:
                    request['headers']['Range'] = 'bytes=%d-%d' % task[1:]
                    data = self.dump_data(request)
                    for i in xrange(3):
                        self = random.choice(handler)
                        res = self.fetch(data)
                        if res[0] == -1:
                            time.sleep(2)
                        elif res[1] == 206:
                            #print res[2]
                            print '>>>>>>>>>> block=%d bytes=%d-%d' % task
                            self.write_data(req, res[0], res[3])
                            break
                    else:
                        raise StopIteration('Failed')
            except:
                return False
            return True

        def _range_thread(self, request, tasks, results, threads, mutex):
            ct = threading.current_thread()
            while True:
                mutex.acquire()
                try:
                    if threads[ct].intersection(*threads.itervalues()):
                        raise StopIteration('All threads failed')
                    for i,task in enumerate(tasks):
                        if task[0] not in threads[ct]:
                            task = tasks.pop(i)
                            break
                    else:
                        raise StopIteration('No task for me')
                    request['headers']['Range'] = 'bytes=%d-%d' % task[1:]
                    data = self.dump_data(request)
                except StopIteration, e:
                    #print '>>>>>>>>>> %s: %s' % (ct.name, e)
                    del threads[ct]
                    break
                finally:
                    mutex.release()
                success = False
                for i in xrange(2):
                    res = self.fetch(data)
                    if res[0] == -1:
                        time.sleep(2)
                    elif res[1] == 206:
                        try: data = self.read_data(res[0], res[3])
                        except: continue
                        if len(data) == task[2]-task[1]+1:
                            success = True
                            break
                mutex.acquire()
                if success:
                    print '>>>>>>>>>> block=%d bytes=%d-%d'%task, len(data)
                    results[task[0]] = data
                else:
                    threads[ct].add(task[0])
                    tasks.append(task)
                    tasks.sort(key=lambda x: x[0])
                mutex.release()

        def handle(self, handler, req, force_range):
            req.handler_name = handler[0].handler_name
            if len(handler) == 1:
                handlers = handler[0], handler[0]
            else:
                handlers = random.sample(handler, 2)
            request, range = self.process_request(req, force_range)
            data = self.dump_data(request)
            errors = []
            for self in handlers:
                res = self.fetch(data)
                if res[0] != -1: break
                e = res[1]; es = str(e); errors.append(es)
                if not es.startswith('Server: '): del_bad_hosts()
            else:
                return req.send_error(502, str(errors))
            if res[1]==206 and req.command=='GET':
                data = self._need_range_fetch(req, res, range)
                if data:
                    start, end = data
                    if start > end: return #end
                    return self.range_fetch(req, handler, request, start, end)
            req.start_response(res[1], res[2])
            self.write_data(req, res[0], res[3])

    def _base_init(cls, config, listen=None):
        name = cls.handler_name
        print 'Initializing %s for old version.' % name
        server = [None] * len(config)
        for i,v in enumerate(config):
            if isinstance(v, basestring):
                v = {'url': v}
            try:
                server[i] = cls(v)
                print server[i]
            except:
                traceback.print_exc()
        def handler(req, force_range=False):
            return server[0].handle(server, req, force_range)
        if listen:
            def find_handler(req):
                if req.proxy_type.endswith('http'):
                    return handler
            listen = data['%s_server'%name] = start_new_server(listen, find_handler)
            print ' %s listen on: %s' % (name, unparse_netloc(listen.server_address[:2]))
        return handler

    # ============================== plugins.gaeproxy ==============================
    import zlib, struct, cPickle as pickle

    class GAEHandler(Handler):
        handler_name = 'OGAE'
        def dump_data(self, data):
            return zlib.compress(pickle.dumps(data, 1))

        def load_data(self, data):
            return pickle.loads(data)

        def process_request(self, req, force_range):
            data, headers = req.read_body(), req.headers
            for k in self._dirty_headers:
                del headers[k]
            if req.command == 'GET':
                rawrange, range = self._process_range(req.headers)
                if force_range:
                    headers['Range'] = range
            else:
                rawrange, range = '', ''
            request = {'url':req.url, 'method':req.command, 'payload':data,
                       'headers':headers.__getstate__(), 'range':range}
            return request, rawrange

        def fetch(self, data):
            data, resp = self._fetch(data)
            if data == -1: return data, resp
            crypto = self.crypto.getcrypto(self.key)
            headers = HeaderDict()
            try:
                raw_data = resp.read(7)
                zip, code, hlen = struct.unpack('>BHI', raw_data)
                if zip == 1:
                    data = self.crypto.unpaddata(crypto.decrypt(resp.read()))
                    data = zlib.decompress(data)
                    content = data[hlen:]
                    if code == 555:
                        raise ValueError('Server: '+content)
                    headers.__setstate__(self.load_data(data[:hlen]))
                    resp.close()
                    return 1, code, headers, content
                elif zip == 0:
                    h = crypto.decrypt(resp.read(hlen))
                    headers.__setstate__(self.load_data(self.crypto.unpaddata(h)))
                    if code == 555:
                        content = crypto.decrypt(resp.read())
                        raise ValueError('Server: '+self.crypto.unpaddata(content))
                    return 0, code, headers, (resp, crypto)
                else:
                    raw_data += resp.read()
                    raise ValueError('Data format not match(%s:%s)'%(self.url.url, raw_data))
            except Exception, e:
                resp.close()
                return -1, e

    def gaeproxy(*a, **kw):
        return _base_init(GAEHandler, *a, **kw)

    # =============================== plugins.forold ===============================
    class OldHandler(Handler):
        handler_name = 'OOLD'
        crypto = Crypto2('XOR--32')

        _unquote_map = {'0':'\x10', '1':'=', '2':'&'}
        def _quote(self, s):
            return str(s).replace('\x10', '\x100').replace('=','\x101').replace('&','\x102')
        def dump_data(self, dic):
            return zlib.compress('&'.join('%s=%s' % (self._quote(k),
                    self._quote(v)) for k,v in dic.iteritems()))
        def _unquote(self, s):
            res = s.split('\x10')
            for i in xrange(1, len(res)):
                item = res[i]
                try:
                    res[i] = self._unquote_map[item[0]] + item[1:]
                except KeyError:
                    res[i] = '\x10' + item
            return ''.join(res)
        def load_data(self, qs):
            pairs = qs.split('&')
            dic = {}
            for name_value in pairs:
                if not name_value:
                    continue
                nv = name_value.split('=', 1)
                if len(nv) != 2:
                    continue
                if len(nv[1]):
                    dic[self._unquote(nv[0])] = self._unquote(nv[1])
            return dic

        def __init__(self, config):
            if 'crypto' in config:
                self.__class__.crypto = Crypto2(config.pop('crypto'))
            Handler.__init__(self, config)

        def fetch(self, data):
            data, resp = self._fetch(data)
            if data == -1: return data, resp
            try:
                raw_data = resp.read(); resp.close()
                data = self.crypto.decrypt(raw_data, self.key)
                if data[0] == '0':
                    data = data[1:]
                elif data[0] == '1':
                    data = zlib.decompress(data[1:])
                else:
                    return -1, 'Data format not match(%s:%s)' % (self.url.url,raw_data)
                code, hlen, clen = struct.unpack('>3I', data[:12])
                if len(data) != 12+hlen+clen:
                    return -1, 'Data length not match'
                content = data[12+hlen:]
                if code == 555:     #Urlfetch Failed
                    return -1, 'Server: '+content
                headers = HeaderDict(self.load_data(data[12:12+hlen]))
                return 1, code, headers, content
            except Exception, e:
                return -1, e

    def forold(*a, **kw):
        return _base_init(OldHandler, *a, **kw)

    # =============================== plugins.goagent ==============================
    from binascii import a2b_hex, b2a_hex

    class GAHandler(OldHandler):
        handler_name = 'OGA'
        crypto = Crypto('XOR--0'); key = ''
    
        def dump_data(self, dic):
            return zlib.compress('&'.join('%s=%s' % (k,b2a_hex(str(v))) for k,v in dic.iteritems()))
    
        def load_data(self, qs):
            return dict((k,a2b_hex(v)) for k,v in (x.split('=') for x in qs.split('&')))
    
        def __init__(self, config):
            config.pop('crypto', None)
            self.password = config.pop('key', '')
            OldHandler.__init__(self, config)
    
        def process_request(self, req, force_range):
            request, rawrange = OldHandler.process_request(self, req, force_range)
            request['password'] = self.password
            return request, rawrange

    def goagent(*a, **kw):
        return _base_init(GAHandler, *a, **kw)

    # =============================== plugins.simple ===============================
    class SPHandler(GAEHandler):
        handler_name = 'OSP'
        def dump_data(self, dic):
            return zlib.compress('&'.join('%s=%s' % (k,b2a_hex(str(v))) for k,v in dic.iteritems()))

        def load_data(self, qs):
            return dict((k,a2b_hex(v)) for k,v in (x.split('=') for x in qs.split('&'))) if qs else {}

        process_request = Handler.process_request

    def simple(*a, **kw):
        return _base_init(SPHandler, *a, **kw)

    # =============================== plugins.simple2 ==============================
    import marshal

    class SP2Handler(Handler):
        handler_name = 'OSP2'
        def dump_data(self, data):
            return marshal.dumps(tuple((k,str(v)) for k,v in data.iteritems()))

        def load_data(self, data):
            return dict(marshal.loads(data))

        def fetch(self, data):
            data, resp = self._fetch(data)
            if data == -1: return data, resp
            crypto = self.crypto.getcrypto(self.key)
            try:
                raw_data = resp.read(7)
                mix, code, hlen = struct.unpack('>BHI', raw_data)
                if mix == 0:
                    headers = self.crypto.unpaddata(crypto.decrypt(resp.read(hlen)))
                    if code == 555:
                        content = self.crypto.unpaddata(crypto.decrypt(resp.read()))
                        raise ValueError('Server: '+content)
                    headers = HeaderDict(headers)
                    return 0, code, headers, (resp, crypto)
                elif mix == 1:
                    data = self.crypto.unpaddata(crypto.decrypt(resp.read()))
                    content = data[hlen:]
                    if code == 555:
                        raise ValueError('Server: '+content)
                    headers = HeaderDict(data[:hlen])
                    resp.close()
                    return 1, code, headers, content
                else:
                    raw_data += resp.read()
                    raise ValueError('Data format not match(%s:%s)'%(self.url.url, raw_data))
            except Exception, e:
                resp.close()
                return -1, e

    def simple2(*a, **kw):
        return _base_init(SP2Handler, *a, **kw)

    # ==============================================================================
    globals().update(gaeproxy=gaeproxy, forold=forold, 
        goagent=goagent, simple=simple, simple2=simple2)

########NEW FILE########
__FILENAME__ = plugins
# -*- coding: utf-8 -*-
from __future__ import with_statement

def paas():
    # this part is compatible with goagent 1.1.0 by phus.lu@gmail.com and others
    print 'Initializing PAAS for proxy based on cloud service.'
    set_hosts, Forward = config.import_from('util')
    HeaderDict, Proxy, URLInfo, unparse_netloc, del_bad_hosts = config.import_from(utils)
    import re, zlib, socket, struct, time, random, threading
    from binascii import a2b_hex, b2a_hex
    from base64 import b64encode
    try:
        import ssl
    except ImportError:
        ssl = None

    class HTTPError(Exception):
        #noinspection PyMissingConstructor
        def __init__(self, code, msg):
            self.code = code
            self.msg = msg

        def __str__(self):
            return 'HTTP Error %s: %s' % (self.code, self.msg)

    _range_re = re.compile(r'(\d+)?-(\d+)?')
    _crange_re = re.compile(r'bytes\s+(\d+)-(\d+)/(\d+)')
    def _process_range(headers, max_range):
        range = headers.get('Range', '')
        m = _range_re.search(range)
        if m:
            m = m.groups()
            if m[0]:
                max_range -= 1
                if m[1]:
                    m = 2, int(m[0]), int(m[1])
                    if m[2] - m[1] > max_range:
                        range = 'bytes=%d-%d' % (m[1], m[1] + max_range)
                else:
                    m = 0, int(m[0])
                    range = 'bytes=%d-%d' % (m[1], m[1] + max_range)
            else:
                if m[1]:
                    m = 1, int(m[1])
                    if m[1] > max_range:
                        range = 'bytes=-1024'
                else:
                    m = None,
                    range = 'bytes=0-%d' % (max_range - 1)
        else:
            m = None,
            range = 'bytes=0-%d' % (max_range - 1)
        return m, range

    _setcookie_re = re.compile(r', ([^ =]+(?:=|$))')
    def _fix_setcookie(headers):
        hdr = headers.get('Set-Cookie')
        if hdr:
            headers['Set-Cookie'] = _setcookie_re.sub(r'\r\nSet-Cookie: \1', hdr)
        return headers

    def GAE(**kw):
        self = _GAEHandler
        v = kw.get('appids', '')
        self.appids = v = v.split() if isinstance(v, str) else list(v)
        if not v: raise ValueError('no appids specified')
        scheme = kw.get('scheme', 'http').lower()
        if scheme not in ('http', 'https'):
            raise ValueError('invalid scheme: '+scheme)
        self.url = URLInfo('%s://%s.appspot.com%s?' % (
            scheme, self.appids[0], kw.get('path', '/fetch.py')))
        self.password = kw.get('password', '')
        v = kw.get('proxy', 'default')
        self.proxy = config.global_proxy if v == 'default' else Proxy(v)
        v = kw.get('hosts')
        if v: v = v.split() if isinstance(v, str) else list(v)
        if not v:
            v = ('eJxdztsNgDAMQ9GNIvIoSXZjeApSqc3nUVT3ZojakFTR47wSNEhB8qXhorXg+kM'
                 'jckGtQM9efDKf91Km4W+N4M1CldNIYMu+qSVoTm7MsG5E4KPd8apInNUUMo4bet'
                 'RQjg==').decode('base64').decode('zlib').split('|')
        set_hosts('.appspot.com', v, 0)
        if self.proxy.value:
            self.hosts = v
            self.proxy = self.proxy.new_hosts((v[0], self.url.port))
        self.headers = HeaderDict(kw.get('headers',
            'Content-Type: application/octet-stream'))
        v = kw.get('max_threads', 0)
        self.max_threads = min(10 if v <= 0 else v, len(self.appids))
        self.bufsize = kw.get('bufsize', 8192)
        self.maxsize = kw.get('maxsize', 1000000)
        self.waitsize = kw.get('waitsize', 500000)
        assert self.bufsize <= self.waitsize <= self.maxsize
        self.local_times = kw.get('local_times', 3)
        self.server_times = kw.get('server_times')
        self.fetch_mode = kw.get('fetch_mode', 0)
        self.fetch_args = kw.get('fetch_args', {})
        print '  Init GAE with appids: %s' % '|'.join(self.appids)
        print '  max_threads when range fetch: %d' % self.max_threads
        v = kw.get('listen')
        if v:
            def find_handler(req):
                if req.proxy_type.endswith('http'):
                    return self
            v = data['GAE_server'] = utils.start_new_server(v, find_handler)
            print '  GAE listen on: %s' % unparse_netloc(v.server_address[:2])
        return self

    class GAEHandler(object):
        skip_headers = frozenset(['Proxy-Connection', 'Content-Length', 'Host',
            'Vary', 'Via', 'X-Forwarded-For', 'X-ProxyUser-IP'])

        def build_params(self, req, force_range):
            method = req.command; headers = req.headers
            if method == 'GET':
                req.rangeinfo, range = _process_range(headers, self.maxsize)
                if force_range or req.rangeinfo[0] == 0:
                    headers['Range'] = range
            else:
                req.rangeinfo, range = (None,), ''
            skip_headers = self.skip_headers
            headers.data = dict(kv for kv in headers.iteritems()
                if kv[0] not in skip_headers)
            params = {'url':req.url, 'method':method,
                'headers':headers, 'payload':req.read_body()}
            if range:
                params['range'] = range
            if self.password:
                params['password'] = self.password
            if self.server_times:
                params['fetchmax'] = self.server_times
            return params, dict(self.fetch_args, proxy_auth=req.userid)

        def fetch(self, (params, fetch_args), server=None):
            params = zlib.compress('&'.join(['%s=%s' % (k, b2a_hex(str(v)))
                for k,v in params.iteritems()]), 9)
            errors = []
            url = server or self.url
            opener = self.proxy.get_opener(url, fetch_args)
            ti = si = 0; tend = self.local_times; send = len(self.appids)
            while ti < tend and si < send:
                flag = 0
                try:
                    resp = opener.open(url, params, 'POST', self.headers, 0)
                    if resp.status != 200:
                        resp.close()
                        raise HTTPError(resp.status, resp.reason)
                except Exception, e:
                    opener.close()
                    if isinstance(e, HTTPError):
                        errors.append(str(e))
                        if e.code in (503, 404, 403):
                            if e.code == 503:
                                errors[-1] = 'Bandwidth Over Quota(%s)'%self.appids[0]
                            else:
                                errors[-1] = '%s(%s)'%(errors[-1],self.appids[0])
                                if self.proxy.value:
                                    self.hosts.append(self.hosts.pop(0)); flag |= 2
                                    print 'GAE: switch host to %s' % self.hosts[0]
                                else:
                                    del_bad_hosts()
                            ti -= 1
                            if server:
                                url = self.url; server.__init__(url); server = None
                            else:
                                si += 1
                                self.appids.append(self.appids.pop(0)); flag |= 1
                                url.hostname = '%s.appspot.com' % self.appids[0]
                                print 'GAE: switch appid to %s' % self.appids[0]
                        elif e.code == 502:
                            if url.scheme != 'https':
                                ti -= 1
                                url.scheme = 'https'; url.port = 443; flag |= 3
                                print 'GAE: switch scheme to https'
                    elif isinstance(e, socket.error):
                        k = e.args[0]
                        if url.scheme != 'https' and k in (10054, 54, 20054, 104):
                            ti -= 1
                            url.scheme = 'https'; url.port = 443; flag |= 3
                            print 'GAE: switch scheme to https'
                        elif self.proxy.value:
                            errors.append('Connect other proxy failed: %s' % e)
                            self.hosts.append(self.hosts.pop(0)); flag |= 2
                            print 'GAE: switch host to %s' % self.hosts[0]
                        else:
                            errors.append('Connect fetchserver failed: %s' % e)
                            if del_bad_hosts() and k in (10054, 54, 20054, 104, 10047): ti -= 1
                    else:
                        errors.append('Connect fetchserver failed: %s' % e)
                    if flag & 1:
                        url.rebuild()
                    if flag & 2:
                        if self.proxy.value:
                            self.proxy = self.proxy.new_hosts(
                                (self.hosts[0], url.port))
                        opener = self.proxy.get_opener(url, fetch_args)
                else:
                    try:
                        flag = resp.read(1)
                        if flag == '0':
                            code, hlen, clen = struct.unpack('>3I', resp.read(12))
                            headers = HeaderDict([(k, a2b_hex(v))
                                for k,_,v in (x.partition('=')
                                for x in resp.read(hlen).split('&'))])
                            if self.fetch_mode == 1 or (code == 206 and self.fetch_mode == 2):
                                resp = resp.read()
                        elif flag == '1':
                            rawdata = zlib.decompress(resp.read()); resp.close()
                            code, hlen, clen = struct.unpack('>3I', rawdata[:12])
                            headers = HeaderDict([(k, a2b_hex(v))
                                for k,_,v in (x.partition('=')
                                for x in rawdata[12:12+hlen].split('&'))])
                            resp = rawdata[12+hlen:12+hlen+clen]
                        else:
                            raise ValueError('Data format not match(%s)' % url)
                        headers.setdefault('Content-Length', str(clen))
                        return 0, (code, headers, resp)
                    except Exception, e:
                        errors.append(str(e))
                ti += 1
            return -1, errors

        def write_content(self, req, resp, first=False):
            sendall = req.socket.sendall
            if isinstance(resp, str):
                sendall(resp)
            else:
                bufsize = self.bufsize
                data = resp.read(self.waitsize if first else bufsize)
                while data:
                    sendall(data)
                    data = resp.read(bufsize)
                resp.close()

        def need_range_fetch(self, req, headers, resp):
            m = _crange_re.search(headers.get('Content-Range', ''))
            if not m: return None
            m = map(int, m.groups())#bytes %d-%d/%d
            info = req.rangeinfo
            t = info[0]
            if t is None:
                start = 0; end = m[2]; code = 200
                del headers['Content-Range']
            else:
                #noinspection PySimplifyBooleanCheck
                if t == 0: #bytes=%d-
                    start = info[1]; end = m[2]
                elif t == 1: #bytes=-%d
                    start = m[2] - info[1]; end = m[2]
                else: #bytes=%d-%d
                    start = info[1]; end = info[2] + 1
                code = 206
                headers['Content-Range'] = 'bytes %d-%d/%d' % (start, end-1, m[2])
            headers['Content-Length'] = str(end - start)
            req.start_response(code, _fix_setcookie(headers))
            if start == m[0]: #Valid
                return [start, end, m[1] + 1, resp]
            return [start, end, start, None]

        def range_fetch(self, req, params, data):
            params[0].pop('range', None) # disable server auto-range-fetch
            length = data[1] - data[0]
            if self.max_threads > 1 and data[1] - data[2] > self.maxsize:
                handle = self._thread_range
            else:
                handle = self._single_range
            t = time.time()
            if handle(req, params, data):
                t = length / 1000.0 / ((time.time() - t) or 0.0001)
                print '>>>>>>>>>> Range Fetch ended (all @ %sKB/s)' % t
            else:
                req.close_connection = True
                print '>>>>>>>>>> Range Fetch failed'

        #noinspection PyUnboundLocalVariable,PyUnusedLocal
        def _single_range(self, req, params, data):
            start0, end, start, resp = data; del data[:]
            end -= 1; step = self.maxsize; failed = 0; iheaders = params[0]['headers']
            print ('>>>>>>>>>> Range Fetch started%s: bytes=%d-%d, step=%d'
                % (req.proxy_host, start0, end, step))
            if resp:
                self.write_content(req, resp, True)
            while start <= end:
                if failed > 16: return False
                iheaders['Range'] = 'bytes=%d-%d' % (start, min(start+step, end))
                flag, data = self.fetch(params)
                if flag != -1:
                    code, headers, resp = data
                    m = _crange_re.search(headers.get('Content-Range', ''))
                if flag == -1 or code >= 400:
                    failed += 1
                    seconds = random.randint(2*failed, 2*(failed+1))
                    time.sleep(seconds)
                elif 'Location' in headers:
                    failed += 1
                    params[0]['url'] = headers['Location']
                elif not m:
                    failed += 1
                else:
                    print '>>>>>>>>>> %s' % headers['Content-Range']
                    failed = 0
                    self.write_content(req, resp)
                    start = int(m.group(2)) + 1
            return True

        def _thread_range(self, req, params, info):
            tasks, task_size, info, write_content = \
                self._start_thread_range(req, params, info)
            i = 0
            while i < task_size:
                if info[1]: #All threads failed
                    print '>>>>>>>>>> failed@%d bytes=%d-%d' % tuple(info[1][2:5])
                    return False
                task = tasks[i]
                if not isinstance(task[0], int):
                    if task[0]:
                        write_content(task[0], task)
                    i += 1
                    continue
                time.sleep(0.001)
            return True

        def _start_thread_range(self, req, params, info):
            task0, end, start, resp = info; del info[:]
            s = self.maxsize; t = s - 1; tasks = []; i = 1
            while start < end:
                tasks.append([0, set(), i, start, start+t])
                start += s; i += 1
            end -= 1; tasks[-1][-1] = end
            task_size = len(tasks)
            thread_size = min(task_size, self.max_threads)
            lock = threading.Lock(); wlock = threading.Lock()
            info = [1, None, thread_size]
            def write_content(resp, task):
                #noinspection PyBroadException
                try:
                    buf = None
                    if info[0] != task[2] or not wlock.acquire(0):
                        buf = []
                        data = resp.read(8192)
                        while data:
                            buf.append(data)
                            if info[0] == task[2] and wlock.acquire(0):
                                break
                            data = resp.read(8192)
                        else:
                            resp.close()
                            lock.acquire(); task[0] = ''.join(buf); lock.release()
                            return
                    try:
                        info[0] += 1
                        print '>>>>>>>>>> block=%d bytes=%d-%d' % tuple(task[2:5])
                        if buf: req.socket.sendall(''.join(buf))
                        self.write_content(req, resp)
                        task[0] = None
                    finally:
                        wlock.release()
                except:
                    lock.acquire(); del tasks[:]; info[1] = task; lock.release()
            # appids = random.sample(self.appids, thread_size)
            appids = self.appids[1:]; random.shuffle(appids)
            appids.append(self.appids[0]); appids = appids[:thread_size]
            print ('>>>>>>>>>> Range Fetch started: threads=%d blocks=%d '
                'bytes=%d-%d appids=%s' % (thread_size, task_size, task0, end,
                '|'.join(appids)))
            task0 = 0, (), 0, task0, tasks[0][3] - 1
            #noinspection PyBroadException
            try:
                with wlock:
                    for i in xrange(thread_size):
                        t = threading.Thread(target=self._range_thread, args=(
                            appids[i], params, tasks, lock, info, write_content))
                        t.setDaemon(True)
                        t.start()
                    if resp:
                        print '>>>>>>>>>> block=%d bytes=%d-%d' % task0[2:5]
                        self.write_content(req, resp, True)
            except:
                lock.acquire(); del tasks[:]; info[1] = task0; lock.release()
            return tasks, task_size, info, write_content

        def _range_thread(self, server, params, tasks, lock, info, write_content):
            server = URLInfo(self.url, hostname='%s.appspot.com' % server)
            ct = params[0].copy()
            ct['headers'] = headers = HeaderDict(ct['headers'])
            params = ct, params[1]
            ct = threading.current_thread()
            while 1:
                with lock:
                    try:
                        for task in tasks:
                            #noinspection PySimplifyBooleanCheck
                            if task[0] == 0:
                                failed = task[1]
                                if len(failed) == info[2]:
                                    failed.clear()
                                if ct not in failed:
                                    task[0] = 1
                                    break
                        else:
                            for task in tasks:
                                task[1].discard(ct)
                            info[2] -= 1
                            raise StopIteration('No task for me')
                    except StopIteration:
                        break
                headers['Range'] = 'bytes=%d-%d' % (task[3], task[4])
                while 1:
                    if not tasks: return
                    flag, resp = self.fetch(params, server)
                    if not tasks: return
                    if flag != -1 and resp[0] == 206:
                        resp = resp[2]
                        if isinstance(resp, str):
                            lock.acquire(); task[0] = resp; lock.release()
                        else:
                            write_content(resp, task)
                        break
                    with lock:
                        if task[0] >= 2:
                            failed.add(ct); task[0] = 0; break
                        task[0] += 1

        def __call__(self, req, force_range=False):
            req.handler_name = 'GAE'
            params = self.build_params(req, force_range)
            flag, data = self.fetch(params)
            if flag == -1:
                return req.send_error(502, str(data))
            code, headers, resp = data
            if code == 206 and req.command == 'GET':
                data = self.need_range_fetch(req, headers, resp)
                if data:
                    del code, headers, resp
                    return self.range_fetch(req, params, data)
            req.start_response(code, _fix_setcookie(headers))
            self.write_content(req, resp)

    _GAEHandler = GAEHandler()

    def PAAS(**kw):
        self = PAASHandler()
        self.url = url = URLInfo(kw['url'])
        self.password = kw.get('password', '')
        v = kw.get('proxy', 'default')
        self.proxy = config.global_proxy if v == 'default' else Proxy(v)
        self.hosts = None
        v = kw.get('hosts')
        if v:
            v = v.split() if isinstance(v, str) else list(v)
            if self.proxy.value:
                if len(v) > 1: self.hosts = v
                self.proxy = self.proxy.new_hosts((v[0], url.port))
            else:
                set_hosts(url.hostname, v, 0)
        self.headers = HeaderDict(kw.get('headers',
            'Content-Type: application/octet-stream'))
        self.fetch_args = kw.get('fetch_args', {})
        print '  Init PAAS with url: %s' % url
        v = kw.get('listen')
        if v:
            def find_handler(req):
                proxy_type = req.proxy_type
                if proxy_type.endswith('http'):
                    return self
                proxy = self.proxy
                if proxy.https_mode and not proxy.userid and proxy_type == 'https':
                    return self.try_https_auth
            v = data['PAAS_server'] = utils.start_new_server(v, find_handler)
            print '  PAAS listen on: %s' % unparse_netloc(v.server_address[:2])
        return self

    class PAASHandler(object):
        def __call__(self, req):
            req.handler_name = 'PAAS'
            params = {'method':req.command, 'url':req.url, 'headers':req.headers}
            if self.password:
                params['password'] = self.password
            params = '&'.join(['%s=%s' % (k, b2a_hex(str(v)))
                for k,v in params.iteritems()])
            self.headers['Cookie'] = b64encode(zlib.compress(params, 9))
            url = self.url
            try:
                resp = self.proxy.get_opener(url, 
                        dict(self.fetch_args, proxy_auth=req.userid)).open(
                    url, req.read_body(), 'POST', self.headers, 0)
            except Exception, e:
                if self.hosts:
                    self.hosts.append(self.hosts.pop(0))
                    print 'PAAS: switch host to %s' % self.hosts[0]
                    self.proxy = self.proxy.new_hosts((self.hosts[0], url.port))
                    return req.send_error(502, 'Connect other proxy failed: %s' % e)
                return req.send_error(502, 'Connect fetchserver failed: %s' % e)
            req.start_response(resp.status, _fix_setcookie(resp.msg), resp.reason)
            sendall = req.socket.sendall
            data = resp.read(8192)
            while data:
                sendall(data)
                data = resp.read(8192)
            resp.close()

        def try_https_auth(self, req):
            url = self.url
            try:
                resp = self.proxy.get_opener(url,
                        dict(self.fetch_args, proxy_auth=req.userid)).open(
                    url, '', 'POST', self.headers, 0)
            except Exception, e:
                return req.send_error(502, ('Connect fetchserver failed: %s' % e))
            resp.read()
            if resp.status != 407:
                return req.fake_https()
            if 'keep-alive' in resp.msg.get('Proxy-Connection', '').lower():
                req.close_connection = False
            resp.msg['Content-Length'] = '0'
            req.socket.sendall('HTTP/1.0 %d %s\r\n%s\r\n' % (
                resp.status, resp.reason, resp.msg))
            resp.close()

    def SOCKS5(**kw):
        self = SOCKS5Handler()
        url = URLInfo(kw['url'])
        self.scheme = url.scheme
        self.host = url.host
        self.path = url.path
        v = kw.get('password')
        self.auth = v if v is None else ('',v)
        v = kw.get('proxy', 'default')
        self.proxy = config.global_proxy if v == 'default' else Proxy(v)
        if self.scheme == 'https' and self.proxy.https_mode:
            self.proxy = self.proxy.https_mode
        self.value = self.hosts = None
        v = kw.get('hosts')
        if v:
            v = v.split() if isinstance(v, str) else list(v)
            if self.proxy.value:
                if len(v) > 1: self.hosts = v
                self.value = [v[0], url.port]
            else:
                set_hosts(url.hostname, v, 0)
        if not self.value:
            self.value = url.hostname, url.port
        print '  Init SOCKS5 with url: %s' % url
        self = Forward(self)
        self.handler_name = 'SOCKS5'
        v = kw.get('listen')
        if v:
            v = data['SOCKS5_server'] = utils.start_new_server(v, lambda req:self)
            print '  SOCKS5 listen on: %s' % unparse_netloc(v.server_address[:2])
        return self

    class SOCKS5Handler(Proxy):
        __new__ = object.__new__

        def connect(self, addr, timeout, cmd=1):
            try:
                sock = self.proxy.connect(self.value, timeout, 1)
            except Exception:
                if self.hosts:
                    self.hosts.append(self.hosts.pop(0))
                    print 'SOCKS5: switch host to %s' % self.hosts[0]
                    self.value[0] = self.hosts[0]
                raise
            if self.scheme == 'https':
                try:
                    sock = ssl.wrap_socket(sock)
                except Exception, e:
                    raise socket.error(e)
            sock.sendall('PUT %s HTTP/1.1\r\nHost: %s\r\n'
                'Connection: Keep-Alive\r\n\r\n' % (self.path, self.host))
            addr = self.handlers['socks5'](
                sock, sock.makefile('rb', 0), self.auth, 0, addr, cmd)
            return self._proxysocket(sock, addr)

    globals().update(GAE=GAE, PAAS=PAAS, SOCKS5=SOCKS5)

def third(daemons={}, modules=[]):
    print '-' * 78
    print 'Initializing third for other python applications.'

    import sys, os, thread, time
    from types import ModuleType

    del modules[:]

    def run(*argv, **kw):
        if not argv or argv in daemons: return
        mod = daemons[argv] = ModuleType('__main__')
        def register_stop(cb):
            config.server_stop.append(cb)
            modules.append(daemons.pop(argv))
        mod.register_stop = register_stop
        mod.__file__ = argv[0]
        import __main__ as sysmain
        sysdir = os.getcwd(); os.chdir(utils.misc_dir)
        sysargv = sys.argv[:]; syspath = sys.path[:]
        sys.path.insert(0, os.path.abspath(os.path.dirname(argv[0])))
        sys.argv[:] = argv; sys.modules['__main__'] = mod
        try:
            thread.start_new_thread(execfile, (argv[0], mod.__dict__))
            time.sleep(kw.get('wait', 5))
        finally:
            os.chdir(sysdir)
            sys.modules['__main__'] = sysmain
            sys.argv[:] = sysargv; sys.path[:] = syspath
            if getattr(mod, 'register_stop', None) is register_stop:
                del mod.register_stop

    globals().update(run=run)

def misc():
    import os

    def Page(file):
        HeaderDict = utils.HeaderDict
        version = utils.__version__
        listen = 'http://%s/' % utils.unparse_netloc(utils.get_main_address(), 80)
        file = os.path.join(utils.misc_dir, file)
        try:
            with open(file, 'rb') as fp: tpl = fp.read()
        except IOError:
            tpl = ''
        def handler(req):
            req.handler_name = 'PAGE'
            if req.content_length > 1 * 1024 * 1024:
                return req.send_error(413)
            data = tpl.format(listen=listen, version=version, req=req,
                    server=req.server_address, client=req.client_address,
                    method=req.command, url=req.url, headers=req.headers,
                    body=req.read_body())
            headers = HeaderDict()
            headers['Content-Length'] = str(len(data))
            req.start_response(200, headers)
            req.socket.sendall(data)
        return handler

    def Redirects(regexps):
        import re
        from urllib import unquote
        rules = tuple((re.compile(pat),repl) for pat,repl in regexps)
        def handler(req):
            url = req.url
            for pat,repl in rules:
                loc = pat.sub(repl, url)
                if loc != url:
                    loc = 'Location: %s\r\n' % unquote(loc)
                    return lambda req: req.send_error(301, '', loc)
        return handler

    globals().update(Page=Page, Redirects=Redirects)

########NEW FILE########
__FILENAME__ = proxy
# -*- coding: latin-1 -*-
code = 'xÚRÛNÃ0\x0c}ÏW”\x07ˆÏ\x06cÝ4\x01í²Oà\x07ª¨ÚÚl\x14ÊŠ:\x1e\x10âã±“v\x17\x18\x12‘*7Žs.ŽK·ŽŠ¦t”çF"\x12\x15ñ¿_0´©›Õ²Þ–®¦ýI¦¥X[¨¨ZÓ!?Ú¸wÒy^6Ežk Ú\x11=6[\x07\x08° 3èëò\rDM[âZ\x12\x19M§\x0fH,Rêy³±\x1d¬Úm!èÀb`@wÀ-Ý3\\êI=Â>p™!\x1aó.|¬.Z7m\x00¨¶!Š\x0e/š7sŠ\'\x0c–¬Z·|9äE‚‘ûÉ\t‰€û]ì‘#WïœGë;ÆVB´†BS0Ÿww¿|\x02WÌÈ\x1e\x16\x0bb+7Ý\x198=™ÍÐw\x00CÃ\x1céyòN ïÇ¥o…úåçÄÊE°Ò\x0bÅYm\x1cþÐ¤ÎøK¬ÉB7­’>üä:š•£;\x02å>\\A¤õè¹‘\x07\t£P<µý\x0b\nó¨t~$õg]­xˆº§ëŽ;·ÿ\x1a¹£yí\x0b¬ÑZyx¨o\x1eÇF¼¶ÝËë¥ö›ãå¦Ôöÿ¢ÖÆ·ªÛ–á‰ã°ÀÓ³ ²Žúñ’ã¤È¹ø¯ ¬„Í‰„¡‚ƒ¡€’‰þÿÞíÝœÕºÝåÚ¸Ù¡Êæ·Ÿµá–¬ÈÐ®òåŸ¾®›êçºÆ¼ß÷í×´ìÇÏÑþ›×ÝÓ²Æùû­Õó¸ÏÛñ«Ë†ð¿äüÙ¶ûêñÛé°Å™ûÕÏÝ³ÝïõÆ·ÿó¼þÇïùÓµÿý²Ô§ëÛïýþõðì™âº•éõµÂ‡Ç«¤–“Ï§‹Èá¿Ç’“Î¿¾–Íœ×åß™ò–ÕÛ¦Åú˜ï‹êõ¬ÅŒÈÈ™Ž‘žÈÿÐ˜ÌéÒ§¶ÈØ¿ÌÅºý†ñÉ¾’øå‹Žª˜¦²å“ö¯³‡íó§ÏüÜúñ†çôì¯ËúüÙ–ôó¶’¯ÅïÏï×ïÇ»²åÿ©ù»úðüÿ‰ÉùÝŸÁÎ³Ìåèß¤ÒšüÜöµÃ·˜—ÍôŸŸéßˆû…¦žÖõÕø×îÿÄœÞ»¶ôæÿ¸£ú’æâŸõõþ®È¿ú’¨¥ú¦ÕíçåúúÚÁö¾Ç¬Ìéñð÷ÇÏ¢÷êˆþìÛ¨õÍÔ¬õˆúÎØñ¼ÎÜ§íú­ÓòäÙÈ¶–¡îÉãù©ñ¸öÅÃ¿ÊÝ‡¹–þË“ž×åðÖæ…ú¸Ÿôž¢ß‘Æ©÷þ‡§ïç¦ÍàÏÇÃüÄÿÜç»ÿŒºæ÷«†¬³«ñ®íüý±¾ë˜ïå¯çŽÞ¡½Ý·íý¬§ö–ýÉÊËäî«·êÅûÕ‹‹ó£ÌƒËÿ¡Ïó‹õ÷®«ÒöÚ–§²Æë±Þ·âÙ†åþúáï§³µýÇœÎüËõî‰™¡­Šƒú„çÊßÏÍëù¶’Ç ªþü»ýÅóÏ­” ”¾‰üë›ÛíÎþÝŠ½ó“õ½Ë¹£¼ÐÇþší­þÚèÃö¼¨ÑÆ‰ó¯ƒüß‹æýÞ¶¸µŸ¶â™î«¡§×ÏÈà´Ý±ü«“»†ï²Ž—µ¿è×ßó’ãØ‹¼¥‰óæç¸óˆ½ó¥³š©‰ØèâîþÖÿ²¡Îíƒ…öÀ—³ÎÜ“ÉŽ‚ëÝ¦©ØÝ«“õ®ƒºÌëöóÌ”Èþ°™â¦€ßéß­ÂÏó‰“¹Ò×žÆ–Ï»¡ÝäÎü¤ýºðÆŠ‹ëìúßª‹óç¼ìŽ¹¢êóëÑëÒ•¥ÈŽßååýóî›ÖµÂ¼ìåÞØÿ¯Þý­”ï¬¯¹–¥Öæ×ÕàÆëôîÙ¹Ù’ŒôüÅÅ¹•§×—çéùÍÕû§ñãËìû¸±§·”÷¬É‘—–…ƒÞ×ïü›™ó±—¥ÕõùþÖžÍÛÝí¾ìªÿé’ç­´Îäìë¾ãØ®Æžïï¯Åë°ÑÕÕÕÃóõ«ü¾ÕòÍØÿÒå®’„÷šÁ£íùýÈ…ìâÁ²ÒÌÛ®Ù¶úû»ØÀë¶¡¼µ€ºà–’˜âÁŸ›¨ÉÛÜë£œúÄ­úÒîýÓþ¸ú¾®¦í­”£º½¼ÊÙüÉ˜‰÷Ë½‡”¼æÁÓ¾Ë¿òŒ¿©ä¾î³Âô¬ÒÓü¤Ž·¹Ò¤«”£Ëð•·Àã”ƒñž¬Ðç°´óšð‰ëÙ«º¬×’Ì‡ºü˜ãŽ„æØÑí“œùâ¢žÖö¨¼î©È®æÃð´æ¡ññ¾–­Ç”­²ËÎ¿Ž²„À•Ìü˜ãããí¨Ž Éúêã¢üÏÑèÍâÍ·ÐÐçèôòý‹íÛŠ™¡—äŽ¼¢¾÷Ãˆ¾ªþ§Ã€„Ñ°Ÿ„Çþ¬¥Žñ˜–ó¬Æç¥ùô¿Ÿ»ˆŽ¶Ž›£…çö¢¾¾ßßŒ¸™Àþ×›¶ÀÃ´žÜŽü¸Ã•‘ÁÙŠ¼„Ö¬Ð©ôÁÐ³ÍÄúÙöÞŠ…Å¯§ó‚Ù’éÌ×²©Éµ¡»†±¿®Ó¡äÃçÌ˜ÝÐ©œ±¹·‘¦ÞÓþ•„ß»±÷ÖåàªÃû¡×§¢š¹øëÁ¢Ø…‹¢¸¸ÃÒ½®ÉØ˜–»ƒ…ÖØ¨ÀôôýŠßª¹èÔ²£º±Ö¡ßž±Ë‡´œ˜„­º’¬Å£Ü“¿ü§Ðñ¢³Ôª›ëêÉŠâêÝÖ¸Ñ¬ö’ñµòØë¥¼‰”éûÐ¿„ÚƒŒ«Éî‡¹¨žà¿‚íÏµ†…­ÁÕÂ¥®Íæø£ï¼Ãžö„‡Ì•Â“Äö†˜½âÃƒÌÑÛ«£¾¡œ·ýÄ¸ÂÊ Ô©­â·¢áù´¯—™ç‰óáç÷á•ëò¿žÍ¬”¯Â‡§áöó›—ûÃ—™¥îë°·²ÁâÿºÓðÜ–Õêµ®‹Ý¸€¾›ÁŽ’ûÆ¦¾×‘ÆÔåû­¨éÎÕŠ©Â«ÇŸÀÔ˜Áü¥¬õ‘åÁÙ„ú‰áö·ìÛÂÞ³—ÂÚ‰¶î¯”˜ûÙ†×»ö¥¼âí†‘ä®ŒòŒç“â¡ó¼ãÄðäÓóˆ—óúä˜çøŸ­îÃŠéúÛ¬ÖÝÆ«øéÂº¾òØ÷ËéÍâœÀ±Ø§¬Ù°©…ßó”ÒžÔÇï…œÂä€­°Íæáü­‹œŒ“¥õÈÀÒ—ýŒ¯´Ëãº€³µÞºöé§£¥Œì“Üº±ËÀì÷„ÉÒ’àÈ„øÇÌÀðÏ¤„íú–åí¬©Úþö¹‡ó•žÖÖäåÓÅÝ¬­ë¾“…Äªé–ÄêÃý¹äù“›ÖßèÙŽóòèáÉÃŠª¸ÐÛ„ÍÂß¨º¼±ëÒ¢îþ’‡À±ö±Œ§ŸÁÊÁÊÁ…Á‡÷ ýòò¬ú†¦…´êÌô‡ãÍ©Ëûñ¦²”ŠÚžéÂ£ÏÏ°¼ÕÌÀŸ›Û¸¡èå¤è¶ÛïÝñ³¡†ÆÛƒ«æýýÁÔ‹éÍå’ä¥ïË»òúØ»•šÎ‚ÇçÒçÐ°Õ‘ö«’»Œ‚Î®¿†¸ÒÕÑ­èÓòôÛ—‚ìážÎÞ°¿­ÅË¼Ò°Ï»‚ß¤ßþÎæ—ï×§ÌÝþÿüðøÜö»¿ä·§ß÷§çÇç›Ü…µÚ÷ùŒ‡æÓÂß¯¨Ä©³ø™…Ó´íÃåÞ•ÒÆóÚ¶éÈÒð€à„á£ô€¥ò»ŠÈÐùÐÄ›¿´ÿ–¢Ï™§ƒ¾Í‰ø—¦÷ØáŠØŠ­š—¨û¿ß¬¬Îÿç—÷÷ËÕóñÉÁ¨ÔÉÊÊ©’•çë«öÄíå“ÔƒãíåŠÊó¿½æƒ×ß›–ú¡µœµÍ¥ãÍ¯Ã†ÝóÐ‡³Šøê®¹üÂÖŠˆÍ¸Í«üô£õ¢«òé¼«ÔÃÆ´É§ëŽöÓÿ¹¨ò‚Ô“Î–ýÔ—Ú¢øÿ¥—ùÚ´©Ç³ƒ¶³Ðï—…¡÷ÅÄÔŠñÅ§¸–›ÍÅçãº„„ì‰ÒÞÅ€‚ñ¦¯ŠÅ®þß±ùµÌåë¨ÛÉÂÓÞ¬®ÌÐ¸œ¥­Þ§²Å§¢Ï¢žº†ÍžõÌÓ–­ç—¹Ÿ‘¤™éÝ©½Ã¼ýŒíêÜÒ˜ò¬Ñ¨áó¯ìÅ¢«’²ËžÄ½Ì¹ß«ºýØç¥ô×Å¯òÕ¸ì’ÂÒþ¾ÍÓöÿ¤Ÿºú«º»Ð¹£”Ê“±²³œôð˜êÕ×‚ßÉ ïØô¼Õ²‚§›½…î®¯“ÝèÚÐáœðÑ”ß ÏÅç¶”„Ä¼üê²øðÒ¬°ßº¹·à˜ªÞùáÓöáú˜Õ ´²Æû¾ÝŒçù®Š½Î±”‹ç»¬ÓÁ·²óÝ¹ƒß½Šö¥Õ×ŠÎØ·ùÆÀÉªðÈÈ“”îÃàê©Ôñó–ÃŒ¥ÆÎÚë”ý†ßÔÁÚ¼Ù¢Ê‚Žæ¡Æõ±ˆìÁ¸Ý©»ñÆ…œ•ç¤Ò©ÛÌõ¢ª¶‡ÌïÓ„æ‡þ²£¦¬ïí²•ðÿðÈç°ÀÛŽ•Ðƒ„Þ‚ÛÈÉñÿŸçëíéâúþ®îôšÞó™£¼—ÅÌ‚“¯×‚Å–ˆ¨‡Î½³µ”¶Ý›×¸Ó’È×Êüåÿœ—àõŠØÁÜ™™ô‡‚ÆÔðžïé¿ßãÑŠú¹‰š·›û×Ž‰²ƒ¦»‹ì–úŸ³ØÈ­ÉìöÍò¹ÍÔè¦ºêÅÙë¶žû†‹ì€ùÁ¹‰úÄ¿¹º²Ÿò€Ýð“ê™Áºï«‡ýýŸåäŽ±„Ê˜øÀýûã™±‡Ñúîíá–ðÿó¨–€’Ü¡ù»¼Üž†èÁá ¢¬”ÎÛÄ¥Í«Áôßž™ŠË²¯ï‹Ó•‚«µäíÕñÏÀÞ¿éº³–“ÉÁÎ•À•–âÌµ–ë’œéŽ§«‰—–è¦ôÁ¶æüëâýÆƒ›ÃÀÏÐà‹„þ–šæ¸¢Ä¼‹÷ùÜÛ§™Ì¹Ùã‘©ÿ­ÕÙÆ´þ¾¾Ðì’¶Œ‡öëÏŸ–ÕÚ¼Ì‹‘ôÒ·¤ãÒµÉä˜¯ æ‰Œ¼œñù˜Ž™…©Õ¶æä¯¾´‘”ª×·Êù¥ ª‘…‰ß‚‰Ù–˜—Šð¢ØÁÊÚ€ŠšÁàÆº·ãðÑ©¢´‡©‹šÐ´ÀÎõÅÕµÃýî“Ëçœ–ãô—“§û…¨‹˜ðÑÃÑœ‰å—¢Áµ§—¼– ÜØùÄ‘îÃ®±úÁñŒÈëú¨åÇ÷þÈ€èë•†áÐƒ˜æØ¿Ú™ ‘¯å»áßž„²¦Àï¥â¥¡ÈùÒ¤ÓÖ³–Õšè×°·€®®ÂžÀàÎ‡Ó¤´ïÓÙÙ¢Õ™Ì³¤µ¨ùè™¤Ù˜¾³¤—äí—æ¸´ŸˆË†ï¦À™ÃË……ÝÕ´åˆ„àß…ÖÒ¬·ð•Èœ¸Üáƒ‰ñ£Æøâ½¤¹éÌæ±ÄöØ°Šã†áÂî…¦Þ« †æšÒ‘®ì‡‰Ù½ô£¹­  Äì¹ñõÂåþ•æŠùÓÆ…éÚÙÄÁ »·¢ƒ¯ÂÞÈÔ¥Çá‚à­†²à„£°Ëˆ¼¬“Ïƒ³•¡’Õð½ÈÒ®¨·”ï¸ŠÛ§†—ÒÿÅØ•¨…µŠÚÌ… É£»ËÅ®ìõ§¬ß†éšêêÂæÙ €çéííî““À·‘ïÛŽëÆ¶ò¾êÉÒ‚þÕÎ­Œº²ŸÝ‰ŽþÁ‘Ù¦ï¯‹‡´Ö äÉÖõàËâÔŸ´îœß¤õÁ“¤¢‰ÿ ¾àâíæ¬¤èŽ¨Ç‰ÆÌô‹Åš ­¶œáû·ÄÒèŸß›ÜºëÝ–ÛŠµœ­åÕ¿Ï­“æÝÁèÑÒ“‡Øð§òÜïÆ †£ÑÔŒàóøœÍÉã„‰”ÙÿØ¨±œê™æÁÝÏÈŽŽÅ«üßÎ¡ÙŠÕ«”»  ¥¢³Æóƒ©¼ÅÖëÖÂ®ª”òúŠ×Æ‹Íî´ÍÑ±âÒ²‡Øä½ý±ž÷¡œ’º­ß‹Äí¿”ÒØÒÄ®ÐÍœºæõ©˜´Á’¼®þçð”­¤øÝïÃ¢áüê‚ßëöêž¡Ž¢ÜèØî«•†›åô·þúŸ·ô¨Æƒª×¸Ô«ëå÷Žÿ´×ÞÚ¶ÝÎó±¯Ÿ¥«ûµÚÖØÞ§Ù¼þüÊ£Íü¶ÎÝ§»îºé›ŠéûßµŽµÔ­õÓŽ†…˜¶ñ¶ãÂø¹ÕÌ…ˆüÃ»óŠ€±æ‹°¹‹ü‚æ‹Œ»ÝÐÔ”—¶•ãàÐæ£ù”‡žàÕáºõÂíÝÄÎŠŽ‘†Ö˜‰ØŠñ²³ÃŠ‰Ë¹„ã±„È³ò“¾æÓã×Î»ÿÑìóêìïà„û¯¢šÂê™Áæ“ºÑÝ– é‹ªŒ¡¥çüÖÃ›Ý®ÄÄÈ‰€ì¤¥¯µìÛ¸ñµë‰ áøÐ¶÷Š›æï›ãØ›©Î·£àŽÒŒ¾ìèÓúøµŸà¸óÖÙÊÇÓÍ³òæ©å½­¥ÎÈ‚Ñ–°ÒÒï“™„ì¿Üþø£ÚÒùã³“û¬µ¶ãúÐø¢ÃÖçèÒÚƒÙ·õ—‰Àìˆ‘ÔÝï“Æ Èè‘¢™ó•çˆõ±ÝõÇåþ’©¿æ‚ö–±­Ð¬ÁŒ¡—×úŒ§é²Ä¯àß€…Ï¤´€Ùª•øˆµÆèÜ­É÷ÒÜÄ«öôÝŸÔÔ¿ä‡¯“°ü¬¯ÆÛºêžãÝñ†—Õ–Øè‘ÿñž–­Ù³³ÄÑßÆ‡×¯å°¥ó‘ÇóÔ’¹ÍÕØåŽƒ¥ÓõËà–ã®¾ÇÏ¤‰˜¾ÈíÚ¤¼žÔ³ÇšžÀ·Ù‚ Á¹œàÓ’¢²û¢¯ú‰±Ðäõ…®©†é¡²§¿Ž³Æ¸µÅÁ´™ÒåŸ‡ÃÙ…©ÑÛæ•ïÓŽÆ¬è±·©üåµÅµ§½òàÎ¹š¸ØÀÿ³±ÒÎ½ÖŽ ƒÜÿ°¶²îæ«ØÂàêÔÇ¤­ª„òßÙÛã”È±úý™Êöç““¨ÇÏ¿Æ³û®ŸâëÛëëåë˜ÿÜžŸÒ°øŸÄ”»äðçí•ÙÀ¶§Ïß÷Ë«åÇü†‰‹Ì¬‹‚ÿ¤¶¥€ƒ×øÐˆüÈø½óõÿñéÙæ¹³ˆÁïµ£ßøôÅÝ‰¹’è¦Ò•¯›ŒÌ‚É¼õŠ—Õ—Ù ÑÄ±‹ôÈëä˜¢¨§þúâ£‡¸â³ÓÆ¤þ”Á˜›¤ŒÖ¸æ¼‹¼ˆÓ†å£÷“¨Ã´ìÖŽ×Õ²Ôƒ äˆ´Ïç÷ûä‚¡ŠåÿÿÏËò“…˜ØŸ˜£‹í» Å¼¨Öß•ú˜¥ŸÒ½Çè€­ï¡ã¥®œ«‰ÊÆ¹§Š·¤±”ÜÑÂ¡öÙ¦”¬®Ü†Û–“ÈÝ‹¢ËÓÔíÚ¦šâŠ£ÖÒÆ Ä“Ÿù§¤Ï³ŒÜŸ”Ù³äµæ„´ðØÅ‹ªÊö±Éœ‹¦û’Ï§ñ¸óÉ¦‡›Ê—˜ªÞÄ£€¡¯ûÛæö¼–ò–¡‚éÂ–ŽºŒóÑ¬¬ÊŒíÔªÛ°²Ä©Ý½ªë° ìÕÞß‹¹˜œÔÅÌ…ª•˜„Œêø¼ÖÃÏÑ¤°ÅØö•’éñüÊß˜ÇÕ÷Ú™¨¼†ˆÛý×ö’Ì¤ŸžÊæ«ºÓ—¥Ýã”ä¡ÜÎà¼Š÷œº¶œ×ºýúåÉŸŠï©¹«…›ƒ¢„ãÀ‡†¶ÎœãˆÏ€œ†ŽØÏšö·à›˜´ìÑ«˜…ï¨˜ Ú…þ°¯…æâÓ¤Öž‡ï’¹Â•ÀŸªÃ’ë€»ŽÎÌ€­”½ÎÃãéÚÍ•ÚìÃ›€¨£±Ùø‘‚Ë·éìäÙÉôàïêÝ¸×â¤ýƒîÈÓ„þ¶¡éÐ´€Ú©ö«ùêÛÝ·”ÓÒÐâÚ¶“×Üå¤ò•‰‘›¸Û°œ¢ôÁÄøÚ¶ªŒ…®íš£¡’¨ºâ­‘ÀÝÀ¡«¶ÄÍºýÅ©ˆÉ«Îšò£òÚ·¡ð´Áîž‘³”äÙºÁ· ÇåÅ°ê€Òí§Øýú¥•ŒÆ­Ïš×ùë»ˆ½ù’¨ö¢ÆùƒæúÔ‰ú­Ž‡¤ÛµïÊà—žÊ°ª™Ÿý´´˜¦€‹ýÕˆ—ž°ÓˆŽ°Ôç›ì°ßÖ˜¥„Ä§Õ¥ä„••ç™›ê‘”«þ¯’¥¹±¼ŠƒÍÒÁù¥£¥Ä¢­ãüñÞà½Ï§¶û²·ç¢ÝÔ»šò»å™º™ä‹Í•É„©ÇÈ©’ØŸå¬ÓÉäÓØ–’½š˜Ž»ëÈÄº€‘¤êËï›Æ×ÌŠ®‰ÌÞ¡Áö³Ñ“ìÀû½íæ²½¾¡¦Õ§ñÃà‘Ÿ¦àà¥â¨úò´¾ã¼·À¥áÊÚÍ÷ª¢Ò¼¶Šã¬åžòÛÞ‹Ñ¾ö³Þ±Œ§¬¾º×âì³»©ôü¼öóÜõ‹‘“û÷çëåòÿÍ¯®–ƒ¢»ê±¼Óòˆðê¤¿¿¹’²ÎÜé£·ã›‚ŠöŒ¢û”Æå÷Å”Š²¢‘›ø¡ÖÀÙÆ³ºŠ“¿÷žþýÿŠß‹Ýæ©á èòûÙ½î¢€ŸðŽ‹²Œß™ÞÚäÑëÜÏÙÊ¤¨â·ˆù³ÚûÙ¬‚‰ñöÿœìÈÑ»â¨”Ê¿¼§«Ð¢«–ìóàë‘ªà™±ì¯æè˜îŠ·¡ïìßÈØèãªÆÑÊ¥”ˆàÙò²ûÝêÖâ¡› ó´é« ÇÑÀÝ—¸”ûÎÁ±ƒÖ²êÉÿ±ßÿáÒïÛªôó£Ø¦÷Ï“ì÷üì­ÖÊÑò‰“¾¯ô°¢¸ÑÔ¾Ì·îš§º§Ä›Â‹à‘ìÿ•ì¸§’þ¬»ú¹£¾èõÌ¡Â¯ê’™ÑöÁþ¥ÐÉòî†ÃËÇöü¨É ……àÂ—äÅªïÍ“óúå¡™¾Ìó’ýÙÉÝ±ˆ‚©©üý¸Œï¯Ÿ¯ÉÊ­Í¬³§Â¥›—úŒþ‰¿˜šúŠùû¬ÏŒë½»„å“–ÖÅž¨¡ÁýÒÍ¯Ï°·ý·„”Ø÷«“íä³–¢ßš‡‹å«…ü´øßæâÜÙ§ñ³Þ§ùñ¹¬ë¯–ƒø–ìŸÜˆ³çå¦ÂòŽÿÕìòÛáËû•Ò·žÒ–»ªŸý¢”¦¬îéÒ‡Š©æìñøÐÎò‘°¬§Œ™é¡§ÙîÃÏÖùØäªàÝÖ“è×øÕš‹ˆ×Â²ƒ…Ž“Œ¢²²µ”‰“ù¼Ô£ÖÒ¦…¿€¾¡Þ‹êÄÆŒ—„æíþû´á ƒÏóðéš–ÉÞø‚Ãú‚”¨£…Ñ½‚ÍÙ¯°ÑØªÝÑ†ÛÈ¤Š±”Å‚¼÷‡¨¥ÇÞÎÝÝìëÆí¼®û²á¡®½ƒ“ÀÅì£Î•¼ˆÏ¯ý¡¼ì”º×ÙúÌû¶ý¾Ý™”Ê¢åØÕ¦‰æÙÈËàÕ¡÷•í¾Î†ñòíÚî“²ÿ“ùšÊêè÷ôàÚàûãÜú¸¬¿©Á¸§Áõµ­ºª´âÝî÷ä¸š™œ¬ðÁÌÞäÓŽ¢ùÏØõ³ñÞª¿¥³Ú—´‰Œ³œö±òƒšçÝîÎËöÿ›Þ©ì†¬Þå˜þ¼¾ÝÙš¥ž¯—Ÿêª²°âë«ƒ¦ª¦’‘¢õå¥‹ÖàÑ®ä¶Û¹é™—‚žØñÝ’‚¥ô‰‘Ú‡¬åÐªÈŒè–˜«ÿç˜Ôööï¾›ïÛ¤ìß¦Ú‹ŸÃ©ùÑº°²ò­‰˜±ØŽ±àÏžç·¥Á¬Î…œåÔ»„Ðˆ¥îâÀÉµÖì¨•Ïðó‘„´¦×ñÅ˜Ù’ÌÜÊ»©ïÝøß»“ë€’—è×çŠ’¾ò»„Ë—‡ÉüÆ¼ˆÅø§¯Ÿ®ºœž¶Ï“÷ùÃ§¾‹»æ™– õáÿ–ÃÅö÷¤šÅµ‹ÇŒÖÜñžªÃž’ôÛ§Íý¬‰ŽïÇ„ŒÃì¦ÓÅ¹òì­€öú“ù»ÔõŠôßÝªµ ¸°ÖúÁ«õ·¼Õê…¾­æ‰Õ×š²çÝù”ü·ž°·§Œú“Ü¡Íú¶®«¤ë’€§îÌ•ñÁ«Ù“Øú°ƒœÐÇ¹¥¹ÄŠ¯Ö˜æˆ»ÒŠ…Ì‘’Ã„ÞÑèü—ö±Ú¤–‹ÍÌ®ÜÌŒý„Žäê‚Èü³û‘ïàÏ—Ù†þ†¼Øé“±Š¹âÝ·îö¸˜®ŠŽœ‚“œâÏåë¦Ú€ó¥³¬“ÃŸ†Å²ôž¢ä€á‹õò¥ÑÌÞó¸ìéøì±ˆõ‚éëèÌÏ¢¦­“Ñ¨í—¢ÑŒÇÍÒœÎºˆòÍ“šïÛžðÛ¢‡¾ë±Ü •Ñ¾¡Ð‡º”àÆÉæšèÐëÆ×—¤Ú’åþ–Ú üˆŠÔùø¬ÿÙäÀð‚Š¬”«ÈèêŒÅï¨„Áµð±´ÉÉ£½·ßªÂ•’½‰ï¯¹ÒòàùÊ¨ûÙžœèÙ˜í¸­¼á×Œó¦€îûÑ§­‹äíœÊ÷ã¿âÃÌ±ü°¢Ïç£È ò²Žºà¥×Þ¨†¿ˆêÁÓãÄÐõÐúúˆå¿Ò®„ÀÖûéãØžØÈŽ­ÔÁ¼Ù¨¥¥Ô¥¨Ù‰™§œÅ´äÄ÷Œ‰òÁÎöéÑÇÜ²Œ–¦õª¨÷ÚÕÎß„ÕªÂ‰±¿Ð£œØØ™ûâòé¹³À´˜ÕüÂ­˜Ø¯Èùêý…ýžº¹¯’ß³Ù—Õ³¸ØöÈÍ­–™Ï¤å¹ûã„ßÓãßÅóïÃžÇÿ§éûîäàÌ«©»†ª—…×ÌØšüêñ§í÷‹Î£¹‰Ô‘Ñæ·‚ÔãÄÍ‹ŽÑë›Ç¾ÒàÕá°¦¬âÑÅ™Œä”âß·ñÍÞ¼ìçøùŒäº¯µéÈû»Îˆßœ«ì¶ÁÊ‰Ë™Ì”¨³·µ‘å’ÌÔÉ²ÊûÁØåÛ¼íÖöÚ¼¼šúžŽ÷£áö¾ÇÃÁðÓð¼žÞÁ½áÈùËö‚½áÌœžø÷õ¥½ß¹×ý¨³ýðëð÷¼žçÃÃÏãÛ÷ø×½¦”ŽŠâŠÀÿÀ…é×û‚Þ²ýÏÍ²Í–’ëÜŽˆÁî²Œ–Ä•Øà‡ˆõ£ñÒ‰ªšš´Ø¤´ÉÆÞ½²è·Ã˜ÌüÝçíþ¬Ãü«‡’¦ÓºÂ†Áô¡ð¯»”þ¯‹Ü´¦Æ ¢µÆúÒâéÙÓÁáìíÁßŽì»¼¼òÝ°æŠ—«Ëª·ƒôµúÒõê»¼—ú‰ºåãðÕÔ›ùÙ¹…õôÓÖÏÑåÑ¦ˆ‡«Ð‘ø¬Ë„‹ºí·ñøþßëê½®÷íöúÛ–õÚî¬›øÿ§ÇÈ¤öº™¾úäïÑ³ß§’ñ“Ï‘ÌÅœóˆ¼Â’¥¤†šôÒÓ×²É¼î¡ªõý›”Ï’¿æ…ö¾Ë‡ÕºÞß»˜ôÚÖÅØÄËó£ž‹‹ÁØ¦¤ Ó†Ãã¦ ƒèÜ’«ðŠñªýÞÀÃá‚áýÍ°Ë¿Ë°ˆ±…øá€¸å¤ð’“ïàØ…ðÉÌðžÁ±©®Ï•Ž‘¡ðç¡äÁìñ†Ñ·ÅíÊ±ãÇ…Œ‹š¥ øŠƒ¯¬Ñ¼ÅˆÛú°íàÁÜ­õîô‹íèå‡‘½ßæôÍÌêª¯ËþÐ×§úá±ÃÛ¾•‹ÊÁÖ”¢¥©†„Ë‰Ð„Š‡¢þÛš«âåø§ÉŒçí·Âè€¸ÊüÛ¨­¡ÚñµÐã¶¹Ú­½¢ôí«‡å…•œ€ÙÌ±’‰Ðò±Ä³²¸Ü„öÍÂÏ¤¹¼¦£÷ õþ§¦¤—Íç•é¸ÁŽ’ˆþûñôÁ¨çµýëú²¾½ë·®°àšàù®ÐËêÎòÔË–®«Ÿ©¿©¬¾´ë¢àš¯œ¿Þß‘Ö×ý°×Ì±¶èº¿¿Ä¤úÁ®«ç¥ò¤¨ãÒû×ª·³¦ã¨Ÿ£Ëºµ‹ô›Œèë©·Ö ”ëÏÄÄüùÇ‡ƒêèœ°Ê–«ô¨Ú¥¤´Ï™¶ÌÈš×éÑ¬å¾¸ûÒ’öÓÈÿÆùÍå¼Ñˆ¿üôßÿÀ—ó±õ¡ê“Ýó°­Ñ·©ý—…Ïýù¶í…íµÔŸ÷Øòõé£¸ÏìË¯·ÞÃÒµãõ‚Ô¥ì×¬êßŽ¼‘±ž‘ÇâÅ½°Ú‘ÉÉìÌ–ÿ¦žÁ­”ŸÉ³½“¼Ð¹ßŠÞ­ùÖ™¢®æ‹™Í¢ºœ²ÐÔµõ‡á•š…éÖË›ŒÿÉôõ¹ÕŽ´ýŠ« ©ÀÿŸ¬¤Úóõ‹ã…ž¦æˆ€—®¤ÊÓ¨Ê¤Ô…„ÁÄ–ú÷Ÿå°×à¦á¨ä„£´°ÛÑä«–˜ÒéÜöïéíÏ—ÔÔÞ” Ó€«¿Ý˜âÕÛ¦È´ ‡ÿ­¹§Ë“«†‰Êñáò ‡û½ð®ÊÔõÁ¦‹è†È…©«¥¬†®¸°¬›¦×¥ËªÇ¦¬Â»ÆÅä£‚º“¢ìÛ‰ßøŠØñ®¦°•ëž°àÌ›ï–ôÜ‘­ªè‡õæÕÕ×ÅÆ©ÖüªõÂýÄôÑýÞÕ˜ý‚î‡ø«‚«Øµ¬–²Äñ–æçÂûöÛ«÷Çì¶Õü¥æã‚Ü÷äí¶Êë¨ÄÓ»ÒûÐŒ›­çŒÊÀþžÌ¬ØâÍÎ¼ Å£ö¶’Âï¥Å„»þ‚¿ì ¥ÿ–¦ÎËêÔâÃ£Ã©Í ì§¼Û”Ù…œÝíþÂÚ¿ûõÇûëÅ®ô¶½“¶£µËÝ½ØÕíµÍ÷õ®Ä¡Ö„ÐÅÒÌé›ß˜÷È›àÝ€µãÌÂÄûæèÑª÷®Ý ûÇÛŸä¡°ÎÐßóÔ‰½–­ÖµÀà–­Õí¨¨¢×ù³á„ÝÒ®¼Œç¹á‡œ Ÿ€˜ÖÊÙÂïý‰¿ˆÕ‚÷È¨À»ÖÐæÞçíšœ«ŸðË¿•Ù‡Š¨ÿ¹²õüº¨ùã·Ó®¦ã£·™ù‚ƒ½‚úªšÜþ‘¡ ŠüžÒ£Šê¾ˆÊ˜Ë«¿¸±Æ¹–¥”½ß¸Õá•‡€™Ï³²í»Ê•Ïøäÿ£©‚°¿ä€ÿöìÀÚžòà€±‘Øªµ¸­î–ë¸Ü Œ­‡—…’¬ðÃ«Èííœ¬ ù¦•º§­â†¾Áñ­ÛÍ¬©¡šÞÓ‰ÿ»ËÅûõ±‘÷ù—ã”ÃöÃª™ÿº¾¤ï²ØÞÆµþË˜—êš¸ôýŒëžêÛÂ‰Å¿ð€Õ÷€Î¥á´¯ª‡Å†©ÑÑå»Ã÷ÇÝÈÝöˆ‹¼°»ž–ÖÛÎÄ÷©ÂÛÏËÒÂË¢µ¹•ôÍ¨·©÷Œ­Ð”©ŽÂ›´ü¦Ò•ªµ‹Ÿ¶ÍÍ¶î­ÔåÔûØ§²¾‡¤ÿÏ¦²ìöòÒÖú‘ùˆž‘ôÅÍ©¨­¦‚÷Í¨ªÐ®‰”ŠË€»èí’œúïË¨•‰’Œ“è­ì”—ƒº³ñÒ®ËÚÛ›ÛàÛ·ƒË’íÀô™ˆ¦‹ÔÞÔù“Ï¯¬ø²üù±ßðïž°ÈÝ¯ŽÆòƒ„éà¶‘ý©ÁòÚø­ß›ÁöýÝï‹Ÿô‚¥éŒîƒÒÖð°›ÈÂÛ“õÅ«ÍÅêúí¥®ÄÈŒôÉ™Ô‹ŠÂÁÕñýáãäªó÷ÃÿÃŸ ©ÆÙ÷“×ò…¦´áƒ”¼Ø¨‚Øîÿ‘‡À£û¥Ï¤æ¾°ÔŒÉáúÀÕÑÁçÖ•öÛŒ–¯ÈÕÆàÅêÎ™¸ÔÁüºÄöð¥€Œ‚çÜÞóƒñ­‹šÚÔÕæÞÀöŠÃåú°”¢­Œ©åï‰§¨ƒ­ŽúóµÉÓïäÂ©•ÃñÍÔÄèíñûªóäü‡¨Ž„ÄåµÑèÔ‰×ú²¸ï«¿Å‰·ÓŽ‘ø–¬§ÆÁ¹€îÅˆÓêÙì†Ìîºÿ’Ñ³‚Ò×Ô¯¸…ÉçÓèˆºù‡Æ­×±ÒŸûî˜õ•úÆÝÂÌªÐ™î˜ƒŸÛéÌêã©ññŒ·ÑÝ©„ÄÚñ¤àË›È²ß¶…¥«‰Õß½þã¥Æá°€¶é³ñŽèåÕóØÓ†—ÄÄ€Û†£€•”ËäÎÅƒƒÆ¹«ºÒú¦¯©èø´ŽØÚ­Ö¥¤â¤µáÿÆôß— •…îþ›î¥˜ñü½Ñ¯åöž¡º‘©·ŒðÐ¹¡ä®ó—Ú”¼ÛË‘éÖÑòÆŠýâÿ¯‹‰×›ì™ŠžÐ¤½¬Õ¶¹¢À„ÔöÆì¨Åóš¹±Ù¨–ß¦íØÏµ¥È½Å¸àÌ»éßÖ·«ÊÉ… ûêÉ•ÀÏÿÒÕéøµûªØÿûéÓØó®äð°£ôô«ÙžåëŽïîÂòŽú·—è†Ë¬ý…ß°‚¸Úò›ä»µÁ÷‡£Ð­¤³¥ÏÍŸÒîÝÁ ðŸ°Ë„î«ì¢÷ØÈÆÆÔÞ«§ëÑçå„ýú¼—Ùèú÷šØƒÒ¨ÞÉ´§Öà£´©›«Ñðò¦Òˆˆè³«ŸÝ»‹î™·ãËÝÝ‘ìä‰ÿ»Ö´ÍæÚ¡Ð¯‰Íã”Êœ¬ÝÈó¶®Ÿ¤Šâ·…ùœÊ¡·Ö´Ó³æû»‘÷˜Œ§éöü ÅÚòÙ–áÇéßòø¢’¹ßƒÂŒˆêî¬»†®ŸëüéÅëï««¢•û±ÕŠŒàãØÜ¾¯©ÐŠÏñËÁ°Ì¡ò×•Ê•…úÑÕ’„€Þ³øÊû‚éãˆ¥Ïò¸ñäƒÐ¨‚«öý… »Ü¼Œ«Òæê™’Ïò¬àß¹÷°”¢¤ƒ™Ô²¿ø½Áƒœ¥–”Á½¨«ÇÝí²ÚÖ—æØ‹Êê×‘ÀüÀæ³©Àá‡õž»ÿ¡´ñ¾ÿ›ˆâ³ýêÔŸ¨ÂÉÂ…Þ©Žá–ßÂ¸¥Ó×º°‰çÞÌ“Ú‘Õ¿š¦êžäîàáþö…š’Åï‰óá†Üù…Òƒ¹ãÞ½»Ï¥ÔÇÉ’¼ïÓíþŸ¢™––¥á•ËØøðöÇØåÈ¼ƒ«Å²·ýå¿ˆ†ÆÛí¥ôÚÚÎ¤¼‘²—ÞÐ±»÷Œ®Ü°§£Æã„Õ¹ùð¦Ü–ùÎ¿¬°ßÚªÐ—ñÝ³†â°ìÚ¼£ ªý¤³œ±ÈŽµ˜Ûõ­„Þç³º®»­çÆ›Ð¯þˆë–±‘Ë¡þ¼ŸËŒÆ·Ä˜ÑÞ›ÓÃ…ó–æÄÀÄ©¥”ñ§é“¹ÀªùžÞÐ¦ìÙ×Ò†ë±Ž•´ÐÁÙˆ¨ÊÊìü³­¢ž“Ùž¹ºñº´•ÄèÂçö‡¿£Ö™ÝÕ£¿”§¬¯ÓìÃò—ëïü¦ŸÇ±õòÝ°Û»½ƒü£¯Ãßå·øí­¥×óŠ–Åü†úŸ‡äè¹§¯É¶š°ÝÈ½ñ«ÆÎ¹ÏÂÔ«¢øæŸ¢äòâüüÚçâ±‚¤Ëöë¶á‘©ñ³£‘ïâ¹í‚¿¥¼»âêÎÉ¿¾ÛØ’äÖ½òÕ³Ïð¿ÑÞæÝÖç†”ðÒÈðŽ «¤‰Ÿ´´Ö…¬¯¿¤²ŸœÞ‘¼³©÷ÃŒ÷äé¶Óáš„½¬»Àê©‰àä¤™œê»·‘áÝÚÔ¤ÿÈ¾µÑýÔŸÂöœÛäºÎøÁŽã¹›·ËÈù¨‡Šæ½ª¨­í˜”ÑØ§ñöÑÄ‹»ÅËÒ×úˆÅ¤îìÞÄ•ÌÊÍÀÊ›ŸÉ²“‡®æ·ÖŠ«® Æˆ¼‹²ü’ÁøÙãë¸­Ïå ¥¹–çÝü¢Æç­åžõ ´·ÆÇ™ª¹‡£öîÍØ¶À­Ã”Ï¨æÄíÇÓú¤åÇ«úÂýÀÅ½’µÆÙ“ÆæÆÚùÒÓ¿ÑŸ‘—‘¤’æ”Ÿï§”òù»ê®Ø à…˜ùìñ¯¿‡“°ÆœÙ´ ˆ‚ÿžþÁÞ§¿‰ŒíÖ€‹ûâ¸Å«ÇÖéÊïÈˆ”«±îšÐÎ§áõ¹­Ûð‰–“¢¦ƒÅµºÙ˜æ§×ïíÃèþ…»öÃÅòçÑƒö§˜Ù”ÅŸå¸ÞÇ¯ú½èÑ˜»Å‡©»•»‰±Ê·È«å­ê±ÂäÝ«–»î¹¶µ×·‹¯ü¼ÜôÜîéÍ¦×‡•ìÕëÕ€»¥ö±›Ø«óð¤Öß×Í¾®µÜšèò•·›Â¥õÓùëúéßŽµÃùúŒ¿ÍÒàŒÈ¿Ý¸ò¢§˜ƒ€‚°²–«¿Ê¿ø¢¢„ç†ÔÑÆ’ÿùÛò¿”Éã¿Ïê¶£¢å”Ø¥Ðæ™ÉäÔüñá¬ÁõŒ“¬âË‘§Ñ…µ€ò™ï“æý‰¼ßÀµˆí¸ð´ž©¾èý‹ýÿþÁÂ¥Ñºúã‚Ë‹ÉöÒÅº‡™²òÇŠ„³÷Ùð™Ð°íÃ™È´â«Ï‘ ÉÀ°â§ñÓ€±Æ®®„‚ôÜ˜¨‰–†¥ÛàÙ­ý£Ð¸¤ÞÒèÜÅ’ì’ô§ç‰ˆ£¨Í‹”Ñ¨‹ªòÂ§¡Þ§ŸÔ¡ŸÏ²×ùÍÁÄšÛâ­ü©×ŸÌÌ¹ÛÈ‹À¨ÒÈáìšÙª€ÏÌîõ¨Ãž¹ã´•Õß«“ÎÏßò‡‚‡ä“°×û™éôÃ£•™£ÒÑò×‹ö†«ßáÏÀÔá–¬‹èœËÄ‚¼©šÒø¾ºŠ×’áÅÉ·â Ýšáµ¸Ÿö Ò§þÏÖõÕ£õýÉŠ¹­ý¯«Ôîþ¨½ý”šæþýÄŸûñ°ûþ¬¨ÔÙÌô¸íÄ°í¿õ«µ‰îƒ÷´´ˆ±ï¯ØîÜÑ¡¦™ÚæÂçú¯êóæöæµ¯Ä¥°£¤ÐŒšÈý’ûŽä°÷©…Œï¦¯ãÁºÃŒ„›ñÜÓÚäŽŒù¢ÕÜî¢¤øÜÈ¶™±ŽÂÊªö¾°øæÏªõ³òÜ¢—Šñ äÐ¤®ŒºäÔµÂØ¬¡åôÁ÷ÅðÁ‰¿ƒ¾Áë¡Ý¯×ž¾ƒ«õéÕÿŠ¥æ¡¼¥úøìï˜ùŒÙÊúàÒø¥ñòÇù–Ò«üè¯õ²Ûÿ–Ê’´©ôé¡—•’çÝ¬æÄØþ¬¿Ð¬ÄËÛÃ­Ý…é£¢”õ‚ÒÜú¬¸«é–¡áÿýœÜÚÜßÞÞ²›óãç“»á´ãÿ—œß¾ßßŽï‹®«˜Ñò¶¯ƒé£…åÆðªðÉÃÜ°¶­€ä¶ƒ”ä•ˆ—áÝø¦´’ÿÆþÖÊˆÄÜ¥¦ËÕ¯ÂýÕÄ‡Äš¡®¢Š¤¤×Ï•×Š¤‡ßÈËÑÁÎŠÇ·Í”Ç½±ˆ‹¼–ÐÄ­õ¾„õýÑõÔšÄë ÎÃÞÀ­§ž†Áº§£°™­ŠÁ¸¸„å·ŠºÞÚñ£¬ÇÉñ¿ÏéŸ›€ºÓ®Ý¼¥˜ÝÚ§ª…™äÊÉÝÈ­Ë¯ªâÄÚžþÜº¦¬æšÅŸŒß†¨ëíß§£ãÞ´²–ÄüÅ˜êç­’Äåúš·¸±›üï™¢áÄÅ§ÍÌÉÑ¼ˆ²ÖÅªÜªàøÒ‘Ä¦˜Œ¯ÉžÎò•¥ãžðã¢Ž˜”Ù¢‡§„èè‰÷©¸¬›«‡Óý«ëÜŽ…¼× ‹ã‰ë¾…–Éæäÿ–áÚÇ’î×‚Ý’Û€Å»ÜÅêËáô¢ê¸ÂÅàîŒÍô¶æâñ—“€È»ìÁÐŸ«Ç¬Øõ„ýÿÉ‡Ê…‚›ÂÆ® ûÅ²ÇâÙš˜ù£Ì…ñ„¡á²«¨ÃâÅ’Ñ¶ÍŸÌ±¯¤€ØÅòñäü€ÝéÓëèü…“Å‰¨¡ÄàñÄ®Ø·“µÕˆ‹˜Œ¥æ¸Ñ¯ÓýéÜÁÙÚ–âÔÂüùœõÝ¤ýšâç²½¨ê‚ÎÐ¡ìÓ—ˆ×°¬µ­¤Öº™•¹¬¶£´î·¡…›½¬ýÒèªÐË½Ö‚ù•¥ƒè«–ú™Á¥µí’ÜŽÄ‹ñ—µÜ¿Ý»‰žï£È„ðöÐ‘Ïçú™ÆµÌÛ¯ÅóºŠ §ŽÔÒàýï£Úîü«óÌ Ã•ÄøàÇÀãÚäâ›™›æ—³¬¥ªðàå³ëò‘ÉÍÜìÃâÇÏ„Í½Ô…óÖñ×Ä›•Ê¸Éß®®²¸—ÄàÉ¬œàþä›¾ÞùÃæÅ¢Å°­·µ»Ç¶Ø¬ÚÄÜ½÷¯ú˜–Ê¹÷ŽÊ“Ó»÷ðÈˆä–„ÎêâÎÇ—™Ô®’ó°ö§Èçø³ƒ†”ŒÙ«§Š–±¼§ìé¨—Áö¶¹•š©ÜËÌŸÙ¼Î÷õØÝ¿³§Åë¾®‰ßÙÃþŠ‰ý£ðÈÏæºýËµÔþ­Ë¾Í¯¨œÞÄÅÍ­ÑàÄÿªöðÑ„êí‹Ñ³´·óåÖÿÂ‰ŠÊ‡¹ÒÄ¾¬Ðê´øÆòäÍ´¬þåêìÃžÈƒ¯”¾‚©‰Ûž†úÒª’£©°ÍÀ‘›¨àÞ·°• ªõô†ÞÉèÑ»ÙÞ†è»¬àï—£££Õ¾¹È‹±À¢½¨×Ðšçµýž‘Ïö¡½¡Ñ¼´¿€Ž¤„‘¢¯¦ŽÈÞ…¨º¯‚¸Æ¾ÙˆñØ‡ä£Õ€õ›Š¼¤‡†ðÊÍöÁ¡ÉŽÁÚØ½»¹ŠðšÜ©ÝùØ¥ÚÅöçÒÎ°¹Ý¤ôßáÆËÔ…†šÙ¹í·…Ø×Ú«‡¿Àôˆ°ð›¼»èÀåª«èô‘å¶³ ê’Ö­éÉý¨¤•·Æü‡ô”®Åè”†ÃÙ³ŽÌ”šå«§–Ž¬ÁÜÛñ¸¯¦å€çæÚíæ¶Ï›Šãÿ±åÚ¢Þˆª­ÄÚÈ·±ä¬¥·ÔáÎâäùÀ€³Ä·˜òìÚæøšùòÅç¸©ßµÓ´Ò•“©ò±‚ä³·Ÿ£ª»àãÒÖ¸¯Ý‡Æïåù·Ýí £µ¸™Ê”‰°ÃœÏ§þÀÕÁ°çÔ‘«‰£­ÂËªÌ´»„ôò¼«Ó¼ù¸š¾ü›Ãçê´Ë…ñ•‘ìªªÙ»‚—ØÊ´æþ¦¬¸Ê×õäýûØ÷¡µ«Ú«ü£Ì‹êéý·´™á¶ëü§¦µþôàß¤ÁªâûŸ¼âª¶Ö’Â€³ŒÑ›âøÎâ‹ê«Þè¨åÄÍòÆÍŸ¹’¬­íÉÔÉ§½ÄñÓÕæôÒçÍ·‰¹ÍÈì¾¸Ö±Œ—òÊÿÊ‚ÎÔ”»¹ì«¯Ë•ÀÜúøøÿ¿ž¬ÌìñÄÖ¨„€Í¼ø¸°­ñµÆž˜­˜¤˜°½íÏ…ûêˆ¯‡–š²…ÎÝ—šœ¸ÙÈÕî¯³òõ„¿œ×œûÃÞ– “õ“ö‘®œÛ„´Öýãóî—ß›úí¾ôÈº³‰ÈåÕ³£Îõ¬õê¾‹€ÝÁÇŒáé›µÅ’•žÕœ¥ž©ÝåôÌäî¸Á‡Ž·”ØÀ©²õ·Üª¬†ðÎü•ÉŸº­ëäýƒÝ­ªýûøÊ¬ú¥ƒéì¸“‚îÖî¸‡¶ÿ¦©¡œÞ„¬‘¸ŸÑ»’¤ÓöÕ¼ºã®Ü¶ à‚õ™Ë££¦†êã×î·¦°ß£ç¿àÍúÌ–óŒÚîñŽã¥ñÐ§½®ÃÛ†ö–©¢ÇÕÜ×·´Ü‡òç¢õ½î«Üè ¸¾Ü¾î—“¢Èå•žš¥‰ƒÞë¯’à´Î²ÿ—µ©¼Úã÷©›ÁÈ´çÓª½êÚ¤³õÎæ˜á×û‡ú¢•œË±›ùÀÿÊýëÛ°‡¯ÝÉâ­Æ®µ‡Ã¶Îú›˜­”—¼ü±ßë§Ô«ëûÍÌñë¢ÎšÏÉ”ÛÜŽãÔ­‰×Ñ½èÉ¶Ö…‘É›ÙŽ—±é±ÀäÎ¥å½Ï‰¡Ú»ÊÝáé´îë±¨Ÿ’ù„Áà´þŠîºáÖïìãÖ‰ÕÕ½ËÈ‚œøêÝž¨Ò”¹’¢œ Èö»µšôçÓÑ©°Ã•‘ýíôÝŒ†Òº¸Îå‹¾ø° ÊåÛ¤Îƒé ’µ‹” íÂ¶Üµ³ÒÁÛ‚Û÷íÚ©«¤Ãž¿‡êå¡²ºó…Šîö°æÏâ¯öñ ’Ó›§³ÀáŠýœ‰Ž’½ùåóÒÑžøµö¶þŠÃØ–…Ùò–Í‚íç¢Ö’©ÖøÞ’øÎÉ§¯Ö¸„ÑƒÃ¥ÖåÑ®ˆÞÇÂòÙ‡Ÿ´£Õ¸©à–½äØ¤æøÕ­æ¦ó²Þ·¨ÌÊ¾ËÕâÏêöîµ“¨¬Óºüˆ¯ÿ×óåî‚‘¦¡Ÿ’çœ»¾éÏƒ¤Ù½õç›˜Ê¡«ˆ¶Ÿ ©¶âÄ³”°­£µå¶îåˆš®å¡™£€áŠº½ÈÙ“œÈ¶•‰Ùžé»‘ÈÑÓ»â†¯Ú¦ñù¬ÿíÉ³ª·‘â¹¼ü¤›·Äí—Ðº¢ÆúÌûž¨çŒÿƒÄÎ•íþé›¹Þ†£Ü°äÄºÒªôç¡‚®´ÜÊŒØ³÷¡ñš¥ôû‘Š‰áèˆï”†òä­úŽî¨ÇÃ€˜¦Ì·Íê§Ý‰–ê›ŸŠ­ÿý½½ùÛÝàé˜‚’þˆŠÀê³üôäÀéÌ°Ê£°ê¦ýã›àðýÆèŠŒòÔÞèÝöÐÛ‘ÒÎû­Ø×å®ìËù¾ÞÝÓ±Ý™µ¦…Ò²·¯²Ã›­†«¸Ù‘£ò‹Ò­ˆÂö¦·Á“¼®¿‘òï‚²žÑ£ç¨±¶û¬•á„©ê‚•œŸìãÎ¾û˜…Ðçî­³Ûý”âðÝ”‡Î¤õÅÖ©é¬¢Ù«„Á£ÈÜ–é‹éò’ß—›ëªÏ•Ó±¢Æäªô¯‚€–¯Ùõµ›Šè±œÂò˜•ñâªÂ¦¨Š®ÍšÕ•Èã‘ª–™¤¥½”±ôŒÏêœšÂÉÐôç™õÇžé£Ùøòšé‡Ñº·ì­›è¨©ûØòûø™‡¡ãÙ‚–†‹…ãÖãÆ”¨ƒŠ¬‘Ú³þ›ÌšÖ‹ûµù²Å ÙæÎõÉÝ¾ø™—Õ…Ð×˜ªç’ÚÌÙ¬çÒÇ²·ÒÛ¤±¤ìäË·ê·Ä«´±½ºü‡›‹ãá­…îò¤‡ÜË´Ää«Ý¿¾Ì“šçÏü‰ôÏÊÊÔ¶³Ýê—‰àáéÔëëóñÏç©þýµÃŒ‚ºðÖÝëà’à«Ü÷¢…Þ¼ôµˆÝ£¿Çñ‚‘Ë¿ëèŠ€ˆ †‘Ž€€¬äÈ®•Ý·ÈôÔ¡µ»Éöá ñþ€‹ê›¥Å…êÔ¾õé™¾É³á®±Ø”ÿ‚Ïñ–§ä‹÷ÉÙêÙ£ßÜË¿žì£ßÎÔ“ˆŠ‹œÝ‹Öå‚‰ò›¾´¯â¶©÷†–œ·é£´·ñÖ·°Ï¡ÒßÔ—ëˆÝ¬‹Ó¶ù‰çßÓüü•Éø™­Ðªóµ‚­¾ƒÏþ†Õ¥­û•õ‘®–øþÝÌå¿Æ¡äš¡æÔ¿–èéô’‚½ÇåÝ‚Üò¼çõ©«‹š¥¯åÕ‘¡‰ù×’¨¼Àìëˆ¾ëèáçÕ˜¦µâô’Ñ‰Ìð‡”ââ®¤úÄ¥õ•¥÷Ë¼Â™‘ùïî¦÷úÈìÔ×ùÛÔ¸„æ‡·‘æ‘ò³“ƒÕ©í¿ÛŠ”æÖîöä¸„„ªæã¨å¯…µÝ¿Ö®·ÃíÅÉ¾¼‡»åð¾›Ž§àå¬þŠïÌá’€ª¿™¨–µâ“¼ÞàîÏÚ·³û®ÔÐÛÔòà—ð˜Ÿ„ªÀ•…ÃëèçÀ¥—°óòÕ†´ñªÜøÎÄ•Ã‘ð¦ÂáßžÁÊŒÏ¡ªÖ¨¤ýÉ¦Ý¶‚çÀ°¥Ñ¸¨‘ €ì±Õé£Ã¹ý›´¤üà¸¼ü½ÜÅÎÑ¾ÕÒ²¥‡üü­ÙÁÃ§¢íçÕí²»î¬ÿ»ÓÚ÷¹àÇ÷…µŽØå ›îÀå×ˆÒþ†ðØ—¨èÃ¨ ÓèòÍé›Ï¶æ³¾¨ùÝœýõÖ˜˜õºó×¿‘öÚîÄðõ„ù²Ê­¼ÅöšÒ¾¸¿ôÀÈÖ’ÜËð·ÇŠÚƒõïÁš’Æã·‰†šâ˜Ìïë»­ë—¢»ËÒº”®‡š» ñÌ›¯¶ž¢’±€ÍøðöäïíÄÔõÁÿäõžë¨ôÏýÔ˜²ÛÁªæÚ£Ñ® Þ«ŠÁ¡«ÚõÆ˜ó»Ï…¥ÌÏóð«Þ¨’Ì÷Ô¸ÒÊ—›‰Ž¥¬Õ¾÷ÕÍ´µ¿Ò£ã¨ì÷¥œ›Ä¦Œä¤øÚ¡Ð„Œ§”ý¤°ÉÕò±Â”ÂÓœ¤…œ¥ñÖ‡ó—ïñ«Š§©ÊÖÅ¼’ˆ§‚Í”ª³¤„¸åÍÝ¨µÍ¤¶‡·—Üîí«×Ìôžªœ¸Âÿ¶ÕŠº®àÚîä’ÆÉ¼¸œàéë¡òËþš¥ŠÂÍë¬²ä×¢ª•žû®®±³ˆ…„Ñ±±Žå†ö»°›¾ÔßÉÝÞÞ•Ìç×ÛùàÕª²² ÉšªÌý½¼åÌŒ†Ÿ’éÛ¥ä®õ†Äæýâé½Ö„Îòìè¿Æ’ž‹¯‘¹æð’­„ððÕù¡µ¸Ø˜í çëþÈçÚ‹ÆíÛîÉÅØË™ÁÝËªÕžÀ˜ùëöªÑ‹©£ç˜Ô”Ò™ÁñÑåµôöÎú€³ÛÈõÕó¹ÒîÝ¢­³¸ÃòÌöÞ•ÅÜ®¿†«¬ùŸ‰Ýµæ­öò…î¨˜Øæ¨ƒþ²øÁ¿×ØüÓã™Ù²×Ÿ‘‰¼Í¡ƒ€îž÷ªÏ–±¿Ÿ¯‘Ý¾Ü…ö—Ò×Á¼ÿ×Ó£Â’èŸö—Ë­´œêåÃÁñ¬ÓŽºÚÙªà×Ê¤°µ£ßÛé¨û”›îýÞçÕÃ‰¬æ¤‰•±¦ÒéÚÕ˜…é¿ßªêÍðßôÐÕÖÅõ´¬”¿–ï¥ï’âì“ßºð•óµ²×ÆÉÿÜïù©ôßéá¤ˆÍÒÌÜ²±í™ÃúØàÃ³´·’æþ¶ÈÓüÓÛ‡ÐÊ¨´Œµ—õº§ÀëÙ½þ“›‡Á¦÷îÐâÎÓ«²¯›Ô½¯¾ô‰É²·å¤ÊŠ—›±ûÇõüÖŽè»â¶ÙÂÕ©ÓêÙÿ•ª½§®õß¢àæ–Ä¦·ÈšøÔšÊÌ¿±Ó¾æ±æ®ä§ì³Û­íñ¶£¡Ðô¡Ö÷Ò…¢·”ÎÊÒÈ‚ñ¥›ˆ©‘‚Éø„Þé•••ƒç¤§ÈµÅŠï»ûø®Žñ«åúÒŒêÉÍöå¹‘ãæ‚øÝœÂ´‰ü¥Ó¾™Ùýá¯•°€Áö×‡àšúê«ñ…Í‡ìÎÄ—ÈðÒ£çòŽ®ê¼¬±ìò›èôÎò®©ÈÖù¾Ò¨©«äâÚøÇ‚ÜÛ½»ÑÉæ”®‘ª´Žº»²ÓâŸ’µ‡ÌÝºÏ´ƒö»¥Ç…¤ÄÛ¿íÞ¥™½ïªÏÝÄ•ý£è–ÛÆãŠð˜“ÜëçË«¥ ™¹þ¥‹õ¾óºÚ¯¯ˆÊùÚû«½÷ú×ïŸÄ©Çƒú³²ùøÄú‘¹•ÓØ­º¬ÀÇÁïŒ¨æÚåÀ‰°ôßÐ—À»ŠÎŽ‘Öðß‚åƒ•ñÜôÊ¬‚Æ¢ˆÂÔÅÙŽ”©½‹÷šÛ®Ü©ÐäÂ…ùƒ«×²µÚ¹£Çø¯¨Ó•é×“ƒ›Ç®Þ‚ÙÜý’Ïë³Ò‚ƒéÌš±ûãºõ»ëë™Öâä¸…Ð»ü¬ïŒšŒùÀí÷ã¸€ƒ²Ž¿ÜÖ‚ƒ¨ŽÖ¡Ìúž‡Ñ´á¸ÖÌ”º¤Í”àªíÀŸÒ–Á“‚ô“Æ‘ˆÿ¤Õ½’Û¡ÍåÈ®ùüóÌß±³½¦²î ÏãëÍ‚ùÌ­øÇä¿¾‘­úìåíž…ÜïçŠø»°‚×¾¯þ–™˜¾Ò¼ ü¯ê‹¢Ÿëïõ½¨…Êüäá¦ãž®¹‰Öâ¨ãÙ¦›Åî´Íƒõó™÷ÊÃõ…’€¦Ûþ²ìË¼üÜé‚…€ŠªÙæÁ³·•Èˆ®‡®¸Äÿáåù“þ§ÁŽÜŒæáŒÉË¡™¥ÕæÄæéÄ‰œµ¿‡„×®ŽÕˆ¥çµ¾Î–ÃÒÜÔºÀÁŽŽšˆä·î­Ñ¾œáàçŽï»šì‚£ÏÀ·Œ‡·”«íœ½ÏÅ±œÙþ×ÞÎ ¥äÝ¼«¨…èÜ§²Îþª¸ýåÇ²„ò¦ÅÎÿ‰ýÀíµëõ€ÒßÊÃú¿Ã–’‹µ¤´‚š¨‰Ü…šñß‘ƒ·¬ïá­˜á™ªãõÒŠ¹Š‡™ßÛ»ÙÚÀ²¬èƒˆ½ùù×¿–…ÒàÅõ³Îºê¨º‚ðÐ¸»¸û¤Ï‚üåÎùÐÔ–…ê“Æžã›òÿ´¬Ñîƒï±ˆÃ¦®ª×ö×Ô¥¹×ªâ˜¥¨ÀŽÑÀ¡â¯‹þäŒùùã–õ£‘¾ƒ£áè¨ÔÏ³Ý®«­ˆ½ðå§ÏÕÃ±ÏÒ…ãûš…‹šã¢“Ôœ²ðÿÜêÚÖÑ€ŒíŽÚá£µÀß§”«Þ”áÑº½Æ‘‡êÍ¾ÿŸˆ¡ôžèÇíÂòìÛ¹‹×Œ¼ë÷»¤ÀÍÄ„¤×Õ‡Ç‡íé ¹èÝ³ÞâÁ¾Ä½ƒêöàâ¦¥ð™è¶·ïÅœ‚”ÔâÊÑˆÿª¹ÅÝ‹ƒî£è´˜Ó—‚Ì®é½í¢ší¬«ÒÒ€Ÿ­¯¼¹±Œ›ÊšÜâê¯Å«À‰äð‘×ììß‚„³‹Ä¾ªâÜÉÁÆ‘ƒ±ùÓÚó®ÀüƒºÓß­õº©¥Þ•Í‰£ª öÒÑºóÅœ”ã°÷ù›Ô´çþýÒ›êúÍ­áí“·•‹…­Îå£³ÎóÉùœÃ€ì¿ÃªÒìò“…Ž‡ØøÉìŒ°¢ï€ Žä‹ˆŸì»¾òƒÈŠâ ‡ÅßÅœÎÁÒË°ö­ÇÿñÙ• ô‘¢¢®Í–‰ôÙÖ–Ò¯ËÍÜˆŠ¼­ÂòÞ¿”®æÑÆ£ÐÙÔÅ˜ƒäÚíŽ±ÃÂÕÐåœ¥šå¬‚³¢ûÊÅ·ƒ´ Ì˜û£œ‚Ï“‘ËÌŒ¶»˜×íÊ¿¥ù±ø´Œò·üÊñ³ÙÃØÞØ§ñ‘œºÓÛ•ÀåáÅàÈ‘¾êÈÁ‹öÉæž›à¡í²åËºÓ¬ê°¶«ÂæÈþáÞÎÎ­„Úî·¾„Ý¥«×äÏ¦æìºÜÝÂôò½£óƒÒÝÆú»Ë¬¾ì»‘Ê¡†ÔÜÞŠ†õ…Ì©·ñóœþÝåñƒÌ–¬ÚŠ›ö“µå¬¬ìØº¯ßÆñÚ­ãØÞ¢µÛˆáäÇ„ÒèÚ•Ÿ˜ú´ºÓ•ƒÍª¸ªÅÂ ¿Â¼†ÜÓÅÔƒÁæº¢‹þ¤ØÅã£²ÛÕèˆÉËªê¹º–•Äãü®ÃÅèú³•·™ÄË°¦ÄÐøðž‹“¢óÀ§Ú ™ÞÒàÍŽ¼ê‹„–ˆîä¹¨ÔîÄŸå‘¶ÏªÝ€ÌÆù«æÇúµ­ô¢½¯ëý³ŸÎ»Ü·‘“‚ŒÓÌô¼õíÖ†ÿÛÁ®î¿ÖÊž…û½ï³üÊÒä±âß¢‘ø–±•ð‘ì×íþúÝ–ú±êç¢Îø¯Ë–ÿ¦›‰ìš‚’õ¿ÁÔÛ×Åþ²ï‚Ã„Œ†®Î£ÁÇ“Ïíê¾ÊÐ£â²ãòÿ¡•”ê‰™¬Ð”ÌŒÕôÙ‚ÔøÃµšô„×ô¥³ÆøÎš†Âÿƒí°ÅÆïÓéÑÉÃžŽúØ­©¡ý…µµãÓô¥ñÕÔõ¿ßé‰»åãúÉÁ·ªË’ÉŠµ² ™¯Ñ§Çªïà«žõ¾ÂŽ«ôãÌ›½Œ¡Ÿ–…Îþ£í­²µóôô¶áÃÒÔí«ê»±µöø€£¬¶‘“ÖŠÔ¥³Æ›À›Ö¾›Þ«–Â¦´éÛÊ³ŒÍÊ™ÌÒ¾¨ÿÖ½æ™ô·à«‰Ðç¶ÜÃ‰­øúÍÉ¢»…ÑÍÐÐÂÅñØº‹­ö™–àìŸ€¶…›Ì³‘åÃ¬ßÎçÕªå¦Ï¤ÄÔ±Çš˜ÊòÜ××Ø×ê±§Í’ü—ÕÆÜÒ‡ýŽªìØØã”¶úž˜á±È°ÔüûÿñùüäæûýúùäÚôÕžõÆøéøöÞïÏï«œï—žÓ½íüÌøÎÚÑ«‚àþ©ì¯ÛÊæÚÿÔ×öˆ´è„â²§Ï©Ù¾Ò¬Ñ¦Á÷Æö§®òÍ³ØõçÔ¿«‹Õ‹­ˆóû˜…×…ÄÇÌþÌ¬Š„Ïýÿ½ËßÛ³åèÖ¾ø¿ù£¯¹õ§ó×ÿÝäÝèäö¹þè»‹Óÿ«ìÌœÞ´‹÷Õç»ÜþÐÑö¿ÒÁÅÚß·Ëÿç²¨ ÞÊ«Žˆê”·Éó¹ßÞŒ©ó©‚ÍÁ‰á‡ñáœË·Î»×ÝØÖ²àØµþ¬§¨±ÅÉÒ¾•Ò¾èöù§Æý·µðéïýúØ¿€æ§™Ú¶Ô«ý¡ûþƒîÉ¸óˆ—Ò‹®û½ÚŒ’½„õ½–Þï«‡ß‰Å‘‡å“êìËÂè«âé±‘§’îÏâéä÷ÿŒÝò¸·ã²öŽ¡Ùú™¤‡ÿ…±ÉçÌ–¢¯³šãý°í¥–ñÚÖÝ‚Ü¼¬åíß¬£„‹è©ý‡ÑÝ€‹é÷´³µäåÄ¼÷“šüÝÊ…àÃÊÒê‡Œ‘«ûšý„¾­³Á¶ýáº¿Õ¥õø§ã÷¼­·¡ÎêûûÏ±Ä´ý¬ûÁ±ïæ®Ø„ÂýºùàÞ†²¿¿ø³³Á†Ü¾¤´úÖ’Å™±¨–­¿äªÿˆÛÄ‰®Ú€öß×î•½«æû…˜­‰Þ÷´‘ó¡Üô¢á†¤õ Œ€°¸ÜŸ¸žƒÉÂáªÉ“ö•Ý Šöö£É£þ—åý¾úÐƒ›³ûòøÛ›œÞÞÞþ¹õÿÍ¯—×·ËËëì¦ÛÔô€¸‡³û³ Šñ¼æ¯µ‡÷¢»ÖžîÃûìŒ§ºž¬ÛüÈšãî•„ï¤¥Í™œ«×ÕÚµ‡ŒÈîößæê‘ÙˆÌ¶º†³·¥¦êÆó¹Þþ²ÏØˆ‘ý”ö«òðÙ©¨î—ª“ö«…£Öµ‰ƒâ«ë£šÂíÑ€¼½ ÔÓ³ªýòåÛÒÝýô††Ä÷“ÿ¶µ®Ó²èß«õí¸Ü„öÙ­ê’‚×«šÜµÂÝ“¸±±£¡ÓÚ¥ÅÕÄ¢ž¹¥ŠôÛÁ½öˆâø¢ŠÛšÈ×ãŒÊºë“ÉÓëË•¢ùËëÊ¡¿®¼º˜öïîëÜÆ•ýùæå…žß™‚ÕÈíþ‚éå³‚Ëÿ·³º„Î÷‡©Ýœ¶×‰Úßïâèœ·Í½†¯ªˆÌ¦ž¼š®¦ã½©À¨ºœÅ§êÆš·óö¿Èš¸Öñž¿æã°Ùøê‘éùÛ¹Œå§¿Ûô‰··¿î¿¼ŽÊœ£ŸÇÝŸÛˆ°ˆˆð¼î Ì®›®ì©­“ÚóçÀÅ•ØÄíïª¯ùý¿¹›€·£ÞÍû¶ý×è¼³†Ï¶˜ªíçØ£‰Îßã°–òÄÍ¼ªŽÛ…¢ƒùºµ£Ìá®ÕÌ„¦Ñå¤Ÿ¾Ü¶¥ó­²ë†Ë‹ë„¤‹éî“’¸¥§ÙÖ€Î¹ÐçÂ¦Ÿ¯¿ÎŽ¢ÑÉàà‹À†°–—“ÇîŸÁ’¦Êó€€ÐËØ²šŠÞû«¨¬¾µ’†áãÒÕ´À»ªØŠä€§žî¼Œ‡ú›¦ºŒ«ƒÒõ×¥áì„Öøîè–’»¿«Çþ´¹ë¶Í ÎÓî é·‘ùÓâû­²Äƒ†µ““Û Ä†®¹ÏÅ®¼†óÒý¹¾½üœßÿÞ¶×ËÅ§ó™³ê÷æÇì¹ûÿÿ§«Å§Ò«„±®ˆÍ„ÀÈœ¥ÿÜ—üÛ€•Š¨…Š³Ø¥ƒˆ‰”“Ò¨¤½­·±í®å¶¢ÊëÄøðóë˜ý¯™£•Ö®—ó×Þ­—‡Û‘ÿÑØì½ØÕî×¿ˆÕˆæ÷é³Ç¾çÜÓœ–ªšÐšœš…Î¬ÅË¿“ö§¢øžýÚœÏÙœÜ¤Øê«–ŸÌÎÃøàˆè˜‘Š†¨¡ß¡Ýõ¨€»ãÑëø¸ô†èõÅÊÿ“Ö¢£×¦÷¾ã†‰­µ‡ñÊ¥þÑû“²ùÇÎÚŒìñè†íòœ¥‹Ô³ìƒÝ†·…ˆ¬‘¶Ç‚¹âêÓü¾Ò¡è­ÀõºŽÕ™¼Íš¿¼Î¨“Ðÿð—ó»Ã¾º«Çùº¹ªë‘¶±’íŠùÓ²ÂÄÌžÃñæêßŠ¹­¯ŒûÈÛ¶•Ü‹»›ò¡Ù‰¦Î¼ÕÇãÖÙ‘‘äƒåº×Ÿœ‰âú¶Ù¦¾äœ„Ê”€©ÉÜÂŸÌÚò•·ÉÎ±ð®¨å¶ú˜Ñæü¨Û¸«Ùé¾ÜÖ±·ã”õìô ÜÄòø³Ô­Ô…¨žƒñÂ©°ÕÏè¶ÁÖË°æãžóÑöìÿ€©€Ìš¿€ó§©äóáê¼ã©Âó±¥ž­ „¤ã¨ÊÙÎš¹¿Ö¡Ò²Ÿ¬úžû±ðíƒáÅ–äÛèÿÍ°Í¨¬¦ó©õª¸„â”ÐÀ¡“ ÂÉ²ß´É±«ÍÊìÉ–Ó”ðÌ«èÔµš•ôÑˆ¢•¢ë™ë€Ã‹’üÜŠÜ„¶©§‚¡Å­„¨Î¢Ë®ï¥¶ó¼í¾ß‹¦Ð²ùÞ¯ðê½´¨‡ÑÔ±Û¥‘Ê„ÏÛÖØ´îû‡ÿ­Ûã®…‹ ñ¦´…¶¼¢ì˜€äŠÔ¼´âÅÀ©Ü‡Û•ÔÍ·âåÅç­É¶ìúý¸—³²ýà¾×ê±†žŠµ›¥‰šàÖþ¼•˜æÛªŒÍÕ±®Ú×¢™·¥ºÂÿî£û¯ ßù”§ Õéñ…´ªœéë¸¹‰²­íäÃ‰ÙµžÕ÷ÌÇ¥®¶²Ç òÜ†¯›šÌØÉ¢ñÉ‡•´Š¦¤îµË±“âõÚðÓü‘€Æœå€÷Âþµ¾ž ³«õ‡Ð£ÇÁŸ•ýÕÕÒçðÓîÛ¦ƒ›ßù…ËËÐ³žžœõÀÅ«ŠÄé„¦º÷Á¹†÷Û‡óàÈüüÂŒ–×ªÀÈˆ¢Ü”Àå¿‰ª¢Îƒ»ŒšÝ‚Â«í™‰¹íÔÌÉØ¹íÁ–‹™ø¾õã•©¨¾÷ãÁ¢¯§ÌØð’°Àü•£ÞÞÍÂ™à•ÂÉ‰Ü‚Ð¿ÏŸí¤’ÄÕ±¤ ÁÇ€úòœ³¢Ü¢³¾´ÐÒÒðè…™Ë˜ ¡¹­†ä¥ÇàŽÌÆµì±®¼£ ßË‡ÇÞœ‰¬¯¸ÑáÀ®ØøÀÒÁ©¦Ê™ì‘Àµƒ©ÍÚã›À–Û‹è÷·‡Î€™µø¨ðÐÐò ¤üêŸâáúÇ·ï¹ü®ò»™žƒ„†Ø÷Ùþ‹§ƒ®ÅÔå ·´çÔ£¥æáÅœóËÜôÜ”í¤àùò§‰ÜÎºÞûˆÎÞêþˆ–á½“­¸Òÿ½‚¯Ô÷ˆÙÊÝ€´°¡ö×ôËÊÅÏœóˆ¼ÆæØÓ§†„¼ž”âë¾¾Žð‰êÜáÜ¬ª¿ƒÇÓ…ã¯êîƒ“•„ŠÕ˜èÍøæ¯ä”«¥„Š€‡«„çƒ±Úþºñˆàº¦í‰Ö÷ Ç´•ºúàý«„Ÿ‹Š‚¥–ßˆ¢¹¡Š¬ëê¼ê¾¥öŠ¼Ÿäˆ€å„ª¨é™þÉƒíÁã±×µíçŠÌ¾Ë¤Ï¹ý®Ë¬Šô´ÿ›´€ÄÎ»é§ÑŽùà´ÆÇµžôËð¬¦å«ª¼Á‰š¥†ß¿¬œÍàÿÚ˜Þë÷Õ¦Ê¨Ï×ÒŸø„ÆÅÇ­Õ½ªÝƒ½°ÏÁ˜ÉµÝœ÷ÄÀÎØÆ·Á¨ÃÌƒÊÔ²Îà‰»›Ä”µ–®ÕÜÐ®ôßêà«¦­­ÄÁµù¦” î åÃ®£í¸‹ùî–¯¼ø£÷äêÜ¦¨Æ°š»”ûŽ òÞ£ôÙºíðÄÈ¤äž˜ÅÞ½Š–òü¿¦šÿ«ÏåµäÈÆô®ôå£¡ñë›Ÿ±ß—’õ§â«º¡Ë¶”øÜÂÈìÉŽš°å­¥Ï‘Îè³´©è»£ˆÎŽ÷ÓÞÛ…·ûýç‡ò˜ÀÔÀ ­Ò†ð‚Ü¶†ª´„ÌÂåËøª½öŠßÑ’òÒÉ•ÌžÊŒÓóô‡ì¬¦¦À¤þÌÄ—úâ„µ¢ŠïÄß­›ê„¹Ê¿ìæ¸Ø¶ƒ‹¯Ö¤éê³ÿ¿Í›Á¨ŸÛ²À…¢È„ë¢æêéËšûºÛ£Àþ±š²ŸÑËÛå‘ºº£¾–Å˜Ê¡¨žÜ×âò§î¥¹Ÿ¡·ÊÙÌ¶­îôÆ¶çèûïßâ—›×èœä½ÿñà¨²ãÇ¸Âž§¦²þ õÑ²’œ¹«†·±´¡×©œÁïÜø÷‰ŒþæÚà¼Ö¨‰†´†àÂœ¶„ÎßÚ˜¸€·äæŽÄ’•¬žð‡’¬»†•©Û¾à¶œ€ýÓÉ˜—ÝèÝ€¯‚€î‚ñ†òž•Ð¨‘¹‘¬Ü¨°¶à±Š³Õ€Ï¼„ âÅƒÀú†–ßæ†ð™Ê‘¾»¹óýÚÓÐÝØ¯öìýÞ£‹Ýáðàºå¦Žš©™»³ÓôÖ±•ïåÂ‘¨àˆÎÎ»Æ¾¬”¡…‰ÓŒÄ•úô‰ïî¹×ë÷âÙ¤àÏÉàïÂÁÇïøÓÖ¯ÓÑÔ«ÌÅë£­ØéÀ‹¾¼„ÐñŠõ˜”Ó”’æ€È»¯îÍÁÕŽíèÿà¬ý–ê¶Ûó²¾‘ÕÞáÃ¦©·½ÏµëÅí†ûÙÃ»˜æ×ÎÀÏÐ”¢ÙÁýž…üÒµÈ—ŸòŠË·Ãë›Œ¶„‡åŽã›œáè¥Ôæïê§ìÝº¤Ô›Ç¼ûÚ±ôý¬ï¬½ÅÉÎ«ëŸ‘Ã²ÌÄªŽÙ„ùƒ™¯£Šê¤·²Ë¸¢¼Í±’·û†Ý“ä«ºº¥ß£®á²ÃÔòƒ¦ð³íØáÏ¤ê›öìòßšÆ­šÍ“ëÌóÖÊñ¸˜äÇèÙÐ¸ÊÍ¨¥¶¬ÒÌ‡¯›ÅÆÉÈÉáÎ«—³èüŽ§¤Í‹¹µ“ðÆÏ“ú­–ÉîöÕÕÞð…—Êß×­ú‚ÏúŠ˜Ü‡¤Ì ›’âý¢¢ßÜ¼Ìêã§½íÈ—ÙÜ¬Û²ßó²ã½¹ðÞ²¤¼Üª…°ÉÝ™ØÈÒ¦Ãà¡¤õí†¼ÑÜº«À¸‡–ÝÞÐè´¨ˆÀ»š‡Û££Ã˜ÕàÚø‡š¾¢Ö½çªÚ×Œ”º ÿÝ£û¸…ÑÐœý¢¦Ó‹¾ëøÔõ÷³’ïŒ’Ÿ…ãèàË£ÏæóÂ¢“áÞ‹õà…²ëÔ¼Ì®Óê§ô×Ÿëº¤¨à†´·ÅÕôÒ¥¨éïŒ‚³×æ¼ÔÅ£…’í¾½è£¼¤Å¤ÿ·­Ñ©ÄƒÃÒ‘®Æé¶ŸÒ²¸îÊÒ“ê«œ®áÌ»Ñ¥°ðéš×ª»Õ§‘Ñõµ¦ÿÆñïíôåüÊžÏÔÎÇ¿‚â÷«…†ºÂæÜåÛÌ–ãûª¼ÕÅ¿ëçÝÝÞ–€š¤Ìû…óÉªçúÔüèû•ùÿ²«Ô·ûž–Å¹˜ÕŸì„¯ëÀÝã–²šëÑ¢”ÉÓ¨ßÙéÖ»©³ÑÇ‡ÅèØ¿·’† ûªƒéÜãÁûË’‚ÁÃÂ˜£­á‡û°Íþ§þþó¡Ï·Øìù®ÄÈ®°™©˜œÀçè§»îû¹þ–Ÿâ€ßÆŠÐÚìýò¦‡ÿŽþ›¨º¤ÓŠ“ˆüÊ’ß±œŠÑîÒß«á·­Ê‰Ö–¹—ç Õà·ò¤²øÒÙâÂáÁš«¦Í­¢ãˆééÍèºÙì„ÏÑ„ëŠŽ“¤Ð™ÖòÎß¾ÓÊðˆ÷ßõÚÈ¯¥Á€ïýý¢¦Á“ ¶„óÐÂâýð¿ìÔÄ¼“õÅíÐç€ñ´…íáÕÔæ¾íŠýÃ¦°Š›æ”¬¿¿Ã·ëÌÒ±ëöÄ’˜Æ÷°×¯©ÏÙ©žŽü®å€É˜éÅí„ÕÒ°Ö¤ÚŽ°‚°Ó‘›¹øè«¬Þëñ•ÉŽê¤¾©ÛõÙ†ÏÔœ´þ½Ýûàó‡÷°Ì î‚òÃÂµ€»ù¯¿ñÍŠã‡þÑæßÿ±’¯™™æ°Œå•›…˜ÜË·åÉºàÉèˆÞ©‡ ¶èß‚¾åùþ‹æ¯Ä“¡íã›ú«£áûŠò»ÕíÉÁ”öËûŒŸ³ ‘òÏêàÈÙçÕ¹Óî™÷ô‡ý¡Û©‡×Êà±“Ô˜º¹é©‡àˆÅ‰å“Ì¯þ¹¢Æ¤Ü­Ý«¨ŽÀ†çú•©ˆ¥žŒ—é÷íŒ°Ý•“ýò§ëÐºûîù”±‡ªÕž¸Ú³í™¬Œîž‡üµ¢çºë…èâ·˜–ä»Ž„æÚ¬›äŒó¸Â«­Äµ ¨»ÔÃ×ÊÃØ˜ËêÒðœÈ»¬ç×²ÂÜßú¥ûô»»ÛÅ»¥ƒôšÐ„ÁÝï˜Íîº®Ê¸ØÂä®¯¤Õò˜Šõ½ÐÉÒÜŠÔ½äïÕþªÓââÖÑÁòãàòàÀõ´¹„’Ýªú£ÍŽ¨«Š¼ªÿ–²†öÏÛÍ¬®–î²øõð¨˜×ôóÏÝšŒŸ­óžüÅ—»èñþ½îÅ‚Ì¥å±ñ¾­¿Àµ«¨åîÔ­ÇàÍ—§ýñÿÊäýýØ¦µÞÃçê’î±ÅÈÿÚâ¢æàÉ¨âÂ©áûËª§¡øùàÆ¶¶ÀŒç–ÊÞµ£ÊÄ¯œ‹Ã‚ÿ±ôÏç×ßÇ»ÄÙÿ¿¼ÐøÜþ¿½ä÷÷Ïë§åÅçæžÈ¶æíì÷ÁëË¿Ô“ÔÙ•û´ßÙ¢Íå‚›¸£èóÈÔˆûèèÜå”á÷Ðž„Â·ú÷š®½•Öß‰ÄÂì®Û¶ùßãªî­–ˆ´¤ïž¹ÆçÜÃë ™ÄŠÙ¢ˆ³ãÇ²­µñŒ¿ÞÂØÕÀØÊ°Âôí¿‡Ô»’ïÜ‰º©«¡å¾û±¡öâð”Ñ·¿à­Üí¤ã‹ÍñÃïæë½ç£‚¬î¤¼Ž¨ë«ñ«ØÔ¨Û™é‘Õ·Ó èÞÑÖôÐŠË¼€¹ù¼Â•³¡ºæ¯»ŠŸŸä‹Ò²¦±ŠÐìÙÞ­‚€ëÕŸ„ï„„ÿ“ð‰¡„˜—ºãø¢ª©·¼ÎÒçÒˆ¨°îÌôÅÌÓ¾˜‡š½ÃÓß¤¿ŸÍë²•Äçîóß‹ßæ ŸéÇ‡£Ží×‡ˆŽý¦“ó›ù¾÷¡’ôÄó°äíÎËÅ¨ÔÚœÌ§¿·ò°¯óÖùéí«¤þ»ù¹Ó„»âØ³•ÀÈû€åøËÇ‰º’ŽÑÜó¼À¶žÃþû¿Ÿ—õÈ±ÏÔ«‰§¯«²²¿·¶ü¨ÊÕÁÅõÎ÷Ï×ˆ»Üì¶–ÝÝÃß›ãÕíý“âØÞÚŒáŠ×ûô íÔ¨ª ƒ±™¶—íÃµ¼ÅýÙ´Ð–Î·È³°ùøŒÄëÏò¼¶ì©×ÝìÌ„î‡¿¼¼Ñ×œ«êýáßÓÊ÷»Þà¿Ì¬»ÊîÞØŒ›ãìñè ÆÈ’ðçåï·Þ‹•–Þ¢µëë¡¦Ä¹æÂæ“¤Ë¾‰¾âöôÅ¢ßØ¶îæ¼£öÌ‚¡ðýäê öÚÀ‰×Êè˜ÚŽªŽÏŽÀö›úÄáê»”ÉòÎˆËì„‚Âß³¿Ø”Õ”Þáá€óýåßö¦¨Ÿ¯ëãÁõËý½ŽƒñÔ¾Ú…ÊôÛå–Ç¿Ÿ÷Í¸žÔÿßœ€‚ð²ž³È¡ÚÇ ¶¢Þ˜Ü¶ðÝ”õõ£Ãª„ÒëÛß°™˜’š§¨¡ŸÜñ¦ãäÍ²ÆÓ£‹°áŒÎð£Í‹Ô¡Öç³Âá£æ™½ÉþÖºå‰«¸£ÚÆô–áþ‹Éï³Ù‘©Šæ¯›“­ÇÒ¿íÞˆŸâÂ ÝÔÉÞî¶ÿ¬™“‰¬Å¼Ø˜†‰Øæì“ÏÛ´¥×ÓúÐ¾ïà€Èñ¶£äžè¸±õ³Ë‰öÍúøÈ’ïÓ„ÈÁ‚Ù×˜—ü¯È¥®¢Å×ù§ÁÀÞ’³õƒÅƒ”¥ß¦à‘ëÎÄ™ù·”áÂ…ˆ”ì„ôÓ„¤ç¿œ‰´‹Ã‰Õî“©‰â™§¡©ÇûóççòÊø•£ÇŒÁ«Õïê›õŸ÷’ÖÜÂîÌÅúî¥ÌìÐ‚è°½žß‘Ò›Ñ÷š€Ù¶ò©ý·Í…£×ú¢­ù«Ûõ¹Ì¦‘àâÆÙ…ß¶ª…ºÒ£ë•Š¸Þ‘²çáŸ¯ÚÖ…ŒÊÎŽÿÙ¸Žª²¥–”ð‰ùÇ”òò¡’Žñ‚Ö¯—àÅ¥ý„©·¸Îˆ¹»ÃÒŽ±ŒÍèæÄ’õâ‰ÔÎÒÒˆÞŒ±Þ„†å‡ó»±¼˜³ø¨Ûù®¦½ˆù‹†Ðð‰éÏØÂ„²ù³ëÀÊÁ†Û„óŸ„ö½×Ž»±ûñ¾‚ÚÛÂ£ÀïÌÓ‰Ê€°¤ÒÖ¨Ë¦æÜ°†ôÎÕ—“ÄºÑï¢ÔõœšËý€Ä¢…¬—™„¨Ú‚°ÆÔô÷ÑÁ÷œ÷ðÉ–à§ÎèÓÌœ±·Ÿòè¹¹ª«ã¹î€ì¬“Å¥â˜°Ì·º©Ç¬ÇñîÑº¶±„ÃÔªçÅ¶×Ø’Ÿ÷Ò¹ØýèËè÷þ„´²ýºß˜Ò…ÐœéØ«§‹‰žÏÁ¤ï°Š¹âíÆ¨Ø»Ô¸‹þÖÿ›ÁŸƒÓÄ±šÜÃÉã€ÆÓÔÝœ¥Êðä†§éÀËø¬²Ç·§Àîêª¬ª¡’ÕŽÊ™„Æ·¢©à •ä¥¾›£ñÛÞ„ƒ§„«“¥Ñ«¥µ¿Í†¦’ºæð¡‚¯£ÁÆÖ„˜øäŠÛà×»Ø‰žÒ¶‚…æÖ‰íâÏ¯µ‚µ¬ìžôƒØ€»×å¨úÔØ¯µÎ¡¢¥Ë×Ç×óŸ’§‹Ö§É¦ûœªÓã¯€Í·¸Þîìà€ã¾­‹‘ãÑðöšÕŽ§¨¦ÂÂôÌ¤¹ÖÓ´šÚü½œŽ±ÔÛ¶ß´ï¶àçíÀã°ì‹‰ÅÖÝƒä•÷û‘“Ð·œª´õÁ¯´Å«­¯ÇŸø¯÷”«Ï¿½¬ýüØúŠ¤ã¯Þžó“ÿö‚–ëð‹¯ÄõóùÅ§Ú–á‚Ûÿóë¤ŽŽÍü¬ŸøèÎÁ¨ãö©‰ì½¹¢““õÉïØ÷÷àèöù·ÿøœ½…ÇŸ“ƒÀÛ¤ê®…«±ö«ì¡íÔñ¿ÅÒÚ ÆÉ¶û¯Õµÿ°˜ú±÷À€þÕàÇÊÎÀÌâÂàŸÎá¤îêªúóÁ–² ü×òØˆß­ÒÅîî±ùŒðÜÚŒðÉÞîÏþºÁ–ÎÖ‘‘Õ­ÝÕ¤¹Ì¶±âÜÖ„¦­…Ë–åù„¯þ§È¢ß£öˆ‚©®¡¦Ø‡Ý§¼´êñð™¥ÂÑˆõÓ¢æíÌƒƒÒµÌŒÖžÀ•­Ëù‰øžˆ„•ÉÕê¡Ñ¢ÉÕ°¥§éÖÐýËŸ„À—‘œÉ ¨¬¶ÓØ«Ÿîˆ¤¡½¿ú¶ÈõÞÄ³ø§Ï´¤÷¸­ÖËäÒØÞ…‰ÏíÉòþÕÏ•àÛ‘»ûÖò‚–£Û¡ý²ÓÈ õœ²Ä¨ ãÎ”œ§é‰“ƒåçÔ—ì‹ËÒûÿ‹”Öìÿ¶Ûú»£ÕÛŠÎÙÀÂéç²´ˆ„¶÷— ’•Åä­´ðÍïæÂˆÚŸƒ»ùïäòšã¢™Íûï†ëõÑ²÷˜ýÙõîÙ¸»×Ìë‘¹¢˜‡­Àƒà¾©Ò˜û¹”ÿð‹È§ÂÈÍ¿¤ß®Â”ï½ƒ¯öÒÄù‰«‚œ¸Üöª·»Üçÿ‚œüÀá‚žåÑ‘™×ËŒä§¸€©âíï–ûÎåÂÜ¸¿ˆ”ÇÁ¸‘²ÃÏàãÌÖ„Áðô¬ãàøµË³Ã–á¦âñüÛàÐ©ðíÛ™ž¬ý‘±‡žÏ…ùÈÒ¯Éåüãóÿ­ýÍƒ¥¨ó²ó‘£©ùõôô²±¾¾¼ßŸÞ µ‚¿Àˆž³Ú¿¾ï›ÁðØ¹›å’œùŒÑøÓ‰ú´¬ó›ñ¿Ò’Ÿ«ù²æŸÜƒýŸÇ©†ÜÐµÒÖáÐ°Íôíß¦òß•¥øùç¾þÅˆ…©©£çŠƒ•°Ô½³ã×öŒ£¤ÙÎÃÎ‹Ä½²ƒ‡õ¸Î‘»ì´»’µ»Ù©Ý¨Þ„ÊÅ¹†Ê¢é³¾ãµÀ€ÕðÃš¨úÈÂœž¥¥£ý¼îå ‘°ß¬ÉÒ÷©è—´…ÈºÂ³Ê¶Üü—÷åÖÿšÝ¼ðÐ¼ÐèŠ–ˆ×ˆÉä¤ìÎîÛ³è¤á¼Ä³‚Ä®‘žù¯Æô¥Ä½¥üÔòÀ’£ËŸäšå¬Ü² ¡Þ˜‹ñ×¬õèÈ–Ò€ûÔŽ˜ã¦ Žß¯ÏèÐÖÀ”ý†šñ¨Ã£Ñš§ÈÔ»Üã‹‡­æ”·€š¤€öúŠðÛ“ò¿äñÏþÚ¤¡ïòè’ª€Žñˆ€–ò°“¤ˆ…É™§ï½Ã‚”·ÔÐéª§÷ÙØ¼ææ÷£ù„·­ÜÞðÄ‹Ö“©õÖÂ¹ÛýÍì—¤´“åªñß·€©…¢­ƒÒ“ÃÐ€×«„”É“Þ€øÕý³à¢Íˆ°žú¦ÑÇÃ÷ÕÎý‘ÌÜ ž–ù°«ÊÌª­Ÿ‰±€£àÉ¬Ü÷–çîì¸±Â“»•¤ Šá½ƒÔ’‹ä½í”ö¶ÕŸ©‹ØÅ¢­ý‰úã®ÛüØ’ÌšÙÂ†ôçå¯²Ì¢¶ûŸÂÜ“øÊ·ùõÈÊóÞãÈúä¥‡¶Èãƒª£ŸŽ²ÚèÛÖ±ƒÃ™‘„™®ì¤Æè®ýŠ˜Þ“ÜÚ–Ü—èé­µƒžë¥ÔòÃßêêå¾ÁÝé‡ú›«íú§“é·ÜÄâÅòÉá¥ÅÇúùŸµØ“ÍÒûë¿¡×ìŽÜ—Õ¿ºÚ·­‰†Ë°éª‹ÇÅ’²²¡¢æ‰áéß…›ùãµëüæ²œÊª´²åÉƒ½×ÕØ¢ ÁË„µ˜ÆïÕ­°†ìüÊù¨ÚÓÁÄ õ•ŠŠŒñÐ™šªÈŠå¼¾–Ž¦ª”òí·©ÒˆêƒžïØÅö³ß äòçŽøÀ‡«¶èÐºŸÐÁ½“ñ¬åÝÏˆô½®ë»ñ­ÍÀ³¼óùÿÿóùÅ×óîÙí×¤Š¿ÎËñ¢Ý·Û¤Ö•Òó§‡­ÊÏ³žö­‰öª²š²§“éºæÙ™ô­óÒë«¨ƒÛ”Ü£ÿñ„ŒþàˆÂ¬á¢ï­õÊŒÞ÷ú´Íò¤êùÅ«‚¿Æ¶Ïæ²åç±ò¤û¹È©ÒØ­»™Í“˜ÐÂßé½¬âÆçöŒ²­¤äÁœÙóïÛŒ°¥¤ëÓ®·®Ð¯‡õÅÊï¶×ÌÏ Í§âÜòÚÂ™Àì—Ú þ¬ÎÌŸòâÈìóÏÙ ÁßÏÕŒ¨‰ˆóË‰°êž¢¸ñ¬Òð¯ÛÚÑÑŠ²ð‡ÓŽßÒÞ§‹Á¹çßÑÚ§ýÜÉ°èé¯ÛÃËý€þÐÒµ—Æé„³ÿèÒÎ×œ¡ûÂû ÷ô²ŒÏþñµ—îº½ÀØÉÈ²ò—†‡Ñ£½©Œ‰¤ç®åÅÏ§¼–Ñ¸ßÏÉû¸å°‡´Êü›ä¿¨†‚™’ÂƒÜ’ß½À¼Ñþå“ÌüÄåÐòÃµüÏµÒš½«Ô‚¯¬†‚ðüùë”£à®¾Ÿ¨½””“ñÿÛ¥·ô™Ü‡µ¬ÐÈáÎ„“™“ÉÌÊãÈÞ´¢à‹ûê¢™ Äæ¯¡«ÄÃ·¥é²Üï€´úÐ›öÎ ÂÑåÝÙŠŸâÚÎãÅñøêŸ™²Äë³‚ÿñéé·¿¥™þò°ƒèèÆ¾Ýá¦ÀÔ§û÷°ú…Òðó­¡«å×ô›éÝƒÁ½üÅìŸØ¢ÓÕ¿¢áÖÝÂ•„ÇÎêýÎ×ÝÚý¹³ºòš‘×õ»Þ½çªÊÖ–Ú³ú˜“¦•ÁýóŸÿ¿íÍ”ßÒìšÀêÓØÆþ±Ð‰Í«Ü×ªŠ‰‚Œæ•›ßúÍà¤Éî¼ï»¶ôªÿï…­°£Èù¯æÜ†µèíŸÎà°Èøå¨áäÅÕ©ŒÒ•ãÇ›¤ùÕ›Õš¯è›ŽŠÚ¯Ã·ØÁÑ–Ø´®­¦¹´æô¢ëÇ«Æ˜ììì¶”†œ€ÇÃÆôõò÷üÆÿþùÜ­¬ï—ïûí×ãüäØ©ô—ÊµÏ‚ªÀœíáÓæµóî¯šËÎŒ—ó÷ ü¶Î‚³¶€©‘æã•Ø–ÈÓ˜«ááðèèèóúù¼üÇªÿöÊ™» ¡¢õ Ì›¿Ò®Ôÿ‡ÏŒ¡úÄ¾²„ÇõËÔ„ü­ÿ†ÂÛæ¡¾µ¨Ð°©çÓðíá”ºÌ±þÛ„³±ÿªÿá”Ò…¤îš”èà’ÃÏïåÉ»‡¼Ê¡æ”šþŠšµÍÅÓœÉ£­á•µ¨ÄÆõó úÒš¥´ÀÐ¹äöØúúåÖë€“þ‡Ÿé–‚Äà¶Ž’Ö†½ÀáÐ˜üçé”Îò¬¥¢õ™Ï­Í•ÎËÄ‰èœ¼ÓåÜóÎÉÉ–›×žéÑûÞ«ËÚŸÏ…ÃŸ÷Ã¨µ°Ÿ¡›ÇêßÀé¤à½¡­ÈáŸæ¤¹¹„ŒøÆ¶•æðäÈ¡õ®üª™Ãð¯Íµ¼›Ç‹”æŒØñº¯ÓêÛ—ëççé™úÀ«µ‰ò¿¿ß¯±ùï­ñ™ï¸ä¸ÞÁž¾¾Âª¥Å©´Êå„„§›•Á™ç†ö”Üû¿£¢ÜàúÍÚ×›Üµ´²Þ‚ÙàÀÁôýæ¾Â²ð÷ ûƒÖ”°ÄÝ…Â¤´ ¥Ô¬» “ÛõÜìùßîëñ§éÅŽ£€³ƒ•ŽÍÍ¼¯¢³þœ½ŽŸŸŸ‡‹ÒùÛîÇŠ’²à‚×¡ß£ïôŽˆûÄÒõªíæ©²´é¥¯Ëˆ©©•¬ÐÝŽ‚Ê¥òËÆèµ­¯ç÷úõŠæÍ¿Ú¢ˆ«ˆºÿÒÉþá«ÛüÖµÖƒ›ÕÙ²‘Ô€‡©²ö×•ûë±Àî¿¼Ñ€Ú³û“Ñðˆ³Ý‚Ô Œü©åƒ…–çÃþûßø™ð”Ñ‘ªÙ¸¨ÂÁ¦ŸŠ×…©Ò¾…ò¡¦ýÒ“ª¦¬â±€ßí¤òÍÆÊóÚÏÌþ°ÀÅÏÑÅ®†£”±ƒ¸Çäç¨†˜ÉïÕÍ²¨­ƒ¯˜ª’‡·óŽ†‚¼Á–ÃŠùÄÌøà„‹²ñ¨ÆÖàŒ¨ï²’Äæì’Ìªâë¢÷ÉÖ½¹±™çìß‹šÀä±ÍÜÝœÓÃÐ¨óâõ­“¨ÄŸå±õÐ–¨ø¨ÃêìÛÆ†ÙäÐ„æà»©—­œ•í‘Ì²¯éÍ€Š…¡’î¸Îþ¼’ˆÎ¾Ö€ìïšÏ„Ã¹ßÛüƒ¾©¶º¤Àä‘÷–¾Ó®©šûË™”ÐÔ¨”µëý÷žšŠ«ÕÄÌÆË²Á¢ÇÒºŒðÀÑÊ”«½ÁÙ†Àûº•þ¼°ôÄËØ¡£ÿò­¡ñÙè„½¨¦­ÕÈî‘­§ÙÇêÚÎâùŠ¬„¿ø×ðÁ¥Ñ˜ÏÝš­ú¶â›·êŽëÎ±µöÚ¸—à—™æòÂ¤½ÇíÅõÍéÆ¼–ó…Ã¾ÔüÙÞ‘¬…½®üª‰²ÿŽîãû¥°õã«ÝË¼ÓæÛßÓ‘Ô¸ð•”ˆ”ªð¯Òè€©†¿ºí³«µÔš©ç›å‚÷Æ”Õ„ªÝ…µ’€Õñ†…‰œœ ÈÎá¥øÏÄÓÚÖ°Õ¯êÓ—ô®ÑŒ¿“ËÙÅºâë‹£ÿÝ¾¼þ¶±¸„·‚Ð”±¹Þåâ™’óòßë÷‚ç£¹îØÆÑ¥ÿÁ¡ùâÕÀÞúò³­èà™å¢ì°ÖÂþ±¦’ÿÿÄ»ª§àáÌ¡íúÚªÄ×Ø«ØÕ‡±ƒ‚¼Óªí€‰þÐ³£ïµ ˜µå´âÝðŠ‡ÝöêîºÛ“ÿ½Ì²Ï„ÜúþßµùŸ®×ÊÎƒ¼µ«üÆ†™Õ‡½ÿÎÙ”ê§ë§Œñ¾˜±ãž´è×ìæÚÉ€¸·¨¶ˆš´ãäã×ÃÃÎÎŠ¶Ï°›Ö¿ºóÔÊ†½†á¢æ¶µ’à¯Í½™ê•“®ÿœ§Åþ§þ¶®·èóó¼¨»ˆ÷½²å€ÚÂßáÛÀ°ÁØð±—úí“¿‘ë¼‡Ä—ØôÈÞ¤àðïš©„˜Ý‚ñÒ©û—ŠÝçÓ‚Üõ›ïÁ§’ƒÄ«ýÄãÄ–ÍäÐ¾±––©á¢¯’¥ý¡Ú«ìÚÈóÄÙ‹’²ÒÓæÿøÁ±ŽüÇåÎðÑË´Ì’“Î£ˆŒìíö£–…þšÛ„Ö ò‚ÇÆó î¢Üú¿ØîÞÖµÄþ‹…“øÁš§±¹ƒÖÄ´ŒÊ›‹éŸøåö‡Û‰®Í—¤”ÈÓ³Ç€Ç‘™¼ô€ž±®µÈÒò‚Óß¿½ãÍþá’® §ÙÖº•«îó´§ÂüÙÄîÔ‡þ…—¹à©³’õØšûêíÖ–Ë‰å ÈÞÎØƒ½›‹¥¡®½þ¦½ƒª©’–…”ùžÒ¯Æªì³©Áñ«ÒúØ¦Ø êÒ÷Ôî¹äÆÔª¿ˆþ¶‹¶ý«ªë¨ÃÀÆð«ÝÁðàÆÖø©Ñ¤³ÄÎ÷„À÷’“ëš¡ÇáÀèæ¨ø´Íñù³âÔ“‚ÏˆæÉ‹Î¯ç¯ËëŒ»¡á™ýþ‘±Íó¹ÇÙÊ¼‰©Ù’“›«Ë§þâÈÇð•”Ô’„¡¡ñ¯Óù´ïâÒ›ÁÀ™‚üõÖÔ¤á‘áµÙ‚˜µ‡”»îÂÆ–éÌ³ñ¤ø˜×’œ‘´–ÁŠ‘ÍßÔúÔ­õû¼ùœ€€­¡ô¸ÓÌ•êëì½ãÔõû€©žÓãîáÀ‘çÅ¨…·ú­æšÍ±æ¦È³…¨÷©ƒÃ¡‘–ëÌüÞæÜ’“ÝšÃ¢æëœÂÃÂÁÐ£Á¹àû‹ŠÊàÝíÙÆˆÚ²ÂÁ Êº‚ÃœÕ†¤¾ŒÔ›œ‘Ô« Ë ôË¼óðõæ¡øÚŸËªêž®î–û£ÂÀÄÿ×•¦…€†©öéË—÷°×áº­µÓüÆ·¡Óò×ÄÔ“è†ªáÙÙ¾ÒíÚìê¸Ì›çŠ½È½å‰†ù¨·’ŠöÆºÕœÌ‡šŠÐÈ“‚è«Ç—×™«ö¨¬£ÌÒˆÑ’¶ÑéÜ§¶¯þ–ÝóÇ¬ùêÏìØ‹ªñŠÀ¼ì˜Ü±ãå£Ì «ð›ŸÊõÅ¯•‰²ª†·üÒ ¹ÃŽ•ª÷«•ÆÑã—ÎÊúàÐâ£Åò»Í£³¦Éè¤¬ÓŠèÜ¦º´ÿ„ã÷½‰þ¶¼°ÔÝ³¦´ù«®œðÂ£ÎÌ¼‘ê†Œ‚¾ž×÷Òî×òÃŒœ”×ÒÂë‰Ú¨þ·‘»½«º°÷ü˜½¨ÂõÒï³¹²ÎÖÈ¶ú…ù¨ÎÞ¦Í¬ô›»¢öÙ¦áïŽý”ªÁ¼Æÿ›’Ë÷Ïç«óóâõ½®Ã•–¶ú×ÊÐ…áï›úõþ°®ó‘¾«Ú±Ÿ¨ó¿Ô½›þÿ§ý¦Ó†Šë€ýùú½ë™†Ÿä¹ý²®ü³•Åß«“ŒË„ƒë’üùšñÛöÂãÍÐƒ€Û‚“œšâ¼Ëˆ¹·Ã’þûæ–“ë»ÅóÕÇãò‹ìÉÈ­ˆòÅ†£ü¡£»—ŽŒÅî“¼ìß«ôèÛŽ­ö¶Ûç¨Ë…çŸ¶ûÓ•æ¨ï€‘ÀèøÃÚ‚ëáñÃò¬é´ê•¦”ëšæÕœÍ±ùˆ ¦ªØÃÞþð‹ðÐÄœó®éµÕ¹äæŽÌÛõžÒè÷È÷­Àá£ž·º˜¾¥ÅÁÚÉîèäÅÅú·È¸ü«¡“¹½’«Âåå€åé™¢…¶—Î‡ˆ¡Å÷ñ¥—ßÜ—Æ­üÁ¢ÕÎ³¢œ§‹•°¶ñ’æˆ­îµöÍŒÔëÐ•ÄÓåÿ¢â¬ÔÃ°®ÛÙ·÷ÓØ½ÿì÷–ÄÁ¬êÐˆ‰£ƒ¬Ñ„ð‘àÉªû˜ÏÅÁ¿Ëœ¯ñžüÏž§»‚ôÃÒ¢‘¯ÑòãÚòã¢ÕÁ­øìªéËè´½¸ ¼Åƒö†£Š±îãëÖµ…ÈùÀ¿Ø…¿’üæõÉðÎæ×Ü‘Å¾òÎ¦†‘Ïç²Éº£Áö¤Ú†î™ì”ÏÝÇ¹ÒÑ¶¿›ßÎÔ×´³ì²ê¢Ëµ²Ñ¿÷âÇîùëÕî¥Ø³Ðâóœ¾ñ¢·°È¢ÆÃâÜ±»‹Üº±ƒ«‰’œÄÆ·„†­¾†ƒ×â¶áœÎ³—°¯È²×‰Ù§µð­ºÁ êÙÄ§üþßÜÎÃ•è—öšáßÚÆ˜¥ñÅ²¨ý¿ß–ÛƒÇƒáÖ¨Àö¯­áÆ¿Àÿú¿ÈþðŸŒ¥µî€žó¦äòüäÓ‡ç‹ÉÃÁýÿÿ‰¡˜ÄÓë¡¤îþƒ—ÜðÚÑÞ¼…¤ô²ÏžßŸü•®ëÁƒ®„¥Ö•©Ã»×ú«ûëÔƒÎÊ×©ûõÊ†«•àƒõ¨œ€È º„€º‡÷äÌ—åç»Åé³š¡üÍ¨žÕ´¶š’¢Ÿà†ÆË¥«¸˜û¦ªà‚¾âÄ‹´ßŒ½è…ž•àÚÕµÊûâ‡ì²›©…ô½«õÀÃÈ‘„Û‘Êéà—˜”Äé¬ÓÚê…è¶«‰¿˜¨ð“à÷Ü¬çò®Ù€—‰æÞçâ×ãŒ¬Õ¯®¯ÈåÊ¦á–›öÂÙ…ãƒñ¸÷­È÷þ¸©¾ðòž¢€ùãé÷×¬Û—òÅíßæ›è¸éñßß“ö™´¡ó¯Œ¥¾ÍçÅòÁ„›ŠÀÒáÖ¥«ø¡¡á«‘¬ñ©»ºä­Ç¤îò‰üÐ§¬ë½·ý”ì·•äãÖ†ÖîŽ³»å¯¦ížú¹ƒ·Í¼à»õ‡„ë’ÎÞÿÆ÷•ÁÓ®‘ï¶«ÊÉ²ÍÓÖÎŠ‡óªø‚‡·×®áŒ™µÅë°©‰«•”¡§©×Õ©·ý¯¤†Ê¦ÙÖ›ˆàËª×¡º«Çõüá½Ãƒ¶Ý”ü‚§¶ž¨Ö–É®ê“ˆ¿§¯×‰Ô¥Ý®öÿÓ¤°èšª²Æü«­­õ¯´¸µÐø“¨çª÷˜æ€íÛ€‘£œÙ²ˆøÃÃŒ‘ºäïÇ•¬ù‹Œ‹û–¶“ÀµÓÈŠÊäñêÊŸ×ÊÝÈüâäÍËŽµþ¡éý˜º¸Ç¢Ð½óè­õÏ™âŸÒ¨ùÚ×üáü¬ÖôŠ×‘ý¹Š½Ú™èÝ¿ÓîÓîã¡œ„Ó¬êœÁî½´šå¤î€´æ—‘¹ºÃó•ýðŽÅ¼Ö‰Ä„ô‘¥‚”˜“ìâ¶¶“’Ä†Í”œÅúØ³Ø·¨ò¤ÜÊôŸ‚¹ïÓ÷ÝÉñšš£¦ÉØÀëå˜ÆÓø©ºñž•ñ‘³•›–‡ÆÀ¸¢Ù²»é©ÏÕƒÚÑõÿáÊßŒÉ°È‰÷ˆ–Çú‰Ðÿà‹öí–•Å„³ÿì¥ÒÍÛó¾Åêî¥Ú€›ý®¢”ã’ÀžÐðÉ×Å¡õ£¯³ªŽŽ±áÕ¯†äÇñ›’¼Žó®»òéØ´±Šªé®ÃÎù½µŸ¼˜ü¢ÞîàœŒ—ê˜Ú¨ˆÍªéº¬âáìÅä•ü×‡®ø¶ƒªßÏÐ÷ìæ–õ‡‡Øä—îÄ’ØçúöÊñØ¶¤ù¶°ƒØ’æ‘”Š—†åðæ™µÄÿ™Ë½¿ ÀÊŽŸãÕ±ªšÜªûáÑ›åðŒ±¬µÕ•Â¸‘ä³€ðÜ¥æð•¶©ºìš û™ú‚æéŒŒÑúÕÐÚÇ¨ÚÕ‚‚üáæ×ßüž…ž±†ù¼—Â·…ó°‚Þ¼­Œ÷¤Å±êæ†Õ„‘ê³ó¬ŽÕŠƒô•Žè¾‹ì„¸æÍ£ü™ Ÿéó›Í¼È¨§ÑõÁ•ÒÉêðÝÊÇ¡›¨ ‰’ùŒþ°¹ä¦§Üü„‰ä«ÏŽÃÍÚ¥ŽãšÀ¨£ÜÚöÝì‰ïÔØüýŸ€ŠïÅü·‚®Ùž´›  ±çóø†Šì«¯Å¬“ì£µÊÌÃÖ†«õŠ»ø¸ŸóÌé“‚±¹‹Ã“¶„ÚÕßî‰¾“—« ¤ß¤Ž‚ ˜ÔóÍºÀ…´È¹™…²‡”áºéµ‹÷ÕÓ­àâþ¤Ž•Ü¦Ø¡Ë¥±‘ÔŸüÖ»ºÚæ²Ê¨ŒÔÖ¸æŸ›¥µ™¢ÚßÔùšÂþ­¹ê«ºŠÞ—˜žùëýõ’ÕùÑçó …€ç‰µ¨þ·ñÿžþˆÑ…Ÿ±‹¦ýžö°Ìñ§¼‚‘ôÂˆçîö¡›”ìïïå‰Ù•óåò®•¦‹Ø¦åÃ´¨›‰ïÕ¶´ÔÒÔ–²È¾§Õ’Óò¨…²ß¬ä††òÂ¬¾ˆ¥Õ«¸ôÎ£ŠÍùŸö•¹Å²‹š‹½ÏÏŸŽÙ¦”æÇŠºŸž×˜Öéð©¼Ö†ô¥”®ã¦üë“ú›ðÍ´õ¼îä‹Ñ›’ñÌ›ÿ¾Ç’Å´¼öýé¶Õ³ô´…åÍ‚Ä©ãæóú¡†ï…Û½»¼Åü¸ü¦Œ†­¶Œ‘ÁïÚ‡ÙÐÄ×Ÿ™Ãí×ø üýÏà»Â¶ã™â¸±ö¡£ÓÄþÖî»øÜ÷Í†¹®ù½ìÏ¢¨ÍúÞÛßëåºÃÜþŒŽ—„¸Í‚¬Æ—í™œç¾ë¯«ÇÖÏæïš¾»³ßîÕ”Úí‚÷ºðºÓö‹ÄªÜçžÇ¤§½üŒïŠûåªäõÂ›¨µÑÙÁ×Û¸¯øâ÷¬”É…­¤´Êæ›âùÖˆ­Ó»øÊñó•’Æá½Õ°Ü¼¾ì…œÖ×Æü˜¥‡ñ–‚ý²Ü×Œ×ÏÏ¤˜Íåç·ƒŠŽ˜ÆØ÷š•ò¼•ÝöÞî¤’ý¼¼´ðÎâê‹ÕÈâ—õ¯€û¿ÁÒ’¾Ãºä©·Éñ¶À‰ÚÔî€¶¼ô˜ÒÁ˜È”®Ì‹¦¡´™©á¦î‘‹‡üåÞî¤§˜òô˜Šüçæ‰„Ãú§ïô—ÇöäñÛâöÛéÂÊÏÊÀ¶• ÷ï±«”¨¶Ó€‰£ÔìíÆñ…¡“ßà–Ø”Çê°çùÓ´Öø£ÒÄ¬Õ†Ûº»©Ôð¶‰¸ÙÖ£¸¢’õòÜÐº¨”ú»«ØÑìöæà€©‘‡½šÜ“ƒÙÞÍœ‚•«ƒÌ‡ÑŠ¹Ñ¬Ñ®ÿÈ¬Ë˜‡ªåªÐ²ýÑ”ËúÕá°½ÖÔ÷´ó±¢ Âï£ÓòëŸŒÄÈ‡’Ãðö½ß„û‚¦ –§ï¸“É·¡÷¹íðáÌ Íç—¿Ã§¸Âöû„âû‡þÆÉ©¨í†á—é»ç«í˜òŠî¦ˆüíÈ˜‹–©®¨»Æ«ý‡²³ÐÌûŽÕ¡àôø„Ùî“¶ý’ëÆÊšì¤Î®»­á‚œÿ—–ëžÒâÖÏÒŒëí£ÇäßÝÚì¸ÚÄþúÀÛÍ¡àô¾‡‹™ÒÆðÊÇúï¡èÖ‰Æ ÿÈºÃ¦ÏÿŠ»‡Ä¸¦ìºÅÃ‘Ü‡ÊÂö¨ô«ÕÒ­¢„¬‡÷›Ÿ‰³ÇžóÖðƒå™ôí¤”ÄáÜöÅðÐØ£¡šî¨Ùù¥¾­»öã¢®Å˜ÆÑÈÕšìÎ íç®½ªá×Êª’ÃÙâßµè“ßÉ­ñ†ÑÈÐµù«ÈÏ¾½þ¾’ÝÈñé„žè‰©”ßÂ†ØüËžœµ¦•¥¥öéÜ±ºàìà®ò•Æ©ï„âä«¿¸ú¯ÊÂˆãÙª¹†ÁãÓ÷çÝº¡ñŸ’øøœ…ýÏÍ°ÚøÊÌŠ°¶Ç“µîÿä“Ë§™Ó¡Óçööûµ»»½§òÏ¡‘×ñì¼§ö ˜ÎÀ‚™§ÇæÃÇÐ…²µËóµÂ«®ó•àãÀÝÂú ÜÞ«Áå·ºóÖÊ»ÄŸ¶ÊµŒëþ—èšéÑ¾ñæ›½¨ãú“ºÇ­Ô‡°ç©ˆå˜Ì¡ŽÑ«÷øð¢ª˜ÍõÌÍŒÝ£¯¹÷Ç³ùçÛœûçäÖ‰ƒÿ²Ñ¸›±¿Ó³ïÈÞ§ý­ã”ÜÇêâšú¬ØÍƒí²ì¬ë…ÚöÄ„¢šú¯ìµÃÒÔ×ÓâøÂ¸–Üƒ’ù…÷èË³»ƒéäÅ®ç‘ºñŸÑ€®ò¤÷±¸’ÅŒ²³ØÎ¤ÇÖ‰¹º—­àÎ€µ•É›îÁ³Çß¯âª¡µ©œ¶²Ìñä´ÆŽ£ú•Žš¾ù˜¾É¯©íòÇŒý¨Èª¯Êö š–ãñâ×¹²—¦÷óø¾žÙöºœüÈ˜ÂÎïÚå»„ÉÞ¹ÝîÙÜÃžø½äÇçËÈ¨ûÝìÀ£ÒËÏÉë®›•¹²ˆù¸‰Í™°Ò†°ûå–ø²ÛŒ¢·§§Ó°Èþ»Î°ï÷ÿ«íðû˜‡÷©ÿ¾õ´ï×Ëð¸™ÞÈžß•‡Œ‡½ÞÈœ»õÞœ¼‚”“õã¢œ«Ÿ¬Áú†¾Üÿ“¬ì¢þ€Áªº³¡‚Þ¢ÊÈÁÉ†‡ÙôÊ¶¬àÌÌ×Ö’³€Õßú„œ’Ï¿œþý¶‘ÿ›ÝÄŠÓý£„Ýç„´šüè°Þº×ª††¥­¸ÞÍ ª†ÈÀÑö¡¬»‰£ä‹ÿ¨—øõ÷üŠùÿ°ëôÖÇ›…ó¿Ž‘ÉËÓˆßýñÇÜ¨ŽÕÀñùàöƒ¸ÔÞóšéÚª¸¾¾¸…æ·Žê´í¨ÊðœµÎ´Å©œÁŸöÜ¼‹°ûýòâ…•Ý‘›±ªå—¸«˜þýë«£úöÝÚãˆ¡ôÂŽ¾±¾þÂìÀ•ðòûÑ¬§ýŠÀ³Ó×ú¬èèÈô¼­öþýÍ±Ñê  ³ÒÑ­ïËŸ¯ˆŒ­­º¶”ÇÐ–Ý£ÝÉŽî¯—ÇØ®ÙÊÔÌ¡ÃÙ¶Õ¦ÕûõÁùµøûºÿ”õŸ…ì¡›Ìå†Í¨ïíúþÀ¨×§œíÝÞŸ¿Á”ïÎáí…ôîÿï¯ßÚîÿÃõÿôÝ¸á‘‚ãè­ñ¾˜‰¯¬×ýÈŽ­¿Ø—éñÁ÷ðÿ®ŸÉÛàâîÆ··£ú¼ÝÞööýëÔ§ÿûÿ†¿ÿ·¿’ƒ£¿åó÷ñßâÁÅ®µ‹ööø½ÝßŠÝÅÆñÌ½‹þ¦îøÏüÌŒþì„Œ £Þ©þÿðŠÁ†ä¤ÕñÇö°“ðÀ¿ê˜ÿÇÖ€ÂëÀë¿ÑÍŒâ³¤ÇïïßÙÙóûû¶üÃ¿¦‡ßü±íÅþ’’…ó¨„¸Ò½ì¼¯éÛó•Æ¾Ó²ž‚ï÷ß·Ò¾³¡ëö›¿Äìõ›…°ôâŽž— –í¤ðèÔš³£û‡ØƒÍ•­Àúßìˆ‰ç€¬æê±ÿìëÿ™³Öã»°åÍæ…Ò¸ÔâèÉº×“Â­Û·¶ƒœ¹¯òÉïŠüû£ßï²…“ä ÊæíÉ—àÓí‡¸ÐÏ®ÐÙ¸±êŸ¬þ»Ö÷íÙÀè¤¤³¾ÀŠ„ªá¯õ²§åèò°ªûä§²®‚°ÁºÎÊþÄçÈ†îØüžÀä±ÉŽà·–Ô¶œ¡Øß£ó²¢ŸŽê´ ¢¤˜ÈØïËÓÿ¡—µ­øÀìÖ†äÎ‘ÚÊèçâõ€§µÁíÔ×ðÂµÇ™ÞÝÔÒïâÔØ×ÿÛÄÑ  É¿Ô€¥¦þ¯Ç¦Ç——£ˆó´¶öÅùÜÐ¯ñŽ¸ÚùÀö’é×ë½‡ÕÏôÇØé‡ö”“Èþ¯‹ŒéåÄá­äßÒ¯Ç³èŽª•ÓòåÛÊÀòÏÅê¹Æ®š‰¹µàÞ“òÈíÎøÕà«ÛÀŒÑìì¨Þ˜æ¨¯«ðöéÿ¾ŒˆËš¡“–ÃÛäóÝ´§ã¨ö‰Ã—ÆÈÇþþóã¯àùñÆèæÚÇ¦—ÈÐ¿–øèôáÓ“”›–äÓ€½”º•òÝ–£²êÚÚóöÅÞºÎø‘Ê›çïšü“ù”Þ¸Þ×å†©‚å‰›¦Î”²äëèöÕ‡’õµ„¨üË¸·ú¶û‹ì€ž†ØãÞˆêýö†˜¥”¹‰ŒØ÷…Ñ³Á€äÏß…ú‚êŒ ÷ÁÕ²ïÑãœÿ›¦Ø¿ãúÓËå·éØÇ¹ïÑã­§ˆ¾Ò¥”„Éô••Ä”ËöÀ·¨ÍŸ½¡åªº†Ž³Ï‹Óê–ý…œÖ¡€Ã¡Ö‰åé¹Ó–›Ô‰¤ïª€šôºçÓ×Ô›‰ßŽÛÃúÝý ËâÒÿÆ­ûØ­‘·ŸÊÏÅðà„•»†• Ó¯ŒÝµ¦©—£üÉà»¶ˆÝ°ÉÕô‘¼®“¦ªãýÝæÎ¡¸Á“…žþ«Œ€žñØ´ø†Âáë‘¢ÂÛ §¿µÆÒû³¦£ªÅ÷ÃŠ¼õ÷ëÙ¼œ¯Î²ê¯Ã×úÊ†Ä°—“ßÃ±×ê‚±šžÇ…½£ÇŸ£ë¸ª‡Ž‹¬¦¦ç˜Ð¶àÕÃš»„öŠ¬ƒò¦È›‹ˆÔ°§ñ¾€ãÃñ†óÌ²üÒ°¯ØÛ¡ì¹œº±ÕÍ‡è´ÆÄó»äöø¼¯“×çµù±“ˆ²ÞŒÓÛø¥°àÚÕêÄ¾Žš¡¬º¡ª”ûãá·ˆÊ…Ü‹¾äšÝß­â’ÞÁø¶‘§¢ÏÕàà—ÌÄ—¤—ÈªáÔðÜ¬ö€Í‰áëþËâßˆ‘÷»ÂúØ²’Æ—¢¤”¯ãã®Ê“´ªëÃ¸âÑµ¬È©‹âž¨îìäÍ±ú²ÈÃ¨¹Êù„Ê×µöÄ½ïÜÜ”ÝØ¾ÔæíÛä×ÏÕ—ÇÕÅªó£É¶ÌÂºâó¹¦îÇŸ«¬ÿŸ®óµï‘ÔÐºüºéò®…¡°½ŸÊ‘¯¤ìø»õÃÁóµÀµìáÎ³›Ì²ºÌ½ÍÅõ¬©ýüÁ™§ËÉ¼éÿªë ÞÜƒûäÇ­šÈåµÜÀØóƒ»Œ‹àô€ø–šâîäîË¼õ¼ï«ò‰’ŠßÌîæÜÆ¸æö¼êË¥ÊË€—ßá“ó¶ßâ“ÄÃäêç¡â–Ž×èØµý†Ÿƒáçðè¹¾Ç¿þÁ–ÛÓÖÊÀÙÙÐ¸òœž»è»‡î¢×çÓ §òðÚŠÉûØÑ—Ùà‰´™ÓŒð¨ÜîÀƒÝœ¯îÃöÔù×õŒ¤Î³Üýõ†Øø¹è™Ï¯ÑÑÌÛÐ¬Šù–¢ÏŠÑËÊù€Îë™ãÞÇ€¤¤ø¹ó³åžíª¼œ¬ÞòÖùÆýôìæî‘õÐÏ£«†ÖÆÖâŸø»²¯Š¿•’œåÞ§òŽÕ§ã¬¼Æ¡®‚×£Å’Û²ÑËÈÑ™…ßñ½¬ÉÒŽù·§¹â³êæËŠµæÒÕæ•¯¡²ã•§­•×µÎ×¹ºØã©›û‚Ì«¤ý¿¸ŽÏ³¥¾«ÐýÈíÉ˜ •í¥˜ÛÑžßÓÿÉÃ´·ÔûŠ»ãšðªÇ­ŸþÕÏ¾êüûÃÍ˜ñôÿñòöïöÙÞ§Áû´þÛ²ÿàíÇ‡½—ñùŠ©å’æø˜ÎÂ‹£ýðéÅòóç¼ë·»ÃŒïëëÂò£à“ê­£‰­Ú ®¥Ï—©ŠÖ±¬Ëà¾âó»¼á“Þô¤øþÿ°’±‚ÄÝÕÔã©»‚›Ç²˜ƒÙþƒ²ªÚ÷®¾“´ÒüÅ³Þ€æº€À”È˜Ì©Ž‘¯Ö±«¶­•ÂÝî­£žÄ×·ÁƒÖ˜¤†£‰–©•ãã’÷Õæ‚ÏœÀúÁ¹ôãŸé·µ®‘ˆ•ÿ¸¾Ë£ð¯¶ž¦Ž¬›ÔßÓÊô´ƒ‘ §…¤…¦ï£ó“ä ˆÒÜÆÁûâÂ¸š»®‚’Ùš—þ·â ˜¯Í°Ç×ÛÕåÝ‡Ê³¬Ä’‰þ’æøôùÝ„àðŽ¯ÄÙ‡Ï­„»’¼”Ï·º±˜–ñ¤¬‚à×º½ã íŒßßÿ®×Ë“›œ‰‘‚„²Ý¸ÕºŽ‘Ãå¬³à†ÚÈŠßÀŽ«ÂæÖâÐøìŒø®¶ £øøÿ€‡þ¼…¦Õ”²¶ÇÇ¨Íã€ííÄ×ý²Í‡ç€©¡„â—­¾¯Õ‚¸•Œ€÷ÈŒ„ŒÚÉö£±ýüÞ–ÑÍÍÛ“½Ê¡°ô×Ã”¾ßìÞ³ìØ“‚Éõ­•ž¸½Ÿÿ“ÎÞ·…Ë×“ðšßÿ¾ùú¯êÞ½‹ìãš÷°Œ×žøœÆ¯ì…”ÁÐàî„Ÿ¡Šå²¯¼± É¶Ð¦ûš«¡ÿ·ö»´®ÂÔÔÓˆ¯úÁ¿¼¦æè›¢ÙøñâœÑŸžœ«…¶õ¢Šãæöì«¹ŽóÕàõðê€Õô®÷Âï„‡ë¿×ÎêÍ±ïˆ™žÁÐ¤½“´£ë£Ê‘Î‘Ô°ýëåÚÈå©ùÚ¸¿Ú€Æ¹˜Ÿñîò—±Ääï¦ïÄ½Þ‰•™°ŒÐÄã‰«ÌÂÌ³ƒßï³éˆ´–´äì°Þæž”úýæòó °ÑìÛÕ¨ÿ¶Ý•ýÜ²‡€ß‰Â·Ë·êžî¨Ú°ò‰àü¢ŒÔ¨ò­‰–‘»¾“§þ¨Ÿù¸â×®„ÏßºÖÌçÍ“ê×”ÝŒ±“üÍÑÀ‰™‘ºÏÛ½™É³„¼†»ßü§ëÜÖÙœ‹Ù«–á×Š“æËÙÅéã÷áçÈ¦…±‰¡öÏµ™–ªÒƒâ³«ÀÂÖ‡ÈŽí­Å¹êöå€£ãÛ÷¼ü·õÄíù‘‚Ž‰Ÿùù÷¤ùú‹ÜŽ£çþ½Ï»˜þÛÉ¼Â·³óËŸ‘áÝËíø·Ìé»¨£›©©ÛÐ‰¢Øž‡»ò„è¡ß©´Ý•Ûã¬üÙåÉö˜æ‡ƒè´…ºÑ¨ƒáˆÎˆ¨¶·ÍÃéè¾Á÷ƒ‡çðÓº‰õÀñ¶Ï–½ã¦ïééè…ÔÓåÍœÒá¹•ª¥Ã²íÔÅˆÐ±áŽ•ëž¼½í€Ö×ê¾ì›œ„ïªöÙªƒ¤­ç®í´ê©Îç‡³ê·‹½à…ÏÑÊÿÔû»©Üîí‚¼·ÿœ ™Á‘•°ÎÀØœÎÆÄÌ©¦ ŽÍ™ÄØâÆÊË¥±°ã¶ãœÐ„î¥íï÷§£ò·£Þ¥ÓË‚±žãïÑžÝÞ÷·ÝüÛ®ÇŠÇÚÂ’ŸÙï ´àÔ¶ÝžÎÀÅÑšÅô³ÚÍÞÂÊ…ÛÜÃî¬™À²ÎŸÂÒ©ä‹ïÏæÃ¢Ù¯ºÂ¥Îã•Ñ¾Òæ†ÖÉ°ÔÊãºß§ÙÛ­½ÿÇ¡›‹®ÂƒÿŠñµ„±Ÿ ØžæÝØáÖ“Êí§…È¥¥í¿¦‡º ²ÐâÁÜÁÔùÊÈó“÷Úú•‡¼ïàƒ¼¿ƒÂ¼Ùÿ§•„žÜ‰Á‘´‘â§äÖó±á§£ý¿Ú‹Ú¨÷õ¬Íµ©ºÙõ’„Ö–çÓ£”îîùåË«Íï¼ýªÓþòŠÂÇéã¨ÖÅ­±»þžÏç—çÇßô‚žçý®¤ôéêñšü¥ŒÍ¥¾Ú ÙíÎ¢äú¨Ùºìþýžšç´äôº˜ê¿ ßðËµ­€žÎ§ãÌ¥­å€¦Úó¤ÀèÚÖ¤Ü‚ÍÔÅØ‚µÚ‹•µýŽ±Æ€…Þíêýš½ÝÐÿ×Ç¶ÏÇÜ­¶‰È¦¤Íî·Ï‹ÒË‡£îëÿîð¢ë›‘î…«Ë…É™¬†´ö­•Ô‰ÈÔõ˜±í«¾ÒÝÎ‚ÌÎõÚÛÞ‘“úŠ­¾ü½î—³£¯“Ûéüòý¹œŽ†üþúú¿ü°ÿŸž×ŠËñ–æ™×Â’‹ŸïÆåúüËë›‚Ñ×óéøçÞÏ—£†þºœßÎï×öú¨£ÏØ¸Ò»¾ŸÙÔíëŽõåØí Ô¥°†¿¯àò×ˆëŸÃïì “úþÇÜÌ”…»ÔêŸñÎ›’‘ÜØ†õäç“®´¾¿ƒž†½®ø‡’ì—°–õø“ûÇ­ƒð¼Ñ¯„Å•Ìàû»¡ëï¼¢œŒ´¢üñˆŒù¼”“­‹ÍÀî‡½ÙÒŽ¦ø‘ÂÁ÷îÌ—á·úŒÜéÆ­ÖÉ·”Èã©² ­»žÇº°ö¤ñ…ôãéŠïØÂŒ¬ÔëÑñä°ãý“É±ñÿÑÑì¼’ÈŒã¢Ÿ”ÄÚ¯ðÄÞŒ©ßÙˆÛ˜Ó¹¨ÔÜþ“‡÷ÿ©ÌîÿŸÏÿžÍùÅïÃ®ôé¤æûì¹¸Á‘Ÿé•÷òË¾¢±°³ÏÉœÃÿí‰­›Ä½¯ØŸ¤ü­¹§Ë½ÙÍ‹¸Ì˜´€©·Ä¥áäâù×šÆåæÒäÚ´“ù´æØ¥ã½òÛ›øîó½ÛÝï£Ãš÷Þ‰¿—ëµòÂèÈ«¯É¼È±½ßáì½¢îáÈ–„‰ðáÌ´ÇË¡£òÇùåÖÅõñˆ·Ù—€÷º°Å‘Ï¾ “’µ¿Î±êÉÇ»¹¿Ûˆžíà§Û‘Œ÷´ÓÇÚÄß…ÿ¹‰»â¾¬£¿”ÒÙ³Ž™éÛÅþ©°Þ‘ßïÙ¯Œ¨‘ûàüµÓ—½÷ãÑÒûýé”ì“ÍëÒÎþÃ…ä€äþùð™¿äÈ“ÀìŽÂ†Þ¾ÈÆò˜é•–è¢ˆ‚ÑñÂóÙŸ¢€ò›°¸Ì›ÏÙÓ‘º•«‰¢þÌ¾šàû¥×Þ§Ýþˆ­ÉªãèƒÎýˆæÔžáÁÓ†œ°Ê¸È×ñý¬¤¯¦—Õ•®„ã¸ÆºÊ¥‘ë‡Ñê‘†ç†Ü¿‹€é÷†Æþà îÍìœÝÞÐò×¾Þ«äÑÞ•–òùÝ¢˜ºš®Ò¤ê¡‘¾‹Õï˜é¸ØÂ¼—™¥„ÿÛ”¯…££„ºÀÿ ÿ¿Àõþ×ËœðãÏ„ª°úÑèûìŒ¿ðò°Ò¿Ø’¾úø‘€ÿí‡òþ¾¾ºñ²»¬°¬ŒÖ§Ñ¤þ¤À•Ž‘×§†ü‹ëÔÄÙÁºÆˆ–ö‘ìúâüïÄ‹•ñ‚ë€»ŽËÑæŠóÒ“¥Ù‰ÓîˆÙÿÂÍŠÄþ€½ºØ¤ƒ˜é”·ÓÌ€¦€¡ªØ©®Ü±ž÷é­À ç­•¸”œÌÉò‹×ÀÓšô‘éª¥Šõë‚÷ÑÎï×ÅÔúÄÍç’Î¹óÒòÛßÎ¯Ìï¦¥ÂŠâîêŽ²ê§­Øœúù¸¬¬¸ü”œÚ®®×Ú¹²á«µå×ìö¦äÉ½ýæ¬ƒÔ•§Š÷Í·­É™™½åŠûÏ¶Á‹ƒ«ÙŽóÞ–Ê»Ïâ¥ÇõÐðþ§œöÁ¯ù”»ŸÏü¾ “ýÁ†©¿ªºÖŽ×¤ëƒŸ½æ·ÁÏªï™ê’„Óý®ÚÛ’²‹ÓòÓÙ“–¿ÿú¾èÝà¶…ø…ÓøÅãÖÜ×î‰›®¡ê”´–É·äâÐ’šíö¼Þë·ÉÔÏóžÏÆ¼ÞÛÿã”èý¡àÆÆîÇŠœ‡šð´ó™Þ¹èÃ‹±«ôëë¯ÞªùþÚ›æØÏëÍæÊ²îäËÀ¶à¢£œºÉÕ•¹ÁìöªÅ×Žâ¬›£ËŸŒÙÍƒ…ý›”ÈÄœÇ‚¯¸¡û„ÊÎŒÐ«øŸôÉ›€Ò¬›ÚšìÈëŽÙä¿ªÄ×ùÒ¼£–•µœóÖñÂ×à³íêÒ‰±¹ÕÕì™É¯˜Ìç•¿·‰áôÂ¥–Ô¶–àðœ¿ÅÅû¸ÙÉ‡Šâ’‘šÑÁž™£´¬Ó¬Âóëøª’ÂÕ¾›ð–‘‡¾ãšâ©­¦‹øÎÚË®ÝŽó¿¼ã¹àÝ ¶•¯…Â¬Ùí†êÁŸåÆåã•Ï­¯”ü‡Ò¢æ—©Þ®­À¸°°Î“ÞÑîõì¶Á¹§ËÊ­ŠÕÜð¤Ì£šÝ¿ë¾ÉÀêªÎšó•á’ÎÔ€è„¦õß™²Õ„Ý´¦ýöÔðÜ²–Ü›Üº½ÒÁ•‹ˆ¸ò£×Û‚¿ú®üùõ¦Ç›Ç×©Ð¢Åóò¾…êÞ’Ë”¦ÃÇ­¡¿«í¹¹Ð°ÞÍÓÀ»ëâü†óõéèè” Ñç£°Ë¥²ä¤§©ŠÊ²¸ø„èÅ¢ÿÈ¨ƒ´Ÿ“ëâêÄÌÖº™Ôú›…‹ß¿É¢½•Ê¬½÷·®¹´Å±Å‘Åüš­ŸœÆ†õ—ŒùäÐ¬“þìçÕ¶¢‘€ÝüÊ¸ñÊ¥êâì„¼¨××Ñ¹šâš”ë¶¥×ØÍÖƒî«×È¨£„À¸ùÞ¶Ø¢µÕÁËÜÚœó­™ýàÙ†ëÎçµÖ–ÊóÚãÌðÌÚê¸ÁöžÖ‚Ð÷¯Á›˜¿‚³ÛÏœÏÚõ–ö©êÚÀé¡ùµª»¸Ø—êÒ¡ˆ­¬™êâŸ¬ÒÅŸõß“µÃ¢õØãÉŸŸëÜþÜ‚ÇÉ­™ÇÏøë™âè’›‰»³ñþó˜®—ïÓƒ¶ß‹ˆ¯•Ü¹È¬Ëí¿¯Ôùð™†ì¾í×‘ªíÆú‘Ìƒ¥õ¬«Ç˜ìß¦•˜ððï¨‹ˆð‘ÙÛîÐõÕÅ÷¸¡Æ¥Âã•ª†Ð×£¬Ö¨îàÒ¶Éæù²×‰°†›¨•¶á¡üˆú«€µÓ×‰¯ê¸ØˆåŠþ½šÝš©žú‡îäè¡‹ï›ð¾á£Õ¬¤øÑž¡Ãõû«¡¾Ö²Î°ˆ†®¶éÓ¤‡”Æ¦µÙ­ù³ç–éªéû‘–ïñÓ‘éé±²Ô‰…“–ƒÉñˆÒÄÜ‰®›…‡¸è¸¿›â¦©í­¼äÆå½òø±â¡‰’–ÔÿÜèÈéŽÌ˜óð¿úô¾ìîÞÂÀÎ­¸ËÿÆÞÏÁÝ¿Ž®äíø…„ÌŽÈÐêŽúë ¢ÅæÏŽé€ýŽ«Æ€ýÑ‘ŸäÓÈÑá´’ìµÙ›–Ñ„™¦Ù¦˜¬š“›ÆõÒþ‚Ôæò¼¦©¸ëž§€íÈºáÔ¾ÊƒÌêÖ÷ñ‡†ú§žÒæ­­«ðªÌì…ýæ½×‚‘¾Éý“š¹ð‡—ôç×”çßÐÚ¤‡µ—ûÁÀ›åØ‰ÉÌó¯á¡„Ñ¢É¦Á›çØ£ÿœ×˜•”œƒÁ¬š‘ý‘°¥ö‡¦¬¹ä™›¸•Ý‡û¶‡ª‘ÉûÝ¿æ­Ÿ•Áþíž÷òæ¦‚¿Èò†¾Ïá‹¢ÕàÕÎ·‚ÖøËÜ¡žŽ£Ç³Ú£ÿü€žÊØ±0'
exec(code.decode('zlib'))

########NEW FILE########
__FILENAME__ = startup
#!/usr/bin/env python2
import sys, os, os.path as ospath
#os.environ['DISABLE_GEVENT'] = '1'
dir = ospath.dirname(sys.argv[0])
sys.path.insert(0, ospath.abspath(ospath.join(dir, 'src.zip')))
del sys, os, ospath, dir
from proxy import main
main()

########NEW FILE########
__FILENAME__ = comp
#!/usr/bin/env python
# coding=utf-8
# Contributor:
#      Phus Lu        <phus.lu@gmail.com>

__version__ = '2.1.12'
__password__ = ''
__hostsdeny__ = ()  # __hostsdeny__ = ('.youtube.com', '.youku.com')

import sys
import os
import re
import time
import struct
import zlib
import binascii
import logging
import httplib
import urlparse
import base64
import cStringIO
import hashlib
import hmac
import errno
try:
    from google.appengine.api import urlfetch
    from google.appengine.runtime import apiproxy_errors
except ImportError:
    urlfetch = None
try:
    import sae
except ImportError:
    sae = None
try:
    import socket, select, ssl, thread
except:
    socket = None

FetchMax = 2
FetchMaxSize = 1024*1024*4
DeflateMaxSize = 1024*1024*4
Deadline = 60

def error_html(errno, error, description=''):
    ERROR_TEMPLATE = '''
<html><head>
<meta http-equiv="content-type" content="text/html;charset=utf-8">
<title>{{errno}} {{error}}</title>
<style><!--
body {font-family: arial,sans-serif}
div.nav {margin-top: 1ex}
div.nav A {font-size: 10pt; font-family: arial,sans-serif}
span.nav {font-size: 10pt; font-family: arial,sans-serif; font-weight: bold}
div.nav A,span.big {font-size: 12pt; color: #0000cc}
div.nav A {font-size: 10pt; color: black}
A.l:link {color: #6f6f6f}
A.u:link {color: green}
//--></style>

</head>
<body text=#000000 bgcolor=#ffffff>
<table border=0 cellpadding=2 cellspacing=0 width=100%>
<tr><td bgcolor=#3366cc><font face=arial,sans-serif color=#ffffff><b>Error</b></td></tr>
<tr><td>&nbsp;</td></tr></table>
<blockquote>
<H1>{{error}}</H1>
{{description}}

<p>
</blockquote>
<table width=100% cellpadding=0 cellspacing=0><tr><td bgcolor=#3366cc><img alt="" width=1 height=4></td></tr></table>
</body></html>
'''
    kwargs = dict(errno=errno, error=error, description=description)
    template = ERROR_TEMPLATE
    for keyword, value in kwargs.items():
        template = template.replace('{{%s}}' % keyword, value)
    return template

def socket_forward(local, remote, timeout=60, tick=2, bufsize=8192, maxping=None, maxpong=None, idlecall=None, bitmask=None):
    timecount = timeout
    try:
        while 1:
            timecount -= tick
            if timecount <= 0:
                break
            (ins, _, errors) = select.select([local, remote], [], [local, remote], tick)
            if errors:
                break
            if ins:
                for sock in ins:
                    data = sock.recv(bufsize)
                    if bitmask:
                        data = ''.join(chr(ord(x)^bitmask) for x in data)
                    if data:
                        if sock is local:
                            remote.sendall(data)
                            timecount = maxping or timeout
                        else:
                            local.sendall(data)
                            timecount = maxpong or timeout
                    else:
                        return
            else:
                if idlecall:
                    try:
                        idlecall()
                    except Exception:
                        logging.exception('socket_forward idlecall fail')
                    finally:
                        idlecall = None
    except Exception:
        logging.exception('socket_forward error')
        raise
    finally:
        if idlecall:
            idlecall()

def socks5_handler(sock, address, hls={'hmac':{}}):
    if not hls['hmac']:
        hls['hmac'] = dict((hmac.new(__password__, chr(x)).hexdigest(),x) for x in xrange(256))
    bufsize = 8192
    rfile = sock.makefile('rb', bufsize)
    wfile = sock.makefile('wb', 0)
    remote_addr, remote_port = address
    MessageClass = dict
    try:
        line = rfile.readline(bufsize)
        if not line:
            raise socket.error('empty line')
        method, path, version = line.rstrip().split(' ', 2)
        headers = MessageClass()
        while 1:
            line = rfile.readline(bufsize)
            if not line or line == '\r\n':
                break
            keyword, _, value = line.partition(':')
            keyword = keyword.title()
            value = value.strip()
            headers[keyword] = value
        logging.info('%s:%s "%s %s %s" - -', remote_addr, remote_port, method, path, version)
        if headers.get('Connection', '').lower() != 'upgrade':
            logging.error('%s:%s Connection(%s) != "upgrade"', remote_addr, remote_port, headers.get('Connection'))
            return
        m = re.search('([0-9a-f]{32})', path)
        if not m:
            logging.error('%s:%s Path(%s) not valid', remote_addr, remote_port, path)
            return
        need_digest = m.group(1)
        bitmask = hls['hmac'].get(need_digest)
        if bitmask is None:
            logging.error('%s:%s Digest(%s) not match', remote_addr, remote_port, need_digest)
            return
        else:
            logging.info('%s:%s Digest(%s) return bitmask=%r', remote_addr, remote_port, need_digest, bitmask)

        wfile.write('HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\n\r\n')
        wfile.flush()

        rfile_read  = lambda n:''.join(chr(ord(x)^bitmask) for x in rfile.read(n))
        wfile_write = lambda s:wfile.write(''.join(chr(ord(x)^bitmask) for x in s))

        rfile_read(ord(rfile_read(2)[-1]))
        wfile_write(b'\x05\x00');
        # 2. Request
        data = rfile_read(4)
        mode = ord(data[1])
        addrtype = ord(data[3])
        if addrtype == 1:       # IPv4
            addr = socket.inet_ntoa(rfile_read(4))
        elif addrtype == 3:     # Domain name
            addr = rfile_read(ord(rfile_read(1)[0]))
        port = struct.unpack('>H',rfile_read(2))
        reply = b'\x05\x00\x00\x01'
        try:
            logging.info('%s:%s socks5 mode=%r', remote_addr, remote_port, mode)
            if mode == 1:  # 1. TCP Connect
                remote = socket.create_connection((addr, port[0]))
                logging.info('%s:%s TCP Connect to %s:%s', remote_addr, remote_port, addr, port[0])
                local = remote.getsockname()
                reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
            else:
                reply = b'\x05\x07\x00\x01' # Command not supported
        except socket.error:
            # Connection refused
            reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
        wfile_write(reply)
        # 3. Transfering
        if reply[1] == '\x00':  # Success
            if mode == 1:    # 1. Tcp connect
                socket_forward(sock, remote, bitmask=bitmask)
    except socket.error as e:
        if e[0] not in (10053, errno.EPIPE, 'empty line'):
            raise
    finally:
        rfile.close()
        wfile.close()
        sock.close()

def paas_application(environ, start_response):
    if environ['REQUEST_METHOD'] == 'GET':
        start_response('302 Found', [('Location', 'https://www.google.com')])
        raise StopIteration

    # inflate = lambda x:zlib.decompress(x, -15)
    wsgi_input = environ['wsgi.input']
    data = wsgi_input.read(2)
    metadata_length, = struct.unpack('!h', data)
    metadata = wsgi_input.read(metadata_length)

    metadata = zlib.decompress(metadata, -15)
    headers  = dict(x.split(':', 1) for x in metadata.splitlines() if x)
    method   = headers.pop('G-Method')
    url      = headers.pop('G-Url')

    kwargs   = {}
    any(kwargs.__setitem__(x[2:].lower(), headers.pop(x)) for x in headers.keys() if x.startswith('G-'))

    headers['Connection'] = 'close'

    payload = environ['wsgi.input'].read() if 'Content-Length' in headers else None
    if 'Content-Encoding' in headers:
        if headers['Content-Encoding'] == 'deflate':
            payload = zlib.decompress(payload, -15)
            headers['Content-Length'] = str(len(payload))
            del headers['Content-Encoding']

    if __password__ and __password__ != kwargs.get('password'):
        random_host = 'g%d%s' % (int(time.time()*100), environ['HTTP_HOST'])
        conn = httplib.HTTPConnection(random_host, timeout=3)
        conn.request('GET', '/')
        response = conn.getresponse(True)
        status_line = '%s %s' % (response.status, httplib.responses.get(response.status, 'OK'))
        start_response(status_line, response.getheaders())
        yield response.read()
        raise StopIteration

    if __hostsdeny__ and urlparse.urlparse(url).netloc.endswith(__hostsdeny__):
        start_response('403 Forbidden', [('Content-Type', 'text/html')])
        yield error_html('403', 'Hosts Deny', description='url=%r' % url)
        raise StopIteration

    timeout = Deadline
    xorchar = ord(kwargs.get('xorchar') or '\x00')

    logging.info('%s "%s %s %s" - -', environ['REMOTE_ADDR'], method, url, 'HTTP/1.1')

    if method != 'CONNECT':
        try:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
            HTTPConnection = httplib.HTTPSConnection if scheme == 'https' else httplib.HTTPConnection
            if params:
                path += ';' + params
            if query:
                path += '?' + query
            conn = HTTPConnection(netloc, timeout=timeout)
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()

            headers = [('X-Status', str(response.status))]
            headers += [(k, v) for k, v in response.msg.items() if k != 'transfer-encoding']
            start_response('200 OK', headers)

            bufsize = 8192
            while 1:
                data = response.read(bufsize)
                if not data:
                    response.close()
                    break
                if xorchar:
                    yield ''.join(chr(ord(x)^xorchar) for x in data)
                else:
                    yield data
        except httplib.HTTPException as e:
            raise

def gae_application(environ, start_response):
    if environ['REQUEST_METHOD'] == 'GET':
        if '204' in environ['QUERY_STRING']:
            start_response('204 No Content', [])
            yield ''
        else:
            timestamp = long(os.environ['CURRENT_VERSION_ID'].split('.')[1])/pow(2,28)
            ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp+8*3600))
            html = u'Python Fetch Server %s \u5df2\u7ecf\u5728\u5de5\u4f5c\u4e86\uff0c\u90e8\u7f72\u65f6\u95f4 %s\n' % (__version__, ctime)
            start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
            yield html.encode('utf8')
        raise StopIteration

    # inflate = lambda x:zlib.decompress(x, -15)
    wsgi_input = environ['wsgi.input']
    data = wsgi_input.read(2)
    metadata_length, = struct.unpack('!h', data)
    metadata = wsgi_input.read(metadata_length)

    metadata = zlib.decompress(metadata, -15)
    headers  = dict(x.split(':', 1) for x in metadata.splitlines() if x)
    method   = headers.pop('G-Method')
    url      = headers.pop('G-Url')

    kwargs   = {}
    any(kwargs.__setitem__(x[2:].lower(), headers.pop(x)) for x in headers.keys() if x.startswith('G-'))

    #logging.info('%s "%s %s %s" - -', environ['REMOTE_ADDR'], method, url, 'HTTP/1.1')
    #logging.info('request headers=%s', headers)

    if __password__ and __password__ != kwargs.get('password', ''):
        start_response('403 Forbidden', [('Content-Type', 'text/html')])
        yield error_html('403', 'Wrong password', description='proxy.ini password is wrong!')
        raise StopIteration

    if __hostsdeny__ and urlparse.urlparse(url).netloc.endswith(__hostsdeny__):
        start_response('403 Forbidden', [('Content-Type', 'text/html')])
        yield error_html('403', 'Hosts Deny', description='url=%r' % url)
        raise StopIteration

    fetchmethod = getattr(urlfetch, method, '')
    if not fetchmethod:
        start_response('501 Unsupported', [('Content-Type', 'text/html')])
        yield error_html('501', 'Invalid Method: %r'% method, description='Unsupported Method')
        raise StopIteration

    deadline = Deadline
    validate_certificate = bool(int(kwargs.get('validate', 0)))
    headers = dict(headers)
    headers['Connection'] = 'close'
    payload = environ['wsgi.input'].read() if 'Content-Length' in headers else None
    if 'Content-Encoding' in headers:
        if headers['Content-Encoding'] == 'deflate':
            payload = zlib.decompress(payload, -15)
            headers['Content-Length'] = str(len(payload))
            del headers['Content-Encoding']

    accept_encoding = headers.get('Accept-Encoding', '')

    errors = []
    for i in xrange(int(kwargs.get('fetchmax', FetchMax))):
        try:
            response = urlfetch.fetch(url, payload, fetchmethod, headers, allow_truncated=False, follow_redirects=False, deadline=deadline, validate_certificate=validate_certificate)
            break
        except apiproxy_errors.OverQuotaError as e:
            time.sleep(5)
        except urlfetch.DeadlineExceededError as e:
            errors.append('%r, deadline=%s' % (e, deadline))
            logging.error('DeadlineExceededError(deadline=%s, url=%r)', deadline, url)
            time.sleep(1)
            deadline = Deadline * 2
        except urlfetch.DownloadError as e:
            errors.append('%r, deadline=%s' % (e, deadline))
            logging.error('DownloadError(deadline=%s, url=%r)', deadline, url)
            time.sleep(1)
            deadline = Deadline * 2
        except urlfetch.ResponseTooLargeError as e:
            response = e.response
            logging.error('ResponseTooLargeError(deadline=%s, url=%r) response(%r)', deadline, url, response)
            m = re.search(r'=\s*(\d+)-', headers.get('Range') or headers.get('range') or '')
            if m is None:
                headers['Range'] = 'bytes=0-%d' % int(kwargs.get('fetchmaxsize', FetchMaxSize))
            else:
                headers.pop('Range', '')
                headers.pop('range', '')
                start = int(m.group(1))
                headers['Range'] = 'bytes=%s-%d' % (start, start+int(kwargs.get('fetchmaxsize', FetchMaxSize)))
            deadline = Deadline * 2
        except urlfetch.SSLCertificateError as e:
            errors.append('%r, should validate=0 ?' % e)
            logging.error('%r, deadline=%s', e, deadline)
        except Exception as e:
            errors.append(str(e))
            if i==0 and method=='GET':
                deadline = Deadline * 2
    else:
        start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
        yield error_html('502', 'Python Urlfetch Error: %r' % method, description='<br />\n'.join(errors) or 'UNKOWN')
        raise StopIteration

    #logging.debug('url=%r response.status_code=%r response.headers=%r response.content[:1024]=%r', url, response.status_code, dict(response.headers), response.content[:1024])

    data = response.content
    if 'content-encoding' not in response.headers and len(response.content) < DeflateMaxSize and response.headers.get('content-type', '').startswith(('text/', 'application/json', 'application/javascript')):
        if 'deflate' in accept_encoding:
            response.headers['Content-Encoding'] = 'deflate'
            data = zlib.compress(data)[2:-4]
        elif 'gzip' in accept_encoding:
            response.headers['Content-Encoding'] = 'gzip'
            compressobj = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
            dataio = cStringIO.StringIO()
            dataio.write('\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff')
            dataio.write(compressobj.compress(data))
            dataio.write(compressobj.flush())
            dataio.write(struct.pack('<LL', zlib.crc32(data)&0xFFFFFFFFL, len(data)&0xFFFFFFFFL))
            data = dataio.getvalue()
    response.headers['Content-Length'] = str(len(data))
    response_headers = zlib.compress('\n'.join('%s:%s'%(k.title(),v) for k, v in response.headers.items() if not k.startswith('x-google-')))[2:-4]
    start_response('200 OK', [('Content-Type', 'image/gif')])
    yield struct.pack('!hh', int(response.status_code), len(response_headers))+response_headers
    yield data

app = gae_application if urlfetch else paas_application
application = app if sae is None else sae.create_wsgi_app(app)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - - %(asctime)s %(message)s', datefmt='[%b %d %H:%M:%S]')
    import gevent, gevent.server, gevent.wsgi, gevent.monkey, getopt
    gevent.monkey.patch_all(dns=gevent.version_info[0]>=1)

    options = dict(getopt.getopt(sys.argv[1:], 'l:p:a:')[0])
    host = options.get('-l', '0.0.0.0')
    port = options.get('-p', '80')
    app  = options.get('-a', 'socks5')

    if app == 'socks5':
        server = gevent.server.StreamServer((host, int(port)), socks5_handler)
    else:
        server = gevent.wsgi.WSGIServer((host, int(port)), paas_application)

    logging.info('serving %s at http://%s:%s/', app.upper(), server.address[0], server.address[1])
    server.serve_forever()

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
# coding=utf-8
# Contributor:
#      Phus Lu        <phus.lu@gmail.com>

__version__ = '1.10.1'
__password__ = ''

import sys, os, time, struct, zlib, binascii, logging, httplib, urlparse
try:
    from google.appengine.api import urlfetch
    from google.appengine.runtime import apiproxy_errors, DeadlineExceededError
except ImportError:
    urlfetch = None
try:
    import sae
except ImportError:
    sae = None
try:
    import socket, select, ssl, thread
except:
    socket = None

FetchMax = 2
Deadline = 30

def io_copy(source, dest):
    try:
        io_read  = getattr(source, 'read', None) or getattr(source, 'recv')
        io_write = getattr(dest, 'write', None) or getattr(dest, 'sendall')
        while 1:
            data = io_read(8192)
            if not data:
                break
            io_write(data)
    except Exception as e:
        logging.exception('io_copy(source=%r, dest=%r) error: %s', source, dest, e)
    finally:
        pass

def fileobj_to_generator(fileobj, bufsize=8192, gzipped=False):
    assert hasattr(fileobj, 'read')
    if not gzipped:
        while 1:
            data = fileobj.read(bufsize)
            if not data:
                fileobj.close()
                break
            else:
                yield data
    else:
        compressobj = zlib.compressobj(zlib.Z_BEST_COMPRESSION, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        crc         = zlib.crc32('')
        size        = 0
        yield '\037\213\010\000' '\0\0\0\0' '\002\377'
        while 1:
            data = fileobj.read(bufsize)
            if not data:
                break
            crc = zlib.crc32(data, crc)
            size += len(data)
            zdata = compressobj.compress(data)
            if zdata:
                yield zdata
        zdata = compressobj.flush()
        if zdata:
            yield zdata
        yield struct.pack('<LL', crc&0xFFFFFFFFL, size&0xFFFFFFFFL)

def httplib_request(method, url, body=None, headers={}, timeout=None):
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    HTTPConnection = httplib.HTTPSConnection if scheme == 'https' else httplib.HTTPConnection
    if params:
        path += ';' + params
    if query:
        path += '?' + query
    conn = HTTPConnection(netloc, timeout=timeout)
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    return response

def paas_application(environ, start_response):
    cookie  = environ['HTTP_COOKIE']
    request = decode_data(zlib.decompress(cookie.decode('base64')))

    url     = request['url']
    method  = request['method']

    logging.info('%s "%s %s %s" - -', environ['REMOTE_ADDR'], method, url, 'HTTP/1.1')

    headers = dict((k.title(),v.lstrip()) for k, _, v in (line.partition(':') for line in request['headers'].splitlines()))

    data = environ['wsgi.input'] if int(headers.get('Content-Length',0)) else None

    if method != 'CONNECT':
        try:
            response = httplib_request(method, url, body=data, headers=headers, timeout=16)
            status_line = '%d %s' % (response.status, httplib.responses.get(response.status, 'OK'))

            gzipped = False
##            if response.getheader('content-encoding') != 'gzip' and response.getheader('content-length'):
##                if response.getheader('content-type', '').startswith(('text/', 'application/json', 'application/javascript')):
##                    headers += [('Content-Encoding', 'gzip')]
##                    gzipped = True

            start_response(status_line, response.getheaders())
            return fileobj_to_generator(response, gzipped=gzipped)
        except httplib.HTTPException as e:
            raise

def socket_forward(local, remote, timeout=60, tick=2, bufsize=8192, maxping=None, maxpong=None, idlecall=None):
    timecount = timeout
    try:
        while 1:
            timecount -= tick
            if timecount <= 0:
                break
            (ins, _, errors) = select.select([local, remote], [], [local, remote], tick)
            if errors:
                break
            if ins:
                for sock in ins:
                    data = sock.recv(bufsize)
                    if data:
                        if sock is local:
                            remote.sendall(data)
                            timecount = maxping or timeout
                        else:
                            local.sendall(data)
                            timecount = maxpong or timeout
                    else:
                        return
            else:
                if idlecall:
                    try:
                        idlecall()
                    except Exception:
                        logging.exception('socket_forward idlecall fail')
                    finally:
                        idlecall = None
    except Exception:
        logging.exception('socket_forward error')
        raise
    finally:
        if idlecall:
            idlecall()

def paas_socks5(environ, start_response):
    wsgi_input = environ['wsgi.input']
    sock = None
    rfile = None
    if hasattr(wsgi_input, 'rfile'):
        sock = wsgi_input.rfile._sock
        rfile = wsgi_input.rfile
    elif hasattr(wsgi_input, '_sock'):
        sock = wsgi_input._sock
    elif hasattr(wsgi_input, 'fileno'):
        sock = socket.fromfd(wsgi_input.fileno())
    if not sock:
        raise RuntimeError('cannot extract socket from wsgi_input=%r' % wsgi_input)
    # 1. Version
    if not rfile:
        rfile = sock.makefile('rb', -1)
    data = rfile.read(ord(rfile.read(2)[-1]))
    if __password__:
        if '\x02' in data:
            sock.send(b'\x05\x02') # username/password authentication
            data = rfile.read(2)
            data = rfile.read(ord(data[1])+1)
            data = data[:-1], rfile.read(ord(data[-1]))
        if data != ('', __password__):
            # connection not allowed by ruleset
            return sock.send(b'\x05\x02\x00\x01\x00\x00\x00\x00\x00\x00')
    sock.send(b'\x05\x00')
    # 2. Request
    data = rfile.read(4)
    mode = ord(data[1])
    addrtype = ord(data[3])
    if addrtype == 1:       # IPv4
        addr = socket.inet_ntoa(rfile.read(4))
    elif addrtype == 3:     # Domain name
        addr = rfile.read(ord(sock.recv(1)[0]))
    port = struct.unpack('>H', rfile.read(2))
    reply = b'\x05\x00\x00\x01'
    try:
        logging.info('paas_socks5 mode=%r', mode)
        if mode == 1:  # 1. TCP Connect
            remote = socket.create_connection((addr, port[0]))
            logging.info('TCP Connect to %s:%s', addr, port[0])
            local = remote.getsockname()
            reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
        else:
            reply = b'\x05\x07\x00\x01' # Command not supported
    except socket.error:
        # Connection refused
        reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
    sock.send(reply)
    # 3. Transfering
    if reply[1] == '\x00':  # Success
        if mode == 1:    # 1. Tcp connect
            socket_forward(sock, remote)

def encode_data(dic):
    return '&'.join('%s=%s' % (k, binascii.b2a_hex(v)) for k, v in dic.iteritems() if v)

def decode_data(qs):
    return dict((k,binascii.a2b_hex(v)) for k, _, v in (x.partition('=') for x in qs.split('&')))

def send_response(start_response, status, headers, content, content_type='image/gif'):
    strheaders = encode_data(headers)
    #logging.debug('response status=%s, headers=%s, content length=%d', status, headers, len(content))
    if 'content-encoding' not in headers and headers.get('content-type', '').startswith(('text/', 'application/json', 'application/javascript')):
        data = ['1', zlib.compress('%s%s%s' % (struct.pack('>3I', status, len(strheaders), len(content)), strheaders, content))]
    else:
        data = ['0', struct.pack('>3I', status, len(strheaders), len(content)), strheaders, content]
    start_response('200 OK', [('Content-type', content_type), ('Connection', 'keep-alive')])
    return data

def send_notify(start_response, method, url, status, content):
    logging.warning('%r Failed: url=%r, status=%r', method, url, status)
    content = '<h2>Python Server Fetch Info</h2><hr noshade="noshade"><p>%s %r</p><p>Return Code: %d</p><p>Message: %s</p>' % (method, url, status, content)
    return send_response(start_response, status, {'content-type':'text/html'}, content)

def gae_post(environ, start_response):
    request = decode_data(zlib.decompress(environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))))
    #logging.debug('post() get fetch request %s', request)

    method = request['method']
    url = request['url']
    payload = request['payload']

    if __password__ and __password__ != request.get('password', ''):
        return send_notify(start_response, method, url, 403, 'Wrong password.')

    fetchmethod = getattr(urlfetch, method, '')
    if not fetchmethod:
        return send_notify(start_response, method, url, 501, 'Invalid Method')

    deadline = Deadline

    headers = dict((k.title(),v.lstrip()) for k, _, v in (line.partition(':') for line in request['headers'].splitlines()))
    headers['Connection'] = 'close'

    errors = []
    for i in xrange(FetchMax if 'fetchmax' not in request else int(request['fetchmax'])):
        try:
            response = urlfetch.fetch(url, payload, fetchmethod, headers, False, False, deadline, False)
            break
        except apiproxy_errors.OverQuotaError, e:
            time.sleep(4)
        except DeadlineExceededError, e:
            errors.append(str(e))
            logging.error('DeadlineExceededError(deadline=%s, url=%r)', deadline, url)
            time.sleep(1)
            # deadline = Deadline * 2
        except urlfetch.DownloadError, e:
            errors.append(str(e))
            logging.error('DownloadError(deadline=%s, url=%r)', deadline, url)
            time.sleep(1)
            # deadline = Deadline * 2
        except urlfetch.InvalidURLError, e:
            return send_notify(start_response, method, url, 501, 'Invalid URL: %s' % e)
        except urlfetch.ResponseTooLargeError, e:
            logging.error('ResponseTooLargeError(deadline=%s, url=%r)', deadline, url)
            range = request.pop('range', None)
            if range:
                headers['Range'] = range
            else:
                errors.append(str(e))
                return send_notify(start_response, method, url, 500, 'Python Server: Urlfetch error: %s' % errors)
            # deadline = Deadline * 2
        except Exception, e:
            errors.append(str(e))
            # if i==0 and method=='GET':
                # deadline = Deadline * 2
    else:
        return send_notify(start_response, method, url, 500, 'Python Server: Urlfetch error: %s' % errors)

    return send_response(start_response, response.status_code, response.headers, response.content)

def gae_get(environ, start_response):
    timestamp = long(os.environ['CURRENT_VERSION_ID'].split('.')[1])/pow(2,28)
    ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp+8*3600))
    html = u'Python Fetch Server %s \u5df2\u7ecf\u5728\u5de5\u4f5c\u4e86\uff0c\u90e8\u7f72\u65f6\u95f4 %s\n' % (__version__, ctime)
    start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
    return [html.encode('utf8')]

def app(environ, start_response):
    if urlfetch and environ['REQUEST_METHOD'] == 'POST':
        return gae_post(environ, start_response)
    elif not urlfetch:
        if environ['PATH_INFO'] == '/socks5':
            return paas_socks5(environ, start_response)
        else:
            return paas_application(environ, start_response)
    else:
        return gae_get(environ, start_response)

application = app if sae is None else sae.create_wsgi_app(app)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - - %(asctime)s %(message)s', datefmt='[%b %d %H:%M:%S]')
    import gevent, gevent.pywsgi, gevent.monkey
    gevent.monkey.patch_all(dns=gevent.version_info[0]>=1)
    def read_requestline(self):
        line = self.rfile.readline(8192)
        while line == '\r\n':
            line = self.rfile.readline(8192)
        return line
    gevent.pywsgi.WSGIHandler.read_requestline = read_requestline
    host, _, port = sys.argv[1].rpartition(':') if len(sys.argv) == 2 else ('', ':', 443)
    if '-ssl' in sys.argv[1:]:
        ssl_args = dict(certfile=os.path.splitext(__file__)[0]+'.pem')
    else:
        ssl_args = dict()
    server = gevent.pywsgi.WSGIServer((host, int(port)), application, log=None, **ssl_args)
    server.environ.pop('SERVER_SOFTWARE')
    logging.info('serving %s://%s:%s/wsgi.py', 'https' if ssl_args else 'http', server.address[0] or '0.0.0.0', server.address[1])
    server.serve_forever()

########NEW FILE########
__FILENAME__ = uploader
#!/usr/bin/env python2
import sys, os.path as ospath
dir = ospath.dirname(sys.argv[0])
sys.argv[1:1] = [ospath.join(dir, 'uploader')]
sys.path.insert(0, ospath.abspath(ospath.join(dir, '../local/src.zip')))
del sys, ospath, dir
from proxy import main
main()

########NEW FILE########
