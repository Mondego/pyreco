__FILENAME__ = context_processors
from couch_lifestream import USERNAMES

def usernames(request):
    return dict(USERNAMES=USERNAMES)
########NEW FILE########
__FILENAME__ = fetch_lifestream_items
import datetime
import time
from django.core.management.base import NoArgsCommand
from django.conf import settings
from urllib2 import urlopen
from couch_lifestream import db

try:
    import simplejson as json
except ImportError:
    import json

from couch_lifestream import USERNAMES as un

### HELPER FUNCTIONS ###

def parse_json(url, item_type, callback, discriminator='id', list_key=None):
    print "Fetching %s items" % (item_type,)
    fetched = urlopen(url).read()
    data = json.loads(fetched)
    if list_key:
        data = data[list_key]
    map_fun = 'function(doc) { emit(doc.%s, null); }' % (discriminator,)
    for item in map(callback, data):
        item['item_type'] = item_type
        if len(db.query(map_fun, key=item[discriminator])) == 0:
            db.create(item)
    print "%s items fetched" % (item_type,)

def parse_feed(url, item_type, discriminator='id'):
    import feedparser
    print "Fetching %s items" % (item_type,)
    d = feedparser.parse(url)
    map_fun = 'function(doc) { emit(doc.%s, null); }' % (discriminator,)
    for item in map(dict, d['entries']):
        item['item_type'] = item_type
        item['couch_lifestream_date'] = datetime.datetime.fromtimestamp(
            time.mktime(item['updated_parsed']))
        if len(db.query(map_fun, key=item[discriminator])) == 0:
            for (key, val) in item.items():
                if 'parsed' in key:
                    del item[key]
                elif isinstance(val, datetime.datetime):
                    item[key] = val.isoformat()
                elif isinstance(val, datetime.date):
                    item[key] = val.isoformat()
            db.create(item)
    print "%s items fetched" % (item_type,)

### PER-SERVICE FUNCTIONS ###

def fetch_twitter_items():
    from dateutil.parser import parse
    def callback(item):
        item['couch_lifestream_date'] = parse(item['created_at']).isoformat()
        return item
    url = 'http://twitter.com/statuses/user_timeline.json?id=%s' % (un['TWITTER'],)
    parse_json(url, 'twitter', callback)

def fetch_reddit_items():
    reddit_like_url = 'http://www.reddit.com/user/%s/liked/.rss' % (un['REDDIT'],)
    parse_feed(reddit_like_url, 'reddit-like', discriminator='link')
    reddit_bookmark_url = 'http://www.reddit.com/user/%s/submitted/.rss' % (un['REDDIT'],)
    parse_feed(reddit_bookmark_url, 'reddit-bookmark', discriminator='link')
    reddit_comment_url = 'http://www.reddit.com/user/%s/comments/.rss' % (un['REDDIT'],)
    parse_feed(reddit_comment_url, 'reddit-comment', discriminator='link')

def fetch_flickr_items():
    flickr_url = 'http://api.flickr.com/services/feeds/photos_public.gne?format=atom&id=%s' % (un['FLICKR'],)
    parse_feed(flickr_url, 'flickr')

def fetch_github_items():
    github_url = 'http://github.com/%s.atom' % (un['GITHUB'],)
    parse_feed(github_url, 'github')

def fetch_digg_items():
    digg_digg_url = 'http://digg.com/users/%s/history/diggs.rss' % (un['DIGG'],)
    parse_feed(digg_digg_url, 'digg-digg', discriminator='link')
    digg_comment_url = 'http://digg.com/users/%s/history/comments.rss' % (un['DIGG'],)
    parse_feed(digg_comment_url, 'digg-comment', discriminator='link')
    digg_bookmark_url = 'http://digg.com/users/%s/history/submissions.rss' % (un['DIGG'],)
    parse_feed(digg_bookmark_url, 'digg-bookmark', discriminator='link')

def fetch_youtube_items():
    youtube_post_url = 'http://gdata.youtube.com/feeds/base/users/%s/uploads?alt=atom' % (un['YOUTUBE'],)
    parse_feed(youtube_post_url, 'youtube-post')
    youtube_favorite_url = 'http://gdata.youtube.com/feeds/base/users/%s/favorites?alt=atom' % (un['YOUTUBE'],)
    parse_feed(youtube_favorite_url, 'youtube-favorite')

def fetch_lastfm_items():
    lastfm_tracks_url = 'http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss' % (un['LASTFM'],)
    parse_feed(lastfm_tracks_url, 'lastfm-recent')

def fetch_pandora_items():
    pandora_bookmarks_url = 'http://feeds.pandora.com/feeds/people/%s/favorites.xml?max=10' % (un['PANDORA'],)
    parse_feed(pandora_bookmarks_url, 'pandora-bookmark')

def fetch_readernaut_items():
    readernaut_books_url = 'http://readernaut.com/rss/%s/books/' % (un['READERNAUT'],)
    parse_feed(readernaut_books_url, 'readernaut-book')
    readernaut_notes_url = 'http://readernaut.com/rss/%s/notes/' % (un['READERNAUT'],)
    parse_feed(readernaut_notes_url, 'readernaut-note')

def fetch_delicious_items():
    delicious_bookmark_url = 'http://feeds.delicious.com/v2/rss/%s?count=15' % (un['DELICIOUS'],)
    parse_feed(delicious_bookmark_url, 'delicious-bookmark', discriminator='comments')

def fetch_disqus_items():
    disqus_comment_url = 'http://disqus.com/people/%s/comments.rss' % (un['DISQUS'],)
    parse_feed(disqus_comment_url, 'disqus-comment', discriminator='link')

class Command(NoArgsCommand):
    help = 'Fetch the latest lifestream items and insert them into CouchDB.'
    
    def handle_noargs(self, **options):
        if un['TWITTER'] is not None:
            fetch_twitter_items()
        if un['REDDIT'] is not None:
            fetch_reddit_items()
        if un['FLICKR'] is not None:
            fetch_flickr_items()
        if un['GITHUB'] is not None:
            fetch_github_items()
        if un['DIGG'] is not None:
            fetch_digg_items()
        if un['YOUTUBE'] is not None:
            fetch_youtube_items()
        if un['LASTFM'] is not None:
            fetch_lastfm_items()
        if un['PANDORA'] is not None:
            fetch_pandora_items()
        if un['READERNAUT'] is not None:
            fetch_readernaut_items()
        if un['DELICIOUS'] is not None:
            fetch_delicious_items()
        if un['DISQUS'] is not None:
            fetch_disqus_items()
        print "Finished loading lifestream items."
########NEW FILE########
__FILENAME__ = models
# Not much to see here. We're using CouchDB :)
########NEW FILE########
__FILENAME__ = couch_lifestream_tags
import re
from django import template
from django import forms
from django.template.loader import render_to_string
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from couch_lifestream import db
from copy import copy

register = template.Library()

def do_display_lifestream_item(parser, token):
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r tag must be of format {%% %r ITEM %%}' % (token.contents.split()[0], token.contents.split()[0]))
    if len(split) != 2:
        raise template.TemplateSyntaxError('%r tag must be of format {%% %r ITEM %%}' % (token.contents.split()[0], token.contents.split()[0]))
    return DisplayLifestreamItemNode(split[1])

class DisplayLifestreamItemNode(template.Node):
    def __init__(self, row):
        self.row = template.Variable(row)
    
    def render(self, context):
        row = self.row.resolve(context)
        item = db[row.id]
        context_with_item = copy(context)
        context_with_item['item'] = item
        return render_to_string(
            'couch_lifestream/%s_item.html' % (item['item_type'],),
            context_with_item
        )

def do_get_id_for_doc(parser, token):
    try:
        split = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r tag must be of format {%% %r DOC as CONTEXT_VAR_NAME %%}' % (token.contents.split()[0], token.contents.split()[0]))
    if len(split) != 4:
        raise template.TemplateSyntaxError('%r tag must be of format {%% %r DOC as CONTEXT_VAR_NAME %%}' % (token.contents.split()[0], token.contents.split()[0]))
    return GetIdForDocNode(split[1], split[3])

class GetIdForDocNode(template.Node):
    def __init__(self, doc, context_var):
        self.doc = template.Variable(doc)
        self.context_var = context_var
    
    def render(self, context):
        doc = self.doc.resolve(context)
        context[self.context_var] = doc['_id']
        return ''

def extract_tags(value, arg):
    from BeautifulSoup import BeautifulSoup
    soup = BeautifulSoup(value)
    safe_tags = [s.strip() for s in arg.split()]
    return u''.join(map(unicode, soup.findAll(safe_tags)))

TWITTER_RE = re.compile('@(\S+)')

def twitterfy(value):
    return mark_safe(
        TWITTER_RE.sub(r'<a href="http://twitter.com/\1">@\1</a>',value)
    )
twitterfy = stringfilter(twitterfy)

register.tag('display_lifestream_item', do_display_lifestream_item)
register.tag('get_id_for_doc', do_get_id_for_doc)

register.filter('twitterfy', twitterfy)
register.filter('extract_tags', extract_tags)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('couch_lifestream.views',
    url(r'^$', 'items', name='clife_index'),
    url(r'^all/$', 'items', name='clife_all'),
    url(r'^service/(?P<service>\S+)/$', 'items', name='clife_service'),
    url(r'^item/(?P<id>\S+)/$', 'item', name='clife_item'),
)
########NEW FILE########
__FILENAME__ = views
from couch_lifestream import db, COUCHDB_DESIGN_DOCNAME
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404
from couchdb import client

def items(request, service=None, extra_context={},
    template='couch_lifestream/list.html'):
    kwargs = dict(descending=True)
    if service is None:
        item_type_viewname = '%s/by_date' % (COUCHDB_DESIGN_DOCNAME,)
        lifestream_items = db.view(item_type_viewname, **kwargs)
    else:
        item_type_viewname = '%s/item_type_date' % (COUCHDB_DESIGN_DOCNAME,)
        lifestream_items = db.view(item_type_viewname, **kwargs)[
            [service, "z"]:[service, None]]
    context = {
        'items': list(lifestream_items),
    }
    context.update(extra_context)
    return render_to_response(
        template,
        context,
        context_instance=RequestContext(request)
    )

def item(request, id, extra_context={}, template='couch_lifestream/item.html'):
    try:
        obj = db[id]
    except client.ResourceNotFound:
        raise Http404
    context = {
        'item': obj,
    }
    context.update(extra_context)
    return render_to_response(
        template,
        context,
        context_instance=RequestContext(request)
    )
########NEW FILE########
