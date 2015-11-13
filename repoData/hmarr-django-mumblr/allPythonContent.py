__FILENAME__ = local_settings
import mongoengine
mongoengine.connect('mumblr-example')

import os
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
#MEDIA_ROOT = os.path.join(PROJECT_PATH, '..', 'mumblr', 'static')

SECRET_KEY = '$geoon8_ymg-k)!9wl3wloq4&30w$rhc1*zv%h6m_&nza(4)nk'

RECAPTCHA_PUBLIC_KEY = "6LfFgQoAAAAAABQTj4YjuPbccgKtZStoiWtr7E5k"
RECAPTCHA_PRIVATE_KEY = "6LfFgQoAAAAAAM-0SAUTe7WxZ-thnWFfSpoc7sfJ"


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    ('Harry Marr', 'harry.marr@gmail.com'),
)

MANAGERS = ADMINS

import os
from local_settings import *

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'
USE_I18N = False

MEDIA_ROOT = os.path.join(PROJECT_PATH, 'static')
MEDIA_URL = '/static/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.media',
    'mumblr.context_processors.auth',
    'mumblr.context_processors.site_info',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.csrf.middleware.CsrfMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'mongoengine.django.auth.MongoEngineBackend',
)

SESSION_ENGINE = 'mongoengine.django.sessions'

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'mumblr',
    'mytheme',
)

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'

TEST_RUNNER = 'testrunner.run_tests'

MUMBLR_MARKUP_LANGUAGE = 'markdown'
#MUMBLR_THEME = 'mytheme'

########NEW FILE########
__FILENAME__ = testrunner
from django.conf import settings
from django.test import TestCase
from django.test.simple import (setup_test_environment, reorder_suite,
                                build_test, build_suite, get_app, get_apps, 
                                teardown_test_environment)
import unittest

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """Run the unit tests without using the ORM.
    """
    setup_test_environment()

    settings.DEBUG = False
    settings.DATABASE_SUPPORTS_TRANSACTIONS = False
    suite = unittest.TestSuite()

    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    else:
        for app in get_apps():
            suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    suite = reorder_suite(suite, (TestCase,))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    teardown_test_environment()

    return len(result.failures) + len(result.errors)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    (r'^', include('mumblr.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('', 
                            (r'^' + settings.MEDIA_URL.lstrip('/') + r'(.*)$', 
                            'django.views.static.serve',
                            {'document_root': settings.MEDIA_ROOT}))

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings

def auth(request):
    if hasattr(request, 'user'):
        return {'user': request.user}
    return {}

def site_info(context):
    title = getattr(settings, 'SITE_INFO_TITLE', 'Mumblr')
    description = getattr(settings, 'SITE_INFO_DESC', 'Simple Blogging.')
    return {
        'SITE_INFO_TITLE': title,
        'SITE_INFO_DESC': description,
    }

########NEW FILE########
__FILENAME__ = captcha
import urllib2, urllib

API_SSL_SERVER="https://api-secure.recaptcha.net"
API_SERVER="http://api.recaptcha.net"
VERIFY_SERVER="api-verify.recaptcha.net"

class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

def displayhtml(public_key, use_ssl = False, error = None):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)
    """
    error_param = ''
    if error:
        error_param = '&error=%s' % error

    if use_ssl:
        server = API_SSL_SERVER
    else:
        server = API_SERVER

    return """<script type="text/javascript" src="%(ApiServer)s/challenge?k=%(PublicKey)s%(ErrorParam)s"></script>

<noscript>
  <iframe src="%(ApiServer)s/noscript?k=%(PublicKey)s%(ErrorParam)s" height="300" width="500" frameborder="0"></iframe><br />
  <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
  <input type='hidden' name='recaptcha_response_field' value='manual_challenge' />
</noscript>
""" % {
        'ApiServer': server,
        'PublicKey': public_key,
        'ErrorParam': error_param,
        }


def submit(recaptcha_challenge_field, recaptcha_response_field, private_key,
           remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field from
    the form
    recaptcha_response_field -- The value of recaptcha_response_field from the
    form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    if not (recaptcha_response_field and recaptcha_challenge_field and
            len(recaptcha_response_field) and len(recaptcha_challenge_field)):
        return RecaptchaResponse(is_valid=False, 
                                 error_code='incorrect-captcha-sol')
    

    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode({
        'privatekey': encode_if_necessary(private_key),
        'remoteip':  encode_if_necessary(remoteip),
        'challenge':  encode_if_necessary(recaptcha_challenge_field),
        'response':  encode_if_necessary(recaptcha_response_field),
    })

    request = urllib2.Request(
        url = "http://%s/verify" % VERIFY_SERVER,
        data = params,
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "User-agent": "reCAPTCHA Python"
        }
    )
    
    httpresp = urllib2.urlopen(request)

    return_values = httpresp.read().splitlines();
    httpresp.close();

    return_code = return_values [0]

    if return_code == "true":
        return RecaptchaResponse(is_valid=True)
    else:
        return RecaptchaResponse(is_valid=False, error_code=return_values[1])

########NEW FILE########
__FILENAME__ = core
import re
from django import forms

from mongoengine import *

from mumblr.entrytypes import EntryType, Comment, markup


class HtmlComment(Comment):
    """An HTML-based entry, which will be converted from the markup language
    specified in the settings.
    """
    rendered_content = StringField(required=True)


class TextEntry(EntryType):
    """An HTML-based entry, which will be converted from the markup language
    specified in the settings.
    """
    content = StringField(required=True)
    rendered_content = StringField(required=True)

    type = 'Text'

    def save(self):
        """Convert any markup to HTML before saving.
        """
        self.rendered_content = markup(self.content)
        super(TextEntry, self).save()

    class AdminForm(EntryType.AdminForm):
        content = forms.CharField(widget=forms.Textarea)


class LinkEntry(EntryType):
    """A link-based entry - the title is a link to the specified url and the
    content is the optional description.
    """
    link_url = StringField(required=True)
    description = StringField()

    type = 'Link'

    def rendered_content(self):
        if self.description:
            return markup(self.description, no_follow=False)
        return '<p>Link: <a href="%s">%s</a></p>' % (self.link_url, 
                                                     self.link_url)

    class AdminForm(EntryType.AdminForm):
        link_url = forms.URLField()
        description = forms.CharField(widget=forms.Textarea, required=False)


class ImageEntry(EntryType):
    """An image-based entry - displays the image at the given url along with
    the optional description.
    """
    image_url = StringField(required=True)
    description = StringField()

    type = 'Image'

    def rendered_content(self):
        url = self.image_url
        html = '<img src="%s" />' % url
        if self.description:
            html += markup(self.description)
        return html

    class AdminForm(EntryType.AdminForm):
        image_url = forms.URLField()
        description = forms.CharField(widget=forms.Textarea, required=False)


class VideoEntry(EntryType):
    """An video-based entry - will try to embed the video if it is of
    and known type e.g. YouTube
    """
    video_url = StringField(required=True)
    description = StringField()

    type = 'Video'

    embed_codes = {
        'vimeo': (
            '<object width="600" height="338"><param name="allowfullscr'
            'een" value="true" /><param name="allowscriptaccess" value='
            '"always" /><param name="movie" value="http://vimeo.com/moo'
            'galoop.swf?clip_id={{!ID}}&amp;server=vimeo.com&amp;show_t'
            'itle=0&amp;show_byline=0&amp;show_portrait=0&amp;color=59a'
            '5d1&amp;fullscreen=1" /><embed src="http://vimeo.com/mooga'
            'loop.swf?clip_id={{!ID}}&amp;server=vimeo.com&amp;show_tit'
            'le=0&amp;show_byline=0&amp;show_portrait=0&amp;color=59a5d'
            '1&amp;fullscreen=1" type="application/x-shockwave-flash" a'
            'llowfullscreen="true" allowscriptaccess="always" width="60'
            '0" height="338"></embed></object>'
        ),
        'youtube': (
            '<object width="600" height="338">'
            '<param name="movie" value="{{!ID}}"></param>'
            '<param name="allowFullScreen" value="true"></param>'
            '<param name="allowscriptaccess" value="always"></param>'
            '<embed src="http://www.youtube.com/v/{{!ID}}&fs=1&rel=&'
            'hd=10&showinfo=0&iv_load_policy=3" ' 
            'type="application/x-shockwave-flash" '
            'allowscriptaccess="always" allowfullscreen="true" '
            'width="600" height="338"></embed></object>'
        )
    }

    embed_patterns = (
        ('youtube', r'youtube\.com\/watch\?v=([A-Za-z0-9._%-]+)[&\w;=\+_\-]*'),
        ('vimeo', r'vimeo\.com\/(\d+)'),
    )

    def rendered_content(self):
        video_url = self.video_url
        for source, pattern in VideoEntry.embed_patterns:
            id = re.findall(pattern, video_url)
            if id:
                embed = VideoEntry.embed_codes[source]
                html = embed.replace('{{!ID}}', id[0])
                break
        else:
            html = 'Video: <a href="video_url">%s</a>' % video_url

        if self.description:
            html += markup(self.description)
        return html

    class AdminForm(EntryType.AdminForm):
        video_url = forms.URLField()
        description = forms.CharField(widget=forms.Textarea, required=False)


EntryType.register(TextEntry)
EntryType.register(LinkEntry)
EntryType.register(ImageEntry)
EntryType.register(VideoEntry)

########NEW FILE########
__FILENAME__ = fields
from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import Widget, Select, TextInput
from django.forms.extras.widgets import SelectDateWidget

import captcha


class ReCaptcha(forms.widgets.Widget):
    """Renders the proper ReCaptcha widget
    """
    def render(self, name, value, attrs=None):
        html = captcha.displayhtml(settings.RECAPTCHA_PUBLIC_KEY)
        return mark_safe(u'%s' % html)

    def value_from_datadict(self, data, files, name):
        return [data.get('recaptcha_challenge_field', None), 
                data.get('recaptcha_response_field', None)]


class ReCaptchaField(forms.CharField):
    """Provides ReCaptcha functionality using ReCaptcha python client
    """
    default_error_messages = {
        'captcha_invalid': _(u'Invalid captcha.')
    }

    def __init__(self, *args, **kwargs):
        self.widget = ReCaptcha
        self.required = True
        super(ReCaptchaField, self).__init__(*args, **kwargs)

    def clean(self, values):
        super(ReCaptchaField, self).clean(values[1])
        recaptcha_challenge_value = smart_unicode(values[0])
        recaptcha_response_value = smart_unicode(values[1])
        check_captcha = captcha.submit(recaptcha_challenge_value, 
            recaptcha_response_value, settings.RECAPTCHA_PRIVATE_KEY, {})
        if not check_captcha.is_valid:
            raise forms.util.ValidationError(
                    self.error_messages['captcha_invalid'])
        return values[0]


########NEW FILE########
__FILENAME__ = adduser
import getpass
import hashlib
from django.core.management.base import BaseCommand

from mongoengine.django.auth import User


class Command(BaseCommand):
    
    def _get_string(self, prompt, reader_func=raw_input, required=True):
        """Helper method to get a non-empty string.
        """
        string = ''
        while not string:
            string = reader_func(prompt + ': ')
            if not required:
                break
        return string

    def handle(self, **kwargs):
        username = self._get_string('Username')
        email = self._get_string('Email', required=False)
        password = self._get_string('Password', getpass.getpass)
        first_name = self._get_string('First name')
        last_name = self._get_string('Last name')

        user = User(username=username)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.set_password(password)
        user.is_staff = True
        user.save()

        print 'User "%s %s" successfully added' % (first_name, last_name)

########NEW FILE########
__FILENAME__ = listusers
from django.core.management.base import BaseCommand

from mongoengine.django.auth import User


class Command(BaseCommand):

    def handle(self, **kwargs):
        for user in User.objects:
            print '[%s] %s' % (user.username, user.get_full_name())

########NEW FILE########
__FILENAME__ = rmuser
from django.core.management.base import BaseCommand

from mongoengine.django.auth import User


class Command(BaseCommand):

    def _get_string(self, prompt, reader_func=raw_input):
        """Helper method to get a non-empty string.
        """
        string = ''
        while not string:
            string = reader_func(prompt + ': ')
        return string
    
    def handle(self, **kwargs):
        username = self._get_string('Username')
        user = User.objects(username=username).first()
        if user:
            user.delete()
            print 'User "%s %s" successfully removed' % (user.first_name, 
                                                         user.last_name)
        else:
            print 'Error! Could not find user with username "%s"' % username

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = mumblr_tags
from django.template import Library, Node, TemplateSyntaxError

import re

from mumblr.entrytypes import EntryType

register = Library()


class LatestEntriesNode(Node):

    def __init__(self, num, var_name):
        self.num = int(num or 10)
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = list(EntryType.live_entries()[:self.num])
        return ''


@register.tag
def get_latest_entries(parser, token):
    # Usage:
    #   {% get_latest_entries as entries %} (default 10 entries)
    #   (or {% get_latest_entries 7 as entries %} for 7 entries)
    #   {% for entry in entries %}
    #       <li>{{ entry.title }}</li>
    #   {% endfor %}
    tag_name, contents = token.contents.split(None, 1)
    match = re.search(r'(\d+\s+)?as\s+([A-z_][A-z0-9_]+)', contents)
    if not match:
        raise TemplateSyntaxError("%r tag syntax error" % tag_name)

    num, var_name = match.groups()
    return LatestEntriesNode(num, var_name)

########NEW FILE########
__FILENAME__ = smartypants
#!/usr/bin/python

r"""
==============
smartypants.py
==============

----------------------------
SmartyPants ported to Python
----------------------------

Ported by `Chad Miller`_
Copyright (c) 2004, 2007 Chad Miller

original `SmartyPants`_ by `John Gruber`_
Copyright (c) 2003 John Gruber


Synopsis
========

A smart-quotes plugin for Pyblosxom_.

The priginal "SmartyPants" is a free web publishing plug-in for Movable Type,
Blosxom, and BBEdit that easily translates plain ASCII punctuation characters
into "smart" typographic punctuation HTML entities.

This software, *smartypants.py*, endeavours to be a functional port of
SmartyPants to Python, for use with Pyblosxom_.


Description
===========

SmartyPants can perform the following transformations:

- Straight quotes ( " and ' ) into "curly" quote HTML entities
- Backticks-style quotes (\`\`like this'') into "curly" quote HTML entities
- Dashes (``--`` and ``---``) into en- and em-dash entities
- Three consecutive dots (``...`` or ``. . .``) into an ellipsis entity

This means you can write, edit, and save your posts using plain old
ASCII straight quotes, plain dashes, and plain dots, but your published
posts (and final HTML output) will appear with smart quotes, em-dashes,
and proper ellipses.

SmartyPants does not modify characters within ``<pre>``, ``<code>``, ``<kbd>``,
``<math>`` or ``<script>`` tag blocks. Typically, these tags are used to
display text where smart quotes and other "smart punctuation" would not be
appropriate, such as source code or example markup.


Backslash Escapes
=================

If you need to use literal straight quotes (or plain hyphens and
periods), SmartyPants accepts the following backslash escape sequences
to force non-smart punctuation. It does so by transforming the escape
sequence into a decimal-encoded HTML entity:

(FIXME:  table here.)

.. comment    It sucks that there's a disconnect between the visual layout and table markup when special characters are involved.
.. comment ======  =====  =========
.. comment Escape  Value  Character
.. comment ======  =====  =========
.. comment \\\\\\\\    &#92;  \\\\
.. comment \\\\"     &#34;  "
.. comment \\\\'     &#39;  '
.. comment \\\\.     &#46;  .
.. comment \\\\-     &#45;  \-
.. comment \\\\`     &#96;  \`
.. comment ======  =====  =========

This is useful, for example, when you want to use straight quotes as
foot and inch marks: 6'2" tall; a 17" iMac.

Options
=======

For Pyblosxom users, the ``smartypants_attributes`` attribute is where you
specify configuration options. 

Numeric values are the easiest way to configure SmartyPants' behavior:

"0"
	Suppress all transformations. (Do nothing.)
"1" 
	Performs default SmartyPants transformations: quotes (including
	\`\`backticks'' -style), em-dashes, and ellipses. "``--``" (dash dash)
	is used to signify an em-dash; there is no support for en-dashes.

"2"
	Same as smarty_pants="1", except that it uses the old-school typewriter
	shorthand for dashes:  "``--``" (dash dash) for en-dashes, "``---``"
	(dash dash dash)
	for em-dashes.

"3"
	Same as smarty_pants="2", but inverts the shorthand for dashes:
	"``--``" (dash dash) for em-dashes, and "``---``" (dash dash dash) for
	en-dashes.

"-1"
	Stupefy mode. Reverses the SmartyPants transformation process, turning
	the HTML entities produced by SmartyPants into their ASCII equivalents.
	E.g.  "&#8220;" is turned into a simple double-quote ("), "&#8212;" is
	turned into two dashes, etc.


The following single-character attribute values can be combined to toggle
individual transformations from within the smarty_pants attribute. For
example, to educate normal quotes and em-dashes, but not ellipses or
\`\`backticks'' -style quotes:

``py['smartypants_attributes'] = "1"``

"q"
	Educates normal quote characters: (") and (').

"b"
	Educates \`\`backticks'' -style double quotes.

"B"
	Educates \`\`backticks'' -style double quotes and \`single' quotes.

"d"
	Educates em-dashes.

"D"
	Educates em-dashes and en-dashes, using old-school typewriter shorthand:
	(dash dash) for en-dashes, (dash dash dash) for em-dashes.

"i"
	Educates em-dashes and en-dashes, using inverted old-school typewriter
	shorthand: (dash dash) for em-dashes, (dash dash dash) for en-dashes.

"e"
	Educates ellipses.

"w"
	Translates any instance of ``&quot;`` into a normal double-quote character.
	This should be of no interest to most people, but of particular interest
	to anyone who writes their posts using Dreamweaver, as Dreamweaver
	inexplicably uses this entity to represent a literal double-quote
	character. SmartyPants only educates normal quotes, not entities (because
	ordinarily, entities are used for the explicit purpose of representing the
	specific character they represent). The "w" option must be used in
	conjunction with one (or both) of the other quote options ("q" or "b").
	Thus, if you wish to apply all SmartyPants transformations (quotes, en-
	and em-dashes, and ellipses) and also translate ``&quot;`` entities into
	regular quotes so SmartyPants can educate them, you should pass the
	following to the smarty_pants attribute:

The ``smartypants_forbidden_flavours`` list contains pyblosxom flavours for 
which no Smarty Pants rendering will occur.


Caveats
=======

Why You Might Not Want to Use Smart Quotes in Your Weblog
---------------------------------------------------------

For one thing, you might not care.

Most normal, mentally stable individuals do not take notice of proper
typographic punctuation. Many design and typography nerds, however, break
out in a nasty rash when they encounter, say, a restaurant sign that uses
a straight apostrophe to spell "Joe's".

If you're the sort of person who just doesn't care, you might well want to
continue not caring. Using straight quotes -- and sticking to the 7-bit
ASCII character set in general -- is certainly a simpler way to live.

Even if you I *do* care about accurate typography, you still might want to
think twice before educating the quote characters in your weblog. One side
effect of publishing curly quote HTML entities is that it makes your
weblog a bit harder for others to quote from using copy-and-paste. What
happens is that when someone copies text from your blog, the copied text
contains the 8-bit curly quote characters (as well as the 8-bit characters
for em-dashes and ellipses, if you use these options). These characters
are not standard across different text encoding methods, which is why they
need to be encoded as HTML entities.

People copying text from your weblog, however, may not notice that you're
using curly quotes, and they'll go ahead and paste the unencoded 8-bit
characters copied from their browser into an email message or their own
weblog. When pasted as raw "smart quotes", these characters are likely to
get mangled beyond recognition.

That said, my own opinion is that any decent text editor or email client
makes it easy to stupefy smart quote characters into their 7-bit
equivalents, and I don't consider it my problem if you're using an
indecent text editor or email client.


Algorithmic Shortcomings
------------------------

One situation in which quotes will get curled the wrong way is when
apostrophes are used at the start of leading contractions. For example:

``'Twas the night before Christmas.``

In the case above, SmartyPants will turn the apostrophe into an opening
single-quote, when in fact it should be a closing one. I don't think
this problem can be solved in the general case -- every word processor
I've tried gets this wrong as well. In such cases, it's best to use the
proper HTML entity for closing single-quotes (``&#8217;``) by hand.


Bugs
====

To file bug reports or feature requests (other than topics listed in the
Caveats section above) please send email to: mailto:smartypantspy@chad.org

If the bug involves quotes being curled the wrong way, please send example
text to illustrate.

To Do list
----------

- Provide a function for use within templates to quote anything at all.


Version History
===============

1.5_1.6: Fri, 27 Jul 2007 07:06:40 -0400
	- Fixed bug where blocks of precious unalterable text was instead
	  interpreted.  Thanks to Le Roux and Dirk van Oosterbosch.
	
1.5_1.5: Sat, 13 Aug 2005 15:50:24 -0400
	- Fix bogus magical quotation when there is no hint that the 
	  user wants it, e.g., in "21st century".  Thanks to Nathan Hamblen.
	- Be smarter about quotes before terminating numbers in an en-dash'ed
	  range.

1.5_1.4: Thu, 10 Feb 2005 20:24:36 -0500
	- Fix a date-processing bug, as reported by jacob childress.
	- Begin a test-suite for ensuring correct output.
	- Removed import of "string", since I didn't really need it.
	  (This was my first every Python program.  Sue me!)

1.5_1.3: Wed, 15 Sep 2004 18:25:58 -0400
	- Abort processing if the flavour is in forbidden-list.  Default of 
	  [ "rss" ]   (Idea of Wolfgang SCHNERRING.)
	- Remove stray virgules from en-dashes.  Patch by Wolfgang SCHNERRING.

1.5_1.2: Mon, 24 May 2004 08:14:54 -0400
	- Some single quotes weren't replaced properly.  Diff-tesuji played
	  by Benjamin GEIGER.

1.5_1.1: Sun, 14 Mar 2004 14:38:28 -0500
	- Support upcoming pyblosxom 0.9 plugin verification feature.

1.5_1.0: Tue, 09 Mar 2004 08:08:35 -0500
	- Initial release

Version Information
-------------------

Version numbers will track the SmartyPants_ version numbers, with the addition
of an underscore and the smartypants.py version on the end.

New versions will be available at `http://wiki.chad.org/SmartyPantsPy`_

.. _http://wiki.chad.org/SmartyPantsPy: http://wiki.chad.org/SmartyPantsPy

Authors
=======

`John Gruber`_ did all of the hard work of writing this software in Perl for
`Movable Type`_ and almost all of this useful documentation.  `Chad Miller`_
ported it to Python to use with Pyblosxom_.


Additional Credits
==================

Portions of the SmartyPants original work are based on Brad Choate's nifty
MTRegex plug-in.  `Brad Choate`_ also contributed a few bits of source code to
this plug-in.  Brad Choate is a fine hacker indeed.

`Jeremy Hedley`_ and `Charles Wiltgen`_ deserve mention for exemplary beta
testing of the original SmartyPants.

`Rael Dornfest`_ ported SmartyPants to Blosxom.

.. _Brad Choate: http://bradchoate.com/
.. _Jeremy Hedley: http://antipixel.com/
.. _Charles Wiltgen: http://playbacktime.com/
.. _Rael Dornfest: http://raelity.org/


Copyright and License
=====================

SmartyPants_ license::

	Copyright (c) 2003 John Gruber
	(http://daringfireball.net/)
	All rights reserved.

	Redistribution and use in source and binary forms, with or without
	modification, are permitted provided that the following conditions are
	met:

	*   Redistributions of source code must retain the above copyright
		notice, this list of conditions and the following disclaimer.

	*   Redistributions in binary form must reproduce the above copyright
		notice, this list of conditions and the following disclaimer in
		the documentation and/or other materials provided with the
		distribution.

	*   Neither the name "SmartyPants" nor the names of its contributors 
		may be used to endorse or promote products derived from this
		software without specific prior written permission.

	This software is provided by the copyright holders and contributors "as
	is" and any express or implied warranties, including, but not limited
	to, the implied warranties of merchantability and fitness for a
	particular purpose are disclaimed. In no event shall the copyright
	owner or contributors be liable for any direct, indirect, incidental,
	special, exemplary, or consequential damages (including, but not
	limited to, procurement of substitute goods or services; loss of use,
	data, or profits; or business interruption) however caused and on any
	theory of liability, whether in contract, strict liability, or tort
	(including negligence or otherwise) arising in any way out of the use
	of this software, even if advised of the possibility of such damage.


smartypants.py license::

	smartypants.py is a derivative work of SmartyPants.
	
	Redistribution and use in source and binary forms, with or without
	modification, are permitted provided that the following conditions are
	met:

	*   Redistributions of source code must retain the above copyright
		notice, this list of conditions and the following disclaimer.

	*   Redistributions in binary form must reproduce the above copyright
		notice, this list of conditions and the following disclaimer in
		the documentation and/or other materials provided with the
		distribution.

	This software is provided by the copyright holders and contributors "as
	is" and any express or implied warranties, including, but not limited
	to, the implied warranties of merchantability and fitness for a
	particular purpose are disclaimed. In no event shall the copyright
	owner or contributors be liable for any direct, indirect, incidental,
	special, exemplary, or consequential damages (including, but not
	limited to, procurement of substitute goods or services; loss of use,
	data, or profits; or business interruption) however caused and on any
	theory of liability, whether in contract, strict liability, or tort
	(including negligence or otherwise) arising in any way out of the use
	of this software, even if advised of the possibility of such damage.



.. _John Gruber: http://daringfireball.net/
.. _Chad Miller: http://web.chad.org/

.. _Pyblosxom: http://roughingit.subtlehints.net/pyblosxom
.. _SmartyPants: http://daringfireball.net/projects/smartypants/
.. _Movable Type: http://www.movabletype.org/

"""

default_smartypants_attr = "1"

import re

tags_to_skip_regex = re.compile(r"<(/)?(pre|code|kbd|script|math)[^>]*>", re.I)


def verify_installation(request):
	return 1
	# assert the plugin is functional


def cb_story(args):
	global default_smartypants_attr

	try:
		forbidden_flavours = args["entry"]["smartypants_forbidden_flavours"]
	except KeyError:
		forbidden_flavours = [ "rss" ]

	try:
		attributes = args["entry"]["smartypants_attributes"]
	except KeyError:
		attributes = default_smartypants_attr

	if attributes is None:
		attributes = default_smartypants_attr

	entryData = args["entry"].getData()

	try:
		if args["request"]["flavour"] in forbidden_flavours:
			return
	except KeyError:
		if "&lt;" in args["entry"]["body"][0:15]:  # sniff the stream
			return  # abort if it looks like escaped HTML.  FIXME

	# FIXME: make these configurable, perhaps?
	args["entry"]["body"] = smartyPants(entryData, attributes)
	args["entry"]["title"] = smartyPants(args["entry"]["title"], attributes)


### interal functions below here

def smartyPants(text, attr=default_smartypants_attr):
	convert_quot = False  # should we translate &quot; entities into normal quotes?

	# Parse attributes:
	# 0 : do nothing
	# 1 : set all
	# 2 : set all, using old school en- and em- dash shortcuts
	# 3 : set all, using inverted old school en and em- dash shortcuts
	# 
	# q : quotes
	# b : backtick quotes (``double'' only)
	# B : backtick quotes (``double'' and `single')
	# d : dashes
	# D : old school dashes
	# i : inverted old school dashes
	# e : ellipses
	# w : convert &quot; entities to " for Dreamweaver users

	skipped_tag_stack = []
	do_dashes = "0"
	do_backticks = "0"
	do_quotes = "0"
	do_ellipses = "0"
	do_stupefy = "0"

	if attr == "0":
		# Do nothing.
		return text
	elif attr == "1":
		do_quotes    = "1"
		do_backticks = "1"
		do_dashes    = "1"
		do_ellipses  = "1"
	elif attr == "2":
		# Do everything, turn all options on, use old school dash shorthand.
		do_quotes    = "1"
		do_backticks = "1"
		do_dashes    = "2"
		do_ellipses  = "1"
	elif attr == "3":
		# Do everything, turn all options on, use inverted old school dash shorthand.
		do_quotes    = "1"
		do_backticks = "1"
		do_dashes    = "3"
		do_ellipses  = "1"
	elif attr == "-1":
		# Special "stupefy" mode.
		do_stupefy   = "1"
	else:
		for c in attr:
			if c == "q": do_quotes = "1"
			elif c == "b": do_backticks = "1"
			elif c == "B": do_backticks = "2"
			elif c == "d": do_dashes = "1"
			elif c == "D": do_dashes = "2"
			elif c == "i": do_dashes = "3"
			elif c == "e": do_ellipses = "1"
			elif c == "w": convert_quot = "1"
			else:
				pass
				# ignore unknown option

	tokens = _tokenize(text)
	result = []
	in_pre = False

	prev_token_last_char = ""
	# This is a cheat, used to get some context
	# for one-character tokens that consist of 
	# just a quote char. What we do is remember
	# the last character of the previous text
	# token, to use as context to curl single-
	# character quote tokens correctly.

	for cur_token in tokens:
		if cur_token[0] == "tag":
			# Don't mess with quotes inside some tags.  This does not handle self <closing/> tags!
			result.append(cur_token[1])
			skip_match = tags_to_skip_regex.match(cur_token[1])
			if skip_match is not None:
				if not skip_match.group(1):
					skipped_tag_stack.append(skip_match.group(2).lower())
					in_pre = True
				else:
					if len(skipped_tag_stack) > 0:
						if skip_match.group(2).lower() == skipped_tag_stack[-1]:
							skipped_tag_stack.pop()
						else:
							pass
							# This close doesn't match the open.  This isn't XHTML.  We should barf here.
					if len(skipped_tag_stack) == 0:
						in_pre = False
		else:
			t = cur_token[1]
			last_char = t[-1:] # Remember last char of this token before processing.
			if not in_pre:
				oldstr = t
				t = processEscapes(t)

				if convert_quot != "0":
					t = re.sub('&quot;', '"', t)

				if do_dashes != "0":
					if do_dashes == "1":
						t = educateDashes(t)
					if do_dashes == "2":
						t = educateDashesOldSchool(t)
					if do_dashes == "3":
						t = educateDashesOldSchoolInverted(t)

				if do_ellipses != "0":
					t = educateEllipses(t)

				# Note: backticks need to be processed before quotes.
				if do_backticks != "0":
					t = educateBackticks(t)

				if do_backticks == "2":
					t = educateSingleBackticks(t)

				if do_quotes != "0":
					if t == "'":
						# Special case: single-character ' token
						if re.match("\S", prev_token_last_char):
							t = "&#8217;"
						else:
							t = "&#8216;"
					elif t == '"':
						# Special case: single-character " token
						if re.match("\S", prev_token_last_char):
							t = "&#8221;"
						else:
							t = "&#8220;"

					else:
						# Normal case:
						t = educateQuotes(t)

				if do_stupefy == "1":
					t = stupefyEntities(t)

			prev_token_last_char = last_char
			result.append(t)

	return "".join(result)


def educateQuotes(str):
	"""
	Parameter:  String.
	
	Returns:	The string, with "educated" curly quote HTML entities.
	
	Example input:  "Isn't this fun?"
	Example output: &#8220;Isn&#8217;t this fun?&#8221;
	"""

	oldstr = str
	punct_class = r"""[!"#\$\%'()*+,-.\/:;<=>?\@\[\\\]\^_`{|}~]"""

	# Special case if the very first character is a quote
	# followed by punctuation at a non-word-break. Close the quotes by brute force:
	str = re.sub(r"""^'(?=%s\\B)""" % (punct_class,), r"""&#8217;""", str)
	str = re.sub(r"""^"(?=%s\\B)""" % (punct_class,), r"""&#8221;""", str)

	# Special case for double sets of quotes, e.g.:
	#   <p>He said, "'Quoted' words in a larger quote."</p>
	str = re.sub(r""""'(?=\w)""", """&#8220;&#8216;""", str)
	str = re.sub(r"""'"(?=\w)""", """&#8216;&#8220;""", str)

	# Special case for decade abbreviations (the '80s):
	str = re.sub(r"""\b'(?=\d{2}s)""", r"""&#8217;""", str)

	close_class = r"""[^\ \t\r\n\[\{\(\-]"""
	dec_dashes = r"""&#8211;|&#8212;"""

	# Get most opening single quotes:
	opening_single_quotes_regex = re.compile(r"""
			(
				\s          |   # a whitespace char, or
				&nbsp;      |   # a non-breaking space entity, or
				--          |   # dashes, or
				&[mn]dash;  |   # named dash entities
				%s          |   # or decimal entities
				&\#x201[34];    # or hex
			)
			'                 # the quote
			(?=\w)            # followed by a word character
			""" % (dec_dashes,), re.VERBOSE)
	str = opening_single_quotes_regex.sub(r"""\1&#8216;""", str)

	closing_single_quotes_regex = re.compile(r"""
			(%s)
			'
			(?!\s | s\b | \d)
			""" % (close_class,), re.VERBOSE)
	str = closing_single_quotes_regex.sub(r"""\1&#8217;""", str)

	closing_single_quotes_regex = re.compile(r"""
			(%s)
			'
			(\s | s\b)
			""" % (close_class,), re.VERBOSE)
	str = closing_single_quotes_regex.sub(r"""\1&#8217;\2""", str)

	# Any remaining single quotes should be opening ones:
	str = re.sub(r"""'""", r"""&#8216;""", str)

	# Get most opening double quotes:
	opening_double_quotes_regex = re.compile(r"""
			(
				\s          |   # a whitespace char, or
				&nbsp;      |   # a non-breaking space entity, or
				--          |   # dashes, or
				&[mn]dash;  |   # named dash entities
				%s          |   # or decimal entities
				&\#x201[34];    # or hex
			)
			"                 # the quote
			(?=\w)            # followed by a word character
			""" % (dec_dashes,), re.VERBOSE)
	str = opening_double_quotes_regex.sub(r"""\1&#8220;""", str)

	# Double closing quotes:
	closing_double_quotes_regex = re.compile(r"""
			#(%s)?   # character that indicates the quote should be closing
			"
			(?=\s)
			""" % (close_class,), re.VERBOSE)
	str = closing_double_quotes_regex.sub(r"""&#8221;""", str)

	closing_double_quotes_regex = re.compile(r"""
			(%s)   # character that indicates the quote should be closing
			"
			""" % (close_class,), re.VERBOSE)
	str = closing_double_quotes_regex.sub(r"""\1&#8221;""", str)

	# Any remaining quotes should be opening ones.
	str = re.sub(r'"', r"""&#8220;""", str)

	return str


def educateBackticks(str):
	"""
	Parameter:  String.
	Returns:    The string, with ``backticks'' -style double quotes
	            translated into HTML curly quote entities.
	Example input:  ``Isn't this fun?''
	Example output: &#8220;Isn't this fun?&#8221;
	"""

	str = re.sub(r"""``""", r"""&#8220;""", str)
	str = re.sub(r"""''""", r"""&#8221;""", str)
	return str


def educateSingleBackticks(str):
	"""
	Parameter:  String.
	Returns:    The string, with `backticks' -style single quotes
	            translated into HTML curly quote entities.
	
	Example input:  `Isn't this fun?'
	Example output: &#8216;Isn&#8217;t this fun?&#8217;
	"""

	str = re.sub(r"""`""", r"""&#8216;""", str)
	str = re.sub(r"""'""", r"""&#8217;""", str)
	return str


def educateDashes(str):
	"""
	Parameter:  String.
	
	Returns:    The string, with each instance of "--" translated to
	            an em-dash HTML entity.
	"""

	str = re.sub(r"""---""", r"""&#8211;""", str) # en  (yes, backwards)
	str = re.sub(r"""--""", r"""&#8212;""", str) # em (yes, backwards)
	return str


def educateDashesOldSchool(str):
	"""
	Parameter:  String.
	
	Returns:    The string, with each instance of "--" translated to
	            an en-dash HTML entity, and each "---" translated to
	            an em-dash HTML entity.
	"""

	str = re.sub(r"""---""", r"""&#8212;""", str)    # em (yes, backwards)
	str = re.sub(r"""--""", r"""&#8211;""", str)    # en (yes, backwards)
	return str


def educateDashesOldSchoolInverted(str):
	"""
	Parameter:  String.
	
	Returns:    The string, with each instance of "--" translated to
	            an em-dash HTML entity, and each "---" translated to
	            an en-dash HTML entity. Two reasons why: First, unlike the
	            en- and em-dash syntax supported by
	            EducateDashesOldSchool(), it's compatible with existing
	            entries written before SmartyPants 1.1, back when "--" was
	            only used for em-dashes.  Second, em-dashes are more
	            common than en-dashes, and so it sort of makes sense that
	            the shortcut should be shorter to type. (Thanks to Aaron
	            Swartz for the idea.)
	"""
	str = re.sub(r"""---""", r"""&#8211;""", str)    # em
	str = re.sub(r"""--""", r"""&#8212;""", str)    # en
	return str



def educateEllipses(str):
	"""
	Parameter:  String.
	Returns:    The string, with each instance of "..." translated to
	            an ellipsis HTML entity.
	
	Example input:  Huh...?
	Example output: Huh&#8230;?
	"""

	str = re.sub(r"""\.\.\.""", r"""&#8230;""", str)
	str = re.sub(r"""\. \. \.""", r"""&#8230;""", str)
	return str


def stupefyEntities(str):
	"""
	Parameter:  String.
	Returns:    The string, with each SmartyPants HTML entity translated to
	            its ASCII counterpart.

	Example input:  &#8220;Hello &#8212; world.&#8221;
	Example output: "Hello -- world."
	"""

	str = re.sub(r"""&#8211;""", r"""-""", str)  # en-dash
	str = re.sub(r"""&#8212;""", r"""--""", str) # em-dash

	str = re.sub(r"""&#8216;""", r"""'""", str)  # open single quote
	str = re.sub(r"""&#8217;""", r"""'""", str)  # close single quote

	str = re.sub(r"""&#8220;""", r'''"''', str)  # open double quote
	str = re.sub(r"""&#8221;""", r'''"''', str)  # close double quote

	str = re.sub(r"""&#8230;""", r"""...""", str)# ellipsis

	return str


def processEscapes(str):
	r"""
	Parameter:  String.
	Returns:    The string, with after processing the following backslash
	            escape sequences. This is useful if you want to force a "dumb"
	            quote or other character to appear.
	
	            Escape  Value
	            ------  -----
	            \\      &#92;
	            \"      &#34;
	            \'      &#39;
	            \.      &#46;
	            \-      &#45;
	            \`      &#96;
	"""
	str = re.sub(r"""\\\\""", r"""&#92;""", str)
	str = re.sub(r'''\\"''', r"""&#34;""", str)
	str = re.sub(r"""\\'""", r"""&#39;""", str)
	str = re.sub(r"""\\\.""", r"""&#46;""", str)
	str = re.sub(r"""\\-""", r"""&#45;""", str)
	str = re.sub(r"""\\`""", r"""&#96;""", str)

	return str


def _tokenize(str):
	"""
	Parameter:  String containing HTML markup.
	Returns:    Reference to an array of the tokens comprising the input
	            string. Each token is either a tag (possibly with nested,
	            tags contained therein, such as <a href="<MTFoo>">, or a
	            run of text between tags. Each element of the array is a
	            two-element array; the first is either 'tag' or 'text';
	            the second is the actual value.
	
	Based on the _tokenize() subroutine from Brad Choate's MTRegex plugin.
	    <http://www.bradchoate.com/past/mtregex.php>
	"""

	pos = 0
	length = len(str)
	tokens = []

	depth = 6
	nested_tags = "|".join(['(?:<(?:[^<>]',] * depth) + (')*>)' * depth)
	#match = r"""(?: <! ( -- .*? -- \s* )+ > ) |  # comments
	#		(?: <\? .*? \?> ) |  # directives
	#		%s  # nested tags       """ % (nested_tags,)
	tag_soup = re.compile(r"""([^<]*)(<[^>]*>)""")

	token_match = tag_soup.search(str)

	previous_end = 0
	while token_match is not None:
		if token_match.group(1):
			tokens.append(['text', token_match.group(1)])

		tokens.append(['tag', token_match.group(2)])

		previous_end = token_match.end()
		token_match = tag_soup.search(str, token_match.end())

	if previous_end < len(str):
		tokens.append(['text', str[previous_end:]])

	return tokens



if __name__ == "__main__":

	import locale

	try:
		locale.setlocale(locale.LC_ALL, '')
	except:
		pass

	from docutils.core import publish_string
	docstring_html = publish_string(__doc__, writer_name='html')

	print docstring_html


	# Unit test output goes out stderr.  No worries.
	import unittest
	sp = smartyPants

	class TestSmartypantsAllAttributes(unittest.TestCase):
		# the default attribute is "1", which means "all".

		def test_dates(self):
			self.assertEqual(sp("1440-80's"), "1440-80&#8217;s")
			self.assertEqual(sp("1440-'80s"), "1440-&#8216;80s")
			self.assertEqual(sp("1440---'80s"), "1440&#8211;&#8216;80s")
			self.assertEqual(sp("1960s"), "1960s")  # no effect.
			self.assertEqual(sp("1960's"), "1960&#8217;s")
			self.assertEqual(sp("one two '60s"), "one two &#8216;60s")
			self.assertEqual(sp("'60s"), "&#8216;60s")

		def test_skip_tags(self):
			self.assertEqual(
				sp("""<script type="text/javascript">\n<!--\nvar href = "http://www.google.com";\nvar linktext = "google";\ndocument.write('<a href="' + href + '">' + linktext + "</a>");\n//-->\n</script>"""), 
				   """<script type="text/javascript">\n<!--\nvar href = "http://www.google.com";\nvar linktext = "google";\ndocument.write('<a href="' + href + '">' + linktext + "</a>");\n//-->\n</script>""")
			self.assertEqual(
				sp("""<p>He said &quot;Let's write some code.&quot; This code here <code>if True:\n\tprint &quot;Okay&quot;</code> is python code.</p>"""), 
				   """<p>He said &#8220;Let&#8217;s write some code.&#8221; This code here <code>if True:\n\tprint &quot;Okay&quot;</code> is python code.</p>""")


		def test_ordinal_numbers(self):
			self.assertEqual(sp("21st century"), "21st century")  # no effect.
			self.assertEqual(sp("3rd"), "3rd")  # no effect.

		def test_educated_quotes(self):
			self.assertEqual(sp('''"Isn't this fun?"'''), '''&#8220;Isn&#8217;t this fun?&#8221;''')

	unittest.main()




__author__ = "Chad Miller <smartypantspy@chad.org>"
__version__ = "1.5_1.6: Fri, 27 Jul 2007 07:06:40 -0400"
__url__ = "http://wiki.chad.org/SmartyPantsPy"
__description__ = "Smart-quotes, smart-ellipses, and smart-dashes for weblog entries in pyblosxom"

########NEW FILE########
__FILENAME__ = smart_if
"""
A smarter {% if %} tag for django templates.

While retaining current Django functionality, it also handles equality,
greater than and less than operators. Some common case examples::

    {% if articles|length >= 5 %}...{% endif %}
    {% if "ifnotequal tag" != "beautiful" %}...{% endif %}
"""
import unittest
from django import template


register = template.Library()


#==============================================================================
# Calculation objects
#==============================================================================

class BaseCalc(object):
    def __init__(self, var1, var2=None, negate=False):
        self.var1 = var1
        self.var2 = var2
        self.negate = negate

    def resolve(self, context):
        try:
            var1, var2 = self.resolve_vars(context)
            outcome = self.calculate(var1, var2)
        except:
            outcome = False
        if self.negate:
            return not outcome
        return outcome

    def resolve_vars(self, context):
        var2 = self.var2 and self.var2.resolve(context)
        return self.var1.resolve(context), var2

    def calculate(self, var1, var2):
        raise NotImplementedError()


class Or(BaseCalc):
    def calculate(self, var1, var2):
        return var1 or var2


class And(BaseCalc):
    def calculate(self, var1, var2):
        return var1 and var2


class Equals(BaseCalc):
    def calculate(self, var1, var2):
        return var1 == var2


class Greater(BaseCalc):
    def calculate(self, var1, var2):
        return var1 > var2


class GreaterOrEqual(BaseCalc):
    def calculate(self, var1, var2):
        return var1 >= var2


class In(BaseCalc):
    def calculate(self, var1, var2):
        return var1 in var2


#==============================================================================
# Tests
#==============================================================================

class TestVar(object):
    """
    A basic self-resolvable object similar to a Django template variable. Used
    to assist with tests.
    """
    def __init__(self, value):
        self.value = value

    def resolve(self, context):
        return self.value


class SmartIfTests(unittest.TestCase):
    def setUp(self):
        self.true = TestVar(True)
        self.false = TestVar(False)
        self.high = TestVar(9000)
        self.low = TestVar(1)

    def assertCalc(self, calc, context=None):
        """
        Test a calculation is True, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assert_(calc.resolve(context))
        calc.negate = not calc.negate
        self.assertFalse(calc.resolve(context))

    def assertCalcFalse(self, calc, context=None):
        """
        Test a calculation is False, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assertFalse(calc.resolve(context))
        calc.negate = not calc.negate
        self.assert_(calc.resolve(context))

    def test_or(self):
        self.assertCalc(Or(self.true))
        self.assertCalcFalse(Or(self.false))
        self.assertCalc(Or(self.true, self.true))
        self.assertCalc(Or(self.true, self.false))
        self.assertCalc(Or(self.false, self.true))
        self.assertCalcFalse(Or(self.false, self.false))

    def test_and(self):
        self.assertCalc(And(self.true, self.true))
        self.assertCalcFalse(And(self.true, self.false))
        self.assertCalcFalse(And(self.false, self.true))
        self.assertCalcFalse(And(self.false, self.false))

    def test_equals(self):
        self.assertCalc(Equals(self.low, self.low))
        self.assertCalcFalse(Equals(self.low, self.high))

    def test_greater(self):
        self.assertCalc(Greater(self.high, self.low))
        self.assertCalcFalse(Greater(self.low, self.low))
        self.assertCalcFalse(Greater(self.low, self.high))

    def test_greater_or_equal(self):
        self.assertCalc(GreaterOrEqual(self.high, self.low))
        self.assertCalc(GreaterOrEqual(self.low, self.low))
        self.assertCalcFalse(GreaterOrEqual(self.low, self.high))

    def test_in(self):
        list_ = TestVar([1,2,3])
        invalid_list = TestVar(None)
        self.assertCalc(In(self.low, list_))
        self.assertCalcFalse(In(self.low, invalid_list))

    def test_parse_bits(self):
        var = IfParser([True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([False, 'or', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([False, 'and', True]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser(['not', False, 'and', 'not', False]).parse()
        self.assert_(var.resolve({}))

        var = IfParser(['not', 'not', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '=', 1]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, 'not', '=', 1]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([1, 'not', 'not', '=', 1]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '!=', 1]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([3, '>', 2]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '<', 2]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([2, 'not', 'in', [2, 3]]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([1, 'or', 1, '=', 2]).parse()
        self.assert_(var.resolve({}))

    def test_boolean(self):
        var = IfParser([True, 'and', True, 'and', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([True, 'and', False, 'or', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([True, 'and', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'and', True, 'or', False]).parse()
        self.assertFalse(var.resolve({}))

    def test_invalid(self):
        self.assertRaises(ValueError, IfParser(['not']).parse)
        self.assertRaises(ValueError, IfParser(['==']).parse)
        self.assertRaises(ValueError, IfParser([1, 'in']).parse)
        self.assertRaises(ValueError, IfParser([1, '>', 'in']).parse)
        self.assertRaises(ValueError, IfParser([1, '==', 'not', 'not']).parse)
        self.assertRaises(ValueError, IfParser([1, 2]).parse)


OPERATORS = {
    '=': (Equals, True),
    '==': (Equals, True),
    '!=': (Equals, False),
    '>': (Greater, True),
    '>=': (GreaterOrEqual, True),
    '<=': (Greater, False),
    '<': (GreaterOrEqual, False),
    'or': (Or, True),
    'and': (And, True),
    'in': (In, True),
}
BOOL_OPERATORS = ('or', 'and')


class IfParser(object):
    error_class = ValueError

    def __init__(self, tokens):
        self.tokens = tokens

    def _get_tokens(self):
        return self._tokens

    def _set_tokens(self, tokens):
        self._tokens = tokens
        self.len = len(tokens)
        self.pos = 0

    tokens = property(_get_tokens, _set_tokens)

    def parse(self):
        if self.at_end():
            raise self.error_class('No variables provided.')
        var1 = self.get_bool_var()
        while not self.at_end():
            op, negate = self.get_operator()
            var2 = self.get_bool_var()
            var1 = op(var1, var2, negate=negate)
        return var1

    def get_token(self, eof_message=None, lookahead=False):
        negate = True
        token = None
        pos = self.pos
        while token is None or token == 'not':
            if pos >= self.len:
                if eof_message is None:
                    raise self.error_class()
                raise self.error_class(eof_message)
            token = self.tokens[pos]
            negate = not negate
            pos += 1
        if not lookahead:
            self.pos = pos
        return token, negate

    def at_end(self):
        return self.pos >= self.len

    def create_var(self, value):
        return TestVar(value)

    def get_bool_var(self):
        """
        Returns either a variable by itself or a non-boolean operation (such as
        ``x == 0`` or ``x < 0``).

        This is needed to keep correct precedence for boolean operations (i.e.
        ``x or x == 0`` should be ``x or (x == 0)``, not ``(x or x) == 0``).
        """
        var = self.get_var()
        if not self.at_end():
            op_token = self.get_token(lookahead=True)[0]
            if isinstance(op_token, basestring) and (op_token not in
                                                     BOOL_OPERATORS):
                op, negate = self.get_operator()
                return op(var, self.get_var(), negate=negate)
        return var

    def get_var(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting a variable.')
        if isinstance(token, basestring) and token in OPERATORS:
            raise self.error_class('Expected variable, got operator (%s).' %
                                   token)
        var = self.create_var(token)
        if negate:
            return Or(var, negate=True)
        return var

    def get_operator(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting an operator.')
        if not isinstance(token, basestring) or token not in OPERATORS:
            raise self.error_class('%s is not a valid operator.' % token)
        if self.at_end():
            raise self.error_class('No variable provided after "%s".' % token)
        op, true = OPERATORS[token]
        if not true:
            negate = not negate
        return op, negate


#==============================================================================
# Actual templatetag code.
#==============================================================================

class TemplateIfParser(IfParser):
    error_class = template.TemplateSyntaxError

    def __init__(self, parser, *args, **kwargs):
        self.template_parser = parser
        return super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return self.template_parser.compile_filter(value)


class SmartIfNode(template.Node):
    def __init__(self, var, nodelist_true, nodelist_false=None):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.var = var

    def render(self, context):
        if self.var.resolve(context):
            return self.nodelist_true.render(context)
        if self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

    def __repr__(self):
        return "<Smart If node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        if self.nodelist_false:
            for node in self.nodelist_false:
                yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        if self.nodelist_false:
            nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes


@register.tag('if')
def smart_if(parser, token):
    """
    A smarter {% if %} tag for django templates.

    While retaining current Django functionality, it also handles equality,
    greater than and less than operators. Some common case examples::

        {% if articles|length >= 5 %}...{% endif %}
        {% if "ifnotequal tag" != "beautiful" %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid smart if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``=`` (or ``==``),
    ``!=``, ``>``, ``>=``, ``<`` and ``<=``.
    """
    bits = token.split_contents()[1:]
    var = TemplateIfParser(parser, bits).parse()
    nodelist_true = parser.parse(('else', 'endif'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif',))
        parser.delete_first_token()
    else:
        nodelist_false = None
    return SmartIfNode(var, nodelist_true, nodelist_false)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = typogrify
import re
from django.conf import settings
from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

register = template.Library()

def amp(text):
    """Wraps apersands in HTML with ``<span class="amp">`` so they can be
    styled with CSS. Apersands are also normalized to ``&amp;``. Requires 
    ampersands to have whitespace or an ``&nbsp;`` on both sides.
    
    >>> amp('One & two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &amp; two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &#38; two')
    u'One <span class="amp">&amp;</span> two'

    >>> amp('One&nbsp;&amp;&nbsp;two')
    u'One&nbsp;<span class="amp">&amp;</span>&nbsp;two'

    It won't mess up & that are already wrapped, in entities or URLs

    >>> amp('One <span class="amp">&amp;</span> two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('&ldquo;this&rdquo; & <a href="/?that&amp;test">that</a>')
    u'&ldquo;this&rdquo; <span class="amp">&amp;</span> <a href="/?that&amp;test">that</a>'

    It should ignore standalone amps that are in attributes
    >>> amp('<link href="xyz.html" title="One & Two">xyz</link>')
    u'<link href="xyz.html" title="One & Two">xyz</link>'
    """
    text = force_unicode(text)
    # tag_pattern from http://haacked.com/archive/2004/10/25/usingregularexpressionstomatchhtml.aspx
    # it kinda sucks but it fixes the standalone amps in attributes bug
    tag_pattern = '</?\w+((\s+\w+(\s*=\s*(?:".*?"|\'.*?\'|[^\'">\s]+))?)+\s*|\s*)/?>'
    amp_finder = re.compile(r"(\s|&nbsp;)(&|&amp;|&\#38;)(\s|&nbsp;)")
    intra_tag_finder = re.compile(r'(?P<prefix>(%s)?)(?P<text>([^<]*))(?P<suffix>(%s)?)' % (tag_pattern, tag_pattern))
    def _amp_process(groups):
        prefix = groups.group('prefix') or ''
        text = amp_finder.sub(r"""\1<span class="amp">&amp;</span>\3""", groups.group('text'))
        suffix = groups.group('suffix') or ''
        return prefix + text + suffix
    output = intra_tag_finder.sub(_amp_process, text)
    return mark_safe(output)
amp.is_safe = True

def caps(text):
    """Wraps multiple capital letters in ``<span class="caps">`` 
    so they can be styled with CSS. 
    
    >>> caps("A message from KU")
    u'A message from <span class="caps">KU</span>'
    
    Uses the smartypants tokenizer to not screw with HTML or with tags it shouldn't.
    
    >>> caps("<PRE>CAPS</pre> more CAPS")
    u'<PRE>CAPS</pre> more <span class="caps">CAPS</span>'

    >>> caps("A message from 2KU2 with digits")
    u'A message from <span class="caps">2KU2</span> with digits'
        
    >>> caps("Dotted caps followed by spaces should never include them in the wrap D.O.T.   like so.")
    u'Dotted caps followed by spaces should never include them in the wrap <span class="caps">D.O.T.</span>  like so.'

    All caps with with apostrophes in them shouldn't break. Only handles dump apostrophes though.
    >>> caps("JIMMY'S")
    u'<span class="caps">JIMMY\\'S</span>'

    >>> caps("<i>D.O.T.</i>HE34T<b>RFID</b>")
    u'<i><span class="caps">D.O.T.</span></i><span class="caps">HE34T</span><b><span class="caps">RFID</span></b>'
    """
    text = force_unicode(text)
    try:
        import smartypants
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% caps %} filter: The Python SmartyPants library isn't installed."
        return text
        
    tokens = smartypants._tokenize(text)
    result = []
    in_skipped_tag = False    
    
    cap_finder = re.compile(r"""(
                            (\b[A-Z\d]*        # Group 2: Any amount of caps and digits
                            [A-Z]\d*[A-Z]      # A cap string much at least include two caps (but they can have digits between them)
                            [A-Z\d']*\b)       # Any amount of caps and digits or dumb apostsrophes
                            | (\b[A-Z]+\.\s?   # OR: Group 3: Some caps, followed by a '.' and an optional space
                            (?:[A-Z]+\.\s?)+)  # Followed by the same thing at least once more
                            (?:\s|\b|$))
                            """, re.VERBOSE)

    def _cap_wrapper(matchobj):
        """This is necessary to keep dotted cap strings to pick up extra spaces"""
        if matchobj.group(2):
            return """<span class="caps">%s</span>""" % matchobj.group(2)
        else:
            if matchobj.group(3)[-1] == " ":
                caps = matchobj.group(3)[:-1]
                tail = ' '
            else:
                caps = matchobj.group(3)
                tail = ''
            return """<span class="caps">%s</span>%s""" % (caps, tail)

    tags_to_skip_regex = re.compile("<(/)?(?:pre|code|kbd|script|math)[^>]*>", re.IGNORECASE)
    
    
    for token in tokens:
        if token[0] == "tag":
            # Don't mess with tags.
            result.append(token[1])
            close_match = tags_to_skip_regex.match(token[1])
            if close_match and close_match.group(1) == None:
                in_skipped_tag = True
            else:
                in_skipped_tag = False
        else:
            if in_skipped_tag:
                result.append(token[1])
            else:
                result.append(cap_finder.sub(_cap_wrapper, token[1]))
    output = "".join(result)
    return mark_safe(output)
caps.is_safe = True

def initial_quotes(text):
    """Wraps initial quotes in ``class="dquo"`` for double quotes or  
    ``class="quo"`` for single quotes. Works in these block tags ``(h1-h6, p, li, dt, dd)``
    and also accounts for potential opening inline elements ``a, em, strong, span, b, i``
    
    >>> initial_quotes('"With primes"')
    u'<span class="dquo">"</span>With primes"'
    >>> initial_quotes("'With single primes'")
    u'<span class="quo">\\'</span>With single primes\\''
    
    >>> initial_quotes('<a href="#">"With primes and a link"</a>')
    u'<a href="#"><span class="dquo">"</span>With primes and a link"</a>'
    
    >>> initial_quotes('&#8220;With smartypanted quotes&#8221;')
    u'<span class="dquo">&#8220;</span>With smartypanted quotes&#8221;'
    """
    text = force_unicode(text)
    quote_finder = re.compile(r"""((<(p|h[1-6]|li|dt|dd)[^>]*>|^)              # start with an opening p, h1-6, li, dd, dt or the start of the string
                                  \s*                                          # optional white space! 
                                  (<(a|em|span|strong|i|b)[^>]*>\s*)*)         # optional opening inline tags, with more optional white space for each.
                                  (("|&ldquo;|&\#8220;)|('|&lsquo;|&\#8216;))  # Find me a quote! (only need to find the left quotes and the primes)
                                                                               # double quotes are in group 7, singles in group 8 
                                  """, re.VERBOSE)
    def _quote_wrapper(matchobj):
        if matchobj.group(7): 
            classname = "dquo"
            quote = matchobj.group(7)
        else:
            classname = "quo"
            quote = matchobj.group(8)
        return """%s<span class="%s">%s</span>""" % (matchobj.group(1), classname, quote) 
    output = quote_finder.sub(_quote_wrapper, text)
    return mark_safe(output)
initial_quotes.is_safe = True

def smartypants(text):
    """Applies smarty pants to curl quotes.
    
    >>> smartypants('The "Green" man')
    u'The &#8220;Green&#8221; man'
    """
    text = force_unicode(text)
    try:
        import smartypants
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% smartypants %} filter: The Python smartypants library isn't installed."
        return text
    else:
        output = smartypants.smartyPants(text)
        return mark_safe(output)
smartypants.is_safe = True

def titlecase(text):
    """Support for titlecase.py's titlecasing

    >>> titlecase("this V that")
    u'This v That'

    >>> titlecase("this is just an example.com")
    u'This Is Just an example.com'
    """
    text = force_unicode(text)
    try:
        import titlecase
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% titlecase %} filter: The titlecase.py library isn't installed."
        return text
    else:
        return titlecase.titlecase(text)

def typogrify(text):
    """The super typography filter
    
    Applies the following filters: widont, smartypants, caps, amp, initial_quotes
    
    >>> typogrify('<h2>"Jayhawks" & KU fans act extremely obnoxiously</h2>')
    u'<h2><span class="dquo">&#8220;</span>Jayhawks&#8221; <span class="amp">&amp;</span> <span class="caps">KU</span> fans act extremely&nbsp;obnoxiously</h2>'

    Each filters properly handles autoescaping.
    >>> conditional_escape(typogrify('<h2>"Jayhawks" & KU fans act extremely obnoxiously</h2>'))
    u'<h2><span class="dquo">&#8220;</span>Jayhawks&#8221; <span class="amp">&amp;</span> <span class="caps">KU</span> fans act extremely&nbsp;obnoxiously</h2>'
    """
    text = force_unicode(text)
    text = amp(text)
    text = widont(text)
    text = smartypants(text)
    text = caps(text)
    text = initial_quotes(text)
    return text

def widont(text):
    """Replaces the space between the last two words in a string with ``&nbsp;``
    Works in these block tags ``(h1-h6, p, li, dd, dt)`` and also accounts for 
    potential closing inline elements ``a, em, strong, span, b, i``
    
    >>> widont('A very simple test')
    u'A very simple&nbsp;test'

    Single word items shouldn't be changed
    >>> widont('Test')
    u'Test'
    >>> widont(' Test')
    u' Test'
    >>> widont('<ul><li>Test</p></li><ul>')
    u'<ul><li>Test</p></li><ul>'
    >>> widont('<ul><li> Test</p></li><ul>')
    u'<ul><li> Test</p></li><ul>'
    
    >>> widont('<p>In a couple of paragraphs</p><p>paragraph two</p>')
    u'<p>In a couple of&nbsp;paragraphs</p><p>paragraph&nbsp;two</p>'
    
    >>> widont('<h1><a href="#">In a link inside a heading</i> </a></h1>')
    u'<h1><a href="#">In a link inside a&nbsp;heading</i> </a></h1>'
    
    >>> widont('<h1><a href="#">In a link</a> followed by other text</h1>')
    u'<h1><a href="#">In a link</a> followed by other&nbsp;text</h1>'

    Empty HTMLs shouldn't error
    >>> widont('<h1><a href="#"></a></h1>') 
    u'<h1><a href="#"></a></h1>'
    
    >>> widont('<div>Divs get no love!</div>')
    u'<div>Divs get no love!</div>'
    
    >>> widont('<pre>Neither do PREs</pre>')
    u'<pre>Neither do PREs</pre>'
    
    >>> widont('<div><p>But divs with paragraphs do!</p></div>')
    u'<div><p>But divs with paragraphs&nbsp;do!</p></div>'
    """
    text = force_unicode(text)
    widont_finder = re.compile(r"""((?:</?(?:a|em|span|strong|i|b)[^>]*>)|[^<>\s]) # must be proceeded by an approved inline opening or closing tag or a nontag/nonspace
                                   \s+                                             # the space to replace
                                   ([^<>\s]+                                       # must be flollowed by non-tag non-space characters
                                   \s*                                             # optional white space! 
                                   (</(a|em|span|strong|i|b)>\s*)*                 # optional closing inline tags with optional white space after each
                                   ((</(p|h[1-6]|li|dt|dd)>)|$))                   # end with a closing p, h1-6, li or the end of the string
                                   """, re.VERBOSE)
    output = widont_finder.sub(r'\1&nbsp;\2', text)
    return mark_safe(output)
widont.is_safe = True

register.filter('amp', amp)
register.filter('caps', caps)
register.filter('initial_quotes', initial_quotes)
register.filter('smartypants', smartypants)
register.filter('titlecase', titlecase)
register.filter('typogrify', typogrify)
register.filter('widont', widont)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.conf import settings

import mongoengine
from mongoengine.django.auth import User

import re
from datetime import datetime

from mumblr.entrytypes.core import TextEntry, HtmlComment, LinkEntry

mongoengine.connect('mumblr-unit-tests')


class MumblrTest(TestCase):

    urls = 'mumblr.urls'

    # Stop ORM-related stuff from happening as we don't use the ORM
    def _fixture_setup(self):
        pass
    def _fixture_teardown(self):
        pass

    def login(self):
        self.client.get('/admin/login/')
        data = self.user_data.copy()
        data['csrfmiddlewaretoken'] = self.get_csrf_token()
        return self.client.post('/admin/login/', data)

    def setUp(self):
        # Create a test user
        self.user_data = {
            'username': 'test',
            'password': 'testpassword123',
        }
        self.user = User.create_user(*self.user_data.values())

        # Create a test entry
        self.text_entry = TextEntry(title='Test-Entry', slug='test-entry')
        self.text_entry.tags = ['tests']
        self.text_entry.published = True
        self.text_entry.content = 'some-test-content'
        self.text_entry.rendered_content = '<p>some test content</p>'

        # Create test comment
        self.comment = HtmlComment(
            author='Mr Test',
            body='test comment',
            rendered_content = '<p>test comment</p>',
        )
        self.text_entry.comments = [self.comment]

        self.text_entry.save()

    def get_csrf_token(self):
        # Scrape CSRF token
        response = self.client.get('/admin/login/')
        csrf_regex = r'csrfmiddlewaretoken\'\s+value=\'(\w+)\''
        csrf_regex = r'value=\'(\w+)\''
        return re.search(csrf_regex, response.content).groups()[0]

    def test_recent_entries(self):
        """Ensure that the recent entries page works properly.
        """
        response = self.client.get('/')
        self.assertContains(response, self.text_entry.rendered_content, 
                            status_code=200)

    def test_entry_detail(self):
        """Ensure that the entry detail page works properly.
        """
        response = self.client.get(self.text_entry.get_absolute_url())
        self.assertContains(response, self.text_entry.rendered_content, 
                            status_code=200)

    def test_tagged_entries(self):
        """Ensure that the 'tagged entries' page works properly.
        """
        response = self.client.get('/tag/tests/')
        self.assertContains(response, self.text_entry.rendered_content, 
                            status_code=200)

        response = self.client.get('/tag/programming/')
        self.assertNotContains(response, self.text_entry.rendered_content, 
                               status_code=200)

    def test_tag_cloud(self):
        """Ensure that the 'tag cloud' page works properly.
        """
        response = self.client.get('/tags/')
        self.assertContains(response, 'tests', status_code=200)

    def test_add_link(self):
        """Ensure links get added properly, without nofollow attr
        """
        self.login()
        response = self.client.get('/admin/add/Lext')

        entry_data = {
            'title': 'Link Entry',
            'slug': 'link-entry',
            'tags': 'tests',
            'published': 'true',
            'content': 'test',
            'publish_date_year': datetime.now().year,
            'publish_date_month': datetime.now().month,
            'publish_date_day': datetime.now().day,
            'publish_time': datetime.now().strftime('%H:%M:%S'),
            'rendered_content': '<p>test</p>',
            'link_url': 'http://stevechallis.com/',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }
        # Check invalid form fails
        invalid_data = entry_data.copy()
        invalid_data['link_url'] = 'this-is-not-a-url'
        response = self.client.post('/admin/add/Link/', invalid_data)
        self.assertTemplateUsed(response, 'mumblr/admin/add_entry.html')

        # Check adding an entry does work
        response = self.client.post('/admin/add/text/', entry_data)
        entry = LinkEntry(slug=entry_data['slug'], publish_time=datetime.now())
        url = entry.get_absolute_url()
        self.assertRedirects(response, url, target_status_code=200)

        response = self.client.get(url)
        self.assertNotContains(response, 'rel="nofollow"')

        response = self.client.get('/')
        self.assertContains(response, entry_data['content'])

    def test_add_entry(self):
        """Ensure that entries may be added.
        """
        self.login()
        response = self.client.get('/admin/add/text/')

        entry_data = {
            'title': 'Second test entry',
            'slug': 'second-test-entry',
            'tags': 'tests',
            'published': 'true',
            'content': 'test',
            'publish_date_year': datetime.now().year,
            'publish_date_month': datetime.now().month,
            'publish_date_day': datetime.now().day,
            'publish_time': datetime.now().strftime('%H:%M:%S'),
            'rendered_content': '<p>test</p>',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }
        # Check invalid form fails
        response = self.client.post('/admin/add/text/', {
            'csrfmiddlewaretoken': self.get_csrf_token(),
            'content': 'test',
        })
        self.assertTemplateUsed(response, 'mumblr/admin/add_entry.html')

        # Check adding an entry does work
        response = self.client.post('/admin/add/text/', entry_data)
        entry = TextEntry(slug=entry_data['slug'], publish_time=datetime.now())
        url = entry.get_absolute_url()
        self.assertRedirects(response, url, target_status_code=200)

        response = self.client.get('/')
        self.assertContains(response, entry_data['content'])

    def test_add_comment(self):
        """Ensure that comments can be added
        """
        # Login to prevent Captcha
        self.login()
        add_url = self.text_entry.get_absolute_url()+'#comments'

        comment_data = {
            'author': 'Mr Test 2',
            'body': 'another-test-comment',
            'rendered_content': '<p>another-test-comment</p>',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }

        # Check invalid form fails
        response = self.client.post(add_url, {
            'body': 'test',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        })

        # Check adding comment works
        response = self.client.post(add_url, comment_data)
        self.assertRedirects(response, add_url, target_status_code=200)

        response = self.client.get(add_url)
        self.assertContains(response, comment_data['rendered_content'])

    def test_edit_entry(self):
        """Ensure that entries may be edited.
        """
        self.login()
        edit_url = '/admin/edit/%s/' % self.text_entry.id

        entry_data = {
            'title': self.text_entry.title,
            'slug': self.text_entry.slug,
            'published': 'true',
            'publish_date_year': datetime.now().year,
            'publish_date_month': datetime.now().month,
            'publish_date_day': datetime.now().day,
            'publish_time': datetime.now().strftime('%H:%M:%S'),
            'content': 'modified-test-content',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }
        # Check invalid form fails
        response = self.client.post(edit_url, {
            'content': 'test',
            'csrfmiddlewaretoken': self.get_csrf_token(),
        })
        self.assertTemplateUsed(response, 'mumblr/admin/add_entry.html')

        # Check editing an entry does work
        response = self.client.post(edit_url, entry_data)
        entry = TextEntry(slug=entry_data['slug'], publish_time=datetime.now())
        url = entry.get_absolute_url()
        self.assertRedirects(response, url, target_status_code=200)

        response = self.client.get('/')
        self.assertContains(response, entry_data['content'])

    def test_delete_entry(self):
        """Ensure that entries may be deleted.
        """
        delete_url = '/admin/delete/'
        data = {
            'entry_id': self.text_entry.id,
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }
        response = self.client.post(delete_url, data) 
        self.assertRedirects(response, '/admin/login/?next=' + delete_url,
                             target_status_code=200)

        self.login()

        data['csrfmiddlewaretoken'] = self.get_csrf_token()
        response = self.client.post(delete_url, data) 
        self.assertRedirects(response, '/')

        response = self.client.get('/')
        self.assertNotContains(response, self.text_entry.rendered_content, 
                               status_code=200)

    def test_delete_comment(self):
        """Ensure that comments can be deleted
        """
        self.login()

        data = {
            'comment_id': self.text_entry.comments[0].id,
            'csrfmiddlewaretoken': self.get_csrf_token(),
        }
        delete_url = '/admin/delete-comment/'

        response = self.client.post(delete_url, data)
        redirect_url = self.text_entry.get_absolute_url() + '#comments'
        self.assertRedirects(response, redirect_url)

        self.text_entry.reload()
        self.assertEqual(len(self.text_entry.comments), 0)

    def test_login_logout(self):
        """Ensure that users may log in and out.
        """
        # User not logged in
        response = self.client.get('/admin/login/')
        self.assertFalse(isinstance(response.context['user'], User))

        # User logging in
        data = self.user_data.copy()
        data['csrfmiddlewaretoken'] = self.get_csrf_token()
        response = self.client.post('/admin/login/', data)
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL, 
                             target_status_code=200)

        # User logged in
        response = self.client.get('/')
        self.assertTrue(isinstance(response.context['user'], User))

        response = self.client.get('/admin/logout/')
        self.assertRedirects(response, '/', target_status_code=200)

        # User logged out
        response = self.client.get('/admin/login/')
        self.assertFalse(isinstance(response.context['user'], User))

    def test_login_requred(self):
        """Ensure that a login is required for restricted pages.
        """
        restricted_pages = ['/admin/', '/admin/add/text/'] 
        restricted_pages.append('/admin/edit/%s/' % self.text_entry.id)
        restricted_pages.append('/admin/delete/')

        # Check in turn that each of the restricted pages may not be accessed
        for url in restricted_pages:
            response = self.client.get(url)
            self.assertRedirects(response, '/admin/login/?next=' + url,
                                 target_status_code=200)

        self.login()
        # Check in turn that each of the restricted pages may be accessed
        for url in restricted_pages:
            response = self.client.get(url, follow=True)
            self.assertFalse('/admin/login' in response.get('location', ''))

    def tearDown(self):
        self.user.delete()
        TextEntry.objects.delete()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib.auth.views import login, logout

from mumblr.views.core import (recent_entries, tagged_entries, entry_detail, 
                               tag_cloud, archive, RssFeed, AtomFeed)
from mumblr.views.admin import (dashboard, delete_entry, add_entry, edit_entry,
                                delete_comment)

feeds = {
    'rss': RssFeed,
    'atom': AtomFeed,
}

urlpatterns = patterns('',
    url('^$', recent_entries, name='recent-entries'),
    url('^(?P<page_number>\d+)/$', recent_entries, name='recent-entries'),
    url('^(\d{4}/\w{3}/\d{2})/([\w-]+)/$', entry_detail, name='entry-detail'),
    url('^tag/(?P<tag>[a-z0-9_-]+)/$', tagged_entries, name='tagged-entries'),
    url('^tag/(?P<tag>[a-z0-9_-]+)/(?P<page_number>\d+)/$', tagged_entries, 
        name='tagged-entries'),
    url('^archive/$', archive, name='archive'),
    url('^archive/(?P<page_number>\d+)/$', archive, name='archive'),
    url('^archive/(?P<entry_type>[a-z0-9_-]+)/$', archive, name='archive'),
    url('^archive/(?P<entry_type>[a-z0-9_-]+)/(?P<page_number>\d+)/$',
        archive, name='archive'),
    url('^tags/$', tag_cloud, name='tag-cloud'),
    url('^admin/$', dashboard, name='admin'),
    url('^admin/add/(\w+)/$', add_entry, name='add-entry'),
    url('^admin/edit/(\w+)/$', edit_entry, name='edit-entry'),
    url('^admin/delete/$', delete_entry, name='delete-entry'),
    url('^admin/delete-comment/$', delete_comment, name='delete-comment'),
    url('^admin/login/$', login, {'template_name': 'mumblr/admin/login.html'}, 
        name='log-in'),
    url('^admin/logout/$', logout, {'next_page': '/'}, name='log-out'),
    url('^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': feeds}, name='feeds'),
)

########NEW FILE########
__FILENAME__ = admin
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.conf import settings
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from django.template import defaultfilters

from datetime import datetime, time
from mongoengine.django.auth import REDIRECT_FIELD_NAME
from pymongo.son import SON
import string

from mumblr.entrytypes import markup, EntryType

def _lookup_template(name):
    return 'mumblr/admin/%s.html' % name

@login_required
def dashboard(request):
    """Display the main admin page.
    """
    entry_types = [e.type for e in EntryType._types.values()]
    entries = EntryType.objects.order_by('-publish_date')[:10]

    context = {
        'entry_types': entry_types,
        'entries': entries,
        'datenow': datetime.now(),
    }
    return render_to_response(_lookup_template('dashboard'), context,
                              context_instance=RequestContext(request))

@login_required
def edit_entry(request, entry_id):
    """Edit an existing entry.
    """
    entry = EntryType.objects.with_id(entry_id)
    if not entry:
        return HttpResponseRedirect(reverse('admin'))

    # Select correct form for entry type
    form_class = entry.AdminForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            # Get necessary post data from the form
            for field, value in form.cleaned_data.items():
                if field in entry._fields.keys():
                    entry[field] = value
            entry.save()
            return HttpResponseRedirect(entry.get_absolute_url())
    else:
        fields = entry._fields.keys()
        field_dict = dict([(name, entry[name]) for name in fields])

        # tags are stored as a list in the db, convert them back to a string
        field_dict['tags'] = ', '.join(field_dict['tags'])

        # publish_time and expiry_time are not initialised as they
        # don't have a field in the DB
        field_dict['publish_time'] = time(
            hour=entry.publish_date.hour,
            minute=entry.publish_date.minute,
            second=entry.publish_date.second,
        )
        if field_dict['expiry_date']:
            field_dict['expiry_time'] = time(
                hour=entry.expiry_date.hour,
                minute=entry.expiry_date.minute,
                second=entry.expiry_date.second,
            )
        form = form_class(field_dict)

    link_url = reverse('add-entry', args=['Link'])
    video_url = reverse('add-entry', args=['Video'])
    context = {
        'title': 'Edit an entry',
        'type': type, 
        'form': form,
        'link_url': request.build_absolute_uri(link_url),
        'video_url': request.build_absolute_uri(video_url),
    }
    return render_to_response(_lookup_template('add_entry'), context,
                              context_instance=RequestContext(request))

@login_required
def add_entry(request, type):
    """Display the 'Add an entry' form when GET is used, and add an entry to
    the database when POST is used.
    """
    # 'type' must be a valid entry type (e.g. html, image, etc..)
    if type.lower() not in EntryType._types:
        raise Http404

    # Use correct entry type Document class
    entry_type = EntryType._types[type.lower()]
    # Select correct form for entry type
    form_class = entry_type.AdminForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            entry = entry_type(**form.cleaned_data)

            # Save the entry to the DB
            entry.save()
            return HttpResponseRedirect(entry.get_absolute_url())
    else:
        initial = {
            'publish_date': datetime.now(),
            'publish_time': datetime.now().time(),
            'comments_enabled': True,
        }
        # Pass in inital values from query string - added by bookmarklet
        for field, value in request.GET.items():
            if field in form_class.base_fields:
                initial[field] = value
        
        if 'title' in initial:
            initial['slug'] = defaultfilters.slugify(initial['title'])

        form = form_class(initial=initial)

    link_url = reverse('add-entry', args=['Link'])
    video_url = reverse('add-entry', args=['Video'])
    context = {
        'title': 'Add %s Entry' % type,
        'type': type, 
        'form': form,
        'link_url': request.build_absolute_uri(link_url),
        'video_url': request.build_absolute_uri(video_url),
    }
    return render_to_response(_lookup_template('add_entry'), context,
                              context_instance=RequestContext(request))

@login_required
def delete_entry(request):
    """Delete an entry from the database.
    """
    entry_id = request.POST.get('entry_id', None)
    if request.method == 'POST' and entry_id:
        EntryType.objects.with_id(entry_id).delete()
    return HttpResponseRedirect(reverse('recent-entries'))

@login_required
def delete_comment(request):
    """Delete a comment from the database.
    """
    comment_id = request.POST.get('comment_id', None)
    if request.method == 'POST' and comment_id:
        # Delete matching comment from entry
        entry = EntryType.objects(comments__id=comment_id).first()
        if entry:
            entry.comments = [c for c in entry.comments if c.id != comment_id]
            entry.save()
        return HttpResponseRedirect(entry.get_absolute_url()+'#comments')
    return HttpResponseRedirect(reverse('recent-entries'))


########NEW FILE########
__FILENAME__ = core
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.conf import settings
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from django.utils.functional import lazy

from datetime import datetime, timedelta

from mumblr.entrytypes import markup, EntryType, Comment
from mumblr.entrytypes.core import HtmlComment

NO_ENTRIES_MESSAGES = (
    ('Have <a href="http://icanhazcheezburger.com">some kittens</a> instead.'),
    ('Have <a href="http://xkcd.com">a comic</a> instead.'),
    ('How about <a href="http://www.youtube.com/watch?v=oHg5SJYRHA0">'
     'a song</a> instead.'),
)

def _lookup_template(name):
    theme = getattr(settings, 'MUMBLR_THEME', 'default')
    return 'mumblr/themes/%s/%s.html' % (theme, name)

def archive(request, entry_type=None, page_number=1):
    """Display an archive of posts.
    """
    num = getattr(settings, 'MUMBLR_NUM_ENTRIES_PER_PAGE', 10)
    entry_types = [e.type for e in EntryType._types.values()]
    entry_class = EntryType
    type = "All"

    if entry_type and entry_type in [e.lower() for e in entry_types]:
        entry_class = EntryType._types[entry_type.lower()]
        type = entry_class.type

    paginator = Paginator(entry_class.live_entries(), num)
    try:
        entries = paginator.page(page_number)
    except (EmptyPage, InvalidPage):
        entries = paginator.page(paginator.num_pages)

    context = {
        'entry_types': entry_types,
        'entries': entries,
        'num_entries': entry_class.live_entries().count(),
        'entry_type': type,
    }
    return render_to_response(_lookup_template('archive'), context,
                              context_instance=RequestContext(request))

def recent_entries(request, page_number=1):
    """Show the [n] most recent entries.
    """
    num = getattr(settings, 'MUMBLR_NUM_ENTRIES_PER_PAGE', 10)
    entry_list = EntryType.live_entries()
    paginator = Paginator(entry_list, num)
    try:
        entries = paginator.page(page_number)
    except (EmptyPage, InvalidPage):
        entries = paginator.page(paginator.num_pages)
    context = {
        'title': 'Recent Entries',
        'entries': entries,
        'no_entries_messages': NO_ENTRIES_MESSAGES,
    }
    return render_to_response(_lookup_template('list_entries'), context,
                              context_instance=RequestContext(request))

def entry_detail(request, date, slug):
    """Display one entry with the given slug and date.
    """
    try:
        today = datetime.strptime(date, "%Y/%b/%d")
        tomorrow = today + timedelta(days=1)
    except:
        raise Http404

    try:
        entry = EntryType.objects(publish_date__gte=today, 
                                  publish_date__lt=tomorrow, slug=slug)[0]
    except IndexError:
        raise Http404

    # Select correct form for entry type
    form_class = Comment.CommentForm

    if request.method == 'POST':
        form = form_class(request.user, request.POST)
        if form.is_valid():
            # Get necessary post data from the form
            comment = HtmlComment(**form.cleaned_data)
            if request.user.is_authenticated():
                comment.is_admin = True
            # Update entry with comment
            q = EntryType.objects(id=entry.id)
            comment.rendered_content = markup(comment.body, escape=True,
                                              small_headings=True)
            q.update(push__comments=comment)

            return HttpResponseRedirect(entry.get_absolute_url()+'#comments')
    else:
        form = form_class(request.user)

    # Check for comment expiry
    comments_expired = False
    if entry.comments_expiry_date:
        if entry.comments_expiry_date < datetime.now():
            comments_expired = True

    context = {
        'entry': entry,
        'form': form,
        'comments_expired': comments_expired,
    }
    return render_to_response(_lookup_template('entry_detail'), context,
                              context_instance=RequestContext(request))

def tagged_entries(request, tag=None, page_number=1):
    """Show a list of all entries with the given tag.
    """
    tag = tag.strip().lower()
    num = getattr(settings, 'MUMBLR_NUM_ENTRIES_PER_PAGE', 10)
    entry_list = EntryType.live_entries(tags=tag)
    paginator = Paginator(entry_list, num)
    try:
        entries = paginator.page(page_number)
    except (EmptyPage, InvalidPage):
        entries = paginator.page(paginator.num_pages)
    context = {
        'title': 'Entries Tagged "%s"' % tag,
        'entries': entries,
        'no_entries_messages': NO_ENTRIES_MESSAGES,
    }
    return render_to_response(_lookup_template('list_entries'), context,
                              context_instance=RequestContext(request))

def tag_cloud(request):
    """A page containing a 'tag-cloud' of the tags present on entries.
    """
    entries = EntryType.live_entries
    
    freqs = entries.item_frequencies('tags', normalize=True)
    freqs = sorted(freqs.iteritems(), key=lambda (k,v):(v,k))
    freqs.reverse()

    context = {
        'tag_cloud': freqs,
    }
    return render_to_response(_lookup_template('tag_cloud'), context,
                              context_instance=RequestContext(request))


_lazy_reverse = lazy(reverse, str)

class RssFeed(Feed):
    title = getattr(settings, 'SITE_INFO_TITLE', 'Mumblr Recent Entries')
    link = _lazy_reverse('recent-entries')
    description = ""
    title_template = 'mumblr/feeds/rss_title.html'
    description_template = 'mumblr/feeds/rss_description.html'

    def items(self):
        return EntryType.live_entries[:30]

    def item_pubdate(self, item):
        return item.publish_date


class AtomFeed(RssFeed):
    feed_type = Atom1Feed
    subtitle = RssFeed.description
    title_template = 'mumblr/feeds/atom_title.html'
    description_template = 'mumblr/feeds/atom_description.html'

########NEW FILE########
