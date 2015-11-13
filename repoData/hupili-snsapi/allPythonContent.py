__FILENAME__ = backup
import sys
from os.path import dirname, abspath
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

from snsapi.snspocket import SNSPocket
sp = SNSPocket()
sp.load_config()
sp.auth()

ml = sp['myrenren'].home_timeline()
for m in ml:
    sp['mysqlite'].update(m)

########NEW FILE########
__FILENAME__ = clock-annotated
# -*- coding: utf-8 -*-

from snsapi.snspocket import SNSPocket
from datetime import datetime
import time

TEXTS = ['凌晨好', '清晨好', '早上好', '下午好', '傍晚好', '晚上好']
#URL = 'https://github.com/hupili/snsapi/tree/master/app/clock'
URL = 'http://t.cn/zj1VSdV'
AD = '10行写个跨平台的钟：%s' % URL

sp = SNSPocket() # SNSPocket 是一个承载各种SNS的容器
sp.load_config() # 如名
sp.auth()        # 批量授权（如果已授权，读取授权信息）

while True:
    h, m = datetime.now().hour, datetime.now().minute                        # 获取当前小时和分钟
    if m == 0:                                                               # 每小时0分钟的时候发状态
        t = '%s -- 0x%X点钟， %s。( %s )' % ('烫' * h, h, TEXTS[h / 4], AD)  # 构造钟的报时文字
        print t
        sp.update(t)                                                         # 发一条新状态
    time.sleep(60)                                                           # 睡一分钟

########NEW FILE########
__FILENAME__ = clock
# -*- coding: utf-8 -*-
'''
clock (SNSAPI Sample Apps)

docstring placeholder
'''

from snsapi.snspocket import SNSPocket
from datetime import datetime
import time

TEXTS = ['凌晨好', '清晨好', '早上好', '下午好', '傍晚好', '晚上好']
#URL = 'https://github.com/hupili/snsapi/tree/master/app/clock'
URL = 'http://t.cn/zj1VSdV'
AD = '10行写个跨平台的钟：%s' % URL

sp = SNSPocket()
sp.load_config()
sp.auth()

while True:
    h, m = datetime.now().hour, datetime.now().minute
    if m == 0:
        t = '%s -- 0x%X点钟， %s。( %s )' % ('烫' * h, h, TEXTS[h / 4], AD)
        print t
        # SNSAPI use unicode internally
        sp.update(t.decode('utf-8'))
    time.sleep(60)

########NEW FILE########
__FILENAME__ = forwarder
# -*- coding: utf-8 -*-
'''
forwarder (SNSAPI Sample Application)

introduction placeholder
'''

import sys
from os.path import dirname, abspath
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))


import time
from os.path import abspath

import snsapi
from snsapi import errors
from snsapi import utils as snsapi_utils
from snsapi.utils import json, obj2str, str2obj
from snsapi.snspocket import SNSPocket
from snsapi.snslog import SNSLog as logger
from snsapi.snstype import Message

class Forwarder(object):
    def __init__(self, fn_channel = "conf/channel.json",
            fn_forwarder = "conf/forwarder.json",
            fn_message = "messages.json"):
        super(Forwarder, self).__init__()

        self.fn_channel = fn_channel
        self.fn_forwarder = fn_forwarder
        self.fn_message = fn_message
        self.load_config(fn_channel, fn_forwarder)
        self.db_init()

    def db_init(self):
        try:
            self.messages = json.load(open(self.fn_message))
        except IOError, e:
            if e.errno == 2: #no such file
                self.messages = {}
            else:
                raise e

    def db_save(self):
        from snsapi.utils import JsonDict
        dct = JsonDict(self.messages)
        open(self.fn_message,'w').write(dct._dumps_pretty())

    def db_add(self, msg):
        '''
        msg: the snsapi.Message object
        '''
        sig = msg.digest()
        if sig in self.messages:
            logger.debug("One duplicate message: %s", sig)
        else:
            logger.debug("New message: %s", str(msg))
            self.messages[sig] = {
                'sig': sig,
                'time': msg.parsed.time,
                'username': msg.parsed.username,
                'text': msg.parsed.text,
                'success': {"__null": "yes"},
                'obj': obj2str(msg)
            }

    def db_get_message(self):
        '''
        Pick one message that is not forwarded (successfully). Returen a
        list of <channel_name, msg> pairs. If the intended out channel is
        limited in quota, we do not append it.
        '''
        ret = []
        for (sig, msg) in self.messages.iteritems():
            for (cn, quota)  in self.jsonconf['quota'].iteritems():
                if cn in self.messages[sig]['success'] and self.messages[sig]['success'][cn] == "yes":
                    pass
                else:
                    if quota > 0:
                        self.jsonconf['quota'][cn] -= 1
                        ret.append((cn, msg))
        return ret

    def _copy_channels(self, src, dst, names):
        for cn in names:
            if src.get(cn, None):
                dst[cn] = src[cn]

    def _set_default_quota(self):
        if not 'quota' in self.jsonconf:
            self.jsonconf['quota'] = {}
        for cn in self.sp_out:
            if not cn in self.jsonconf['quota']:
                self.jsonconf['quota'][cn] = 1

    def load_config(self, fn_channel, fn_forwarder):
        self.sp_all = SNSPocket()
        self.sp_all.load_config(fn_channel)
        self.sp_in = SNSPocket()
        self.sp_out = SNSPocket()
        try:
            self.jsonconf = json.load(open(fn_forwarder))
            self._copy_channels(self.sp_all, self.sp_in, self.jsonconf['channel_in'])
            self._copy_channels(self.sp_all, self.sp_out, self.jsonconf['channel_out'])
            self._set_default_quota()
        except IOError, e:
            logger.warning("Load '%s' failed, use default: no in_channel and out_channel", fn_forwarder)
            # Another possible handle of this error instead of default
            #raise errors.NoConfigFile
        logger.info("SNSPocket for all: %s", self.sp_all)
        logger.info("SNSPocket for in channel: %s", self.sp_in)
        logger.info("SNSPocket for out channel: %s", self.sp_out)

    def auth(self, *args, **kargs):
        return self.sp_all.auth(*args, **kargs)

    def home_timeline(self, *args, **kargs):
        return self.sp_in.home_timeline(*args, **kargs)

    def update(self, *args, **kargs):
        return self.sp_out.update(*args, **kargs)

    def format_msg(self, msg):
        return "%s (fwd from: %s)"  % (msg['text'], msg['username'])
        #return "%s (fwd from: %s at %s)"  % (msg['text'], msg['username'], snsapi_utils.utc2str(msg['time']), )
        #return "[%s] at %s \n %s (fwd at:%s)"  % (msg['username'], msg['time'], msg['text'], time.time())

    def forward(self, forward_predicate):
        sl = self.home_timeline()
        if forward_predicate:
            sl = filter(forward_predicate, sl)
        for s in sl:
            self.db_add(s)
        for (cn, msg) in self.db_get_message():
            text = self.format_msg(msg)
            #r = self.sp_out[cn].update(text)
            r = self.sp_out[cn].forward(str2obj(msg['obj']), u'')
            msg['success'][cn] = "yes" if r else "no"
            logger.info("forward '%s' -- %s", text, r)

def sample_forward_predicate(m):
    '''
    Forward predicate.
    Return True or False whether to forward this message.

    :param m:
        A ``Message`` object.
        See the doc of ``snsapi.snstype`` for useful fields.
    '''
    return m.parsed.username==u"hpl"

if __name__ == "__main__":
    import time

    try:
        from strategy import forward_predicate
        logger.info("Use customized strategy")
    except:
        logger.info("Do not find customized strategy. Use default")
        forward_predicate = sample_forward_predicate

    while True:
        logger.info("Start forward")
        try:
            fwd = Forwarder()
            fwd.auth()
            fwd.forward(forward_predicate=forward_predicate)
            fwd.db_save()
            del fwd
        except Exception as e:
            logger.warning('Catch exception: %s', e)
        logger.info("End forward. Sleep 300 sconds for next round.")
        time.sleep(300)

########NEW FILE########
__FILENAME__ = forwarder
# -*- coding: utf-8 -*-

import time
import hashlib
import snsapi
from snsapi import errors
try:
    import json
except ImportError:
    import simplejson as json
from os.path import abspath
import sys

def channel_init(fn_channel):
    fname = abspath(fn_channel)
    channels = {}
    try:
        with open(fname, "r") as fp:
            allinfo = json.load(fp)
            for site in allinfo:
                print "=== channel:%s;open:%s;platform:%s" % \
                        (site['channel_name'],site['open'],site['platform'])
                if site['open'] == "yes" :
                    #TODO: the following code seems clumsy
                    #any way to simplify it?
                    #e.g. use the string name to the the corresponding class directly
                    if site['platform'] == "sina" :
                        #clis.append(snsapi.sina.SinaAPI(site))
                        channels[site['channel_name']] = snsapi.sina.SinaAPI(site)
                    elif site['platform'] == "rss":
                        #clis.append(snsapi.rss.RSSAPI(site))
                        channels[site['channel_name']] = snsapi.rss.RSSAPI(site)
                    elif site['platform'] == "qq":
                        #clis.append(snsapi.qq.QQAPI(site))
                        channels[site['channel_name']] = snsapi.qq.QQAPI(site)
                    else:
                        raise errors.NoSuchPlatform
            return channels
    except IOError:
        raise errors.NoConfigFile


if __name__ == "__main__":

    channels = channel_init('conf/channel.json') ;
    #authenticate all channels
    for cname in channels:
        channels[cname].auth()

    fp = open(abspath('conf/forwarder.json'), "r")
    fconf = json.load(fp)
    channel_in = fconf['channel_in']
    channel_out = fconf['channel_out']
    print "channel_in ===== "
    for c in channel_in :
        print c
    print "channel_out ===== "
    for c in channel_out :
        print c

    try:
        messages = json.load(open('messages.json'))
    except IOError, e:
        if e.errno == 2: #no such file
            messages = {}
        else:
            raise e

    #load message information and check in channels.
    #merge new messages into local storage
    #messages = json.load(open(abspath('messages.json'),'r'))
    for cin_name in channel_in :
        print "==== Reading channel: %s" % (cin_name)
        cin_obj = channels[cin_name]
        #TODO: make it configurable for each channel
        sl = cin_obj.home_timeline(2)
        for s in sl:
            #s.show()
            #print type(s.created_at)
            #print type(s.username)
            #print type(s.text)
            msg_full = unicode(s.created_at) + unicode(s.username) + unicode(s.text)
            sig = hashlib.sha1(msg_full.encode('utf-8')).hexdigest()
            #sig = hashlib.sha1(msg_full).hexdigest() # <-- this line will raise an error
            if sig in messages:
                print "One duplicate message:%s" % (sig)
            else:
                print ">>>New message"
                s.show()
                messages[sig] = {
                    'sig': sig,
                    'created_at': s.created_at,
                    'username': s.username,
                    'text': s.text,
                    'success':{"__null":"yes"}
                }
                #The message is new
                #forward it to all output channels

    #set quota/run for each out_channel
    #TODO: make it configurable
    quota = {}
    for c in channel_out :
        quota[c] = 1

    #forward non-successful messages to all out_channels
    for m in messages :
        #break
        for cout_name in quota :
            if cout_name in messages[m]['success'] and messages[m]['success'][cout_name] == "yes":
                pass
            else:
                if quota[cout_name] > 0:
                    quota[cout_name] -= 1
                    cout_obj = channels[cout_name]
                    #text = "[%s] at %s \n %s"  % (s.username, s.created_at, s.text)
                    #text = "[%s] at %s \n %s (forward time:%s)"  % (s.username, s.created_at, s.text, time.time())
                    s = messages[m]
                    print "forwarding %s to %s" % (m, cout_name)
                    text = "[%s] at %s \n %s (forward time:%s)"  % (s['username'], s['created_at'], s['text'], time.time())
                    print "Text: %s" % (text)
                    #TODO: check the real cause of the problem.
                    #      It is aleady announec in the front of this file
                    #      that all strings should be treated as UTF-8 encoding.
                    #      Why do the following problem happen?
                    if ( cout_obj.update(text.encode('utf-8')) ):
                        messages[m]['success'][cout_name] = "yes"
                        print "Forward success: %s" % (sig)
                    else:
                        messages[m]['success'][cout_name] = "no"
                        print "Forward fail: %s" % (sig)

    print "forwarding done!"
    #print messages

    json.dump(messages, open('messages.json','w'))
    #json.dumps({'1':2,3:4})
    sys.exit()


########NEW FILE########
__FILENAME__ = test_read_all
# -*- coding: utf-8 -*-
'''
Read timeline from all configured channels

docstring placeholder
'''

from snsapi.snspocket import SNSPocket
from snsapi.utils import console_input,console_output

if __name__ == "__main__":
    sp = SNSPocket()
    sp.load_config()

    sp.auth()

    sl = sp.home_timeline()

    print sl

########NEW FILE########
__FILENAME__ = test_read_reply
# -*- coding: utf-8 -*-
'''
Read timeline from all configured channels and reply one

docstring placeholder
'''

from snsapi.snspocket import SNSPocket
from snsapi.utils import console_input,console_output

if __name__ == "__main__":
    '''
    QQ weibo may fail sometimes, even with same input. May be the invoking frequency limit.
    Sina weibo is better, and more stable.
    '''

    sp = SNSPocket()
    sp.load_config()

    sp.auth()

    status_list = sp.home_timeline()

    print "==== read messages from all channels ===="

    no = 0
    for s in status_list:
        print "--No. %d --" % no
        s.show()
        no = no + 1

    print "==== try to reply one ===="

    print "Input the no:"
    no = int(console_input())
    print "Input the text:"
    text = console_input()

    sID = status_list[no].ID
    print sp.reply(sID, text)


########NEW FILE########
__FILENAME__ = test_write_all
# -*- coding: utf-8 -*-
'''
Update status on all channels

docstring placeholder
'''

from snsapi.snspocket import SNSPocket
from snsapi.utils import console_input,console_output

if __name__ == "__main__":
    '''
    QQ weibo may fail sometimes, even with same input. May be the invoking frequency limit.
    Sina weibo is better, and more stable.
    '''

    sp = SNSPocket()
    sp.load_config()

    sp.auth()

    for cname in sp:
        print "listen first___________________________%s" % cname
        sl = sp.home_timeline(channel = cname)
        print sl

        print "update status__________________________%s" % cname
        print "Input text:"
        text = raw_input()
        ret = sp.update(text, channel = cname)
        print ret

########NEW FILE########
__FILENAME__ = mysofa
# -*- coding: utf-8 -*-
'''
mysofa (SNSAPI Sample Application)

introduction placeholder

**Warning: The code is under reconstruction using new SNSAPI interface.
Do not use this app until it is done.**
'''

#from snsapi.plugin.renren import RenrenAPI
import json
import hashlib
import time

MYSOFAR_REPLY_STRING = "(微笑)"
MYSOFAR_REPLY_GAP = 10 # seconds, 10 seems the minimum
MYSOFAR_NEWS_QUERY_COUNT = 1

def can_reply(status):
    """
    A filter function of the status you want to reply
    """
    if status.username.count('hpl'):
        return True
    else:
        return False

def main():
    """docstring for main"""

    #load channel configurations
    channels = json.load(open('conf/channel.json'))

    #find one renren account
    rr = None
    for c in channels:
        if c['platform'] == "renren":
            rr = RenrenAPI(c)

    if rr is None:
        print "cannot find one renren platform in channel.json"
        return
    else:
        rr.auth()

    #load record to avoid repeated reply
    try:
        sIDs = json.load(open('statusID.json'))
    except IOError, e:
        if e.errno == 2: #no such file
            sIDs = {}
        else:
            raise e

    status_list = rr.home_timeline(MYSOFAR_NEWS_QUERY_COUNT)
    for s in status_list:
        s.show()
        msg_string = "".join( unicode(x) for x in \
                [s.created_at, s.username, s.text, \
                s.ID.platform, s.ID.status_id, s.ID.source_user_id])
        sig = hashlib.sha1(msg_string.encode('utf-8')).hexdigest()
        if not sig in sIDs and can_reply(s):
            print '[reply it]'
            ret = rr.reply(s.ID, MYSOFAR_REPLY_STRING)
            print "[ret: %s]" % ret
            print "[wait for %d seconds]" % MYSOFAR_REPLY_GAP
            time.sleep(MYSOFAR_REPLY_GAP)
            if ret:
                sIDs[sig] = msg_string
        else:
            print '[no reply]'

    #save reply record
    json.dump(sIDs, open('statusID.json', 'w'))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = myword
# -*- coding: utf-8 -*-
'''
myword

'''

#from snsapi.plugin.renren import RenrenAPI
from snsapi.snspocket import SNSPocket
import json
import sys
import urllib2
import hashlib
import time

REPLY_GAP = 10 # seconds, 10 seems the minimum
NEWS_QUERY_COUNT = 5
MY_NAME = "hsama2012"

def can_reply(status):
    """
    A filter function of the status you want to reply
    """
    if not status.parsed.text.find("@" + MY_NAME) == -1:
        return True
    else:
        return False


def get_word(text):
    """
    To the get word in a message
    """
    text = text.replace("@" + MY_NAME +" ","")
    return text


def translate(word):
    """
    Translate a word with dic.zhan-dui.com
    """
    url = "http://dic.zhan-dui.com/api.php?s=" + word + "&type=json"
    req = urllib2.Request(url, data='')
    req.add_header('User_Agent', 'toolbar')
    results = json.load(urllib2.urlopen(req))
    if "error_code" in results:
        return word +" " + " not found"
    else:
        mean = ""
        for c in results["simple_dic"]:
            mean = mean + c
        return word + " " + mean




def main():
    """docstring for main"""
    #set system default encoding to utf-8 to avoid encoding problems
    reload(sys)
    sys.setdefaultencoding( "utf-8" )

    #load channel configurations
    channels = json.load(open('conf/channel.json'))



    #find one account
    rr = SNSPocket()
    for c in channels:
        rr.add_channel(c)

    if rr is None:
        print "cannot find one renren platform in channel.json"
        return
    else:
        rr.load_config()
        rr.auth()


    #load record to avoid repeated reply
    try:
        sIDs = json.load(open('statusID.json'))
    except IOError, e:
        if e.errno == 2: #no such file
            sIDs = {}
        else:
            raise e

    status_list = rr.home_timeline(NEWS_QUERY_COUNT)
    for s in status_list:
        s.show()
        msg_string = "".join( unicode(x) for x in \
                [s.parsed.time, s.ID, s.parsed.username, \
                s.parsed.userid, s.parsed.text])
        sig = hashlib.sha1(msg_string.encode('utf-8')).hexdigest()
        if not sig in sIDs and can_reply(s):
            print '[reply it]'
            REPLY_STRING = translate(get_word(s.parsed.text))
            ret = rr.reply(s.ID, REPLY_STRING.decode('utf-8'))
            print "[ret: %s]" % ret
            print "[wait for %d seconds]" % REPLY_GAP
            time.sleep(REPLY_GAP)
            if ret:
                sIDs[sig] = msg_string
        else:
            print '[no reply]'

    #save reply record
    json.dump(sIDs, open('statusID.json', 'w'))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = google-reader2snsapi
# -*- coding: utf-8 -*-
#
# Convert Google Reader subscription.xml to SNSAPI's channel.json
# You can download your subscription data from Google Takeout:
#
#    * https://www.google.com/takeout
#

from lxml import etree
import json

def gr2snsapi(gr_str):
    root = etree.XML(gr_str)
    ret = []
    num = 0
    for e in root.iter('outline'):
        num += 1
        if e.get('type', None):
            ret.append({
                'platform': 'RSS',
                'open': 'yes',
                'url': e.get('xmlUrl'),
                'channel_name': 'ch%d. %s' % (num, e.get('title')),
                '__other__info': {
                    'html_url': e.get('htmlUrl'),
                    'text': e.get('text')
                    }
                })
    return json.dumps(ret, indent=2)

def main(i, o):
    f_in = open(i, 'r') if isinstance(i, str) else i
    f_out = open(o, 'w') if isinstance(o, str) else o
    f_out.write(gr2snsapi(f_in.read()))
    f_in.close()
    f_out.close()

if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Convert Google Reader subscription.xml to SNSAPI's channel.json")
    parser.add_argument('-i', metavar='INPUT', type=str,
            help='filename of input (e.g. subscription.xml)',
            default=sys.stdin)
    parser.add_argument('-o', metavar='OUTPUT', type=str,
            help='filename of output (e.g. channel.json)',
            default=sys.stdout)
    args = parser.parse_args()

    main(**vars(args))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# SNSAPI documentation build configuration file, created by
# sphinx-quickstart on Wed Aug 29 11:28:07 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'SNSAPI'
copyright = u'Unlicensed'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7.1'
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'SNSAPIdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'SNSAPI.tex', u'SNSAPI Documentation',
   u'uxian, hupili', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'snsapi', u'SNSAPI Documentation',
     [u'uxian, hupili'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'SNSAPI', u'SNSAPI Documentation',
   u'uxian, hupili', 'SNSAPI', 'Bridge everything that is "social"',
   'Social Networking'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = async
# coding: utf-8

import types
import time
import threading
from snslog import SNSLog as logger


class AsynchronousThreading(threading.Thread):
    def __init__(self, func, callback=None, args=(), kwargs={}, daemon=False):
        super(AsynchronousThreading, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.daemon = daemon

    def run(self):
        ret = self.func(*self.args, **self.kwargs)
        if self.callback:
            self.callback(ret)


class AsynchronousWithCallBack:
    def __init__(self, instance):
        self._p = instance
        for i in filter(lambda t: type(getattr(self._p, t)) == types.MethodType, dir(self._p)):
            setattr(self, i, self._call_(getattr(self._p, i)))

    def _call_(self, target):
        def func(callback=None, *args, **kwargs):
            AsynchronousThreading(target, callback, args, kwargs).start()
        return func

class AsyncDaemonWithCallBack:
    def __init__(self, target, args, kwargs, callback, sleepsec):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.sleepsec = sleepsec

    def start(self):
        self.started = True
        self._start()

    def _start(self):
        AsynchronousThreading(self.target, self.callback_and_sleep, self.args, self.kwargs, daemon=True).start()

    def stop(self):
        self.started = False

    def callback_and_sleep(self, value):
        if self.callback:
            try:
                self.callback(value)
            except Exception as e:
                logger.warning("Error while executing callback %s" % (str(e)))
        if self.started:
            for i in range(self.sleepsec):
                time.sleep(1)
                if not self.started:
                    break
            if self.started:
                self._start()

########NEW FILE########
__FILENAME__ = errors
#-*- encoding: utf-8 -*-

'''
Errors or Exceptions for SNSAPI

How to add an error type?

   * Check out ``Mark1`` (in ``errors.py``).
     Inherit your error type from a right class.
     The ``#>>`` comment denotes the level an error type is in.
   * Check out ``Makr2`` (in ``errors.py``).
     Add your new error type to the corresponding tree.

How to reference an error type?

   * By convention, others should only import "snserror".
     e.g. ``from errors import snserror``, or
     ``from snsapi import snserror``.
   * Use dot expression to enter the exact type.
     e.g. ``snserror.config.nofile``.

'''


# =============== Error Type ==============

# Mark1

#>
class SNSError(Exception):
    def __str__(self):
        return "SNSError!"

#>>
class ConfigError(SNSError):
    def __str__(self):
        return "SNS configuration error!"

#>>>
class NoConfigFile(ConfigError):
    def __init__(self, fname="conf/channel.json"):
        self.fname = fname
    def __str__(self):
        return self.fname + " NOT EXISTS!"

#>>>
class NoPlatformInfo(ConfigError):
    def __str__(self):
        return "No platform info found in snsapi/plugin/conf/config.json. \
        self.platform and platform in snsapi/plugin/conf/config.json must match."

#>>>
class MissAPPInfo(ConfigError):
    def __str__(self):
        return "Please config the file snsapi/plugin/conf/config.json. \
        You may forget to add your app_key and app_secret into it"

#>>>
class NoSuchPlatform(ConfigError):
    def __str__(self):
        return "No Such Platform. Please check your 'channel.json'."

#>>>
class NoSuchChannel(ConfigError):
    def __str__(self):
        return "No Such Channel. Please check your 'channel.json'. Or do you forget to set snsapi.channel_name before calling read_config()?"

#>>
class SNSTypeWrongInput(SNSError):
    def __init__(self, value=""):
        self.value = value
    def __str__(self):
        return "Wrong input for snsType initializing! It must be a dict\n"+str(self.value)

#>>
class SNSTypeError(SNSError):
    def __init__(self, value=""):
        self.value = value
    def __str__(self):
        return "errors when when dealing snsType." + self.value

#>>>
class SNSTypeParseError(SNSError):
    def __init__(self, value=""):
        self.value = value
    def __str__(self):
        return "errors when parsing JsonObject for snsType: " + self.value

#>>
class SNSEncodingError(SNSError):
    def __init__(self):
        super(SNSEncodingError, self).__init__()
    def __str__(self):
        return "Do not evaluate our interface objects using str(). " \
                "Internal data structure of the entire project is " \
                "unicode. For text exchange with other parties, we " \
                "stick to utf-8"

#>>
class SNSAuthFail(SNSError):
    def __str__(self):
        return "Authentication Failed!"

#>>>
class SNSAuthFechCodeError(SNSAuthFail):
    def __str__(self):
        return "Fetch Code Error!"

#>>
class SNSOperation(SNSError):
    def __str__(self):
        return "SNS Operation Failed"

#>>>
class SNSWriteFail(SNSOperation):
    def __init__(self, value):
        super(SNSWriteFail, self).__init__()
        self.value = value
    def __str__(self):
        return "This channel is non-writable: %s" % self.value

#>>>
class SNSReadFail(SNSOperation):
    def __str__(self):
        return "This channel is non-readable"

#>>
class SNSPocketError(SNSError):
    def __init__(self):
        super(SNSPocketError, self).__init__()
    def __str__(self):
        return "SNSPocket Error!"

#>>>
class SNSPocketSaveConfigError(SNSPocketError):
    def __init__(self):
        super(SNSPocketSaveConfigError, self).__init__()
    def __str__(self):
        return "SNSPocket Save Config Error!"

#>>>
class SNSPocketLoadConfigError(SNSPocketError):
    def __init__(self, msg = ""):
        super(SNSPocketLoadConfigError, self).__init__()
        self.msg = msg
    def __str__(self):
        return "SNSPocket Load Config Error! %s" % self.msg

#>>
class SNSPocketDuplicateName(SNSError):
    def __init__(self, cname):
        super(SNSPocketDuplicateName, self).__init__()
        self.channel_name = cname
    def __str__(self):
        return "Encounter a duplicate channel name!"

# ========= Error Tree ==================

# Mark2

class snserror(object):
    config = ConfigError
    config.nofile = NoConfigFile
    config.save = SNSPocketSaveConfigError
    config.load = SNSPocketLoadConfigError

    type = SNSTypeError
    type.parse = SNSTypeParseError

    op = SNSOperation
    op.read = SNSReadFail
    op.write = SNSWriteFail

    auth = SNSAuthFail
    auth.fetchcode = SNSAuthFechCodeError

########NEW FILE########
__FILENAME__ = platform
# -*- coding: utf-8 -*-

'''
Platforms.

Upper layer can reference platforms from this module
'''

from plugin import *

# Comment/uncomment the following line to
# disable/enable trial plugins
from plugin_trial import *

import sys
import types
platform_list = []
__thismodule = sys.modules[__name__]
for n in dir():
    # do not include built-in names
    if n.find("__") == -1 and n.find("platform_list") == -1:
        # do not include module names
        if not type(getattr(__thismodule,n)) == types.ModuleType:
            platform_list.append(n)

#print platform_list

########NEW FILE########
__FILENAME__ = rss
#-*- encoding: utf-8 -*-

'''
RSS Feed

Contains:
   * RSS Read-only feed platform.
   * RSS Read/Write platform.
   * RSS Summary platform.

'''


from ..snslog import SNSLog as logger
from ..snsbase import SNSBase
from .. import snstype
from ..third import feedparser
import datetime
from ..third import PyRSS2Gen
from ..errors import snserror
from .. import utils

logger.debug("%s plugged!", __file__)

class RSSMessage(snstype.Message):
    platform = "RSS"

    def parse(self):
        self.ID.platform = self.platform

        self.parsed.username = self.raw.get('author', self.ID.channel)
        #TODO:
        #    According to the notion of ID, it should identify
        #    a single user in a cross platform fashion. From the
        #    message, we know platform is RSS. However, author
        #    name is not enough. Suppose all feeds do their due
        #    dilligence to make 'author' identifiable, we can
        #    use 'url' (of RSS feed) + 'author' to identify a
        #    single user of RSS platform. This requires some
        #    framework change in SNSAPI, allowing putting this
        #    prefix information to Message class (not Message
        #    instance).
        self.parsed.userid = self.parsed.username
        self.parsed.time = utils.str2utc(self.raw.get(['updated', 'published']),
                self.conf.get('timezone_correction', None))

        self.parsed.title = self.raw.get('title')
        self.parsed.link = self.raw.get('link')

        self.ID.link = self.parsed.link

        try:
            _body = '\n'.join(map(lambda x: x['value'], self.raw['content']))
        except Exception:
            _body = None
        self.parsed.body = _body

        self.parsed.description = self.raw.get('summary', None)

        # Other plugins' statuses have 'text' field
        # The RSS channel is supposed to read contents from
        # different places with different formats.
        # The entries are usually page update notifications.
        # We format them in a unified way and use this as 'text'.
        self.parsed.text = '"%s" ( %s )' % (self.parsed.title, self.parsed.link)

    def dump_full(self):
        '''
        Override ``Message.dump_full`` because default ``.raw``
        attribute of RSSMessage object is not JSON serializable.

        Note: dumpped messages are meant for the consumption of other
        languages. We do not concern how to convert back. If you do
        that, make sure call ``str2obj`` on ``.raw`` yourself. Besides,
        make sure the source of the string is trustful.

        For the use in Python, directly serialize the message for
        persistent storage. Do not recommend you use any of the three
        level of ``dump_xxx`` functions. Use of ``digest_xxx`` is OK.
        '''
        _raw = self.raw
        self.raw = utils.obj2str(self.raw)
        _str = self._dumps()
        self.raw = _raw
        return _str

class RSS(SNSBase):
    '''
    Supported Methods
        * auth() :
            a NULL stub.
        * home_timeline() :
            read and parse RSS feed.
            pretend it to be a 'special' SNS platform,
            where you can only read your wall but can
            not write to it.
    '''

    Message = RSSMessage

    def __init__(self, channel = None):
        super(RSS, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)
        c['platform'] = 'RSS'
        c['url'] = 'https://github.com/hupili/snsapi/commits/master.atom'

        if full:
            c['message'] = {'timezone_correction': None}

        return c

    def read_channel(self, channel):
        super(RSS, self).read_channel(channel)

    def auth(self):
        logger.info("%s platform do not need auth!", self.platform)

    def auth_first(self):
        logger.info("%s platform do not need auth_first!", self.platform)

    def auth_second(self):
        logger.info("%s platform do not need auth_second!", self.platform)

    def home_timeline(self, count=20):
        '''Get home timeline

           * function : get statuses of yours and your friends'
           * parameter count: number of statuses
        '''

        d = feedparser.parse(self.jsonconf.url)
        conf = self.jsonconf.get('message', {})

        statuslist = snstype.MessageList()
        for j in d['items']:
            if len(statuslist) >= count:
                break
            s = self.Message(j,
                    platform=self.jsonconf['platform'],
                    channel=self.jsonconf['channel_name'],
                    conf=conf)
            #TODO:
            #     RSS parsed result is not json serializable.
            #     Try to find other ways of serialization.
            statuslist.append(s)
        return statuslist

    def expire_after(self, token = None):
        # This platform does not have token expire issue.
        return -1

class RSS2RWMessage(RSSMessage):
    platform = "RSS2RW"
    def parse(self):
        super(RSS2RWMessage, self).parse()
        self.ID.platform = self.platform

        # RSS2RW channel is intended for snsapi-standardized communication.
        # It does not have to digest RSS entry as is in RSSStatus.
        # The 'title' field is the place where we put our messages.
        self.parsed.text = self.parsed.title

class RSS2RW(RSS):
    '''
    Read/Write Channel for rss2

    '''

    Message = RSS2RWMessage

    def __init__(self, channel = None):
        super(RSS2RW, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        c = RSS.new_channel(full)
        c['platform'] = 'RSS2RW'
        if full:
            c['author'] = 'snsapi'
            c['entry_timeout'] = 3600

        return c

    def read_channel(self, channel):
        super(RSS2RW, self).read_channel(channel)

        if not 'author' in self.jsonconf:
            self.jsonconf['author'] = 'snsapi'
        if not 'entry_timeout' in self.jsonconf:
            # Default entry timeout in seconds (1 hour)
            self.jsonconf['entry_timeout'] = 3600

    def update(self, message):
        '''
        :type message: ``Message`` or ``str``
        :param message:
            For ``Message`` update it directly. RSS2RW guarantee the
            message can be read back with the same values in standard
            fields of ``Message.parsed``.
            For ``str``, we compose the virtual ``Message`` first
            using current time and configured author information.
        '''
        try:
            if isinstance(message, snstype.Message):
                msg = message
            else:
                # 'str' or 'unicode'
                msg = snstype.Message()
                msg.parsed.text = message
                msg.parsed.username = self.jsonconf.author
                msg.parsed.userid = self.jsonconf.author
                msg.parsed.time = self.time()
            return self._update(msg)
        except Exception as e:
            logger.warning("Update fail: %s", str(e))
            return False

    def _make_link(self, msg):
        '''
        Make a URL for current ``Message``.

        Note that ``Message.link`` is not mandotary field in SNSApi.
        However, some RSS readers do not accept items with no links.
        Some other readers perform deduplication based on links.
        Towards this end, we use this function to generate unique links
        for each message.
        '''
        _link = msg.parsed.get('link', 'http://goo.gl/7aokV')
        # No link or the link is our official stub
        if _link is None or _link.find('http://goo.gl/7aokV') != -1:
            _link = 'http://goo.gl/7aokV#' + msg.digest()
        return _link

    def _update(self, message):
        '''
        Update the RSS2 feeds.
        This is the raw update method.
        The file pointed to by self.jsonconf.url should be writable.
        Remember to set 'author' and 'entry_timeout' in configurations.
        Or the default values are used.

           * parameter text: messages to update in a feeds
        '''

        _entry_timeout = self.jsonconf.entry_timeout
        cur_time = self.time()

        items = []

        # Read and filter existing entries.
        # Old entries are disgarded to keep the file short and clean.
        try:
            d = feedparser.parse(self.jsonconf.url)
            for j in d['items']:
                try:
                    s = self.Message(j)
                    entry_time = s.parsed.time
                    if _entry_timeout is None or cur_time - entry_time < _entry_timeout:
                        items.append(
                            PyRSS2Gen.RSSItem(
                                author = s.parsed.username,
                                title = s.parsed.title,
                                description = "snsapi RSS2RW update",
                                link = self._make_link(s),
                                pubDate = utils.utc2str(entry_time)
                                )
                            )
                except Exception as e:
                    logger.warning("can not parse RSS entry: %s", e)
        except Exception as e:
            logger.warning("Can not parse '%s', no such file? Error: %s", self.jsonconf.url, e)

        if _entry_timeout is None or cur_time - message.parsed.time < _entry_timeout:
            items.insert(0,
                PyRSS2Gen.RSSItem(
                    author = message.parsed.username,
                    title = message.parsed.text,
                    description = "snsapi RSS2RW update",
                    link = self._make_link(message),
                    pubDate = utils.utc2str(message.parsed.time)
                    )
                )

        rss = PyRSS2Gen.RSS2(
            title = "snsapi, RSS2 R/W Channel",
            link = "https://github.com/hupili/snsapi",
            description = "RSS2 R/W channel based on feedparser and PyRSS2Gen",
            lastBuildDate = datetime.datetime.now(),
            items = items
            )

        try:
            rss.write_xml(open(self.jsonconf.url, "w"))
        except Exception as e:
            raise snserror.op.write(str(e))

        return True

class RSSSummaryMessage(RSSMessage):
    platform = "RSSSummary"
    def parse(self):
        super(RSSSummaryMessage, self).parse()
        self.ID.platform = self.platform

        # The format of feedparser's returning object
        #
        #    * o['summary'] : the summary
        #    * o['content'] : an array of contents.
        #      Each element is a dict. and the 'value' field is the text (maybe in HTML).

        _summary = None
        if self.parsed.body != None:
            _summary = self.parsed.body
        elif self.parsed.description != None:
            _summary = self.parsed.description
        if _summary:
            _summary = utils.strip_html(_summary).replace('\n', '')
        else:
            _summary = ""
        self.parsed.text = '"%s" ( %s ) %s' % (self.parsed.title, self.parsed.link, _summary)

class RSSSummary(RSS):
    '''
    Summary Channel for RSS

    It provides more meaningful 'text' field.

    '''

    Message = RSSSummaryMessage

    def __init__(self, channel = None):
        super(RSSSummary, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        c = RSS.new_channel(full)
        c['platform'] = 'RSSSummary'
        return c

########NEW FILE########
__FILENAME__ = sina
#-*- encoding: utf-8 -*-

'''
Sina Weibo client
'''

if __name__ == '__main__':
    import sys
    sys.path.append('..')
    from snslog import SNSLog as logger
    from snsbase import SNSBase, require_authed
    import snstype
    import utils
else:
    from ..snslog import SNSLog as logger
    from ..snsbase import SNSBase, require_authed
    from .. import snstype
    from .. import utils

logger.debug("%s plugged!", __file__)

class SinaWeiboBase(SNSBase):

    def __init__(self, channel = None):
        super(SinaWeiboBase, self).__init__(channel)

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['app_key'] = ''
        c['app_secret'] = ''
        c['platform'] = 'SinaWeiboStatus'
        c['auth_info'] = {
                "save_token_file": "(default)",
                "cmd_request_url": "(default)",
                "callback_url": "http://snsapi.sinaapp.com/auth.php",
                "cmd_fetch_code": "(default)"
                }

        return c

    def read_channel(self, channel):
        super(SinaWeiboBase, self).read_channel(channel)

        if not "auth_url" in self.auth_info:
            self.auth_info.auth_url = "https://api.weibo.com/oauth2/"
        if not "callback_url" in self.auth_info:
            self.auth_info.callback_url = "http://snsapi.sinaapp.com/auth.php"

        # According to our test, it is 142 unicode character
        # We also use 140 by convention
        self.jsonconf['text_length_limit'] = 140

        #if not 'platform_prefix' in self.jsonconf:
        #    self.jsonconf['platform_prefix'] = u'新浪'

    def need_auth(self):
        return True

    def auth_first(self):
        self._oauth2_first()

    def auth_second(self):
        try:
            self._oauth2_second()
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def _fetch_code_local_username_password(self):
        try:
            login_username = self.auth_info.login_username
            login_password = self.auth_info.login_password
            app_key = self.jsonconf.app_key
            app_secret = self.jsonconf.app_secret
            callback_url = self.auth_info.callback_url

            referer_url = self._last_requested_url

            postdata = {"client_id": app_key,
                        "redirect_uri": callback_url,
                        "userId": login_username,
                        "passwd": login_password,
                        "isLoginSina": "0",
                        "action": "submit",
                        "response_type": "code",
            }

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0",
                       "Host": "api.weibo.com",
                       "Referer": referer_url
            }

            auth_url = "https://api.weibo.com/oauth2/authorize"
            #auth_url = self.auth_info.auth_url
            resp_url = self._http_post(auth_url, data=postdata, headers=headers, json_parse=False).url
            logger.debug("response URL from local post: %s", resp_url)
            return resp_url
        except Exception, e:
            logger.warning("Catch exception: %s", e)

    @require_authed
    def weibo_request(self, name, method, params, files={}):
        '''
        General request method for Weibo V2 Api via OAuth.

        :param name:
            The Api name shown on main page
            (http://open.weibo.com/wiki/API%E6%96%87%E6%A1%A3_V2).
            e.g. ``friendships/create`` (no "2/" prefix)

        :param method:
            HTTP request method: 'GET' or 'POST'

        :param params:
            Parameters from Api doc.
            No need to manually put ``access_token`` in.

        :return:
            The http response from SinaWeibo (a JSON compatible structure).
        '''

        base_url = "https://api.weibo.com/2"
        full_url = "%s/%s.json" % (base_url, name)

        if not 'access_token' in params:
            params['access_token'] = self.token.access_token

        http_request_funcs = {
                'GET': self._http_get,
                'POST': self._http_post
                }
        if files:
            return http_request_funcs[method](full_url, params, files=files)
        else:
            return http_request_funcs[method](full_url, params)

    @require_authed
    def _short_url_weibo(self, url):
        try:
            results = self.weibo_request('short_url/shorten',
                    'GET',
                    {'url_long': url})
            logger.debug("URL shortening response: %s", results)
            u = results["urls"][0]
            return u["url_short"]
            # Even for usable URL, it returns False?
            #if u['result'] == 'true':
            #    return u["url_short"]
            #else:
            #    logger.warning("Response short URL is not usable ('%s'). Fallback to original URL", u["url_short"])
            #    return url
        except Exception as e:
            logger.warning("Catch exception when shortening URL on SinaWeibo: '%s'", e)
            return url

    @require_authed
    def _replace_with_short_url(self, text):
        import re
        #TODO:
        #    1) This regex needs upgrade.
        #       Is it better to match only http(s):// prefix?
        #    2) A better place to locate the pattern is the upper level dir,
        #       e.g. snstype.py. URL matching pattern is universal for all
        #       platforms. Placing it at a common area and making the pattern
        #       testable is favourable.
        p = re.compile("[a-zA-z]+://[^\s]*")
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        lst = p.findall(text)
        result = text
        for c in lst:
            ex_c = self._expand_url(c);
            surl = self._short_url_weibo(ex_c).encode('utf-8')
            logger.debug("url='%s', short_url='%s'", c, surl)
            result = result.replace(c,surl)
        return result.decode('utf-8')

class SinaWeiboStatusMessage(snstype.Message):
    platform = "SinaWeiboStatus"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        if 'deleted' in dct and dct['deleted']:
            logger.debug("This is a deleted message %s of SinaWeiboStatusMessage", dct["id"])
            self.parsed.time = "unknown"
            self.parsed.username = "unknown"
            self.parsed.userid = "unknown"
            self.parsed.text = "unknown"
            self.deleted = True
            return

        self.ID.id = dct["id"]

        self.parsed.time = utils.str2utc(dct["created_at"])
        self.parsed.username = dct['user']['name']
        self.parsed.userid = dct['user']['id']
        self.parsed.reposts_count = dct['reposts_count']
        self.parsed.comments_count = dct['comments_count']
        if 'pic_urls' in dct:
            for pic in dct['pic_urls']:
                self.parsed.attachments.append(
                {
                    'type': 'picture',
                    'format': ['link'],
                    'data': pic['thumbnail_pic'].replace('/thumbnail/', '/woriginal/')
                })

        if 'retweeted_status' in dct:
            self.parsed.username_orig = "unknown"
            if 'pic_urls' in dct['retweeted_status']:
                for pic in dct['retweeted_status']['pic_urls']:
                    self.parsed.attachments.append(
                        {
                            'type': 'picture',
                            'format': ['link'],
                            'data': pic['thumbnail_pic'].replace('/thumbnail/', '/woriginal/')
                        })

            try:
                self.parsed.username_orig = dct['retweeted_status']['user']['name']
            except KeyError:
                logger.warning('KeyError when parsing SinaWeiboStatus. May be deleted original message')
            self.parsed.text_orig = dct['retweeted_status']['text']
            self.parsed.text_trace = dct['text']
            self.parsed.text = self.parsed.text_trace \
                    + "//@" + self.parsed.username_orig \
                    + ": " + self.parsed.text_orig
        else:
            self.parsed.text_orig = dct['text']
            self.parsed.text_trace = None
            self.parsed.text = self.parsed.text_orig

class SinaWeiboStatus(SinaWeiboBase):

    Message = SinaWeiboStatusMessage

    def __init__(self, channel = None):
        super(SinaWeiboStatus, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @require_authed
    def home_timeline(self, count=20):
        '''Get home timeline

        :param count: number of statuses
        '''

        statuslist = snstype.MessageList()
        try:
            jsonobj = self.weibo_request('statuses/home_timeline',
                    'GET',
                    {'count': count})
            if("error" in  jsonobj):
                logger.warning("error json object returned: %s", jsonobj)
                return []
            for j in jsonobj['statuses']:
                statuslist.append(self.Message(j,\
                        platform = self.jsonconf['platform'],\
                        channel = self.jsonconf['channel_name']\
                        ))
            logger.info("Read %d statuses from '%s'", len(statuslist), self.jsonconf['channel_name'])
        except Exception, e:
            logger.warning("Catch exception: %s", e)

        return statuslist

    @require_authed
    def update(self, text, pic=None):
        '''update a status

           * parameter text: the update message
           * return: success or not
        '''
        # NOTE:
        #     * With this pre-shortening, we can post potentially longer messages.
        #     * It consumes one more API quota.
        text = self._replace_with_short_url(text)
        text = self._cat(self.jsonconf['text_length_limit'], [(text,1)], delim='//')

        try:
            if not pic:
                ret = self.weibo_request('statuses/update',
                        'POST',
                        {'status': text})
            else:
                ret = self.weibo_request(
                    'statuses/upload',
                    'POST',
                    {'status': text},
                    files={'pic': ('pic.jpg', pic)}
                )
            self.Message(ret)
            logger.info("Update status '%s' on '%s' succeed", text, self.jsonconf.channel_name)
            return True
        except Exception as e:
            logger.warning("Update status fail. Message: %s", e)
            return False

    @require_authed
    def reply(self, statusID, text):
        '''reply to a status

           * parameter text: the comment text
           * return: success or not
        '''
        try:
            ret = self.weibo_request('comments/create',
                    'POST',
                    {'id': statusID.id, 'comment': text })
            ret['id']
            return True
        except Exception as e:
            logger.info("Reply '%s' to status '%s' fail: %s", text, self.jsonconf.channel_name, e)
            return False

    @require_authed
    def forward(self, message, text):
        '''
        Forward a status on SinaWeibo:

           * If message is from the same platform, forward it
             using special interface.
           * Else, route the request
             to a general forward method of ``SNSBase``.
           * Decorate the text with previous comment sequence.

        :param message:
            An ``snstype.Message`` object to forward

        :param text:
            Append comment text

        :return: Success or not

        '''
        if not message.platform == self.platform:
            return super(SinaWeiboStatus, self).forward(message, text)
        else:
            mID = message.ID
            if not message.parsed['text_trace'] is None:
                #origin_sequence = u'@' + m.raw['user']['name'] + u'：' + m.raw['text'])
                origin_sequence = u'@' + message.parsed['username'] + u'：' + message.parsed['text_trace']
                decorated_text = self._cat(self.jsonconf['text_length_limit'],
                        [(text,2), (origin_sequence, 1)],
                        delim='//')
            else:
                decorated_text = text
            return self._forward(mID, decorated_text)

    @require_authed
    def _forward(self, mID, text):
        '''
        Raw forward method

           * Only support Sina message
           * Use 'text' as exact comment sequence
        '''
        try:
            ret = self.weibo_request('statuses/repost',
                    'POST',
                    {'id': mID.id, 'status': text })
            if 'id' in ret:
                return True
            else:
                logger.warning("'%s' forward status '%s' with comment '%s' fail. ret: %s",
                        self.jsonconf.channel_name, mID, text, ret)
                return False
        except Exception as e:
            logger.warning("'%s' forward status '%s' with comment '%s' fail: %s",
                    self.jsonconf.channel_name, mID, text, e)
            return False

if __name__ == '__main__':
    print '\n\n\n'
    print '==== SNSAPI Demo of sina.py module ====\n'
    # Create and fill in app information
    sina_conf = SinaWeiboStatus.new_channel()
    sina_conf['channel_name'] = 'test_sina'
    sina_conf['app_key'] = '2932547522'                           # Chnage to your own keys
    sina_conf['app_secret'] = '93969e0d835ffec8dcd4a56ecf1e57ef'  # Change to your own keys
    # Instantiate the channel
    sina = SinaWeiboStatus(sina_conf)
    # OAuth your app
    print 'SNSAPI is going to authorize your app.'
    print 'Please make sure:'
    print '   * You have filled in your own app_key and app_secret in this script.'
    print '   * You configured the callback_url on open.weibo.com as'
    print '     http://snsapi.sinaapp.com/auth.php'
    print 'Press [Enter] to continue or Ctrl+C to end.'
    raw_input()
    sina.auth()
    # Test get 2 messages from your timeline
    status_list = sina.home_timeline(2)
    print '\n\n--- Statuses of your friends is followed ---'
    print status_list
    print '--- End of status timeline ---\n\n'

    print 'Short demo ends here! You can do more with SNSAPI!'
    print 'Please join our group for further discussions'

########NEW FILE########
__FILENAME__ = tencent
#-*- encoding: utf-8 -*-

'''
Tencent Weibo Client
'''

from ..snslog import SNSLog as logger
from ..snsbase import SNSBase, require_authed
from .. import snstype
from .. import utils

logger.debug("%s plugged!", __file__)

class TencentWeiboStatusMessage(snstype.Message):
    platform = "TencentWeiboStatus"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        #TODO: unify the data type
        #      In SinaAPI, 'created_at' is a string
        #      In TecentWeibo, 'created_at' is an int
        #Proposal:
        #      1. Store a copy of dct object in the Status object.
        #         Derived class of TecentWeibo or SinaAPI can extract
        #         other fields for future use.
        #      2. Defaultly convert every fields into unicode string.
        #         Upper layer can tackle with a unified interface

        self.ID.reid = dct['id']

        self.parsed.time = dct['timestamp']
        self.parsed.userid = dct['name']
        self.parsed.username = dct['nick']

        # The 'origtext' field is plaintext.
        # URLs in 'text' field is parsed to HTML tag
        self.parsed.reposts_count = dct['count']
        self.parsed.comments_count = dct['mcount']
        self.parsed.text_last = utils.html_entity_unescape(dct['origtext'])
        if 'source' in dct and dct['source']:
            self.parsed.text_trace = utils.html_entity_unescape(dct['origtext'])
            self.parsed.text_orig = utils.html_entity_unescape(dct['source']['origtext'])
            self.parsed.username_orig = utils.html_entity_unescape(dct['source']['nick'])
            self.parsed.text = self.parsed.text_trace \
                    + " || " + "@" + self.parsed.username_orig \
                    + " : " + self.parsed.text_orig
        else:
            self.parsed.text_trace = None
            self.parsed.text_orig = utils.html_entity_unescape(dct['origtext'])
            self.parsed.username_orig = dct['nick']
            self.parsed.text = utils.html_entity_unescape(dct['origtext'])

        #TODO:
        #    retire past fields
        #self.ID.reid = dct['id']
        #self.parsed.id = dct['id']
        #self.parsed.created_at = dct['timestamp']
        #self.parsed.text = dct['text']
        #self.parsed.reposts_count = dct['count']
        #self.parsed.comments_count = dct['mcount']
        #self.parsed.username = dct['name']
        #self.parsed.usernick = dct['nick']

class TencentWeiboStatus(SNSBase):

    Message = TencentWeiboStatusMessage

    def __init__(self, channel = None):
        super(TencentWeiboStatus, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['app_key'] = ''
        c['app_secret'] = ''
        c['platform'] = 'TencentWeiboStatus'
        c['auth_info'] = {
                "save_token_file": "(default)",
                "cmd_request_url": "(default)",
                "callback_url": "http://snsapi.sinaapp.com/auth.php",
                "cmd_fetch_code": "(default)"
                }

        return c

    def read_channel(self, channel):
        super(TencentWeiboStatus, self).read_channel(channel)

        if not "auth_url" in self.auth_info:
            self.auth_info.auth_url = "https://open.t.qq.com/cgi-bin/oauth2/"
        if not "callback_url" in self.auth_info:
            self.auth_info.callback_url = "http://snsapi.sinaapp.com/auth.php"

        # Tencent limit is a little more than 140.
        # We just use 140, which is a global industrial standard.
        self.jsonconf['text_length_limit'] = 140

        #if not 'platform_prefix' in self.jsonconf:
        #    self.jsonconf['platform_prefix'] = u'腾讯'

    def need_auth(self):
        return True

    def auth_first(self):
        self._oauth2_first()

    def auth_second(self):
        try:
            self._oauth2_second()
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def _attach_authinfo(self, params):
        params['access_token'] = self.token.access_token
        params['openid'] = self.token.openid
        params['oauth_consumer_key'] = self.jsonconf.app_key
        params['oauth_version'] = '2.a'
        params['scope'] = 'all'
        return params

    def tencent_request(self, method, http_method="GET", files={}, **kwargs):
        self._attach_authinfo(kwargs)
        if http_method == "GET":
            return self._http_get("https://open.t.qq.com/api/" + method, params=kwargs)
        else:
            return self._http_post("https://open.t.qq.com/api/" + method, params=kwargs, files=files)

    @require_authed
    def home_timeline(self, count=20):
        '''Get home timeline

           * function : get statuses of yours and your friends'
           * parameter count: number of statuses
        '''

        jsonobj = self.tencent_request("statuses/home_timeline", reqnum=count)
        #logger.debug("returned: %s", jsonobj)

        statuslist = snstype.MessageList()
        try:
            for j in jsonobj['data']['info']:
                statuslist.append(self.Message(j,\
                    platform = self.jsonconf['platform'],\
                    channel = self.jsonconf['channel_name']\
                    ))
        except Exception, e:
            logger.warning("Catch exception: %s", e)
            return []
        return statuslist

    @require_authed
    def update(self, text, pic=None):
        '''update a status

           * parameter text: the update message
           * return: success or not
        '''

        text = self._cat(self.jsonconf['text_length_limit'], [(text,1)])

        if not pic:
            method = "t/add"
        else:
            method = "t/add_pic"

        try:
            if pic:
                ret = self.tencent_request(method, "POST", content=text, files={'pic': ('pic.jpg', pic)})
            else:
                ret = self.tencent_request(method, "POST", content=text)
            if(ret['msg'] == "ok"):
                logger.info("Update status '%s' on '%s' succeed", text, self.jsonconf.channel_name)
                return True
            else:
                return ret
        except Exception, e:
            logger.warning("Catch Exception: %s", e)
            return False

    @require_authed
    def reply(self, statusID, text):
        '''reply to a status

           * parameter text: the comment text
           * return: success or not
        '''
        ret = self.tencent_request("t/reply", "POST", content=text, reid=statusID.reid)
        if(ret['msg'] == "ok"):
            return True
        logger.info("Reply '%s' to status '%s' fail: %s", text, self.jsonconf.channel_name, ret)
        return ret


########NEW FILE########
__FILENAME__ = emails
#-*- encoding: utf-8 -*-

'''
email platform

Support get message by IMAP and send message by SMTP

The file is named as "emails.py" instead of "email.py"
because there is a package in Python called "email".
We will import that package..

Premature warning:
   * This is platform is only tested on GMail so far.
   * Welcome to report test results of other platform.

'''

from ..snslog import SNSLog
logger = SNSLog
from ..snsbase import SNSBase, require_authed
from .. import snstype
from ..utils import console_output
from .. import utils
from ..utils import json

import time
import email
from email.mime.text import MIMEText
from email.header import decode_header, make_header
import imaplib
import smtplib

import base64
import re

logger.debug("%s plugged!", __file__)

class EmailMessage(snstype.Message):
    platform = "Email"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _decode_header(self, header_value):
        ret = unicode()
        #print decode_header(header_value)
        for (s,e) in decode_header(header_value):
            ret += s.decode(e) if e else s
        return ret

    def _parse(self, dct):
        #TODO:
        #    Put in message id.
        #    The id should be composed of mailbox and id in the box.
        #
        #    The IMAP id can not be used as a global identifier.
        #    Once messages are deleted or moved, it will change.
        #    The IMAP id is more like the subscript of an array.
        #
        #    SNSAPI should work out its own message format to store an
        #    identifier. An identifier should be (address, sequence).
        #    There are three ways to generate the sequence number:
        #       * 1. Random pick
        #       * 2. Pass message through a hash
        #       * 3. Maintain a counter in the mailbox
        #       * 4. UID as mentioned in some discussions. Not sure whether
        #       this is account-dependent or not.
        #
        #     I prefer 2. at present. Our Message objects are designed
        #     to be able to digest themselves.

        self.parsed.title = self._decode_header(dct.get('Subject'))
        self.parsed.text = dct.get('body')
        self.parsed.time = utils.str2utc(dct.get('Date'))

        sender = dct.get('From')
        r = re.compile(r'^(.+)<(.+@.+\..+)>$', re.IGNORECASE)
        m = r.match(sender)
        if m:
            self.parsed.username = m.groups()[0].strip()
            self.parsed.userid = m.groups()[1].strip()
        else:
            self.parsed.username = sender
            self.parsed.userid = sender

        #TODO:
        #    The following is just temporary method to enable reply email.
        #    See the above TODO for details. The following information
        #    suffices to reply email. However, they do not form a real ID.
        self.ID.title = self.parsed.title
        self.ID.reply_to = dct.get('Reply-To', self.parsed.userid)

class Email(SNSBase):

    Message = EmailMessage

    def __init__(self, channel = None):
        super(Email, self).__init__(channel)
        self.platform = self.__class__.__name__

        self.imap = None
        self.imap_ok = False
        self.smtp = None
        self.smtp_ok = False

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['platform'] = 'Email'
        c['imap_host'] = 'imap.gmail.com'
        c['imap_port'] = 993 #default IMAP + TLS port
        c['smtp_host'] = 'smtp.gmail.com'
        c['smtp_port'] = 587 #default SMTP + TLS port
        c['username'] = 'username'
        c['password'] = 'password'
        c['address'] = 'username@gmail.com'
        return c

    def read_channel(self, channel):
        super(Email, self).read_channel(channel)

    def __decode_email_body(self, payload, msg):
        ret = payload
        if 'Content-Transfer-Encoding' in msg:
            transfer_enc = msg['Content-Transfer-Encoding'].strip()
            if transfer_enc == "base64":
                ret = base64.decodestring(ret)
            elif transfer_enc == "7bit":
                #TODO:
                #    It looks like 7bit is just ASCII standard.
                #    Do nothing.
                #    Check whether this logic is correct?
                pass
            else:
                logger.warning("unknown transfer encoding: %s", transfer_enc)
                return "(Decoding Failed)"
        # The past content-type fetching codes.
        # It's better to rely on email.Message functions.
        #
        #if 'Content-Type' in msg:
        #    ct = msg['Content-Type']
        #    r = re.compile(r'^(.+); charset="(.+)"$', re.IGNORECASE)
        #    m = r.match(ct)
        #    # Use search if the pattern does not start from 0.
        #    # Use group() to get matched part and groups() to get
        #    # mateched substrings.
        #    if m:
        #        cs = m.groups()[1]
        #    else:
        #        # By default, we assume ASCII charset
        #        cs = "ascii"
        #    try:
        #        ret = ret.decode(cs)
        #    except Exception, e:
        #        #logger.warning("Decoding payload '%s' using '%s' failed!", payload, cs)
        #        return "(Decoding Failed)"

        try:
            cs = msg.get_content_charset()
            ret = ret.decode(cs)
        except Exception, e:
            return "(Decoding Failed)"

        return ret

    def _extract_body(self, payload, msg):
        if isinstance(payload,str):
            return self.__decode_email_body(payload, msg)
        else:
            return '\n'.join([self._extract_body(part.get_payload(), msg) for part in payload])

    def _get_text_plain(self, msg):
        '''
        Extract text/plain section from a multipart message.

        '''
        tp = None
        if not msg.is_multipart():
            if msg.get_content_type() == 'text/plain':
                tp = msg
            else:
                return u"No text/plain found"
        else:
            for p in msg.walk():
                if p.get_content_type() == 'text/plain':
                    tp = p
                    break
        if tp:
            return self.__decode_email_body(tp.get_payload(), tp)
        else:
            return u"No text/plain found"

    def _format_from_text_plain(self, text):
        '''
        Some text/plain message is sent from email services.
        The formatting is not SNSAPI flavoured. To work around
        this and enable unified view, we use this function
        to do post-formatting.

        '''
        return text.replace('>', '').replace('\r\n', '').replace('\n', '')

    def _wait_for_email_subject(self, sub):
        conn = self.imap
        conn.select('INBOX')
        num = None
        while (num is None):
            logger.debug("num is None")
            typ, data = conn.search(None, '(Subject "%s")' % sub)
            num = data[0].split()[0]
            time.sleep(0.5)
        return num

    def _get_buddy_list(self):
        # 1. Get buddy_list from "buddy" folder

        (typ, data) = self.imap.create('buddy')
        conn = self.imap
        conn.select('buddy')

        self.buddy_list = {}
        num = None
        self._buddy_message_id = None
        try:
            typ, data = conn.search(None, 'ALL')
            # We support multiple emails in "buddy" folder.
            # Each of the files contain a json list. We'll
            # merge all the list and use it as the buddy_list.
            for num in data[0].split():
                typ, msg_data = conn.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_string(response_part[1])
                        text = self._extract_body(msg.get_payload(), msg)
                        logger.debug("Extract part text: %s", text.rstrip())
                        try:
                            self.buddy_list.update(json.loads(text))
                        except Exception, e:
                            logger.warning("Extend list with '%s' failed!", e)
            logger.debug("reading buddylist successful: %s", self.buddy_list)
        except Exception, e:
            logger.warning("catch exception when trying to read buddylist %s", e)
            pass

        if self.buddy_list is None:
            logger.debug("buddy list is None")
            self.buddy_list = {}

        # 2. Get buddy_list from local conf files

        if "manual_buddy_list" in self.jsonconf:
            for b in self.jsonconf['manual_buddy_list']:
                self.buddy_list[b['userid']] = b

    def _update_buddy_list(self):
        conn = self.imap

        # The unique identifier for a buddy_list
        title = 'buddy_list:' + str(self.time())
        from email.mime.text import MIMEText
        msg = MIMEText(json.dumps(self.buddy_list))
        self._send(self.jsonconf['address'], title, msg)

        # Wait for the new buddy_list email to arrive
        mlist = self._wait_for_email_subject(title)
        logger.debug("returned message id: %s", mlist)

        # Clear obsolete emails in "buddy" box
        conn.select('buddy')
        typ, data = conn.search(None, 'ALL')
        for num in data[0].split():
            conn.store(num, '+FLAGS', r'(\deleted)')
            logger.debug("deleting message '%s' from 'buddy'", num)

        # Move the new buddy_list email from INBOX to "buddy" box
        conn.select('INBOX')
        conn.copy(mlist, 'buddy')
        conn.store(mlist, '+FLAGS', r'(\deleted)')

    def add_buddy(self, address, nickname = None):
        '''
        Warning: Use this function only when necessary. (20121026)

        We have not abstracted User class yet. The first step for SNSAPI
        is to abstract the information flow. That is the Message class
        you see. We assume buddy_list is maintained in other offline manner.
        e.g. Users login Sina Weibo and change their buddy list. In the
        next milestone, we may consider abstract User class. In the current
        framework, we need some esential function to manage buddy_list on
        email platform. This is why the currrent function is here. The
        interface may be (drastically) changed in the future.

        The better way for upper layer developers is to operate
        'self.buddy_list' directly following the format.

        '''
        #self.buddy_list.append({"userid": address, "username": nickname})
        self.buddy_list[address] = {"userid": address, "username": nickname}
        self._update_buddy_list()

    def _receive(self, count = 20):
        #TODO:
        #    1.
        #    Consider UNSEEN message first. If we get less than count
        #    number of messages, then search for 'ALL'.
        #
        #    2.
        #    Make a separate box for snsapi. According to configs,
        #    search for all messages or snsapi formated messages.
        #    For snsapi formated messages, move them to this mailbox.

        # Check out all the email IDs
        conn = self.imap
        conn.select('INBOX')
        typ, data = conn.search(None, 'ALL')
        #logger.debug("read message IDs: %s", data)

        # We assume ID is in chronological order and filter
        # the count number of latest messages.
        latest_messages = sorted(data[0].split(), key = lambda x: int(x), reverse = True)[0:count]
        #logger.debug("selected message IDs: %s", latest_messages)

        message_list = []
        try:
            #for num in data[0].split():
            for num in latest_messages:
                typ, msg_data = conn.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_string(response_part[1])

                        #TODO:
                        #    Parse header fields. Header fields can also be
                        #    encoded, e.g. UTF-8.
                        #
                        #    email.header.decode_header() may help.
                        #
                        #    There are some ill-formated senders, e.g. Baidu Passport.
                        #    See the link for workaround:
                        #    http://stackoverflow.com/questions/7331351/python-email-header-decoding-utf-8

                        # Convert header fields into dict
                        d = dict(msg)
                        d['body'] = self._format_from_text_plain(self._get_text_plain(msg))
                        d['_pyobj'] = utils.Serialize.dumps(msg)
                        message_list.append(utils.JsonDict(d))
        except Exception, e:
            logger.warning("Error when making message_list: %s", e)
        return message_list

    def auth(self):
        #TODO:
        #    login here once is not enough.
        #    If the client stays idle for a long time,
        #    it will disconnect from the server. So in
        #    later transactions, we should check and
        #    login again if necessary.
        #
        #    The error caught is "socket error: EOF"

        imap_ok = False
        smtp_ok = False

        logger.debug("Try login IMAP server...")
        try:
            if self.imap:
                del self.imap
            self.imap = imaplib.IMAP4_SSL(self.jsonconf['imap_host'], self.jsonconf['imap_port'])
            self.imap.login(self.jsonconf['username'], self.jsonconf['password'])
            imap_ok = True
        except imaplib.IMAP4_SSL.error, e:
            if e.message.find("AUTHENTICATIONFAILED"):
                logger.warning("IMAP Authentication failed! Channel '%s'", self.jsonconf['channel_name'])
            else:
                raise e

        logger.debug("Try login SMTP server...")
        try:
            if self.smtp:
                del self.smtp
            self.smtp = smtplib.SMTP("%s:%s" % (self.jsonconf['smtp_host'], self.jsonconf['smtp_port']))
            self.smtp.starttls()
            self.smtp.login(self.jsonconf['username'], self.jsonconf['password'])
            smtp_ok = True
        except smtplib.SMTPAuthenticationError:
            logger.warning("SMTP Authentication failed! Channel '%s'", self.jsonconf['channel_name'])

        if imap_ok and smtp_ok:
            self.imap_ok = True
            self.smtp_ok = True
            logger.info("Email channel '%s' auth success", self.jsonconf['channel_name'])
            self._get_buddy_list()
            return True
        else:
            logger.warning("Email channel '%s' auth failed!!", self.jsonconf['channel_name'])
            return False

    def _send(self, toaddr, title, msg):
        '''
        :param toaddr:
            The recipient, only one in a string.

        :param msg:
            One email object, which supports as_string() method
        '''
        fromaddr = self.jsonconf['address']
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = make_header([(self._unicode_encode(title), 'utf-8')])

        try:
            self.smtp.sendmail(fromaddr, toaddr, msg.as_string())
            return True
        except Exception, e:
            if e.message.count("socket error: EOF"):
                logger.debug("Catch EOF. Reconnect...")
                self.auth()
            logger.warning("Catch exception: %s", e)
            return False

    @require_authed
    def home_timeline(self, count = 20):
        try:
            r = self._receive(count)
        except Exception, e:
            if e.message.count("socket error: EOF"):
                logger.debug("Catch EOF. Reconnect...")
                self.auth()
            logger.warning("Catch exception: %s", e)
            return snstype.MessageList()

        message_list = snstype.MessageList()
        try:
            for m in r:
                message_list.append(self.Message(
                        m,\
                        platform = self.jsonconf['platform'],\
                        channel = self.jsonconf['channel_name']\
                        ))
        except Exception, e:
            logger.warning("Catch expection: %s", e)

        logger.info("Read %d statuses from '%s'", len(message_list), self.jsonconf.channel_name)
        return message_list

    def _send_to_all_buddy(self, title, msg):
        ok_all = True
        for u in self.buddy_list.values():
            toaddr = u['userid'] #userid of email platform is email address
            re = self._send(toaddr, title, msg)
            logger.debug("Send email to '%s': %s", toaddr, re)
            ok_all = ok_all and re
        return ok_all

    @require_authed
    def update(self, text, title = None):
        '''
        :title:
            The unique field of email. Other platforms do not use it. If not supplied,
            we'll format a title according to SNSAPI convention.
        '''
        msg = MIMEText(text, _charset = 'utf-8')
        if not title:
            #title = '[snsapi][status][from:%s][timestamp:%s]' % (self.jsonconf['address'], str(self.time()))
            title = '[snsapi][status]%s' % (text[0:10])
        return self._send_to_all_buddy(title, msg)

    @require_authed
    def reply(self, statusID, text):
        """reply status
        @param status: StatusID object
        @param text: string, the reply message
        @return: success or not
        """
        msg = MIMEText(text, _charset = 'utf-8')
        title = "Re:" + statusID.title
        toaddr = statusID.reply_to
        return self._send(toaddr, title, msg)

    def expire_after(self, token = None):
        # Check whether the user supplied secrets are correct
        if self.imap_ok == True and self.smtp_ok == True:
            # -1: Means this platform does not have token expire issue.
            #     More precisely, when the secrets are correct,
            #     you can re-login at any time. Same effect as
            #     refresing the token of OSN.
            return -1
        else:
            # 0: Means it has already expired. The effect of incorrect
            #    secrets is same as expired.
            return 0

# === email message fields for future reference
# TODO:
#     Enhance the security level by check fields like
#     'Received'. GMail has its checking at the web
#     interface side. Fraud identity problem will be
#     alleviated.
# In [7]: msg.keys()
# Out[7]:
# ['Delivered-To',
# 'Received',
# 'Received',
# 'Return-Path',
# 'Received',
# 'Received-SPF',
# 'Authentication-Results',
# 'Received',
# 'DKIM-Signature',
# 'MIME-Version',
# 'Received',
# 'X-Notifications',
# 'X-UB',
# 'X-All-Senders-In-Circles',
# 'Date',
# 'Message-ID',
# 'Subject',
# 'From',
# 'To',
# 'Content-Type']
#
# In [8]: msg['From']
# Out[8]: '"Google+ team" <noreply-daa26fef@plus.google.com>'
#
# In [9]: msg['To']
# Out[9]: 'hupili.snsapi@gmail.com'
#
# In [10]: msg['Subject']
# Out[10]: 'Getting started on Google+'
#
# In [11]: msg['Date']
# Out[11]: 'Mon, 22 Oct 2012 22:37:37 -0700 (PDT)'
#
# In [12]: msg['Content-Type']
# Out[12]: 'multipart/alternative; boundary=047d7b5dbe702bc3f804ccb35e18'

########NEW FILE########
__FILENAME__ = facebook
#-*- encoding: utf-8 -*-

import time
import re
from ..snslog import SNSLog
logger = SNSLog
from ..snsbase import SNSBase, require_authed
from .. import snstype
from .. import utils

from ..third import facebook

logger.debug("%s plugged!", __file__)

class FacebookFeedMessage(snstype.Message):
    platform = "FacebookFeed"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        self.ID.id = dct['id']

        self.parsed.time = utils.str2utc(dct['created_time'])
        self.parsed.username = dct['from']['name']
        self.parsed.userid = dct['from']['id']
        self.parsed.attachments = []
        resmsg = []
        if 'message' in dct:
            resmsg.append(dct['message'])
        if 'story' in dct:
            resmsg.append(dct['story'])
        if dct['type'] == 'photo':
            self.parsed.attachments.append({
                'type': 'picture',
                'format': ['link'],
                #NOTE: replace _s to _n will get the original picture
                'data': re.sub(r'_[a-z](\.[^.]*)$', r'_n\1', dct['picture'])
            })
        if dct['type'] == 'video':
            self.parsed.attachments.append({
                'type': 'video',
                'format': ['link'],
                'data': dct['link']
            })
        if dct['type'] == 'link':
            self.parsed.attachments.append({
                'type': 'link',
                'format': ['link'],
                'data': dct['link']
            })
        self.parsed.text = '\n'.join(resmsg)


class FacebookFeed(SNSBase):

    Message = FacebookFeedMessage

    def __init__(self, channel=None):
        super(FacebookFeed, self).__init__(channel)
        self.platform = self.__class__.__name__
        self.token = {}

    @staticmethod
    def new_channel(full=False):
        c = SNSBase.new_channel(full)

        c['platform'] = 'FacebookFeed'
        c['access_token'] = ''
        # The client_id in FB's term
        c['app_key'] = ''
        c['app_secret'] = ''

        c['auth_info'] = {
                "save_token_file": "(default)",
                "cmd_request_url": "(default)",
                "callback_url": "http://snsapi.ie.cuhk.edu.hk/aux/auth.php",
                "cmd_fetch_code": "(default)"
                }

        return c

    def read_channel(self, channel):
        super(FacebookFeed, self).read_channel(channel)

    def auth_first(self):
        url = "https://www.facebook.com/dialog/oauth?client_id=" + \
                self.jsonconf['app_key'] + \
                "&redirect_uri=" + \
                self.auth_info['callback_url'] + \
                "&response_type=token&scope=read_stream,publish_stream"
        self.request_url(url)

    def auth_second(self):
        #TODO:
        #    Find a way to get the code in parameters, not in URL fragmentation
        try:
            url = self.fetch_code()
            url = url.replace('#', '?')
            self.token = self._parse_code(url)
            self.token.expires_in = int(int(self.token.expires_in) + time.time())
            #self.token = {'access_token' : self.fetch_code(),
            #              'expires_in' : -1}
            self.graph = facebook.GraphAPI(access_token=self.token['access_token'])
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def _do_oauth(self):
        '''
        The two-stage OAuth
        '''
        self.auth_first()
        self.auth_second()
        if self._is_authed():
            self.save_token()
            return True
        else:
            logger.info("OAuth channel '%s' on Facebook fail", self.jsonconf.channel_name)
            return False


    def auth(self):
        if self.get_saved_token():
            self.graph = facebook.GraphAPI(access_token=self.token['access_token'])
            return True
        if self.jsonconf['access_token'] and self._is_authed(self.jsonconf['access_token']):
            self.token = {'access_token': self.jsonconf['access_token'], 'expires_in' : -1}
            self.graph = facebook.GraphAPI(access_token=self.token['access_token'])
            self.save_token()
            return True
        elif 'access_token' not in self.jsonconf or not self.jsonconf['access_token']:
            return self._do_oauth()
        else:
            logger.debug('auth failed')
            return False

    @require_authed
    def home_timeline(self, count=20):
        status_list = snstype.MessageList()
        statuses = self.graph.get_connections("me", "home", limit=count)
        for s in statuses['data']:
            try:
                status_list.append(self.Message(s,\
                        self.jsonconf['platform'],\
                        self.jsonconf['channel_name']))
            except Exception, e:
                logger.warning("Catch expection: %s", e)
        logger.info("Read %d statuses from '%s'", len(status_list), self.jsonconf['channel_name'])
        return status_list

    @require_authed
    def update(self, text):
        try:
            status = self.graph.put_object("me", "feed", message=self._unicode_encode(text))
            if status:
                return True
            else:
                return False
        except Exception, e:
            logger.warning('update Facebook failed: %s', str(e))
            return False

    @require_authed
    def reply(self, statusID, text):
        try:
            status = self.graph.put_object(statusID.id, "comments", message=self._unicode_encode(text))
            if status:
                return True
            else:
                return False
        except Exception, e:
            logger.warning("commenting on Facebook failed:%s", str(e))
            return False

    def need_auth(self):
        return True

    def _is_authed(self, token=None):
        #FIXME:
        #TODO:
        #    Important refactor point here!
        #    See `SNSBase.expire_after` for the flow.
        #    The aux function should only look at the 'token' parameter.
        #    Belowing is just a logic fix.
        orig_token = token
        if token == None:
            if self.token and 'access_token' in self.token:
                token = self.token['access_token']
            else:
                # No token passed in. No token in `self.token`
                # --> not authed
                return False
        t = facebook.GraphAPI(access_token=token)
        try:
            res = t.request('me/')
            if orig_token == None and self.token and self.jsonconf['app_secret'] and self.jsonconf['app_key'] and (self.token['expires_in'] - time.time() < 6000):
                logger.debug("refreshing token")
                try:
                    res = t.extend_access_token(self.jsonconf['app_key'], self.jsonconf['app_secret'])
                    print res
                    logger.debug("new token expires in %s relative seconds" % (res['expires']))
                    self.token['access_token'] = res['access_token']
                    if 'expires' in res:
                        self.token['expires_in'] = int(res['expires']) + time.time()
                    else:
                        #TODO:
                        #    How to come to this branch?
                        #    Can we assert False here?
                        self.token['expires_in'] = -1
                    self.graph.access_token = res['access_token']
                    self.save_token()
                except Exception, ei:
                    logger.warning("Refreshing token failed: %s", ei)
                    return False
            return True
        except Exception, e:
            logger.warning("Catch Exception: %s", e)
            return False

    def expire_after(self, token = None):
        # This platform does not have token expire issue.
        if token and 'access_token' in token:
            token = token['access_token']
        else:
            token = None
        if self._is_authed(token):
            if 'expires_in' in self.token:
                return self.token['expires_in'] - time.time()
            else:
                return -1
        else:
            return 0

########NEW FILE########
__FILENAME__ = renren
#-*- encoding: utf-8 -*-

'''
Renren Client

'''

if __name__ == '__main__':
    import sys
    sys.path.append('..')
    from snslog import SNSLog as logger
    from snsbase import SNSBase, require_authed
    import snstype
    from snstype import BooleanWrappedData
    import utils
    import time
    import urllib
else:
    from ..snslog import SNSLog as logger
    from ..snsbase import SNSBase, require_authed
    from ..snstype import BooleanWrappedData
    from .. import snstype
    from .. import utils
    import time
    import urllib


logger.debug("%s plugged!", __file__)

# Inteface URLs.
# This differs from other platforms
RENREN_AUTHORIZATION_URI = "http://graph.renren.com/oauth/authorize"
RENREN_ACCESS_TOKEN_URI = "http://graph.renren.com/oauth/token"
RENREN_API_SERVER = "https://api.renren.com/restserver.do"
RENREN_API2_SERVER = "https://api.renren.com/v2/"

# This error is moved back to "renren.py".
# It's platform specific and we do not expect other
# file to raise this error.
class RenrenAPIError(Exception):
    def __init__(self, code, message):
        super(RenrenAPIError, self).__init__(message)
        self.code = code

class RenrenFeedMessage(snstype.Message):
    platform = "RenrenFeed"

    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        self.ID.status_id = dct['source_id']
        self.ID.source_user_id = self.parsed.userid = str(dct['actor_id'])
        self.parsed.username = dct['name']
        self.parsed.time = utils.str2utc(dct['update_time'], " +08:00")
        self.parsed.text = ""
        self.ID.feed_type = self.parsed.feed_type = {
            10: 'STATUS',
            11: 'STATUS',
            20: 'BLOG',
            21: 'SHARE',
            22: 'BLOG',
            23: 'SHARE',
            30: 'PHOTO',
            31: 'PHOTO',
            32: 'SHARE',
            33: 'SHARE',
            34: 'OTHER',
            35: 'OTHER',
            36: 'SHARE',
            40: 'OTHER',
            41: 'OTHER',
            50: 'SHARE',
            51: 'SHARE',
            52: 'SHARE',
            53: 'SHARE',
            54: 'SHARE',
            55: 'SHARE'
        }[dct['feed_type']]
        ORIG_USER = 'orig'
        if 'attachment' in dct and dct['attachment']:
            for at in dct['attachment']:
                if 'owner_name' in at and at['owner_name']:
                    ORIG_USER = at['owner_name']
                    self.parsed.username_orig = ORIG_USER
        if 'message' in dct:
            self.parsed.text += dct['message']
        if dct['feed_type'] in [21, 23, 32, 33, 36, 50, 51, 52, 53, 54, 55]:
            self.parsed.text += u" //" + ORIG_USER + ":"
        if 'title' in dct:
            if 'message' not in dct or dct['message'] != dct['title']:
                self.parsed.text += ' "' + dct['title'] + '" '
        if 'description' in dct:
            self.parsed.text += dct['description']
        if 'attachment' in dct and dct['attachment']:
            for at in dct['attachment']:
                if at['media_type'] == 'photo':
                    self.parsed.attachments.append(
                        {
                            'type': 'picture',
                            'format': ['link'],
                            #FIXME: page photo don't have raw_src
                            'data': 'raw_src' in at and at['raw_src'] or at['src'].replace('head_', 'original_')
                        }
                    )
                elif 'href' in at:
                    attype = 'link'
                    if at['media_type'] in ['album', 'blog']:
                        attype = at['media_type']
                    self.parsed.attachments.append(
                        {
                            'type': attype,
                            'format': ['link'],
                            'data': at['href']
                        })
                if 'content' in at:
                    self.parsed.text += at['content']



class RenrenStatusMessage(RenrenFeedMessage):
    platform = 'RenrenStatus'

class RenrenShareMessage(RenrenFeedMessage):
    platform = 'RenRenShare'

class RenrenBlogMessage(RenrenFeedMessage):
    platform = 'RenrenBlog'

class RenrenPhotoMessage(RenrenFeedMessage):
    platform = 'RenrenPhoto'


class RenrenFeed(SNSBase):

    Message = RenrenFeedMessage

    def __init__(self, channel = None):
        super(RenrenFeed, self).__init__(channel)
        self.platform = self.__class__.__name__

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['app_key'] = ''
        c['app_secret'] = ''
        c['platform'] = 'RenrenFeed'
        c['auth_info'] = {
                "save_token_file": "(default)",
                "cmd_request_url": "(default)",
                "callback_url": "http://snsapi.ie.cuhk.edu.hk/aux/auth.php",
                "cmd_fetch_code": "(default)"
                }
        return c

    def renren_request(self, method=None, **kwargs):
        return self._renren_request_v1_no_sig(method, **kwargs)

    def _renren_request_v2_bearer_token(self, method=None, **kwargs):
        kwargs['access_token'] = self.token.access_token
        if '_files' in kwargs:
            _files = kwargs['_files']
            del kwargs['_files']
        else:
            _files = {}
        if _files:
            args = urllib.urlencode(kwargs)
            response = self._http_post(RENREN_API2_SERVER + method + '?' + args, {}, files=_files)
        else:
            response = self._http_get(RENREN_API2_SERVER + method, kwargs)
        #logger.debug('response: %s', response)
        if response == {} or 'error' in response:
            if 'error' in response:
                logger.warning(response['error']['message'])
            else:
                logger.warning("error")
        return response



    def _renren_request_v1_no_sig(self, method=None, **kwargs):
        '''
        A general purpose encapsulation of renren API.
        It fills in system paramters and compute the signature.
        Return a list on success
        raise Exception on error
        '''

        kwargs['method'] = method
        kwargs['access_token'] = self.token.access_token
        kwargs['v'] = '1.0'
        kwargs['format'] = 'json'
        if '_files' in kwargs:
            _files = kwargs['_files']
            del kwargs['_files']
        else:
            _files = {}
        response = self._http_post(RENREN_API_SERVER, kwargs, files=_files)


        if type(response) is not list and "error_code" in response:
            logger.warning(response["error_msg"])
            raise RenrenAPIError(response["error_code"], response["error_msg"])
        return response


    def auth_first(self):
        '''
        docstring placeholder
        '''

        args = {"client_id": self.jsonconf.app_key,
                "redirect_uri": self.auth_info.callback_url}
        args["response_type"] = "code"
        args["scope"] = " ".join(["read_user_feed",
                                  "read_user_status",
                                  "read_user_blog",
                                  "status_update",
                                  "publish_comment",
                                  "publish_blog",
                                  "photo_upload"])

        url = RENREN_AUTHORIZATION_URI + "?" + self._urlencode(args)
        self.request_url(url)

    def auth_second(self):
        '''
        docstring placeholder
        '''

        try:
            url = self.fetch_code()
            self.token = self._parse_code(url)
            args = dict(client_id=self.jsonconf.app_key, redirect_uri = self.auth_info.callback_url)
            args["client_secret"] = self.jsonconf.app_secret
            args["code"] = self.token.code
            args["grant_type"] = "authorization_code"
            self.token.update(self._http_get(RENREN_ACCESS_TOKEN_URI, args))
            self.token.expires_in = self.token.expires_in + self.time()
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def auth(self):
        '''
        docstring placeholder
        '''

        if self.get_saved_token():
            return

        logger.info("Try to authenticate '%s' using OAuth2", self.jsonconf.channel_name)
        self.auth_first()
        self.auth_second()
        if not self.token:
            return False
        self.save_token()
        logger.debug("Authorized! access token is " + str(self.token))
        logger.info("Channel '%s' is authorized", self.jsonconf.channel_name)

    def need_auth(self):
        return True

    @require_authed
    def home_timeline(self, count=20, **kwargs):
        #FIXME: automatic paging for count > 100
        ttype='10,11,20,21,22,23,30,31,32,33,34,35,36,40,41,50,51,52,53,54,55'
        if 'type' in kwargs:
            ttype = kwargs['type']
        try:
            jsonlist = self.renren_request(
                method="feed.get",
                page=1,
                count=count,
                type=ttype,
            )
        except RenrenAPIError, e:
            logger.warning("RenrenAPIError, %s", e)
            return snstype.MessageList()

        statuslist = snstype.MessageList()
        for j in jsonlist:
            try:
                statuslist.append(self.Message(
                    j,
                    platform = self.jsonconf['platform'],
                    channel = self.jsonconf['channel_name']
                ))
            except Exception, e:
                logger.warning("Catch exception: %s", e)

        logger.info("Read %d statuses from '%s'", len(statuslist), self.jsonconf['channel_name'])
        return statuslist

    def _update_status(self, text):
        try:
            self.renren_request(
                method='status.set',
                status = text
            )
            return BooleanWrappedData(True)
        except:
            return BooleanWrappedData(False, {
                'errors': ['PLATFORM_'],
            })


    def _update_blog(self, text, title):
        try:
            self.renren_request(
                method='blog.addBlog',
                title=title,
                content=text
            )
            return BooleanWrappedData(True)
        except:
            return BooleanWrappedData(False, {
                'errors': ['PLATFORM_'],
            })


    def _update_share_link(self, text, link):
        try:
            self.renren_request(
                method='share.share',
                type='6',
                url=link,
                comment=text
            )
            return BooleanWrappedData(True)
        except:
            return    BooleanWrappedData(False, {
                'errors': ['PLATFORM_']
            })

    def _update_photo(self, text, pic):
        try:
            self.renren_request(
                method='photos.upload',
                caption=text,
                _files={'upload': ('%d.jpg' % int(time.time()), pic)}
            )
            return BooleanWrappedData(True)
        except:
            return BooleanWrappedData(False, {
                'errors': ['PLATFORM_'],
            })

    def _dummy_update(self, text, **kwargs):
        return False

    @require_authed
    def update(self, text, **kwargs):
        coder= int(''.join(map(lambda t: str(int(t)),
                               [
                                   'title' in kwargs,
                                   'link' in kwargs,
                                   'pic' in kwargs
                               ][::-1])
                           ))
        try:
            update_what = {
                0: self._update_status,
                1: self._update_blog,
                10: self._update_share_link,
                100: self._update_photo
            }[coder]
        except:
            return BooleanWrappedData(False, {
                'errors' : ['SNSAPI_NOT_SUPPORTED'],
            })
        return update_what(text, **kwargs)

    @require_authed
    def reply(self, statusId, text):
        #NOTE: you can mix API1 and API2.
        #NOTE: API2 is more better on comment
        res = None
        try:
            if statusId.feed_type == 'STATUS':
                res = self.renren_request(
                    method='status.addComment',
                    status_id=statusId.status_id,
                    owner_id=statusId.source_user_id,
                    content=text
                )
            elif statusId.feed_type == 'SHARE':
                res = self.renren_request(
                    method='share.addComment',
                    share_id=statusId.status_id,
                    user_id=statusId.source_user_id,
                    content=text
                )
            elif statusId.feed_type == 'BLOG':
                res = self.renren_request(
                    method='blog.addComment',
                    id=statusId.status_id,
                    #FIXME: page_id, uid
                    uid=statusId.source_user_id,
                    content=text
                )
            elif statusId.feed_type == 'PHOTO':
                res = self.renren_request(
                    method='photos.addComment',
                    uid=statusId.source_user_id,
                    content=text,
                    #FIXME: aid, pid
                    pid=statusId.status_id
                )
            else:
                return BooleanWrappedData(False, {
                    'errors' : ['SNSAPI_NOT_SUPPORTED'],
                })
        except:
            return BooleanWrappedData(False, {
                'errors': ['PLATFORM_'],
            })
        if res:
            return BooleanWrappedData(True)
        else:
            return BooleanWrappedData(False, {
                'errors' : ['PLATFORM_'],
            })

    @require_authed
    def forward(self, message, text):
        res = None
        try:
            if message.ID.feed_type == 'STATUS':
                res = self.renren_request(
                    method='status.forward',
                    status=text,
                    forward_id=message.ID.status_id,
                    forward_owner=message.ID.source_user_id,
                )
            elif message.ID.feed_type != 'OTHER':
                res = self.renren_request(
                    method='share.share',
                    type=str({
                        'BLOG': 1,
                        'PHOTO': 2,
                        'SHARE': 20
                    }[message.parsed.feed_type]),
                    ugc_id=message.ID.status_id,
                    user_id=message.ID.source_user_id,
                    comment=text
                )
            else:
                return BooleanWrappedData(False, {
                    'errors' : ['SNSAPI_NOT_SUPPORTED'],
                })
        except Exception as e:
            logger.warning('Catch exception: %s', e)
            return BooleanWrappedData(False, {
                'errors': ['PLATFORM_'],
            })
        if res:
            return BooleanWrappedData(True)
        else:
            return BooleanWrappedData(False, {
                'errors' : ['PLATFORM_'],
            })


class RenrenStatus(RenrenFeed):
    Message = RenrenStatusMessage

    def __init__(self, channel=None):
        super(RenrenStatus, self).__init__(channel)

    @staticmethod
    def new_channel(full=False):
        c = RenrenFeed.new_channel(full)
        c['platform'] = 'RenrenStatus'
        return c

    @require_authed
    def home_timeline(self, count=20):
        return RenrenFeed.home_timeline(self, count, type='10,11')

    @require_authed
    def update(self, text):
        return RenrenFeed._update_status(self, text)


class RenrenBlog(RenrenFeed):
    Message = RenrenBlogMessage

    def __init__(self, channel=None):
        super(RenrenBlog, self).__init__(channel)

    @staticmethod
    def new_channel(full=False):
        c = RenrenFeed.new_channel(full)
        c['platform'] = 'RenrenBlog'
        return c

    @require_authed
    def home_timeline(self, count=20):
        return RenrenFeed.home_timeline(self, count, type='20,22')

    @require_authed
    def update(self, text, title=None):
        if not title:
            title = text.split('\n')[0]
            return RenrenFeed._update_blog(self, text, title)

class RenrenPhoto(RenrenFeed):
    Message = RenrenPhotoMessage

    def __init__(self, channel=None):
        super(RenrenPhoto, self).__init__(channel)

    @staticmethod
    def new_channel(full=False):
        c = RenrenFeed.new_channel(full)
        c['platform'] = 'RenrenPhoto'
        return c

    @require_authed
    def home_timeline(self, count=20):
        return RenrenFeed.home_timeline(self, count, type='30,31')

    @require_authed
    def update(self, text, pic=None):
        return self._update_photo(text, pic)

class RenrenShare(RenrenFeed):
    Message = RenrenShareMessage

    def __init__(self, channel=None):
        super(RenrenShare, self).__init__(channel)

    @staticmethod
    def new_channel(full=False):
        c = RenrenFeed.new_channel(full)
        c['platform'] = 'RenrenShare'
        return c

    @require_authed
    def home_timeline(self, count=20):
        return RenrenFeed.home_timeline(self, count, type='21,23,32,33,36,50,51,52,53,54,55')

    @require_authed
    def update(self, text, link=None):
        if not link:
            link = text
            return RenrenFeed._update_share_link(self, text, link)


class RenrenStatusDirectMessage(snstype.Message):
    platform = "RenrenStatusDirect"

    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        self.ID.status_id = dct['status_id']
        self.ID.source_user_id = dct['uid']
        self.ID.feed_type = 'STATUS'

        self.parsed.userid = str(dct['uid'])
        self.parsed.username = dct['name']
        self.parsed.time = utils.str2utc(dct['time'], " +08:00")
        self.parsed.text = dct['message']

class RenrenStatusDirect(RenrenFeed):
    Message = RenrenStatusDirectMessage

    def __init__(self, channel=None):
        super(RenrenStatusDirect, self).__init__(channel)

    @staticmethod
    def new_channel(full=False):
        c = RenrenFeed.new_channel(full)
        c['platform'] = 'RenrenStatusDirect'
        c['friend_list'] = [
                    {
                    "username": "Name",
                    "userid": "ID"
                    }
                ]
        return c

    @require_authed
    def update(self, text):
        return RenrenFeed._update_status(self, text)

    def _get_user_status_list(self, count, userid, username):
        try:
            jsonlist = self.renren_request(
                method="status.gets",
                page=1,
                count=count,
                uid = userid,
            )
        except RenrenAPIError, e:
            logger.warning("RenrenAPIError, %s", e)
            return snstype.MessageList()

        statuslist = snstype.MessageList()
        for j in jsonlist:
            try:
                j['name'] = username
                statuslist.append(self.Message(
                    j,
                    platform = self.jsonconf['platform'],
                    channel = self.jsonconf['channel_name']
                ))
            except Exception, e:
                logger.warning("Catch exception: %s", e)
        return statuslist

    @require_authed
    def home_timeline(self, count=20):
        '''
        Return count ``Message`` for each uid configured.

        Configure 'friend_list' in your ``channel.json`` first.
        Or, it returns your own status list by default.
        '''
        statuslist = snstype.MessageList()
        for user in self.jsonconf['friend_list']:
            userid = user['userid']
            username = user['username']
            statuslist.extend(self._get_user_status_list(count, userid, username))
        logger.info("Read %d statuses from '%s'", len(statuslist), self.jsonconf['channel_name'])
        return statuslist

########NEW FILE########
__FILENAME__ = sina_wap
#-*- encoding: utf-8 -*-

'''
Sina Weibo Wap client
'''

if __name__ == '__main__':
    import sys
    import urllib2
    import urllib
    import re
    import lxml.html, lxml.etree
    import time
    sys.path.append('..')
    from snslog import SNSLog as logger
    from snsbase import SNSBase, require_authed
    import snstype
else:
    import urllib2
    import urllib
    import re
    import lxml.html, lxml.etree
    import time
    from ..snslog import SNSLog as logger
    from ..snsbase import SNSBase, require_authed
    from .. import snstype


logger.debug("%s plugged!", __file__)


class SinaWeiboWapStatusMessage(snstype.Message):
    platform = 'SinaWeiboWapStatus'
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        #TODO:
        #    Check whether the fields conform to snsapi convention.
        #    http://snsapi.ie.cuhk.edu.hk/doc/snsapi.html#module-snsapi.snstype
        self.parsed.time = dct['time']
        if u'分钟前' in self.parsed.time:
            self.parsed.time = time.time() - 60 * \
                    int(self.parsed.time[0:self.parsed.time.find(u'分钟前')])
            pp = time.localtime(self.parsed.time)
            # FIXME:
            # approximate time aligned to minute
            # if your request is at different minute from
            # the server's response. You might get ONE minute's
            # difference.
            if pp.tm_sec > 0:
                self.parsed.time = 60 + \
                        time.mktime((
                            pp.tm_year,
                            pp.tm_mon,
                            pp.tm_mday,
                            pp.tm_hour,
                            pp.tm_min,
                            0,
                            pp.tm_wday,
                            pp.tm_yday,
                            pp.tm_isdst))
        elif u'今天' in self.parsed.time:
            minute, second = map(int, re.search('([0-9]*):([0-9]*)', self.parsed.time).groups())
            today = time.gmtime(time.time() + 28800)
            self.parsed.time = time.mktime(time.strptime("%04d-%02d-%02d %02d:%02d" % (
                today.tm_year,
                today.tm_mon,
                today.tm_mday,
                minute,
                second), '%Y-%m-%d %H:%M')) - time.altzone - 28800
        else:
            minute, second = map(int, re.search('([0-9]*):([0-9]*)', self.parsed.time).groups())
            month, day = map(int, re.search(u'([0-9]*)月([0-9]*)', self.parsed.time).groups())
            today = time.gmtime(time.time() + 28800)
            self.parsed.time = time.mktime(time.strptime("%04d-%02d-%02d %02d:%02d" % (
                today.tm_year,
                month,
                day,
                minute,
                second), '%Y-%m-%d %H:%M')) - time.altzone - 28800

        self.parsed.username = dct['author']
        self.parsed.text = dct['text']
        self.parsed.comments_count = dct['comments_count']
        self.parsed.reposts_count = dct['reposts_count']
        self.parsed.userid = dct['uid']
        if 'orig' in dct:
            self.parsed.has_orig = True
            self.parsed.username_origin = dct['orig']['author']
            self.parsed.text_orig = dct['orig']['text']
            self.parsed.comments_count_orig = dct['orig']['comments_count']
            self.parsed.reposts_count_orig = dct['orig']['reposts_count']
            self.parsed.text = self.parsed.text + '//@' + self.parsed.username_origin + ':' + self.parsed.text_orig
        else:
            self.parsed.has_orig = False
        self.ID.id = dct['id']
        if 'attachment_img' in dct:
            self.parsed.attachments.append({
                'type': 'picture',
                'format': ['link'],
                'data': dct['attachment_img']
                })


class SinaWeiboWapStatus(SNSBase):
    Message = SinaWeiboWapStatusMessage

    def __init__(self, channel = None):
        super(SinaWeiboWapStatus, self).__init__(channel)
        assert channel['auth_by'] in ['userpass', 'gsid']
        self.platform = self.__class__.__name__
        self.Message.platform = self.platform


    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)
        c['platform'] = 'SinaWeiboWapStatus'
        c['uidtype'] = 'path'
        c['auth_by'] = 'userpass'
        c['auth_info'] = {
            'save_token_file': "(default)",
            'login_username': '',
            'login_password': ''

        }
        return c

    def _process_req(self, req):
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.151 Safari/535.19')
        return req


    def _get_weibo_homepage(self, token = None):
        if token:
            gsid = token['gsid']
        elif self.token and 'gsid' in self.token:
            gsid = self.token['gsid']
        else:
            gsid =  ''
        req = urllib2.Request('http://weibo.cn/?gsid=' + gsid)
        req = self._process_req(req)
        m = urllib2.urlopen(req, timeout = 10).read()
        return m

    def auth(self):
        if self.get_saved_token():
            return self.is_authed()
        if self.jsonconf['auth_by'] == 'gsid':
            self.token['gsid'] = self.jsonconf['gsid']
        elif self.jsonconf['auth_by'] == 'userpass':
            show_verification = False
            verification_code = ''
            req = urllib2.Request('http://login.weibo.cn/login/?vt=4&revalid=2&ns=1&pt=1')
            req = self._process_req(req)
            response = urllib2.urlopen(req, timeout = 10)
            p = response.read()
            while True:
                req = urllib2.Request('http://login.weibo.cn/login/?rand=' + (re.search("rand=([0-9]*)", p).group(1) )+ '&backURL=http%3A%2F%2Fweibo.cn&backTitle=%E6%89%8B%E6%9C%BA%E6%96%B0%E6%B5%AA%E7%BD%91&vt=4&revalid=2&ns=1')
                data = {'mobile': self.auth_info['login_username'],
                        'password_%s' % (re.search('name="password_([0-9]*)"', p).group(1)): self.auth_info['login_password'],
                        'backURL': 'http%3A%2F%2Fweibo.cn',
                        'backTitle': '手机新浪网',
                        'tryCount': '',
                        'vk': re.search('name="vk" value="([^"]*)"', p).group(1),
                        'submit' : '登录'}
                if show_verification:
                    data['code'] = verification_code
                    data['capId'] = re.search('name="capId" value="([^"]*)"', p).group(1)
                    show_verification = False
                req = self._process_req(req)
                data = urllib.urlencode(data)
                response = urllib2.urlopen(req, data, timeout = 10)
                p = response.read()
                final_url = response.geturl()
                if 'newlogin' in final_url:
                    final_gsid = re.search('g=([^&]*)', final_url).group(1)
                    self.token = {'gsid' :  final_gsid}
                    break
                elif '验证码' in p:
                    err_msg = re.search('class="me">([^>]*)<', p).group(1)
                    if '请输入图片中的字符' in p:
                        captcha_url = re.search(r'"([^"]*captcha[^"]*)', p).group(1)
                        show_verification = True
                        import Image
                        import StringIO
                        ss = urllib2.urlopen(captcha_url, timeout=10).read()
                        sss = StringIO.StringIO(ss)
                        img = Image.open(sss)
                        img.show()
                        verification_code = raw_input(err_msg)
                else:
                    err_msg = re.search('class="me">([^>]*)<', p).group(1)
                    logger.warning(err_msg)
                    break
        else:
            return False
        res = self.is_authed()
        if res:
            self.save_token()
        return res

    def _is_authed(self, token = None):
        '''
        ``is_authed`` is an ``SNSBase`` general method.
        It invokes platform specific ``expire_after`` to
        determine whether this platform is authed.

        Rename this method.
        '''
        return '<input type="submit" value="发布" />' in self._get_weibo_homepage(token)

    def expire_after(self, token = None):
        if self._is_authed(token):
            return -1
        else:
            return 0

    def _get_uid_by_pageurl(self, url, type='num'):
        if url[0:len('http://weibo.cn')] == 'http://weibo.cn':
            url = url[len('http://weibo.cn'):]
        if type == 'num':
            if re.search('\/u\/[0-9]*', url):
                return re.search('\/u\/([0-9]*)', url).group(1)
            req = urllib2.Request('http://weibo.cn' + url)
            req = self._process_req(req)
            m = urllib2.urlopen(req, timeout = 10).read()
            return re.search(r'\/([0-9]*)\/info', m).group(1)
        elif type == 'path':
            return re.search(r'\/([^?]*)\?', url).group(1)

    def _get_weibo(self, page = 1):
        #FIXME: 获取转发和评论数应该修改为分析DOM而不是正则表达式（以免与内容重复）
        #FIXME: 对于转发的微博，原微博信息不足
        req = urllib2.Request('http://weibo.cn/?gsid=' + self.token['gsid'] + '&page=%d' % (page))
        req = self._process_req(req)
        m = urllib2.urlopen(req, timeout = 10).read()
        h = lxml.html.fromstring(m)
        weibos = []
        for i in h.find_class('c'):
            try:
                if i.get('id') and i.get('id')[0:2] == 'M_':
                    weibo = None
                    if i.find_class('cmt'): # 转发微博
                        weibo = {
                                'uid' : self._get_uid_by_pageurl(i.find_class('nk')[0].attrib['href'], self.jsonconf['uidtype']),
                                'author' : i.find_class('nk')[0].text,
                                'id': i.get('id')[2:],
                                'time': i.find_class('ct')[0].text.encode('utf-8').strip(' ').split(' ')[0].decode('utf-8'),
                                'text' : None,
                                'orig' : {
                                    'text': unicode(i.find_class('ctt')[0].text_content()),
                                    'author': re.search(u'转发了\xa0(.*)\xa0的微博', i.find_class('cmt')[0].text_content()).group(1),
                                    'comments_count' : 0,
                                    'reposts_count' : 0
                                    },
                                'comments_count' : 0,
                                'reposts_count' : 0
                                }
                        parent = i.find_class('cmt')[-1].getparent()
                        retweet_reason = re.sub(r'转发理由:(.*)赞\[[0-9]*\] 转发\[[0-9]*\] 评论\[[0-9]*\] 收藏.*$', r'\1', parent.text_content().encode('utf-8'))
                        weibo['text'] = retweet_reason.decode('utf-8')
                        zf = re.search(r'赞\[([0-9]*)\] 转发\[([0-9]*)\] 评论\[([0-9]*)\]', parent.text_content().encode('utf-8'))
                        if zf:
                            weibo['comments_count'] = int(zf.group(3))
                            weibo['reposts_count'] = int(zf.group(2))
                        zf = re.search(r'赞\[([0-9]*)\] 原文转发\[([0-9]*)\] 原文评论\[([0-9]*)\]', i.text_content().encode('utf-8'))
                        if zf:
                            weibo['orig']['comments_count'] = int(zf.group(3))
                            weibo['orig']['reposts_count'] = int(zf.group(2))
                    else:
                        weibo = {'author' : i.find_class('nk')[0].text,
                                'uid' : self._get_uid_by_pageurl(i.find_class('nk')[0].attrib['href'], self.jsonconf['uidtype']),
                                'text': i.find_class('ctt')[0].text_content()[1:],
                                'id': i.get('id')[2:],
                                'time': i.find_class('ct')[0].text.encode('utf-8').strip(' ').split(' ')[0].decode('utf-8')
                                }
                        zf = re.search(r'赞\[([0-9]*)\] 转发\[([0-9]*)\] 评论\[([0-9]*)\]', i.text_content().encode('utf-8'))
                        if zf:
                            weibo['comments_count'] = int(zf.group(3))
                            weibo['reposts_count'] = int(zf.group(2))
                    if i.find_class('ib'):
                        #FIXME: Still not able to process a collections of pictures
                        weibo['attachment_img'] = i.find_class('ib')[0].get('src').replace('wap128', 'woriginal')
                    weibos.append(weibo)
            except Exception, e:
                logger.warning("Catch exception: %s" % (str(e)))
        statuslist = snstype.MessageList()
        for i in weibos:
            statuslist.append(self.Message(i, platform = self.jsonconf['platform'],
                channel = self.jsonconf['channel_name']))
        return statuslist


    @require_authed
    def home_timeline(self, count = 20):
        all_weibo = snstype.MessageList()
        page = 1
        while len(all_weibo) < count:
            weibos = self._get_weibo(page)
            all_weibo += weibos[0:min(len(weibos), count - len(all_weibo))]
            page += 1
        return all_weibo

    @require_authed
    def update(self, text):
        homepage = self._get_weibo_homepage()
        m = re.search('<form action="(/mblog/sendmblog?[^"]*)" accept-charset="UTF-8" method="post">', homepage).group(1)
        data = {'rl' : '0', 'content' : self._unicode_encode(text)}
        data = urllib.urlencode(data)
        req = urllib2.Request('http://weibo.cn' + m.replace('&amp;', '&'))
        req = self._process_req(req)
        opener = urllib2.build_opener()
        response = opener.open(req, data, timeout = 10)
        t = response.read()
        if '<div class="ps">发布成功' in t:
            return True
        else:
            return False

    @require_authed
    def reply(self, statusID, text):
        id = statusID.id
        url = 'http://weibo.cn/comment/%s?gsid=%s' % (id, self.token['gsid'])
        req = self._process_req(urllib2.Request(url))
        res = urllib2.build_opener().open(req, timeout = 10).read()
        addcomment_url = 'http://weibo.cn' +  \
                re.search('<form action="(/comments/addcomment?[^"]*)" method="post">', res).group(1).replace('&amp;', '&')
        srcuid = re.search('<input type="hidden" name="srcuid" value="([^"]*)" />', res).group(1)
        rl = '1'
        req = self._process_req(urllib2.Request(addcomment_url))
        opener = urllib2.build_opener()
        data = urllib.urlencode(
                {'rl' : rl, 'srcuid' : srcuid, 'id': id, 'content' : self._unicode_encode(text)}
                )
        response = opener.open(req, data, timeout = 10)
        t = response.read()
        return '<div class="ps">评论成功!</div>' in t

if __name__ == '__main__':
    try:
        # Write a 'channel.json' file in SNSAPI format with required information
        # OR, (see 'except' section)
        import json
        sina_conf = json.load(open('channel.json'))[0]
        print sina_conf
    except IOError:
        # Else, we let you input from console
        import getpass
        sina_conf = SinaWeiboWapStatus.new_channel()
        sina_conf['channel_name'] = 'demo_channel'
        sina_conf['auth_by'] = 'userpass'
        print 'Username:' ,
        _username = raw_input().strip()
        _password = getpass.getpass()
        sina_conf['auth_info'] = {
                'login_username': _username,
                'login_password': _password
                }
        sina_conf['uidtype'] = 'path'
        print sina_conf

    sina = SinaWeiboWapStatus(sina_conf)
    print sina.auth()
    # Too slow.. change the demo to 2 msgs
    ht = sina.home_timeline(2)
    #print ht
    c = 0
    for i in ht:
        c += 1
        print c, i.ID.id, i.parsed.username, i.parsed.userid, i.parsed.time, i.parsed.text, i.parsed.comments_count, i.parsed.reposts_count,
        if i.parsed.has_orig:
            print i.parsed.orig_text, i.parsed.orig_comments_count, i.parsed.orig_reposts_count
        else:
            print ''

########NEW FILE########
__FILENAME__ = sqlite
#-*- encoding: utf-8 -*-

'''
sqlite

We use sqlite3 as the backend.
'''

from ..snslog import SNSLog
logger = SNSLog
from ..snsbase import SNSBase
from .. import snstype
from ..utils import console_output
from .. import utils

import sqlite3

logger.debug("%s plugged!", __file__)

class SQLiteMessage(snstype.Message):
    platform = "SQLite"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        self.parsed = dct

class SQLite(SNSBase):

    Message = SQLiteMessage

    def __init__(self, channel = None):
        super(SQLite, self).__init__(channel)
        self.platform = self.__class__.__name__

        self.con = None

    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['platform'] = 'SQLite'
        c['url'] = ''
        return c

    def read_channel(self, channel):
        super(SQLite, self).read_channel(channel)

        if not 'username' in self.jsonconf:
            self.jsonconf['username'] = 'snsapi_sqlite_username'
        if not 'userid' in self.jsonconf:
            self.jsonconf['userid'] = 'snsapi_sqlite_userid'

    def _create_schema(self):
        cur = self.con.cursor()

        try:
            cur.execute("create table meta (time integer, path text)")
            cur.execute("insert into meta values (?,?)", (int(self.time()), self.jsonconf.url))
            self.con.commit()
        except sqlite3.OperationalError, e:
            if e.message == "table meta already exists":
                return
            else:
                raise e

        cur.execute("""
        CREATE TABLE message (
        id INTEGER PRIMARY KEY,
        time INTEGER,
        text TEXT,
        userid TEXT,
        username TEXT,
        mid TEXT,
        digest TEXT,
        digest_parsed TEXT,
        digest_full TEXT,
        parsed TEXT,
        full TEXT
        )
        """)
        self.con.commit()

    def _connect(self):
        '''
        Connect to SQLite3 database and create cursor.
        Also initialize the schema if necessary.

        '''
        url = self.jsonconf.url
        self.con = sqlite3.connect(url, check_same_thread = False)
        self.con.isolation_level = None
        self._create_schema()

    def auth(self):
        '''
        SQLite3 do not need auth.

        We define the "auth" procedure to be:

           * Close previously connected database.
           * Reconnect database using current config.

        '''
        logger.info("SQLite3 channel do not need auth. Try connecting to DB...")
        if self.con:
            self.con.close()
            self.con = None
        self._connect()

    def auth_first(self):
        logger.info("%s platform do not need auth_first!", self.platform)

    def auth_second(self):
        logger.info("%s platform do not need auth_second!", self.platform)

    def home_timeline(self, count = 20):
        message_list = snstype.MessageList()

        try:
            cur = self.con.cursor()
            r = cur.execute('''
            SELECT time,userid,username,text FROM message
            ORDER BY time DESC LIMIT ?
            ''', (count,))
            for m in r:
                message_list.append(self.Message({
                        'time':m[0],
                        'userid':m[1],
                        'username':m[2],
                        'text':m[3]
                        },\
                        platform = self.jsonconf['platform'],\
                        channel = self.jsonconf['channel_name']\
                        ))
        except Exception, e:
            logger.warning("Catch expection: %s", e)

        return message_list

    def _update_text(self, text):
        m = self.Message({\
                'time':int(self.time()),
                'userid':self.jsonconf['userid'],
                'username':self.jsonconf['username'],
                'text':text
                }, \
                platform = self.jsonconf['platform'],\
                channel = self.jsonconf['channel_name']\
                )
        return self._update_message(m)

    def _update_message(self, message):
        cur = self.con.cursor()

        try:
            cur.execute('''
            INSERT INTO message(time,userid,username,text,mid,digest,digest_parsed,digest_full,parsed,full)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', (\
                    message.parsed.time,\
                    message.parsed.userid,\
                    message.parsed.username,\
                    message.parsed.text,\
                    str(message.ID),\
                    message.digest(),\
                    message.digest_parsed(),\
                    message.digest_full(),\
                    message.dump_parsed(),
                    message.dump_full()
                    ))
            return True
        except Exception, e:
            logger.warning("failed: %s", str(e))
            return False

    def update(self, text):
        if isinstance(text, str):
            return self._update_text(text)
        elif isinstance(text, unicode):
            return self._update_text(text)
        elif isinstance(text, snstype.Message):
            return self._update_message(text)
        else:
            logger.warning('unknown type: %s', type(text))
            return False

    def expire_after(self, token = None):
        # This platform does not have token expire issue.
        return -1

########NEW FILE########
__FILENAME__ = twitter
#-*- encoding: utf-8 -*-

'''
twitter

We use python-twitter as the backend at present.
It should be changed to invoke REST API directly later.
'''

from ..snslog import SNSLog
logger = SNSLog
from ..snsbase import SNSBase
from .. import snstype
from ..utils import console_output
from .. import utils

from ..third import twitter

logger.debug("%s plugged!", __file__)

class TwitterStatusMessage(snstype.Message):
    platform = "TwitterStatus"
    def parse(self):
        self.ID.platform = self.platform
        self._parse(self.raw)

    def _parse(self, dct):
        self.ID.id = dct['id']

        self.parsed.time = utils.str2utc(dct['created_at'])
        #NOTE:
        #   * dct['user']['screen_name'] is the path part of user's profile URL.
        #   It is actually in a position of an id. You should @ this string in
        #   order to mention someone.
        #   * dct['user']['name'] is actually a nick name you can set. It's not
        #   permanent.
        self.parsed.username = dct['user']['screen_name']
        self.parsed.userid = dct['user']['id']
        self.parsed.text = dct['text']


class TwitterStatus(SNSBase):

    Message = TwitterStatusMessage

    def __init__(self, channel = None):
        super(TwitterStatus, self).__init__(channel)
        self.platform = self.__class__.__name__

        self.api = twitter.Api(consumer_key=self.jsonconf['app_key'],\
                consumer_secret=self.jsonconf['app_secret'],\
                access_token_key=self.jsonconf['access_key'],\
                access_token_secret=self.jsonconf['access_secret'])


    @staticmethod
    def new_channel(full = False):
        c = SNSBase.new_channel(full)

        c['platform'] = 'TwitterStatus'
        c['app_key'] = ''
        c['app_secret'] = ''
        c['access_key'] = ''
        c['access_secret'] = ''

        return c

    def read_channel(self, channel):
        super(TwitterStatus, self).read_channel(channel)
        self.jsonconf['text_length_limit'] = 140

    def auth(self):
        logger.info("Current implementation of Twitter does not use auth!")

    def home_timeline(self, count = 20):
        '''
        NOTE: this does not include your re-tweeted statuses.
        It's another interface to get re-tweeted status on Tiwtter.
        We'd better save a call.
        Deprecate the use of retweets.
        See reply and forward of this platform for more info.
        '''
        status_list = snstype.MessageList()
        try:
            statuses = self.api.GetHomeTimeline(count = count)
            for s in statuses:
                status_list.append(self.Message(s.AsDict(),\
                        self.jsonconf['platform'],\
                        self.jsonconf['channel_name']))
            logger.info("Read %d statuses from '%s'", len(status_list), self.jsonconf['channel_name'])
        except Exception, e:
            logger.warning("Catch expection: %s", e)
        return status_list

    def update(self, text):
        text = self._cat(self.jsonconf['text_length_limit'], [(text, 1)])
        try:
            status = self.api.PostUpdate(text)
            #TODO:
            #     Find better indicator for status update success
            if status:
                return True
            else:
                return False
        except Exception, e:
            logger.warning('update Twitter failed: %s', str(e))
            return False

    def reply(self, statusID, text):
        text = self._cat(self.jsonconf['text_length_limit'], [(text, 1)])
        try:
            status = self.api.PostUpdate(text,
                                         in_reply_to_status_id=statusID.id)
            #TODO:
            #     Find better indicator for status update success
            if status:
                return True
            else:
                return False
        except Exception, e:
            logger.warning('update Twitter failed: %s', str(e))
            return False

    def forward(self, message, text):
        if not message.platform == self.platform:
            return super(TwitterStatus, self).forward(message, text)
        else:
            decorated_text = self._cat(self.jsonconf['text_length_limit'],
                    [(text, 2),
                     ('@' + message.parsed.username + ' ' + message.parsed.text, 1)],
                    delim='//')
            try:
                status = self.api.PostUpdate(decorated_text)
                #TODO:
                #     Find better indicator for status update success
                if status:
                    return True
                else:
                    return False
            except Exception, e:
                logger.warning('update Twitter failed: %s', str(e))
                return False

    def expire_after(self, token = None):
        # This platform does not have token expire issue.
        return -1

class TwitterSearchMessage(TwitterStatusMessage):
    platform = "TwitterSearch"

class TwitterSearch(TwitterStatus):
    Message = TwitterSearchMessage

    @staticmethod
    def new_channel(full=False):
        c = TwitterStatus.new_channel(full)
        c['platform'] = 'TwitterSearch'
        c['term'] = 'snsapi'
        c['include_entities'] = True
        return c

    def __init__(self, channel = None):
        super(TwitterSearch, self).__init__(channel)
        self.platform = self.__class__.__name__

        self.api = twitter.Api(consumer_key=self.jsonconf['app_key'],\
                consumer_secret=self.jsonconf['app_secret'],\
                access_token_key=self.jsonconf['access_key'],\
                access_token_secret=self.jsonconf['access_secret'])

    def home_timeline(self, count = 100):
        status_list = snstype.MessageList()
        try:
            #statuses = self.api.GetHomeTimeline(count = count)
            statuses = self.api.GetSearch(term=self.jsonconf['term'],
                            include_entities=self.jsonconf['include_entities'],
                            count=count)
            for s in statuses:
                status_list.append(self.Message(s.AsDict(),\
                        self.jsonconf['platform'],\
                        self.jsonconf['channel_name']))
            logger.info("Read %d statuses from '%s'", len(status_list), self.jsonconf['channel_name'])
        except Exception, e:
            logger.warning("Catch expection: %s", e)
        return status_list


########NEW FILE########
__FILENAME__ = snsbase
# -*- coding: utf-8 -*-

'''
snsapi base class.

All plugins are derived from this class.
It provides common authenticate and communicate methods.
'''

# === system imports ===
import webbrowser
from utils import json
import requests
from errors import snserror
import urllib
import urllib2
import urlparse
import subprocess
import functools

# === snsapi modules ===
from snsconf import SNSConf
import snstype
import utils
from snslog import SNSLog as logger

# === 3rd party modules ===
from third import oauth
oauth.logger = logger

def require_authed(func):
    '''
    A decorator to require auth before an operation

    '''
    @functools.wraps(func)
    def wrapper_require_authed(self, *al, **ad):
        if self.is_authed():
            return func(self, *al, **ad)
        else:
            logger.warning("Channel '%s' is not authed!", self.jsonconf['channel_name'])
            return
    doc_orig = func.__doc__ if func.__doc__ else ''
    doc_new = doc_orig + '\n        **NOTE: This method require authorization before invokation.**'
    wrapper_require_authed.__doc__ = doc_new
    return wrapper_require_authed


class SNSBase(object):
    def __init__(self, channel = None):

        self.token = None

        self.auth_info = snstype.AuthenticationInfo()
        self.__fetch_code_timeout = 2
        self.__fetch_code_max_try = 30

        # methods binding
        import time
        self.time = lambda : time.time()
        self.console_input = lambda : utils.console_input()
        self.console_output = lambda : utils.console_output()
        self._urlencode = lambda params : urllib.urlencode(params)

        # We can not init the auth client here.
        # As the base class, this part is first
        # executed. Not until we execute the derived
        # class, e.g. sina.py, can we get all the
        # information to init an auth client.
        self.auth_client = None

        if channel:
            self.read_channel(channel)

    def fetch_code(self):
        if self.auth_info.cmd_fetch_code == "(console_input)" :
            utils.console_output("Please input the whole url from Broswer's address bar:")
            return self.console_input().strip()
        elif self.auth_info.cmd_fetch_code == "(local_webserver)":
            try:
                self.httpd.handle_request()
                return "http://localhost%s" % self.httpd.query_path
            finally:
                del self.httpd
        elif self.auth_info.cmd_fetch_code == "(authproxy_username_password)":
            # Currently available for SinaWeibo.
            # Before using this method, please deploy one authproxy:
            #    * https://github.com/xuanqinanhai/weibo-simulator/
            # Or, you can use the official one:
            #    * https://snsapi.ie.cuhk.edu.hk/authproxy/auth.php
            # (Not recommended; only for test purpose; do not use in production)
            try:
                login_username = self.auth_info.login_username
                login_password = self.auth_info.login_password
                app_key = self.jsonconf.app_key
                app_secret = self.jsonconf.app_secret
                callback_url = self.auth_info.callback_url
                authproxy_url = self.auth_info.authproxy_url
                params = urllib.urlencode({'userid': login_username,
                    'password': login_password, 'app_key': app_key,
                    'app_secret': app_secret,'callback_uri': callback_url})
                req = urllib2.Request(url=authproxy_url, data=params);
                code = urllib2.urlopen(req).read()
                logger.debug("response from authproxy: %s", code)
                # Just to conform to previous SNSAPI convention
                return "http://snsapi.snsapi/?code=%s" % code
            except Exception, e:
                logger.warning("Catch exception: %s", e)
                raise snserror.auth.fetchcode
        elif self.auth_info.cmd_fetch_code == "(local_username_password)":
            # Currently available for SinaWeibo.
            # The platform must implement _fetch_code_local_username_password() method
            try:
                return self._fetch_code_local_username_password()
            except Exception, e:
                logger.warning("Catch exception: %s", e)
                raise snserror.auth.fetchcode
        else:  # Execute arbitrary command to fetch code
            import time
            cmd = "%s %s" % (self.auth_info.cmd_fetch_code, self.__last_request_time)
            logger.debug("fetch_code command is: %s", cmd)
            ret = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).stdout.readline().rstrip()
            tries = 1
            while str(ret) == "null" :
                tries += 1
                if tries > self.__fetch_code_max_try :
                    break
                time.sleep(self.__fetch_code_timeout)
                ret = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).stdout.read().rstrip()
            return ret

    def request_url(self, url):
        self._last_requested_url = url
        if self.auth_info.cmd_request_url == "(webbrowser)" :
            self.open_brower(url)
        elif self.auth_info.cmd_request_url == "(dummy)" :
            logger.debug("dummy method used for request_url(). Do nothing.")
            pass
        elif self.auth_info.cmd_request_url == "(console_output)" :
            utils.console_output(url)
        elif self.auth_info.cmd_request_url == "(local_webserver)+(webbrowser)" :
            host = self.auth_info.host
            port = self.auth_info.port
            from third.server import ClientRedirectServer
            from third.server import ClientRedirectHandler
            import socket
            try:
                self.httpd = ClientRedirectServer((host, port), ClientRedirectHandler)
                self.open_brower(url)
            except socket.error:
                raise snserror.auth
        else:  # Execute arbitrary command to request url
            self.__last_request_time = self.time()
            cmd = "%s '%s'" % (self.auth_info.cmd_request_url, url)
            logger.debug("request_url command is: %s", cmd)
            res = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).stdout.read().rstrip()
            logger.debug("request_url result is: %s", res)
            return

    # The init process is separated out and we
    # adopt an idle evaluation strategy for it.
    # This is because the two stages of OAtuh
    # should be context-free. We can not assume
    # calling the second is right after calling
    # the first. They can be done in different
    # invokation of the script. They can be done
    # on different servers.
    def __init_oauth2_client(self):
        if self.auth_client == None:
            try:
                self.auth_client = oauth.APIClient(self.jsonconf.app_key, \
                        self.jsonconf.app_secret, self.auth_info.callback_url, \
                        auth_url = self.auth_info.auth_url)
            except:
                logger.critical("auth_client init error")
                raise snserror.auth

    def _oauth2_first(self):
        '''
        The first stage of oauth.
        Generate auth url and request.
        '''
        self.__init_oauth2_client()

        url = self.auth_client.get_authorize_url()

        self.request_url(url)

    def _oauth2_second(self):
        '''
        The second stage of oauth.
        Fetch authenticated code.
        '''
        try:
            self.__init_oauth2_client()
            url = self.fetch_code()
            logger.debug("get url: %s", url)
            if str(url) == "null" :
                raise snserror.auth
            self.token = self._parse_code(url)
            self.token.update(self.auth_client.request_access_token(self.token.code))
            logger.debug("Authorized! access token is " + str(self.token))
            logger.info("Channel '%s' is authorized", self.jsonconf.channel_name)
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def oauth2(self):
        '''
        Authorizing using synchronized invocation of OAuth2.

        Users need to collect the code in the browser's address bar to this client.
        callback_url MUST be the same one you set when you apply for an app in openSNS platform.
        '''

        logger.info("Try to authenticate '%s' using OAuth2", self.jsonconf.channel_name)
        self._oauth2_first()
        self._oauth2_second()

    def auth(self):
        """
        General entry for authorization.
        It uses OAuth2 by default.
        """
        if self.get_saved_token():
            return
        self.oauth2()
        self.save_token()

    def auth_first(self):
        self._oauth2_first()

    def auth_second(self):
        try:
            self._oauth2_second()
        except Exception, e:
            logger.warning("Auth second fail. Catch exception: %s", e)
            self.token = None

    def open_brower(self, url):
        return webbrowser.open(url)

    def _parse_code(self, url):
        '''
        Parse code from a URL containing ``code=xx`` parameter

        :param url:
            contain code and optionally other parameters

        :return: JsonDict containing 'code' and **(optional) other URL parameters**

        '''
        return utils.JsonDict(urlparse.parse_qsl(urlparse.urlparse(url).query))

    def _token_filename(self):
        import os
        _dir_save = os.path.join(SNSConf.SNSAPI_DIR_STORAGE_ROOT, 'save')
        if not os.path.isdir(_dir_save):
            try:
                os.mkdir(_dir_save)
            except Exception as e:
                logger.warning("Create token save dir '.save' failed. Do not use token save function. %s", e)
                return None
        fname = self.auth_info.save_token_file
        if fname == "(default)":
            fname = os.path.join(_dir_save, self.jsonconf.channel_name + ".token.json")
        return fname

    def save_token(self):
        '''
        access token can be saved, it stays valid for a couple of days
        if successfully saved, invoke get_saved_token() to get it back
        '''
        fname = self._token_filename()
        # Do not save expired token (or None type token)
        if not fname is None and not self.is_expired():
            #TODO: encrypt access token
            token = utils.JsonObject(self.token)
            with open(fname,"w") as fp:
                json.dump(token, fp)

        return True

    def get_saved_token(self):
        try:
            fname = self._token_filename()
            if not fname is None:
                with open(fname, "r") as fp:
                    token = utils.JsonObject(json.load(fp))
                    # check expire time
                    if self.is_expired(token):
                        logger.debug("Saved Access token is expired, try to get one through sns.auth() :D")
                        return False
                    #TODO: decrypt token
                    self.token = token
            else:
                logger.debug("This channel is configured not to save token to file")
                return False

        except IOError:
            logger.debug("No access token saved, try to get one through sns.auth() :D")
            return False

        logger.info("Read saved token for '%s' successfully", self.jsonconf.channel_name)
        return True

    def expire_after(self, token = None):
        '''
        Calculate how long it is before token expire.

        :return:

           * >0: the time in seconds.
           * 0: has already expired.
           * -1: there is no token expire issue for this platform.

        '''
        if token == None:
            token = self.token
        if token:
            if token.expires_in - self.time() > 0:
                return token.expires_in - self.time()
            else:
                return 0
        else:
            # If there is no 'token' attribute available,
            # we regard it as token expired.
            return 0

    def is_expired(self, token = None):
        '''
        Check if the access token is expired.

        It delegates the logic to 'expire_after', which is a more
        formal module to use. This interface is kept for backward
        compatibility.
        '''
        #TODO:
        #    For those token that are near 0, we'd better inform
        #    the upper layer somehow. Or, it may just expire when
        #    the upper layer calls.
        if self.expire_after(token) == 0:
            return True
        else:
            # >0 (not expire) or ==-1 (no expire issue)
            return False

    def is_authed(self):
        return False if self.is_expired() else True

    def need_auth(self):
        '''
        Whether this platform requires two-stage authorization.

        Note:

           * Some platforms have authorization flow but we do not use it,
             e.g. Twitter, where we have a permanent key for developer
             They'll return False.
           * If your platform do need authorization, please override this
             method in your subclass.

        '''

        return False

    @staticmethod
    def new_channel(full = False):
        '''
        Return a JsonDict object containing channel configurations.

        :param full: Whether to return all config fields.

           * False: only returns essential fields.
           * True: returns all fields (essential + optional).

        '''

        c = utils.JsonDict()
        c['channel_name'] = 'new_channel_name'
        c['open'] = 'yes'

        if full:
            c['description'] = "A string for you to memorize this channel"
            # Comma separated lists of method names.
            # Enabled those methods in SNSPocket batch operation by default.
            # If all methods are enabled, remove this entry from your jsonconf.
            c['methods'] = ""
            # User identification may not be available on all platforms.
            # The following two optional fields can be used by Apps,
            # e.g. filtering out all the messages "I" posted.
            c['user_name'] = "Your Name on this channel (optional)"
            c['user_id'] = "Your ID on this channel (optional)"
            c['text_length_limit'] = None

        return c

    def read_channel(self, channel):
        self.jsonconf = utils.JsonDict(channel)

        if 'auth_info' in channel :
            self.auth_info.update(channel['auth_info'])
            self.auth_info.set_defaults()

        if not 'host' in self.auth_info:
            self.auth_info['host'] = 'localhost'
        if not 'port' in self.auth_info:
            self.auth_info['port'] = 12121

    def setup_oauth_key(self, app_key, app_secret):
        '''
        If you do not want to use read_channel, and want to set app_key on your own, here it is.
        '''
        self.jsonconf.app_key = app_key
        self.jsonconf.app_secret = app_secret

    def _http_get(self, baseurl, params={}, headers=None, json_parse=True):
        '''Use HTTP GET to request a JSON interface

        :param baseurl: Base URL before parameters

        :param params: a dict of params (can be unicode)

        :param headers: a dict of params (can be unicode)

        :param json_parse: whether to parse json (default True)

        :return:

           * Success: If json_parse is True, a dict of json structure
             is returned. Otherwise, the response of requests library
             is returned.
           * Failure: A warning is logged.
             If json_parse is True, {} is returned.
             Otherwise, the response of requests library is returned.
             (can be None)
        '''
        # Support unicode parameters.
        # We should encode them as exchanging stream (e.g. utf-8)
        # before URL encoding and issue HTTP requests.
        r= None
        try:
            for p in params:
                params[p] = self._unicode_encode(params[p])
            r = requests.get(baseurl, params=params, headers=headers)
            if json_parse:
                return r.json()
            else:
                return r
        except Exception, e:
            # Tolerate communication fault, like network failure.
            logger.warning("_http_get fail: %s", e)
            if json_parse:
                return {}
            else:
                return r

    def _http_post(self, baseurl, params={}, headers=None, files=None, json_parse=True):
        '''Use HTTP POST to request a JSON interface.

        See ``_http_get`` for more info.

        :param files {'name_in_form': (filename, data/file/)}
        '''
        r = None
        try:
            for p in params:
                params[p] = self._unicode_encode(params[p])
            r = requests.post(baseurl, data=params, headers=headers, files=files)
            if json_parse:
                return r.json()
            else:
                return r
        except Exception, e:
            logger.warning("_http_post fail: %s", e)
            if json_parse:
                return {}
            else:
                return r

    def _unicode_encode(self, s):
        """
        Detect if a string is unicode and encode as utf-8 if necessary
        """
        if isinstance(s, unicode):
            return s.encode('utf-8')
        else:
            return s

    def _expand_url(self, url):
        '''
        expand a shorten url

        :param url:
            The url will be expanded if it is a short url, or it will
            return the origin url string. url should contain the protocol
            like "http://"
        '''
        try:
            return self._http_get(url, json_parse=False).url
        except Exception, e:
            logger.warning("Unable to expand url: %s" % (str(e)))
            return url

    def _cat(self, length, text_list, delim = "||"):
        '''
        Concatenate strings.

        :param length:
            The output should not exceed length unicode characters.

        :param text_list:
            A list of text pieces. Each element is a tuple (text, priority).
            The _cat function will concatenate the texts using the order in
            text_list. If the output exceeds length, (part of) some texts
            will be cut according to the priority. The lower priority one
            tuple is assigned, the earlier it will be cut.

        '''
        if length:
            order_list = zip(range(0, len(text_list)), text_list)
            order_list.sort(key = lambda tup: tup[1][1])
            extra_length = sum([len(t[1][0]) for t in order_list]) \
                    - length + len(delim) * (len(order_list) - 1)

            output_list = []
            for (o, (t, p)) in order_list:
                if extra_length <= 0:
                    output_list.append((o, t, p))
                elif extra_length >= len(t):
                    extra_length -= len(t)
                else:
                    output_list.append((o, t[0:(len(t) - extra_length)], p))
                    extra_length = 0

            output_list.sort(key = lambda tup: tup[0])
            return delim.join([t for (o, t, p) in output_list])
        else:
            # length is None, meaning unlimited
            return delim.join([t for (t, p) in text_list])


    # Just a memo of possible methods

    # def home_timeline(self, count=20):
    #     '''Get home timeline
    #     get statuses of yours and your friends'
    #     @param count: number of statuses
    #     Always returns a list of Message objects. If errors happen in the
    #     requesting process, return an empty list. The plugin is recommended
    #     to log warning message for debug use.
    #     '''
    #     pass

    # def update(self, text):
    #     """docstring for update"""
    #     pass

    # def reply(self, mID, text):
    #     """docstring for reply"""
    #     pass

    @require_authed
    def forward(self, message, text):
        """
        A general forwarding implementation using update method.

        :param message:
            The Message object. The message you want to forward.

        :param text:
            A unicode string. The comments you add to the message.

        :return:
            Successful or not: True / False

        """

        if not isinstance(message, snstype.Message):
            logger.warning("unknown type to forward: %s", type(message))
            return False

        if self.update == None:
            # This warning message is for those who build application on
            # individual plugin classes. If the developers based their app
            # on SNSPocket, they will see the warning message given by the
            # dummy update method.
            logger.warning("this platform does not have update(). can not forward")
            return False

        tll = None
        if 'text_length_limit' in self.jsonconf:
            tll = self.jsonconf['text_length_limit']

        #TODO:
        #    This mapping had better be configurable from user side
        mapping = {
                'RSS': u'RSS',
                'RSS2RW': u'RSS2RW',
                'RenrenShare': u'人人',
                'RenrenStatus': u'人人',
                'SQLite': u'SQLite',
                'SinaWeiboStatus': u'新浪',
                'TencentWeiboStatus': u'腾讯',
                'TwitterStatus': u'推特',
                'Email': u'伊妹'
        }

        platform_prefix = message.platform
        if platform_prefix in mapping:
            platform_prefix = mapping[platform_prefix]
        last_user = "[%s:%s]" % (platform_prefix, message.parsed.username)
        if 'text_orig' in message.parsed and 'text_trace' in message.parsed:
            #TODO:
            #
            # We wrap unicode() here, in case the 'text_trace' field
            # or 'text_orig' field is parsed to None.
            #
            # This problem can also be solved at _cat() function. In
            # this way, it we can compat the message further. i.e.
            # When one field is None, we omit the text "None" and
            # delimiter.
            final = self._cat(tll, [(text, 5), (last_user, 4), \
                    (unicode(message.parsed.text_trace), 1), \
                    (unicode(message.parsed.text_orig), 3)])
        else:
            final = self._cat(tll, [(text, 3), (last_user, 2),\
                    (unicode(message.parsed.text), 1)])

        return self.update(final)

########NEW FILE########
__FILENAME__ = snsconf
# -*- coding: utf-8 -*-

'''
snsapi Basic Hardcode Conf

See documentations of variables for more information.

For first time users, please ignore the following discussion in the same
section. They are intended for SNSAPI middleware developers. I don't
want to confuse you at the moement. When you are ready to refactor this
piece of code, you can come back to read them discuss in the group.

This files may look weird at first glance,
here's a short background story on how I
get to this point:

   * There are many debugging information
     printed on the console previously,
     which make stdin/stdout interface a
     mess.
   * I just developed a wrapper for logging.
     Hope it can unify different log messages.
   * 'snsapi' as a whole package will import
     all plugins at the initialization stage.
     This will trigger a 'xxx plugged!" message.
   * Some calls to write logs happens before
     we have a chance to init SNSLog (Original
     plan is to let the upper layer init with
     its own preference).
   * The workaround is to develop this
     hardcode conf files.

Guidelines to add things here:

   * If something is to be configured before
     fully init of snsapi(which involves
     init those plugins), the configuration
     can go into this file.
   * Otherwise, try best to let the upper
     layer configure it. Put the confs in the
     ``../conf`` folder.

'''

from os import path

from snslog import SNSLog


class SNSConf(object):
    """
    Hardcode Confs for SNSAPI

    """

    SNSAPI_CONSOLE_STDOUT_ENCODING = 'utf-8'

    '''
    See ``SNSAPI_CONSOLE_STDIN_ENCODING``.
    '''

    SNSAPI_CONSOLE_STDIN_ENCODING = 'utf-8'

    '''
    For chinese version windows systems, you may want to change
    ``SNSAPI_CONSOLE_STDOUT_ENCODING = 'utf-8'``
    and
    ``SNSAPI_CONSOLE_STDIN_ENCODING = 'utf-8'``
    to 'gbk'. For others, check the encoding of
    your console and set it accordingly.

    See the discussion: https://github.com/hupili/snsapi/issues/8
    '''

    SNSAPI_LOG_INIT_LEVEL = SNSLog.INFO

    '''
    Possible values:
       * SNSLog.DEBUG
       * SNSLog.INFO
       * SNSLog.WARNING
       * SNSLog.ERROR
       * SNSLog.CRITICAL

    In Release version, set to WARNING
    '''

    SNSAPI_LOG_INIT_VERBOSE = False

    '''
    Examples,

    True:
       * [DEBUG][20120829-135506][sina.py][<module>][14]SinaAPI plugged!

    False:
       * [DEBUG][20120829-142322]SinaAPI plugged!
    '''

    #SNSAPI_LOG_INIT_LOGFILE = "snsapi.log"
    SNSAPI_LOG_INIT_LOGFILE = None

    '''
       * None: Output to STDOUT. Good for Debug version.
       * {Filename}: Log to {Filename}. Good for Relase version.
    '''

    #TODO:
    #    Find better way to organize static package data
    _SNSAPI_DIR_STATIC_DATA = path.join(path.dirname(path.abspath(__file__)), 'data')
    _USER_HOME = path.expanduser('~')
    _SNSAPI_DIR_USER_ROOT = path.join(_USER_HOME, '.snsapi')
    _SNSAPI_DIR_CWD = path.abspath('.')
    if path.isdir(path.join(_SNSAPI_DIR_CWD, 'conf'))\
        and path.isdir(path.join(_SNSAPI_DIR_CWD, 'save')):
        SNSAPI_DIR_STORAGE_ROOT = _SNSAPI_DIR_CWD
    else:
        SNSAPI_DIR_STORAGE_ROOT = _SNSAPI_DIR_USER_ROOT
    SNSAPI_DIR_STORAGE_CONF = path.join(SNSAPI_DIR_STORAGE_ROOT, 'conf')
    SNSAPI_DIR_STORAGE_SAVE = path.join(SNSAPI_DIR_STORAGE_ROOT, 'save')

    '''
    ``SNSAPI_DIR_STORAGE_ROOT`` can be:

       * ``./``: if there exists ``./save`` and ``./conf``.
         This is the usual case for running SNSAPI under the repo.
         We have the two dirs by default.
         In this way, you can have multiple configurations on your machine at the same time.
       * ``~/.snsapi/``: if the above condition is not satisfied.
         This is to allow users to launch applications
         (e.g. ``snscli.py`` and ``snsgui.py``)
         from any place in the system.
         The per-user configurations and saved credentials can be used.

    ``SNSAPI_DIR_STORAGE_CONF`` and ``SNSAPI_DIR_STORAGE_SAVE``
    are just subdir "conf" and "save" under
    ``SNSAPI_DIR_STORAGE_ROOT``
    '''

    import os
    if not path.isdir(SNSAPI_DIR_STORAGE_ROOT):
        os.mkdir(SNSAPI_DIR_STORAGE_ROOT)
    if not path.isdir(SNSAPI_DIR_STORAGE_CONF):
        os.mkdir(SNSAPI_DIR_STORAGE_CONF)
    if not path.isdir(SNSAPI_DIR_STORAGE_SAVE):
        os.mkdir(SNSAPI_DIR_STORAGE_SAVE)


    def __init__(self):
        raise SNSConfNoInstantiation()


class SNSConfNoInstantiation(Exception):
    """
    This exception is used to make sure you do not
    instantiate SNSConf class.
    """
    def __init__(self):
        super(SNSConfNoInstantiation, self).__init__()

    def __str__(self):
        return "You can not instantiate SNSConf. "\
                "Access its static members directly!"

try:
    #NOTE:
    #    `set_custom_conf`` is a callable which modifies `SNSConf` class.
    #    e.g. developers can set
    import custom_conf
    custom_conf.set_custom_conf(SNSConf)
except:
    pass

# ========== Init Operations  =================

SNSLog.init(level = SNSConf.SNSAPI_LOG_INIT_LEVEL, \
        logfile = SNSConf.SNSAPI_LOG_INIT_LOGFILE, \
        verbose = SNSConf.SNSAPI_LOG_INIT_VERBOSE)

########NEW FILE########
__FILENAME__ = snscrypt
# -*- coding: utf-8 -*-

'''
snsapi Cryptography Tools
'''

import base64

class SNSCrypto(object):
    """snsapi cryptography tools"""
    def __init__(self):
        super(SNSCrypto, self).__init__()
        self.__init_crypt()

    def __init_crypt(self):
        """
        Init the crypto utility which will be called by
        __encrypt and __decrypt.

        """
        from third import pyDes
        self.crypt = pyDes.des("DESCRYPT", pyDes.CBC, "\0\0\0\0\0\0\0\0",\
                pad=None, padmode=pyDes.PAD_PKCS5)

    def __encrypt(self, string):
        """
        The delegate for encrypt utility.
        e.g. You can change the following use of pyDes
        to openssl if you have it. We use pyDes for by
        Default because we don't want o bother the user
        to install other softwares.

        See also, __init_crypt, __encrypt, __decrypt

        """
        return self.crypt.encrypt(string)

    def __decrypt(self, string):
        """
        The delegate for decrypt utility.

        See also, __init_crypt, __encrypt, __decrypt

        """
        return self.crypt.decrypt(string)


    def encrypt(self, string):
        """
        INPUT: any string
        OUTPUT: hexadecimal string of encrypt output

        The input string will first be encoded by BASE-64.
        This is to make sure the intermediate value is a
        printable string. It will be easier to change
        pyDes to other crypto utilities. After actual
        encryption delegated to other modules, the final
        output is also base64 encrypted, this makes it
        printable.

        """
        tmp1 = base64.encodestring(string)
        tmp2 = self.__encrypt(tmp1)
        tmp3 = base64.encodestring(tmp2)
        return tmp3

    def decrypt(self, string):
        """
        INPUT: hexadecimal string of encrypt output
        OUTPUT: any string

        Reverse process of decrypt

        """
        tmp1 = base64.decodestring(string)
        tmp2 = self.__decrypt(tmp1)
        tmp3 = base64.decodestring(tmp2)
        return tmp3

if __name__ == '__main__':
    c = SNSCrypto()
    plain = "Test Crypto wapper for SNSAPI!"
    secret = c.encrypt(plain)
    decplain = c.decrypt(secret)
    print "plain:%s\nsecret:%s\ndecrypted plain:%s\n" \
            % (plain, secret, decplain)

########NEW FILE########
__FILENAME__ = snslog
# -*- coding: utf-8 -*-

'''
snsapi Log Tools
'''

import logging
import inspect
import os.path

#Test piece.
#This lambda expression does not "inline" into
#the caller file. The filename and funcname
#reported in log is still in 'snslog.py'
#mylog = lambda *x: logging.info(*x)

class SNSLog(object):
    """
    Provide the unified entry to write logs

    The current backend is Python's logging module.
    """

    #Static variables
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    VERBOSE = True

    def __init__(self):
        super(SNSLog).__init__()
        raise SNSLogNoInstantiation

    @staticmethod
    def init(logfile = None, level = WARNING, verbose = True):
        """
        Init the log basic configurations. It should
        be called only once over the entire execution.

        If you invoke it for multiple times, only the
        first one effects. This is the behaviour of
        logging module.

        """

        # Debug information writes to log using SNSLog.debug().
        # How do you debug the logger itself...?
        # Here it is...
        # We fall back to the print.
        # They should be comment out to make the screen clean.
        #print "=== init log ==="
        #print "logfile:%s" % logfile
        #print "level:%s" % level
        #print "verbose:%s" % verbose

        if logfile:
            logging.basicConfig(\
                    format='[%(levelname)s][%(asctime)s]%(message)s', \
                    datefmt='%Y%m%d-%H%M%S', \
                    level = level, \
                    filename = logfile
                    )
        else:
            logging.basicConfig(\
                    format='[%(levelname)s][%(asctime)s]%(message)s', \
                    datefmt='%Y%m%d-%H%M%S', \
                    level = level
                    )
        SNSLog.VERBOSE = verbose

    @staticmethod
    def __env_info():
        if SNSLog.VERBOSE:
            caller = inspect.stack()[2]
            fn = os.path.basename(caller[1])
            no = caller[2]
            func = caller[3]
            return "[%s][%s][%s]" % (fn, func, no)
        else:
            return ""

    @staticmethod
    def debug(fmt, *args):
        logging.debug(SNSLog.__env_info() + fmt, *args)

    @staticmethod
    def info(fmt, *args):
        logging.info(SNSLog.__env_info() + fmt, *args)

    @staticmethod
    def warning(fmt, *args):
        logging.warning(SNSLog.__env_info() + fmt, *args)

    @staticmethod
    def warn(fmt, *args):
        logging.warn(SNSLog.__env_info() + fmt, *args)

    @staticmethod
    def error(fmt, *args):
        logging.error(SNSLog.__env_info() + fmt, *args)

    @staticmethod
    def critical(fmt, *args):
        logging.critical(SNSLog.__env_info() + fmt, *args)

class SNSLogNoInstantiation(Exception):
    """docstring for SNSLogNoInstantiation"""
    def __init__(self):
        super(SNSLogNoInstantiation, self).__init__()

    def __str__(self):
        return "You can not instantiate SNSLog. "\
                "Call its static methods directly!"


if __name__ == '__main__':
    #SNSLog.init(level = SNSLog.DEBUG, verbose = False)
    SNSLog.init(level = SNSLog.DEBUG)
    SNSLog.warning('test: %d; %s', 123, "str")
    SNSLog.debug('test debug')
    SNSLog.info('test info')
    SNSLog.warning('test warning')
    SNSLog.warn('test warn')
    SNSLog.error('test error')
    SNSLog.critical('test critical')


########NEW FILE########
__FILENAME__ = snspocket
# -*- coding: utf-8 -*-

'''
snspocket: the container class for snsapi's

'''

# === system imports ===
from utils import json
from os import path
import sqlite3
import thread

# === snsapi modules ===
import snstype
import utils
from errors import snserror
from utils import console_output, obj2str, str2obj
from snslog import SNSLog as logger
from snsconf import SNSConf
import platform
from async import AsyncDaemonWithCallBack

# === 3rd party modules ===

DIR_DEFAULT_CONF_CHANNEL = path.join(SNSConf.SNSAPI_DIR_STORAGE_CONF, 'channel.json')
DIR_DEFAULT_CONF_POCKET = path.join(SNSConf.SNSAPI_DIR_STORAGE_CONF, 'pocket.json')


def _default_callback(pocket, res):
    pass

class BackgroundOperationPocketWithSQLite:
    def __init__(self, pocket, sqlite, callback=_default_callback, timeline_sleep=60, update_sleep=10):
        self.sp = pocket
        self.dblock = thread.allocate_lock()
        self.sqlitefile = sqlite
        conn = sqlite3.connect(self.sqlitefile)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS home_timeline (
            id integer primary key, pickled_object text, digest text, text text, username text, userid text, time integer, isread integer DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS pending_update (
            id integer primary key, callback text, type text, args text, kwargs text
        )""")
        conn.commit()
        c.close()
        self.home_timeline_job = AsyncDaemonWithCallBack(self.sp.home_timeline, (), {}, self.write_timeline_to_db, timeline_sleep)
        self.update_job = AsyncDaemonWithCallBack(self.update_func, (), {}, None, update_sleep)
        self.home_timeline_job.start()
        self.update_job.start()

    def home_timeline(self, count=20):
        ret = snstype.MessageList()
        logger.debug("acquiring lock")
        self.dblock.acquire()
        try:
            conn = sqlite3.connect(self.sqlitefile)
            c = conn.cursor()
            c.execute("SELECT pickled_object FROM home_timeline ORDER BY time DESC LIMIT 0, %d" % (count,))
            p = c.fetchall()
            logger.info("%d messages read from database" % (len(p)))
            for i in p:
                ret.append(str2obj(str(i[0])))
        except Exception, e:
            logger.warning("Error while reading database: %s" % (str(e)))
        finally:
            logger.debug("releasing lock")
            self.dblock.release()
            return ret

    def write_timeline_to_db(self, msglist):
        logger.debug("acquiring lock")
        self.dblock.acquire()
        try:
            conn = sqlite3.connect(self.sqlitefile)
            cursor = conn.cursor()
            what_to_write = [
            ]
            for msg in msglist:
                try:
                    pickled_msg = obj2str(msg)
                    sig = unicode(msg.digest())
                    cursor.execute("SELECT * FROM home_timeline WHERE digest = ?", (sig,))
                    if not cursor.fetchone():
                        what_to_write.append((
                            unicode(pickled_msg), sig, msg.parsed.text, msg.parsed.username, msg.parsed.userid, msg.parsed.time
                        ))
                except Exception, e:
                    logger.warning("Error while checking message: %s" % (str(e)))
            try:
                logger.info("Writing %d messages" % (len(what_to_write)))
                cursor.executemany("INSERT INTO home_timeline (pickled_object, digest, text, username, userid, time) VALUES(?, ?, ?, ?, ?, ?)", what_to_write)
            except Exception, e:
                logger.warning("Error %s" % (str(e)))
            conn.commit()
            cursor.close()
        finally:
            logger.debug("releasing lock")
            self.dblock.release()

    def _update(self, type, args, kwargs):
        logger.debug("acquiring lock")
        self.dblock.acquire()
        try:
            conn = sqlite3.connect(self.sqlitefile)
            cursor = conn.cursor()
            callback = None
            if 'callback' in kwargs:
                callback = kwargs['callback']
                del kwargs['callback']
            cursor.execute("INSERT INTO pending_update (type, callback, args, kwargs) VALUES (?, ?, ?, ?)", (
                type,
                obj2str(callback),
                obj2str(args),
                obj2str(kwargs)
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception, e:
            logger.warning("Error while saving pending_update: %s" % (str(e)))
            return False
        finally:
            logger.debug("releasing lock")
            self.dblock.release()

    def update(self, *args, **kwargs):
        return self._update('update', args, kwargs)

    def forward(self, *args, **kwargs):
        return self._update('forward', args, kwargs)

    def reply(self, *args, **kwargs):
        return self._update('reply', args, kwargs)

    def update_func(self):
        logger.debug("acquiring lock")
        self.dblock.acquire()
        try:
            conn = sqlite3.connect(self.sqlitefile)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pending_update")
            i = cursor.fetchone()
            if i:
                cursor.execute("DELETE FROM pending_update WHERE id = ?", (i['id'], ))
                j = {
                    'id': str(i['id']),
                    'args': str2obj(str(i['args'])),
                    'kwargs': str2obj(str(i['kwargs'])),
                    'type': str(i['type']),
                    'callback': str2obj(str(i['callback']))
                }
                res = getattr(self.sp, j['type'])(*j['args'], **j['kwargs'])
                if j['callback']:
                    j['callback'](self, res)
            conn.commit()
            cursor.close()
        except Exception, e:
            logger.warning("Error while updating: %s" % (str(e)))
        finally:
            logger.debug("releasing lock")
            self.dblock.release()


class SNSPocket(dict):
    """The container class for snsapi's"""

    __default_mapping = {
        "home_timeline" : "home_timeline",
        "update" : "update",
        "reply" : "reply",
        "read" : "home_timeline",
        "write" : "update",
        "writeto" : "reply"}

    def __init__(self):
        super(SNSPocket, self).__init__()
        self.jsonconf = {}

    def __iter__(self):
        """
        By default, the iterator only return opened channels.
        """
        l = []
        for c in self.itervalues():
            if c.jsonconf['open'] == 'yes':
                l.append(c.jsonconf['channel_name'])
        return iter(l)

    def clear_channel(self):
        self.clear()

    def __dummy_method(self, channel, name):

        def dummy(*al, **ad):
            logger.warning("'%s' does not have method '%s'", channel, name)
            return False

        return dummy

    def __method_routing(self, channel, mapping = None):
        #TODO:
        #    This function can support higher layer method
        #    routing. The basic usage is to enable alias to
        #    lower level methods. e.g. you can call "read",
        #    which may be routed to "home_timeline" for
        #    real business.
        #
        #    Currently, it is here to map non existing methods
        #    to dummy methods.
        #
        #    It's also unclear that where is the best place
        #    for this function. here, or in the base class
        #    'SNSBase'?
        #
        #    The implementation does not look good.
        #    I need two scan:
        #       * The first is to determine who is dummy.
        #       * The second is to really assign dummy.
        #
        #    If we do everything in one scan, after assigning
        #    dummy, the later reference will find it "hasattr".
        #    Then we do not get the correct method name in
        #    log message.

        if not mapping:
            mapping = SNSPocket.__default_mapping

        c = self[channel]
        d = {}

        for src in mapping:
            dst = mapping[src]
            if not hasattr(c, dst):
                d[dst] = 1
                d[src] = 1
            else :
                if src != dst:
                    setattr(c, src, getattr(c,dst))

        for m in d:
            setattr(c, m, self.__dummy_method(channel, m))

    def add_channel(self, jsonconf):
        logger.debug(json.dumps(jsonconf))
        cname = jsonconf['channel_name']

        if cname in self:
            logger.warning("Duplicate channel_name '%s'. Nothing happens to it. ", cname)
            return False

        try:
            p = getattr(platform, jsonconf['platform'])
        except AttributeError:
            p = None
            logger.warning("No such platform '%s'. Nothing happens to it. ", jsonconf['platform'])
            return False
        if p:
            self[cname] = p(jsonconf)
            self.__method_routing(cname, SNSPocket.__default_mapping)

        return True

    def load_config(self,
            fn_channel = DIR_DEFAULT_CONF_CHANNEL,
            fn_pocket = DIR_DEFAULT_CONF_POCKET):
        """
        Read configs:
        * channel.conf
        * pocket.conf
        """

        count_add_channel = 0
        try:
            with open(path.abspath(fn_channel), "r") as fp:
                allinfo = json.load(fp)
                for site in allinfo:
                    if self.add_channel(utils.JsonDict(site)):
                        count_add_channel += 1
        except IOError:
            #raise snserror.config.nofile(fn_channel)
            logger.warning("'%s' does not exist. Use default", fn_channel)
        except ValueError as e:
            raise snserror.config.load("file: %s; message: %s" % (fn_channel, e))

        try:
            with open(path.abspath(fn_pocket), "r") as fp:
                allinfo = json.load(fp)
                self.jsonconf = allinfo
        except IOError:
            #raise snserror.config.nofile(fn_pocket)
            logger.warning("'%s' does not exist. Use default", fn_pocket)
        except ValueError as e:
            raise snserror.config.load("file: %s; message:%s" % (fn_channel, e))

        logger.info("Read configs done. Add %d channels" % count_add_channel)

    def save_config(self,
            fn_channel = DIR_DEFAULT_CONF_CHANNEL,
            fn_pocket = DIR_DEFAULT_CONF_POCKET):
        """
        Save configs: reverse of load_config

        Configs can be modified during execution. snsapi components
        communicate with upper layer using Python objects. Pocket
        will be the unified place to handle file transactions.

        """

        conf_channel = []
        for c in self.itervalues():
            conf_channel.append(c.jsonconf)

        conf_pocket = self.jsonconf

        try:
            json.dump(conf_channel, open(fn_channel, "w"), indent = 2)
            json.dump(conf_pocket, open(fn_pocket, "w"), indent = 2)
        except:
            raise snserror.config.save

        logger.info("save configs done")

    def new_channel(self, pl = None, **kwarg):
        if pl:
            try:
                return getattr(platform, pl).new_channel(**kwarg)
            except AttributeError:
                logger.warning("can not find platform '%s'", pl)
                return utils.JsonDict()
        else:
            _fn_conf = path.join(SNSConf._SNSAPI_DIR_STATIC_DATA, 'init-channel.json.example')
            return utils.JsonDict(json.load(open(_fn_conf)))

    def list_platform(self):
        console_output("")
        console_output("Supported platforms:")
        for p in platform.platform_list:
            console_output("   * %s" % p)
        console_output("")


    def list_channel(self, channel = None, verbose = False):
        if channel:
            try:
                console_output(str(self[channel].jsonconf))
            except KeyError:
                logger.warning("No such channel '%s'.", channel)
        else:
            console_output("")
            console_output("Current channels:")
            for cname in self.iterkeys():
                c = self[cname].jsonconf
                console_output("   * %s: %s %s" % \
                        (c['channel_name'],c['platform'],c['open']))
                if verbose:
                    console_output("    %s" % json.dumps(c))
            console_output("")

    def auth(self, channel = None):
        """docstring for auth"""
        if channel:
            self[channel].auth()
        else:
            for c in self.itervalues():
                if self.__check_method(c, ''):
                    c.auth()

    def __check_method(self, channel, method):
        '''
        Check availability of batch operation methods:

           * First the channel 'open' is switched on.
           * There is no 'methods' fields meaning all
           methods can be invoked by default.
           * If there is methods, check whether the current
           method is defaultly enabled.

        '''
        if channel.jsonconf['open'] == "yes":
            if not 'methods' in channel.jsonconf:
                return True
            elif channel.jsonconf['methods'].find(method) != -1:
                return True
        return False

    def _home_timeline(self, count, ch):
        #TODO:
        #    The following set default parameter for home_timeline.
        #    Other methods may also need default parameter some time.
        #    We should seek for a more unified solution.
        #    e.g.
        #    When adding channels, hide their original function
        #    and substitue it with a partial evaluated version
        #    using configured defaults
        if not count:
            if 'home_timeline' in ch.jsonconf:
                count = ch.jsonconf['home_timeline']['count']
            else:
                count = 20
        return ch.home_timeline(count)

    def home_timeline(self, count = None, channel = None):
        """
        Route to home_timeline method of snsapi.

        :param channel:
            The channel name. Use None to read all channels
        """

        status_list = snstype.MessageList()
        if channel:
            if channel in self:
                if self[channel].is_expired():
                    logger.warning("channel '%s' is expired. Do nothing.", channel)
                else:
                    status_list.extend(self._home_timeline(count, self[channel]))
            else:
                logger.warning("channel '%s' is not in pocket. Do nothing.", channel)
        else:
            for c in self.itervalues():
                if self.__check_method(c, 'home_timeline') and not c.is_expired():
                    status_list.extend(self._home_timeline(count, c))

        logger.info("Read %d statuses", len(status_list))
        return status_list

    def update(self, text, channel = None, **kwargs):
        """
        Route to update method of snsapi.

        :param channel:
            The channel name. Use None to update all channels
        """
        re = {}
        if channel:
            if channel in self:
                if self[channel].is_expired():
                    logger.warning("channel '%s' is expired. Do nothing.", channel)
                else:
                    re[channel] = self[channel].update(text)
            else:
                logger.warning("channel '%s' is not in pocket. Do nothing.", channel)
        else:
            for c in self.itervalues():
                if self.__check_method(c, 'update') and not c.is_expired():
                    re[c.jsonconf['channel_name']] = c.update(text, **kwargs)

        logger.info("Update status '%s'. Result:%s", text, re)
        return re

    def reply(self, message, text, channel = None):
        """
        Route to reply method of snsapi.

        :param channel:
            The channel name. Use None to automatically select
            one compatible channel.

        :param status:
            Message or MessageID object.

        :text:
            Reply text.
        """

        if isinstance(message, snstype.Message):
            mID = message.ID
        elif isinstance(message, snstype.MessageID):
            mID = message
        else:
            logger.warning("unknown type: %s", type(message))
            return {}

        re = {}
        if channel:
            if channel in self:
                if self[channel].is_expired():
                    logger.warning("channel '%s' is expired. Do nothing.", channel)
                else:
                    re = self[channel].reply(mID, text)
            else:
                logger.warning("channel '%s' is not in pocket. Do nothing.", channel)
        else:
            for c in self.itervalues():
                if self.__check_method(c, 'reply') and not c.is_expired():
                    #TODO:
                    #    First try to match "channel_name".
                    #    If there is no match, try to match "platform".
                    if c.jsonconf['platform'] == mID.platform:
                        re = c.reply(mID, text)
                        break

        logger.info("Reply to status '%s' with text '%s'. Result: %s",\
                mID, text, re)
        return re

    def forward(self, message, text, channel = None):
        """
        forward a message

        """
        re = {}
        if channel:
            if channel in self:
                if self[channel].is_expired():
                    logger.warning("channel '%s' is expired. Do nothing.", channel)
                else:
                    re = self[channel].forward(message, text)
            else:
                logger.warning("channel '%s' is not in pocket. Do nothing.", channel)
        else:
            for c in self.itervalues():
                if self.__check_method(c, 'forward') and not c.is_expired():
                    re[c.jsonconf['channel_name']] = c.forward(message, text)

        logger.info("Forward status '%s' with text '%s'. Result: %s",\
                message.digest(), text, re)
        return re

########NEW FILE########
__FILENAME__ = snstype
# -*- coding: utf-8 -*-

'''
SNS type: status, user, comment
'''

import hashlib

import utils
from errors import snserror
from snsconf import SNSConf
from snslog import SNSLog as logger


class BooleanWrappedData:
    def __init__(self, boolval, data=None):
        self.boolval = boolval
        self.data = data

    def __nonzero__(self):
        return self.boolval

    def __eq__(self, other):
        if self.boolval ^ bool(other):
            return False
        else:
            return True

    def __unicode__(self):
        return unicode((self.boolval, self.data))

    def __str__(self):
        return str((self.boolval, self.data))

    def __repr__(self):
        return repr((self.boolval, self.data))

class MessageID(utils.JsonDict):
    """
    All information to locate one status is here.

    It shuold be complete so that:

       * one can invoke reply() function of plugin on this object.
       * Or one can invoke reply() function of container on this object.

    There are two mandatory fields:

       * platform: Name of the platform (e.g. RenrenStatus)
       * channel: Name of the instantiated channel
         (e.g. 'renren_account_1').
         Same as a channel's ``.jsonconf['channel_name']``.

    In order to reply one status, here's the information
    required by each platforms:

       * Renren: the status_id and source_user_id
       * Sina: status_id
       * QQ: status_id

    **NOTE**: This object is mainly for SNSAPI to identify a Message.
    Upper layer had better not to reference fields of this object directly.
    If you must reference this object, please do not touch those
    non-mandatory fields.

    """
    def __init__(self, platform = None, channel = None):
        super(MessageID, self).__init__()

        self.platform = platform
        self.channel = channel

    #def __str__(self):
    #    """docstring for __str__"""
    #    return "(p:%s|sid:%s|uid:%s)" % \
    #            (self.platform, self.status_id, self.source_user_id)

    def __str__(self):
        return self._dumps()


class Message(utils.JsonDict):
    '''
    The Message base class for SNSAPI

    Data Fields:

       * ``platform``: a string describing the platform
         where this message come from. See 'snsapi/platform.py'
         for more details.
       * ``raw``: the raw json or XML object returned from
         the platform spefiic API. This member is here to give
         upper layer developers the last chance of manipulating
         any available information. Having an understanding of
         the platform-specific returning format is esential.
       * ``parsed``: this member abstracts some common fields
         that all messages are supposed to have. e.g. 'username',
         'time', 'text', etc.
       * ``ID``: a ``MessageID`` object. This ID should be enough
         to indentify a message across all different platforms.

    For details of ``ID``, please see the docstring of ``MessageID``.

    Mandatory fields of ``parsed`` are:

       * ``time:`` a utc integer. (some platform returns parsed string)
       * ``userid:`` a string. (called as "username" at some platform)
       * ``username:`` a string. (called as "usernick" as some platform)
       * ``text:`` a string. (can be 'text' in the returning json object,
         or parsed from other fields.)
       * ``attachments``: an array of attachments. Each attachment is:
         ``{'type': TYPE, 'format': [FORMAT1, FORMAT2, ...], 'data': DATA}``.
         TYPE can be one of ``link``, ``picture``, ``album``, ``video``, ``blog``.
         FORMAT can be ``link``, ``binary``, ``text`` and ``other``.
         DATA is your data presented in FORMAT.

    Optional fields of 'parsed' are:

       * ``deleted``: Bool. For some OSN.
       * ``reposts_count``: an integer. For some OSN.
       * ``comments_count``: an integer. For some OSN.
       * ``link``: a string. For RSS; Parsed from microblog message;
         Parsed from email message; etc.
       * ``title``: a string. For RSS; Blog channel of some OSN.
       * ``description``: a string. For RSS digest text;
         Sharing channel of some OSN; etc.
       * ``body``: a string. The 'content' of RSS, the 'body' of HTML,
         or whatever sematically meaning the body of a document.
       * ``text_orig``: a string. The original text, also known as
         "root message" in some context. e.g. the earliest status
         in one thread.
       * ``text_last``: a string. The latest text, also known as
         "message" in some context. e.g. the reply or forwarding
         comments made by the last user.
       * ``text_trace``: a string. Using any (can be platform-specific)
         method to construt the trace of this message. e.g.
         the forwarding / retweeting / reposting sequence.
         There is no unified format yet.
       * ``username_origin``: a string. The username who posts 'text_orig'.

    '''

    platform = "SNSAPI"

    def __init__(self, dct = None, platform = None, channel = None, conf = {}):

        self.conf = conf
        self['deleted'] = False
        self['ID'] = MessageID(platform, channel)

        self['raw'] = utils.JsonDict({})
        self['parsed'] = utils.JsonDict({'attachments' : []})
        if dct:
            self['raw'] = utils.JsonDict(dct)
            try:
                self.parse()
            except KeyError as e:
                raise snserror.type.parse(str(e))

    def parse(self):
        '''
        Parse self.raw and store result in self.parsed

        '''
        # Default action: copy all fields in 'raw' to 'parsed'.
        self.parsed.update(self.raw)

    def show(self):
        '''
        Level 1 serialization and print to console

        See dump()

        '''
        utils.console_output(unicode(self))

    def __str__(self):
        '''
        Level 1 serialization and convert to str using console encoding

        See dump()

        '''
        return unicode(self).encode(SNSConf.SNSAPI_CONSOLE_STDOUT_ENCODING)

    def __unicode__(self):
        '''
        Level 1 serialization and convert to unicode

        See dump()

        '''
        # NOTE:
        #
        #     dump() method remains stable because the downstream is
        #     digest methods. The __str__ and __unicode__ are only
        #     for console interaction. Normal apps should refer to
        #     those fields in 'parsed' themselves.
        #
        #     We limit the output to 500 characters to make the console
        #     output uncluttered.
        return unicode("[%s] at %s \n  %s") % (self.parsed.username,
                utils.utc2str(self.parsed.time),
                self.parsed.text[0:500])

    def dump(self, tz=None):
        '''
        Level 1 serialization: console output.

        This level targets console output. It only digests essnetial
        information which end users can understand. e.g. the text
        of a status is digested whereas the ID fields is not digested.

        To control the format, please rewrite dump() in derived Message class.

        See also __str__(), __unicode__(), show()

        '''
        if tz:
            return unicode("[%s] at %s \n  %s") % \
                    (self.parsed.username, utils.utc2str(self.parsed.time, tz), self.parsed.text)
        else:
            return unicode("[%s] at %s \n  %s") % \
                    (self.parsed.username, utils.utc2str(self.parsed.time), self.parsed.text)

    def dump_parsed(self):
        '''
        Level 2 serialization: interface output.

        This level targets both Python class interface and
        STDIO/STDOUT interface. The output of all kinds of
        Messages conform to the same format. The json object
        can be used to pass information in/out SNSAPI using
        Python class. It is also able to pretty print, so
        that the STDOUT result is easy to parse in any
        language.
        '''
        return self.parsed._dumps_pretty()


    def dump_full(self):
        '''
        Level 3 serialization: complete output.

        This level targets more sophisticated applications.
        The basic function of SNSAPI is to unify different
        formats. That's what the first two level of
        serialization do. However, app developers may want
        more sophisticated processing. We serialize the full
        Message object through this function. In this way,
        app developers can get all information they need.
        Note that knowledge of the platform specific return
        format is essential. We conclude their fields in:

           * https://github.com/hupili/snsapi/wiki/Status-Attributes

        This wiki page may not always be up to date. Please
        refer to the offical API webpage for more info.
        '''
        return self._dumps()

    def digest(self):
        '''
        Digest the message content. This value is useful in
        for example forwarding services to auto-reply services,
        for those applications requires message deduplication.

        It corresponds to dump().

        Note: different messages may be regarded as the same
        according to this digest function.

        '''
        from utils import FixedOffsetTimeZone
        tz = FixedOffsetTimeZone(0, 'GMT')
        return hashlib.sha1(self.dump(tz=tz).encode('utf-8')).hexdigest()

    def digest_parsed(self):
        '''
        It corresponds to dump_parsed()

        '''
        return hashlib.sha1(self.dump_parsed().encode('utf-8')).hexdigest()

    def digest_full(self):
        '''
        It corresponds to dump_full()

        '''
        return hashlib.sha1(self.dump_full().encode('utf-8')).hexdigest()


class MessageList(list):
    """
    A list of Message object
    """
    def __init__(self, init_list=None):
        super(MessageList, self).__init__()
        if init_list:
            self.extend(init_list)

    def append(self, e):
        if isinstance(e, Message):
            if hasattr(e, 'deleted') and e.deleted:
                logger.debug("Trying to append Deleted Message type element. Ignored")
            else:
                super(MessageList, self).append(e)
        else:
            logger.debug("Trying to append non- Message type element. Ignored")

    def extend(self, l):
        if isinstance(l, MessageList):
            super(MessageList, self).extend(l)
        elif isinstance(l, list):
            # We still extend the list if the user asks to.
            # However, a warning will be placed. Doing this
            # may violate some properties of MessageList, e.g.
            # there is no Deleted Message in the list.
            super(MessageList, self).extend(l)
            logger.warning("Extend MessageList with non MessageList list.")
        else:
            logger.warning("Extend MessageList with unknown type.")

    def __str__(self):
        tmp = ""
        no = 0
        for s in self:
            tmp = tmp + "<%d>\n%s\n" % (no, str(s))
            no = no + 1
        return tmp

    def __unicode__(self):
        tmp = ""
        no = 0
        for s in self:
            tmp = tmp + "<%d>\n%s\n" % (no, unicode(s))
            no = no + 1
        return tmp

class User(object):
    def __init__(self, jobj=None):
        self.id = 0

class AuthenticationInfo(utils.JsonObject):
    # default auth configurations
    def __init__(self, auth_info = None):
        if auth_info :
            self.update(auth_info)
        else :
            self.callback_url = None
            self.cmd_fetch_code = "(default)"
            self.cmd_request_url = "(default)"
            self.save_token_file = "(default)"
            self.login_username = None
            self.login_password = None

    def set_defaults(self):
        DEFAULT_MAPPING = {
                "cmd_request_url": "(local_webserver)+(webbrowser)",
                "cmd_fetch_code": "(local_webserver)"
                }
        for (k,v) in DEFAULT_MAPPING.items():
            if (not (k in self)) or (self[k] == "(default)"):
                self[k] = DEFAULT_MAPPING[k]

if __name__ == "__main__":
    import time
    m1 = Message({'text': 'test',
        'username': 'snsapi',
        'userid': 'snsapi',
        'time': time.time() })
    m2 = Message({'text': u'测试',
        'username': 'snsapi',
        'userid': 'snsapi',
        'time': time.time() })
    ml = MessageList()
    ml.append(m1)
    ml.append(m2)
    # NOTE:
    #     When you develop new plugins, the MessageList returned
    #     by your ``home_timeline`` should be printable in this
    #     way. This is minimum checking for whether you have
    #     mandatory fields.
    print ml

########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the
official Facebook JavaScript SDK, which is the canonical way to
implement Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
if user:
    graph = facebook.GraphAPI(user["access_token"])
    profile = graph.get_object("me")
    friends = graph.get_connections("me", "friends")

"""

import cgi
import time
import urllib
import urllib2
import httplib
import hashlib
import hmac
import base64
import logging
import socket

# Find a JSON parser
try:
    import simplejson as json
except ImportError:
    try:
        from django.utils import simplejson as json
    except ImportError:
        import json
_parse_json = json.loads

# Find a query string parser
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs


class GraphAPI(object):
    """A client for the Facebook Graph API.

    See http://developers.facebook.com/docs/api for complete
    documentation for the API.

    The Graph API is made up of the objects in Facebook (e.g., people,
    pages, events, photos) and the connections between them (e.g.,
    friends, photo tags, and event RSVPs). This client provides access
    to those primitive types in a generic way. For example, given an
    OAuth access token, this will fetch the profile of the active user
    and the list of the user's friends:

       graph = facebook.GraphAPI(access_token)
       user = graph.get_object("me")
       friends = graph.get_connections(user["id"], "friends")

    You can see a list of all of the objects and connections supported
    by the API at http://developers.facebook.com/docs/reference/api/.

    You can obtain an access token via OAuth or by using the Facebook
    JavaScript SDK. See
    http://developers.facebook.com/docs/authentication/ for details.

    If you are using the JavaScript SDK, you can use the
    get_user_from_cookie() method below to get the OAuth access token
    for the active user from the cookie saved by the SDK.

    """
    def __init__(self, access_token=None, timeout=None):
        self.access_token = access_token
        self.timeout = timeout

    def get_object(self, id, **args):
        """Fetchs the given object from the graph."""
        return self.request(id, args)

    def get_objects(self, ids, **args):
        """Fetchs all of the given object from the graph.

        We return a map from ID to object. If any of the IDs are
        invalid, we raise an exception.
        """
        args["ids"] = ",".join(ids)
        return self.request("", args)

    def get_connections(self, id, connection_name, **args):
        """Fetchs the connections for given object."""
        return self.request(id + "/" + connection_name, args)

    def put_object(self, parent_object, connection_name, **data):
        """Writes the given object to the graph, connected to the given parent.

        For example,

            graph.put_object("me", "feed", message="Hello, world")

        writes "Hello, world" to the active user's wall. Likewise, this
        will comment on a the first post of the active user's feed:

            feed = graph.get_connections("me", "feed")
            post = feed["data"][0]
            graph.put_object(post["id"], "comments", message="First!")

        See http://developers.facebook.com/docs/api#publishing for all
        of the supported writeable objects.

        Certain write operations require extended permissions. For
        example, publishing to a user's feed requires the
        "publish_actions" permission. See
        http://developers.facebook.com/docs/publishing/ for details
        about publishing permissions.

        """
        assert self.access_token, "Write operations require an access token"
        return self.request(parent_object + "/" + connection_name,
                            post_args=data)

    def put_wall_post(self, message, attachment={}, profile_id="me"):
        """Writes a wall post to the given profile's wall.

        We default to writing to the authenticated user's wall if no
        profile_id is specified.

        attachment adds a structured attachment to the status message
        being posted to the Wall. It should be a dictionary of the form:

            {"name": "Link name"
             "link": "http://www.example.com/",
             "caption": "{*actor*} posted a new review",
             "description": "This is a longer description of the attachment",
             "picture": "http://www.example.com/thumbnail.jpg"}

        """
        return self.put_object(profile_id, "feed", message=message,
                               **attachment)

    def put_comment(self, object_id, message):
        """Writes the given comment on the given post."""
        return self.put_object(object_id, "comments", message=message)

    def put_like(self, object_id):
        """Likes the given post."""
        return self.put_object(object_id, "likes")

    def delete_object(self, id):
        """Deletes the object with the given ID from the graph."""
        self.request(id, post_args={"method": "delete"})

    def delete_request(self, user_id, request_id):
        """Deletes the Request with the given ID for the given user."""
        conn = httplib.HTTPSConnection('graph.facebook.com')

        url = '/%s_%s?%s' % (
            request_id,
            user_id,
            urllib.urlencode({'access_token': self.access_token}),
        )
        conn.request('DELETE', url)
        response = conn.getresponse()
        data = response.read()

        response = _parse_json(data)
        # Raise an error if we got one, but don't not if Facebook just
        # gave us a Bool value
        if (response and isinstance(response, dict) and response.get("error")):
            raise GraphAPIError(response)

        conn.close()

    def put_photo(self, image, message=None, album_id=None, **kwargs):
        """Uploads an image using multipart/form-data.

        image=File like object for the image
        message=Caption for your image
        album_id=None posts to /me/photos which uses or creates and uses
        an album for your application.

        """
        object_id = album_id or "me"
        #it would have been nice to reuse self.request;
        #but multipart is messy in urllib
        post_args = {
            'access_token': self.access_token,
            'source': image,
            'message': message,
        }
        post_args.update(kwargs)
        content_type, body = self._encode_multipart_form(post_args)
        req = urllib2.Request(("https://graph.facebook.com/%s/photos" %
                               object_id),
                              data=body)
        req.add_header('Content-Type', content_type)
        try:
            data = urllib2.urlopen(req).read()
        #For Python 3 use this:
        #except urllib2.HTTPError as e:
        except urllib2.HTTPError, e:
            data = e.read()  # Facebook sends OAuth errors as 400, and urllib2
                             # throws an exception, we want a GraphAPIError
        try:
            response = _parse_json(data)
            # Raise an error if we got one, but don't not if Facebook just
            # gave us a Bool value
            if (response and isinstance(response, dict) and
                    response.get("error")):
                raise GraphAPIError(response)
        except ValueError:
            response = data

        return response

    # based on: http://code.activestate.com/recipes/146306/
    def _encode_multipart_form(self, fields):
        """Encode files as 'multipart/form-data'.

        Fields are a dict of form name-> value. For files, value should
        be a file object. Other file-like objects might work and a fake
        name will be chosen.

        Returns (content_type, body) ready for httplib.HTTP instance.

        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields.items():
            logging.debug("Encoding %s, (%s)%s" % (key, type(value), value))
            if not value:
                continue
            L.append('--' + BOUNDARY)
            if hasattr(value, 'read') and callable(value.read):
                filename = getattr(value, 'name', '%s.jpg' % key)
                L.append(('Content-Disposition: form-data;'
                          'name="%s";'
                          'filename="%s"') % (key, filename))
                L.append('Content-Type: image/jpeg')
                value = value.read()
                logging.debug(type(value))
            else:
                L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            if isinstance(value, unicode):
                logging.debug("Convert to ascii")
                value = value.encode('ascii')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def request(self, path, args=None, post_args=None):
        """Fetches the given path in the Graph API.

        We translate args to a valid query string. If post_args is
        given, we send a POST request to the given path with the given
        arguments.

        """
        args = args or {}

        if self.access_token:
            if post_args is not None:
                post_args["access_token"] = self.access_token
            else:
                args["access_token"] = self.access_token
        post_data = None if post_args is None else urllib.urlencode(post_args)
        try:
            file = urllib2.urlopen("https://graph.facebook.com/" + path + "?" +
                                   urllib.urlencode(args),
                                   post_data, timeout=self.timeout)
        except urllib2.HTTPError, e:
            response = _parse_json(e.read())
            raise GraphAPIError(response)
        except TypeError:
            # Timeout support for Python <2.6
            if self.timeout:
                socket.setdefaulttimeout(self.timeout)
            file = urllib2.urlopen("https://graph.facebook.com/" + path + "?" +
                                   urllib.urlencode(args), post_data)
        try:
            fileInfo = file.info()
            if fileInfo.maintype == 'text':
                response = _parse_json(file.read())
            elif fileInfo.maintype == 'image':
                mimetype = fileInfo['content-type']
                response = {
                    "data": file.read(),
                    "mime-type": mimetype,
                    "url": file.url,
                }
            else:
                raise GraphAPIError('Maintype was not text or image')
        finally:
            file.close()
        if response and isinstance(response, dict) and response.get("error"):
            raise GraphAPIError(response["error"]["type"],
                                response["error"]["message"])
        return response

    def fql(self, query, args=None, post_args=None):
        """FQL query.

        Example query: "SELECT affiliations FROM user WHERE uid = me()"

        """
        args = args or {}
        if self.access_token:
            if post_args is not None:
                post_args["access_token"] = self.access_token
            else:
                args["access_token"] = self.access_token
        post_data = None if post_args is None else urllib.urlencode(post_args)

        """Check if query is a dict and
           use the multiquery method
           else use single query
        """
        if not isinstance(query, basestring):
            args["queries"] = query
            fql_method = 'fql.multiquery'
        else:
            args["query"] = query
            fql_method = 'fql.query'

        args["format"] = "json"

        try:
            file = urllib2.urlopen("https://api.facebook.com/method/" +
                                   fql_method + "?" + urllib.urlencode(args),
                                   post_data, timeout=self.timeout)
        except TypeError:
            # Timeout support for Python <2.6
            if self.timeout:
                socket.setdefaulttimeout(self.timeout)
            file = urllib2.urlopen("https://api.facebook.com/method/" +
                                   fql_method + "?" + urllib.urlencode(args),
                                   post_data)

        try:
            content = file.read()
            response = _parse_json(content)
            #Return a list if success, return a dictionary if failed
            if type(response) is dict and "error_code" in response:
                raise GraphAPIError(response)
        except Exception, e:
            raise e
        finally:
            file.close()

        return response

    def extend_access_token(self, app_id, app_secret):
        """
        Extends the expiration time of a valid OAuth access token. See
        <https://developers.facebook.com/roadmap/offline-access-removal/
        #extend_token>

        """
        args = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "fb_exchange_token",
            "fb_exchange_token": self.access_token,
        }
        response = urllib.urlopen("https://graph.facebook.com/oauth/"
                                  "access_token?" +
                                  urllib.urlencode(args)).read()
        query_str = parse_qs(response)
        if "access_token" in query_str:
            result = {"access_token": query_str["access_token"][0]}
            if "expires" in query_str:
                result["expires"] = query_str["expires"][0]
            return result
        else:
            response = json.loads(response)
            raise GraphAPIError(response)


class GraphAPIError(Exception):
    def __init__(self, result):
        #Exception.__init__(self, message)
        #self.type = type
        self.result = result
        try:
            self.type = result["error_code"]
        except:
            self.type = ""

        # OAuth 2.0 Draft 10
        try:
            self.message = result["error_description"]
        except:
            # OAuth 2.0 Draft 00
            try:
                self.message = result["error"]["message"]
            except:
                # REST server style
                try:
                    self.message = result["error_msg"]
                except:
                    self.message = result

        Exception.__init__(self, self.message)


def get_user_from_cookie(cookies, app_id, app_secret):
    """Parses the cookie set by the official Facebook JavaScript SDK.

    cookies should be a dictionary-like object mapping cookie names to
    cookie values.

    If the user is logged in via Facebook, we return a dictionary with
    the keys "uid" and "access_token". The former is the user's
    Facebook ID, and the latter can be used to make authenticated
    requests to the Graph API. If the user is not logged in, we
    return None.

    Download the official Facebook JavaScript SDK at
    http://github.com/facebook/connect-js/. Read more about Facebook
    authentication at
    http://developers.facebook.com/docs/authentication/.

    """
    cookie = cookies.get("fbsr_" + app_id, "")
    if not cookie:
        return None
    parsed_request = parse_signed_request(cookie, app_secret)
    if not parsed_request:
        return None
    try:
        result = get_access_token_from_code(parsed_request["code"], "",
                                            app_id, app_secret)
    except GraphAPIError:
        return None
    result["uid"] = parsed_request["user_id"]
    return result


def parse_signed_request(signed_request, app_secret):
    """ Return dictionary with signed request data.

    We return a dictionary containing the information in the
    signed_request. This includes a user_id if the user has authorised
    your application, as well as any information requested.

    If the signed_request is malformed or corrupted, False is returned.

    """
    try:
        encoded_sig, payload = map(str, signed_request.split('.', 1))

        sig = base64.urlsafe_b64decode(encoded_sig + "=" *
                                       ((4 - len(encoded_sig) % 4) % 4))
        data = base64.urlsafe_b64decode(payload + "=" *
                                        ((4 - len(payload) % 4) % 4))
    except IndexError:
        # Signed request was malformed.
        return False
    except TypeError:
        # Signed request had a corrupted payload.
        return False

    data = _parse_json(data)
    if data.get('algorithm', '').upper() != 'HMAC-SHA256':
        return False

    # HMAC can only handle ascii (byte) strings
    # http://bugs.python.org/issue5285
    app_secret = app_secret.encode('ascii')
    payload = payload.encode('ascii')

    expected_sig = hmac.new(app_secret,
                            msg=payload,
                            digestmod=hashlib.sha256).digest()
    if sig != expected_sig:
        return False

    return data


def auth_url(app_id, canvas_url, perms=None, **kwargs):
    url = "https://www.facebook.com/dialog/oauth?"
    kvps = {'client_id': app_id, 'redirect_uri': canvas_url}
    if perms:
        kvps['scope'] = ",".join(perms)
    kvps.update(kwargs)
    return url + urllib.urlencode(kvps)

def get_access_token_from_code(code, redirect_uri, app_id, app_secret):
    """Get an access token from the "code" returned from an OAuth dialog.

    Returns a dict containing the user-specific access token and its
    expiration date (if applicable).

    """
    args = {
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": app_id,
        "client_secret": app_secret,
    }
    # We would use GraphAPI.request() here, except for that the fact
    # that the response is a key-value pair, and not JSON.
    response = urllib.urlopen("https://graph.facebook.com/oauth/access_token" +
                              "?" + urllib.urlencode(args)).read()
    query_str = parse_qs(response)
    if "access_token" in query_str:
        result = {"access_token": query_str["access_token"][0]}
        if "expires" in query_str:
            result["expires"] = query_str["expires"][0]
        return result
    else:
        response = json.loads(response)
        raise GraphAPIError(response)


def get_app_access_token(app_id, app_secret):
    """Get the access_token for the app.

    This token can be used for insights and creating test users.

    app_id = retrieved from the developer page
    app_secret = retrieved from the developer page

    Returns the application access_token.

    """
    # Get an app access token
    args = {'grant_type': 'client_credentials',
            'client_id': app_id,
            'client_secret': app_secret}

    file = urllib2.urlopen("https://graph.facebook.com/oauth/access_token?" +
                           urllib.urlencode(args))

    try:
        result = file.read().split("=")[1]
    finally:
        file.close()

    return result

########NEW FILE########
__FILENAME__ = feedparser
"""Universal feed parser

Handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom 0.3, and Atom 1.0 feeds

Visit https://code.google.com/p/feedparser/ for the latest version
Visit http://packages.python.org/feedparser/ for the latest documentation

Required: Python 2.4 or later
Recommended: iconv_codec <http://cjkpython.i18n.org/>
"""

__version__ = "5.1.2"
__license__ = """
Copyright (c) 2010-2012 Kurt McKee <contactme@kurtmckee.org>
Copyright (c) 2002-2008 Mark Pilgrim
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""
__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__contributors__ = ["Jason Diamond <http://injektilo.org/>",
                    "John Beimler <http://john.beimler.org/>",
                    "Fazal Majid <http://www.majid.info/mylos/weblog/>",
                    "Aaron Swartz <http://aaronsw.com/>",
                    "Kevin Marks <http://epeus.blogspot.com/>",
                    "Sam Ruby <http://intertwingly.net/>",
                    "Ade Oshineye <http://blog.oshineye.com/>",
                    "Martin Pool <http://sourcefrog.net/>",
                    "Kurt McKee <http://kurtmckee.org/>"]

# HTTP "User-Agent" header to send to servers when downloading feeds.
# If you are embedding feedparser in a larger application, you should
# change this to your application name and URL.
USER_AGENT = "UniversalFeedParser/%s +https://code.google.com/p/feedparser/" % __version__

# HTTP "Accept" header to send to servers when downloading feeds.  If you don't
# want to send an Accept header, set this to None.
ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

# List of preferred XML parsers, by SAX driver name.  These will be tried first,
# but if they're not installed, Python will keep searching through its own list
# of pre-installed parsers until it finds one that supports everything we need.
PREFERRED_XML_PARSERS = ["drv_libxml2"]

# If you want feedparser to automatically run HTML markup through HTML Tidy, set
# this to 1.  Requires mxTidy <http://www.egenix.com/files/python/mxTidy.html>
# or utidylib <http://utidylib.berlios.de/>.
TIDY_MARKUP = 0

# List of Python interfaces for HTML Tidy, in order of preference.  Only useful
# if TIDY_MARKUP = 1
PREFERRED_TIDY_INTERFACES = ["uTidy", "mxTidy"]

# If you want feedparser to automatically resolve all relative URIs, set this
# to 1.
RESOLVE_RELATIVE_URIS = 1

# If you want feedparser to automatically sanitize all potentially unsafe
# HTML content, set this to 1.
SANITIZE_HTML = 1

# If you want feedparser to automatically parse microformat content embedded
# in entry contents, set this to 1
PARSE_MICROFORMATS = 1

# ---------- Python 3 modules (make it work if possible) ----------
try:
    import rfc822
except ImportError:
    from email import _parseaddr as rfc822

try:
    # Python 3.1 introduces bytes.maketrans and simultaneously
    # deprecates string.maketrans; use bytes.maketrans if possible
    _maketrans = bytes.maketrans
except (NameError, AttributeError):
    import string
    _maketrans = string.maketrans

# base64 support for Atom feeds that contain embedded binary data
try:
    import base64, binascii
except ImportError:
    base64 = binascii = None
else:
    # Python 3.1 deprecates decodestring in favor of decodebytes
    _base64decode = getattr(base64, 'decodebytes', base64.decodestring)

# _s2bytes: convert a UTF-8 str to bytes if the interpreter is Python 3
# _l2bytes: convert a list of ints to bytes if the interpreter is Python 3
try:
    if bytes is str:
        # In Python 2.5 and below, bytes doesn't exist (NameError)
        # In Python 2.6 and above, bytes and str are the same type
        raise NameError
except NameError:
    # Python 2
    def _s2bytes(s):
        return s
    def _l2bytes(l):
        return ''.join(map(chr, l))
else:
    # Python 3
    def _s2bytes(s):
        return bytes(s, 'utf8')
    def _l2bytes(l):
        return bytes(l)

# If you want feedparser to allow all URL schemes, set this to ()
# List culled from Python's urlparse documentation at:
#   http://docs.python.org/library/urlparse.html
# as well as from "URI scheme" at Wikipedia:
#   https://secure.wikimedia.org/wikipedia/en/wiki/URI_scheme
# Many more will likely need to be added!
ACCEPTABLE_URI_SCHEMES = (
    'file', 'ftp', 'gopher', 'h323', 'hdl', 'http', 'https', 'imap', 'magnet',
    'mailto', 'mms', 'news', 'nntp', 'prospero', 'rsync', 'rtsp', 'rtspu',
    'sftp', 'shttp', 'sip', 'sips', 'snews', 'svn', 'svn+ssh', 'telnet',
    'wais',
    # Additional common-but-unofficial schemes
    'aim', 'callto', 'cvs', 'facetime', 'feed', 'git', 'gtalk', 'irc', 'ircs',
    'irc6', 'itms', 'mms', 'msnim', 'skype', 'ssh', 'smb', 'svn', 'ymsg',
)
#ACCEPTABLE_URI_SCHEMES = ()

# ---------- required modules (should come with any Python distribution) ----------
import cgi
import codecs
import copy
import datetime
import re
import struct
import time
import types
import urllib
import urllib2
import urlparse
import warnings

from htmlentitydefs import name2codepoint, codepoint2name, entitydefs

try:
    from io import BytesIO as _StringIO
except ImportError:
    try:
        from cStringIO import StringIO as _StringIO
    except ImportError:
        from StringIO import StringIO as _StringIO

# ---------- optional modules (feedparser will work without these, but with reduced functionality) ----------

# gzip is included with most Python distributions, but may not be available if you compiled your own
try:
    import gzip
except ImportError:
    gzip = None
try:
    import zlib
except ImportError:
    zlib = None

# If a real XML parser is available, feedparser will attempt to use it.  feedparser has
# been tested with the built-in SAX parser and libxml2.  On platforms where the
# Python distribution does not come with an XML parser (such as Mac OS X 10.2 and some
# versions of FreeBSD), feedparser will quietly fall back on regex-based parsing.
try:
    import xml.sax
    from xml.sax.saxutils import escape as _xmlescape
except ImportError:
    _XML_AVAILABLE = 0
    def _xmlescape(data,entities={}):
        data = data.replace('&', '&amp;')
        data = data.replace('>', '&gt;')
        data = data.replace('<', '&lt;')
        for char, entity in entities:
            data = data.replace(char, entity)
        return data
else:
    try:
        xml.sax.make_parser(PREFERRED_XML_PARSERS) # test for valid parsers
    except xml.sax.SAXReaderNotAvailable:
        _XML_AVAILABLE = 0
    else:
        _XML_AVAILABLE = 1

# sgmllib is not available by default in Python 3; if the end user doesn't have
# it available then we'll lose illformed XML parsing, content santizing, and
# microformat support (at least while feedparser depends on BeautifulSoup).
try:
    import sgmllib
except ImportError:
    # This is probably Python 3, which doesn't include sgmllib anymore
    _SGML_AVAILABLE = 0

    # Mock sgmllib enough to allow subclassing later on
    class sgmllib(object):
        class SGMLParser(object):
            def goahead(self, i):
                pass
            def parse_starttag(self, i):
                pass
else:
    _SGML_AVAILABLE = 1

    # sgmllib defines a number of module-level regular expressions that are
    # insufficient for the XML parsing feedparser needs. Rather than modify
    # the variables directly in sgmllib, they're defined here using the same
    # names, and the compiled code objects of several sgmllib.SGMLParser
    # methods are copied into _BaseHTMLProcessor so that they execute in
    # feedparser's scope instead of sgmllib's scope.
    charref = re.compile('&#(\d+|[xX][0-9a-fA-F]+);')
    tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
    attrfind = re.compile(
        r'\s*([a-zA-Z_][-:.a-zA-Z_0-9]*)[$]?(\s*=\s*'
        r'(\'[^\']*\'|"[^"]*"|[][\-a-zA-Z0-9./,:;+*%?!&$\(\)_#=~\'"@]*))?'
    )

    # Unfortunately, these must be copied over to prevent NameError exceptions
    entityref = sgmllib.entityref
    incomplete = sgmllib.incomplete
    interesting = sgmllib.interesting
    shorttag = sgmllib.shorttag
    shorttagopen = sgmllib.shorttagopen
    starttagopen = sgmllib.starttagopen

    class _EndBracketRegEx:
        def __init__(self):
            # Overriding the built-in sgmllib.endbracket regex allows the
            # parser to find angle brackets embedded in element attributes.
            self.endbracket = re.compile('''([^'"<>]|"[^"]*"(?=>|/|\s|\w+=)|'[^']*'(?=>|/|\s|\w+=))*(?=[<>])|.*?(?=[<>])''')
        def search(self, target, index=0):
            match = self.endbracket.match(target, index)
            if match is not None:
                # Returning a new object in the calling thread's context
                # resolves a thread-safety.
                return EndBracketMatch(match)
            return None
    class EndBracketMatch:
        def __init__(self, match):
            self.match = match
        def start(self, n):
            return self.match.end(n)
    endbracket = _EndBracketRegEx()


# iconv_codec provides support for more character encodings.
# It's available from http://cjkpython.i18n.org/
try:
    import iconv_codec
except ImportError:
    pass

# chardet library auto-detects character encodings
# Download from http://chardet.feedparser.org/
try:
    import chardet
except ImportError:
    chardet = None

# BeautifulSoup is used to extract microformat content from HTML
# feedparser is tested using BeautifulSoup 3.2.0
# http://www.crummy.com/software/BeautifulSoup/
try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    PARSE_MICROFORMATS = False

try:
    # the utf_32 codec was introduced in Python 2.6; it's necessary to
    # check this as long as feedparser supports Python 2.4 and 2.5
    codecs.lookup('utf_32')
except LookupError:
    _UTF32_AVAILABLE = False
else:
    _UTF32_AVAILABLE = True

# ---------- don't touch these ----------
class ThingsNobodyCaresAboutButMe(Exception): pass
class CharacterEncodingOverride(ThingsNobodyCaresAboutButMe): pass
class CharacterEncodingUnknown(ThingsNobodyCaresAboutButMe): pass
class NonXMLContentType(ThingsNobodyCaresAboutButMe): pass
class UndeclaredNamespace(Exception): pass

SUPPORTED_VERSIONS = {'': u'unknown',
                      'rss090': u'RSS 0.90',
                      'rss091n': u'RSS 0.91 (Netscape)',
                      'rss091u': u'RSS 0.91 (Userland)',
                      'rss092': u'RSS 0.92',
                      'rss093': u'RSS 0.93',
                      'rss094': u'RSS 0.94',
                      'rss20': u'RSS 2.0',
                      'rss10': u'RSS 1.0',
                      'rss': u'RSS (unknown version)',
                      'atom01': u'Atom 0.1',
                      'atom02': u'Atom 0.2',
                      'atom03': u'Atom 0.3',
                      'atom10': u'Atom 1.0',
                      'atom': u'Atom (unknown version)',
                      'cdf': u'CDF',
                      }

class FeedParserDict(dict):
    keymap = {'channel': 'feed',
              'items': 'entries',
              'guid': 'id',
              'date': 'updated',
              'date_parsed': 'updated_parsed',
              'description': ['summary', 'subtitle'],
              'description_detail': ['summary_detail', 'subtitle_detail'],
              'url': ['href'],
              'modified': 'updated',
              'modified_parsed': 'updated_parsed',
              'issued': 'published',
              'issued_parsed': 'published_parsed',
              'copyright': 'rights',
              'copyright_detail': 'rights_detail',
              'tagline': 'subtitle',
              'tagline_detail': 'subtitle_detail'}
    def __getitem__(self, key):
        if key == 'category':
            try:
                return dict.__getitem__(self, 'tags')[0]['term']
            except IndexError:
                raise KeyError, "object doesn't have key 'category'"
        elif key == 'enclosures':
            norel = lambda link: FeedParserDict([(name,value) for (name,value) in link.items() if name!='rel'])
            return [norel(link) for link in dict.__getitem__(self, 'links') if link['rel']==u'enclosure']
        elif key == 'license':
            for link in dict.__getitem__(self, 'links'):
                if link['rel']==u'license' and 'href' in link:
                    return link['href']
        elif key == 'updated':
            # Temporarily help developers out by keeping the old
            # broken behavior that was reported in issue 310.
            # This fix was proposed in issue 328.
            if not dict.__contains__(self, 'updated') and \
                dict.__contains__(self, 'published'):
                warnings.warn("To avoid breaking existing software while "
                    "fixing issue 310, a temporary mapping has been created "
                    "from `updated` to `published` if `updated` doesn't "
                    "exist. This fallback will be removed in a future version "
                    "of feedparser.", DeprecationWarning)
                return dict.__getitem__(self, 'published')
            return dict.__getitem__(self, 'updated')
        elif key == 'updated_parsed':
            if not dict.__contains__(self, 'updated_parsed') and \
                dict.__contains__(self, 'published_parsed'):
                warnings.warn("To avoid breaking existing software while "
                    "fixing issue 310, a temporary mapping has been created "
                    "from `updated_parsed` to `published_parsed` if "
                    "`updated_parsed` doesn't exist. This fallback will be "
                    "removed in a future version of feedparser.",
                    DeprecationWarning)
                return dict.__getitem__(self, 'published_parsed')
            return dict.__getitem__(self, 'updated_parsed')
        else:
            realkey = self.keymap.get(key, key)
            if isinstance(realkey, list):
                for k in realkey:
                    if dict.__contains__(self, k):
                        return dict.__getitem__(self, k)
            elif dict.__contains__(self, realkey):
                return dict.__getitem__(self, realkey)
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        if key in ('updated', 'updated_parsed'):
            # Temporarily help developers out by keeping the old
            # broken behavior that was reported in issue 310.
            # This fix was proposed in issue 328.
            return dict.__contains__(self, key)
        try:
            self.__getitem__(key)
        except KeyError:
            return False
        else:
            return True

    has_key = __contains__

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __setitem__(self, key, value):
        key = self.keymap.get(key, key)
        if isinstance(key, list):
            key = key[0]
        return dict.__setitem__(self, key, value)

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
            return value
        return self[key]

    def __getattr__(self, key):
        # __getattribute__() is called first; this will be called
        # only if an attribute was not already found
        try:
            return self.__getitem__(key)
        except KeyError:
            raise AttributeError, "object has no attribute '%s'" % key

    def __hash__(self):
        return id(self)

_cp1252 = {
    128: unichr(8364), # euro sign
    130: unichr(8218), # single low-9 quotation mark
    131: unichr( 402), # latin small letter f with hook
    132: unichr(8222), # double low-9 quotation mark
    133: unichr(8230), # horizontal ellipsis
    134: unichr(8224), # dagger
    135: unichr(8225), # double dagger
    136: unichr( 710), # modifier letter circumflex accent
    137: unichr(8240), # per mille sign
    138: unichr( 352), # latin capital letter s with caron
    139: unichr(8249), # single left-pointing angle quotation mark
    140: unichr( 338), # latin capital ligature oe
    142: unichr( 381), # latin capital letter z with caron
    145: unichr(8216), # left single quotation mark
    146: unichr(8217), # right single quotation mark
    147: unichr(8220), # left double quotation mark
    148: unichr(8221), # right double quotation mark
    149: unichr(8226), # bullet
    150: unichr(8211), # en dash
    151: unichr(8212), # em dash
    152: unichr( 732), # small tilde
    153: unichr(8482), # trade mark sign
    154: unichr( 353), # latin small letter s with caron
    155: unichr(8250), # single right-pointing angle quotation mark
    156: unichr( 339), # latin small ligature oe
    158: unichr( 382), # latin small letter z with caron
    159: unichr( 376), # latin capital letter y with diaeresis
}

_urifixer = re.compile('^([A-Za-z][A-Za-z0-9+-.]*://)(/*)(.*?)')
def _urljoin(base, uri):
    uri = _urifixer.sub(r'\1\3', uri)
    #try:
    if not isinstance(uri, unicode):
        uri = uri.decode('utf-8', 'ignore')
    uri = urlparse.urljoin(base, uri)
    if not isinstance(uri, unicode):
        return uri.decode('utf-8', 'ignore')
    return uri
    #except:
    #    uri = urlparse.urlunparse([urllib.quote(part) for part in urlparse.urlparse(uri)])
    #    return urlparse.urljoin(base, uri)

class _FeedParserMixin:
    namespaces = {
        '': '',
        'http://backend.userland.com/rss': '',
        'http://blogs.law.harvard.edu/tech/rss': '',
        'http://purl.org/rss/1.0/': '',
        'http://my.netscape.com/rdf/simple/0.9/': '',
        'http://example.com/newformat#': '',
        'http://example.com/necho': '',
        'http://purl.org/echo/': '',
        'uri/of/echo/namespace#': '',
        'http://purl.org/pie/': '',
        'http://purl.org/atom/ns#': '',
        'http://www.w3.org/2005/Atom': '',
        'http://purl.org/rss/1.0/modules/rss091#': '',

        'http://webns.net/mvcb/':                                'admin',
        'http://purl.org/rss/1.0/modules/aggregation/':          'ag',
        'http://purl.org/rss/1.0/modules/annotate/':             'annotate',
        'http://media.tangent.org/rss/1.0/':                     'audio',
        'http://backend.userland.com/blogChannelModule':         'blogChannel',
        'http://web.resource.org/cc/':                           'cc',
        'http://backend.userland.com/creativeCommonsRssModule':  'creativeCommons',
        'http://purl.org/rss/1.0/modules/company':               'co',
        'http://purl.org/rss/1.0/modules/content/':              'content',
        'http://my.theinfo.org/changed/1.0/rss/':                'cp',
        'http://purl.org/dc/elements/1.1/':                      'dc',
        'http://purl.org/dc/terms/':                             'dcterms',
        'http://purl.org/rss/1.0/modules/email/':                'email',
        'http://purl.org/rss/1.0/modules/event/':                'ev',
        'http://rssnamespace.org/feedburner/ext/1.0':            'feedburner',
        'http://freshmeat.net/rss/fm/':                          'fm',
        'http://xmlns.com/foaf/0.1/':                            'foaf',
        'http://www.w3.org/2003/01/geo/wgs84_pos#':              'geo',
        'http://postneo.com/icbm/':                              'icbm',
        'http://purl.org/rss/1.0/modules/image/':                'image',
        'http://www.itunes.com/DTDs/PodCast-1.0.dtd':            'itunes',
        'http://example.com/DTDs/PodCast-1.0.dtd':               'itunes',
        'http://purl.org/rss/1.0/modules/link/':                 'l',
        'http://search.yahoo.com/mrss':                          'media',
        # Version 1.1.2 of the Media RSS spec added the trailing slash on the namespace
        'http://search.yahoo.com/mrss/':                         'media',
        'http://madskills.com/public/xml/rss/module/pingback/':  'pingback',
        'http://prismstandard.org/namespaces/1.2/basic/':        'prism',
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#':           'rdf',
        'http://www.w3.org/2000/01/rdf-schema#':                 'rdfs',
        'http://purl.org/rss/1.0/modules/reference/':            'ref',
        'http://purl.org/rss/1.0/modules/richequiv/':            'reqv',
        'http://purl.org/rss/1.0/modules/search/':               'search',
        'http://purl.org/rss/1.0/modules/slash/':                'slash',
        'http://schemas.xmlsoap.org/soap/envelope/':             'soap',
        'http://purl.org/rss/1.0/modules/servicestatus/':        'ss',
        'http://hacks.benhammersley.com/rss/streaming/':         'str',
        'http://purl.org/rss/1.0/modules/subscription/':         'sub',
        'http://purl.org/rss/1.0/modules/syndication/':          'sy',
        'http://schemas.pocketsoap.com/rss/myDescModule/':       'szf',
        'http://purl.org/rss/1.0/modules/taxonomy/':             'taxo',
        'http://purl.org/rss/1.0/modules/threading/':            'thr',
        'http://purl.org/rss/1.0/modules/textinput/':            'ti',
        'http://madskills.com/public/xml/rss/module/trackback/': 'trackback',
        'http://wellformedweb.org/commentAPI/':                  'wfw',
        'http://purl.org/rss/1.0/modules/wiki/':                 'wiki',
        'http://www.w3.org/1999/xhtml':                          'xhtml',
        'http://www.w3.org/1999/xlink':                          'xlink',
        'http://www.w3.org/XML/1998/namespace':                  'xml',
    }
    _matchnamespaces = {}

    can_be_relative_uri = set(['link', 'id', 'wfw_comment', 'wfw_commentrss', 'docs', 'url', 'href', 'comments', 'icon', 'logo'])
    can_contain_relative_uris = set(['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description'])
    can_contain_dangerous_markup = set(['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description'])
    html_types = [u'text/html', u'application/xhtml+xml']

    def __init__(self, baseuri=None, baselang=None, encoding=u'utf-8'):
        if not self._matchnamespaces:
            for k, v in self.namespaces.items():
                self._matchnamespaces[k.lower()] = v
        self.feeddata = FeedParserDict() # feed-level data
        self.encoding = encoding # character encoding
        self.entries = [] # list of entry-level data
        self.version = u'' # feed type/version, see SUPPORTED_VERSIONS
        self.namespacesInUse = {} # dictionary of namespaces defined by the feed

        # the following are used internally to track state;
        # this is really out of control and should be refactored
        self.infeed = 0
        self.inentry = 0
        self.incontent = 0
        self.intextinput = 0
        self.inimage = 0
        self.inauthor = 0
        self.incontributor = 0
        self.inpublisher = 0
        self.insource = 0
        self.sourcedata = FeedParserDict()
        self.contentparams = FeedParserDict()
        self._summaryKey = None
        self.namespacemap = {}
        self.elementstack = []
        self.basestack = []
        self.langstack = []
        self.baseuri = baseuri or u''
        self.lang = baselang or None
        self.svgOK = 0
        self.title_depth = -1
        self.depth = 0
        if baselang:
            self.feeddata['language'] = baselang.replace('_','-')

        # A map of the following form:
        #     {
        #         object_that_value_is_set_on: {
        #             property_name: depth_of_node_property_was_extracted_from,
        #             other_property: depth_of_node_property_was_extracted_from,
        #         },
        #     }
        self.property_depth_map = {}

    def _normalize_attributes(self, kv):
        k = kv[0].lower()
        v = k in ('rel', 'type') and kv[1].lower() or kv[1]
        # the sgml parser doesn't handle entities in attributes, nor
        # does it pass the attribute values through as unicode, while
        # strict xml parsers do -- account for this difference
        if isinstance(self, _LooseFeedParser):
            v = v.replace('&amp;', '&')
            if not isinstance(v, unicode):
                v = v.decode('utf-8')
        return (k, v)

    def unknown_starttag(self, tag, attrs):
        # increment depth counter
        self.depth += 1

        # normalize attrs
        attrs = map(self._normalize_attributes, attrs)

        # track xml:base and xml:lang
        attrsD = dict(attrs)
        baseuri = attrsD.get('xml:base', attrsD.get('base')) or self.baseuri
        if not isinstance(baseuri, unicode):
            baseuri = baseuri.decode(self.encoding, 'ignore')
        # ensure that self.baseuri is always an absolute URI that
        # uses a whitelisted URI scheme (e.g. not `javscript:`)
        if self.baseuri:
            self.baseuri = _makeSafeAbsoluteURI(self.baseuri, baseuri) or self.baseuri
        else:
            self.baseuri = _urljoin(self.baseuri, baseuri)
        lang = attrsD.get('xml:lang', attrsD.get('lang'))
        if lang == '':
            # xml:lang could be explicitly set to '', we need to capture that
            lang = None
        elif lang is None:
            # if no xml:lang is specified, use parent lang
            lang = self.lang
        if lang:
            if tag in ('feed', 'rss', 'rdf:RDF'):
                self.feeddata['language'] = lang.replace('_','-')
        self.lang = lang
        self.basestack.append(self.baseuri)
        self.langstack.append(lang)

        # track namespaces
        for prefix, uri in attrs:
            if prefix.startswith('xmlns:'):
                self.trackNamespace(prefix[6:], uri)
            elif prefix == 'xmlns':
                self.trackNamespace(None, uri)

        # track inline content
        if self.incontent and not self.contentparams.get('type', u'xml').endswith(u'xml'):
            if tag in ('xhtml:div', 'div'):
                return # typepad does this 10/2007
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = u'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == u'application/xhtml+xml':
            if tag.find(':') <> -1:
                prefix, tag = tag.split(':', 1)
                namespace = self.namespacesInUse.get(prefix, '')
                if tag=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                    attrs.append(('xmlns',namespace))
                if tag=='svg' and namespace=='http://www.w3.org/2000/svg':
                    attrs.append(('xmlns',namespace))
            if tag == 'svg':
                self.svgOK += 1
            return self.handle_data('<%s%s>' % (tag, self.strattrs(attrs)), escape=0)

        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # special hack for better tracking of empty textinput/image elements in illformed feeds
        if (not prefix) and tag not in ('title', 'link', 'description', 'name'):
            self.intextinput = 0
        if (not prefix) and tag not in ('title', 'link', 'description', 'url', 'href', 'width', 'height'):
            self.inimage = 0

        # call special handler (if defined) or default handler
        methodname = '_start_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            return method(attrsD)
        except AttributeError:
            # Since there's no handler or something has gone wrong we explicitly add the element and its attributes
            unknown_tag = prefix + suffix
            if len(attrsD) == 0:
                # No attributes so merge it into the encosing dictionary
                return self.push(unknown_tag, 1)
            else:
                # Has attributes so create it in its own dictionary
                context = self._getContext()
                context[unknown_tag] = attrsD

    def unknown_endtag(self, tag):
        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'
        if suffix == 'svg' and self.svgOK:
            self.svgOK -= 1

        # call special handler (if defined) or default handler
        methodname = '_end_' + prefix + suffix
        try:
            if self.svgOK:
                raise AttributeError()
            method = getattr(self, methodname)
            method()
        except AttributeError:
            self.pop(prefix + suffix)

        # track inline content
        if self.incontent and not self.contentparams.get('type', u'xml').endswith(u'xml'):
            # element declared itself as escaped markup, but it isn't really
            if tag in ('xhtml:div', 'div'):
                return # typepad does this 10/2007
            self.contentparams['type'] = u'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == u'application/xhtml+xml':
            tag = tag.split(':')[-1]
            self.handle_data('</%s>' % tag, escape=0)

        # track xml:base and xml:lang going out of scope
        if self.basestack:
            self.basestack.pop()
            if self.basestack and self.basestack[-1]:
                self.baseuri = self.basestack[-1]
        if self.langstack:
            self.langstack.pop()
            if self.langstack: # and (self.langstack[-1] is not None):
                self.lang = self.langstack[-1]

        self.depth -= 1

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        if not self.elementstack:
            return
        ref = ref.lower()
        if ref in ('34', '38', '39', '60', '62', 'x22', 'x26', 'x27', 'x3c', 'x3e'):
            text = '&#%s;' % ref
        else:
            if ref[0] == 'x':
                c = int(ref[1:], 16)
            else:
                c = int(ref)
            text = unichr(c).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        if not self.elementstack:
            return
        if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
            text = '&%s;' % ref
        elif ref in self.entities:
            text = self.entities[ref]
            if text.startswith('&#') and text.endswith(';'):
                return self.handle_entityref(text)
        else:
            try:
                name2codepoint[ref]
            except KeyError:
                text = '&%s;' % ref
            else:
                text = unichr(name2codepoint[ref]).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_data(self, text, escape=1):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack:
            return
        if escape and self.contentparams.get('type') == u'application/xhtml+xml':
            text = _xmlescape(text)
        self.elementstack[-1][2].append(text)

    def handle_comment(self, text):
        # called for each comment, e.g. <!-- insert message here -->
        pass

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        pass

    def handle_decl(self, text):
        pass

    def parse_declaration(self, i):
        # override internal declaration handler to handle CDATA blocks
        if self.rawdata[i:i+9] == '<![CDATA[':
            k = self.rawdata.find(']]>', i)
            if k == -1:
                # CDATA block began but didn't finish
                k = len(self.rawdata)
                return k
            self.handle_data(_xmlescape(self.rawdata[i+9:k]), 0)
            return k+3
        else:
            k = self.rawdata.find('>', i)
            if k >= 0:
                return k+1
            else:
                # We have an incomplete CDATA block.
                return k

    def mapContentType(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text' or contentType == 'plain':
            contentType = u'text/plain'
        elif contentType == 'html':
            contentType = u'text/html'
        elif contentType == 'xhtml':
            contentType = u'application/xhtml+xml'
        return contentType

    def trackNamespace(self, prefix, uri):
        loweruri = uri.lower()
        if not self.version:
            if (prefix, loweruri) == (None, 'http://my.netscape.com/rdf/simple/0.9/'):
                self.version = u'rss090'
            elif loweruri == 'http://purl.org/rss/1.0/':
                self.version = u'rss10'
            elif loweruri == 'http://www.w3.org/2005/atom':
                self.version = u'atom10'
        if loweruri.find(u'backend.userland.com/rss') <> -1:
            # match any backend.userland.com namespace
            uri = u'http://backend.userland.com/rss'
            loweruri = uri
        if loweruri in self._matchnamespaces:
            self.namespacemap[prefix] = self._matchnamespaces[loweruri]
            self.namespacesInUse[self._matchnamespaces[loweruri]] = uri
        else:
            self.namespacesInUse[prefix or ''] = uri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri or u'', uri)

    def decodeEntities(self, element, data):
        return data

    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (t[0],_xmlescape(t[1],{'"':'&quot;'})) for t in attrs])

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element, stripWhitespace=1):
        if not self.elementstack:
            return
        if self.elementstack[-1][0] != element:
            return

        element, expectingText, pieces = self.elementstack.pop()

        if self.version == u'atom10' and self.contentparams.get('type', u'text') == u'application/xhtml+xml':
            # remove enclosing child element, but only if it is a <div> and
            # only if all the remaining content is nested underneath it.
            # This means that the divs would be retained in the following:
            #    <div>foo</div><div>bar</div>
            while pieces and len(pieces)>1 and not pieces[-1].strip():
                del pieces[-1]
            while pieces and len(pieces)>1 and not pieces[0].strip():
                del pieces[0]
            if pieces and (pieces[0] == '<div>' or pieces[0].startswith('<div ')) and pieces[-1]=='</div>':
                depth = 0
                for piece in pieces[:-1]:
                    if piece.startswith('</'):
                        depth -= 1
                        if depth == 0:
                            break
                    elif piece.startswith('<') and not piece.endswith('/>'):
                        depth += 1
                else:
                    pieces = pieces[1:-1]

        # Ensure each piece is a str for Python 3
        for (i, v) in enumerate(pieces):
            if not isinstance(v, unicode):
                pieces[i] = v.decode('utf-8')

        output = u''.join(pieces)
        if stripWhitespace:
            output = output.strip()
        if not expectingText:
            return output

        # decode base64 content
        if base64 and self.contentparams.get('base64', 0):
            try:
                output = _base64decode(output)
            except binascii.Error:
                pass
            except binascii.Incomplete:
                pass
            except TypeError:
                # In Python 3, base64 takes and outputs bytes, not str
                # This may not be the most correct way to accomplish this
                output = _base64decode(output.encode('utf-8')).decode('utf-8')

        # resolve relative URIs
        if (element in self.can_be_relative_uri) and output:
            output = self.resolveURI(output)

        # decode entities within embedded markup
        if not self.contentparams.get('base64', 0):
            output = self.decodeEntities(element, output)

        # some feed formats require consumers to guess
        # whether the content is html or plain text
        if not self.version.startswith(u'atom') and self.contentparams.get('type') == u'text/plain':
            if self.lookslikehtml(output):
                self.contentparams['type'] = u'text/html'

        # remove temporary cruft from contentparams
        try:
            del self.contentparams['mode']
        except KeyError:
            pass
        try:
            del self.contentparams['base64']
        except KeyError:
            pass

        is_htmlish = self.mapContentType(self.contentparams.get('type', u'text/html')) in self.html_types
        # resolve relative URIs within embedded markup
        if is_htmlish and RESOLVE_RELATIVE_URIS:
            if element in self.can_contain_relative_uris:
                output = _resolveRelativeURIs(output, self.baseuri, self.encoding, self.contentparams.get('type', u'text/html'))

        # parse microformats
        # (must do this before sanitizing because some microformats
        # rely on elements that we sanitize)
        if PARSE_MICROFORMATS and is_htmlish and element in ['content', 'description', 'summary']:
            mfresults = _parseMicroformats(output, self.baseuri, self.encoding)
            if mfresults:
                for tag in mfresults.get('tags', []):
                    self._addTag(tag['term'], tag['scheme'], tag['label'])
                for enclosure in mfresults.get('enclosures', []):
                    self._start_enclosure(enclosure)
                for xfn in mfresults.get('xfn', []):
                    self._addXFN(xfn['relationships'], xfn['href'], xfn['name'])
                vcard = mfresults.get('vcard')
                if vcard:
                    self._getContext()['vcard'] = vcard

        # sanitize embedded markup
        if is_htmlish and SANITIZE_HTML:
            if element in self.can_contain_dangerous_markup:
                output = _sanitizeHTML(output, self.encoding, self.contentparams.get('type', u'text/html'))

        if self.encoding and not isinstance(output, unicode):
            output = output.decode(self.encoding, 'ignore')

        # address common error where people take data that is already
        # utf-8, presume that it is iso-8859-1, and re-encode it.
        if self.encoding in (u'utf-8', u'utf-8_INVALID_PYTHON_3') and isinstance(output, unicode):
            try:
                output = output.encode('iso-8859-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        # map win-1252 extensions to the proper code points
        if isinstance(output, unicode):
            output = output.translate(_cp1252)

        # categories/tags/keywords/whatever are handled in _end_category
        if element == 'category':
            return output

        if element == 'title' and -1 < self.title_depth <= self.depth:
            return output

        # store output in appropriate place(s)
        if self.inentry and not self.insource:
            if element == 'content':
                self.entries[-1].setdefault(element, [])
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                self.entries[-1][element].append(contentparams)
            elif element == 'link':
                if not self.inimage:
                    # query variables in urls in link elements are improperly
                    # converted from `?a=1&b=2` to `?a=1&b;=2` as if they're
                    # unhandled character references. fix this special case.
                    output = re.sub("&([A-Za-z0-9_]+);", "&\g<1>", output)
                    self.entries[-1][element] = output
                    if output:
                        self.entries[-1]['links'][-1]['href'] = output
            else:
                if element == 'description':
                    element = 'summary'
                old_value_depth = self.property_depth_map.setdefault(self.entries[-1], {}).get(element)
                if old_value_depth is None or self.depth <= old_value_depth:
                    self.property_depth_map[self.entries[-1]][element] = self.depth
                    self.entries[-1][element] = output
                if self.incontent:
                    contentparams = copy.deepcopy(self.contentparams)
                    contentparams['value'] = output
                    self.entries[-1][element + '_detail'] = contentparams
        elif (self.infeed or self.insource):# and (not self.intextinput) and (not self.inimage):
            context = self._getContext()
            if element == 'description':
                element = 'subtitle'
            context[element] = output
            if element == 'link':
                # fix query variables; see above for the explanation
                output = re.sub("&([A-Za-z0-9_]+);", "&\g<1>", output)
                context[element] = output
                context['links'][-1]['href'] = output
            elif self.incontent:
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                context[element + '_detail'] = contentparams
        return output

    def pushContent(self, tag, attrsD, defaultContentType, expectingText):
        self.incontent += 1
        if self.lang:
            self.lang=self.lang.replace('_','-')
        self.contentparams = FeedParserDict({
            'type': self.mapContentType(attrsD.get('type', defaultContentType)),
            'language': self.lang,
            'base': self.baseuri})
        self.contentparams['base64'] = self._isBase64(attrsD, self.contentparams)
        self.push(tag, expectingText)

    def popContent(self, tag):
        value = self.pop(tag)
        self.incontent -= 1
        self.contentparams.clear()
        return value

    # a number of elements in a number of RSS variants are nominally plain
    # text, but this is routinely ignored.  This is an attempt to detect
    # the most common cases.  As false positives often result in silent
    # data loss, this function errs on the conservative side.
    @staticmethod
    def lookslikehtml(s):
        # must have a close tag or an entity reference to qualify
        if not (re.search(r'</(\w+)>',s) or re.search("&#?\w+;",s)):
            return

        # all tags must be in a restricted subset of valid HTML tags
        if filter(lambda t: t.lower() not in _HTMLSanitizer.acceptable_elements,
            re.findall(r'</?(\w+)',s)):
            return

        # all entities must have been defined as valid HTML entities
        if filter(lambda e: e not in entitydefs.keys(), re.findall(r'&(\w+);', s)):
            return

        return 1

    def _mapToStandardPrefix(self, name):
        colonpos = name.find(':')
        if colonpos <> -1:
            prefix = name[:colonpos]
            suffix = name[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            name = prefix + ':' + suffix
        return name

    def _getAttribute(self, attrsD, name):
        return attrsD.get(self._mapToStandardPrefix(name))

    def _isBase64(self, attrsD, contentparams):
        if attrsD.get('mode', '') == 'base64':
            return 1
        if self.contentparams['type'].startswith(u'text/'):
            return 0
        if self.contentparams['type'].endswith(u'+xml'):
            return 0
        if self.contentparams['type'].endswith(u'/xml'):
            return 0
        return 1

    def _itsAnHrefDamnIt(self, attrsD):
        href = attrsD.get('url', attrsD.get('uri', attrsD.get('href', None)))
        if href:
            try:
                del attrsD['url']
            except KeyError:
                pass
            try:
                del attrsD['uri']
            except KeyError:
                pass
            attrsD['href'] = href
        return attrsD

    def _save(self, key, value, overwrite=False):
        context = self._getContext()
        if overwrite:
            context[key] = value
        else:
            context.setdefault(key, value)

    def _start_rss(self, attrsD):
        versionmap = {'0.91': u'rss091u',
                      '0.92': u'rss092',
                      '0.93': u'rss093',
                      '0.94': u'rss094'}
        #If we're here then this is an RSS feed.
        #If we don't have a version or have a version that starts with something
        #other than RSS then there's been a mistake. Correct it.
        if not self.version or not self.version.startswith(u'rss'):
            attr_version = attrsD.get('version', '')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            elif attr_version.startswith('2.'):
                self.version = u'rss20'
            else:
                self.version = u'rss'

    def _start_channel(self, attrsD):
        self.infeed = 1
        self._cdf_common(attrsD)

    def _cdf_common(self, attrsD):
        if 'lastmod' in attrsD:
            self._start_modified({})
            self.elementstack[-1][-1] = attrsD['lastmod']
            self._end_modified()
        if 'href' in attrsD:
            self._start_link({})
            self.elementstack[-1][-1] = attrsD['href']
            self._end_link()

    def _start_feed(self, attrsD):
        self.infeed = 1
        versionmap = {'0.1': u'atom01',
                      '0.2': u'atom02',
                      '0.3': u'atom03'}
        if not self.version:
            attr_version = attrsD.get('version')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            else:
                self.version = u'atom'

    def _end_channel(self):
        self.infeed = 0
    _end_feed = _end_channel

    def _start_image(self, attrsD):
        context = self._getContext()
        if not self.inentry:
            context.setdefault('image', FeedParserDict())
        self.inimage = 1
        self.title_depth = -1
        self.push('image', 0)

    def _end_image(self):
        self.pop('image')
        self.inimage = 0

    def _start_textinput(self, attrsD):
        context = self._getContext()
        context.setdefault('textinput', FeedParserDict())
        self.intextinput = 1
        self.title_depth = -1
        self.push('textinput', 0)
    _start_textInput = _start_textinput

    def _end_textinput(self):
        self.pop('textinput')
        self.intextinput = 0
    _end_textInput = _end_textinput

    def _start_author(self, attrsD):
        self.inauthor = 1
        self.push('author', 1)
        # Append a new FeedParserDict when expecting an author
        context = self._getContext()
        context.setdefault('authors', [])
        context['authors'].append(FeedParserDict())
    _start_managingeditor = _start_author
    _start_dc_author = _start_author
    _start_dc_creator = _start_author
    _start_itunes_author = _start_author

    def _end_author(self):
        self.pop('author')
        self.inauthor = 0
        self._sync_author_detail()
    _end_managingeditor = _end_author
    _end_dc_author = _end_author
    _end_dc_creator = _end_author
    _end_itunes_author = _end_author

    def _start_itunes_owner(self, attrsD):
        self.inpublisher = 1
        self.push('publisher', 0)

    def _end_itunes_owner(self):
        self.pop('publisher')
        self.inpublisher = 0
        self._sync_author_detail('publisher')

    def _start_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('contributor', 0)

    def _end_contributor(self):
        self.pop('contributor')
        self.incontributor = 0

    def _start_dc_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('name', 0)

    def _end_dc_contributor(self):
        self._end_name()
        self.incontributor = 0

    def _start_name(self, attrsD):
        self.push('name', 0)
    _start_itunes_name = _start_name

    def _end_name(self):
        value = self.pop('name')
        if self.inpublisher:
            self._save_author('name', value, 'publisher')
        elif self.inauthor:
            self._save_author('name', value)
        elif self.incontributor:
            self._save_contributor('name', value)
        elif self.intextinput:
            context = self._getContext()
            context['name'] = value
    _end_itunes_name = _end_name

    def _start_width(self, attrsD):
        self.push('width', 0)

    def _end_width(self):
        value = self.pop('width')
        try:
            value = int(value)
        except ValueError:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['width'] = value

    def _start_height(self, attrsD):
        self.push('height', 0)

    def _end_height(self):
        value = self.pop('height')
        try:
            value = int(value)
        except ValueError:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['height'] = value

    def _start_url(self, attrsD):
        self.push('href', 1)
    _start_homepage = _start_url
    _start_uri = _start_url

    def _end_url(self):
        value = self.pop('href')
        if self.inauthor:
            self._save_author('href', value)
        elif self.incontributor:
            self._save_contributor('href', value)
    _end_homepage = _end_url
    _end_uri = _end_url

    def _start_email(self, attrsD):
        self.push('email', 0)
    _start_itunes_email = _start_email

    def _end_email(self):
        value = self.pop('email')
        if self.inpublisher:
            self._save_author('email', value, 'publisher')
        elif self.inauthor:
            self._save_author('email', value)
        elif self.incontributor:
            self._save_contributor('email', value)
    _end_itunes_email = _end_email

    def _getContext(self):
        if self.insource:
            context = self.sourcedata
        elif self.inimage and 'image' in self.feeddata:
            context = self.feeddata['image']
        elif self.intextinput:
            context = self.feeddata['textinput']
        elif self.inentry:
            context = self.entries[-1]
        else:
            context = self.feeddata
        return context

    def _save_author(self, key, value, prefix='author'):
        context = self._getContext()
        context.setdefault(prefix + '_detail', FeedParserDict())
        context[prefix + '_detail'][key] = value
        self._sync_author_detail()
        context.setdefault('authors', [FeedParserDict()])
        context['authors'][-1][key] = value

    def _save_contributor(self, key, value):
        context = self._getContext()
        context.setdefault('contributors', [FeedParserDict()])
        context['contributors'][-1][key] = value

    def _sync_author_detail(self, key='author'):
        context = self._getContext()
        detail = context.get('%s_detail' % key)
        if detail:
            name = detail.get('name')
            email = detail.get('email')
            if name and email:
                context[key] = u'%s (%s)' % (name, email)
            elif name:
                context[key] = name
            elif email:
                context[key] = email
        else:
            author, email = context.get(key), None
            if not author:
                return
            emailmatch = re.search(ur'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))(\?subject=\S+)?''', author)
            if emailmatch:
                email = emailmatch.group(0)
                # probably a better way to do the following, but it passes all the tests
                author = author.replace(email, u'')
                author = author.replace(u'()', u'')
                author = author.replace(u'<>', u'')
                author = author.replace(u'&lt;&gt;', u'')
                author = author.strip()
                if author and (author[0] == u'('):
                    author = author[1:]
                if author and (author[-1] == u')'):
                    author = author[:-1]
                author = author.strip()
            if author or email:
                context.setdefault('%s_detail' % key, FeedParserDict())
            if author:
                context['%s_detail' % key]['name'] = author
            if email:
                context['%s_detail' % key]['email'] = email

    def _start_subtitle(self, attrsD):
        self.pushContent('subtitle', attrsD, u'text/plain', 1)
    _start_tagline = _start_subtitle
    _start_itunes_subtitle = _start_subtitle

    def _end_subtitle(self):
        self.popContent('subtitle')
    _end_tagline = _end_subtitle
    _end_itunes_subtitle = _end_subtitle

    def _start_rights(self, attrsD):
        self.pushContent('rights', attrsD, u'text/plain', 1)
    _start_dc_rights = _start_rights
    _start_copyright = _start_rights

    def _end_rights(self):
        self.popContent('rights')
    _end_dc_rights = _end_rights
    _end_copyright = _end_rights

    def _start_item(self, attrsD):
        self.entries.append(FeedParserDict())
        self.push('item', 0)
        self.inentry = 1
        self.guidislink = 0
        self.title_depth = -1
        id = self._getAttribute(attrsD, 'rdf:about')
        if id:
            context = self._getContext()
            context['id'] = id
        self._cdf_common(attrsD)
    _start_entry = _start_item

    def _end_item(self):
        self.pop('item')
        self.inentry = 0
    _end_entry = _end_item

    def _start_dc_language(self, attrsD):
        self.push('language', 1)
    _start_language = _start_dc_language

    def _end_dc_language(self):
        self.lang = self.pop('language')
    _end_language = _end_dc_language

    def _start_dc_publisher(self, attrsD):
        self.push('publisher', 1)
    _start_webmaster = _start_dc_publisher

    def _end_dc_publisher(self):
        self.pop('publisher')
        self._sync_author_detail('publisher')
    _end_webmaster = _end_dc_publisher

    def _start_published(self, attrsD):
        self.push('published', 1)
    _start_dcterms_issued = _start_published
    _start_issued = _start_published
    _start_pubdate = _start_published

    def _end_published(self):
        value = self.pop('published')
        self._save('published_parsed', _parse_date(value), overwrite=True)
    _end_dcterms_issued = _end_published
    _end_issued = _end_published
    _end_pubdate = _end_published

    def _start_updated(self, attrsD):
        self.push('updated', 1)
    _start_modified = _start_updated
    _start_dcterms_modified = _start_updated
    _start_dc_date = _start_updated
    _start_lastbuilddate = _start_updated

    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = _parse_date(value)
        self._save('updated_parsed', parsed_value, overwrite=True)
    _end_modified = _end_updated
    _end_dcterms_modified = _end_updated
    _end_dc_date = _end_updated
    _end_lastbuilddate = _end_updated

    def _start_created(self, attrsD):
        self.push('created', 1)
    _start_dcterms_created = _start_created

    def _end_created(self):
        value = self.pop('created')
        self._save('created_parsed', _parse_date(value), overwrite=True)
    _end_dcterms_created = _end_created

    def _start_expirationdate(self, attrsD):
        self.push('expired', 1)

    def _end_expirationdate(self):
        self._save('expired_parsed', _parse_date(self.pop('expired')), overwrite=True)

    def _start_cc_license(self, attrsD):
        context = self._getContext()
        value = self._getAttribute(attrsD, 'rdf:resource')
        attrsD = FeedParserDict()
        attrsD['rel'] = u'license'
        if value:
            attrsD['href']=value
        context.setdefault('links', []).append(attrsD)

    def _start_creativecommons_license(self, attrsD):
        self.push('license', 1)
    _start_creativeCommons_license = _start_creativecommons_license

    def _end_creativecommons_license(self):
        value = self.pop('license')
        context = self._getContext()
        attrsD = FeedParserDict()
        attrsD['rel'] = u'license'
        if value:
            attrsD['href'] = value
        context.setdefault('links', []).append(attrsD)
        del context['license']
    _end_creativeCommons_license = _end_creativecommons_license

    def _addXFN(self, relationships, href, name):
        context = self._getContext()
        xfn = context.setdefault('xfn', [])
        value = FeedParserDict({'relationships': relationships, 'href': href, 'name': name})
        if value not in xfn:
            xfn.append(value)

    def _addTag(self, term, scheme, label):
        context = self._getContext()
        tags = context.setdefault('tags', [])
        if (not term) and (not scheme) and (not label):
            return
        value = FeedParserDict({'term': term, 'scheme': scheme, 'label': label})
        if value not in tags:
            tags.append(value)

    def _start_category(self, attrsD):
        term = attrsD.get('term')
        scheme = attrsD.get('scheme', attrsD.get('domain'))
        label = attrsD.get('label')
        self._addTag(term, scheme, label)
        self.push('category', 1)
    _start_dc_subject = _start_category
    _start_keywords = _start_category

    def _start_media_category(self, attrsD):
        attrsD.setdefault('scheme', u'http://search.yahoo.com/mrss/category_schema')
        self._start_category(attrsD)

    def _end_itunes_keywords(self):
        for term in self.pop('itunes_keywords').split(','):
            if term.strip():
                self._addTag(term.strip(), u'http://www.itunes.com/', None)

    def _start_itunes_category(self, attrsD):
        self._addTag(attrsD.get('text'), u'http://www.itunes.com/', None)
        self.push('category', 1)

    def _end_category(self):
        value = self.pop('category')
        if not value:
            return
        context = self._getContext()
        tags = context['tags']
        if value and len(tags) and not tags[-1]['term']:
            tags[-1]['term'] = value
        else:
            self._addTag(value, None, None)
    _end_dc_subject = _end_category
    _end_keywords = _end_category
    _end_itunes_category = _end_category
    _end_media_category = _end_category

    def _start_cloud(self, attrsD):
        self._getContext()['cloud'] = FeedParserDict(attrsD)

    def _start_link(self, attrsD):
        attrsD.setdefault('rel', u'alternate')
        if attrsD['rel'] == u'self':
            attrsD.setdefault('type', u'application/atom+xml')
        else:
            attrsD.setdefault('type', u'text/html')
        context = self._getContext()
        attrsD = self._itsAnHrefDamnIt(attrsD)
        if 'href' in attrsD:
            attrsD['href'] = self.resolveURI(attrsD['href'])
        expectingText = self.infeed or self.inentry or self.insource
        context.setdefault('links', [])
        if not (self.inentry and self.inimage):
            context['links'].append(FeedParserDict(attrsD))
        if 'href' in attrsD:
            expectingText = 0
            if (attrsD.get('rel') == u'alternate') and (self.mapContentType(attrsD.get('type')) in self.html_types):
                context['link'] = attrsD['href']
        else:
            self.push('link', expectingText)

    def _end_link(self):
        value = self.pop('link')

    def _start_guid(self, attrsD):
        self.guidislink = (attrsD.get('ispermalink', 'true') == 'true')
        self.push('id', 1)
    _start_id = _start_guid

    def _end_guid(self):
        value = self.pop('id')
        self._save('guidislink', self.guidislink and 'link' not in self._getContext())
        if self.guidislink:
            # guid acts as link, but only if 'ispermalink' is not present or is 'true',
            # and only if the item doesn't already have a link element
            self._save('link', value)
    _end_id = _end_guid

    def _start_title(self, attrsD):
        if self.svgOK:
            return self.unknown_starttag('title', attrsD.items())
        self.pushContent('title', attrsD, u'text/plain', self.infeed or self.inentry or self.insource)
    _start_dc_title = _start_title
    _start_media_title = _start_title

    def _end_title(self):
        if self.svgOK:
            return
        value = self.popContent('title')
        if not value:
            return
        self.title_depth = self.depth
    _end_dc_title = _end_title

    def _end_media_title(self):
        title_depth = self.title_depth
        self._end_title()
        self.title_depth = title_depth

    def _start_description(self, attrsD):
        context = self._getContext()
        if 'summary' in context:
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self.pushContent('description', attrsD, u'text/html', self.infeed or self.inentry or self.insource)
    _start_dc_description = _start_description

    def _start_abstract(self, attrsD):
        self.pushContent('description', attrsD, u'text/plain', self.infeed or self.inentry or self.insource)

    def _end_description(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            value = self.popContent('description')
        self._summaryKey = None
    _end_abstract = _end_description
    _end_dc_description = _end_description

    def _start_info(self, attrsD):
        self.pushContent('info', attrsD, u'text/plain', 1)
    _start_feedburner_browserfriendly = _start_info

    def _end_info(self):
        self.popContent('info')
    _end_feedburner_browserfriendly = _end_info

    def _start_generator(self, attrsD):
        if attrsD:
            attrsD = self._itsAnHrefDamnIt(attrsD)
            if 'href' in attrsD:
                attrsD['href'] = self.resolveURI(attrsD['href'])
        self._getContext()['generator_detail'] = FeedParserDict(attrsD)
        self.push('generator', 1)

    def _end_generator(self):
        value = self.pop('generator')
        context = self._getContext()
        if 'generator_detail' in context:
            context['generator_detail']['name'] = value

    def _start_admin_generatoragent(self, attrsD):
        self.push('generator', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('generator')
        self._getContext()['generator_detail'] = FeedParserDict({'href': value})

    def _start_admin_errorreportsto(self, attrsD):
        self.push('errorreportsto', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('errorreportsto')

    def _start_summary(self, attrsD):
        context = self._getContext()
        if 'summary' in context:
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self._summaryKey = 'summary'
            self.pushContent(self._summaryKey, attrsD, u'text/plain', 1)
    _start_itunes_summary = _start_summary

    def _end_summary(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            self.popContent(self._summaryKey or 'summary')
        self._summaryKey = None
    _end_itunes_summary = _end_summary

    def _start_enclosure(self, attrsD):
        attrsD = self._itsAnHrefDamnIt(attrsD)
        context = self._getContext()
        attrsD['rel'] = u'enclosure'
        context.setdefault('links', []).append(FeedParserDict(attrsD))

    def _start_source(self, attrsD):
        if 'url' in attrsD:
            # This means that we're processing a source element from an RSS 2.0 feed
            self.sourcedata['href'] = attrsD[u'url']
        self.push('source', 1)
        self.insource = 1
        self.title_depth = -1

    def _end_source(self):
        self.insource = 0
        value = self.pop('source')
        if value:
            self.sourcedata['title'] = value
        self._getContext()['source'] = copy.deepcopy(self.sourcedata)
        self.sourcedata.clear()

    def _start_content(self, attrsD):
        self.pushContent('content', attrsD, u'text/plain', 1)
        src = attrsD.get('src')
        if src:
            self.contentparams['src'] = src
        self.push('content', 1)

    def _start_body(self, attrsD):
        self.pushContent('content', attrsD, u'application/xhtml+xml', 1)
    _start_xhtml_body = _start_body

    def _start_content_encoded(self, attrsD):
        self.pushContent('content', attrsD, u'text/html', 1)
    _start_fullitem = _start_content_encoded

    def _end_content(self):
        copyToSummary = self.mapContentType(self.contentparams.get('type')) in ([u'text/plain'] + self.html_types)
        value = self.popContent('content')
        if copyToSummary:
            self._save('summary', value)

    _end_body = _end_content
    _end_xhtml_body = _end_content
    _end_content_encoded = _end_content
    _end_fullitem = _end_content

    def _start_itunes_image(self, attrsD):
        self.push('itunes_image', 0)
        if attrsD.get('href'):
            self._getContext()['image'] = FeedParserDict({'href': attrsD.get('href')})
        elif attrsD.get('url'):
            self._getContext()['image'] = FeedParserDict({'href': attrsD.get('url')})
    _start_itunes_link = _start_itunes_image

    def _end_itunes_block(self):
        value = self.pop('itunes_block', 0)
        self._getContext()['itunes_block'] = (value == 'yes') and 1 or 0

    def _end_itunes_explicit(self):
        value = self.pop('itunes_explicit', 0)
        # Convert 'yes' -> True, 'clean' to False, and any other value to None
        # False and None both evaluate as False, so the difference can be ignored
        # by applications that only need to know if the content is explicit.
        self._getContext()['itunes_explicit'] = (None, False, True)[(value == 'yes' and 2) or value == 'clean' or 0]

    def _start_media_content(self, attrsD):
        context = self._getContext()
        context.setdefault('media_content', [])
        context['media_content'].append(attrsD)

    def _start_media_thumbnail(self, attrsD):
        context = self._getContext()
        context.setdefault('media_thumbnail', [])
        self.push('url', 1) # new
        context['media_thumbnail'].append(attrsD)

    def _end_media_thumbnail(self):
        url = self.pop('url')
        context = self._getContext()
        if url != None and len(url.strip()) != 0:
            if 'url' not in context['media_thumbnail'][-1]:
                context['media_thumbnail'][-1]['url'] = url

    def _start_media_player(self, attrsD):
        self.push('media_player', 0)
        self._getContext()['media_player'] = FeedParserDict(attrsD)

    def _end_media_player(self):
        value = self.pop('media_player')
        context = self._getContext()
        context['media_player']['content'] = value

    def _start_newlocation(self, attrsD):
        self.push('newlocation', 1)

    def _end_newlocation(self):
        url = self.pop('newlocation')
        context = self._getContext()
        # don't set newlocation if the context isn't right
        if context is not self.feeddata:
            return
        context['newlocation'] = _makeSafeAbsoluteURI(self.baseuri, url.strip())

if _XML_AVAILABLE:
    class _StrictFeedParser(_FeedParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            xml.sax.handler.ContentHandler.__init__(self)
            _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
            self.decls = {}

        def startPrefixMapping(self, prefix, uri):
            if not uri:
                return
            # Jython uses '' instead of None; standardize on None
            prefix = prefix or None
            self.trackNamespace(prefix, uri)
            if prefix and uri == 'http://www.w3.org/1999/xlink':
                self.decls['xmlns:' + prefix] = uri

        def startElementNS(self, name, qname, attrs):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if lowernamespace.find(u'backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                namespace = u'http://backend.userland.com/rss'
                lowernamespace = namespace
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = None
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if givenprefix and (prefix == None or (prefix == '' and lowernamespace == '')) and givenprefix not in self.namespacesInUse:
                raise UndeclaredNamespace, "'%s' is not associated with a namespace" % givenprefix
            localname = str(localname).lower()

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD, self.decls = self.decls, {}
            if localname=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                attrsD['xmlns']=namespace
            if localname=='svg' and namespace=='http://www.w3.org/2000/svg':
                attrsD['xmlns']=namespace

            if prefix:
                localname = prefix.lower() + ':' + localname
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                    if name and value == namespace:
                        localname = name + ':' + localname
                        break

            for (namespace, attrlocalname), attrvalue in attrs.items():
                lowernamespace = (namespace or '').lower()
                prefix = self._matchnamespaces.get(lowernamespace, '')
                if prefix:
                    attrlocalname = prefix + ':' + attrlocalname
                attrsD[str(attrlocalname).lower()] = attrvalue
            for qname in attrs.getQNames():
                attrsD[str(qname).lower()] = attrs.getValueByQName(qname)
            self.unknown_starttag(localname, attrsD.items())

        def characters(self, text):
            self.handle_data(text)

        def endElementNS(self, name, qname):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = ''
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if prefix:
                localname = prefix + ':' + localname
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                    if name and value == namespace:
                        localname = name + ':' + localname
                        break
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc

        # drv_libxml2 calls warning() in some cases
        warning = error

        def fatalError(self, exc):
            self.error(exc)
            raise exc

class _BaseHTMLProcessor(sgmllib.SGMLParser):
    special = re.compile('''[<>'"]''')
    bare_ampersand = re.compile("&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = set([
      'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame',
      'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
      'source', 'track', 'wbr'
    ])

    def __init__(self, encoding, _type):
        self.encoding = encoding
        self._type = _type
        sgmllib.SGMLParser.__init__(self)

    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'

    # By declaring these methods and overriding their compiled code
    # with the code from sgmllib, the original code will execute in
    # feedparser's scope instead of sgmllib's. This means that the
    # `tagfind` and `charref` regular expressions will be found as
    # they're declared above, not as they're declared in sgmllib.
    def goahead(self, i):
        pass
    goahead.func_code = sgmllib.SGMLParser.goahead.func_code

    def __parse_starttag(self, i):
        pass
    __parse_starttag.func_code = sgmllib.SGMLParser.parse_starttag.func_code

    def parse_starttag(self,i):
        j = self.__parse_starttag(i)
        if self._type == 'application/xhtml+xml':
            if j>2 and self.rawdata[j-2:j]=='/>':
                self.unknown_endtag(self.lasttag)
        return j

    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        data = re.sub(r'<([^<>\s]+?)\s*/>', self._shorttag_replace, data)
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        try:
            bytes
            if bytes is str:
                raise NameError
            self.encoding = self.encoding + u'_INVALID_PYTHON_3'
        except NameError:
            if self.encoding and isinstance(data, unicode):
                data = data.encode(self.encoding)
        sgmllib.SGMLParser.feed(self, data)
        sgmllib.SGMLParser.close(self)

    def normalize_attrs(self, attrs):
        if not attrs:
            return attrs
        # utility method to be called by descendants
        attrs = dict([(k.lower(), v) for k, v in attrs]).items()
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        attrs.sort()
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        uattrs = []
        strattrs=''
        if attrs:
            for key, value in attrs:
                value=value.replace('>','&gt;').replace('<','&lt;').replace('"','&quot;')
                value = self.bare_ampersand.sub("&amp;", value)
                # thanks to Kevin Marks for this breathtaking hack to deal with (valid) high-bit attribute values in UTF-8 feeds
                if not isinstance(value, unicode):
                    value = value.decode(self.encoding, 'ignore')
                try:
                    # Currently, in Python 3 the key is already a str, and cannot be decoded again
                    uattrs.append((unicode(key, self.encoding), value))
                except TypeError:
                    uattrs.append((key, value))
            strattrs = u''.join([u' %s="%s"' % (key, value) for key, value in uattrs])
            if self.encoding:
                try:
                    strattrs = strattrs.encode(self.encoding)
                except (UnicodeEncodeError, LookupError):
                    pass
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%s%s />' % (tag, strattrs))
        else:
            self.pieces.append('<%s%s>' % (tag, strattrs))

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%s>" % tag)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        if ref.startswith('x'):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%s;' % ref)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == 'apos':
            self.pieces.append('&%s;' % ref)
        else:
            self.pieces.append('&amp;%s' % ref)

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%s-->' % text)

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%s>' % text)

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%s>' % text)

    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.handle_data(rawdata)
#            self.updatepos(declstartpos, i)
            return None, -1

    def convert_charref(self, name):
        return '&#%s;' % name

    def convert_entityref(self, name):
        return '&%s;' % name

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join([str(p) for p in self.pieces])

    def parse_declaration(self, i):
        try:
            return sgmllib.SGMLParser.parse_declaration(self, i)
        except sgmllib.SGMLParseError:
            # escape the doctype declaration and continue parsing
            self.handle_data('&lt;')
            return i+1

class _LooseFeedParser(_FeedParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding, entities):
        sgmllib.SGMLParser.__init__(self)
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
        _BaseHTMLProcessor.__init__(self, encoding, 'application/xhtml+xml')
        self.entities=entities

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#x3C;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#x3E;', '&gt;')
        data = data.replace('&#38;', '&amp;')
        data = data.replace('&#x26;', '&amp;')
        data = data.replace('&#34;', '&quot;')
        data = data.replace('&#x22;', '&quot;')
        data = data.replace('&#39;', '&apos;')
        data = data.replace('&#x27;', '&apos;')
        if not self.contentparams.get('type', u'xml').endswith(u'xml'):
            data = data.replace('&lt;', '<')
            data = data.replace('&gt;', '>')
            data = data.replace('&amp;', '&')
            data = data.replace('&quot;', '"')
            data = data.replace('&apos;', "'")
        return data

    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (n,v.replace('"','&quot;')) for n,v in attrs])

class _MicroformatsParser:
    STRING = 1
    DATE = 2
    URI = 3
    NODE = 4
    EMAIL = 5

    known_xfn_relationships = set(['contact', 'acquaintance', 'friend', 'met', 'co-worker', 'coworker', 'colleague', 'co-resident', 'coresident', 'neighbor', 'child', 'parent', 'sibling', 'brother', 'sister', 'spouse', 'wife', 'husband', 'kin', 'relative', 'muse', 'crush', 'date', 'sweetheart', 'me'])
    known_binary_extensions =  set(['zip','rar','exe','gz','tar','tgz','tbz2','bz2','z','7z','dmg','img','sit','sitx','hqx','deb','rpm','bz2','jar','rar','iso','bin','msi','mp2','mp3','ogg','ogm','mp4','m4v','m4a','avi','wma','wmv'])

    def __init__(self, data, baseuri, encoding):
        self.document = BeautifulSoup.BeautifulSoup(data)
        self.baseuri = baseuri
        self.encoding = encoding
        if isinstance(data, unicode):
            data = data.encode(encoding)
        self.tags = []
        self.enclosures = []
        self.xfn = []
        self.vcard = None

    def vcardEscape(self, s):
        if isinstance(s, basestring):
            s = s.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
        return s

    def vcardFold(self, s):
        s = re.sub(';+$', '', s)
        sFolded = ''
        iMax = 75
        sPrefix = ''
        while len(s) > iMax:
            sFolded += sPrefix + s[:iMax] + '\n'
            s = s[iMax:]
            sPrefix = ' '
            iMax = 74
        sFolded += sPrefix + s
        return sFolded

    def normalize(self, s):
        return re.sub(r'\s+', ' ', s).strip()

    def unique(self, aList):
        results = []
        for element in aList:
            if element not in results:
                results.append(element)
        return results

    def toISO8601(self, dt):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', dt)

    def getPropertyValue(self, elmRoot, sProperty, iPropertyType=4, bAllowMultiple=0, bAutoEscape=0):
        all = lambda x: 1
        sProperty = sProperty.lower()
        bFound = 0
        bNormalize = 1
        propertyMatch = {'class': re.compile(r'\b%s\b' % sProperty)}
        if bAllowMultiple and (iPropertyType != self.NODE):
            snapResults = []
            containers = elmRoot(['ul', 'ol'], propertyMatch)
            for container in containers:
                snapResults.extend(container('li'))
            bFound = (len(snapResults) != 0)
        if not bFound:
            snapResults = elmRoot(all, propertyMatch)
            bFound = (len(snapResults) != 0)
        if (not bFound) and (sProperty == 'value'):
            snapResults = elmRoot('pre')
            bFound = (len(snapResults) != 0)
            bNormalize = not bFound
            if not bFound:
                snapResults = [elmRoot]
                bFound = (len(snapResults) != 0)
        arFilter = []
        if sProperty == 'vcard':
            snapFilter = elmRoot(all, propertyMatch)
            for node in snapFilter:
                if node.findParent(all, propertyMatch):
                    arFilter.append(node)
        arResults = []
        for node in snapResults:
            if node not in arFilter:
                arResults.append(node)
        bFound = (len(arResults) != 0)
        if not bFound:
            if bAllowMultiple:
                return []
            elif iPropertyType == self.STRING:
                return ''
            elif iPropertyType == self.DATE:
                return None
            elif iPropertyType == self.URI:
                return ''
            elif iPropertyType == self.NODE:
                return None
            else:
                return None
        arValues = []
        for elmResult in arResults:
            sValue = None
            if iPropertyType == self.NODE:
                if bAllowMultiple:
                    arValues.append(elmResult)
                    continue
                else:
                    return elmResult
            sNodeName = elmResult.name.lower()
            if (iPropertyType == self.EMAIL) and (sNodeName == 'a'):
                sValue = (elmResult.get('href') or '').split('mailto:').pop().split('?')[0]
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (sNodeName == 'abbr'):
                sValue = elmResult.get('title')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (iPropertyType == self.URI):
                if sNodeName == 'a':
                    sValue = elmResult.get('href')
                elif sNodeName == 'img':
                    sValue = elmResult.get('src')
                elif sNodeName == 'object':
                    sValue = elmResult.get('data')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (sNodeName == 'img'):
                sValue = elmResult.get('alt')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if not sValue:
                sValue = elmResult.renderContents()
                sValue = re.sub(r'<\S[^>]*>', '', sValue)
                sValue = sValue.replace('\r\n', '\n')
                sValue = sValue.replace('\r', '\n')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if not sValue:
                continue
            if iPropertyType == self.DATE:
                sValue = _parse_date_iso8601(sValue)
            if bAllowMultiple:
                arValues.append(bAutoEscape and self.vcardEscape(sValue) or sValue)
            else:
                return bAutoEscape and self.vcardEscape(sValue) or sValue
        return arValues

    def findVCards(self, elmRoot, bAgentParsing=0):
        sVCards = ''

        if not bAgentParsing:
            arCards = self.getPropertyValue(elmRoot, 'vcard', bAllowMultiple=1)
        else:
            arCards = [elmRoot]

        for elmCard in arCards:
            arLines = []

            def processSingleString(sProperty):
                sValue = self.getPropertyValue(elmCard, sProperty, self.STRING, bAutoEscape=1).decode(self.encoding)
                if sValue:
                    arLines.append(self.vcardFold(sProperty.upper() + ':' + sValue))
                return sValue or u''

            def processSingleURI(sProperty):
                sValue = self.getPropertyValue(elmCard, sProperty, self.URI)
                if sValue:
                    sContentType = ''
                    sEncoding = ''
                    sValueKey = ''
                    if sValue.startswith('data:'):
                        sEncoding = ';ENCODING=b'
                        sContentType = sValue.split(';')[0].split('/').pop()
                        sValue = sValue.split(',', 1).pop()
                    else:
                        elmValue = self.getPropertyValue(elmCard, sProperty)
                        if elmValue:
                            if sProperty != 'url':
                                sValueKey = ';VALUE=uri'
                            sContentType = elmValue.get('type', '').strip().split('/').pop().strip()
                    sContentType = sContentType.upper()
                    if sContentType == 'OCTET-STREAM':
                        sContentType = ''
                    if sContentType:
                        sContentType = ';TYPE=' + sContentType.upper()
                    arLines.append(self.vcardFold(sProperty.upper() + sEncoding + sContentType + sValueKey + ':' + sValue))

            def processTypeValue(sProperty, arDefaultType, arForceType=None):
                arResults = self.getPropertyValue(elmCard, sProperty, bAllowMultiple=1)
                for elmResult in arResults:
                    arType = self.getPropertyValue(elmResult, 'type', self.STRING, 1, 1)
                    if arForceType:
                        arType = self.unique(arForceType + arType)
                    if not arType:
                        arType = arDefaultType
                    sValue = self.getPropertyValue(elmResult, 'value', self.EMAIL, 0)
                    if sValue:
                        arLines.append(self.vcardFold(sProperty.upper() + ';TYPE=' + ','.join(arType) + ':' + sValue))

            # AGENT
            # must do this before all other properties because it is destructive
            # (removes nested class="vcard" nodes so they don't interfere with
            # this vcard's other properties)
            arAgent = self.getPropertyValue(elmCard, 'agent', bAllowMultiple=1)
            for elmAgent in arAgent:
                if re.compile(r'\bvcard\b').search(elmAgent.get('class')):
                    sAgentValue = self.findVCards(elmAgent, 1) + '\n'
                    sAgentValue = sAgentValue.replace('\n', '\\n')
                    sAgentValue = sAgentValue.replace(';', '\\;')
                    if sAgentValue:
                        arLines.append(self.vcardFold('AGENT:' + sAgentValue))
                    # Completely remove the agent element from the parse tree
                    elmAgent.extract()
                else:
                    sAgentValue = self.getPropertyValue(elmAgent, 'value', self.URI, bAutoEscape=1);
                    if sAgentValue:
                        arLines.append(self.vcardFold('AGENT;VALUE=uri:' + sAgentValue))

            # FN (full name)
            sFN = processSingleString('fn')

            # N (name)
            elmName = self.getPropertyValue(elmCard, 'n')
            if elmName:
                sFamilyName = self.getPropertyValue(elmName, 'family-name', self.STRING, bAutoEscape=1)
                sGivenName = self.getPropertyValue(elmName, 'given-name', self.STRING, bAutoEscape=1)
                arAdditionalNames = self.getPropertyValue(elmName, 'additional-name', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'additional-names', self.STRING, 1, 1)
                arHonorificPrefixes = self.getPropertyValue(elmName, 'honorific-prefix', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'honorific-prefixes', self.STRING, 1, 1)
                arHonorificSuffixes = self.getPropertyValue(elmName, 'honorific-suffix', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'honorific-suffixes', self.STRING, 1, 1)
                arLines.append(self.vcardFold('N:' + sFamilyName + ';' +
                                         sGivenName + ';' +
                                         ','.join(arAdditionalNames) + ';' +
                                         ','.join(arHonorificPrefixes) + ';' +
                                         ','.join(arHonorificSuffixes)))
            elif sFN:
                # implied "N" optimization
                # http://microformats.org/wiki/hcard#Implied_.22N.22_Optimization
                arNames = self.normalize(sFN).split()
                if len(arNames) == 2:
                    bFamilyNameFirst = (arNames[0].endswith(',') or
                                        len(arNames[1]) == 1 or
                                        ((len(arNames[1]) == 2) and (arNames[1].endswith('.'))))
                    if bFamilyNameFirst:
                        arLines.append(self.vcardFold('N:' + arNames[0] + ';' + arNames[1]))
                    else:
                        arLines.append(self.vcardFold('N:' + arNames[1] + ';' + arNames[0]))

            # SORT-STRING
            sSortString = self.getPropertyValue(elmCard, 'sort-string', self.STRING, bAutoEscape=1)
            if sSortString:
                arLines.append(self.vcardFold('SORT-STRING:' + sSortString))

            # NICKNAME
            arNickname = self.getPropertyValue(elmCard, 'nickname', self.STRING, 1, 1)
            if arNickname:
                arLines.append(self.vcardFold('NICKNAME:' + ','.join(arNickname)))

            # PHOTO
            processSingleURI('photo')

            # BDAY
            dtBday = self.getPropertyValue(elmCard, 'bday', self.DATE)
            if dtBday:
                arLines.append(self.vcardFold('BDAY:' + self.toISO8601(dtBday)))

            # ADR (address)
            arAdr = self.getPropertyValue(elmCard, 'adr', bAllowMultiple=1)
            for elmAdr in arAdr:
                arType = self.getPropertyValue(elmAdr, 'type', self.STRING, 1, 1)
                if not arType:
                    arType = ['intl','postal','parcel','work'] # default adr types, see RFC 2426 section 3.2.1
                sPostOfficeBox = self.getPropertyValue(elmAdr, 'post-office-box', self.STRING, 0, 1)
                sExtendedAddress = self.getPropertyValue(elmAdr, 'extended-address', self.STRING, 0, 1)
                sStreetAddress = self.getPropertyValue(elmAdr, 'street-address', self.STRING, 0, 1)
                sLocality = self.getPropertyValue(elmAdr, 'locality', self.STRING, 0, 1)
                sRegion = self.getPropertyValue(elmAdr, 'region', self.STRING, 0, 1)
                sPostalCode = self.getPropertyValue(elmAdr, 'postal-code', self.STRING, 0, 1)
                sCountryName = self.getPropertyValue(elmAdr, 'country-name', self.STRING, 0, 1)
                arLines.append(self.vcardFold('ADR;TYPE=' + ','.join(arType) + ':' +
                                         sPostOfficeBox + ';' +
                                         sExtendedAddress + ';' +
                                         sStreetAddress + ';' +
                                         sLocality + ';' +
                                         sRegion + ';' +
                                         sPostalCode + ';' +
                                         sCountryName))

            # LABEL
            processTypeValue('label', ['intl','postal','parcel','work'])

            # TEL (phone number)
            processTypeValue('tel', ['voice'])

            # EMAIL
            processTypeValue('email', ['internet'], ['internet'])

            # MAILER
            processSingleString('mailer')

            # TZ (timezone)
            processSingleString('tz')

            # GEO (geographical information)
            elmGeo = self.getPropertyValue(elmCard, 'geo')
            if elmGeo:
                sLatitude = self.getPropertyValue(elmGeo, 'latitude', self.STRING, 0, 1)
                sLongitude = self.getPropertyValue(elmGeo, 'longitude', self.STRING, 0, 1)
                arLines.append(self.vcardFold('GEO:' + sLatitude + ';' + sLongitude))

            # TITLE
            processSingleString('title')

            # ROLE
            processSingleString('role')

            # LOGO
            processSingleURI('logo')

            # ORG (organization)
            elmOrg = self.getPropertyValue(elmCard, 'org')
            if elmOrg:
                sOrganizationName = self.getPropertyValue(elmOrg, 'organization-name', self.STRING, 0, 1)
                if not sOrganizationName:
                    # implied "organization-name" optimization
                    # http://microformats.org/wiki/hcard#Implied_.22organization-name.22_Optimization
                    sOrganizationName = self.getPropertyValue(elmCard, 'org', self.STRING, 0, 1)
                    if sOrganizationName:
                        arLines.append(self.vcardFold('ORG:' + sOrganizationName))
                else:
                    arOrganizationUnit = self.getPropertyValue(elmOrg, 'organization-unit', self.STRING, 1, 1)
                    arLines.append(self.vcardFold('ORG:' + sOrganizationName + ';' + ';'.join(arOrganizationUnit)))

            # CATEGORY
            arCategory = self.getPropertyValue(elmCard, 'category', self.STRING, 1, 1) + self.getPropertyValue(elmCard, 'categories', self.STRING, 1, 1)
            if arCategory:
                arLines.append(self.vcardFold('CATEGORIES:' + ','.join(arCategory)))

            # NOTE
            processSingleString('note')

            # REV
            processSingleString('rev')

            # SOUND
            processSingleURI('sound')

            # UID
            processSingleString('uid')

            # URL
            processSingleURI('url')

            # CLASS
            processSingleString('class')

            # KEY
            processSingleURI('key')

            if arLines:
                arLines = [u'BEGIN:vCard',u'VERSION:3.0'] + arLines + [u'END:vCard']
                # XXX - this is super ugly; properly fix this with issue 148
                for i, s in enumerate(arLines):
                    if not isinstance(s, unicode):
                        arLines[i] = s.decode('utf-8', 'ignore')
                sVCards += u'\n'.join(arLines) + u'\n'

        return sVCards.strip()

    def isProbablyDownloadable(self, elm):
        attrsD = elm.attrMap
        if 'href' not in attrsD:
            return 0
        linktype = attrsD.get('type', '').strip()
        if linktype.startswith('audio/') or \
           linktype.startswith('video/') or \
           (linktype.startswith('application/') and not linktype.endswith('xml')):
            return 1
        path = urlparse.urlparse(attrsD['href'])[2]
        if path.find('.') == -1:
            return 0
        fileext = path.split('.').pop().lower()
        return fileext in self.known_binary_extensions

    def findTags(self):
        all = lambda x: 1
        for elm in self.document(all, {'rel': re.compile(r'\btag\b')}):
            href = elm.get('href')
            if not href:
                continue
            urlscheme, domain, path, params, query, fragment = \
                       urlparse.urlparse(_urljoin(self.baseuri, href))
            segments = path.split('/')
            tag = segments.pop()
            if not tag:
                if segments:
                    tag = segments.pop()
                else:
                    # there are no tags
                    continue
            tagscheme = urlparse.urlunparse((urlscheme, domain, '/'.join(segments), '', '', ''))
            if not tagscheme.endswith('/'):
                tagscheme += '/'
            self.tags.append(FeedParserDict({"term": tag, "scheme": tagscheme, "label": elm.string or ''}))

    def findEnclosures(self):
        all = lambda x: 1
        enclosure_match = re.compile(r'\benclosure\b')
        for elm in self.document(all, {'href': re.compile(r'.+')}):
            if not enclosure_match.search(elm.get('rel', u'')) and not self.isProbablyDownloadable(elm):
                continue
            if elm.attrMap not in self.enclosures:
                self.enclosures.append(elm.attrMap)
                if elm.string and not elm.get('title'):
                    self.enclosures[-1]['title'] = elm.string

    def findXFN(self):
        all = lambda x: 1
        for elm in self.document(all, {'rel': re.compile('.+'), 'href': re.compile('.+')}):
            rels = elm.get('rel', u'').split()
            xfn_rels = [r for r in rels if r in self.known_xfn_relationships]
            if xfn_rels:
                self.xfn.append({"relationships": xfn_rels, "href": elm.get('href', ''), "name": elm.string})

def _parseMicroformats(htmlSource, baseURI, encoding):
    if not BeautifulSoup:
        return
    try:
        p = _MicroformatsParser(htmlSource, baseURI, encoding)
    except UnicodeEncodeError:
        # sgmllib throws this exception when performing lookups of tags
        # with non-ASCII characters in them.
        return
    p.vcard = p.findVCards(p.document)
    p.findTags()
    p.findEnclosures()
    p.findXFN()
    return {"tags": p.tags, "enclosures": p.enclosures, "xfn": p.xfn, "vcard": p.vcard}

class _RelativeURIResolver(_BaseHTMLProcessor):
    relative_uris = set([('a', 'href'),
                     ('applet', 'codebase'),
                     ('area', 'href'),
                     ('blockquote', 'cite'),
                     ('body', 'background'),
                     ('del', 'cite'),
                     ('form', 'action'),
                     ('frame', 'longdesc'),
                     ('frame', 'src'),
                     ('iframe', 'longdesc'),
                     ('iframe', 'src'),
                     ('head', 'profile'),
                     ('img', 'longdesc'),
                     ('img', 'src'),
                     ('img', 'usemap'),
                     ('input', 'src'),
                     ('input', 'usemap'),
                     ('ins', 'cite'),
                     ('link', 'href'),
                     ('object', 'classid'),
                     ('object', 'codebase'),
                     ('object', 'data'),
                     ('object', 'usemap'),
                     ('q', 'cite'),
                     ('script', 'src')])

    def __init__(self, baseuri, encoding, _type):
        _BaseHTMLProcessor.__init__(self, encoding, _type)
        self.baseuri = baseuri

    def resolveURI(self, uri):
        return _makeSafeAbsoluteURI(self.baseuri, uri.strip())

    def unknown_starttag(self, tag, attrs):
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, ((tag, key) in self.relative_uris) and self.resolveURI(value) or value) for key, value in attrs]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)

def _resolveRelativeURIs(htmlSource, baseURI, encoding, _type):
    if not _SGML_AVAILABLE:
        return htmlSource

    p = _RelativeURIResolver(baseURI, encoding, _type)
    p.feed(htmlSource)
    return p.output()

def _makeSafeAbsoluteURI(base, rel=None):
    # bail if ACCEPTABLE_URI_SCHEMES is empty
    if not ACCEPTABLE_URI_SCHEMES:
        try:
            return _urljoin(base, rel or u'')
        except ValueError:
            return u''
    if not base:
        return rel or u''
    if not rel:
        try:
            scheme = urlparse.urlparse(base)[0]
        except ValueError:
            return u''
        if not scheme or scheme in ACCEPTABLE_URI_SCHEMES:
            return base
        return u''
    try:
        uri = _urljoin(base, rel)
    except ValueError:
        return u''
    if uri.strip().split(':', 1)[0] not in ACCEPTABLE_URI_SCHEMES:
        return u''
    return uri

class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = set(['a', 'abbr', 'acronym', 'address', 'area',
        'article', 'aside', 'audio', 'b', 'big', 'blockquote', 'br', 'button',
        'canvas', 'caption', 'center', 'cite', 'code', 'col', 'colgroup',
        'command', 'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn',
        'dialog', 'dir', 'div', 'dl', 'dt', 'em', 'event-source', 'fieldset',
        'figcaption', 'figure', 'footer', 'font', 'form', 'header', 'h1',
        'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input', 'ins',
        'keygen', 'kbd', 'label', 'legend', 'li', 'm', 'map', 'menu', 'meter',
        'multicol', 'nav', 'nextid', 'ol', 'output', 'optgroup', 'option',
        'p', 'pre', 'progress', 'q', 's', 'samp', 'section', 'select',
        'small', 'sound', 'source', 'spacer', 'span', 'strike', 'strong',
        'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'time', 'tfoot',
        'th', 'thead', 'tr', 'tt', 'u', 'ul', 'var', 'video', 'noscript'])

    acceptable_attributes = set(['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'autocomplete', 'autofocus', 'axis',
      'background', 'balance', 'bgcolor', 'bgproperties', 'border',
      'bordercolor', 'bordercolordark', 'bordercolorlight', 'bottompadding',
      'cellpadding', 'cellspacing', 'ch', 'challenge', 'char', 'charoff',
      'choff', 'charset', 'checked', 'cite', 'class', 'clear', 'color', 'cols',
      'colspan', 'compact', 'contenteditable', 'controls', 'coords', 'data',
      'datafld', 'datapagesize', 'datasrc', 'datetime', 'default', 'delay',
      'dir', 'disabled', 'draggable', 'dynsrc', 'enctype', 'end', 'face', 'for',
      'form', 'frame', 'galleryimg', 'gutter', 'headers', 'height', 'hidefocus',
      'hidden', 'high', 'href', 'hreflang', 'hspace', 'icon', 'id', 'inputmode',
      'ismap', 'keytype', 'label', 'leftspacing', 'lang', 'list', 'longdesc',
      'loop', 'loopcount', 'loopend', 'loopstart', 'low', 'lowsrc', 'max',
      'maxlength', 'media', 'method', 'min', 'multiple', 'name', 'nohref',
      'noshade', 'nowrap', 'open', 'optimum', 'pattern', 'ping', 'point-size',
      'prompt', 'pqg', 'radiogroup', 'readonly', 'rel', 'repeat-max',
      'repeat-min', 'replace', 'required', 'rev', 'rightspacing', 'rows',
      'rowspan', 'rules', 'scope', 'selected', 'shape', 'size', 'span', 'src',
      'start', 'step', 'summary', 'suppress', 'tabindex', 'target', 'template',
      'title', 'toppadding', 'type', 'unselectable', 'usemap', 'urn', 'valign',
      'value', 'variable', 'volume', 'vspace', 'vrml', 'width', 'wrap',
      'xml:lang'])

    unacceptable_elements_with_end_tag = set(['script', 'applet', 'style'])

    acceptable_css_properties = set(['azimuth', 'background-color',
      'border-bottom-color', 'border-collapse', 'border-color',
      'border-left-color', 'border-right-color', 'border-top-color', 'clear',
      'color', 'cursor', 'direction', 'display', 'elevation', 'float', 'font',
      'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
      'height', 'letter-spacing', 'line-height', 'overflow', 'pause',
      'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness',
      'speak', 'speak-header', 'speak-numeral', 'speak-punctuation',
      'speech-rate', 'stress', 'text-align', 'text-decoration', 'text-indent',
      'unicode-bidi', 'vertical-align', 'voice-family', 'volume',
      'white-space', 'width'])

    # survey of common keywords found in feeds
    acceptable_css_keywords = set(['auto', 'aqua', 'black', 'block', 'blue',
      'bold', 'both', 'bottom', 'brown', 'center', 'collapse', 'dashed',
      'dotted', 'fuchsia', 'gray', 'green', '!important', 'italic', 'left',
      'lime', 'maroon', 'medium', 'none', 'navy', 'normal', 'nowrap', 'olive',
      'pointer', 'purple', 'red', 'right', 'solid', 'silver', 'teal', 'top',
      'transparent', 'underline', 'white', 'yellow'])

    valid_css_values = re.compile('^(#[0-9a-f]+|rgb\(\d+%?,\d*%?,?\d*%?\)?|' +
      '\d{0,2}\.?\d{0,2}(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$')

    mathml_elements = set(['annotation', 'annotation-xml', 'maction', 'math',
      'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts', 'mn', 'mo', 'mover', 'mpadded',
      'mphantom', 'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt', 'mstyle',
      'msub', 'msubsup', 'msup', 'mtable', 'mtd', 'mtext', 'mtr', 'munder',
      'munderover', 'none', 'semantics'])

    mathml_attributes = set(['actiontype', 'align', 'columnalign', 'columnalign',
      'columnalign', 'close', 'columnlines', 'columnspacing', 'columnspan', 'depth',
      'display', 'displaystyle', 'encoding', 'equalcolumns', 'equalrows',
      'fence', 'fontstyle', 'fontweight', 'frame', 'height', 'linethickness',
      'lspace', 'mathbackground', 'mathcolor', 'mathvariant', 'mathvariant',
      'maxsize', 'minsize', 'open', 'other', 'rowalign', 'rowalign', 'rowalign',
      'rowlines', 'rowspacing', 'rowspan', 'rspace', 'scriptlevel', 'selection',
      'separator', 'separators', 'stretchy', 'width', 'width', 'xlink:href',
      'xlink:show', 'xlink:type', 'xmlns', 'xmlns:xlink'])

    # svgtiny - foreignObject + linearGradient + radialGradient + stop
    svg_elements = set(['a', 'animate', 'animateColor', 'animateMotion',
      'animateTransform', 'circle', 'defs', 'desc', 'ellipse', 'foreignObject',
      'font-face', 'font-face-name', 'font-face-src', 'g', 'glyph', 'hkern',
      'linearGradient', 'line', 'marker', 'metadata', 'missing-glyph', 'mpath',
      'path', 'polygon', 'polyline', 'radialGradient', 'rect', 'set', 'stop',
      'svg', 'switch', 'text', 'title', 'tspan', 'use'])

    # svgtiny + class + opacity + offset + xmlns + xmlns:xlink
    svg_attributes = set(['accent-height', 'accumulate', 'additive', 'alphabetic',
       'arabic-form', 'ascent', 'attributeName', 'attributeType',
       'baseProfile', 'bbox', 'begin', 'by', 'calcMode', 'cap-height',
       'class', 'color', 'color-rendering', 'content', 'cx', 'cy', 'd', 'dx',
       'dy', 'descent', 'display', 'dur', 'end', 'fill', 'fill-opacity',
       'fill-rule', 'font-family', 'font-size', 'font-stretch', 'font-style',
       'font-variant', 'font-weight', 'from', 'fx', 'fy', 'g1', 'g2',
       'glyph-name', 'gradientUnits', 'hanging', 'height', 'horiz-adv-x',
       'horiz-origin-x', 'id', 'ideographic', 'k', 'keyPoints', 'keySplines',
       'keyTimes', 'lang', 'mathematical', 'marker-end', 'marker-mid',
       'marker-start', 'markerHeight', 'markerUnits', 'markerWidth', 'max',
       'min', 'name', 'offset', 'opacity', 'orient', 'origin',
       'overline-position', 'overline-thickness', 'panose-1', 'path',
       'pathLength', 'points', 'preserveAspectRatio', 'r', 'refX', 'refY',
       'repeatCount', 'repeatDur', 'requiredExtensions', 'requiredFeatures',
       'restart', 'rotate', 'rx', 'ry', 'slope', 'stemh', 'stemv',
       'stop-color', 'stop-opacity', 'strikethrough-position',
       'strikethrough-thickness', 'stroke', 'stroke-dasharray',
       'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin',
       'stroke-miterlimit', 'stroke-opacity', 'stroke-width', 'systemLanguage',
       'target', 'text-anchor', 'to', 'transform', 'type', 'u1', 'u2',
       'underline-position', 'underline-thickness', 'unicode', 'unicode-range',
       'units-per-em', 'values', 'version', 'viewBox', 'visibility', 'width',
       'widths', 'x', 'x-height', 'x1', 'x2', 'xlink:actuate', 'xlink:arcrole',
       'xlink:href', 'xlink:role', 'xlink:show', 'xlink:title', 'xlink:type',
       'xml:base', 'xml:lang', 'xml:space', 'xmlns', 'xmlns:xlink', 'y', 'y1',
       'y2', 'zoomAndPan'])

    svg_attr_map = None
    svg_elem_map = None

    acceptable_svg_properties = set([ 'fill', 'fill-opacity', 'fill-rule',
      'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
      'stroke-opacity'])

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        self.mathmlOK = 0
        self.svgOK = 0

    def unknown_starttag(self, tag, attrs):
        acceptable_attributes = self.acceptable_attributes
        keymap = {}
        if not tag in self.acceptable_elements or self.svgOK:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1

            # add implicit namespaces to html5 inline svg/mathml
            if self._type.endswith('html'):
                if not dict(attrs).get('xmlns'):
                    if tag=='svg':
                        attrs.append( ('xmlns','http://www.w3.org/2000/svg') )
                    if tag=='math':
                        attrs.append( ('xmlns','http://www.w3.org/1998/Math/MathML') )

            # not otherwise acceptable, perhaps it is MathML or SVG?
            if tag=='math' and ('xmlns','http://www.w3.org/1998/Math/MathML') in attrs:
                self.mathmlOK += 1
            if tag=='svg' and ('xmlns','http://www.w3.org/2000/svg') in attrs:
                self.svgOK += 1

            # chose acceptable attributes based on tag class, else bail
            if  self.mathmlOK and tag in self.mathml_elements:
                acceptable_attributes = self.mathml_attributes
            elif self.svgOK and tag in self.svg_elements:
                # for most vocabularies, lowercasing is a good idea.  Many
                # svg elements, however, are camel case
                if not self.svg_attr_map:
                    lower=[attr.lower() for attr in self.svg_attributes]
                    mix=[a for a in self.svg_attributes if a not in lower]
                    self.svg_attributes = lower
                    self.svg_attr_map = dict([(a.lower(),a) for a in mix])

                    lower=[attr.lower() for attr in self.svg_elements]
                    mix=[a for a in self.svg_elements if a not in lower]
                    self.svg_elements = lower
                    self.svg_elem_map = dict([(a.lower(),a) for a in mix])
                acceptable_attributes = self.svg_attributes
                tag = self.svg_elem_map.get(tag,tag)
                keymap = self.svg_attr_map
            elif not tag in self.acceptable_elements:
                return

        # declare xlink namespace, if needed
        if self.mathmlOK or self.svgOK:
            if filter(lambda (n,v): n.startswith('xlink:'),attrs):
                if not ('xmlns:xlink','http://www.w3.org/1999/xlink') in attrs:
                    attrs.append(('xmlns:xlink','http://www.w3.org/1999/xlink'))

        clean_attrs = []
        for key, value in self.normalize_attrs(attrs):
            if key in acceptable_attributes:
                key=keymap.get(key,key)
                # make sure the uri uses an acceptable uri scheme
                if key == u'href':
                    value = _makeSafeAbsoluteURI(value)
                clean_attrs.append((key,value))
            elif key=='style':
                clean_value = self.sanitize_style(value)
                if clean_value:
                    clean_attrs.append((key,clean_value))
        _BaseHTMLProcessor.unknown_starttag(self, tag, clean_attrs)

    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            if self.mathmlOK and tag in self.mathml_elements:
                if tag == 'math' and self.mathmlOK:
                    self.mathmlOK -= 1
            elif self.svgOK and tag in self.svg_elements:
                tag = self.svg_elem_map.get(tag,tag)
                if tag == 'svg' and self.svgOK:
                    self.svgOK -= 1
            else:
                return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)

    def sanitize_style(self, style):
        # disallow urls
        style=re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*').sub(' ',style)

        # gauntlet
        if not re.match("""^([:,;#%.\sa-zA-Z0-9!]|\w-\w|'[\s\w]+'|"[\s\w]+"|\([\d,\s]+\))*$""", style):
            return ''
        # This replaced a regexp that used re.match and was prone to pathological back-tracking.
        if re.sub("\s*[-\w]+\s*:\s*[^:;]*;?", '', style).strip():
            return ''

        clean = []
        for prop,value in re.findall("([-\w]+)\s*:\s*([^:;]*)",style):
            if not value:
                continue
            if prop.lower() in self.acceptable_css_properties:
                clean.append(prop + ': ' + value + ';')
            elif prop.split('-')[0].lower() in ['background','border','margin','padding']:
                for keyword in value.split():
                    if not keyword in self.acceptable_css_keywords and \
                        not self.valid_css_values.match(keyword):
                        break
                else:
                    clean.append(prop + ': ' + value + ';')
            elif self.svgOK and prop.lower() in self.acceptable_svg_properties:
                clean.append(prop + ': ' + value + ';')

        return ' '.join(clean)

    def parse_comment(self, i, report=1):
        ret = _BaseHTMLProcessor.parse_comment(self, i, report)
        if ret >= 0:
            return ret
        # if ret == -1, this may be a malicious attempt to circumvent
        # sanitization, or a page-destroying unclosed comment
        match = re.compile(r'--[^>]*>').search(self.rawdata, i+4)
        if match:
            return match.end()
        # unclosed comment; deliberately fail to handle_data()
        return len(self.rawdata)


def _sanitizeHTML(htmlSource, encoding, _type):
    if not _SGML_AVAILABLE:
        return htmlSource
    p = _HTMLSanitizer(encoding, _type)
    htmlSource = htmlSource.replace('<![CDATA[', '&lt;![CDATA[')
    p.feed(htmlSource)
    data = p.output()
    if TIDY_MARKUP:
        # loop through list of preferred Tidy interfaces looking for one that's installed,
        # then set up a common _tidy function to wrap the interface-specific API.
        _tidy = None
        for tidy_interface in PREFERRED_TIDY_INTERFACES:
            try:
                if tidy_interface == "uTidy":
                    from tidy import parseString as _utidy
                    def _tidy(data, **kwargs):
                        return str(_utidy(data, **kwargs))
                    break
                elif tidy_interface == "mxTidy":
                    from mx.Tidy import Tidy as _mxtidy
                    def _tidy(data, **kwargs):
                        nerrors, nwarnings, data, errordata = _mxtidy.tidy(data, **kwargs)
                        return data
                    break
            except:
                pass
        if _tidy:
            utf8 = isinstance(data, unicode)
            if utf8:
                data = data.encode('utf-8')
            data = _tidy(data, output_xhtml=1, numeric_entities=1, wrap=0, char_encoding="utf8")
            if utf8:
                data = unicode(data, 'utf-8')
            if data.count('<body'):
                data = data.split('<body', 1)[1]
                if data.count('>'):
                    data = data.split('>', 1)[1]
            if data.count('</body'):
                data = data.split('</body', 1)[0]
    data = data.strip().replace('\r\n', '\n')
    return data

class _FeedURLHandler(urllib2.HTTPDigestAuthHandler, urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        # The default implementation just raises HTTPError.
        # Forget that.
        fp.status = code
        return fp

    def http_error_301(self, req, fp, code, msg, hdrs):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp,
                                                            code, msg, hdrs)
        result.status = code
        result.newurl = result.geturl()
        return result
    # The default implementations in urllib2.HTTPRedirectHandler
    # are identical, so hardcoding a http_error_301 call above
    # won't affect anything
    http_error_300 = http_error_301
    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301

    def http_error_401(self, req, fp, code, msg, headers):
        # Check if
        # - server requires digest auth, AND
        # - we tried (unsuccessfully) with basic auth, AND
        # If all conditions hold, parse authentication information
        # out of the Authorization header we sent the first time
        # (for the username and password) and the WWW-Authenticate
        # header the server sent back (for the realm) and retry
        # the request with the appropriate digest auth headers instead.
        # This evil genius hack has been brought to you by Aaron Swartz.
        host = urlparse.urlparse(req.get_full_url())[1]
        if base64 is None or 'Authorization' not in req.headers \
                          or 'WWW-Authenticate' not in headers:
            return self.http_error_default(req, fp, code, msg, headers)
        auth = _base64decode(req.headers['Authorization'].split(' ')[1])
        user, passw = auth.split(':')
        realm = re.findall('realm="([^"]*)"', headers['WWW-Authenticate'])[0]
        self.add_password(realm, host, user, passw)
        retry = self.http_error_auth_reqed('www-authenticate', host, req, headers)
        self.reset_retry_count()
        return retry

def _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers, request_headers):
    """URL, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it can be a tuple of 9 integers
    (as returned by gmtime() in the standard Python time module) or a date
    string in any format supported by feedparser. Regardless, it MUST
    be in GMT (Greenwich Mean Time). It will be reformatted into an
    RFC 1123-compliant date and used as the value of an If-Modified-Since
    request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.

    If handlers is supplied, it is a list of handlers used to build a
    urllib2 opener.

    if request_headers is supplied it is a dictionary of HTTP request headers
    that will override the values generated by FeedParser.
    """

    if hasattr(url_file_stream_or_string, 'read'):
        return url_file_stream_or_string

    if isinstance(url_file_stream_or_string, basestring) \
       and urlparse.urlparse(url_file_stream_or_string)[0] in ('http', 'https', 'ftp', 'file', 'feed'):
        # Deal with the feed URI scheme
        if url_file_stream_or_string.startswith('feed:http'):
            url_file_stream_or_string = url_file_stream_or_string[5:]
        elif url_file_stream_or_string.startswith('feed:'):
            url_file_stream_or_string = 'http:' + url_file_stream_or_string[5:]
        if not agent:
            agent = USER_AGENT
        # test for inline user:password for basic auth
        auth = None
        if base64:
            urltype, rest = urllib.splittype(url_file_stream_or_string)
            realhost, rest = urllib.splithost(rest)
            if realhost:
                user_passwd, realhost = urllib.splituser(realhost)
                if user_passwd:
                    url_file_stream_or_string = '%s://%s%s' % (urltype, realhost, rest)
                    auth = base64.standard_b64encode(user_passwd).strip()

        # iri support
        if isinstance(url_file_stream_or_string, unicode):
            url_file_stream_or_string = _convert_to_idn(url_file_stream_or_string)

        # try to open with urllib2 (to use optional headers)
        request = _build_urllib2_request(url_file_stream_or_string, agent, etag, modified, referrer, auth, request_headers)
        opener = urllib2.build_opener(*tuple(handlers + [_FeedURLHandler()]))
        opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
        try:
            return opener.open(request)
        finally:
            opener.close() # JohnD

    # try to open with native open function (if url_file_stream_or_string is a filename)
    try:
        return open(url_file_stream_or_string, 'rb')
    except (IOError, UnicodeEncodeError, TypeError):
        # if url_file_stream_or_string is a unicode object that
        # cannot be converted to the encoding returned by
        # sys.getfilesystemencoding(), a UnicodeEncodeError
        # will be thrown
        # If url_file_stream_or_string is a string that contains NULL
        # (such as an XML document encoded in UTF-32), TypeError will
        # be thrown.
        pass

    # treat url_file_stream_or_string as string
    if isinstance(url_file_stream_or_string, unicode):
        return _StringIO(url_file_stream_or_string.encode('utf-8'))
    return _StringIO(url_file_stream_or_string)

def _convert_to_idn(url):
    """Convert a URL to IDN notation"""
    # this function should only be called with a unicode string
    # strategy: if the host cannot be encoded in ascii, then
    # it'll be necessary to encode it in idn form
    parts = list(urlparse.urlsplit(url))
    try:
        parts[1].encode('ascii')
    except UnicodeEncodeError:
        # the url needs to be converted to idn notation
        host = parts[1].rsplit(':', 1)
        newhost = []
        port = u''
        if len(host) == 2:
            port = host.pop()
        for h in host[0].split('.'):
            newhost.append(h.encode('idna').decode('utf-8'))
        parts[1] = '.'.join(newhost)
        if port:
            parts[1] += ':' + port
        return urlparse.urlunsplit(parts)
    else:
        return url

def _build_urllib2_request(url, agent, etag, modified, referrer, auth, request_headers):
    request = urllib2.Request(url)
    request.add_header('User-Agent', agent)
    if etag:
        request.add_header('If-None-Match', etag)
    if isinstance(modified, basestring):
        modified = _parse_date(modified)
    elif isinstance(modified, datetime.datetime):
        modified = modified.utctimetuple()
    if modified:
        # format into an RFC 1123-compliant timestamp. We can't use
        # time.strftime() since the %a and %b directives can be affected
        # by the current locale, but RFC 2616 states that dates must be
        # in English.
        short_weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        request.add_header('If-Modified-Since', '%s, %02d %s %04d %02d:%02d:%02d GMT' % (short_weekdays[modified[6]], modified[2], months[modified[1] - 1], modified[0], modified[3], modified[4], modified[5]))
    if referrer:
        request.add_header('Referer', referrer)
    if gzip and zlib:
        request.add_header('Accept-encoding', 'gzip, deflate')
    elif gzip:
        request.add_header('Accept-encoding', 'gzip')
    elif zlib:
        request.add_header('Accept-encoding', 'deflate')
    else:
        request.add_header('Accept-encoding', '')
    if auth:
        request.add_header('Authorization', 'Basic %s' % auth)
    if ACCEPT_HEADER:
        request.add_header('Accept', ACCEPT_HEADER)
    # use this for whatever -- cookies, special headers, etc
    # [('Cookie','Something'),('x-special-header','Another Value')]
    for header_name, header_value in request_headers.items():
        request.add_header(header_name, header_value)
    request.add_header('A-IM', 'feed') # RFC 3229 support
    return request

_date_handlers = []
def registerDateHandler(func):
    '''Register a date handler function (takes string, returns 9-tuple date in GMT)'''
    _date_handlers.insert(0, func)

# ISO-8601 date parsing routines written by Fazal Majid.
# The ISO 8601 standard is very convoluted and irregular - a full ISO 8601
# parser is beyond the scope of feedparser and would be a worthwhile addition
# to the Python library.
# A single regular expression cannot parse ISO 8601 date formats into groups
# as the standard is highly irregular (for instance is 030104 2003-01-04 or
# 0301-04-01), so we use templates instead.
# Please note the order in templates is significant because we need a
# greedy match.
_iso8601_tmpl = ['YYYY-?MM-?DD', 'YYYY-0MM?-?DD', 'YYYY-MM', 'YYYY-?OOO',
                'YY-?MM-?DD', 'YY-?OOO', 'YYYY',
                '-YY-?MM', '-OOO', '-YY',
                '--MM-?DD', '--MM',
                '---DD',
                'CC', '']
_iso8601_re = [
    tmpl.replace(
    'YYYY', r'(?P<year>\d{4})').replace(
    'YY', r'(?P<year>\d\d)').replace(
    'MM', r'(?P<month>[01]\d)').replace(
    'DD', r'(?P<day>[0123]\d)').replace(
    'OOO', r'(?P<ordinal>[0123]\d\d)').replace(
    'CC', r'(?P<century>\d\d$)')
    + r'(T?(?P<hour>\d{2}):(?P<minute>\d{2})'
    + r'(:(?P<second>\d{2}))?'
    + r'(\.(?P<fracsecond>\d+))?'
    + r'(?P<tz>[+-](?P<tzhour>\d{2})(:(?P<tzmin>\d{2}))?|Z)?)?'
    for tmpl in _iso8601_tmpl]
try:
    del tmpl
except NameError:
    pass
_iso8601_matches = [re.compile(regex).match for regex in _iso8601_re]
try:
    del regex
except NameError:
    pass
def _parse_date_iso8601(dateString):
    '''Parse a variety of ISO-8601-compatible formats like 20040105'''
    m = None
    for _iso8601_match in _iso8601_matches:
        m = _iso8601_match(dateString)
        if m:
            break
    if not m:
        return
    if m.span() == (0, 0):
        return
    params = m.groupdict()
    ordinal = params.get('ordinal', 0)
    if ordinal:
        ordinal = int(ordinal)
    else:
        ordinal = 0
    year = params.get('year', '--')
    if not year or year == '--':
        year = time.gmtime()[0]
    elif len(year) == 2:
        # ISO 8601 assumes current century, i.e. 93 -> 2093, NOT 1993
        year = 100 * int(time.gmtime()[0] / 100) + int(year)
    else:
        year = int(year)
    month = params.get('month', '-')
    if not month or month == '-':
        # ordinals are NOT normalized by mktime, we simulate them
        # by setting month=1, day=ordinal
        if ordinal:
            month = 1
        else:
            month = time.gmtime()[1]
    month = int(month)
    day = params.get('day', 0)
    if not day:
        # see above
        if ordinal:
            day = ordinal
        elif params.get('century', 0) or \
                 params.get('year', 0) or params.get('month', 0):
            day = 1
        else:
            day = time.gmtime()[2]
    else:
        day = int(day)
    # special case of the century - is the first year of the 21st century
    # 2000 or 2001 ? The debate goes on...
    if 'century' in params:
        year = (int(params['century']) - 1) * 100 + 1
    # in ISO 8601 most fields are optional
    for field in ['hour', 'minute', 'second', 'tzhour', 'tzmin']:
        if not params.get(field, None):
            params[field] = 0
    hour = int(params.get('hour', 0))
    minute = int(params.get('minute', 0))
    second = int(float(params.get('second', 0)))
    # weekday is normalized by mktime(), we can ignore it
    weekday = 0
    daylight_savings_flag = -1
    tm = [year, month, day, hour, minute, second, weekday,
          ordinal, daylight_savings_flag]
    # ISO 8601 time zone adjustments
    tz = params.get('tz')
    if tz and tz != 'Z':
        if tz[0] == '-':
            tm[3] += int(params.get('tzhour', 0))
            tm[4] += int(params.get('tzmin', 0))
        elif tz[0] == '+':
            tm[3] -= int(params.get('tzhour', 0))
            tm[4] -= int(params.get('tzmin', 0))
        else:
            return None
    # Python's time.mktime() is a wrapper around the ANSI C mktime(3c)
    # which is guaranteed to normalize d/m/y/h/m/s.
    # Many implementations have bugs, but we'll pretend they don't.
    return time.localtime(time.mktime(tuple(tm)))
registerDateHandler(_parse_date_iso8601)

# 8-bit date handling routines written by ytrewq1.
_korean_year  = u'\ub144' # b3e2 in euc-kr
_korean_month = u'\uc6d4' # bff9 in euc-kr
_korean_day   = u'\uc77c' # c0cf in euc-kr
_korean_am    = u'\uc624\uc804' # bfc0 c0fc in euc-kr
_korean_pm    = u'\uc624\ud6c4' # bfc0 c8c4 in euc-kr

_korean_onblog_date_re = \
    re.compile('(\d{4})%s\s+(\d{2})%s\s+(\d{2})%s\s+(\d{2}):(\d{2}):(\d{2})' % \
               (_korean_year, _korean_month, _korean_day))
_korean_nate_date_re = \
    re.compile(u'(\d{4})-(\d{2})-(\d{2})\s+(%s|%s)\s+(\d{,2}):(\d{,2}):(\d{,2})' % \
               (_korean_am, _korean_pm))
def _parse_date_onblog(dateString):
    '''Parse a string according to the OnBlog 8-bit date format'''
    m = _korean_onblog_date_re.match(dateString)
    if not m:
        return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_onblog)

def _parse_date_nate(dateString):
    '''Parse a string according to the Nate 8-bit date format'''
    m = _korean_nate_date_re.match(dateString)
    if not m:
        return
    hour = int(m.group(5))
    ampm = m.group(4)
    if (ampm == _korean_pm):
        hour += 12
    hour = str(hour)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': hour, 'minute': m.group(6), 'second': m.group(7),\
                 'zonediff': '+09:00'}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_nate)

# Unicode strings for Greek date strings
_greek_months = \
  { \
   u'\u0399\u03b1\u03bd': u'Jan',       # c9e1ed in iso-8859-7
   u'\u03a6\u03b5\u03b2': u'Feb',       # d6e5e2 in iso-8859-7
   u'\u039c\u03ac\u03ce': u'Mar',       # ccdcfe in iso-8859-7
   u'\u039c\u03b1\u03ce': u'Mar',       # cce1fe in iso-8859-7
   u'\u0391\u03c0\u03c1': u'Apr',       # c1f0f1 in iso-8859-7
   u'\u039c\u03ac\u03b9': u'May',       # ccdce9 in iso-8859-7
   u'\u039c\u03b1\u03ca': u'May',       # cce1fa in iso-8859-7
   u'\u039c\u03b1\u03b9': u'May',       # cce1e9 in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bd': u'Jun', # c9effded in iso-8859-7
   u'\u0399\u03bf\u03bd': u'Jun',       # c9efed in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bb': u'Jul', # c9effdeb in iso-8859-7
   u'\u0399\u03bf\u03bb': u'Jul',       # c9f9eb in iso-8859-7
   u'\u0391\u03cd\u03b3': u'Aug',       # c1fde3 in iso-8859-7
   u'\u0391\u03c5\u03b3': u'Aug',       # c1f5e3 in iso-8859-7
   u'\u03a3\u03b5\u03c0': u'Sep',       # d3e5f0 in iso-8859-7
   u'\u039f\u03ba\u03c4': u'Oct',       # cfeaf4 in iso-8859-7
   u'\u039d\u03bf\u03ad': u'Nov',       # cdefdd in iso-8859-7
   u'\u039d\u03bf\u03b5': u'Nov',       # cdefe5 in iso-8859-7
   u'\u0394\u03b5\u03ba': u'Dec',       # c4e5ea in iso-8859-7
  }

_greek_wdays = \
  { \
   u'\u039a\u03c5\u03c1': u'Sun', # caf5f1 in iso-8859-7
   u'\u0394\u03b5\u03c5': u'Mon', # c4e5f5 in iso-8859-7
   u'\u03a4\u03c1\u03b9': u'Tue', # d4f1e9 in iso-8859-7
   u'\u03a4\u03b5\u03c4': u'Wed', # d4e5f4 in iso-8859-7
   u'\u03a0\u03b5\u03bc': u'Thu', # d0e5ec in iso-8859-7
   u'\u03a0\u03b1\u03c1': u'Fri', # d0e1f1 in iso-8859-7
   u'\u03a3\u03b1\u03b2': u'Sat', # d3e1e2 in iso-8859-7
  }

_greek_date_format_re = \
    re.compile(u'([^,]+),\s+(\d{2})\s+([^\s]+)\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+([^\s]+)')

def _parse_date_greek(dateString):
    '''Parse a string according to a Greek 8-bit date format.'''
    m = _greek_date_format_re.match(dateString)
    if not m:
        return
    wday = _greek_wdays[m.group(1)]
    month = _greek_months[m.group(3)]
    rfc822date = '%(wday)s, %(day)s %(month)s %(year)s %(hour)s:%(minute)s:%(second)s %(zonediff)s' % \
                 {'wday': wday, 'day': m.group(2), 'month': month, 'year': m.group(4),\
                  'hour': m.group(5), 'minute': m.group(6), 'second': m.group(7),\
                  'zonediff': m.group(8)}
    return _parse_date_rfc822(rfc822date)
registerDateHandler(_parse_date_greek)

# Unicode strings for Hungarian date strings
_hungarian_months = \
  { \
    u'janu\u00e1r':   u'01',  # e1 in iso-8859-2
    u'febru\u00e1ri': u'02',  # e1 in iso-8859-2
    u'm\u00e1rcius':  u'03',  # e1 in iso-8859-2
    u'\u00e1prilis':  u'04',  # e1 in iso-8859-2
    u'm\u00e1ujus':   u'05',  # e1 in iso-8859-2
    u'j\u00fanius':   u'06',  # fa in iso-8859-2
    u'j\u00falius':   u'07',  # fa in iso-8859-2
    u'augusztus':     u'08',
    u'szeptember':    u'09',
    u'okt\u00f3ber':  u'10',  # f3 in iso-8859-2
    u'november':      u'11',
    u'december':      u'12',
  }

_hungarian_date_format_re = \
  re.compile(u'(\d{4})-([^-]+)-(\d{,2})T(\d{,2}):(\d{2})((\+|-)(\d{,2}:\d{2}))')

def _parse_date_hungarian(dateString):
    '''Parse a string according to a Hungarian 8-bit date format.'''
    m = _hungarian_date_format_re.match(dateString)
    if not m or m.group(2) not in _hungarian_months:
        return None
    month = _hungarian_months[m.group(2)]
    day = m.group(3)
    if len(day) == 1:
        day = '0' + day
    hour = m.group(4)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s%(zonediff)s' % \
                {'year': m.group(1), 'month': month, 'day': day,\
                 'hour': hour, 'minute': m.group(5),\
                 'zonediff': m.group(6)}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_hungarian)

# W3DTF-style date parsing adapted from PyXML xml.utils.iso8601, written by
# Drake and licensed under the Python license.  Removed all range checking
# for month, day, hour, minute, and second, since mktime will normalize
# these later
# Modified to also support MSSQL-style datetimes as defined at:
# http://msdn.microsoft.com/en-us/library/ms186724.aspx
# (which basically means allowing a space as a date/time/timezone separator)
def _parse_date_w3dtf(dateString):
    def __extract_date(m):
        year = int(m.group('year'))
        if year < 100:
            year = 100 * int(time.gmtime()[0] / 100) + int(year)
        if year < 1000:
            return 0, 0, 0
        julian = m.group('julian')
        if julian:
            julian = int(julian)
            month = julian / 30 + 1
            day = julian % 30 + 1
            jday = None
            while jday != julian:
                t = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
                jday = time.gmtime(t)[-2]
                diff = abs(jday - julian)
                if jday > julian:
                    if diff < day:
                        day = day - diff
                    else:
                        month = month - 1
                        day = 31
                elif jday < julian:
                    if day + diff < 28:
                        day = day + diff
                    else:
                        month = month + 1
            return year, month, day
        month = m.group('month')
        day = 1
        if month is None:
            month = 1
        else:
            month = int(month)
            day = m.group('day')
            if day:
                day = int(day)
            else:
                day = 1
        return year, month, day

    def __extract_time(m):
        if not m:
            return 0, 0, 0
        hours = m.group('hours')
        if not hours:
            return 0, 0, 0
        hours = int(hours)
        minutes = int(m.group('minutes'))
        seconds = m.group('seconds')
        if seconds:
            seconds = int(seconds)
        else:
            seconds = 0
        return hours, minutes, seconds

    def __extract_tzd(m):
        '''Return the Time Zone Designator as an offset in seconds from UTC.'''
        if not m:
            return 0
        tzd = m.group('tzd')
        if not tzd:
            return 0
        if tzd == 'Z':
            return 0
        hours = int(m.group('tzdhours'))
        minutes = m.group('tzdminutes')
        if minutes:
            minutes = int(minutes)
        else:
            minutes = 0
        offset = (hours*60 + minutes) * 60
        if tzd[0] == '+':
            return -offset
        return offset

    __date_re = ('(?P<year>\d\d\d\d)'
                 '(?:(?P<dsep>-|)'
                 '(?:(?P<month>\d\d)(?:(?P=dsep)(?P<day>\d\d))?'
                 '|(?P<julian>\d\d\d)))?')
    __tzd_re = ' ?(?P<tzd>[-+](?P<tzdhours>\d\d)(?::?(?P<tzdminutes>\d\d))|Z)?'
    __time_re = ('(?P<hours>\d\d)(?P<tsep>:|)(?P<minutes>\d\d)'
                 '(?:(?P=tsep)(?P<seconds>\d\d)(?:[.,]\d+)?)?'
                 + __tzd_re)
    __datetime_re = '%s(?:[T ]%s)?' % (__date_re, __time_re)
    __datetime_rx = re.compile(__datetime_re)
    m = __datetime_rx.match(dateString)
    if (m is None) or (m.group() != dateString):
        return
    gmt = __extract_date(m) + __extract_time(m) + (0, 0, 0)
    if gmt[0] == 0:
        return
    return time.gmtime(time.mktime(gmt) + __extract_tzd(m) - time.timezone)
registerDateHandler(_parse_date_w3dtf)

# Define the strings used by the RFC822 datetime parser
_rfc822_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
_rfc822_daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# Only the first three letters of the month name matter
_rfc822_month = "(?P<month>%s)(?:[a-z]*,?)" % ('|'.join(_rfc822_months))
# The year may be 2 or 4 digits; capture the century if it exists
_rfc822_year = "(?P<year>(?:\d{2})?\d{2})"
_rfc822_day = "(?P<day> *\d{1,2})"
_rfc822_date = "%s %s %s" % (_rfc822_day, _rfc822_month, _rfc822_year)

_rfc822_hour = "(?P<hour>\d{2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?"
_rfc822_tz = "(?P<tz>ut|gmt(?:[+-]\d{2}:\d{2})?|[aecmp][sd]?t|[zamny]|[+-]\d{4})"
_rfc822_tznames = {
    'ut': 0, 'gmt': 0, 'z': 0,
    'adt': -3, 'ast': -4, 'at': -4,
    'edt': -4, 'est': -5, 'et': -5,
    'cdt': -5, 'cst': -6, 'ct': -6,
    'mdt': -6, 'mst': -7, 'mt': -7,
    'pdt': -7, 'pst': -8, 'pt': -8,
    'a': -1, 'n': 1,
    'm': -12, 'y': 12,
 }
# The timezone may be prefixed by 'Etc/'
_rfc822_time = "%s (?:etc/)?%s" % (_rfc822_hour, _rfc822_tz)

_rfc822_dayname = "(?P<dayname>%s)" % ('|'.join(_rfc822_daynames))
_rfc822_match = re.compile(
    "(?:%s, )?%s(?: %s)?" % (_rfc822_dayname, _rfc822_date, _rfc822_time)
).match

def _parse_date_rfc822(dt):
    """Parse RFC 822 dates and times, with one minor
    difference: years may be 4DIGIT or 2DIGIT.
    http://tools.ietf.org/html/rfc822#section-5"""
    try:
        m = _rfc822_match(dt.lower()).groupdict(0)
    except AttributeError:
        return None

    # Calculate a date and timestamp
    for k in ('year', 'day', 'hour', 'minute', 'second'):
        m[k] = int(m[k])
    m['month'] = _rfc822_months.index(m['month']) + 1
    # If the year is 2 digits, assume everything in the 90's is the 1990's
    if m['year'] < 100:
        m['year'] += (1900, 2000)[m['year'] < 90]
    stamp = datetime.datetime(*[m[i] for i in
                ('year', 'month', 'day', 'hour', 'minute', 'second')])

    # Use the timezone information to calculate the difference between
    # the given date and timestamp and Universal Coordinated Time
    tzhour = 0
    tzmin = 0
    if m['tz'] and m['tz'].startswith('gmt'):
        # Handle GMT and GMT+hh:mm timezone syntax (the trailing
        # timezone info will be handled by the next `if` block)
        m['tz'] = ''.join(m['tz'][3:].split(':')) or 'gmt'
    if not m['tz']:
        pass
    elif m['tz'].startswith('+'):
        tzhour = int(m['tz'][1:3])
        tzmin = int(m['tz'][3:])
    elif m['tz'].startswith('-'):
        tzhour = int(m['tz'][1:3]) * -1
        tzmin = int(m['tz'][3:]) * -1
    else:
        tzhour = _rfc822_tznames[m['tz']]
    delta = datetime.timedelta(0, 0, 0, 0, tzmin, tzhour)

    # Return the date and timestamp in UTC
    return (stamp - delta).utctimetuple()
registerDateHandler(_parse_date_rfc822)

def _parse_date_asctime(dt):
    """Parse asctime-style dates"""
    dayname, month, day, remainder = dt.split(None, 3)
    # Convert month and day into zero-padded integers
    month = '%02i ' % (_rfc822_months.index(month.lower()) + 1)
    day = '%02i ' % (int(day),)
    dt = month + day + remainder
    return time.strptime(dt, '%m %d %H:%M:%S %Y')[:-1] + (0, )
registerDateHandler(_parse_date_asctime)

def _parse_date_perforce(aDateString):
    """parse a date in yyyy/mm/dd hh:mm:ss TTT format"""
    # Fri, 2006/09/15 08:19:53 EDT
    _my_date_pattern = re.compile( \
        r'(\w{,3}), (\d{,4})/(\d{,2})/(\d{2}) (\d{,2}):(\d{2}):(\d{2}) (\w{,3})')

    m = _my_date_pattern.search(aDateString)
    if m is None:
        return None
    dow, year, month, day, hour, minute, second, tz = m.groups()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    dateString = "%s, %s %s %s %s:%s:%s %s" % (dow, day, months[int(month) - 1], year, hour, minute, second, tz)
    tm = rfc822.parsedate_tz(dateString)
    if tm:
        return time.gmtime(rfc822.mktime_tz(tm))
registerDateHandler(_parse_date_perforce)

def _parse_date(dateString):
    '''Parses a variety of date formats into a 9-tuple in GMT'''
    if not dateString:
        return None
    for handler in _date_handlers:
        try:
            date9tuple = handler(dateString)
        except (KeyError, OverflowError, ValueError):
            continue
        if not date9tuple:
            continue
        if len(date9tuple) != 9:
            continue
        return date9tuple
    return None

def _getCharacterEncoding(http_headers, xml_data):
    '''Get the character encoding of the XML document

    http_headers is a dictionary
    xml_data is a raw string (not Unicode)

    This is so much trickier than it sounds, it's not even funny.
    According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    is application/xml, application/*+xml,
    application/xml-external-parsed-entity, or application/xml-dtd,
    the encoding given in the charset parameter of the HTTP Content-Type
    takes precedence over the encoding given in the XML prefix within the
    document, and defaults to 'utf-8' if neither are specified.  But, if
    the HTTP Content-Type is text/xml, text/*+xml, or
    text/xml-external-parsed-entity, the encoding given in the XML prefix
    within the document is ALWAYS IGNORED and only the encoding given in
    the charset parameter of the HTTP Content-Type header should be
    respected, and it defaults to 'us-ascii' if not specified.

    Furthermore, discussion on the atom-syntax mailing list with the
    author of RFC 3023 leads me to the conclusion that any document
    served with a Content-Type of text/* and no charset parameter
    must be treated as us-ascii.  (We now do this.)  And also that it
    must always be flagged as non-well-formed.  (We now do this too.)

    If Content-Type is unspecified (input was local file or non-HTTP source)
    or unrecognized (server just got it totally wrong), then go by the
    encoding given in the XML prefix of the document and default to
    'iso-8859-1' as per the HTTP specification (RFC 2616).

    Then, assuming we didn't find a character encoding in the HTTP headers
    (and the HTTP Content-type allowed us to look in the body), we need
    to sniff the first few bytes of the XML data and try to determine
    whether the encoding is ASCII-compatible.  Section F of the XML
    specification shows the way here:
    http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    If the sniffed encoding is not ASCII-compatible, we need to make it
    ASCII compatible so that we can sniff further into the XML declaration
    to find the encoding attribute, which will tell us the true encoding.

    Of course, none of this guarantees that we will be able to parse the
    feed in the declared character encoding (assuming it was declared
    correctly, which many are not).  iconv_codec can help a lot;
    you should definitely install it if you can.
    http://cjkpython.i18n.org/
    '''

    def _parseHTTPContentType(content_type):
        '''takes HTTP Content-Type header and returns (content type, charset)

        If no charset is specified, returns (content type, '')
        If no content type is specified, returns ('', '')
        Both return parameters are guaranteed to be lowercase strings
        '''
        content_type = content_type or ''
        content_type, params = cgi.parse_header(content_type)
        charset = params.get('charset', '').replace("'", "")
        if not isinstance(charset, unicode):
            charset = charset.decode('utf-8', 'ignore')
        return content_type, charset

    sniffed_xml_encoding = u''
    xml_encoding = u''
    true_encoding = u''
    http_content_type, http_encoding = _parseHTTPContentType(http_headers.get('content-type'))
    # Must sniff for non-ASCII-compatible character encodings before
    # searching for XML declaration.  This heuristic is defined in
    # section F of the XML specification:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    try:
        if xml_data[:4] == _l2bytes([0x4c, 0x6f, 0xa7, 0x94]):
            # In all forms of EBCDIC, these four bytes correspond
            # to the string '<?xm'; try decoding using CP037
            sniffed_xml_encoding = u'cp037'
            xml_data = xml_data.decode('cp037').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0x00, 0x3c, 0x00, 0x3f]):
            # UTF-16BE
            sniffed_xml_encoding = u'utf-16be'
            xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == _l2bytes([0xfe, 0xff])) and (xml_data[2:4] != _l2bytes([0x00, 0x00])):
            # UTF-16BE with BOM
            sniffed_xml_encoding = u'utf-16be'
            xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0x3c, 0x00, 0x3f, 0x00]):
            # UTF-16LE
            sniffed_xml_encoding = u'utf-16le'
            xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == _l2bytes([0xff, 0xfe])) and (xml_data[2:4] != _l2bytes([0x00, 0x00])):
            # UTF-16LE with BOM
            sniffed_xml_encoding = u'utf-16le'
            xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0x00, 0x00, 0x00, 0x3c]):
            # UTF-32BE
            sniffed_xml_encoding = u'utf-32be'
            if _UTF32_AVAILABLE:
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0x3c, 0x00, 0x00, 0x00]):
            # UTF-32LE
            sniffed_xml_encoding = u'utf-32le'
            if _UTF32_AVAILABLE:
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0x00, 0x00, 0xfe, 0xff]):
            # UTF-32BE with BOM
            sniffed_xml_encoding = u'utf-32be'
            if _UTF32_AVAILABLE:
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
        elif xml_data[:4] == _l2bytes([0xff, 0xfe, 0x00, 0x00]):
            # UTF-32LE with BOM
            sniffed_xml_encoding = u'utf-32le'
            if _UTF32_AVAILABLE:
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
        elif xml_data[:3] == _l2bytes([0xef, 0xbb, 0xbf]):
            # UTF-8 with BOM
            sniffed_xml_encoding = u'utf-8'
            xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
        else:
            # ASCII-compatible
            pass
        xml_encoding_match = re.compile(_s2bytes('^<\?.*encoding=[\'"](.*?)[\'"].*\?>')).match(xml_data)
    except UnicodeDecodeError:
        xml_encoding_match = None
    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].decode('utf-8').lower()
        if sniffed_xml_encoding and (xml_encoding in (u'iso-10646-ucs-2', u'ucs-2', u'csunicode', u'iso-10646-ucs-4', u'ucs-4', u'csucs4', u'utf-16', u'utf-32', u'utf_16', u'utf_32', u'utf16', u'u16')):
            xml_encoding = sniffed_xml_encoding
    acceptable_content_type = 0
    application_content_types = (u'application/xml', u'application/xml-dtd', u'application/xml-external-parsed-entity')
    text_content_types = (u'text/xml', u'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith(u'application/') and http_content_type.endswith(u'+xml')):
        acceptable_content_type = 1
        true_encoding = http_encoding or xml_encoding or u'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith(u'text/')) and http_content_type.endswith(u'+xml'):
        acceptable_content_type = 1
        true_encoding = http_encoding or u'us-ascii'
    elif http_content_type.startswith(u'text/'):
        true_encoding = http_encoding or u'us-ascii'
    elif http_headers and 'content-type' not in http_headers:
        true_encoding = xml_encoding or u'iso-8859-1'
    else:
        true_encoding = xml_encoding or u'utf-8'
    # some feeds claim to be gb2312 but are actually gb18030.
    # apparently MSIE and Firefox both do the following switch:
    if true_encoding.lower() == u'gb2312':
        true_encoding = u'gb18030'
    return true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type

def _toUTF8(data, encoding):
    '''Changes an XML data stream on the fly to specify a new encoding

    data is a raw sequence of bytes (not Unicode) that is presumed to be in %encoding already
    encoding is a string recognized by encodings.aliases
    '''
    # strip Byte Order Mark (if present)
    if (len(data) >= 4) and (data[:2] == _l2bytes([0xfe, 0xff])) and (data[2:4] != _l2bytes([0x00, 0x00])):
        encoding = 'utf-16be'
        data = data[2:]
    elif (len(data) >= 4) and (data[:2] == _l2bytes([0xff, 0xfe])) and (data[2:4] != _l2bytes([0x00, 0x00])):
        encoding = 'utf-16le'
        data = data[2:]
    elif data[:3] == _l2bytes([0xef, 0xbb, 0xbf]):
        encoding = 'utf-8'
        data = data[3:]
    elif data[:4] == _l2bytes([0x00, 0x00, 0xfe, 0xff]):
        encoding = 'utf-32be'
        data = data[4:]
    elif data[:4] == _l2bytes([0xff, 0xfe, 0x00, 0x00]):
        encoding = 'utf-32le'
        data = data[4:]
    newdata = unicode(data, encoding)
    declmatch = re.compile('^<\?xml[^>]*?>')
    newdecl = '''<?xml version='1.0' encoding='utf-8'?>'''
    if declmatch.search(newdata):
        newdata = declmatch.sub(newdecl, newdata)
    else:
        newdata = newdecl + u'\n' + newdata
    return newdata.encode('utf-8')

def _stripDoctype(data):
    '''Strips DOCTYPE from XML document, returns (rss_version, stripped_data)

    rss_version may be 'rss091n' or None
    stripped_data is the same XML document, minus the DOCTYPE
    '''
    start = re.search(_s2bytes('<\w'), data)
    start = start and start.start() or -1
    head,data = data[:start+1], data[start+1:]

    entity_pattern = re.compile(_s2bytes(r'^\s*<!ENTITY([^>]*?)>'), re.MULTILINE)
    entity_results=entity_pattern.findall(head)
    head = entity_pattern.sub(_s2bytes(''), head)
    doctype_pattern = re.compile(_s2bytes(r'^\s*<!DOCTYPE([^>]*?)>'), re.MULTILINE)
    doctype_results = doctype_pattern.findall(head)
    doctype = doctype_results and doctype_results[0] or _s2bytes('')
    if doctype.lower().count(_s2bytes('netscape')):
        version = u'rss091n'
    else:
        version = None

    # only allow in 'safe' inline entity definitions
    replacement=_s2bytes('')
    if len(doctype_results)==1 and entity_results:
        safe_pattern=re.compile(_s2bytes('\s+(\w+)\s+"(&#\w+;|[^&"]*)"'))
        safe_entities=filter(lambda e: safe_pattern.match(e),entity_results)
        if safe_entities:
            replacement=_s2bytes('<!DOCTYPE feed [\n  <!ENTITY') + _s2bytes('>\n  <!ENTITY ').join(safe_entities) + _s2bytes('>\n]>')
    data = doctype_pattern.sub(replacement, head) + data

    return version, data, dict(replacement and [(k.decode('utf-8'), v.decode('utf-8')) for k, v in safe_pattern.findall(replacement)])

def parse(url_file_stream_or_string, etag=None, modified=None, agent=None, referrer=None, handlers=None, request_headers=None, response_headers=None):
    '''Parse a feed from a URL, file, stream, or string.

    request_headers, if given, is a dict from http header name to value to add
    to the request; this overrides internally generated values.
    '''

    if handlers is None:
        handlers = []
    if request_headers is None:
        request_headers = {}
    if response_headers is None:
        response_headers = {}

    result = FeedParserDict()
    result['feed'] = FeedParserDict()
    result['entries'] = []
    result['bozo'] = 0
    if not isinstance(handlers, list):
        handlers = [handlers]
    try:
        f = _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers, request_headers)
        data = f.read()
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        data = None
        f = None

    if hasattr(f, 'headers'):
        result['headers'] = dict(f.headers)
    # overwrite existing headers using response_headers
    if 'headers' in result:
        result['headers'].update(response_headers)
    elif response_headers:
        result['headers'] = copy.deepcopy(response_headers)

    # lowercase all of the HTTP headers for comparisons per RFC 2616
    if 'headers' in result:
        http_headers = dict((k.lower(), v) for k, v in result['headers'].items())
    else:
        http_headers = {}

    # if feed is gzip-compressed, decompress it
    if f and data and http_headers:
        if gzip and 'gzip' in http_headers.get('content-encoding', ''):
            try:
                data = gzip.GzipFile(fileobj=_StringIO(data)).read()
            except (IOError, struct.error), e:
                # IOError can occur if the gzip header is bad.
                # struct.error can occur if the data is damaged.
                result['bozo'] = 1
                result['bozo_exception'] = e
                if isinstance(e, struct.error):
                    # A gzip header was found but the data is corrupt.
                    # Ideally, we should re-request the feed without the
                    # 'Accept-encoding: gzip' header, but we don't.
                    data = None
        elif zlib and 'deflate' in http_headers.get('content-encoding', ''):
            try:
                data = zlib.decompress(data)
            except zlib.error, e:
                try:
                    # The data may have no headers and no checksum.
                    data = zlib.decompress(data, -15)
                except zlib.error, e:
                    result['bozo'] = 1
                    result['bozo_exception'] = e

    # save HTTP headers
    if http_headers:
        if 'etag' in http_headers:
            etag = http_headers.get('etag', u'')
            if not isinstance(etag, unicode):
                etag = etag.decode('utf-8', 'ignore')
            if etag:
                result['etag'] = etag
        if 'last-modified' in http_headers:
            modified = http_headers.get('last-modified', u'')
            if modified:
                result['modified'] = modified
                result['modified_parsed'] = _parse_date(modified)
    if hasattr(f, 'url'):
        if not isinstance(f.url, unicode):
            result['href'] = f.url.decode('utf-8', 'ignore')
        else:
            result['href'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    if hasattr(f, 'close'):
        f.close()

    if data is None:
        return result

    # there are four encodings to keep track of:
    # - http_encoding is the encoding declared in the Content-Type HTTP header
    # - xml_encoding is the encoding declared in the <?xml declaration
    # - sniffed_encoding is the encoding sniffed from the first 4 bytes of the XML data
    # - result['encoding'] is the actual encoding, as per RFC 3023 and a variety of other conflicting specifications
    result['encoding'], http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type = \
        _getCharacterEncoding(http_headers, data)
    if http_headers and (not acceptable_content_type):
        if 'content-type' in http_headers:
            bozo_message = '%s is not an XML media type' % http_headers['content-type']
        else:
            bozo_message = 'no Content-type specified'
        result['bozo'] = 1
        result['bozo_exception'] = NonXMLContentType(bozo_message)

    # ensure that baseuri is an absolute uri using an acceptable URI scheme
    contentloc = http_headers.get('content-location', u'')
    href = result.get('href', u'')
    baseuri = _makeSafeAbsoluteURI(href, contentloc) or _makeSafeAbsoluteURI(contentloc) or href

    baselang = http_headers.get('content-language', None)
    if not isinstance(baselang, unicode) and baselang is not None:
        baselang = baselang.decode('utf-8', 'ignore')

    # if server sent 304, we're done
    if getattr(f, 'code', 0) == 304:
        result['version'] = u''
        result['debug_message'] = 'The feed has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    # if there was a problem downloading, we're done
    if data is None:
        return result

    # determine character encoding
    use_strict_parser = 0
    known_encoding = 0
    tried_encodings = []
    # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
    for proposed_encoding in (result['encoding'], xml_encoding, sniffed_xml_encoding):
        if not proposed_encoding:
            continue
        if proposed_encoding in tried_encodings:
            continue
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
        except (UnicodeDecodeError, LookupError):
            pass
        else:
            known_encoding = use_strict_parser = 1
            break
    # if no luck and we have auto-detection library, try that
    if (not known_encoding) and chardet:
        proposed_encoding = unicode(chardet.detect(data)['encoding'], 'ascii', 'ignore')
        if proposed_encoding and (proposed_encoding not in tried_encodings):
            tried_encodings.append(proposed_encoding)
            try:
                data = _toUTF8(data, proposed_encoding)
            except (UnicodeDecodeError, LookupError):
                pass
            else:
                known_encoding = use_strict_parser = 1
    # if still no luck and we haven't tried utf-8 yet, try that
    if (not known_encoding) and (u'utf-8' not in tried_encodings):
        proposed_encoding = u'utf-8'
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
        except UnicodeDecodeError:
            pass
        else:
            known_encoding = use_strict_parser = 1
    # if still no luck and we haven't tried windows-1252 yet, try that
    if (not known_encoding) and (u'windows-1252' not in tried_encodings):
        proposed_encoding = u'windows-1252'
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
        except UnicodeDecodeError:
            pass
        else:
            known_encoding = use_strict_parser = 1
    # if still no luck and we haven't tried iso-8859-2 yet, try that.
    if (not known_encoding) and (u'iso-8859-2' not in tried_encodings):
        proposed_encoding = u'iso-8859-2'
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
        except UnicodeDecodeError:
            pass
        else:
            known_encoding = use_strict_parser = 1
    # if still no luck, give up
    if not known_encoding:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingUnknown( \
            'document encoding unknown, I tried ' + \
            '%s, %s, utf-8, windows-1252, and iso-8859-2 but nothing worked' % \
            (result['encoding'], xml_encoding))
        result['encoding'] = u''
    elif proposed_encoding != result['encoding']:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingOverride( \
            'document declared as %s, but parsed as %s' % \
            (result['encoding'], proposed_encoding))
        result['encoding'] = proposed_encoding

    result['version'], data, entities = _stripDoctype(data)

    if not _XML_AVAILABLE:
        use_strict_parser = 0
    if use_strict_parser:
        # initialize the SAX parser
        feedparser = _StrictFeedParser(baseuri, baselang, 'utf-8')
        saxparser = xml.sax.make_parser(PREFERRED_XML_PARSERS)
        saxparser.setFeature(xml.sax.handler.feature_namespaces, 1)
        try:
            # disable downloading external doctype references, if possible
            saxparser.setFeature(xml.sax.handler.feature_external_ges, 0)
        except xml.sax.SAXNotSupportedException:
            pass
        saxparser.setContentHandler(feedparser)
        saxparser.setErrorHandler(feedparser)
        source = xml.sax.xmlreader.InputSource()
        source.setByteStream(_StringIO(data))
        try:
            saxparser.parse(source)
        except xml.sax.SAXParseException, e:
            result['bozo'] = 1
            result['bozo_exception'] = feedparser.exc or e
            use_strict_parser = 0
    if not use_strict_parser and _SGML_AVAILABLE:
        feedparser = _LooseFeedParser(baseuri, baselang, 'utf-8', entities)
        feedparser.feed(data.decode('utf-8', 'replace'))
    result['feed'] = feedparser.feeddata
    result['entries'] = feedparser.entries
    result['version'] = result['version'] or feedparser.version
    result['namespaces'] = feedparser.namespacesInUse
    return result

########NEW FILE########
__FILENAME__ = oauth
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '1.04'
__author__ = 'Liao Xuefeng (askxuefeng@gmail.com)'

'''
Python client SDK for sina weibo API using OAuth 2.
'''

try:
    import json
except ImportError:
    import simplejson as json
import time
import urllib
import urllib2
#import logging
#from ..snslog import SNSLog
#logger = SNSLog

def _obj_hook(pairs):
    '''
    convert json object to python object.
    '''
    o = JsonObject()
    for k, v in pairs.iteritems():
        o[str(k)] = v
    return o

class APIError(StandardError):
    '''
    raise APIError if got failed json message.
    '''
    def __init__(self, error_code, error, request):
        self.error_code = error_code
        self.error = error
        self.request = request
        StandardError.__init__(self, error)

    def __str__(self):
        return 'APIError: %s: %s, request: %s' % (self.error_code, self.error, self.request)

class JsonObject(dict):
    '''
    general json object that can bind any fields but also act as a dict.
    '''
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

def _encode_params(**kw):
    '''
    Encode parameters.
    '''
    args = []
    for k, v in kw.iteritems():
        qv = v.encode('utf-8') if isinstance(v, unicode) else str(v)
        args.append('%s=%s' % (k, urllib.quote(qv)))
    return '&'.join(args)

def _encode_multipart(**kw):
    '''
    Build a multipart/form-data body with generated random boundary.
    '''
    boundary = '----------%s' % hex(int(time.time() * 1000))
    data = []
    for k, v in kw.iteritems():
        data.append('--%s' % boundary)
        if hasattr(v, 'read'):
            # file-like object:
            ext = ''
            filename = getattr(v, 'name', '')
            n = filename.rfind('.')
            if n != (-1):
                ext = filename[n:].lower()
            content = v.read()
            data.append('Content-Disposition: form-data; name="%s"; filename="hidden"' % k)
            data.append('Content-Length: %d' % len(content))
            data.append('Content-Type: %s\r\n' % _guess_content_type(ext))
            data.append(content)
        else:
            data.append('Content-Disposition: form-data; name="%s"\r\n' % k)
            data.append(v.encode('utf-8') if isinstance(v, unicode) else v)
    data.append('--%s--\r\n' % boundary)
    return '\r\n'.join(data), boundary

_CONTENT_TYPES = { '.png': 'image/png', '.gif': 'image/gif', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.jpe': 'image/jpeg' }

def _guess_content_type(ext):
    return _CONTENT_TYPES.get(ext, 'application/octet-stream')

_HTTP_GET = 0
_HTTP_POST = 1
_HTTP_UPLOAD = 2

def _http_get(url, authorization=None, **kw):
    logger.debug('GET %s' % url)
    return _http_call(url, _HTTP_GET, authorization, **kw)

def _http_post(url, authorization=None, **kw):
    logger.debug('POST %s' % url)
    return _http_call(url, _HTTP_POST, authorization, **kw)

def _http_upload(url, authorization=None, **kw):
    logger.debug('MULTIPART POST %s' % url)
    return _http_call(url, _HTTP_UPLOAD, authorization, **kw)

def _http_call(url, method, authorization, **kw):
    '''
    send an http request and expect to return a json object if no error.
    '''
    params = None
    boundary = None
    if method==_HTTP_UPLOAD:
        params, boundary = _encode_multipart(**kw)
    else:
        params = _encode_params(**kw)
    http_url = '%s?%s' % (url, params) if method==_HTTP_GET else url
    http_body = None if method==_HTTP_GET else params
    req = urllib2.Request(http_url, data=http_body)
    if authorization:
        req.add_header('Authorization', 'OAuth2 %s' % authorization)
    if boundary:
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s' % boundary)
    resp = urllib2.urlopen(req)
    body = resp.read()

    try:
        r = json.loads(body, object_hook=_obj_hook)
        if hasattr(r, 'error_code'):
            raise APIError(r.error_code, getattr(r, 'error', ''), getattr(r, 'request', ''))
        return r
    except ValueError:
        #qq weibo's auth response type is string, not like sina whose is json
        return body


class HttpObject(object):

    def __init__(self, client, method):
        self.client = client
        self.method = method

    def __getattr__(self, attr):
        def wrap(**kw):
            if self.client.is_expires():
                raise APIError('21327', 'expired_token', attr)
            return _http_call('%s%s.json' % (self.client.api_url, attr.replace('__', '/')), self.method, self.client.access_token, **kw)
        return wrap

class APIClient(object):
    '''
    API client using synchronized invocation.
    '''
    def __init__(self, app_key, app_secret, redirect_uri=None, response_type='code', auth_url="https://api.weibo.com/oauth2/", api_url="https://api.weibo.com/2/"):
        self.client_id = app_key
        self.client_secret = app_secret
        self.redirect_uri = redirect_uri
        self.response_type = response_type
        self.auth_url = auth_url
        self.api_url = api_url
        self.access_token = None
        self.expires = 0.0
        self.get = HttpObject(self, _HTTP_GET)
        self.post = HttpObject(self, _HTTP_POST)
        self.upload = HttpObject(self, _HTTP_UPLOAD)

    def set_access_token(self, access_token, expires_in):
        self.access_token = str(access_token)
        self.expires = float(expires_in)

    def get_authorize_url(self, redirect_uri=None, display='json'):
        '''
        return the authroize url that should be redirect.
        '''
        redirect = redirect_uri if redirect_uri else self.redirect_uri
        if not redirect:
            raise APIError('21305', 'Parameter absent: redirect_uri', 'OAuth2 request')
        return '%s%s?%s' % (self.auth_url, 'authorize', \
                _encode_params(client_id = self.client_id, \
                        response_type = 'code', \
                        display = display, \
                        redirect_uri = redirect))

    def request_access_token(self, code, redirect_uri=None):
        '''
        return access token as object: {"access_token":"your-access-token","expires_in":12345678}, expires_in is standard unix-epoch-time
        '''
        redirect = redirect_uri if redirect_uri else self.redirect_uri
        if not redirect:
            raise APIError('21305', 'Parameter absent: redirect_uri', 'OAuth2 request')
        r = _http_post('%s%s' % (self.auth_url, 'access_token'), \
                client_id = self.client_id, \
                client_secret = self.client_secret, \
                redirect_uri = redirect, \
                code = code, grant_type = 'authorization_code')
        r = self._parse_authinfo(r)
        r.expires_in += int(time.time())
        return r

    def is_expires(self):
        return not self.access_token or time.time() > self.expires

    def __getattr__(self, attr):
        return getattr(self.get, attr)

    def _parse_authinfo(self, info):
        '''
        if the auth info is a string, parse it and return as a JsonObject
        '''
        if type(info) == str:
            d = dict()
            parts = info.split("&")
            for part in parts:
                sub = part.split("=")
                key = sub[0]
                val = sub[1]
                try:
                    val = int(val)
                except ValueError:
                    pass
                d[key] = val

            r = _obj_hook(d)
            return r
        return info


########NEW FILE########
__FILENAME__ = imap
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import imaplib


class IMAP4_SSL(imaplib.IMAP4_SSL):
    """IMAP wrapper for imaplib.IMAP4_SSL that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        imaplib.IMAP4_SSL.authenticate(self, 'XOAUTH',
            lambda x: oauth2.build_xoauth_string(url, consumer, token))

########NEW FILE########
__FILENAME__ = smtp
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import smtplib
import base64


class SMTP(smtplib.SMTP):
    """SMTP wrapper for smtplib.SMTP that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        self.docmd('AUTH', 'XOAUTH %s' % \
            base64.b64encode(oauth2.build_xoauth_string(url, consumer, token)))

########NEW FILE########
__FILENAME__ = _version
# This is the version of this source code.

manual_verstr = "1.5"



auto_build_num = "211"



verstr = manual_verstr + "." + auto_build_num
try:
    from pyutil.version_class import Version as pyutil_Version
    __version__ = pyutil_Version(verstr)
except (ImportError, ValueError):
    # Maybe there is no pyutil installed.
    from distutils.version import LooseVersion as distutils_Version
    __version__ = distutils_Version(verstr)

########NEW FILE########
__FILENAME__ = pyDes
#############################################################################
# 				Documentation				    #
#############################################################################

# Author:   Todd Whiteman
# Date:     16th March, 2009
# Verion:   2.0.0
# License:  Public Domain - free to do as you wish
# Homepage: http://twhiteman.netfirms.com/des.html
#
# This is a pure python implementation of the DES encryption algorithm.
# It's pure python to avoid portability issues, since most DES
# implementations are programmed in C (for performance reasons).
#
# Triple DES class is also implemented, utilising the DES base. Triple DES
# is either DES-EDE3 with a 24 byte key, or DES-EDE2 with a 16 byte key.
#
# See the README.txt that should come with this python module for the
# implementation methods used.
#
# Thanks to:
#  * David Broadwell for ideas, comments and suggestions.
#  * Mario Wolff for pointing out and debugging some triple des CBC errors.
#  * Santiago Palladino for providing the PKCS5 padding technique.
#  * Shaya for correcting the PAD_PKCS5 triple des CBC errors.
#
"""A pure python implementation of the DES and TRIPLE DES encryption algorithms.

Class initialization
--------------------
pyDes.des(key, [mode], [IV], [pad], [padmode])
pyDes.triple_des(key, [mode], [IV], [pad], [padmode])

key     -> Bytes containing the encryption key. 8 bytes for DES, 16 or 24 bytes
	   for Triple DES
mode    -> Optional argument for encryption type, can be either
	   pyDes.ECB (Electronic Code Book) or pyDes.CBC (Cypher Block Chaining)
IV      -> Optional Initial Value bytes, must be supplied if using CBC mode.
	   Length must be 8 bytes.
pad     -> Optional argument, set the pad character (PAD_NORMAL) to use during
	   all encrypt/decrpt operations done with this instance.
padmode -> Optional argument, set the padding mode (PAD_NORMAL or PAD_PKCS5)
	   to use during all encrypt/decrpt operations done with this instance.

I recommend to use PAD_PKCS5 padding, as then you never need to worry about any
padding issues, as the padding can be removed unambiguously upon decrypting
data that was encrypted using PAD_PKCS5 padmode.

Common methods
--------------
encrypt(data, [pad], [padmode])
decrypt(data, [pad], [padmode])

data    -> Bytes to be encrypted/decrypted
pad     -> Optional argument. Only when using padmode of PAD_NORMAL. For
	   encryption, adds this characters to the end of the data block when
	   data is not a multiple of 8 bytes. For decryption, will remove the
	   trailing characters that match this pad character from the last 8
	   bytes of the unencrypted data block.
padmode -> Optional argument, set the padding mode, must be one of PAD_NORMAL
	   or PAD_PKCS5). Defaults to PAD_NORMAL.
	

Example
-------
from pyDes import *

data = "Please encrypt my data"
k = des("DESCRYPT", CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
# For Python3, you'll need to use bytes, i.e.:
#   data = b"Please encrypt my data"
#   k = des(b"DESCRYPT", CBC, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
d = k.encrypt(data)
print "Encrypted: %r" % d
print "Decrypted: %r" % k.decrypt(d)
assert k.decrypt(d, padmode=PAD_PKCS5) == data


See the module source (pyDes.py) for more examples of use.
You can also run the pyDes.py file without and arguments to see a simple test.

Note: This code was not written for high-end systems needing a fast
      implementation, but rather a handy portable solution with small usage.

"""

import sys

# _pythonMajorVersion is used to handle Python2 and Python3 differences.
_pythonMajorVersion = sys.version_info[0]

# Modes of crypting / cyphering
ECB =	0
CBC =	1

# Modes of padding
PAD_NORMAL = 1
PAD_PKCS5 = 2

# PAD_PKCS5: is a method that will unambiguously remove all padding
#            characters after decryption, when originally encrypted with
#            this padding mode.
# For a good description of the PKCS5 padding technique, see:
# http://www.faqs.org/rfcs/rfc1423.html

# The base class shared by des and triple des.
class _baseDes(object):
	def __init__(self, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		if IV:
			IV = self._guardAgainstUnicode(IV)
		if pad:
			pad = self._guardAgainstUnicode(pad)
		self.block_size = 8
		# Sanity checking of arguments.
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")
		if IV and len(IV) != self.block_size:
			raise ValueError("Invalid Initial Value (IV), must be a multiple of " + str(self.block_size) + " bytes")

		# Set the passed in variables
		self._mode = mode
		self._iv = IV
		self._padding = pad
		self._padmode = padmode

	def getKey(self):
		"""getKey() -> bytes"""
		return self.__key

	def setKey(self, key):
		"""Will set the crypting key for this object."""
		key = self._guardAgainstUnicode(key)
		self.__key = key

	def getMode(self):
		"""getMode() -> pyDes.ECB or pyDes.CBC"""
		return self._mode

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		self._mode = mode

	def getPadding(self):
		"""getPadding() -> bytes of length 1. Padding character."""
		return self._padding

	def setPadding(self, pad):
		"""setPadding() -> bytes of length 1. Padding character."""
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		self._padding = pad

	def getPadMode(self):
		"""getPadMode() -> pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		return self._padmode
		
	def setPadMode(self, mode):
		"""Sets the type of padding mode, pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		self._padmode = mode

	def getIV(self):
		"""getIV() -> bytes"""
		return self._iv

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		if not IV or len(IV) != self.block_size:
			raise ValueError("Invalid Initial Value (IV), must be a multiple of " + str(self.block_size) + " bytes")
		IV = self._guardAgainstUnicode(IV)
		self._iv = IV

	def _padData(self, data, pad, padmode):
		# Pad data depending on the mode
		if padmode is None:
			# Get the default padding mode.
			padmode = self.getPadMode()
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")

		if padmode == PAD_NORMAL:
			if len(data) % self.block_size == 0:
				# No padding required.
				return data

			if not pad:
				# Get the default padding.
				pad = self.getPadding()
			if not pad:
				raise ValueError("Data must be a multiple of " + str(self.block_size) + " bytes in length. Use padmode=PAD_PKCS5 or set the pad character.")
			data += (self.block_size - (len(data) % self.block_size)) * pad
		
		elif padmode == PAD_PKCS5:
			pad_len = 8 - (len(data) % self.block_size)
			if _pythonMajorVersion < 3:
				data += pad_len * chr(pad_len)
			else:
				data += bytes([pad_len] * pad_len)

		return data

	def _unpadData(self, data, pad, padmode):
		# Unpad data depending on the mode.
		if not data:
			return data
		if pad and padmode == PAD_PKCS5:
			raise ValueError("Cannot use a pad character with PAD_PKCS5")
		if padmode is None:
			# Get the default padding mode.
			padmode = self.getPadMode()

		if padmode == PAD_NORMAL:
			if not pad:
				# Get the default padding.
				pad = self.getPadding()
			if pad:
				data = data[:-self.block_size] + \
				       data[-self.block_size:].rstrip(pad)

		elif padmode == PAD_PKCS5:
			if _pythonMajorVersion < 3:
				pad_len = ord(data[-1])
			else:
				pad_len = data[-1]
			data = data[:-pad_len]

		return data

	def _guardAgainstUnicode(self, data):
		# Only accept byte strings or ascii unicode values, otherwise
		# there is no way to correctly decode the data into bytes.
		if _pythonMajorVersion < 3:
			if isinstance(data, unicode):
				raise ValueError("pyDes can only work with bytes, not Unicode strings.")
		else:
			if isinstance(data, str):
				# Only accept ascii unicode values.
				try:
					return data.encode('ascii')
				except UnicodeEncodeError:
					pass
				raise ValueError("pyDes can only work with encoded strings, not Unicode.")
		return data

#############################################################################
# 				    DES					    #
#############################################################################
class des(_baseDes):
	"""DES encryption/decrytpion class

	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key,[mode], [IV])

	key  -> Bytes containing the encryption key, must be exactly 8 bytes
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional Initial Value bytes, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	pad  -> Optional argument, set the pad character (PAD_NORMAL) to use
		during all encrypt/decrpt operations done with this instance.
	padmode -> Optional argument, set the padding mode (PAD_NORMAL or
		PAD_PKCS5) to use during all encrypt/decrpt operations done
		with this instance.
	"""


	# Permutation and translation tables for DES
	__pc1 = [56, 48, 40, 32, 24, 16,  8,
		  0, 57, 49, 41, 33, 25, 17,
		  9,  1, 58, 50, 42, 34, 26,
		 18, 10,  2, 59, 51, 43, 35,
		 62, 54, 46, 38, 30, 22, 14,
		  6, 61, 53, 45, 37, 29, 21,
		 13,  5, 60, 52, 44, 36, 28,
		 20, 12,  4, 27, 19, 11,  3
	]

	# number left rotations of pc1
	__left_rotations = [
		1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1
	]

	# permuted choice key (table 2)
	__pc2 = [
		13, 16, 10, 23,  0,  4,
		 2, 27, 14,  5, 20,  9,
		22, 18, 11,  3, 25,  7,
		15,  6, 26, 19, 12,  1,
		40, 51, 30, 36, 46, 54,
		29, 39, 50, 44, 32, 47,
		43, 48, 38, 55, 33, 52,
		45, 41, 49, 35, 28, 31
	]

	# initial permutation IP
	__ip = [57, 49, 41, 33, 25, 17, 9,  1,
		59, 51, 43, 35, 27, 19, 11, 3,
		61, 53, 45, 37, 29, 21, 13, 5,
		63, 55, 47, 39, 31, 23, 15, 7,
		56, 48, 40, 32, 24, 16, 8,  0,
		58, 50, 42, 34, 26, 18, 10, 2,
		60, 52, 44, 36, 28, 20, 12, 4,
		62, 54, 46, 38, 30, 22, 14, 6
	]

	# Expansion table for turning 32 bit blocks into 48 bits
	__expansion_table = [
		31,  0,  1,  2,  3,  4,
		 3,  4,  5,  6,  7,  8,
		 7,  8,  9, 10, 11, 12,
		11, 12, 13, 14, 15, 16,
		15, 16, 17, 18, 19, 20,
		19, 20, 21, 22, 23, 24,
		23, 24, 25, 26, 27, 28,
		27, 28, 29, 30, 31,  0
	]

	# The (in)famous S-boxes
	__sbox = [
		# S1
		[14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
		 0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
		 4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
		 15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],

		# S2
		[15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
		 3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
		 0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
		 13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],

		# S3
		[10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
		 13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
		 13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
		 1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],

		# S4
		[7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
		 13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
		 10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
		 3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],

		# S5
		[2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
		 14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
		 4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
		 11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],

		# S6
		[12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
		 10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
		 9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
		 4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],

		# S7
		[4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
		 13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
		 1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
		 6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],

		# S8
		[13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
		 1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
		 7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
		 2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
	]


	# 32-bit permutation function P used on the output of the S-boxes
	__p = [
		15, 6, 19, 20, 28, 11,
		27, 16, 0, 14, 22, 25,
		4, 17, 30, 9, 1, 7,
		23,13, 31, 26, 2, 8,
		18, 12, 29, 5, 21, 10,
		3, 24
	]

	# final permutation IP^-1
	__fp = [
		39,  7, 47, 15, 55, 23, 63, 31,
		38,  6, 46, 14, 54, 22, 62, 30,
		37,  5, 45, 13, 53, 21, 61, 29,
		36,  4, 44, 12, 52, 20, 60, 28,
		35,  3, 43, 11, 51, 19, 59, 27,
		34,  2, 42, 10, 50, 18, 58, 26,
		33,  1, 41,  9, 49, 17, 57, 25,
		32,  0, 40,  8, 48, 16, 56, 24
	]

	# Type of crypting being done
	ENCRYPT =	0x00
	DECRYPT =	0x01

	# Initialisation
	def __init__(self, key, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		# Sanity checking of arguments.
		if len(key) != 8:
			raise ValueError("Invalid DES key size. Key must be exactly 8 bytes long.")
		_baseDes.__init__(self, mode, IV, pad, padmode)
		self.key_size = 8

		self.L = []
		self.R = []
		self.Kn = [ [0] * 48 ] * 16	# 16 48-bit keys (K1 - K16)
		self.final = []

		self.setKey(key)

	def setKey(self, key):
		"""Will set the crypting key for this object. Must be 8 bytes."""
		_baseDes.setKey(self, key)
		self.__create_sub_keys()

	def __String_to_BitList(self, data):
		"""Turn the string data, into a list of bits (1, 0)'s"""
		if _pythonMajorVersion < 3:
			# Turn the strings into integers. Python 3 uses a bytes
			# class, which already has this behaviour.
			data = [ord(c) for c in data]
		l = len(data) * 8
		result = [0] * l
		pos = 0
		for ch in data:
			i = 7
			while i >= 0:
				if ch & (1 << i) != 0:
					result[pos] = 1
				else:
					result[pos] = 0
				pos += 1
				i -= 1

		return result

	def __BitList_to_String(self, data):
		"""Turn the list of bits -> data, into a string"""
		result = []
		pos = 0
		c = 0
		while pos < len(data):
			c += data[pos] << (7 - (pos % 8))
			if (pos % 8) == 7:
				result.append(c)
				c = 0
			pos += 1

		if _pythonMajorVersion < 3:
			return ''.join([ chr(c) for c in result ])
		else:
			return bytes(result)

	def __permutate(self, table, block):
		"""Permutate this block with the specified table"""
		return list(map(lambda x: block[x], table))
	
	# Transform the secret key, so that it is ready for data processing
	# Create the 16 subkeys, K[1] - K[16]
	def __create_sub_keys(self):
		"""Create the 16 subkeys K[1] to K[16] from the given key"""
		key = self.__permutate(des.__pc1, self.__String_to_BitList(self.getKey()))
		i = 0
		# Split into Left and Right sections
		self.L = key[:28]
		self.R = key[28:]
		while i < 16:
			j = 0
			# Perform circular left shifts
			while j < des.__left_rotations[i]:
				self.L.append(self.L[0])
				del self.L[0]

				self.R.append(self.R[0])
				del self.R[0]

				j += 1

			# Create one of the 16 subkeys through pc2 permutation
			self.Kn[i] = self.__permutate(des.__pc2, self.L + self.R)

			i += 1

	# Main part of the encryption algorithm, the number cruncher :)
	def __des_crypt(self, block, crypt_type):
		"""Crypt the block of data through DES bit-manipulation"""
		block = self.__permutate(des.__ip, block)
		self.L = block[:32]
		self.R = block[32:]

		# Encryption starts from Kn[1] through to Kn[16]
		if crypt_type == des.ENCRYPT:
			iteration = 0
			iteration_adjustment = 1
		# Decryption starts from Kn[16] down to Kn[1]
		else:
			iteration = 15
			iteration_adjustment = -1

		i = 0
		while i < 16:
			# Make a copy of R[i-1], this will later become L[i]
			tempR = self.R[:]

			# Permutate R[i - 1] to start creating R[i]
			self.R = self.__permutate(des.__expansion_table, self.R)

			# Exclusive or R[i - 1] with K[i], create B[1] to B[8] whilst here
			self.R = list(map(lambda x, y: x ^ y, self.R, self.Kn[iteration]))
			B = [self.R[:6], self.R[6:12], self.R[12:18], self.R[18:24], self.R[24:30], self.R[30:36], self.R[36:42], self.R[42:]]
			# Optimization: Replaced below commented code with above
			#j = 0
			#B = []
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.Kn[iteration][j]
			#	j += 1
			#	if j % 6 == 0:
			#		B.append(self.R[j-6:j])

			# Permutate B[1] to B[8] using the S-Boxes
			j = 0
			Bn = [0] * 32
			pos = 0
			while j < 8:
				# Work out the offsets
				m = (B[j][0] << 1) + B[j][5]
				n = (B[j][1] << 3) + (B[j][2] << 2) + (B[j][3] << 1) + B[j][4]

				# Find the permutation value
				v = des.__sbox[j][(m << 4) + n]

				# Turn value into bits, add it to result: Bn
				Bn[pos] = (v & 8) >> 3
				Bn[pos + 1] = (v & 4) >> 2
				Bn[pos + 2] = (v & 2) >> 1
				Bn[pos + 3] = v & 1

				pos += 4
				j += 1

			# Permutate the concatination of B[1] to B[8] (Bn)
			self.R = self.__permutate(des.__p, Bn)

			# Xor with L[i - 1]
			self.R = list(map(lambda x, y: x ^ y, self.R, self.L))
			# Optimization: This now replaces the below commented code
			#j = 0
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.L[j]
			#	j += 1

			# L[i] becomes R[i - 1]
			self.L = tempR

			i += 1
			iteration += iteration_adjustment
		
		# Final permutation of R[16]L[16]
		self.final = self.__permutate(des.__fp, self.R + self.L)
		return self.final


	# Data to be encrypted/decrypted
	def crypt(self, data, crypt_type):
		"""Crypt the data in blocks, running it through des_crypt()"""

		# Error check the data
		if not data:
			return ''
		if len(data) % self.block_size != 0:
			if crypt_type == des.DECRYPT: # Decryption must work on 8 byte blocks
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n.")
			if not self.getPadding():
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n. Try setting the optional padding character")
			else:
				data += (self.block_size - (len(data) % self.block_size)) * self.getPadding()
			# print "Len of data: %f" % (len(data) / self.block_size)

		if self.getMode() == CBC:
			if self.getIV():
				iv = self.__String_to_BitList(self.getIV())
			else:
				raise ValueError("For CBC mode, you must supply the Initial Value (IV) for ciphering")

		# Split the data into blocks, crypting each one seperately
		i = 0
		dict = {}
		result = []
		#cached = 0
		#lines = 0
		while i < len(data):
			# Test code for caching encryption results
			#lines += 1
			#if dict.has_key(data[i:i+8]):
				#print "Cached result for: %s" % data[i:i+8]
			#	cached += 1
			#	result.append(dict[data[i:i+8]])
			#	i += 8
			#	continue
				
			block = self.__String_to_BitList(data[i:i+8])

			# Xor with IV if using CBC mode
			if self.getMode() == CBC:
				if crypt_type == des.ENCRYPT:
					block = list(map(lambda x, y: x ^ y, block, iv))
					#j = 0
					#while j < len(block):
					#	block[j] = block[j] ^ iv[j]
					#	j += 1

				processed_block = self.__des_crypt(block, crypt_type)

				if crypt_type == des.DECRYPT:
					processed_block = list(map(lambda x, y: x ^ y, processed_block, iv))
					#j = 0
					#while j < len(processed_block):
					#	processed_block[j] = processed_block[j] ^ iv[j]
					#	j += 1
					iv = block
				else:
					iv = processed_block
			else:
				processed_block = self.__des_crypt(block, crypt_type)


			# Add the resulting crypted block to our list
			#d = self.__BitList_to_String(processed_block)
			#result.append(d)
			result.append(self.__BitList_to_String(processed_block))
			#dict[data[i:i+8]] = d
			i += 8

		# print "Lines: %d, cached: %d" % (lines, cached)

		# Return the full crypted string
		if _pythonMajorVersion < 3:
			return ''.join(result)
		else:
			return bytes.fromhex('').join(result)

	def encrypt(self, data, pad=None, padmode=None):
		"""encrypt(data, [pad], [padmode]) -> bytes

		data : Bytes to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, or
		the padmode is set to PAD_PKCS5, as bytes will then added to
		ensure the be padded data is a multiple of 8 bytes.
		"""
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		data = self._padData(data, pad, padmode)
		return self.crypt(data, des.ENCRYPT)

	def decrypt(self, data, pad=None, padmode=None):
		"""decrypt(data, [pad], [padmode]) -> bytes

		data : Bytes to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. In PAD_NORMAL mode, if the
		optional padding character is supplied, then the un-encrypted
		data will have the padding characters removed from the end of
		the bytes. This pad removal only occurs on the last 8 bytes of
		the data (last data block). In PAD_PKCS5 mode, the special
		padding end markers will be removed from the data after decrypting.
		"""
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		data = self.crypt(data, des.DECRYPT)
		return self._unpadData(data, pad, padmode)



#############################################################################
# 				Triple DES				    #
#############################################################################
class triple_des(_baseDes):
	"""Triple DES encryption/decrytpion class

	This algorithm uses the DES-EDE3 (when a 24 byte key is supplied) or
	the DES-EDE2 (when a 16 byte key is supplied) encryption methods.
	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key, [mode], [IV])

	key  -> Bytes containing the encryption key, must be either 16 or
	        24 bytes long
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional Initial Value bytes, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	pad  -> Optional argument, set the pad character (PAD_NORMAL) to use
		during all encrypt/decrpt operations done with this instance.
	padmode -> Optional argument, set the padding mode (PAD_NORMAL or
		PAD_PKCS5) to use during all encrypt/decrpt operations done
		with this instance.
	"""
	def __init__(self, key, mode=ECB, IV=None, pad=None, padmode=PAD_NORMAL):
		_baseDes.__init__(self, mode, IV, pad, padmode)
		self.setKey(key)

	def setKey(self, key):
		"""Will set the crypting key for this object. Either 16 or 24 bytes long."""
		self.key_size = 24  # Use DES-EDE3 mode
		if len(key) != self.key_size:
			if len(key) == 16: # Use DES-EDE2 mode
				self.key_size = 16
			else:
				raise ValueError("Invalid triple DES key size. Key must be either 16 or 24 bytes long")
		if self.getMode() == CBC:
			if not self.getIV():
				# Use the first 8 bytes of the key
				self._iv = key[:self.block_size]
			if len(self.getIV()) != self.block_size:
				raise ValueError("Invalid IV, must be 8 bytes in length")
		self.__key1 = des(key[:8], self._mode, self._iv,
				  self._padding, self._padmode)
		self.__key2 = des(key[8:16], self._mode, self._iv,
				  self._padding, self._padmode)
		if self.key_size == 16:
			self.__key3 = self.__key1
		else:
			self.__key3 = des(key[16:], self._mode, self._iv,
					  self._padding, self._padmode)
		_baseDes.setKey(self, key)

	# Override setter methods to work on all 3 keys.

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		_baseDes.setMode(self, mode)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setMode(mode)

	def setPadding(self, pad):
		"""setPadding() -> bytes of length 1. Padding character."""
		_baseDes.setPadding(self, pad)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setPadding(pad)

	def setPadMode(self, mode):
		"""Sets the type of padding mode, pyDes.PAD_NORMAL or pyDes.PAD_PKCS5"""
		_baseDes.setPadMode(self, mode)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setPadMode(mode)

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		_baseDes.setIV(self, IV)
		for key in (self.__key1, self.__key2, self.__key3):
			key.setIV(IV)

	def encrypt(self, data, pad=None, padmode=None):
		"""encrypt(data, [pad], [padmode]) -> bytes

		data : bytes to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, or
		the padmode is set to PAD_PKCS5, as bytes will then added to
		ensure the be padded data is a multiple of 8 bytes.
		"""
		ENCRYPT = des.ENCRYPT
		DECRYPT = des.DECRYPT
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		# Pad the data accordingly.
		data = self._padData(data, pad, padmode)
		if self.getMode() == CBC:
			self.__key1.setIV(self.getIV())
			self.__key2.setIV(self.getIV())
			self.__key3.setIV(self.getIV())
			i = 0
			result = []
			while i < len(data):
				block = self.__key1.crypt(data[i:i+8], ENCRYPT)
				block = self.__key2.crypt(block, DECRYPT)
				block = self.__key3.crypt(block, ENCRYPT)
				self.__key1.setIV(block)
				self.__key2.setIV(block)
				self.__key3.setIV(block)
				result.append(block)
				i += 8
			if _pythonMajorVersion < 3:
				return ''.join(result)
			else:
				return bytes.fromhex('').join(result)
		else:
			data = self.__key1.crypt(data, ENCRYPT)
			data = self.__key2.crypt(data, DECRYPT)
			return self.__key3.crypt(data, ENCRYPT)

	def decrypt(self, data, pad=None, padmode=None):
		"""decrypt(data, [pad], [padmode]) -> bytes

		data : bytes to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte
		padmode : Optional argument for overriding the padding mode.

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. In PAD_NORMAL mode, if the
		optional padding character is supplied, then the un-encrypted
		data will have the padding characters removed from the end of
		the bytes. This pad removal only occurs on the last 8 bytes of
		the data (last data block). In PAD_PKCS5 mode, the special
		padding end markers will be removed from the data after
		decrypting, no pad character is required for PAD_PKCS5.
		"""
		ENCRYPT = des.ENCRYPT
		DECRYPT = des.DECRYPT
		data = self._guardAgainstUnicode(data)
		if pad is not None:
			pad = self._guardAgainstUnicode(pad)
		if self.getMode() == CBC:
			self.__key1.setIV(self.getIV())
			self.__key2.setIV(self.getIV())
			self.__key3.setIV(self.getIV())
			i = 0
			result = []
			while i < len(data):
				iv = data[i:i+8]
				block = self.__key3.crypt(iv,    DECRYPT)
				block = self.__key2.crypt(block, ENCRYPT)
				block = self.__key1.crypt(block, DECRYPT)
				self.__key1.setIV(iv)
				self.__key2.setIV(iv)
				self.__key3.setIV(iv)
				result.append(block)
				i += 8
			if _pythonMajorVersion < 3:
				data = ''.join(result)
			else:
				data = bytes.fromhex('').join(result)
		else:
			data = self.__key3.crypt(data, DECRYPT)
			data = self.__key2.crypt(data, ENCRYPT)
			data = self.__key1.crypt(data, DECRYPT)
		return self._unpadData(data, pad, padmode)

########NEW FILE########
__FILENAME__ = PyRSS2Gen
"""PyRSS2Gen - A Python library for generating RSS 2.0 feeds."""

__name__ = "PyRSS2Gen"
__version__ = (1, 0, 0)
__author__ = "Andrew Dalke <dalke@dalkescientific.com>"

_generator_name = __name__ + "-" + ".".join(map(str, __version__))

import datetime

# Could make this the base class; will need to add 'publish'
class WriteXmlMixin:
    def write_xml(self, outfile, encoding = "iso-8859-1"):
        from xml.sax import saxutils
        handler = saxutils.XMLGenerator(outfile, encoding)
        handler.startDocument()
        self.publish(handler)
        handler.endDocument()

    def to_xml(self, encoding = "iso-8859-1"):
        try:
            import cStringIO as StringIO
        except ImportError:
            import StringIO
        f = StringIO.StringIO()
        self.write_xml(f, encoding)
        return f.getvalue()


def _element(handler, name, obj, d = {}):
    if isinstance(obj, basestring) or obj is None:
        # special-case handling to make the API easier
        # to use for the common case.
        handler.startElement(name, d)
        if obj is not None:
            handler.characters(obj)
        handler.endElement(name)
    else:
        # It better know how to emit the correct XML.
        obj.publish(handler)

def _opt_element(handler, name, obj):
    if obj is None:
        return
    _element(handler, name, obj)


def _format_date(dt):
    """convert a datetime into an RFC 822 formatted date

    Input date must be in GMT.
    """
    # Looks like:
    #   Sat, 07 Sep 2002 00:00:01 GMT
    # Can't use strftime because that's locale dependent
    #
    # Isn't there a standard way to do this for Python?  The
    # rfc822 and email.Utils modules assume a timestamp.  The
    # following is based on the rfc822 module.
    #hupili:20120810 fix
    #If datetime has tzname() returned, format the timezone info.
    #Not all datetime object is in GMT.
    #return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
    return "%s, %02d %s %04d %02d:%02d:%02d %s" % (
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
            dt.day,
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month-1],
            #dt.year, dt.hour, dt.minute, dt.second)
            dt.year, dt.hour, dt.minute, dt.second, dt.tzname())


##
# A couple simple wrapper objects for the fields which
# take a simple value other than a string.
class IntElement:
    """implements the 'publish' API for integers

    Takes the tag name and the integer value to publish.

    (Could be used for anything which uses str() to be published
    to text for XML.)
    """
    element_attrs = {}
    def __init__(self, name, val):
        self.name = name
        self.val = val
    def publish(self, handler):
        handler.startElement(self.name, self.element_attrs)
        handler.characters(str(self.val))
        handler.endElement(self.name)

class DateElement:
    """implements the 'publish' API for a datetime.datetime

    Takes the tag name and the datetime to publish.

    Converts the datetime to RFC 2822 timestamp (4-digit year).
    """
    def __init__(self, name, dt):
        self.name = name
        self.dt = dt
    def publish(self, handler):
        _element(handler, self.name, _format_date(self.dt))
####

class Category:
    """Publish a category element"""
    def __init__(self, category, domain = None):
        self.category = category
        self.domain = domain
    def publish(self, handler):
        d = {}
        if self.domain is not None:
            d["domain"] = self.domain
        _element(handler, "category", self.category, d)

class Cloud:
    """Publish a cloud"""
    def __init__(self, domain, port, path,
                 registerProcedure, protocol):
        self.domain = domain
        self.port = port
        self.path = path
        self.registerProcedure = registerProcedure
        self.protocol = protocol
    def publish(self, handler):
        _element(handler, "cloud", None, {
            "domain": self.domain,
            "port": str(self.port),
            "path": self.path,
            "registerProcedure": self.registerProcedure,
            "protocol": self.protocol})

class Image:
    """Publish a channel Image"""
    element_attrs = {}
    def __init__(self, url, title, link,
                 width = None, height = None, description = None):
        self.url = url
        self.title = title
        self.link = link
        self.width = width
        self.height = height
        self.description = description

    def publish(self, handler):
        handler.startElement("image", self.element_attrs)

        _element(handler, "url", self.url)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)

        width = self.width
        if isinstance(width, int):
            width = IntElement("width", width)
        _opt_element(handler, "width", width)

        height = self.height
        if isinstance(height, int):
            height = IntElement("height", height)
        _opt_element(handler, "height", height)

        _opt_element(handler, "description", self.description)

        handler.endElement("image")

class Guid:
    """Publish a guid

    Defaults to being a permalink, which is the assumption if it's
    omitted.  Hence strings are always permalinks.
    """
    def __init__(self, guid, isPermaLink = 1):
        self.guid = guid
        self.isPermaLink = isPermaLink
    def publish(self, handler):
        d = {}
        if self.isPermaLink:
            d["isPermaLink"] = "true"
        else:
            d["isPermaLink"] = "false"
        _element(handler, "guid", self.guid, d)

class TextInput:
    """Publish a textInput

    Apparently this is rarely used.
    """
    element_attrs = {}
    def __init__(self, title, description, name, link):
        self.title = title
        self.description = description
        self.name = name
        self.link = link

    def publish(self, handler):
        handler.startElement("textInput", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "description", self.description)
        _element(handler, "name", self.name)
        _element(handler, "link", self.link)
        handler.endElement("textInput")


class Enclosure:
    """Publish an enclosure"""
    def __init__(self, url, length, type):
        self.url = url
        self.length = length
        self.type = type
    def publish(self, handler):
        _element(handler, "enclosure", None,
                 {"url": self.url,
                  "length": str(self.length),
                  "type": self.type,
                  })

class Source:
    """Publish the item's original source, used by aggregators"""
    def __init__(self, name, url):
        self.name = name
        self.url = url
    def publish(self, handler):
        _element(handler, "source", self.name, {"url": self.url})

class SkipHours:
    """Publish the skipHours

    This takes a list of hours, as integers.
    """
    element_attrs = {}
    def __init__(self, hours):
        self.hours = hours
    def publish(self, handler):
        if self.hours:
            handler.startElement("skipHours", self.element_attrs)
            for hour in self.hours:
                _element(handler, "hour", str(hour))
            handler.endElement("skipHours")

class SkipDays:
    """Publish the skipDays

    This takes a list of days as strings.
    """
    element_attrs = {}
    def __init__(self, days):
        self.days = days
    def publish(self, handler):
        if self.days:
            handler.startElement("skipDays", self.element_attrs)
            for day in self.days:
                _element(handler, "day", day)
            handler.endElement("skipDays")

class RSS2(WriteXmlMixin):
    """The main RSS class.

    Stores the channel attributes, with the "category" elements under
    ".categories" and the RSS items under ".items".
    """

    rss_attrs = {"version": "2.0"}
    element_attrs = {}
    def __init__(self,
                 title,
                 link,
                 description,

                 language = None,
                 copyright = None,
                 managingEditor = None,
                 webMaster = None,
                 pubDate = None,  # a datetime, *in* *GMT*
                 lastBuildDate = None, # a datetime

                 categories = None, # list of strings or Category
                 generator = _generator_name,
                 docs = "http://blogs.law.harvard.edu/tech/rss",
                 cloud = None,    # a Cloud
                 ttl = None,      # integer number of minutes

                 image = None,     # an Image
                 rating = None,    # a string; I don't know how it's used
                 textInput = None, # a TextInput
                 skipHours = None, # a SkipHours with a list of integers
                 skipDays = None,  # a SkipDays with a list of strings

                 items = None,     # list of RSSItems
                 ):
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.copyright = copyright
        self.managingEditor = managingEditor

        self.webMaster = webMaster
        self.pubDate = pubDate
        self.lastBuildDate = lastBuildDate

        if categories is None:
            categories = []
        self.categories = categories
        self.generator = generator
        self.docs = docs
        self.cloud = cloud
        self.ttl = ttl
        self.image = image
        self.rating = rating
        self.textInput = textInput
        self.skipHours = skipHours
        self.skipDays = skipDays

        if items is None:
            items = []
        self.items = items

    def publish(self, handler):
        handler.startElement("rss", self.rss_attrs)
        handler.startElement("channel", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)
        _element(handler, "description", self.description)

        self.publish_extensions(handler)

        _opt_element(handler, "language", self.language)
        _opt_element(handler, "copyright", self.copyright)
        _opt_element(handler, "managingEditor", self.managingEditor)
        _opt_element(handler, "webMaster", self.webMaster)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        lastBuildDate = self.lastBuildDate
        if isinstance(lastBuildDate, datetime.datetime):
            lastBuildDate = DateElement("lastBuildDate", lastBuildDate)
        _opt_element(handler, "lastBuildDate", lastBuildDate)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)

        _opt_element(handler, "generator", self.generator)
        _opt_element(handler, "docs", self.docs)

        if self.cloud is not None:
            self.cloud.publish(handler)

        ttl = self.ttl
        if isinstance(self.ttl, int):
            ttl = IntElement("ttl", ttl)
        _opt_element(handler, "ttl", ttl)

        if self.image is not None:
            self.image.publish(handler)

        _opt_element(handler, "rating", self.rating)
        if self.textInput is not None:
            self.textInput.publish(handler)
        if self.skipHours is not None:
            self.skipHours.publish(handler)
        if self.skipDays is not None:
            self.skipDays.publish(handler)

        for item in self.items:
            item.publish(handler)

        handler.endElement("channel")
        handler.endElement("rss")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the three required fields.
        pass



class RSSItem(WriteXmlMixin):
    """Publish an RSS Item"""
    element_attrs = {}
    def __init__(self,
                 title = None,  # string
                 link = None,   # url as string
                 description = None, # string
                 author = None,      # email address as string
                 categories = None,  # list of string or Category
                 comments = None,  # url as string
                 enclosure = None, # an Enclosure
                 guid = None,    # a unique string
                 pubDate = None, # a datetime
                 source = None,  # a Source
                 ):

        if title is None and description is None:
            raise TypeError(
                "must define at least one of 'title' or 'description'")
        self.title = title
        self.link = link
        self.description = description
        self.author = author
        if categories is None:
            categories = []
        self.categories = categories
        self.comments = comments
        self.enclosure = enclosure
        self.guid = guid
        self.pubDate = pubDate
        self.source = source
        # It sure does get tedious typing these names three times...

    def publish(self, handler):
        handler.startElement("item", self.element_attrs)
        _opt_element(handler, "title", self.title)
        _opt_element(handler, "link", self.link)
        self.publish_extensions(handler)
        _opt_element(handler, "description", self.description)
        _opt_element(handler, "author", self.author)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)

        _opt_element(handler, "comments", self.comments)
        if self.enclosure is not None:
            self.enclosure.publish(handler)
        _opt_element(handler, "guid", self.guid)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        if self.source is not None:
            self.source.publish(handler)

        handler.endElement("item")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the title and link elements
        pass

########NEW FILE########
__FILENAME__ = server
"""A simple web server to handle OAuth 2.0 redirects.

Partial code taken from google api python client.
see: https://code.google.com/p/google-api-python-client/source/browse/oauth2client/tools.py
Original author: jcgregorio@google.com (Joe Gregorio)
"""

import BaseHTTPServer
import socket
import sys
try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl


class ClientRedirectServer(BaseHTTPServer.HTTPServer):
  """A server to handle OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into query_params and then stops serving.
  """
  query_params = {}
  query_path = ""


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """A handler for OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into the servers query_params and then stops serving.
  """

  def do_GET(s):
    """Handle a GET request.

    Parses the query parameters and prints a message
    if the flow has completed. Note that we can't detect
    if an error occurred.
    """
    s.send_response(200)
    s.send_header("Content-type", "text/html")
    s.end_headers()
    s.server.query_path = s.path
    query = s.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    s.server.query_params = query
    s.wfile.write("<html><head><title>Authentication Status</title></head>")
    s.wfile.write("<body><p>The authentication flow has completed.</p>")
    s.wfile.write("</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""
    pass


########NEW FILE########
__FILENAME__ = timezone_sample
'''
Source:
   * http://docs.python.org/release/2.5.2/lib/datetime-tzinfo.html

I have to say, the Python world is insane when dealing with time...
The conversion between UTC integer and a human readable string
should be a common function required by apps. However, there does
not seem to be a "only right way" to do it...

Copy these sample TZ class here to give others a hint when their
platforms can not return a correct ``tz.tzlocal()``.

See:

   * Issue 36
   * ``snsconf.py`` for a sample use
'''

from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

# A UTC class.

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()

# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")

########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/env python
#
# vim: sw=2 ts=2 sts=2
#
# Copyright 2007 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''A library that provides a Python interface to the Twitter API'''

__author__ = 'python-twitter@googlegroups.com'
__version__ = '1.0.1'


import calendar
import datetime
import httplib
import os
import rfc822
import sys
import tempfile
import textwrap
import time
import urllib
import urllib2
import urlparse
import gzip
import StringIO

try:
  # Python >= 2.6
  import json as simplejson
except ImportError:
  try:
    # Python < 2.6
    import simplejson
  except ImportError:
    try:
      # Google App Engine
      from django.utils import simplejson
    except ImportError:
      raise ImportError, "Unable to load a json library"

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl, parse_qs
except ImportError:
  from cgi import parse_qsl, parse_qs

try:
  from hashlib import md5
except ImportError:
  from md5 import md5

import oauth2 as oauth


CHARACTER_LIMIT = 140

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'


class TwitterError(Exception):
  '''Base class for Twitter errors'''

  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.favorite_count
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.location
    status.relative_created_at # read only
    status.user
    status.urls
    status.user_mentions
    status.hashtags
    status.geo
    status.place
    status.coordinates
    status.contributors
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               favorite_count=None,
               id=None,
               text=None,
               location=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None,
               urls=None,
               user_mentions=None,
               hashtags=None,
               media=None,
               geo=None,
               place=None,
               coordinates=None,
               contributors=None,
               retweeted=None,
               retweeted_status=None,
               current_user_retweet=None,
               retweet_count=None,
               possibly_sensitive=None,
               scopes=None,
               withheld_copyright=None,
               withheld_in_countries=None,
               withheld_scope=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at:
        The time this status message was posted. [Optional]
      favorited:
        Whether this is a favorite of the authenticated user. [Optional]
      favorite_count:
        Number of times this status message has been favorited. [Optional]
      id:
        The unique id of this status message. [Optional]
      text:
        The text of this status message. [Optional]
      location:
        the geolocation string associated with this message. [Optional]
      relative_created_at:
        A human readable string representing the posting time. [Optional]
      user:
        A twitter.User instance representing the person posting the
        message. [Optional]
      now:
        The current time, if the client chooses to set it.
        Defaults to the wall clock time. [Optional]
      urls:
      user_mentions:
      hashtags:
      geo:
      place:
      coordinates:
      contributors:
      retweeted:
      retweeted_status:
      current_user_retweet:
      retweet_count:
      possibly_sensitive:
      scopes:
      withheld_copyright:
      withheld_in_countries:
      withheld_scope:
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.favorite_count = favorite_count
    self.id = id
    self.text = text
    self.location = location
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.retweeted = retweeted
    self.source = source
    self.urls = urls
    self.user_mentions = user_mentions
    self.hashtags = hashtags
    self.media = media
    self.geo = geo
    self.place = place
    self.coordinates = coordinates
    self.contributors = contributors
    self.retweeted_status = retweeted_status
    self.current_user_retweet = current_user_retweet
    self.retweet_count = retweet_count
    self.possibly_sensitive = possibly_sensitive
    self.scopes = scopes
    self.withheld_copyright = withheld_copyright
    self.withheld_in_countries = withheld_in_countries
    self.withheld_scope = withheld_scope

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at:
        The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited:
        boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetFavoriteCount(self):
    '''Get the favorite count of this status message.

    Returns:
      number of times this status message has been favorited
    '''
    return self._favorite_count

  def SetFavoriteCount(self, favorite_count):
    '''Set the favorited state of this status message.

    Args:
      favorite_count:
        int number of favorites for this status message
    '''
    self._favorite_count = favorite_count

  favorite_count = property(GetFavoriteCount, SetFavoriteCount,
                       doc='The number of favorites for this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id:
        The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                                     doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                                 doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                                   doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                       doc='')

  def GetRetweeted(self):
    return self._retweeted

  def SetRetweeted(self, retweeted):
    self._retweeted = retweeted

  retweeted = property(GetRetweeted, SetRetweeted,
                       doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                    doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text:
        The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetLocation(self):
    '''Get the geolocation associated with this status message

    Returns:
      The geolocation string of this status message.
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geolocation associated with this status message

    Args:
      location:
        The geolocation string of this status message
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geolocation string of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human readable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing '
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User representing the entity posting this status message.

    Returns:
      A twitter.User representing the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User representing the entity posting this status message.

    Args:
      user:
        A twitter.User representing the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User representing the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now:
        The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')

  def GetGeo(self):
    return self._geo

  def SetGeo(self, geo):
    self._geo = geo

  geo = property(GetGeo, SetGeo,
                 doc='')

  def GetPlace(self):
    return self._place

  def SetPlace(self, place):
    self._place = place

  place = property(GetPlace, SetPlace,
                   doc='')

  def GetCoordinates(self):
    return self._coordinates

  def SetCoordinates(self, coordinates):
    self._coordinates = coordinates

  coordinates = property(GetCoordinates, SetCoordinates,
                         doc='')

  def GetContributors(self):
    return self._contributors

  def SetContributors(self, contributors):
    self._contributors = contributors

  contributors = property(GetContributors, SetContributors,
                          doc='')

  def GetRetweeted_status(self):
    return self._retweeted_status

  def SetRetweeted_status(self, retweeted_status):
    self._retweeted_status = retweeted_status

  retweeted_status = property(GetRetweeted_status, SetRetweeted_status,
                              doc='')

  def GetRetweetCount(self):
    return self._retweet_count

  def SetRetweetCount(self, retweet_count):
    self._retweet_count = retweet_count

  retweet_count = property(GetRetweetCount, SetRetweetCount,
                           doc='')

  def GetCurrent_user_retweet(self):
    return self._current_user_retweet

  def SetCurrent_user_retweet(self, current_user_retweet):
    self._current_user_retweet = current_user_retweet

  current_user_retweet = property(GetCurrent_user_retweet, SetCurrent_user_retweet,
                                  doc='')

  def GetPossibly_sensitive(self):
    return self._possibly_sensitive

  def SetPossibly_sensitive(self, possibly_sensitive):
    self._possibly_sensitive = possibly_sensitive

  possibly_sensitive = property(GetPossibly_sensitive, SetPossibly_sensitive,
                                doc='')

  def GetScopes(self):
    return self._scopes

  def SetScopes(self, scopes):
    self._scopes = scopes

  scopes = property(GetScopes, SetScopes, doc='')

  def GetWithheld_copyright(self):
    return self._withheld_copyright

  def SetWithheld_copyright(self, withheld_copyright):
    self._withheld_copyright = withheld_copyright

  withheld_copyright = property(GetWithheld_copyright, SetWithheld_copyright,
                                doc='')

  def GetWithheld_in_countries(self):
    return self._withheld_in_countries

  def SetWithheld_in_countries(self, withheld_in_countries):
    self._withheld_in_countries = withheld_in_countries

  withheld_in_countries = property(GetWithheld_in_countries, SetWithheld_in_countries,
                                doc='')

  def GetWithheld_scope(self):
    return self._withheld_scope

  def SetWithheld_scope(self, withheld_scope):
    self._withheld_scope = withheld_scope

  withheld_scope = property(GetWithheld_scope, SetWithheld_scope,
                                doc='')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.location == other.location and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.retweeted == other.retweeted and \
             self.favorited == other.favorited and \
             self.favorite_count == other.favorite_count and \
             self.source == other.source and \
             self.geo == other.geo and \
             self.place == other.place and \
             self.coordinates == other.coordinates and \
             self.contributors == other.contributors and \
             self.retweeted_status == other.retweeted_status and \
             self.retweet_count == other.retweet_count and \
             self.current_user_retweet == other.current_user_retweet and \
             self.possibly_sensitive == other.possibly_sensitive and \
             self.scopes == other.scopes and \
             self.withheld_copyright == other.withheld_copyright and \
             self.withheld_in_countries == other.withheld_in_countries and \
             self.withheld_scope == other.withheld_scope
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.favorite_count:
      data['favorite_count'] = self.favorite_count
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.location:
      data['location'] = self.location
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.retweeted is not None:
      data['retweeted'] = self.retweeted
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    if self.geo:
      data['geo'] = self.geo
    if self.place:
      data['place'] = self.place
    if self.coordinates:
      data['coordinates'] = self.coordinates
    if self.contributors:
      data['contributors'] = self.contributors
    if self.hashtags:
      data['hashtags'] = [h.text for h in self.hashtags]
    if self.retweeted_status:
      data['retweeted_status'] = self.retweeted_status.AsDict()
    if self.retweet_count:
      data['retweet_count'] = self.retweet_count
    if self.urls:
      data['urls'] = dict([(url.url, url.expanded_url) for url in self.urls])
    if self.user_mentions:
      data['user_mentions'] = [um.AsDict() for um in self.user_mentions]
    if self.current_user_retweet:
      data['current_user_retweet'] = self.current_user_retweet
    if self.possibly_sensitive:
      data['possibly_sensitive'] = self.possibly_sensitive
    if self.scopes:
      data['scopes'] = self.scopes
    if self.withheld_copyright:
      data['withheld_copyright'] = self.withheld_copyright
    if self.withheld_in_countries:
      data['withheld_in_countries'] = self.withheld_in_countries
    if self.withheld_scope:
      data['withheld_scope'] = self.withheld_scope
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    if 'retweeted_status' in data:
      retweeted_status = Status.NewFromJsonDict(data['retweeted_status'])
    else:
      retweeted_status = None

    if 'current_user_retweet' in data:
      current_user_retweet = data['current_user_retweet']['id']
    else:
      current_user_retweet = None

    urls = None
    user_mentions = None
    hashtags = None
    media = None
    if 'entities' in data:
      if 'urls' in data['entities']:
        urls = [Url.NewFromJsonDict(u) for u in data['entities']['urls']]
      if 'user_mentions' in data['entities']:
        user_mentions = [User.NewFromJsonDict(u) for u in data['entities']['user_mentions']]
      if 'hashtags' in data['entities']:
        hashtags = [Hashtag.NewFromJsonDict(h) for h in data['entities']['hashtags']]
      if 'media' in data['entities']:
        media = data['entities']['media']
      else:
        media = []
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  favorite_count=data.get('favorite_count', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  location=data.get('location', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  retweeted=data.get('retweeted', None),
                  source=data.get('source', None),
                  user=user,
                  urls=urls,
                  user_mentions=user_mentions,
                  hashtags=hashtags,
                  media=media,
                  geo=data.get('geo', None),
                  place=data.get('place', None),
                  coordinates=data.get('coordinates', None),
                  contributors=data.get('contributors', None),
                  retweeted_status=retweeted_status,
                  current_user_retweet=current_user_retweet,
                  retweet_count=data.get('retweet_count', None),
                  possibly_sensitive=data.get('possibly_sensitive', None),
                  scopes=data.get('scopes', None),
                  withheld_copyright=data.get('withheld_copyright', None),
                  withheld_in_countries=data.get('withheld_in_countries', None),
                  withheld_scope=data.get('withheld_scope', None))


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
    user.geo_enabled
    user.verified
    user.lang
    user.notifications
    user.contributors_enabled
    user.created_at
    user.listed_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None,
               geo_enabled=None,
               verified=None,
               lang=None,
               notifications=None,
               contributors_enabled=None,
               created_at=None,
               listed_count=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status
    self.geo_enabled = geo_enabled
    self.verified = verified
    self.lang = lang
    self.notifications = notifications
    self.contributors_enabled = contributors_enabled
    self.created_at = created_at
    self.listed_count = listed_count

  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short twitter name of this user.

    Returns:
      The short twitter name of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short twitter name of this user.

    Args:
      screen_name: the short twitter name of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short twitter name of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone:
        The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status:
        The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                    doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.

    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count:
        The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                           doc='The number of friends for this user.')

  def GetListedCount(self):
    '''Get the listed count for this user.

    Returns:
      The number of lists this user belongs to.
    '''
    return self._listed_count

  def SetListedCount(self, count):
    '''Set the listed count for this user.

    Args:
      count:
        The number of lists this user belongs to.
    '''
    self._listed_count = count

  listed_count = property(GetListedCount, SetListedCount,
                          doc='The number of lists this user belongs to.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.

    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count:
        The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                             doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.

    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count:
        The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                            doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.

    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count:
        The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                              doc='The number of favourites for this user.')

  def GetGeoEnabled(self):
    '''Get the setting of geo_enabled for this user.

    Returns:
      True/False if Geo tagging is enabled
    '''
    return self._geo_enabled

  def SetGeoEnabled(self, geo_enabled):
    '''Set the latest twitter.geo_enabled of this user.

    Args:
      geo_enabled:
        True/False if Geo tagging is to be enabled
    '''
    self._geo_enabled = geo_enabled

  geo_enabled = property(GetGeoEnabled, SetGeoEnabled,
                         doc='The value of twitter.geo_enabled for this user.')

  def GetVerified(self):
    '''Get the setting of verified for this user.

    Returns:
      True/False if user is a verified account
    '''
    return self._verified

  def SetVerified(self, verified):
    '''Set twitter.verified for this user.

    Args:
      verified:
        True/False if user is a verified account
    '''
    self._verified = verified

  verified = property(GetVerified, SetVerified,
                      doc='The value of twitter.verified for this user.')

  def GetLang(self):
    '''Get the setting of lang for this user.

    Returns:
      language code of the user
    '''
    return self._lang

  def SetLang(self, lang):
    '''Set twitter.lang for this user.

    Args:
      lang:
        language code for the user
    '''
    self._lang = lang

  lang = property(GetLang, SetLang,
                  doc='The value of twitter.lang for this user.')

  def GetNotifications(self):
    '''Get the setting of notifications for this user.

    Returns:
      True/False for the notifications setting of the user
    '''
    return self._notifications

  def SetNotifications(self, notifications):
    '''Set twitter.notifications for this user.

    Args:
      notifications:
        True/False notifications setting for the user
    '''
    self._notifications = notifications

  notifications = property(GetNotifications, SetNotifications,
                           doc='The value of twitter.notifications for this user.')

  def GetContributorsEnabled(self):
    '''Get the setting of contributors_enabled for this user.

    Returns:
      True/False contributors_enabled of the user
    '''
    return self._contributors_enabled

  def SetContributorsEnabled(self, contributors_enabled):
    '''Set twitter.contributors_enabled for this user.

    Args:
      contributors_enabled:
        True/False contributors_enabled setting for the user
    '''
    self._contributors_enabled = contributors_enabled

  contributors_enabled = property(GetContributorsEnabled, SetContributorsEnabled,
                                  doc='The value of twitter.contributors_enabled for this user.')

  def GetCreatedAt(self):
    '''Get the setting of created_at for this user.

    Returns:
      created_at value of the user
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set twitter.created_at for this user.

    Args:
      created_at:
        created_at value for the user
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The value of twitter.created_at for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status and \
             self.geo_enabled == other.geo_enabled and \
             self.verified == other.verified and \
             self.lang == other.lang and \
             self.notifications == other.notifications and \
             self.contributors_enabled == other.contributors_enabled and \
             self.created_at == other.created_at and \
             self.listed_count == other.listed_count

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    if self.geo_enabled:
      data['geo_enabled'] = self.geo_enabled
    if self.verified:
      data['verified'] = self.verified
    if self.lang:
      data['lang'] = self.lang
    if self.notifications:
      data['notifications'] = self.notifications
    if self.contributors_enabled:
      data['contributors_enabled'] = self.contributors_enabled
    if self.created_at:
      data['created_at'] = self.created_at
    if self.listed_count:
      data['listed_count'] = self.listed_count

    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url_https', data.get('profile_image_url', None)),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status,
                geo_enabled=data.get('geo_enabled', None),
                verified=data.get('verified', None),
                lang=data.get('lang', None),
                notifications=data.get('notifications', None),
                contributors_enabled=data.get('contributors_enabled', None),
                created_at=data.get('created_at', None),
                listed_count=data.get('listed_count', None))

class List(object):
  '''A class representing the List structure used by the twitter API.

  The List structure exposes the following properties:

    list.id
    list.name
    list.slug
    list.description
    list.full_name
    list.mode
    list.uri
    list.member_count
    list.subscriber_count
    list.following
  '''
  def __init__(self,
               id=None,
               name=None,
               slug=None,
               description=None,
               full_name=None,
               mode=None,
               uri=None,
               member_count=None,
               subscriber_count=None,
               following=None,
               user=None):
    self.id = id
    self.name = name
    self.slug = slug
    self.description = description
    self.full_name = full_name
    self.mode = mode
    self.uri = uri
    self.member_count = member_count
    self.subscriber_count = subscriber_count
    self.following = following
    self.user = user

  def GetId(self):
    '''Get the unique id of this list.

    Returns:
      The unique id of this list
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this list.

    Args:
      id:
        The unique id of this list.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this list.')

  def GetName(self):
    '''Get the real name of this list.

    Returns:
      The real name of this list
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this list.

    Args:
      name:
        The real name of this list
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this list.')

  def GetSlug(self):
    '''Get the slug of this list.

    Returns:
      The slug of this list
    '''
    return self._slug

  def SetSlug(self, slug):
    '''Set the slug of this list.

    Args:
      slug:
        The slug of this list.
    '''
    self._slug = slug

  slug = property(GetSlug, SetSlug,
                  doc='The slug of this list.')

  def GetDescription(self):
    '''Get the description of this list.

    Returns:
      The description of this list
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the description of this list.

    Args:
      description:
        The description of this list.
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The description of this list.')

  def GetFull_name(self):
    '''Get the full_name of this list.

    Returns:
      The full_name of this list
    '''
    return self._full_name

  def SetFull_name(self, full_name):
    '''Set the full_name of this list.

    Args:
      full_name:
        The full_name of this list.
    '''
    self._full_name = full_name

  full_name = property(GetFull_name, SetFull_name,
                       doc='The full_name of this list.')

  def GetMode(self):
    '''Get the mode of this list.

    Returns:
      The mode of this list
    '''
    return self._mode

  def SetMode(self, mode):
    '''Set the mode of this list.

    Args:
      mode:
        The mode of this list.
    '''
    self._mode = mode

  mode = property(GetMode, SetMode,
                  doc='The mode of this list.')

  def GetUri(self):
    '''Get the uri of this list.

    Returns:
      The uri of this list
    '''
    return self._uri

  def SetUri(self, uri):
    '''Set the uri of this list.

    Args:
      uri:
        The uri of this list.
    '''
    self._uri = uri

  uri = property(GetUri, SetUri,
                 doc='The uri of this list.')

  def GetMember_count(self):
    '''Get the member_count of this list.

    Returns:
      The member_count of this list
    '''
    return self._member_count

  def SetMember_count(self, member_count):
    '''Set the member_count of this list.

    Args:
      member_count:
        The member_count of this list.
    '''
    self._member_count = member_count

  member_count = property(GetMember_count, SetMember_count,
                          doc='The member_count of this list.')

  def GetSubscriber_count(self):
    '''Get the subscriber_count of this list.

    Returns:
      The subscriber_count of this list
    '''
    return self._subscriber_count

  def SetSubscriber_count(self, subscriber_count):
    '''Set the subscriber_count of this list.

    Args:
      subscriber_count:
        The subscriber_count of this list.
    '''
    self._subscriber_count = subscriber_count

  subscriber_count = property(GetSubscriber_count, SetSubscriber_count,
                              doc='The subscriber_count of this list.')

  def GetFollowing(self):
    '''Get the following status of this list.

    Returns:
      The following status of this list
    '''
    return self._following

  def SetFollowing(self, following):
    '''Set the following status of this list.

    Args:
      following:
        The following of this list.
    '''
    self._following = following

  following = property(GetFollowing, SetFollowing,
                       doc='The following status of this list.')

  def GetUser(self):
    '''Get the user of this list.

    Returns:
      The owner of this list
    '''
    return self._user

  def SetUser(self, user):
    '''Set the user of this list.

    Args:
      user:
        The owner of this list.
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='The owner of this list.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.slug == other.slug and \
             self.description == other.description and \
             self.full_name == other.full_name and \
             self.mode == other.mode and \
             self.uri == other.uri and \
             self.member_count == other.member_count and \
             self.subscriber_count == other.subscriber_count and \
             self.following == other.following and \
             self.user == other.user

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.List instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.List instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.List instance.

    Returns:
      A JSON string representation of this twitter.List instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.List instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.List instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.slug:
      data['slug'] = self.slug
    if self.description:
      data['description'] = self.description
    if self.full_name:
      data['full_name'] = self.full_name
    if self.mode:
      data['mode'] = self.mode
    if self.uri:
      data['uri'] = self.uri
    if self.member_count is not None:
      data['member_count'] = self.member_count
    if self.subscriber_count is not None:
      data['subscriber_count'] = self.subscriber_count
    if self.following is not None:
      data['following'] = self.following
    if self.user is not None:
      data['user'] = self.user.AsDict()
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.List instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return List(id=data.get('id', None),
                name=data.get('name', None),
                slug=data.get('slug', None),
                description=data.get('description', None),
                full_name=data.get('full_name', None),
                mode=data.get('mode', None),
                uri=data.get('uri', None),
                member_count=data.get('member_count', None),
                subscriber_count=data.get('subscriber_count', None),
                following=data.get('following', None),
                user=user)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.

  The DirectMessage structure exposes the following properties:

    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id:
        The unique id of this direct message. [Optional]
      created_at:
        The time this direct message was posted. [Optional]
      sender_id:
        The id of the twitter user that sent this message. [Optional]
      sender_screen_name:
        The name of the twitter user that sent this message. [Optional]
      recipient_id:
        The id of the twitter that received this message. [Optional]
      recipient_screen_name:
        The name of the twitter that received this message. [Optional]
      text:
        The text of this direct message. [Optional]
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id:
        The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at:
        The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender_id:
        The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name:
        The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient_id:
        The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name:
        The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text:
        The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Hashtag(object):
  ''' A class representing a twitter hashtag
  '''
  def __init__(self,
               text=None):
    self.text = text

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Hashtag instance
    '''
    return Hashtag(text = data.get('text', None))

class Trend(object):
  ''' A class representing a trending topic
  '''
  def __init__(self, name=None, query=None, timestamp=None, url=None):
    self.name = name
    self.query = query
    self.timestamp = timestamp
    self.url = url

  def __str__(self):
    return 'Name: %s\nQuery: %s\nTimestamp: %s\nSearch URL: %s\n' % (self.name, self.query, self.timestamp, self.url)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.name == other.name and \
          self.query == other.query and \
          self.timestamp == other.timestamp and \
          self.url == self.url
    except AttributeError:
      return False

  @staticmethod
  def NewFromJsonDict(data, timestamp = None):
    '''Create a new instance based on a JSON dict

    Args:
      data:
        A JSON dict
      timestamp:
        Gets set as the timestamp property of the new object

    Returns:
      A twitter.Trend object
    '''
    return Trend(name=data.get('name', None),
                 query=data.get('query', None),
                 url=data.get('url', None),
                 timestamp=timestamp)

class Url(object):
  '''A class representing an URL contained in a tweet'''
  def __init__(self,
               url=None,
               expanded_url=None):
    self.url = url
    self.expanded_url = expanded_url

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Url instance
    '''
    return Url(url=data.get('url', None),
               expanded_url=data.get('expanded_url', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    consumer key and secret; and the oAuth key and secret:

      >>> api = twitter.Api(consumer_key='twitter consumer key',
                            consumer_secret='twitter consumer secret',
                            access_token_key='the_key_given',
                            access_token_secret='the_key_secret')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetHomeTimeLine()
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.GetSentDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
      >>> api.VerifyCredentials()
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute
  _API_REALM = 'Twitter API'

  def __init__(self,
               consumer_key=None,
               consumer_secret=None,
               access_token_key=None,
               access_token_secret=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE,
               shortner=None,
               base_url=None,
               use_gzip_compression=False,
               debugHTTP=False):
    '''Instantiate a new twitter.Api object.

    Args:
      consumer_key:
        Your Twitter user's consumer_key.
      consumer_secret:
        Your Twitter user's consumer_secret.
      access_token_key:
        The oAuth access token key value you retrieved
        from running get_access_token.py.
      access_token_secret:
        The oAuth access token's secret, also retrieved
        from the get_access_token.py run.
      input_encoding:
        The encoding used to encode input strings. [Optional]
      request_header:
        A dictionary of additional HTTP request headers. [Optional]
      cache:
        The cache instance to use. Defaults to DEFAULT_CACHE.
        Use None to disable caching. [Optional]
      shortner:
        The shortner instance to use.  Defaults to None.
        See shorten_url.py for an example shortner. [Optional]
      base_url:
        The base URL to use to contact the Twitter API.
        Defaults to https://api.twitter.com. [Optional]
      use_gzip_compression:
        Set to True to tell enable gzip compression for any call
        made to Twitter.  Defaults to False. [Optional]
      debugHTTP:
        Set to True to enable debug output from urllib2 when performing
        any HTTP requests.  Defaults to False. [Optional]
    '''
    self.SetCache(cache)
    self._urllib         = urllib2
    self._cache_timeout  = Api.DEFAULT_CACHE_TIMEOUT
    self._input_encoding = input_encoding
    self._use_gzip       = use_gzip_compression
    self._debugHTTP      = debugHTTP
    self._oauth_consumer = None
    self._shortlink_size = 19

    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()

    if base_url is None:
      self.base_url = 'https://api.twitter.com/1.1'
    else:
      self.base_url = base_url

    if consumer_key is not None and (access_token_key is None or
                                     access_token_secret is None):
      print >> sys.stderr, 'Twitter now requires an oAuth Access Token for API calls.'
      print >> sys.stderr, 'If your using this library from a command line utility, please'
      print >> sys.stderr, 'run the the included get_access_token.py tool to generate one.'

      raise TwitterError('Twitter requires oAuth Access Token for all API access')

    self.SetCredentials(consumer_key, consumer_secret, access_token_key, access_token_secret)

  def SetCredentials(self,
                     consumer_key,
                     consumer_secret,
                     access_token_key=None,
                     access_token_secret=None):
    '''Set the consumer_key and consumer_secret for this instance

    Args:
      consumer_key:
        The consumer_key of the twitter account.
      consumer_secret:
        The consumer_secret for the twitter account.
      access_token_key:
        The oAuth access token key value you retrieved
        from running get_access_token.py.
      access_token_secret:
        The oAuth access token's secret, also retrieved
        from the get_access_token.py run.
    '''
    self._consumer_key        = consumer_key
    self._consumer_secret     = consumer_secret
    self._access_token_key    = access_token_key
    self._access_token_secret = access_token_secret
    self._oauth_consumer      = None

    if consumer_key is not None and consumer_secret is not None and \
       access_token_key is not None and access_token_secret is not None:
      self._signature_method_plaintext = oauth.SignatureMethod_PLAINTEXT()
      self._signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()

      self._oauth_token    = oauth.Token(key=access_token_key, secret=access_token_secret)
      self._oauth_consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)

  def ClearCredentials(self):
    '''Clear the any credentials for this instance
    '''
    self._consumer_key        = None
    self._consumer_secret     = None
    self._access_token_key    = None
    self._access_token_secret = None
    self._oauth_consumer      = None

  def GetSearch(self,
                term=None,
                geocode=None,
                since_id=None,
                max_id=None,
                until=None,
                count=15,
                lang=None,
                locale=None,
                result_type="mixed",
                include_entities=None):
    '''Return twitter search results for a given term.

    Args:
      term:
        Term to search by. Optional if you include geocode.
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [Optional]
      until:
        Returns tweets generated before the given date. Date should be
        formatted as YYYY-MM-DD. [Optional]
      geocode:
        Geolocation information in the form (latitude, longitude, radius)
        [Optional]
      count:
        Number of results to return.  Default is 15 [Optional]
      lang:
        Language for results as ISO 639-1 code.  Default is None (all languages)
        [Optional]
      locale:
        Language of the search query. Currently only 'ja' is effective. This is
        intended for language-specific consumers and the default should work in
        the majority of cases.
      result_type:
        Type of result which should be returned.  Default is "mixed".  Other
        valid options are "recent" and "popular". [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discrete structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message containing
      the term
    '''
    # Build request parameters
    parameters = {}

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if until:
        parameters['until'] = until

    if lang:
      parameters['lang'] = lang

    if locale:
      parameters['locale'] = locale

    if term is None and geocode is None:
      return []

    if term is not None:
      parameters['q'] = term

    if geocode is not None:
      parameters['geocode'] = ','.join(map(str, geocode))

    if include_entities:
      parameters['include_entities'] = 1

    try:
        parameters['count'] = int(count)
    except:
        raise TwitterError("count must be an integer")

    if result_type in ["mixed", "popular", "recent"]:
      parameters['result_type'] = result_type

    # Make and send requests
    url  = '%s/search/tweets.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    # Return built list of statuses
    return [Status.NewFromJsonDict(x) for x in data['statuses']]

  def GetUsersSearch(self,
                     term=None,
                     page=1,
                     count=20,
                     include_entities=None):
    '''Return twitter user search results for a given term.

    Args:
      term:
        Term to search by.
      page:
        Page of results to return. Default is 1
        [Optional]
      count:
        Number of results to return.  Default is 20
        [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discrete structure, including: user_mentions, urls, and hashtags.
        [Optional]

    Returns:
      A sequence of twitter.User instances, one for each message containing
      the term
    '''
    # Build request parameters
    parameters = {}

    if term is not None:
      parameters['q'] = term

    if include_entities:
      parameters['include_entities'] = 1

    try:
      parameters['count'] = int(count)
    except:
      raise TwitterError("count must be an integer")

    # Make and send requests
    url  = '%s/users/search.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [User.NewFromJsonDict(x) for x in data]

  def GetTrendsCurrent(self, exclude=None):
    '''Get the current top trending topics (global)

    Args:
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains a trend.
    '''
    return self.GetTrendsWoeid(id=1, exclude=exclude)

  def GetTrendsWoeid(self, id, exclude=None):
    '''Return the top 10 trending topics for a specific WOEID, if trending
    information is available for it.

    Args:
      woeid:
        the Yahoo! Where On Earth ID for a location.
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains a trend.
    '''
    url  = '%s/trends/place.json' % (self.base_url)
    parameters = {'id': id}

    if exclude:
      parameters['exclude'] = exclude

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []
    timestamp = data[0]['as_of']

    for trend in data[0]['trends']:
        trends.append(Trend.NewFromJsonDict(trend, timestamp = timestamp))
    return trends

  def GetHomeTimeline(self,
                         count=None,
                         since_id=None,
                         max_id=None,
                         trim_user=False,
                         exclude_replies=False,
                         contributor_details=False,
                         include_entities=True):
    '''
    Fetch a collection of the most recent Tweets and retweets posted by the
    authenticating user and the users they follow.

    The home timeline is central to how most users interact with the Twitter
    service.

    The twitter.Api instance must be authenticated.

    Args:
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200. Defaults to 20. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      trim_user:
        When True, each tweet returned in a timeline will include a user
        object including only the status authors numerical ID. Omit this
        parameter to receive the complete user object. [Optional]
      exclude_replies:
        This parameter will prevent replies from appearing in the
        returned timeline. Using exclude_replies with the count
        parameter will mean you will receive up-to count tweets -
        this is because the count parameter retrieves that many
        tweets before filtering out retweets and replies.
        [Optional]
      contributor_details:
        This parameter enhances the contributors element of the
        status response to include the screen_name of the contributor.
        By default only the user_id of the contributor is included.
        [Optional]
      include_entities:
        The entities node will be disincluded when set to false.
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    url = '%s/statuses/home_timeline.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except ValueError:
        raise TwitterError("'since_id' must be an integer")
    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except ValueError:
        raise TwitterError("'max_id' must be an integer")
    if trim_user:
      parameters['trim_user'] = 1
    if exclude_replies:
      parameters['exclude_replies'] = 1
    if contributor_details:
      parameters['contributor_details'] = 1
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self,
                      user_id=None,
                      screen_name=None,
                      since_id=None,
                      max_id=None,
                      count=None,
                      include_rts=None,
                      trim_user=None,
                      exclude_replies=None):
    '''Fetch the sequence of public Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user_id:
        Specifies the ID of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid user ID
        is also a valid screen name. [Optional]
      screen_name:
        Specifies the screen name of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid screen
        name is also a user ID. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [Optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200.  [Optional]
      include_rts:
        If True, the timeline will contain native retweets (if they
        exist) in addition to the standard stream of tweets. [Optional]
      trim_user:
        If True, statuses will only contain the numerical user ID only.
        Otherwise a full user object will be returned for each status.
        [Optional]
      exclude_replies:
        If True, this will prevent replies from appearing in the returned
        timeline. Using exclude_replies with the count parameter will mean you
        will receive up-to count tweets - this is because the count parameter
        retrieves that many tweets before filtering out retweets and replies.
        This parameter is only supported for JSON and XML responses. [Optional]

    Returns:
      A sequence of Status instances, one for each message up to count
    '''
    parameters = {}

    url = '%s/statuses/user_timeline.json' % (self.base_url)

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = screen_name

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if include_rts:
      parameters['include_rts'] = 1

    if trim_user:
      parameters['trim_user'] = 1

    if exclude_replies:
      parameters['exclude_replies'] = 1

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self,
                id,
                trim_user=False,
                include_my_retweet=True,
                include_entities=True):
    '''Returns a single status message, specified by the id parameter.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The numeric ID of the status you are trying to retrieve.
      trim_user:
        When set to True, each tweet returned in a timeline will include
        a user object including only the status authors numerical ID.
        Omit this parameter to receive the complete user object.
        [Optional]
      include_my_retweet:
        When set to True, any Tweets returned that have been retweeted by
        the authenticating user will include an additional
        current_user_retweet node, containing the ID of the source status
        for the retweet. [Optional]
      include_entities:
        If False, the entities node will be disincluded.
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]
    Returns:
      A twitter.Status instance representing that status message
    '''
    url  = '%s/statuses/show.json' % (self.base_url)

    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")

    parameters = {}

    try:
      parameters['id'] = long(id)
    except ValueError:
      raise TwitterError("'id' must be an integer.")

    if trim_user:
      parameters['trim_user'] = 1
    if include_my_retweet:
      parameters['include_my_retweet'] = 1
    if not include_entities:
      parameters['include_entities'] = 'none'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id, trim_user=False):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and the
    authenticating user must be the author of the specified status.

    Args:
      id:
        The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")

    try:
      post_data = {'id': long(id)}
    except:
      raise TwitterError("id must be an integer")
    url  = '%s/statuses/destroy/%s.json' % (self.base_url, id)
    if trim_user:
      post_data['trim_user'] = 1
    json = self._FetchUrl(url, post_data=post_data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  @classmethod
  def _calculate_status_length(cls, status, linksize=19):
    dummy_link_replacement = 'https://-%d-chars%s/' % (linksize, '-'*(linksize - 18))
    shortened = ' '.join([x if not (x.startswith('http://') or
                                    x.startswith('https://'))
                            else
                                dummy_link_replacement
                            for x in status.split(' ')])
    return len(shortened)

  def PostUpdate(self, status, in_reply_to_status_id=None, latitude=None, longitude=None, place_id=None, display_coordinates=False, trim_user=False):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    https://dev.twitter.com/docs/api/1.1/post/statuses/update

    Args:
      status:
        The message text to be posted.
        Must be less than or equal to 140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
      latitude:
        Latitude coordinate of the tweet in degrees. Will only work
        in conjunction with longitude argument. Both longitude and
        latitude will be ignored by twitter if the user has a false
        geo_enabled setting. [Optional]
      longitude:
        Longitude coordinate of the tweet in degrees. Will only work
        in conjunction with latitude argument. Both longitude and
        latitude will be ignored by twitter if the user has a false
        geo_enabled setting. [Optional]
      place_id:
        A place in the world. These IDs can be retrieved from
        GET geo/reverse_geocode. [Optional]
      display_coordinates:
        Whether or not to put a pin on the exact coordinates a tweet
        has been sent from. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = '%s/statuses/update.json' % self.base_url

    if isinstance(status, unicode) or self._input_encoding is None:
      u_status = status
    else:
      u_status = unicode(status, self._input_encoding)

    #if self._calculate_status_length(u_status, self._shortlink_size) > CHARACTER_LIMIT:
    #  raise TwitterError("Text must be less than or equal to %d characters. "
    #                     "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    if latitude is not None and longitude is not None:
      data['lat']     = str(latitude)
      data['long']    = str(longitude)
    if place_id is not None:
      data['place_id'] = str(place_id)
    if display_coordinates:
      data['display_coordinates'] = 'true'
    if trim_user:
      data['trim_user'] = 'true'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.
        May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.

    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def PostRetweet(self, original_id, trim_user=False):
    '''Retweet a tweet with the Retweet API.

    The twitter.Api instance must be authenticated.

    Args:
      original_id:
        The numerical id of the tweet that will be retweeted
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A twitter.Status instance representing the original tweet with retweet details embedded.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    try:
      if int(original_id) <= 0:
        raise TwitterError("'original_id' must be a positive number")
    except ValueError:
        raise TwitterError("'original_id' must be an integer")

    url = '%s/statuses/retweet/%s.json' % (self.base_url, original_id)

    data = {'id': original_id}
    if trim_user:
      data['trim_user'] = 'true'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def GetUserRetweets(self, count=None, since_id=None, max_id=None, trim_user=False):
    '''Fetch the sequence of retweets made by the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      count:
        The number of status messages to retrieve. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message up to count
    '''
    return self.GetUserTimeline(since_id=since_id, count=count, max_id=max_id, trim_user=trim_user, exclude_replies=True, include_rts=True)

  def GetReplies(self, since_id=None, count=None, max_id=None, trim_user=False):
    '''Get a sequence of status messages representing the 20 most
    recent replies (status updates prefixed with @twitterID) to the
    authenticating user.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each reply to the user.
    '''
    return self.GetUserTimeline(since_id=since_id, count=count, max_id=max_id, trim_user=trim_user, exclude_replies=False, include_rts=False)

  def GetRetweets(self, statusid, count=None, trim_user=False):
    '''Returns up to 100 of the first retweets of the tweet identified
    by statusid

    Args:
      statusid:
        The ID of the tweet for which retweets should be searched for
      count:
        The number of status messages to retrieve. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A list of twitter.Status instances, which are retweets of statusid
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instsance must be authenticated.")
    url = '%s/statuses/retweets/%s.json' % (self.base_url, statusid)
    parameters = {}
    if trim_user:
      parameters['trim_user'] = 'true'
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(s) for s in data]

  def GetRetweetsOfMe(self,
                      count=None,
                      since_id=None,
                      max_id=None,
                      trim_user=False,
                      include_entities=True,
                      include_user_entities=True):
    '''Returns up to 100 of the most recent tweets of the user that have been
    retweeted by others.

    Args:
      count:
        The number of retweets to retrieve, up to 100. If omitted, 20 is
        assumed.
      since_id:
        Returns results with an ID greater than (newer than) this ID.
      max_id:
        Returns results with an ID less than or equal to this ID.
      trim_user:
        When True, the user object for each tweet will only be an ID.
      include_entities:
        When True, the tweet entities will be included.
      include_user_entities:
        When True, the user entities will be included.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = '%s/statuses/retweets_of_me.json' % self.base_url
    parameters = {}
    if count is not None:
      try:
        if int(count) > 100:
          raise TwitterError("'count' may not be greater than 100")
      except ValueError:
        raise TwitterError("'count' must be an integer")
    if count:
      parameters['count'] = count
    if since_id:
      parameters['since_id'] = since_id
    if max_id:
      parameters['max_id'] = max_id
    if trim_user:
      parameters['trim_user'] = trim_user
    if not include_entities:
      parameters['include_entities'] = include_entities
    if not include_user_entities:
      parameters['include_user_entities'] = include_user_entities
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(s) for s in data]

  def GetFriends(self, user_id=None, screen_name=None, cursor=-1, skip_status=False, include_user_entities=False):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The twitter id of the user whose friends you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      screen_name:
        The twitter name of the user whose friends you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      cursor:
        Should be set to -1 for the initial call and then is used to
        control what result page Twitter returns [Optional(ish)]
      skip_status:
        If True the statuses will not be returned in the user items.
        [Optional]
      include_user_entities:
        When True, the user entities will be included.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/friends/list.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      parameters['user_id'] = user_id
    if screen_name is not None:
      parameters['screen_name'] = screen_name
    if skip_status:
      parameters['skip_status'] = True
    if include_user_entities:
      parameters['include_user_entities'] = True
    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [User.NewFromJsonDict(x) for x in data['users']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def GetFriendIDs(self, user_id=None, screen_name=None, cursor=-1, stringify_ids=False, count=None):
      '''Returns a list of twitter user id's for every person
      the specified user is following.

      Args:
        user_id:
          The id of the user to retrieve the id list for
          [Optional]
        screen_name:
          The screen_name of the user to retrieve the id list for
          [Optional]
        cursor:
          Specifies the Twitter API Cursor location to start at.
          Note: there are pagination limits.
          [Optional]
        stringify_ids:
          if True then twitter will return the ids as strings instead of integers.
          [Optional]
        count:
          The number of status messages to retrieve. [Optional]

      Returns:
        A list of integers, one for each user id.
      '''
      url = '%s/friends/ids.json' % self.base_url
      if not self._oauth_consumer:
          raise TwitterError("twitter.Api instance must be authenticated")
      parameters = {}
      if user_id is not None:
        parameters['user_id'] = user_id
      if screen_name is not None:
        parameters['screen_name'] = screen_name
      if stringify_ids:
        parameters['stringify_ids'] = True
      if count is not None:
        parameters['count'] = count
      result = []
      while True:
        parameters['cursor'] = cursor
        json = self._FetchUrl(url, parameters=parameters)
        data = self._ParseAndCheckTwitter(json)
        result += [x for x in data['ids']]
        if 'next_cursor' in data:
          if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
            break
          else:
            cursor = data['next_cursor']
        else:
          break
      return result


  def GetFollowerIDs(self, user_id=None, screen_name=None, cursor=-1, stringify_ids=False, count=None, total_count=None):
      '''Returns a list of twitter user id's for every person
      that is following the specified user.

      Args:
        user_id:
          The id of the user to retrieve the id list for
          [Optional]
        screen_name:
          The screen_name of the user to retrieve the id list for
          [Optional]
        cursor:
          Specifies the Twitter API Cursor location to start at.
          Note: there are pagination limits.
          [Optional]
        stringify_ids:
          if True then twitter will return the ids as strings instead of integers.
          [Optional]
        count:
          The number of user id's to retrieve per API request. Please be aware that
          this might get you rate-limited if set to a small number. By default Twitter
          will retrieve 5000 UIDs per call.
          [Optional]
        total_count:
          The total amount of UIDs to retrieve. Good if the account has many followers
          and you don't want to get rate limited. The data returned might contain more
          UIDs if total_count is not a multiple of count (5000 by default).
          [Optional]


      Returns:
        A list of integers, one for each user id.
      '''
      url = '%s/followers/ids.json' % self.base_url
      if not self._oauth_consumer:
          raise TwitterError("twitter.Api instance must be authenticated")
      parameters = {}
      if user_id is not None:
        parameters['user_id'] = user_id
      if screen_name is not None:
        parameters['screen_name'] = screen_name
      if stringify_ids:
        parameters['stringify_ids'] = True
      if count is not None:
        parameters['count'] = count
      result = []
      while True:
        if total_count and total_count < count:
          parameters['count'] = total_count
        parameters['cursor'] = cursor
        json = self._FetchUrl(url, parameters=parameters)
        data = self._ParseAndCheckTwitter(json)
        result += [x for x in data['ids']]
        if 'next_cursor' in data:
          if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
            break
          else:
            cursor = data['next_cursor']
            total_count -= len(data['ids'])
            if total_count < 1:
              break
        else:
          break
      return result

  def GetFollowers(self, user_id=None, screen_name=None, cursor=-1, skip_status=False, include_user_entities=False):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The twitter id of the user whose followers you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      screen_name:
        The twitter name of the user whose followers you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      cursor:
        Should be set to -1 for the initial call and then is used to
        control what result page Twitter returns [Optional(ish)]
      skip_status:
        If True the statuses will not be returned in the user items.
        [Optional]
      include_user_entities:
        When True, the user entities will be included.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/followers/list.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      parameters['user_id'] = user_id
    if screen_name is not None:
      parameters['screen_name'] = screen_name
    if skip_status:
      parameters['skip_status'] = True
    if include_user_entities:
      parameters['include_user_entities'] = True
    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [User.NewFromJsonDict(x) for x in data['users']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def UsersLookup(self, user_id=None, screen_name=None, users=None, include_entities=True):
    '''Fetch extended information for the specified users.

    Users may be specified either as lists of either user_ids,
    screen_names, or twitter.User objects. The list of users that
    are queried is the union of all specified parameters.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A list of user_ids to retrieve extended information.
        [Optional]
      screen_name:
        A list of screen_names to retrieve extended information.
        [Optional]
      users:
        A list of twitter.User objects to retrieve extended information.
        [Optional]
      include_entities:
        The entities node that may appear within embedded statuses will be
        disincluded when set to False.
        [Optional]

    Returns:
      A list of twitter.User objects for the requested users
    '''

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    if not user_id and not screen_name and not users:
      raise TwitterError("Specify at least one of user_id, screen_name, or users.")
    url = '%s/users/lookup.json' % self.base_url
    parameters = {}
    uids = list()
    if user_id:
      uids.extend(user_id)
    if users:
      uids.extend([u.id for u in users])
    if len(uids):
      parameters['user_id'] = ','.join(["%s" % u for u in uids])
    if screen_name:
      parameters['screen_name'] = ','.join(screen_name)
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    try:
      data = self._ParseAndCheckTwitter(json)
    except TwitterError, e:
        _, e, _ = sys.exc_info()
        t = e.args[0]
        if len(t) == 1 and ('code' in t[0]) and (t[0]['code'] == 34):
          data = []
        else:
            raise

    return [User.NewFromJsonDict(u) for u in data]

  def GetUser(self, user_id=None, screen_name=None, include_entities=True):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The id of the user to retrieve.
        [Optional]
      screen_name:
        The screen name of the user for whom to return results for. Either a
        user_id or screen_name is required for this method.
        [Optional]
      include_entities:
        if set to False, the 'entities' node will not be included.
        [Optional]


    Returns:
      A twitter.User instance representing that user
    '''
    url  = '%s/users/show.json' % (self.base_url)
    parameters = {}

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")

    if not include_entities:
      parameters['include_entities'] = 'false'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since_id=None, max_id=None, count=None, include_entities=True, skip_status=False):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      count:
        Specifies the number of direct messages to try and retrieve, up to a
        maximum of 200. The value of count is best thought of as a limit to the
        number of Tweets to return because suspended or deleted content is
        removed after the count has been applied. [Optional]
      include_entities:
        The entities node will not be included when set to False.
        [Optional]
      skip_status:
        When set to True statuses will not be included in the returned user
        objects. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = '%s/direct_messages.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    if max_id:
      parameters['max_id'] = max_id
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if not include_entities:
      parameters['include_entities'] = 'false'
    if skip_status:
      parameters['skip_status'] = 1
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def GetSentDirectMessages(self, since_id=None, max_id=None, count=None, page=None, include_entities=True):
    '''Returns a list of the direct messages sent by the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      count:
        Specifies the number of direct messages to try and retrieve, up to a
        maximum of 200. The value of count is best thought of as a limit to the
        number of Tweets to return because suspended or deleted content is
        removed after the count has been applied. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
      include_entities:
        The entities node will not be included when set to False.
        [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = '%s/direct_messages/sent.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    if max_id:
      parameters['max_id'] = max_id
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, text, user_id=None, screen_name=None):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated. user_id or screen_name
    must be specified.

    Args:
      text: The message text to be posted.  Must be less than 140 characters.
      user_id:
        The ID of the user who should receive the direct message.
        [Optional]
      screen_name:
        The screen name of the user who should receive the direct message.
        [Optional]

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url  = '%s/direct_messages/new.json' % self.base_url
    data = {'text': text}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id, include_entities=True):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url  = '%s/direct_messages/destroy.json' % self.base_url
    data = {'id': id}
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user_id=None, screen_name=None, follow=True):
    '''Befriends the user specified by the user_id or screen_name.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A user_id to follow [Optional]
      screen_name:
        A screen_name to follow [Optional]
      follow:
        Set to False to disable notifications for the target user
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url  = '%s/friendships/create.json' % (self.base_url)
    data = {}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    if follow:
      data['follow'] = 'true'
    else:
      data['follow'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user_id=None, screen_name=None):
    '''Discontinues friendship with a user_id or screen_name.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A user_id to unfollow [Optional]
      screen_name:
        A screen_name to unfollow [Optional]
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url  = '%s/friendships/destroy.json' % self.base_url
    data = {}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status=None, id=None, include_entities=True):
    '''Favorites the specified status object or id as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The id of the twitter status to mark as a favorite.
        [Optional]
      status:
        The twitter.Status object to mark as a favorite.
        [Optional]
      include_entities:
        The entities node will be omitted when set to False.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url  = '%s/favorites/create.json' % self.base_url
    data = {}
    if id:
      data['id'] = id
    elif status:
      data['id'] = status.id
    else:
      raise TwitterError("Specify id or status")
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status=None, id=None, include_entities=True):
    '''Un-Favorites the specified status object or id as the authenticating user.
    Returns the un-favorited status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The id of the twitter status to unmark as a favorite.
        [Optional]
      status:
        The twitter.Status object to unmark as a favorite.
        [Optional]
      include_entities:
        The entities node will be omitted when set to False.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url  = '%s/favorites/destroy.json' % self.base_url
    data = {}
    if id:
      data['id'] = id
    elif status:
      data['id'] = status.id
    else:
      raise TwitterError("Specify id or status")
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def GetFavorites(self,
                   user_id=None,
                   screen_name=None,
                   count=None,
                   since_id=None,
                   max_id=None,
                   include_entities=True):
    '''Return a list of Status objects representing favorited tweets.
    By default, returns the (up to) 20 most recent tweets for the
    authenticated user.

    Args:
      user:
        The twitter name or id of the user whose favorites you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
    '''
    parameters = {}

    url = '%s/favorites/list.json' % self.base_url

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = user_id

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if include_entities:
        parameters['include_entities'] = True


    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetMentions(self,
                  count=None,
                  since_id=None,
                  max_id=None,
                  trim_user=False,
                  contributor_details=False,
                  include_entities=True):
    '''Returns the 20 most recent mentions (status containing @screen_name)
    for the authenticating user.

    Args:
      count:
        Specifies the number of tweets to try and retrieve, up to a maximum of
        200. The value of count is best thought of as a limit to the number of
        tweets to return because suspended or deleted content is removed after
        the count has been applied. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than
        (that is, older than) the specified ID.  [Optional]
      trim_user:
        When set to True, each tweet returned in a timeline will include a user
        object including only the status authors numerical ID. Omit this
        parameter to receive the complete user object.
      contributor_details:
        If set to True, this parameter enhances the contributors element of the
        status response to include the screen_name of the contributor. By
        default only the user_id of the contributor is included.
      include_entities:
        The entities node will be disincluded when set to False.

    Returns:
      A sequence of twitter.Status instances, one for each mention of the user.
    '''

    url = '%s/statuses/mentions_timeline.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    parameters = {}

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")
    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")
    if trim_user:
      parameters['trim_user'] = 1
    if contributor_details:
      parameters['contributor_details'] = 'true'
    if not include_entities:
      parameters['include_entities'] = 'false'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def CreateList(self, name, mode=None, description=None):
    '''Creates a new list with the give name for the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      name:
        New name for the list
      mode:
        'public' or 'private'.
        Defaults to 'public'. [Optional]
      description:
        Description of the list. [Optional]

    Returns:
      A twitter.List instance representing the new list
    '''
    url = '%s/lists/create.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {'name': name}
    if mode is not None:
      parameters['mode'] = mode
    if description is not None:
      parameters['description'] = description
    json = self._FetchUrl(url, post_data=parameters)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroyList(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''
    Destroys the list identified by list_id or owner_screen_name/owner_id and
    slug.

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/lists/destroy.json' % self.base_url
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")

    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def CreateSubscription(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''Creates a subscription to a list by the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the list subscribed to
    '''
    url  = '%s/lists/subscribers/create.json' % (self.base_url)
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroySubscription(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''Destroys the subscription to a list for the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/lists/subscribers/destroy.json' % (self.base_url)
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def GetSubscriptions(self, user_id=None, screen_name=None, count=20, cursor=-1):
    '''
    Obtain a collection of the lists the specified user is subscribed to, 20
    lists per page by default. Does not include the user's own lists.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The ID of the user for whom to return results for. [Optional]
      screen_name:
        The screen name of the user for whom to return results for.
        [Optional]
      count:
       The amount of results to return per page. Defaults to 20.
       No more than 1000 results will ever be returned in a single page.
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/lists/subscriptions.json' % (self.base_url)
    parameters = {}

    try:
      parameters['cursor'] = int(cursor)
    except:
      raise TwitterError("cursor must be an integer")

    try:
      parameters['count'] = int(count)
    except:
      raise TwitterError("count must be an integer")

    if user_id is not None:
      try:
        parameters['user_id'] = long(user_id)
      except:
        raise TwitterError('user_id must be an integer')
    elif screen_name is not None:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError('Specify user_id or screen_name')

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [List.NewFromJsonDict(x) for x in data['lists']]

  def GetLists(self, user_id=None, screen_name=None, count=None, cursor=-1):
    '''Fetch the sequence of lists for a user.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The ID of the user for whom to return results for. [Optional]
      screen_name:
        The screen name of the user for whom to return results for.
        [Optional]
      count:
        The amount of results to return per page. Defaults to 20. No more than
        1000 results will ever be returned in a single page.
        [Optional]
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/lists/ownerships.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      try:
        parameters['user_id'] = long(user_id)
      except:
        raise TwitterError('user_id must be an integer')
    elif screen_name is not None:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError('Specify user_id or screen_name')
    if count is not None:
      parameters['count'] = count

    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [List.NewFromJsonDict(x) for x in data['lists']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def VerifyCredentials(self):
    '''Returns a twitter.User instance if the authenticating user is valid.

    Returns:
      A twitter.User instance representing that user if the
      credentials are valid, None otherwise.
    '''
    if not self._oauth_consumer:
      raise TwitterError("Api instance must first be given user credentials.")
    url = '%s/account/verify_credentials.json' % self.base_url
    try:
      json = self._FetchUrl(url, no_cache=True)
    except urllib2.HTTPError, http_error:
      if http_error.code == httplib.UNAUTHORIZED:
        return None
      else:
        raise http_error
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache:
        An instance that supports the same API as the twitter._FileCache
    '''
    if cache == DEFAULT_CACHE:
      self._cache = _FileCache()
    else:
      self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib:
        An instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout:
        Time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent:
        A string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def GetRateLimitStatus(self, resources=None):
    '''Fetch the rate limit status for the currently authorized user.

    Args:
      resources:
        A comma seperated list of resource families you want to know the current
        rate limit disposition of.
        [Optional]

    Returns:
      A dictionary containing the time the limit will reset (reset_time),
      the number of remaining hits allowed before the reset (remaining_hits),
      the number of hits allowed in a 60-minute period (hourly_limit), and
      the time of the reset in seconds since The Epoch (reset_time_in_seconds).
    '''
    parameters = {}
    if resources is not None:
      parameters['resources'] = resources

    url  = '%s/application/rate_limit_status.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters, no_cache=True)
    data = self._ParseAndCheckTwitter(json)
    return data

  def MaximumHitFrequency(self):
    '''Determines the minimum number of seconds that a program must wait
    before hitting the server again without exceeding the rate_limit
    imposed for the currently authenticated user.

    Returns:
      The minimum second interval that a program must use so as to not
      exceed the rate_limit imposed for the user.
    '''
    rate_status = self.GetRateLimitStatus()
    reset_time  = rate_status.get('reset_time', None)
    limit       = rate_status.get('remaining_hits', None)

    if reset_time:
      # put the reset time into a datetime object
      reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

      # find the difference in time between now and the reset time + 1 hour
      delta = reset + datetime.timedelta(hours=1) - datetime.datetime.utcnow()

      if not limit:
          return int(delta.seconds)

      # determine the minimum number of seconds allowed as a regular interval
      max_frequency = int(delta.seconds / limit) + 1

      # return the number of seconds
      return max_frequency

    return 60

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into constituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _DecompressGzippedResponse(self, response):
    raw_data = response.read()
    if response.headers.get('content-encoding', None) == 'gzip':
      url_data = gzip.GzipFile(fileobj=StringIO.StringIO(raw_data)).read()
    else:
      url_data = raw_data
    return url_data

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _ParseAndCheckTwitter(self, json):
    """Try and parse the JSON returned from Twitter and return
    an empty dictionary if there is any error. This is a purely
    defensive check because during some Twitter network outages
    it will return an HTML failwhale page."""
    try:
      data = simplejson.loads(json)
      self._CheckForTwitterError(data)
    except ValueError:
      if "<title>Twitter / Over capacity</title>" in json:
        raise TwitterError("Capacity Error")
      if "<title>Twitter / Error</title>" in json:
        raise TwitterError("Technical Error")
      raise TwitterError("json decoding")

    return data

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data:
        A python dict created from the Twitter json response

    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])
    if 'errors' in data:
      raise TwitterError(data['errors'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None,
                use_gzip_compression=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url:
        The URL to retrieve
      post_data:
        A dict of (str, unicode) key/value pairs.
        If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added
        to the query string. [Optional]
      no_cache:
        If true, overrides the cache on the current request
      use_gzip_compression:
        If True, tells the server to gzip-compress the response.
        It does not apply to POST requests.
        Defaults to None, which will get the value to use from
        the instance variable self._use_gzip [Optional]

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    if post_data:
      http_method = "POST"
    else:
      http_method = "GET"

    if self._debugHTTP:
      _debug = 1
    else:
      _debug = 0

    http_handler  = self._urllib.HTTPHandler(debuglevel=_debug)
    https_handler = self._urllib.HTTPSHandler(debuglevel=_debug)
    http_proxy = os.environ.get('http_proxy')
    https_proxy = os.environ.get('https_proxy')

    if http_proxy is None or  https_proxy is None :
      proxy_status = False
    else :
      proxy_status = True

    opener = self._urllib.OpenerDirector()
    opener.add_handler(http_handler)
    opener.add_handler(https_handler)

    if proxy_status is True :
      proxy_handler = self._urllib.ProxyHandler({'http':str(http_proxy),'https': str(https_proxy)})
      opener.add_handler(proxy_handler)

    if use_gzip_compression is None:
      use_gzip = self._use_gzip
    else:
      use_gzip = use_gzip_compression

    # Set up compression
    if use_gzip and not post_data:
      opener.addheaders.append(('Accept-Encoding', 'gzip'))

    if self._oauth_consumer is not None:
      if post_data and http_method == "POST":
        parameters = post_data.copy()

      req = oauth.Request.from_consumer_and_token(self._oauth_consumer,
                                                  token=self._oauth_token,
                                                  http_method=http_method,
                                                  http_url=url, parameters=parameters)

      req.sign_request(self._signature_method_hmac_sha1, self._oauth_consumer, self._oauth_token)

      headers = req.to_header()

      if http_method == "POST":
        encoded_post_data = req.to_postdata()
      else:
        encoded_post_data = None
        url = req.to_url()
    else:
      url = self._BuildUrl(url, extra_params=extra_params)
      encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      response = opener.open(url, encoded_post_data)
      url_data = self._DecompressGzippedResponse(response)
      opener.close()
    else:
      # Unique keys are a combination of the url and the oAuth Consumer Key
      if self._consumer_key:
        key = self._consumer_key + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        try:
          response = opener.open(url, encoded_post_data)
          url_data = self._DecompressGzippedResponse(response)
          self._cache.Set(key, url_data)
        except urllib2.HTTPError, e:
          print e
        opener.close()
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data

class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (AttributeError, IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()

    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import base64

try:
    import json
except ImportError:
    import simplejson as json

from snsconf import SNSConf
from snslog import SNSLog as logger
import multiprocessing

'''
utilities for snsapi
'''

class JsonObject(dict):
    '''
    general json object that can bind any fields but also act as a dict.
    '''
    def __getattr__(self, attr):
        '''
        HU Pili 20121029:
            We modify the raised error type so that this object
            is pickle-serializable.

        See reference:
            http://bytes.com/topic/python/answers/626288-pickling-class-__getattr__
        '''
        try:
            return self[attr]
        except KeyError:
            raise AttributeError

    def __setattr__(self, attr, value):
        self[attr] = value

class JsonDict(JsonObject):
    """
    The wrapper class for Python dict.

    It is intended to host Json compatible objects.
    In the interative CLI, the users are expected
    to configure SNSAPI during execution. To present
    the current config in a nice way. We should add
    indentation for the dump method.
    """
    def __init__(self, jsonconf = None):
        super(JsonDict, self).__init__()
        if jsonconf:
            self.update(jsonconf)

    def __str__(self):
        return self._dumps_pretty()

    def _dumps(self):
        return json.dumps(self)

    def _dumps_pretty(self):
        return json.dumps(self, indent=2)

    def get(self, attr, default_value = None):
        '''
        dict entry reading with fault tolerance.

        :attr:
            A str or a list of str.

        :return:
            The value corresponding to the (first) key, or default val.

        If attr is a list, we will try all the candidates until
        one 'get' is successful. If none of the candidates succeed,
        return a the ``default_value``.

        e.g. RSS format is very diverse.
        To my current knowledge, some formats have 'author' fields,
        but others do not:

           * rss : no
           * rss2 : yes
           * atom : yes
           * rdf : yes

        NOTE:

           * The original ``default_value`` is "(null)". Now we change
           to ``None``. ``None`` is more standard in Python and it does
           not have problem to convert to ``str`` (the usual way of
           using our data fields). It has the JSON counterpart: ``null``.

        '''
        #TODO:
        #    Check if other parts are broken due to this change from
        #    "(null)" to None.
        if isinstance(attr, str):
            return dict.get(self, attr, default_value)
        elif isinstance(attr, list):
            for a in attr:
                val = dict.get(self, a, None)
                if val:
                    return val
            return default_value
        else:
            logger.warning("Unkown type: %s", type(attr))
            return default_value


def obj2str(obj):
    '''
    Convert Python object to string using SNSApi convention.

    :param obj:
        A Python object that is "serializable".
        Check ``Serialize`` to what backend we use for serialization.
    '''
    return base64.encodestring(Serialize.dumps(obj))

def str2obj(string):
    '''
    Convert string to Python object using SNSApi convention.

    :param obj:
        A string constructed by ``obj2str``.
        Do not call this method on a string coming from an unkown source.
    '''
    return Serialize.loads(base64.decodestring(string))


def console_input(string = None):
    '''
    To make oauth2 testable, and more reusable, we use console_input to wrap raw_input.
    See http://stackoverflow.com/questions/2617057/supply-inputs-to-python-unittests.
    '''
    if string is None:
        return raw_input().decode(SNSConf.SNSAPI_CONSOLE_STDIN_ENCODING)
    else:
        return string.decode(SNSConf.SNSAPI_CONSOLE_STDIN_ENCODING)

def console_output(string):
    '''
    The sister function of console_input()!

    Actually it has a much longer story. See Issue#8:
    the discussion of console encoding~
    '''
    print string.encode(SNSConf.SNSAPI_CONSOLE_STDOUT_ENCODING)

#TODO:
#    Find simpler implementation for str2utc() and utc2str()
#    The current implementation JUST WORKS. It is far from
#    satisfactory. I surveyed the Internet but found no "correct"
#    solution. Many of those implementations on the Internet
#    only work with local time.
#
#    What I want is simple:
#       * Convert between unix timestamp (integer) and
#       an RFC822 string.
#       * The string SHOULD CONTAIN time zone either in
#       text or number format. It is parse-able. Using local
#       time zone is favoured but not mandatory.
import calendar
import time
from datetime import tzinfo, timedelta, datetime
from dateutil import parser as dtparser, tz
from third.PyRSS2Gen import _format_date

ZERO = timedelta(0)

class FixedOffsetTimeZone(tzinfo):
    """
    Fixed offset in minutes east from UTC.

    See ``third/timezone_sample.py`` for more samples.

    """
    def __init__(self, offset, name):
        '''
        Build a fixed offset ``tzinfo`` object.  No DST support.

        :type offset: int
        :param offset:
            Offset of your timezone in **MINUTES**
        :type name: str
        :param name:
            The name string of your timezone
        '''
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

SNSAPI_TIMEZONE = FixedOffsetTimeZone(0, 'GMT')

try:
    SNSAPI_TIMEZONE = tz.tzlocal()
    logger.debug("Get local timezone OK. Use system's tzlocal")
except Exception as e:
    # Silently ignore it and degrades to default TZ (GMT).
    # Logger has not been set at the moment.
    #
    # In case other methods refer to tzlocal(),
    # we fix it by the default TZ configured here.
    # (The ``dtparser`` will refer to ``tz.tzlocal``)
    logger.warning("Get local timezone failed. Use default GMT")
    tz.tzlocal = lambda : SNSAPI_TIMEZONE

def str2utc(s, tc = None):
    '''
    :param tc:
        Timezone Correction (TC). A timezone suffix string.
        e.g. ``" +08:00"``, `` HKT``, etc.
        Some platforms are know to return time string without TZ
        (e.g. Renren). Manually do the correction.
    '''
    if tc and tc.strip() != '':
        s += tc

    try:
        d = dtparser.parse(s)
        #print d
        #print d.utctimetuple()
        return calendar.timegm(d.utctimetuple())
    except Exception, e:
        logger.warning("error parsing time str '%s': %s", s, e)
        return 0

def utc2str(u, tz=None):
    # Format to RFC822 time string in current timezone
    if tz is None:
        tz = SNSAPI_TIMEZONE
    return _format_date(datetime.fromtimestamp(u, tz))

import re
_PATTERN_HTML_TAG = re.compile('<[^<]+?>')
def strip_html(text):
    # Ref:
    #    * http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
    return re.sub(_PATTERN_HTML_TAG, '', text)

import pickle

class Serialize(object):
    """
    The common serialization SAP

    """
    def __init__(self, *al, **ad):
        raise Exception("Use static methods of Serialize directly!")

    @staticmethod
    def loads(string):
        return pickle.loads(string)

    @staticmethod
    def dumps(obj):
        return pickle.dumps(obj)

import HTMLParser
def html_entity_unescape(s):
    '''
    Escape HTML entities, such as "&pound;"
    This interface always returns unicode no matter the input 's'
    is str or unicode.

    '''
    return HTMLParser.HTMLParser().unescape(s)

def report_time(func):
    def report_time_wrapper(*al, **ad):
        start = time.time()
        ret = func(*al, **ad)
        end = time.time()
        logger.info("Function '%s' execution time: %.2f", func.__name__, end - start)
        return ret
    return report_time_wrapper

@report_time
def _test_report_time(i):
    print "your number: %d" % i


class TimeoutException(Exception):
    pass

class RunnableProcess(multiprocessing.Process):
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func, ) + args
        multiprocessing.Process.__init__(self, target=self.execute_func, args=args, kwargs=kwargs)

    def execute_func(self, func, *args, **kwargs):
        try:
            r = func(*args, **kwargs)
            self.queue.put((True, r))
        except Exception as e:
            self.queue.put((False, e))

    def is_finished(self):
        return self.queue.full()

    def get_result(self):
        return self.queue.get()

def timeout(secs):
    def wrapper(function):
        def _func(*args, **kwargs):
            proc = RunnableProcess(function, *args, **kwargs)
            proc.start()
            proc.join(secs)
            if proc.is_alive():
                proc.terminate()
                raise TimeoutException("timed out when running %s" % (str(function)))
            assert proc.is_finished()
            ok, res = proc.get_result()
            if ok:
                return res
            else:
                raise res
        return _func
    return wrapper


if __name__ == '__main__':
    u = time.time()
    print u
    s = utc2str(u)
    print s
    print str2utc(s)
    print _test_report_time(3)

########NEW FILE########
__FILENAME__ = snscli-async
#!/usr/bin/env python
import sys

if len(sys.argv) != 2:
    print "usage: %s {fn_async_db}" % sys.argv[0]
    sys.exit(-1)

if __name__ == '__main__':
    # sync-version CLI initialization
    from snscli import *
    load_config()
    list_channel()
    auth()

    # async facility setup
    from snsapi.snspocket import BackgroundOperationPocketWithSQLite
    fn_async_db = sys.argv[1]
    asp = BackgroundOperationPocketWithSQLite(sp, sys.argv[1])
    ht = home_timeline = asp.home_timeline
    up = update = convert_parameter_to_unicode(asp.update)
    re = reply = convert_parameter_to_unicode(asp.reply)
    fwd = forward = convert_parameter_to_unicode(asp.forward)

    logger.info("Ready to drop into the interactive shell of asynchronous SNSCLI!")
    import code
    code.interact(local=locals())

########NEW FILE########
__FILENAME__ = snscli
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from snsapi.utils import console_output, console_input
from snsapi.snspocket import SNSPocket
from snsapi.snslog import SNSLog as logger

sp = SNSPocket()

import functools

def convert_parameter_to_unicode(func):
    '''
    Decorator to convert parameters to unicode if they are str

       * We use unicode inside SNSAPI.
       * If one str argument is found, we assume it is from console
         and convert it to unicode.

    This can solve for example:

       * The 'text' arg you give to ``update`` is not unicode.
       * You channel name contains non-ascii character, and you
         use ``ht(channel='xxx')`` to get the timeline.
    '''
    def to_unicode(s):
        if isinstance(s, str):
            return console_input(s)
        else:
            return s
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        new_args = map(lambda x: to_unicode(x), args)
        new_kwargs = dict(map(lambda x: (x[0], to_unicode(x[1])), kwargs.items()))
        return func(*new_args, **new_kwargs)
    return wrapper

# Shortcuts for you to operate in Python interactive shell

lc = load_config = sp.load_config
sc = save_config =  sp.save_config
lsc = list_channel =  sp.list_channel
lsp = list_platform =  sp.list_platform
newc = new_channel = sp.new_channel
addc = add_channel = sp.add_channel
clc = clear_channel = sp.clear_channel
auth = auth = sp.auth
ht = home_timeline = convert_parameter_to_unicode(sp.home_timeline)
up = update = convert_parameter_to_unicode(sp.update)
re = reply = convert_parameter_to_unicode(sp.reply)
fwd = forward = convert_parameter_to_unicode(sp.forward)

#==== documentation ====

helpdoc = \
"""
snscli -- the interactive CLI to operate all SNS!

Type "print helpdoc" again to see this document.

To start your new journey, type "print tut"

   * lc = load_config
   * sc = save_config
   * lsc = list_channel
   * lsp = list_platform
   * newc = new_channel
   * addc = add_channel
   * clc = clear_channel
   * auth = auth
   * ht = home_timeline
   * up = update
   * re = reply
   * fwd = forward

Tutorial of SNSCLI:

   * https://github.com/hupili/snsapi/wiki/Tutorial-of-snscli
"""

if __name__ == '__main__':
    #==== default initialization one may like ====
    print helpdoc
    load_config()
    list_channel()
    auth()

    logger.info("Ready to drop into the interactive shell of SNSCLI!")
    import code
    code.interact(local=locals())

########NEW FILE########
__FILENAME__ = snsgui
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# snsgui.py
# a simple gui for snsapi using Tkinter
#
# Author: Alex.wang
# Create: 2013-02-11 15:51


'''
# snsgui - a simple gui for snsapi using Tkinter


Usage
-----

* Press '+' button to add a sns channel.
* Press the Button before '+' to switch channel.
* Click 'Show More' in gray.
* Press 'Post' button to post new Status to current channel.


Theme Config
------------

* open conf/snsgui.ini
* find [theme] section and copy it
* custom your theme, change the value in the copied section
* name your theme, change [theme] to [THEME NAME]
* apply your theme, change 'theme' value in [snsapi] section to your theme name


Add Email Provider
------------------

* open conf/snsgui.ini
* find [Gmail] section and copy it
* change the value in the copied section
* name it, change [Gmail] to [EMAIL_ID]
* add it, add a 'EMAIL_ID = true' line in [email] section
'''


import Tkinter
import tkMessageBox
import tkSimpleDialog
import webbrowser
from ConfigParser import ConfigParser
import os

import snsapi
from snsapi.snspocket import SNSPocket
from snsapi.utils import utc2str


# supported platform
EMAIL = 'Email'
RSS = 'RSS'
RSS_RW = 'RSS2RW'
RSS_SUMMARY = 'RSSSummary'
RENREN_BLOG = 'RenrenBlog'
RENREN_SHARE = 'RenrenShare'
RENREN_STATUS = 'RenrenStatus'
SQLITE = 'SQLite'
SINA_WEIBO = 'SinaWeiboStatus'
TENCENT_WEIBO = 'TencentWeiboStatus'
TWITTER = 'TwitterStatus'


TITLE = 'snsapi'
CONFILE = os.path.join(snsapi._dir_static_data, 'snsgui.ini')


sp = SNSPocket()
gui = None
config = None


class SNSGuiConfig(ConfigParser):
    def __init__(self):
        ConfigParser.__init__(self)
        self.optionxform = str
        self.read(CONFILE)
        self.theme = self.get('snsgui', 'theme')
    def getcolor(self, option):
        return self.get(self.theme, option)
    def email(self):
        '''get supported email platforms'''
        return self.options('email')
    def getmail(self, option):
        '''get mail config dict'''
        d = {}
        for key, value in self.items(option):
            d[key] = value
        return d


class NewChannel(tkSimpleDialog.Dialog):
    '''Dialog to create new Channel'''
    def __init__(self, master, platform):
        self.platform = platform
        tkSimpleDialog.Dialog.__init__(self, master, 'Add %s Channel' % platform)
    def textField(self, master, row, label, id, init = ''):
        var = Tkinter.StringVar(master, init)
        setattr(self, id, var)
        Tkinter.Label(master, text = label).grid(row = row, column = 0, sticky = Tkinter.E)
        Tkinter.Entry(master, textvariable = var).grid(row = row, column = 1, sticky = Tkinter.NSEW)
        return row + 1
    def body(self, master):
        row = self.textField(master, 0, 'Channel Name:', 'channel_name')

        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO, TWITTER):
            row = self.textField(master, row, 'App Key:', 'app_key')
            row = self.textField(master, row, 'App Secret:', 'app_secret')

        if self.platform == EMAIL:
            items = config.email()
            self.email = Tkinter.StringVar(master, items[0])
            Tkinter.Label(master, text = 'Email:').grid(row = row, column = 0, sticky = Tkinter.E)
            Tkinter.OptionMenu(master, self.email, *items).grid(row = row, column = 1, sticky = Tkinter.NSEW)
            row += 1

        if self.platform in (EMAIL, RSS_RW, SQLITE):
            row = self.textField(master, row, 'User Name:', 'username')

        if self.platform in (EMAIL, ):
            row = self.textField(master, row, 'Password:', 'password')

        if self.platform in (TWITTER, ):
            row = self.textField(master, row, 'Access Key:', 'access_key')
            row = self.textField(master, row, 'Access Secret:', 'access_secret')

        if self.platform in (RSS, RSS_RW, RSS_SUMMARY, SQLITE):
            row = self.textField(master, row, 'Url:', 'url')

        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO):
            auth_info = Tkinter.LabelFrame(master, text = 'Auth info')

            self.textField(auth_info, 0, 'Callback Url:', 'callback_url')
            self.textField(auth_info, 1, 'Cmd Request Url:', 'cmd_request_url', '(default)')
            self.textField(auth_info, 2, 'Cmd Fetch Code:', 'cmd_fetch_code', '(default)')
            self.textField(auth_info, 3, 'Save Token File:', 'save_token_file', '(default)')

            auth_info.grid(row = row, column = 0, columnspan = 2)
            row += 1

    def validate(self):
        if not self.channel_name.get():
            return False

        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO, TWITTER):
            if not self.app_key.get() or not self.app_secret.get():
                return False

        if self.platform in (EMAIL, RSS_RW):
            if not self.username.get():
                return False

        if self.platform in (EMAIL, ):
            if not self.password.get():
                return False

        if self.platform in (TWITTER, ):
            if not self.access_key.get() or not self.access_secret.get():
                return False

        if self.platform in (RSS, RSS_RW, RSS_SUMMARY, SQLITE):
            if not self.url.get():
                return False

        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO):
            if not self.callback_url.get() or not self.cmd_request_url.get() or not self.cmd_fetch_code.get() or not self.save_token_file.get():
                return False

        return True

    def apply(self):
        channel = sp.new_channel(self.platform)
        channel['channel_name'] = self.channel_name.get()

        # app_key and app_secret
        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO, TWITTER):
            channel['app_key'] = self.app_key.get()
            channel['app_secret'] = self.app_secret.get()

        # username is optional for sqlite
        if self.platform == SQLITE and self.username.get():
            channel['username'] = self.username.get()

        if self.platform == RSS_RW:
            channel['author'] = self.username.get()

        if self.platform == EMAIL:
            channel['username'] = self.username.get()
            mail = config.getmail(self.email.get())
            channel['imap_host'] = mail['imap_host']
            channel['imap_port'] = int(mail['imap_port'])
            channel['smtp_host'] = mail['smtp_host']
            channel['smtp_port'] = int(mail['smtp_port'])
            channel['address'] = '%s@%s' % (self.username.get(), mail['domain'])

        # password
        if self.platform in (EMAIL, ):
            channel['password'] = self.password.get()

        # access_key and access_secret
        if self.platform in (TWITTER, ):
            channel['access_key'] = self.access_key.get()
            channel['access_secret'] = self.access_secret.get()

        # url
        if self.platform in (RSS, RSS_RW, RSS_SUMMARY, SQLITE):
            channel['url'] = self.url.get()

        # auth_info
        if self.platform in (RENREN_BLOG, RENREN_SHARE, RENREN_STATUS, SINA_WEIBO, TENCENT_WEIBO):
            channel['auth_info']['callback_url'] = self.callback_url.get()
            channel['auth_info']['cmd_request_url'] = self.cmd_request_url.get()
            channel['auth_info']['cmd_fetch_code'] = self.cmd_fetch_code.get()
            channel['auth_info']['save_token_file'] = self.save_token_file.get()

        self.result = channel


class TextDialog(tkSimpleDialog.Dialog):
    '''a general text input box'''
    def __init__(self, master, title, init_text = ''):
        self.init_text = init_text
        tkSimpleDialog.Dialog.__init__(self, master, title)

    def destroy(self):
        self.textWidget.unbind('<Return>', self.bind_id)
        tkSimpleDialog.Dialog.destroy(self)

    def body(self, master):
        self.textWidget = Tkinter.Text(master, width = 50, height = 6)
        self.bind_id = self.textWidget.bind('<Return>', self.enter_key)
        self.textWidget.insert('1.0', self.init_text)
        self.textWidget.pack(expand = True, fill = Tkinter.BOTH)

        return self.textWidget

    def enter_key(self, event):
        self.textWidget.insert(Tkinter.END, '\n')

        # this will stop further bound function, e.g. `OK' button
        return 'break'

    def get_text(self):
        text = ''
        for key, value, index in self.textWidget.dump('1.0', Tkinter.END, text = True):
            text += value
        return text.rstrip()

    def validate(self):
        if not self.get_text():
            return False

        return True

    def apply(self):
        self.result = self.get_text()


class StatusList(Tkinter.Text):
    '''Text widget to show status'''
    def __init__(self, master):
        self.allStatus = []
        Tkinter.Text.__init__(self, master, width = 50, height = 27, relief = Tkinter.FLAT)
        self.__misc()
        for s in sp.home_timeline(5):
            self.insert_status(s)

    def __misc(self):
        # common used tags
        self.tag_config('link', foreground = config.getcolor('link'), underline = 1)
        self.tag_config('text', justify = Tkinter.LEFT)
        self.tag_config('username', foreground = config.getcolor('username'))
        self.tag_config('time', foreground = config.getcolor('time'))
        self.tag_config('other', foreground = config.getcolor('other'))
        self.tag_config('right', justify = Tkinter.RIGHT)

        # `Show More button'
        self.tag_config('center', justify = Tkinter.CENTER)
        self.tag_config('top', foreground = config.getcolor('more'), spacing1 = 5, spacing3 = 5)
        self.tag_bind('top', '<Button-1>', self.top_more)
        self.tag_config('bottom', foreground = config.getcolor('more'), spacing1 = 5, spacing3 = 5)
        self.tag_bind('bottom', '<Button-1>', self.bottom_more)

        self.mark_set('start', '1.0')
        self.mark_gravity('start', Tkinter.LEFT)
        self.mark_set('head', '1.0')
        self.insert('start', 'Show More\n', ('top', 'center'))
        self.mark_gravity('head', Tkinter.LEFT)

        self.mark_set('stop', Tkinter.END)
        self.mark_set('tail', Tkinter.END)
        self.mark_gravity('tail', Tkinter.LEFT)
        self.insert('stop', 'Show More\n', ('bottom', 'center'))
        self.mark_gravity('tail', Tkinter.RIGHT)

    @staticmethod
    def get_mark(status):
        '''get status mark id'''
        return 's#%08x' % id(status)

    def __insert_status(self, index, status):
        '''insert status to Text widget'''
        self.configure(state = Tkinter.NORMAL)

        mark = self.get_mark(status)
        mark_start = mark + '.start'
        mark_end = mark + '.end'
        tag_text = mark + '.text'
        tag_link = mark + '.link'
        tag_forward = mark + '.forward'
        tag_reply = mark + '.reply'
        self.tag_config(tag_forward, foreground = config.getcolor('button'))
        self.tag_config(tag_reply, foreground = config.getcolor('button'))
        self.tag_config(tag_text, borderwidth = 0)
        if index == 0:
            anchor = 'head'
        else:
            anchor = self.get_mark(self.allStatus[index - 1]) + '.end'
        self.mark_set(mark_start, anchor)
        self.mark_gravity(mark_start, Tkinter.LEFT)
        self.mark_set(mark_end, anchor)

        data = status.parsed
        self.insert(mark_end, data.username, ('text', 'username'))
        self.insert(mark_end, ' at ', ('text', 'other'))
        self.insert(mark_end, utc2str(data.time), ('text', 'time'))
        self.insert(mark_end, '\n  ', ('text', 'other'))
        try:
            text = data.title
        except:
            text = data.text
        self.insert(mark_end, text, 'text')
        if data.has_key('link'):
            self.insert(mark_end, '[link]', (tag_link, 'link'))
            self.tag_bind(tag_link, '<Button-1>', lambda e, link = data.link: webbrowser.open(link))
        self.insert(mark_end, '\n', 'text')

        # action buttons
        self.insert(mark_end, 'forward', (tag_forward, 'right'))
        self.tag_bind(tag_forward, '<Button-1>', lambda e, status = status: gui.forward_status(status))
        self.insert(mark_end, ' | ', ('text', 'other'))
        self.insert(mark_end, 'reply', (tag_reply, 'right'))
        self.tag_bind(tag_reply, '<Button-1>', lambda e, status = status: gui.reply_status(status))
        self.insert(mark_end, ' \n', 'text')

        self.configure(state = Tkinter.DISABLED)

    def insert_status(self, status):
        if status in self.allStatus: return

        self.allStatus.append(status)
        self.allStatus.sort(key = lambda v: v.parsed.time, reverse = True)
        self.__insert_status(self.allStatus.index(status), status)

    def show_status(self, n):
        '''show N status'''
        for s in sp.home_timeline(n, gui.channel):
            self.insert_status(s)

    def top_more(self, event):
        self.show_status(1)

    def bottom_more(self, event):
        n = len(self.allStatus) / len(sp) + 2
        self.show_status(n)


class SNSGui(Tkinter.Frame):
    # check snsapi.platform.platform_list
    PLATFORMS = {
        'email': EMAIL,
        'rss': RSS,
        'rss rw': RSS_RW,
        'rss summary': RSS_SUMMARY,
        'renren blog': RENREN_BLOG,
        'renren share': RENREN_SHARE,
        'renren status': RENREN_STATUS,
        'sqlite': SQLITE,
        'sina weibo': SINA_WEIBO,
        'tencent weibo': TENCENT_WEIBO,
        'twitter': TWITTER,
    }
    def __init__(self, master):
        self.channel = None
        sp.load_config()
        sp.auth()

        Tkinter.Frame.__init__(self, master)
        self.__menus()
        self.__widgets()

    def destroy(self):
        sp.save_config()
        Tkinter.Frame.destroy(self)

    def __menus(self):
        self.channelListMenu = Tkinter.Menu(self, tearoff = False)
        self.channelListMenu.add_command(label = 'All', command = lambda: self.switch_channel(None))
        if len(sp): self.channelListMenu.add_separator()
        for cname in sp.iterkeys():
            self.channelListMenu.add_command(label = cname, command = lambda channel = cname: self.switch_channel(channel))

        self.channelTypeMenu = Tkinter.Menu(self, tearoff = False)
        self.channelTypeMenu.add_separator()
        for label in self.PLATFORMS.iterkeys():
            self.channelTypeMenu.add_command(label = label, command = lambda platform = label: self.add_channel(platform))

        self.moreMenu = Tkinter.Menu(self, tearoff = False)
        self.moreMenu.add_separator()
        self.moreMenu.add_command(label = 'Help', command = self.show_help)
        self.moreMenu.add_command(label = 'About', command = self.show_about)

    def __widgets(self):
        self.topFrame = Tkinter.LabelFrame(self, text = 'Channel')
        self.channelButton = Tkinter.Button(self.topFrame, text = 'All', command = lambda: self.channelListMenu.post(*self.winfo_pointerxy()))
        self.addChannelButton = Tkinter.Button(self.topFrame, text = '+', command = lambda: self.channelTypeMenu.post(*self.winfo_pointerxy()))
        self.postButton = Tkinter.Button(self.topFrame, text = 'Post', command = self.post_status)
        self.moreButton = Tkinter.Button(self.topFrame, text = '...', command = lambda: self.moreMenu.post(*self.winfo_pointerxy()))

        self.topFrame.grid_columnconfigure(2, weight = 1)
        self.channelButton.grid(row = 0, column = 0)
        self.addChannelButton.grid(row = 0, column = 1)
        self.postButton.grid(row = 0, column = 3)
        self.moreButton.grid(row = 0, column = 4)

        self.statusFrame = Tkinter.LabelFrame(self, text = 'Status')
        self.statusList = StatusList(self.statusFrame)
        self.scrollbar = Tkinter.Scrollbar(self.statusFrame, command = self.statusList.yview)
        self.statusList.configure(yscrollcommand = self.scrollbar.set)

        self.statusFrame.grid_rowconfigure(0, weight = 1)
        self.statusFrame.grid_columnconfigure(0, weight = 1)
        self.statusList.grid(row = 0, column = 0, sticky = Tkinter.NSEW)
        self.scrollbar.grid(row = 0, column = 1, sticky = Tkinter.NS)

        self.grid_rowconfigure(1, weight = 1, minsize = 200)
        self.grid_columnconfigure(0, weight = 1, minsize = 200)
        self.topFrame.grid(row = 0, column = 0, sticky = Tkinter.EW)
        self.statusFrame.grid(row = 1, column = 0, sticky = Tkinter.NSEW)

    def show_help(self):
        tkMessageBox.showinfo('Help - ' + TITLE, '''Glossary:
Channel: where Status come from and post to.

Usage:
 * Press `+' button to add a sns channel.
 * Press the Button before `+' to switch channel.
 * Click `Show More' in gray.
 * Press `Post' button to post new Status to current channel.
''')

    def show_about(self):
        tkMessageBox.showinfo('About - ' + TITLE, '''a Tkinter GUI for snsapi

by Alex.wang(iptux7#gmail.com)''')

    def switch_channel(self, channel):
        if self.channel == channel:
            return

        if channel:
            sp.auth(channel)
        cname = channel or 'All'
        self.channel = channel
        self.channelButton.configure(text = cname)

    def add_channel(self, platform):
        channel = NewChannel(self, self.PLATFORMS[platform]).result
        if not channel:
            return

        sp.add_channel(channel)
        if len(sp) == 1: self.channelListMenu.add_separator()
        cname = channel['channel_name']
        self.channelListMenu.add_command(label = cname, command = lambda channel = cname: self.switch_channel(channel))

    def get_post_text(self, title, init_text = ''):
        if not self.channel:
            tkMessageBox.showwarning(TITLE, 'switch to a channel first')
            return
        if sp[self.channel].platform in (RSS, RSS_SUMMARY):
            tkMessageBox.showwarning(TITLE, 'cannot post to RSS channel')
            return

        return TextDialog(self, title, init_text).result

    def post_status(self):
        text = self.get_post_text('Post to channel %s' % self.channel)
        if text:
            sp[self.channel].update(text)

    def reply_status(self, status):
        text = self.get_post_text('Reply to This Status')
        if text:
            sp[status.ID.channel].reply(status.ID, text)

    def forward_status(self, status):
        text = self.get_post_text('Forward Status to %s' % self.channel, 'forward')
        if text:
            sp[self.channel].forward(status, text)


def main():
    global gui, config
    config = SNSGuiConfig()
    root = Tkinter.Tk()
    gui = SNSGui(root)
    gui.pack(expand = True, fill = Tkinter.BOTH)
    root.title(TITLE)
    root.mainloop()


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = test_config
#-*-coding:utf-8-*-

"""
Nosetest configs

The layout of nosetest is learned from:
   wong2/xiaohuangji-new
"""

import os
import glob
import sys
import json
import shutil

DIR_TEST = os.path.abspath(os.path.dirname(__file__))
DIR_TMP = os.path.join(DIR_TEST, "tmp")
DIR_TEST_DATA = os.path.join(DIR_TEST, "data")
DIR_ROOT = os.path.dirname(DIR_TEST)
DIR_CONF = os.path.join(DIR_ROOT, "conf")
DIR_SNSAPI = os.path.join(DIR_ROOT, "snsapi")
DIR_PLUGIN = os.path.join(DIR_SNSAPI, "plugin")
sys.path.append(DIR_ROOT)

WRONG_RESULT_ERROR = "wrong result"
NO_SUCH_KEY_ERROR_TEMPLATE = "no such key: %s"

class TestBase(object):

    @classmethod
    def clean_up(klass, path, wildcard):
        os.chdir(path)
        for rm_file in glob.glob(wildcard):
            os.unlink(rm_file)

    @classmethod
    def setup_class(klass):
        sys.stderr.write("\nRunning %s\n" % klass)
        if not os.path.isdir(DIR_TMP):
            print "makedirs"
            os.makedirs(DIR_TMP)

    @classmethod
    def teardown_class(klass):
        klass.clean_up(DIR_TEST, "*.py?")
        klass.clean_up(DIR_SNSAPI, "*.py?")
        klass.clean_up(DIR_PLUGIN, "*.py?")
        klass.clean_up(DIR_ROOT, "*.py?")
        shutil.rmtree(DIR_TMP)

# ===== old funcs from testUtils.py ======

def get_config_paths():
    '''
    How to get the path of config.json in test directory, Use this.
    '''
    paths = {
            'channel': os.path.join(DIR_CONF, 'channel.json'),
            'snsapi': os.path.join(DIR_CONF, 'snsapi.json')
            }
    return paths

def get_channel(platform):
    paths = get_config_paths()
    with open(paths['channel']) as fp:
        channel = json.load(fp)

    for site in channel:
        if site['platform'] == platform:
            return site

    raise TestInitNoSuchPlatform(platform)

def clean_saved_token():
    import os,glob
    for f in glob.glob('*.token.save'):
        os.remove(f)

class TestInitError(Exception):
    """docstring for TestInitError"""
    def __init__(self):
        super(TestInitError, self).__init__()
    def __str__(self):
        print "Test init error. You may want to check your configs."

class TestInitNoSuchPlatform(TestInitError):
    def __init__(self, platform = None):
        self.platform = platform
    def __str__(self):
        if self.platform is not None:
            print "Test init error -- No such platform : %s. " \
            "Please check your channel.json config. " % self.platform

if __name__ == '__main__':
    print DIR_TEST
    print DIR_ROOT
    print DIR_CONF
    print DIR_SNSAPI
    print get_config_paths()

########NEW FILE########
__FILENAME__ = test_email
# -*- coding: utf-8 -*-

__author__ = 'hupili'
__copyright__ = 'Unlicensed'
__license__ = 'Unlicensed'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from test_config import *
from test_utils import *

from snsapi import snstype
from snsapi.plugin_trial.emails import Email

sys.path = [DIR_TEST] + sys.path

class TestEmail(TestBase):

    def setup(self):
        self.channel = Email(get_data('email-channel-conf.json.test'))
        pass

    def teardown(self):
        self.channel = None
        pass

    def _fake_authed(self):
        self.channel.imap_ok = True
        self.channel.smtp_ok = True

    def test_email_init(self):
        eq_(self.channel.platform, "Email")
        eq_(self.channel.imap, None)
        eq_(self.channel.imap_ok, False)
        eq_(self.channel.smtp, None)
        eq_(self.channel.smtp_ok, False)

    def test_email_new_channel_normal(self):
        nc = Email.new_channel()
        in_('address', nc)
        in_('channel_name', nc)
        in_('imap_host', nc)
        in_('imap_port', nc)
        in_('open', nc)
        in_('password', nc)
        in_('platform', nc)
        in_('smtp_host', nc)
        in_('smtp_port', nc)
        in_('username', nc)

    def test_email_home_timeline_normal(self):
        self._fake_authed()
        self.channel._receive = lambda *al, **ad: get_data('email-_receive.json.test')
        sl = self.channel.home_timeline(1)
        eq_(len(sl), 1)
        # Check common Message fields
        ok_(isinstance(sl[0], snstype.Message))
        in_('username', sl[0].parsed)
        in_('userid', sl[0].parsed)
        in_('time', sl[0].parsed)
        in_('text', sl[0].parsed)
        ok_(isinstance(sl[0].parsed['time'], int))
        # Check email spcific fields
        in_('title', sl[0].parsed)

    def test_email_home_timeline_not_authed(self):
        # All plugin public interfaces do not raise error.
        # Return 'None' when the platform has not been authed.
        eq_(self.channel.home_timeline(), None)

    def _timeline_with_malformed_email_raw_data(self, field, value):
        d = get_data('email-_receive.json.test')[0]
        d[field] = value
        self.channel._receive = lambda *al, **ad: [d]
        return self.channel.home_timeline(1)

    def test_email_home_timeline_malform(self):
        # All plugin public interfaces do not raise error.
        # Return [] if no messages can be parsed.
        self._fake_authed()
        # Irrelevant field: normally return one Message
        ml = self._timeline_with_malformed_email_raw_data('_irrelevant', None)
        eq_(len(ml), 1)

########NEW FILE########
__FILENAME__ = test_renren
# -*- coding: utf-8 -*-

__author__ = 'hupili'
__copyright__ = 'Unlicensed'
__license__ = 'Unlicensed'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from test_config import *
from test_utils import *
from snsapi.plugin_trial import renren

sys.path = [DIR_TEST] + sys.path

class TestRenrenStatus(TestBase):

    def setup(self):
        self.channel = renren.RenrenStatus(get_data('email-channel-conf.json.test'))

    def teardown(self):
        self.channel = None
        pass

    def test_renren_init(self):
        eq_(self.channel.platform, "RenrenStatus")

    def test_renren_new_channel_normal(self):
        nc = renren.RenrenStatus.new_channel()
        in_('channel_name', nc)
        in_('open', nc)
        in_('platform', nc)

    def _fake_authed(self, authed=True):
        self.channel.is_authed = lambda *args, **kwargs: authed

    def _fake_http_json_api_response(self, response):
        self.channel.renren_request = lambda *args, **kwargs: response

    def test_renren_home_timeline_normal(self):
        pass

    def test_renren_home_timeline_abnormal(self):
        # feed type=10 should not return this data structure.
        # There was no such structure when we initiated snsapi.
        # The bug was found on June 22, 2013.
        # 'renren-feed-status-2.json.test' contains such a case.
        # We have to make the message parse more robust.
        self._fake_authed()
        self._fake_http_json_api_response(get_data('renren-feed-status-2.json.test'))
        ht = self.channel.home_timeline()
        eq_(len(ht), 1)
        eq_(ht[0].parsed['text'], 'message "title" ')
        eq_(ht[0].parsed['username'], 'user5')
        eq_(ht[0].parsed['userid'], '6666')

    def renren_request_return_api_error(self, **kwargs):
        raise renren.RenrenAPIError(9999999, 'this is a fake error')

    def test_renren_status_update(self):
        self._fake_authed()
        self.channel.renren_request = self.renren_request_return_api_error
        eq_(self.channel.update('test status'), False)


########NEW FILE########
__FILENAME__ = test_rss
# -*- coding: utf-8 -*-

__author__ = 'hupili'
__copyright__ = 'Unlicensed'
__license__ = 'Unlicensed'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from test_config import *
from test_utils import *

from snsapi import snstype
from snsapi.plugin import rss

sys.path = [DIR_TEST] + sys.path

class TestRSS(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

class TestRSSSummary(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

class TestRSS2RW(TestBase):

    def setup(self):
        _url = os.path.join(DIR_TMP, "_test_rss.xml")
        channel_conf = {
          "url": _url,
          "channel_name": "test_rss",
          "open": "yes",
          "platform": "RSS2RW"
        }
        self.rss = rss.RSS2RW(channel_conf)

    def teardown(self):
        _url = self.rss.jsonconf.url
        import os
        if os.path.isfile(_url):
            os.unlink(_url)
        del self.rss

    def test_rss2rw_update_text_str(self):
        import time
        _time1 = int(time.time())
        # Execution takes time
        self.rss.update('test status')
        _time2 = int(time.time())
        msg = self.rss.home_timeline()[0]
        ok_(msg.parsed.time >= _time1 and msg.parsed.time <= _time2)
        eq_(msg.parsed.text, 'test status')
        # The default settings
        eq_(msg.parsed.username, 'snsapi')
        eq_(msg.parsed.userid, 'snsapi')

    def test_rss2rw_update_text_unicode(self):
        import time
        _time1 = int(time.time())
        # Execution takes time
        self.rss.update(u'test status unicode')
        _time2 = int(time.time())
        msg = self.rss.home_timeline()[0]
        ok_(msg.parsed.time >= _time1 and msg.parsed.time <= _time2)
        eq_(msg.parsed.text, 'test status unicode')
        # The default settings
        eq_(msg.parsed.username, 'snsapi')
        eq_(msg.parsed.userid, 'snsapi')

    def test_rss2rw_update_text_with_author(self):
        self.rss.jsonconf.author = 'test_author'
        import time
        _time1 = int(time.time())
        # Execution takes time
        self.rss.update('test status')
        _time2 = int(time.time())
        msg = self.rss.home_timeline()[0]
        ok_(msg.parsed.time >= _time1 and msg.parsed.time <= _time2)
        eq_(msg.parsed.text, 'test status')
        # The default settings
        eq_(msg.parsed.username, 'test_author')
        eq_(msg.parsed.userid, 'test_author')

    def test_rss2rw_update_message(self):
        import time
        # Use the generic Message instead of RSS2RW.Message
        msg = snstype.Message()
        msg.parsed.username = "test_username"
        # Current RSS feeds do not distinguish userid and username
        # In the future, userid may be coded into our special structure
        msg.parsed.userid = "test_username"
        msg.parsed.time = int(time.time())
        msg.parsed.text = "test status"
        self.rss.update(msg)
        msg2 = self.rss.home_timeline()[0]
        eq_(msg.parsed.time, msg2.parsed.time)
        eq_(msg.parsed.username, msg2.parsed.username)
        eq_(msg.parsed.userid, msg2.parsed.userid)
        eq_(msg.parsed.text, msg2.parsed.text)

    def test_rss2rw_update_message_timeout_append(self):
        # We can not make the RSS feed go arbitrary long.
        # Timeout-ed entried will be deleted upon every update operation.
        # This UT tests the behaviour when appending a timeout-ed item.
        import time
        _cur_time = int(time.time())
        # Use the generic Message instead of RSS2RW.Message
        msg = snstype.Message()
        msg.parsed.username = "test_username"
        msg.parsed.userid = "test_username"
        msg.parsed.time = _cur_time
        msg.parsed.text = "test status"

        self.rss.update(msg)
        self.rss.update(msg)
        eq_(len(self.rss.home_timeline()), 2)

        self.rss.update(msg)
        eq_(len(self.rss.home_timeline()), 3)

        # 1 second before timeout
        msg.parsed.time -= self.rss.jsonconf.entry_timeout - 1
        self.rss.update(msg)
        eq_(len(self.rss.home_timeline()), 4)

        # 1 second after timeout
        # Should reject this entry
        msg.parsed.time -= 2
        self.rss.update(msg)
        eq_(len(self.rss.home_timeline()), 4)

    def test_rss2rw_update_message_timeout_simulate(self):
        # This UT simulates a timeout scenario
        import time
        _cur_time = int(time.time())
        # Use the generic Message instead of RSS2RW.Message
        msg = snstype.Message()
        msg.parsed.username = "test_username"
        msg.parsed.userid = "test_username"
        msg.parsed.time = _cur_time
        msg.parsed.text = "test status"

        # Normal update
        self.rss.update(msg)
        eq_(len(self.rss.home_timeline()), 1)

        # Change our timer
        _new_time = _cur_time + self.rss.jsonconf.entry_timeout + 1
        time.time = lambda : _new_time
        msg.parsed.time = int(time.time())
        self.rss.update(msg)
        # The previous message is kicked out
        eq_(len(self.rss.home_timeline()), 1)

    def test_rss2rw_update_message_make_link(self):
        # Check the link is correctly generated
        # See ``_make_link`` for more info.
        # None: no timeout; keep all entries permanently
        self.rss.jsonconf.entry_timeout = None
        msg = snstype.Message()
        msg.parsed.username = "test_username"
        msg.parsed.userid = "test_username"
        msg.parsed.text = "test status"
        msg.parsed.time = 1234567890
        self.rss.update(msg)
        msg2 = self.rss.home_timeline()[0]
        eq_(msg2.parsed.link, 'http://goo.gl/7aokV#a6dd6e622b2b4f01065b6abe47571a33423a16ea')

########NEW FILE########
__FILENAME__ = test_snsapi_utils
# -*- coding: utf-8 -*-

__author__ = 'hupili'
__copyright__ = 'Unlicensed'
__license__ = 'Unlicensed'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from test_config import *
from test_utils import *

sys.path = [DIR_TEST] + sys.path

class TestSNSAPIUtils(TestBase):
    pass

class TestTimeConversion(TestBase):

    def setup(self):
        import snsapi
        reload(snsapi)
        from snsapi import utils as snsapi_utils
        reload(snsapi_utils)
        self.su = snsapi_utils

    def teardown(self):
        pass

    def test_str2utc_normal(self):
        #TODO:
        #    More variants. Make sure the str date can be parsed.
        #eq_(self.su.str2utc('Wed Jun 26 16:06:57 HKT 2013'), 1372234017)
        #eq_(self.su.str2utc('Wed Jun 26 16:06:57 2013 HKT'), 1372234017)
        eq_(self.su.str2utc('Wed Jun 26 16:06:57 2013 +8:00'), 1372234017)
        eq_(self.su.str2utc('Wed Jun 26 16:06:57 2013 +08:00'), 1372234017)

    def test_str2utc_with_correction(self):
        # One sample time string returned by Renren
        # Test with Timezone Correction (TC):
        eq_(self.su.str2utc('2013-06-26 16:13:02', tc='+08:00'), 1372234382)
        # Test without Timezone Correction (TC): 8 hours late than correct time
        eq_(self.su.str2utc('2013-06-26 16:13:02'), 1372263182)

    def _utc2str_and_str2utc(self, utc):
        _str = self.su.utc2str(utc)
        print _str
        return self.su.str2utc(_str)

    def test_utc2str_normal(self):
        # We make the RFC822 compliant time string
        # Since the formatting depends on the TZ of current machine,
        # we can only test the reflection between 'utc2str' and 'str2utc'
        eq_(self._utc2str_and_str2utc(1372234235), 1372234235)
        eq_(self._utc2str_and_str2utc(1172234235), 1172234235)
        import time
        _utc = int(time.time())
        eq_(self._utc2str_and_str2utc(_utc), _utc)
        #from dateutil import parser as dtparser, tz
        #eq_(snsapi_utils.utc2str(1372234235), 'Wed, 26 Jun 2013 16:10:35 HKT')

class TestTimeConversionBadTZ(TestBase):
    def setup(self):
        from dateutil import tz
        self.__tzlocal = tz.tzlocal
        tz.tzlocal = self._raise_exception

        import snsapi
        reload(snsapi)
        from snsapi import utils as snsapi_utils
        reload(snsapi_utils)
        self.su = snsapi_utils

    def teardown(self):
        from dateutil import tz
        tz.tzlocal = self.__tzlocal

    def _raise_exception(self):
        # Simulate Issue #36
        raise Exception('Simulated Exception for Issue #36')

    def test_utc2str_bad_tz(self):
        # The test case for Issue #36
        # On some windows platforms, tz.tzlocal() fails
        import time
        _utc = int(time.time())
        _str = self.su.utc2str(_utc)
        print _str
        eq_(self.su.str2utc(_str), _utc)


########NEW FILE########
__FILENAME__ = test_snsbase
# -*- coding: utf-8 -*-

__author__ = 'hupili'
__copyright__ = 'Unlicensed'
__license__ = 'Unlicensed'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from test_config import *
from test_utils import *

import snsapi
from snsapi.snsbase import SNSBase

sys.path = [DIR_TEST] + sys.path

class TestSNSBase(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_snsbase_new_channel_normal(self):
        nc = SNSBase.new_channel()
        eq_(2, len(nc), WRONG_RESULT_ERROR)
        in_('channel_name', nc)
        in_('open', nc)

    def test_snsbase_new_channel_full(self):
        nc = SNSBase.new_channel(full=True)
        eq_(7, len(nc), WRONG_RESULT_ERROR)
        in_('channel_name', nc)
        in_('open', nc)
        in_('description', nc)
        in_('methods', nc)
        in_('user_name', nc)
        in_('user_id', nc)

    def _build_sns_with_token(self, seconds_after_current_time):
        from snsapi.utils import JsonDict
        import time
        token = JsonDict()
        token.expires_in = time.time() + seconds_after_current_time
        sns = SNSBase()
        sns.token = token
        return sns

    def test_snsbase_expire_after_1(self):
        # Before expiration
        gt_(self._build_sns_with_token(2).expire_after(), 1.5)
        gt_(self._build_sns_with_token(20).expire_after(), 19.5)

    def test_snsbase_expire_after_2(self):
        # On or after expiration
        eq_(self._build_sns_with_token(0).expire_after(), 0)
        eq_(self._build_sns_with_token(-2).expire_after(), 0)
        eq_(self._build_sns_with_token(-20).expire_after(), 0)

    def test_snsbase_expire_after_3(self):
        # Token not exist, consider as expired.
        eq_(SNSBase().expire_after(), 0)

    def test_snsbase_is_expired(self):
        nok_(self._build_sns_with_token(2).is_expired())
        ok_(self._build_sns_with_token(-2).is_expired())

    def test_snsbase_is_authed(self):
        ok_(self._build_sns_with_token(2).is_authed())
        nok_(self._build_sns_with_token(-2).is_authed())

    def _parse_code_ok(self, url, code):
        sns = SNSBase()
        token = sns._parse_code(url)
        ok_(isinstance(token, snsapi.utils.JsonDict))
        eq_(token.code, code)

    def test__parse_code(self):
        # Sina example
        self._parse_code_ok('http://copy.the.code.to.client/?code=b5ffaed78a284a55e81ffe142c4771d9', 'b5ffaed78a284a55e81ffe142c4771d9')
        # Tencent example
        self._parse_code_ok('http://copy.the.code.to.client/?code=fad92807419b5aac433c4128A05e1Cad&openid=921CFC3AF04d76FE59D98a2029D0B978&openkey=6C2FCABD153B18625BAAB1BA206EF2C6', 'fad92807419b5aac433c4128A05e1Cad')

    def _expand_url_ok(self, url, expected_url):
        sns = SNSBase()
        ex_url = sns._expand_url(url)
        eq_(ex_url, expected_url)

    def test__expand_url(self):
        SNSAPI_GH_URL = 'https://github.com/hupili/snsapi'
        # Sina short url
        self._expand_url_ok('http://t.cn/zQvXHkz', SNSAPI_GH_URL)
        # Renren short url
        self._expand_url_ok('http://rrurl.cn/6Apm7B', SNSAPI_GH_URL)
        # Tencent short url
        self._expand_url_ok('http://url.cn/IM0GaW', SNSAPI_GH_URL)

########NEW FILE########
__FILENAME__ = test_snstype
from test_config import *
from test_utils import *

import snsapi
from snsapi.snstype import BooleanWrappedData

sys.path = [DIR_TEST] + sys.path

class TestSNSType(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_snstype_boolean_wrapped(self):
        false_wrapped = BooleanWrappedData(False)
        true_wrapped = BooleanWrappedData(True)
        ok_(true_wrapped == True)
        ok_(true_wrapped != False)
        ok_(false_wrapped == False)
        ok_(false_wrapped != True)
        ok_(true_wrapped)
        ok_(not false_wrapped)

########NEW FILE########
__FILENAME__ = test_utils
#-*-coding:utf-8-*-

"""
Test utils

   * Original nose tools
     https://nose.readthedocs.org/en/latest/testing_tools.html
   * We provide other shortcuts in this module.
   * Other test_xxx.py should use this module as the entry to tools.
"""

from nose.tools import ok_, eq_, raises
from test_config import NO_SUCH_KEY_ERROR_TEMPLATE
from test_config import DIR_TEST_DATA
from test_config import WRONG_RESULT_ERROR
import json
import os.path

def in_(k, dct):
    '''
    Helper function to assert a key is in a dict. The naming
    is following nose's format.

    :param k: Key
    :type k: str
    :param dct: Dict
    :type dct: dict

    '''
    ok_((k in dct), NO_SUCH_KEY_ERROR_TEMPLATE % (k))

def gt_(a, b):
    '''
    Helper function to assert ``a`` is greater than ``b``

    :type a,b: Any comparable type

    '''
    ok_((a > b), WRONG_RESULT_ERROR)

def nok_(v):
    '''
    Helper function to assert Not-OK (NOK)

    :type v: Boolean

    '''
    ok_(not v)

def get_data(filename):
    return json.load(open(os.path.join(DIR_TEST_DATA, filename), 'r'))

def get_str(filename):
    return open(os.path.join(DIR_TEST_DATA, filename), 'r')

########NEW FILE########
