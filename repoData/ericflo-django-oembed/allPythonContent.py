__FILENAME__ = admin
from django.contrib import admin

from oembed.models import ProviderRule, StoredOEmbed

admin.site.register(ProviderRule)
admin.site.register(StoredOEmbed)
########NEW FILE########
__FILENAME__ = core
import re
import urllib2
import gzip
from heapq import heappush, heappop
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
try:
    import simplejson
except ImportError:
    from django.utils import simplejson
from django.conf import settings
from django.utils.safestring import mark_safe
from oembed.models import ProviderRule, StoredOEmbed
from django.template.loader import render_to_string
import logging
logger = logging.getLogger("oembed core")

END_OVERRIDES = (')', ',', '.', '>', ']', ';')
MAX_WIDTH = getattr(settings, "OEMBED_MAX_WIDTH", 320)
MAX_HEIGHT = getattr(settings, "OEMBED_MAX_HEIGHT", 240)
FORMAT = getattr(settings, "OEMBED_FORMAT", "json")

def fetch(url, user_agent="django-oembed/0.1"):
    """
    Fetches from a URL, respecting GZip encoding, etc.
    """
    request = urllib2.Request(url)
    request.add_header('User-Agent', user_agent)
    request.add_header('Accept-Encoding', 'gzip')
    opener = urllib2.build_opener()
    f = opener.open(request)
    result = f.read()
    if f.headers.get('content-encoding', '') == 'gzip':
        result = gzip.GzipFile(fileobj=StringIO(result)).read()
    f.close()
    return result

def re_parts(regex_list, text):
    """
    An iterator that returns the entire text, but split by which regex it
    matched, or none at all.  If it did, the first value of the returned tuple
    is the index into the regex list, otherwise -1.

    >>> first_re = re.compile('asdf')
    >>> second_re = re.compile('an')
    >>> list(re_parts([first_re, second_re], 'This is an asdf test.'))
    [(-1, 'This is '), (1, 'an'), (-1, ' '), (0, 'asdf'), (-1, ' test.')]

    >>> list(re_parts([first_re, second_re], 'asdfasdfasdf'))
    [(0, 'asdf'), (0, 'asdf'), (0, 'asdf')]

    >>> list(re_parts([], 'This is an asdf test.'))
    [(-1, 'This is an asdf test.')]

    >>> third_re = re.compile('sdf')
    >>> list(re_parts([first_re, second_re, third_re], 'This is an asdf test.'))
    [(-1, 'This is '), (1, 'an'), (-1, ' '), (0, 'asdf'), (-1, ' test.')]
    """
    def match_compare(x, y):
        return x.start() - y.start()
    prev_end = 0
    iter_dict = dict((r, r.finditer(text)) for r in regex_list)
    
    # a heapq containing matches
    matches = []
    
    # bootstrap the search with the first hit for each iterator
    for regex, iterator in iter_dict.items():
        try:
            match = iterator.next()
            heappush(matches, (match.start(), match))
        except StopIteration:
            iter_dict.pop(regex)
    
    # process matches, revisiting each iterator from which a match is used
    while matches:
        # get the earliest match
        start, match = heappop(matches)
        end = match.end()
        if start > prev_end:
            # yield the text from current location to start of match
            yield (-1, text[prev_end:start])
        # yield the match
        yield (regex_list.index(match.re), text[start:end])
        # get the next match from the iterator for this match
        if match.re in iter_dict:
            try:
                newmatch = iter_dict[match.re].next()
                heappush(matches, (newmatch.start(), newmatch))
            except StopIteration:
                iter_dict.pop(match.re)
        prev_end = end

    # yield text from end of last match to end of text
    last_bit = text[prev_end:]
    if len(last_bit) > 0:
        yield (-1, last_bit)

def replace(text, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
    """
    Scans a block of text, replacing anything matched by a ``ProviderRule``
    pattern with an OEmbed html snippet, if possible.
    
    Templates should be stored at oembed/{format}.html, so for example:
        
        oembed/video.html
        
    These templates are passed a context variable, ``response``, which is a 
    dictionary representation of the response.
    """
    rules = list(ProviderRule.objects.all())
    patterns = [re.compile(r.regex) for r in rules] # Compiled patterns from the rules
    parts = [] # The parts that we will assemble into the final return value.
    indices = [] # List of indices of parts that need to be replaced with OEmbed stuff.
    indices_rules = [] # List of indices into the rules in order for which index was gotten by.
    urls = set() # A set of URLs to try to lookup from the database.
    stored = {} # A mapping of URLs to StoredOEmbed objects.
    index = 0
    # First we pass through the text, populating our data structures.
    for i, part in re_parts(patterns, text):
        if i == -1:
            parts.append(part)
            index += 1
        else:
            to_append = ""
            # If the link ends with one of our overrides, build a list
            while part[-1] in END_OVERRIDES:
                to_append += part[-1]
                part = part[:-1]
            indices.append(index)
            urls.add(part)
            indices_rules.append(i)
            parts.append(part)
            index += 1
            if to_append:
                parts.append(to_append)
                index += 1
    # Now we fetch a list of all stored patterns, and put it in a dictionary 
    # mapping the URL to to the stored model instance.
    for stored_embed in StoredOEmbed.objects.filter(match__in=urls, max_width=max_width, max_height = max_height):
        stored[stored_embed.match] = stored_embed
    # Now we're going to do the actual replacement of URL to embed.
    for i, id_to_replace in enumerate(indices):
        rule = rules[indices_rules[i]]
        part = parts[id_to_replace]
        try:
            # Try to grab the stored model instance from our dictionary, and
            # use the stored HTML fragment as a replacement.
            parts[id_to_replace] = stored[part].html
        except KeyError:
            try:
                # Build the URL based on the properties defined in the OEmbed spec.
                url = u"%s?url=%s&maxwidth=%s&maxheight=%s&format=%s" % (
                    rule.endpoint, part, max_width, max_height, FORMAT
                )
                # Fetch the link and parse the JSON.
                resp = simplejson.loads(fetch(url))
                
                # link types that don't have html elements aren't dealt with right now.
                if resp['type'] == 'link' and 'html' not in resp:
                    raise ValueError
                
                # Depending on the embed type, grab the associated template and
                # pass it the parsed JSON response as context.
                replacement = render_to_string('oembed/%s.html' % resp['type'], {'response': resp})
                if replacement:
                    stored_embed = StoredOEmbed.objects.create(
                        match = part,
                        max_width = max_width,
                        max_height = max_height,
                        html = replacement,
                    )
                    stored[stored_embed.match] = stored_embed
                    parts[id_to_replace] = replacement
                else:
                    raise ValueError
            except ValueError:
                parts[id_to_replace] = part
            except KeyError:
                parts[id_to_replace] = part
            except urllib2.HTTPError:
                parts[id_to_replace] = part
    # Combine the list into one string and return it.
    return mark_safe(u''.join(parts))

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models

JSON = 1
XML = 2
FORMAT_CHOICES = (
    (JSON, "JSON"),
    (XML, "XML"),
)

class ProviderRule(models.Model):
    name = models.CharField(max_length=128, null=True, blank=True)
    regex = models.CharField(max_length=2000)
    endpoint = models.CharField(max_length=2000)
    format = models.IntegerField(choices=FORMAT_CHOICES)
    
    def __unicode__(self):
        return self.name or self.endpoint

class StoredOEmbed(models.Model):
    match = models.TextField()
    max_width = models.IntegerField()
    max_height = models.IntegerField()
    html = models.TextField()
    date_added = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.match
########NEW FILE########
__FILENAME__ = oembed_tags
from django import template
from django.template.defaultfilters import stringfilter
from oembed.core import replace

register = template.Library()

def oembed(input, args):
    if args:
        width, height = args.lower().split('x')
        if not width and height:
            raise template.TemplateSyntaxError("Oembed's optional WIDTHxHEIGH" \
                "T argument requires WIDTH and HEIGHT to be positive integers.")
    else:
        width, height = None, None
    return replace(input, max_width=width, max_height=height)
oembed.is_safe = True
oembed = stringfilter(oembed)

register.filter('oembed', oembed)

def do_oembed(parser, token):
    """
    A node which parses everything between its two nodes, and replaces any links
    with OEmbed-provided objects, if possible.
    
    Supports one optional argument, which is the maximum width and height, 
    specified like so:
    
        {% oembed 640x480 %}http://www.viddler.com/explore/SYSTM/videos/49/{% endoembed %}
    """
    args = token.contents.split()
    if len(args) > 2:
        raise template.TemplateSyntaxError("Oembed tag takes only one (option" \
            "al) argument: WIDTHxHEIGHT, where WIDTH and HEIGHT are positive " \
            "integers.")
    if len(args) == 2:
        width, height = args[1].lower().split('x')
        if not width and height:
            raise template.TemplateSyntaxError("Oembed's optional WIDTHxHEIGH" \
                "T argument requires WIDTH and HEIGHT to be positive integers.")
    else:
        width, height = None, None
    nodelist = parser.parse(('endoembed',))
    parser.delete_first_token()
    return OEmbedNode(nodelist, width, height)

register.tag('oembed', do_oembed)

class OEmbedNode(template.Node):
    def __init__(self, nodelist, width, height):
        self.nodelist = nodelist
        self.width = width
        self.height = height
    
    def render(self, context):
        kwargs = {}
        if self.width and self.height:
            kwargs['max_width'] = self.width
            kwargs['max_height'] = self.height
        return replace(self.nodelist.render(context), **kwargs)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from oembed.core import replace

class OEmbedTests(TestCase):
    noembed = ur"This is text that should not match any regex."
    end = ur"There is this great video at %s"
    start = ur"%s is a video that I like."
    middle = ur"There is a movie here: %s and I really like it."
    trailing_comma = ur"This is great %s, but it might not work."
    trailing_period = ur"I like this video, located at %s."
    
    loc = u"http://www.viddler.com/explore/SYSTM/videos/49/"
    
    embed = u'<object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" width=\r\n"320" height="222" id="viddlerplayer-e5cb3aac"><param name="movie" value="http://www.viddler.com/player/e5cb3aac/" /><param name="allowScriptAccess" value="always" /><param name="wmode" value="transparent" /><param name="allowFullScreen" value="true" /><embed src="http://www.viddler.com/player/e5cb3aac/" width="320" height="222" type="application/x-shockwave-flash" allowScriptAccess="always" allowFullScreen="true" wmode="transparent" name="viddlerplayer-e5cb3aac" ></embed></object>'
    
    def testNoEmbed(self):
        self.assertEquals(
            replace(self.noembed),
            self.noembed
        )
    
    def testEnd(self):
        for text in (self.end, self.start, self.middle, self.trailing_comma, self.trailing_period):
            self.assertEquals(
                replace(text % self.loc),
                text % self.embed
            )
    
    def testManySameEmbeds(self):
        text = " ".join([self.middle % self.loc] * 100) 
        resp = " ".join([self.middle % self.embed] * 100)
        self.assertEquals(replace(text), resp)
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = runtests
import sys
sys.path.append('..')

import os
# Make a backup of DJANGO_SETTINGS_MODULE environment variable to restore later.
backup = os.environ.get('DJANGO_SETTINGS_MODULE', '')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.test.simple import run_tests

if __name__ == "__main__":
    failures = run_tests(['oembed',], verbosity=9)
    if failures:
        sys.exit(failures)
    # Reset the DJANGO_SETTINGS_MODULE to what it was before running tests.
    os.environ['DJANGO_SETTINGS_MODULE'] = backup

########NEW FILE########
__FILENAME__ = settings
DATABASE_ENGINE = 'sqlite3'
ROOT_URLCONF = ''
SITE_ID = 1
INSTALLED_APPS = (
    'oembed',
)

########NEW FILE########
