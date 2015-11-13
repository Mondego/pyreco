__FILENAME__ = delicious_import
#!/usr/bin/env python

"""Imports delicious.com links into Tumblr.

- get all your delicious.com links into a file:

    curl -u user:password \
        'https://api.del.icio.us/v1/posts/all?meta=yes' >links.xml

- if curl is missing:
  open the above URL in a browser and save the resulting page as "links.xml"
- run this script to post the links to Tumblr
- delete your delicious.com account

The link's timestamp, tags and privacy flag are kept.

XML format of a link:

<post description="The problem with Django's Template Tags"
    extended="My reply"
    hash="ec46dd48f9b117f2adc8d7b10b8356d7"
    href="http://ericholscher.com/blog/2008/nov/8/problem-django-template-tags/"
    meta="28717456b732b4117631ff27fd959708"
    private="yes" shared="no" tag="reply django templetetags"
    time="2008-12-04T07:33:25Z"
/>
"""

import sys
import os
import getopt
import urllib
import urllib2
import netrc
from time import strptime, sleep
from datetime import datetime
from calendar import timegm

import xmltramp

DEBUG = False

HOST = 'www.tumblr.com'

def tumble(links):
    auth = netrc.netrc().authenticators(HOST)
    if auth is not None:
        auth = {'email': auth[0], 'password': auth[2]}
        return [post(auth, e) for e in links]

def post(auth, link):
    ''
    data = {'type': 'link', 'url': link('href'), 'name': link('description')}
    if link('private') == 'yes':
        data['private'] = '1'
    ext = link('extended')
    if ext:
        data['description'] = ext
    tags = link('tag')
    if tags:
        data['tags'] = ','.join('"%s"' % t for t in tags.split())
    t = datetime.fromtimestamp(timegm(strptime(link('time'), '%Y-%m-%dT%H:%M:%SZ')))
    data['date'] = t.isoformat(' ')

    if DEBUG:
        return 'debug', data

    data.update(auth)
    for k in data:
        if type(data[k]) is unicode:
            data[k] = data[k].encode('utf-8')

    sleep(2)
    print data['url']
    try:
        return 'ok', urllib2.urlopen('http://' + HOST + '/api/write', urllib.urlencode(data)).read()
    except Exception, e:
        return 'error', repr(e)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd')
    except:
        print "Usage: %s [-d]" % sys.argv[0].split(os.sep)[-1]
        sys.exit(1)
    for o, v in opts:
        if o == '-d':
            DEBUG = True
    links = xmltramp.parse(open('links.xml').read())
    result = tumble(links)
    if result:
        import pprint
        pprint.pprint(result)
        if 'error' in [r[0] for r in result]:
            sys.exit(2)
    sys.exit(0)

########NEW FILE########
__FILENAME__ = mail_export
#!/usr/bin/env python

"""E-mails a user's recent Tumblr links to recipients.

I use this to automate the distribution of interesting links to
my geek-buddies mailing list.

- tag your links with a special tag
- run this script with your tumblr blog name, this tag and the recipient(s)
  as arguments every hour or so

The script needs write permissions in /var/local to save the ID of the
most recently mailed link. This ID is saved independently per user and tag.
"""

# configuration
SMTP_SERVER = 'localhost'
SENDER = 'bbolli@ewanet.ch'


import urllib
import urlparse
import re
import smtplib
import textwrap
from email.mime.text import MIMEText
try:
    import json
except ImportError:
    # Python 2.5 and earlier need this package
    import simplejson as json


class TumblrToMail:

    def __init__(self, user, tag, recipients):
        self.user = self.domain = user
        if '.' not in self.domain:
            self.domain += '.tumblr.com'
        self.tag = tag
        self.recipients = recipients
        self.db_file = '/var/local/tumblr_mail.latest'
        self.db_key = (user, tag)
        try:
            self.db = eval(open(self.db_file).read(), {}, {})
        except (IOError, OSError):
            self.db = {}
        self.latest = self.db.get(self.db_key, 0)
        self.lw = textwrap.TextWrapper(initial_indent='* ', subsequent_indent='  ',
            break_long_words=False, break_on_hyphens=False
        )
        self.tw = textwrap.TextWrapper(initial_indent='  ', subsequent_indent='  ')

    def __del__(self):
        if self.latest:
            self.db[self.db_key] = self.latest
            open(self.db_file, 'w').write(repr(self.db))

    def get_links(self):
        url = 'http://%s/api/read/json?type=link&filter=text' % self.domain
        posts = urllib.urlopen(url).read()
        posts = re.sub(r'^.*?(\{.*\});*$', r'\1', posts)   # extract the JSON structure
        try:
            posts = json.loads(posts)
        except ValueError:
            print posts
            return []
        return [
            p for p in posts['posts']
            if int(p['id']) > self.latest and self.tag in p.get('tags', [])
        ]

    def make_mail(self, link):
        url = list(urlparse.urlsplit(link['link-url']))
        url[2] = urllib.quote(url[2])
        mail = self.lw.fill(u'%s: %s' % (link['link-text'], urlparse.urlunsplit(url)))
        desc = link['link-description']
        if desc:
            mail += '\n\n' + self.tw.fill(desc)
        return mail

    def run(self, options):
        links = self.get_links()
        if not links:
            return

        body = ('\n\n'.join(self.make_mail(l) for l in links)).strip() + """

-- 
http://%s
""" % self.domain

        self.latest = max(int(l['id']) for l in links) if not options.dry_run else None

        if not self.recipients and not options.full:
            print body
            return

        msg = MIMEText(body.encode('utf-8'))
        msg.set_charset('utf-8')
        msg['Subject'] = "Interesting links" if len(links) > 1 else links[0]['link-text']
        msg['From'] = '%s (%s)' % (SENDER, self.user)
        if self.recipients:
            msg['To'] = ', '.join(self.recipients)

        if options.full:
            print msg.as_string()
            return

        smtp = smtplib.SMTP(SMTP_SERVER)
        smtp.sendmail(SENDER, self.recipients, msg.as_string())
        smtp.quit()


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser("Usage: %prog [options] blog-name tag [recipient ...]",
        description="Sends an email generated from tagged link posts.",
        epilog="Without recipients, prints the mail body to stdout."
    )
    parser.add_option('-d', '--dry-run', action='store_true',
        help="don't save which link was sent last"
    )
    parser.add_option('-f', '--full', action='store_true',
        help="print the full mail with headers to stdout"
    )
    options, args = parser.parse_args()
    try:
        user = args[0]
        tag = args[1]
        recipients = args[2:]
    except IndexError:
        parser.error("blog-name and tag are required arguments.")

    TumblrToMail(user, tag, recipients).run(options)

########NEW FILE########
__FILENAME__ = oauth
import sys
import urlparse
import oauth2 as oauth
import urllib

consumer_key = sys.argv[1]
consumer_secret = sys.argv[2]

request_token_url = 'http://www.tumblr.com/oauth/request_token'
access_token_url = 'http://www.tumblr.com/oauth/access_token'
authorize_url = 'http://www.tumblr.com/oauth/authorize'

consumer = oauth.Consumer(consumer_key, consumer_secret)
client = oauth.Client(consumer)

# Step 1: Get a request token. This is a temporary token that is used for
# having the user authorize an access token and to sign the request to obtain
# said access token.

resp, content = client.request(request_token_url, "POST",
    body=urllib.urlencode({"oauth_callback": "http://www.tumblr.com/omgwtf"})
)
if resp['status'] != '200':
    raise Exception("Invalid response %s." % resp['status'])

request_token = dict(urlparse.parse_qsl(content))

print "Request Token:"
print "    - oauth_token        = %s" % request_token['oauth_token']
print "    - oauth_token_secret = %s\n" % request_token['oauth_token_secret']

# Step 2: Redirect to the provider. Since this is a CLI script we do not
# redirect. In a web application you would redirect the user to the URL
# below.

print "Go to the following link in your browser:"
print "%s?%s\n" % (authorize_url, urllib.urlencode({
    "oauth_token": request_token['oauth_token'],
    "oauth_callback": 'http://localhost/doctorstrange'
}))

# After the user has granted access to you, the consumer, the provider will
# redirect you to whatever URL you have told them to redirect to. You can
# usually define this in the oauth_callback argument as well.
accepted = 'n'
while accepted.lower() == 'n':
    accepted = raw_input('Have you authorized me? (y/n) ')
    oauth_verifier = raw_input('What is the OAuth Verifier? ')

# Step 3: Once the consumer has redirected the user back to the oauth_callback
# URL you can request the access token the user has approved. You use the
# request token to sign this request. After this is done you throw away the
# request token and use the access token returned. You should store this
# access token somewhere safe, like a database, for future use.
token = oauth.Token(
    request_token['oauth_token'], request_token['oauth_token_secret']
)
token.set_verifier(oauth_verifier)
client = oauth.Client(consumer, token)

resp, content = client.request(access_token_url, "POST")
access_token = dict(urlparse.parse_qsl(content))

print "Access Token:"
print "    - oauth_token        = %s" % access_token['oauth_token']
print "    - oauth_token_secret = %s" % access_token['oauth_token_secret']
print
print "You may now access protected resources using the access tokens above.\n"

########NEW FILE########
__FILENAME__ = tumble
#!/usr/bin/env python

"""Read a feed from stdin and post its entries to tumblr.

Options:
    -b sub-blog         Post to a sub-blog of your account.
    -e post-id          Edit the existing post with the given ID.
                        This only looks at the first entry of the feed.
    -d                  Debug mode: print the raw post data instead
                        of posting it to tumblr.com.
"""

"""Authorization is handled via OAuth. Prepare the file ~/.config/tumblr
with 5 lines:

    - your default blog name
    - the consumer key
    - the consumer secret
    - the access token
    - the access secret

You get these values by registering for a new application on the tumblr
developer site and running the included oauth.py with the consumer key and
secret as arguments to get an access token and secret.

Non-standard Python dependencies:
    - simplejson (http://pypi.python.org/pypi/simplejson/; for Python <= 2.6)
    - oauth2 (http://pypi.python.org/pypi/oauth2/)
    - httplib2 (http://pypi.python.org/pypi/httplib2/)
"""

import sys
import os
import getopt
import urllib
from datetime import datetime
from calendar import timegm
try:
    import simplejson as json   # for Python <= 2.6
except ImportError:
    import json

import oauth2 as oauth
import feedparser

URL_FMT = 'http://api.tumblr.com/v2/blog/%s/post'
CONFIG = '~/.config/tumblr'


class Tumble:

    def __init__(self, config_file):
        (
            self.blog,
            self.consumer_token, self.consumer_secret,
            self.access_token, self.access_secret
        ) = (s.strip() for s in open(config_file))
        self.post_id = None
        self.debug = False

    def tumble(self, feed):
        feed = feedparser.parse(feed)
        if self.post_id:
            return [self.post(feed.entries[0])]
        else:
            return [self.post(e) for e in feed.entries]

    def post(self, entry):
        # the first enclosure determines the media type
        enc = entry.get('enclosures', [])
        if enc:
            enc = enc[0]
        if enc and enc.type.startswith('image/'):
            data = {
                'type': 'photo', 'source': enc.href,
                'caption': entry.title, 'link': entry.link
            }
        elif enc and enc.type.startswith('audio/'):
            data = {
                'type': 'audio', 'caption': entry.title, 'external-url': enc.href
            }
        elif 'link' in entry and entry.link:
            data = {'type': 'link', 'url': entry.link, 'title': entry.title}
            if 'content' in entry:
                data['description'] = entry.content[0].value
            elif 'summary' in entry:
                data['description'] = entry.summary
        elif 'content' in entry:
            data = {'type': 'text', 'title': entry.title, 'body': entry.content[0].value}
        elif 'summary' in entry:
            data = {'type': 'text', 'title': entry.title, 'body': entry.summary}
        else:
            return 'unknown', entry
        if 'tags' in entry:
            data['tags'] = ','.join('"%s"' % t.term for t in entry.tags)
        for d in ('published_parsed', 'updated_parsed'):
            if d in entry:
                pub = datetime.fromtimestamp(timegm(entry.get(d)))
                data['date'] = pub.isoformat(' ')
                break

        if not '.' in self.blog:
            self.blog += '.tumblr.com'
        url = URL_FMT % self.blog
        if self.post_id:
            data['id'] = self.post_id
            op = 'edit'
            url += '/edit'
        else:
            op = 'post'
        if self.debug:
            return dict(url=url, entry=entry, data=data)

        for k in data:
            if type(data[k]) is unicode:
                data[k] = data[k].encode('utf-8')

        # do the OAuth thing
        consumer = oauth.Consumer(self.consumer_token, self.consumer_secret)
        token = oauth.Token(self.access_token, self.access_secret)
        client = oauth.Client(consumer, token)
        try:
            headers, resp = client.request(url, method='POST', body=urllib.urlencode(data))
            resp = json.loads(resp)
        except ValueError, e:
            return 'error', 'json', resp
        except Exception, e:
            return 'error', str(e)
        if resp['meta']['status'] in (200, 201):
            return op, str(resp['response']['id'])
        else:
            return 'error', headers, resp

if __name__ == '__main__':
    try:
        t = Tumble(os.path.expanduser(CONFIG))
    except:
        sys.stderr.write('Config file %s not found or not readable\n' % CONFIG);
        sys.exit(1)
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hb:e:d')
    except:
        print "Usage: %s [-b blog-name] [-e post-id] [-d]" % sys.argv[0].split(os.sep)[-1]
        sys.exit(1)
    for o, v in opts:
        if o == '-h':
            print __doc__.strip()
            sys.exit(0)
        if o == '-b':
            t.blog = v
        elif o == '-e':
            t.post_id = v
        elif o == '-d':
            t.debug = True
    result = t.tumble(sys.stdin)
    if result:
        import pprint
        pprint.pprint(result)
        if not t.debug and 'error' in [r[0] for r in result]:
            sys.exit(2)
    sys.exit(0)

########NEW FILE########
__FILENAME__ = tumblr_backup
#!/usr/bin/env python
# encoding: utf-8

# standard Python library imports
from __future__ import with_statement
import os
from os.path import join, split, splitext
import sys
import urllib
import urllib2
from xml.sax.saxutils import escape
from xml.sax import SAXException
import codecs
import imghdr
from collections import defaultdict
import time
import locale
from glob import glob
import re

# extra required packages
import xmltramp

# extra optional packages
try:
    import pyexiv2
except ImportError:
    pyexiv2 = None

# default blog name(s)
DEFAULT_BLOGS = ['bbolli']

# Format of displayed tags
TAG_FMT = '#%s'

# Format of tag link URLs; set to None to suppress the links.
# Named placeholders that will be replaced: domain, tag
TAGLINK_FMT = 'http://%(domain)s/tagged/%(tag)s'

# add another JPEG recognizer
# see http://www.garykessler.net/library/file_sigs.html
def test_jpg(h, f):
    if h[:3] == '\xFF\xD8\xFF' and h[3] in "\xDB\xE0\xE1\xE2\xE3":
        return 'jpg'

imghdr.tests.append(test_jpg)

# variable directory names, will be set in TumblrBackup.backup()
save_folder = ''
image_folder = ''

# constant names
root_folder = os.getcwdu()
post_dir = 'posts'
xml_dir = 'xml'
image_dir = 'images'
archive_dir = 'archive'
theme_dir = 'theme'
save_dir = '../'
backup_css = 'backup.css'
custom_css = 'custom.css'
avatar_base = 'avatar'
dir_index = 'index.html'

blog_name = ''
post_ext = '.html'
have_custom_css = False

MAX_POSTS = 50

# ensure the right date/time format
try:
    locale.setlocale(locale.LC_TIME, '')
except locale.Error:
    pass
encoding = 'utf-8'
time_encoding = locale.getlocale(locale.LC_TIME)[1] or encoding

def log(account, s):
    if not options.quiet:
        if account:
            sys.stdout.write('%s: ' % account)
        sys.stdout.write(s[:-1] + ' ' * 20 + s[-1:])
        sys.stdout.flush()

def mkdir(dir, recursive=False):
    if not os.path.exists(dir):
        if recursive:
            os.makedirs(dir)
        else:
            os.mkdir(dir)

def path_to(*parts):
    return join(save_folder, *parts)

def open_file(open_fn, parts):
    if len(parts) > 1:
        mkdir(path_to(*parts[:-1]), (len(parts) > 2))
    return open_fn(path_to(*parts))

def open_text(*parts):
    return open_file(
        lambda f: codecs.open(f, 'w', encoding, 'xmlcharrefreplace'), parts
    )

def open_image(*parts):
    return open_file(lambda f: open(f, 'wb'), parts)

def strftime(format, t=None):
    if t is None:
        t = time.localtime()
    return time.strftime(format, t).decode(time_encoding)

def get_api_url(account):
    """construct the tumblr API URL"""
    global blog_name
    blog_name = account
    if '.' not in account:
        blog_name += '.tumblr.com'
    base = 'http://' + blog_name + '/api/read'
    if options.private:
        password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, base, '', options.private)
        auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)
        opener = urllib2.build_opener(auth_manager)
        urllib2.install_opener(opener)
    return base

def set_period():
    """Prepare the period start and end timestamps"""
    i = 0; tm = [int(options.period[:4]), 1, 1, 0, 0, 0, 0, 0, -1]
    if len(options.period) >= 6:
        i = 1; tm[1] = int(options.period[4:6])
    if len(options.period) == 8:
        i = 2; tm[2] = int(options.period[6:8])
    options.p_start = time.mktime(tm)
    tm[i] += 1
    options.p_stop = time.mktime(tm)

def xmlparse(base, count, start=0):
    params = {'num': count}
    if start > 0:
        params['start'] = start
    url = base + '?' + urllib.urlencode(params)
    for _ in range(10):
        try:
            resp = urllib2.urlopen(url)
        except (urllib2.URLError, urllib2.HTTPError) as e:
            sys.stderr.write('%s getting %s\n' % (e, url))
            continue
        if resp.info().gettype() == 'text/xml':
            break
    else:
        return None
    xml = resp.read()
    try:
        doc = xmltramp.parse(xml)
    except SAXException as e:
        sys.stderr.write('%s: %s\n%d %s %s\n%r\n' % (
            e.__class__.__name__, e, resp.getcode(), resp.msg, resp.info().gettype(), xml
        ))
        return None
    return doc if doc._name == 'tumblr' else None

def add_exif(image_name, tags):
    try:
        metadata = pyexiv2.ImageMetadata(image_name)
        metadata.read()
    except:
        sys.stderr.write('Error reading metadata for image %s\n' % image_name)
        return
    KW_KEY = 'Iptc.Application2.Keywords'
    if '-' in options.exif:     # remove all tags
        if KW_KEY in metadata.iptc_keys:
            del metadata[KW_KEY]
    else:                       # add tags
        if KW_KEY in metadata.iptc_keys:
            tags |= set(metadata[KW_KEY].value)
        tags = list(tag.strip().lower() for tag in tags | options.exif if tag)
        metadata[KW_KEY] = pyexiv2.IptcTag(KW_KEY, tags)
    try:
        metadata.write()
    except:
        sys.stderr.write('Writing metadata failed for tags: %s in: %s\n' % (tags, image_name))

def save_style():
    with open_text(backup_css) as css:
        css.write('''\
body { width: 720px; margin: 0 auto; }
img { max-width: 720px; }
blockquote { margin-left: 0; border-left: 8px #999 solid; padding: 0 24px; }
.archive h1, .subtitle, article { padding-bottom: 0.75em; border-bottom: 1px #ccc dotted; }
.post a.llink { display: none; }
.meta a { text-decoration: none; }
body > img { float: right; }
.tags, .tags a { font-size: small; color: #999; text-decoration: none; }
''')

def header(heading, title='', body_class='', subtitle='', avatar=''):
    root_rel = '' if body_class == 'index' else save_dir
    css_rel = root_rel + (custom_css if have_custom_css else backup_css)
    if body_class:
        body_class = ' class=' + body_class
    h = u'''<!DOCTYPE html>

<meta charset=%s>
<title>%s</title>
<link rel=stylesheet href=%s>

<body%s>

''' % (encoding, heading, css_rel, body_class)
    if avatar:
        h += '<img src=%s%s/%s alt=Avatar>\n' % (root_rel, theme_dir, avatar)
    if title:
        h += u'<h1>%s</h1>\n' % title
    if subtitle:
        h += u'<p class=subtitle>%s</p>\n' % subtitle
    return h

def get_avatar():
    try:
        resp = urllib2.urlopen('http://api.tumblr.com/v2/blog/%s/avatar' % blog_name)
        avatar_data = resp.read()
    except:
        return
    avatar_file = avatar_base + '.' + imghdr.what(None, avatar_data[:32])
    with open_image(theme_dir, avatar_file) as f:
        f.write(avatar_data)

def get_style():
    """Get the blog's CSS by brute-forcing it from the home page.
    The v2 API has no method for getting the style directly.
    See https://groups.google.com/d/msg/tumblr-api/f-rRH6gOb6w/sAXZIeYx5AUJ"""
    try:
        resp = urllib2.urlopen('http://%s/' % blog_name)
        page_data = resp.read()
    except:
        return
    match = re.search(r'(?s)<style type=.text/css.>(.*?)</style>', page_data)
    if match:
        css = match.group(1).strip().decode(encoding, 'replace')
        if not css:
            return
        css = css.replace('\r', '').replace('\n    ', '\n')
        with open_text(theme_dir, 'style.css') as f:
            f.write(css + '\n')


class TumblrBackup:

    def __init__(self):
        self.total_count = 0

    def build_index(self):
        filter = join('*', dir_index) if options.dirs else '*' + post_ext
        for f in glob(path_to(post_dir, filter)):
            post = LocalPost(f)
            self.index[post.tm.tm_year][post.tm.tm_mon].append(post)

    def save_index(self):
        f = glob(path_to(theme_dir, avatar_base + '.*'))
        avatar = split(f[0])[1] if f else None
        with open_text(dir_index) as idx:
            idx.write(header(self.title, self.title, body_class='index',
                subtitle=self.subtitle, avatar=avatar
            ))
            for year in sorted(self.index.keys(), reverse=options.reverse_index):
                self.save_year(idx, year)
            idx.write('<p>Generated on %s.</p>\n' % strftime('%x %X'))

    def save_year(self, idx, year):
        idx.write('<h3>%s</h3>\n<ul>\n' % year)
        for month in sorted(self.index[year].keys(), reverse=options.reverse_index):
            tm = time.localtime(time.mktime([year, month, 3, 0, 0, 0, 0, 0, -1]))
            month_name = self.save_month(year, month, tm)
            idx.write('    <li><a href=%s/%s title="%d post(s)">%s</a></li>\n' % (
                archive_dir, month_name, len(self.index[year][month]),
                strftime('%B', tm)
            ))
        idx.write('</ul>\n\n')

    def save_month(self, year, month, tm):
        file_name = '%d-%02d' % (year, month)
        if options.dirs:
            arch = open_text(archive_dir, file_name, dir_index)
            file_name += '/'
        else:
            file_name += '.html'
            arch = open_text(archive_dir, file_name)
        with arch:
            arch.write('\n\n'.join([
                header(self.title, strftime('%B %Y', tm), body_class='archive'),
                '\n'.join(p.get_post() for p in sorted(
                    self.index[year][month], key=lambda x: x.date, reverse=options.reverse_month
                )),
                '<p><a href=%s rel=contents>Index</a></p>\n' % save_dir
            ]))
        return file_name

    def backup(self, account):
        """makes single files and an index for every post on a public Tumblr blog account"""

        base = get_api_url(account)

        # make sure there are folders to save in
        global save_folder, image_folder, post_ext, post_dir, save_dir, have_custom_css
        if options.blosxom:
            save_folder = root_folder
            post_ext = '.txt'
            post_dir = os.curdir
            post_class = BlosxomPost
        else:
            save_folder = join(root_folder, options.outdir or account)
            image_folder = path_to(image_dir)
            if options.dirs:
                post_ext = ''
                save_dir = '../../'
                mkdir(path_to(post_dir), True)
            else:
                mkdir(save_folder, True)
            post_class = TumblrPost
            have_custom_css = os.access(path_to(custom_css), os.R_OK)

        self.post_count = 0

        # get the highest post id already saved
        ident_max = None
        if options.incremental:
            try:
                ident_max = max(
                    long(splitext(split(f)[1])[0])
                    for f in glob(path_to(post_dir, '*' + post_ext))
                )
                log(account, "Backing up posts after %d\r" % ident_max)
            except ValueError:  # max() arg is an empty sequence
                pass
        else:
            log(account, "Getting basic information\r")

        # start by calling the API with just a single post
        soup = xmlparse(base, 1)
        if not soup:
            return

        # collect all the meta information
        tumblelog = soup.tumblelog
        try:
            self.title = escape(tumblelog('title'))
        except KeyError:
            self.title = account
        self.subtitle = unicode(tumblelog)

        # use the meta information to create a HTML header
        TumblrPost.post_header = header(self.title, body_class='post')

        # find the total number of posts
        total_posts = options.count or int(soup.posts('total'))
        last_post = options.skip + total_posts

        def _backup(posts):
            for p in sorted(posts, key=lambda x: long(x('id')), reverse=True):
                post = post_class(p)
                if ident_max and long(post.ident) <= ident_max:
                    return False
                if options.period:
                    if post.date >= options.p_stop:
                        continue
                    if post.date < options.p_start:
                        return False
                if options.tags and not options.tags & post.tags_lower:
                    continue
                if options.type and not post.typ in options.type:
                    continue
                post.generate_content()
                if post.error:
                    sys.stderr.write('%s%s\n' % (post.error, 50 * ' '))
                post.save_post()
                self.post_count += 1
            return True

        # Get the XML entries from the API, which we can only do for max 50 posts at once.
        # Posts "arrive" in reverse chronological order. Post #0 is the most recent one.
        i = options.skip
        while i < last_post:
            # find the upper bound
            j = min(i + MAX_POSTS, last_post)
            log(account, "Getting posts %d to %d of %d\r" % (i, j - 1, total_posts))

            soup = xmlparse(base, j - i, i)
            if soup is None:
                i += 50         # try the next batch
                continue

            posts = soup.posts['post':]
            if not _backup(posts):
                break

            i += len(posts)

        if not options.blosxom and self.post_count:
            get_avatar()
            get_style()
            if not have_custom_css:
                save_style()
            self.index = defaultdict(lambda: defaultdict(list))
            self.build_index()
            self.save_index()

        log(account, "%d posts backed up\n" % self.post_count)
        self.total_count += self.post_count


class TumblrPost:

    post_header = ''    # set by TumblrBackup.backup()

    def __init__(self, post):
        self.content = ''
        self.post = post
        self.xml_content = post.__repr__(1, 1)
        self.ident = post('id')
        self.url = post('url')
        self.typ = post('type')
        self.date = int(post('unix-timestamp'))
        self.tm = time.localtime(self.date)
        self.title = ''
        self.tags = [u'%s' % t for t in post['tag':]]
        if options.tags:
            self.tags_lower = set(t.lower() for t in self.tags)
        self.file_name = join(self.ident, dir_index) if options.dirs else self.ident + post_ext
        self.llink = self.ident if options.dirs else self.file_name
        self.error = None

    def generate_content(self):
        """generates the content for this post"""
        post = self.post
        content = []

        def append(s, fmt=u'%s'):
            # the %s conversion calls unicode() on the xmltramp element
            content.append(fmt % s)

        def get_try(elt):
            try:
                return unicode(post[elt])
            except KeyError:
                return ''

        def append_try(elt, fmt=u'%s'):
            elt = get_try(elt)
            if elt:
                append(elt, fmt)

        if self.typ == 'regular':
            self.title = get_try('regular-title')
            append_try('regular-body')

        elif self.typ == 'photo':
            if options.dirs:
                global image_dir, image_folder
                image_dir = join(post_dir, self.ident)
                image_folder = path_to(post_dir, self.ident)
            url = escape(get_try('photo-link-url'))
            for p in post.photoset['photo':] if hasattr(post, 'photoset') else [post]:
                src = unicode(p['photo-url'])
                append(escape(self.get_image_url(src, p().get('offset'))), u'<img alt="" src="%s">')
                if url:
                    content[-1] = '<a href="%s">%s</a>' % (url, content[-1])
                content[-1] = '<p>' + content[-1] + '</p>'
                if p._name == 'photo' and p('caption'):
                    append(p('caption'), u'<p>%s</p>')
            append_try('photo-caption')

        elif self.typ == 'link':
            url = unicode(post['link-url'])
            self.title = u'<a href="%s">%s</a>' % (escape(url),
                post['link-text'] if 'link-text' in post else url
            )
            append_try('link-description')

        elif self.typ == 'quote':
            append(post['quote-text'], u'<blockquote><p>%s</p></blockquote>')
            append_try('quote-source', u'<p>%s</p>')

        elif self.typ == 'video':
            source = unicode(post['video-source']).strip()
            if source.startswith('<'):
                player = source
                source = ''
            else:
                player = unicode(post['video-player']).strip()
            player = player.replace('src="//', 'src="http://')
            append(player)
            append_try('video-caption')
            if '//' in source:
                append(escape(source), u'<p><a href="%s">Original</a></p>')

        elif self.typ == 'audio':
            append(post['audio-player'])
            append_try('audio-caption')

        elif self.typ == 'answer':
            self.title = post.question
            try:
                append(post.answer)
            except AttributeError:
                pass

        elif self.typ == 'conversation':
            self.title = get_try('conversation-title')
            append(
                '<br>\n'.join(escape(unicode(l)) for l in post.conversation['line':]),
                u'<p>%s</p>'
            )

        else:
            self.error = u"Unknown post type '%s' in post #%s" % (self.typ, self.ident)
            append(escape(self.xml_content), u'<pre>%s</pre>')

        self.content = '\n'.join(content)

        # fix wrongly nested HTML tags
        for p in ('<p>(<(%s)>)', '(</(%s)>)</p>'):
            self.content = re.sub(p % 'p|ol|iframe[^>]*', r'\1', self.content)

    def get_image_url(self, image_url, offset):
        """Saves an image if not saved yet. Returns the new URL or
        the original URL in case of download errors."""

        def _url(fn):
            return u'%s%s/%s' % (save_dir, image_dir, fn)

        def _addexif(fn):
           if options.exif and fn.endswith('.jpg'):
               add_exif(fn, set(self.tags))

        # determine the image file name
        offset = '_' + offset if offset else ''
        if options.image_names == 'i':
            image_filename = self.ident + offset
        elif options.image_names == 'bi':
            image_filename = account + '_' + self.ident + offset
        else:
            image_filename = image_url.split('/')[-1]
        glob_filter = '' if '.' in image_filename else '.*'
        # check if a file with this name already exists
        image_glob = glob(join(image_folder, image_filename + glob_filter))
        if image_glob:
            _addexif(image_glob[0])
            return _url(split(image_glob[0])[1])
        # download the image data
        try:
            image_response = urllib2.urlopen(image_url)
        except urllib2.HTTPError:
            # return the original URL
            return image_url
        image_data = image_response.read()
        image_response.close()
        # determine the file type if it's unknown
        if '.' not in image_filename:
            image_type = imghdr.what(None, image_data[:32])
            if image_type:
                image_filename += '.' + image_type.replace('jpeg', 'jpg')
        # save the image
        with open_image(image_dir, image_filename) as image_file:
            image_file.write(image_data)
        _addexif(join(image_folder, image_filename))
        return _url(image_filename)

    def get_post(self):
        """returns this post in HTML"""
        post = self.post_header + '<article class=%s id=p-%s>\n' % (self.typ, self.ident)
        post += '<p class=meta><span class=date>%s</span>\n' % strftime('%x %X', self.tm)
        post += u'<a class=llink href=%s%s/%s>¶</a>\n' % (save_dir, post_dir, self.llink)
        post += u'<a href=%s rel=canonical>●</a></p>\n' % self.url
        if self.title:
            post += '<h2>%s</h2>\n' % self.title
        post += self.content
        if self.tags:
            post += u'\n<p class=tags>%s</p>' % u''.join(self.tag_link(t) for t in self.tags)
        post += '\n</article>\n'
        return post

    def tag_link(self, tag):
        tag_disp = escape(TAG_FMT % tag)
        if not TAGLINK_FMT:
            return tag_disp + ' '
        url = TAGLINK_FMT % {'domain': blog_name, 'tag': urllib.quote(tag.encode('utf-8'))}
        return u'<a href=%s>%s</a>\n' % (url, tag_disp)

    def save_post(self):
        """saves this post locally"""
        if options.dirs:
            f = open_text(post_dir, self.ident, dir_index)
        else:
            f = open_text(post_dir, self.file_name)
        with f:
            f.write(self.get_post())
        os.utime(f.stream.name, (self.date, self.date)) # XXX: is f.stream.name portable?
        if options.xml:
            with open_text(xml_dir, self.ident + '.xml') as f:
                f.write(self.xml_content)

class BlosxomPost(TumblrPost):

    def get_image_url(self, image_url, offset):
        return image_url

    def get_post(self):
        """returns this post as a Blosxom post"""
        post = self.title + '\nmeta-id: _' + self.ident + '\nmeta-url: ' + self.url
        if self.tags:
            post += '\nmeta-tags: ' + ' '.join(t.replace(' ', '+') for t in self.tags)
        post += '\n\n' + self.content
        return post

class LocalPost:

    def __init__(self, post_file):
        with codecs.open(post_file, 'r', encoding) as f:
            self.lines = f.readlines()
        # remove header and footer
        while self.lines and '<article ' not in self.lines[0]:
            del self.lines[0]
        while self.lines and '</article>' not in self.lines[-1]:
            del self.lines[-1]
        parts = post_file.split(os.sep)
        if parts[-1] == dir_index:  # .../<post_id>/index.html
            self.file_name = os.sep.join(parts[-2:])
            self.ident = parts[-2]
        else:
            self.file_name = parts[-1]
            self.ident = splitext(self.file_name)[0]
        self.date = os.stat(post_file).st_mtime
        self.tm = time.localtime(self.date)

    def get_post(self):
        return u''.join(self.lines)


if __name__ == '__main__':
    import optparse

    def csv_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, set(value.split(',')))

    def tags_callback(option, opt, value, parser):
        csv_callback(option, opt, value.lower(), parser)

    def type_callback(option, opt, value, parser):
        value = value.replace('text', 'regular').replace('chat', 'conversation').replace('photoset', 'photo')
        csv_callback(option, opt, value, parser)

    parser = optparse.OptionParser("Usage: %prog [options] blog-name ...",
        description="Makes a local backup of Tumblr blogs."
    )
    parser.add_option('-O', '--outdir', help="set the output directory"
        " (default: blog-name)"
    )
    parser.add_option('-D', '--dirs', action='store_true',
        help="save each post in its own folder"
    )
    parser.add_option('-q', '--quiet', action='store_true',
        help="suppress progress messages"
    )
    parser.add_option('-i', '--incremental', action='store_true',
        help="incremental backup mode"
    )
    parser.add_option('-x', '--xml', action='store_true',
        help="save the original XML source"
    )
    parser.add_option('-b', '--blosxom', action='store_true',
        help="save the posts in blosxom format"
    )
    parser.add_option('-r', '--reverse-month', action='store_false', default=True,
        help="reverse the post order in the monthly archives"
    )
    parser.add_option('-R', '--reverse-index', action='store_false', default=True,
        help="reverse the index file order"
    )
    parser.add_option('-a', '--auto', type='int', metavar="HOUR",
        help="do a full backup at HOUR hours, otherwise do an incremental backup"
        " (useful for cron jobs)"
    )
    parser.add_option('-n', '--count', type='int', help="save only COUNT posts")
    parser.add_option('-s', '--skip', type='int', default=0,
        help="skip the first SKIP posts"
    )
    parser.add_option('-p', '--period', help="limit the backup to PERIOD"
        " ('y', 'm', 'd' or YYYY[MM[DD]])"
    )
    parser.add_option('-P', '--private', help="password for a private tumblr",
        metavar='PASSWORD'
    )
    parser.add_option('-t', '--tags', type='string', action='callback',
        callback=tags_callback, help="save only posts tagged TAGS (comma-separated values;"
        " case-insensitive)"
    )
    parser.add_option('-T', '--type', type='string', action='callback',
        callback=type_callback, help="save only posts of type TYPE (comma-separated values)"
    )
    parser.add_option('-I', '--image-names', type='choice', choices=('o', 'i', 'bi'),
        default='o', metavar='FMT',
        help="image filename format ('o'=original, 'i'=<post-id>, 'bi'=<blog-name>_<post-id>)"
    )
    parser.add_option('-e', '--exif', type='string', action='callback',
        callback=csv_callback, default=set(), metavar='KW',
        help="add EXIF keyword tags to each picture (comma-separated values;"
        " '-' to remove all tags, '' to add no extra tags)"
    )
    options, args = parser.parse_args()

    if options.auto is not None and options.auto != time.localtime().tm_hour:
        options.incremental = True
    if options.period:
        try:
            pformat = {'y': '%Y', 'm': '%Y%m', 'd': '%Y%m%d'}[options.period]
        except KeyError:
            options.period = options.period.replace('-', '')
            try:
                int(options.period)  # must be numeric
            except ValueError:
                options.period = ''  # trigger the length check below
        else:
            options.period = time.strftime(pformat)
        if len(options.period) not in (4, 6, 8):
            parser.error("Period must be 'y', 'm', 'd' or YYYY[MM[DD]]")
        set_period()
    if not args:
        args = DEFAULT_BLOGS
    if options.outdir and len(args) > 1:
        parser.error("-O can only be used for a single blog-name")
    if options.exif and not pyexiv2:
        parser.error("--exif: module 'pyexif2' is not installed")

    tb = TumblrBackup()
    for account in args:
        tb.backup(account)

    sys.exit(0 if tb.total_count else 1)

########NEW FILE########
