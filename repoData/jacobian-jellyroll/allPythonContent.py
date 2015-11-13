__FILENAME__ = bootstrap
#!/usr/bin/env python
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if is_jython:
    import subprocess
    
    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd', 
           quote(tmpeggs), 'zc.buildout'], 
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout',
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout
zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = admin
import django.forms
from django.contrib import admin
from jellyroll.models import Item, Bookmark, Track, Photo, WebSearch, Message
from jellyroll.models import WebSearchResult, Video, CodeRepository, CodeCommit

class ItemAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('timestamp', 'object_str')
    list_filter = ('content_type', 'timestamp')
    search_fields = ('object_str', 'tags')

class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('url', 'description')
    search_fields = ('url', 'description', 'thumbnail')
    
class TrackAdmin(admin.ModelAdmin):
    list_display = ('track_name', 'artist_name')
    search_fields = ('artist_name', 'track_name')

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'photo_id','description', 'taken_by')
    search_fields = ('title', 'description', 'taken_by')

class WebSearchResultInline(admin.TabularInline):
    model = WebSearchResult

class WebSearchAdmin(admin.ModelAdmin):
    list_display = ('query',)
    inlines = [WebSearchResultInline]

class MessageAdmin(admin.ModelAdmin):
    list_display = ('message',)

class WebSearchAdmin(admin.ModelAdmin):
    list_display = ('query',)

class VideoAdmin(admin.ModelAdmin):
    list_display = ('title',)

class CodeRepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'url')
    prepopulated_fields = {"slug": ("name",)}

    class CodeRepositoryForm(django.forms.ModelForm):
        class Meta:
            model = CodeRepository
            
        # Override the URL field to be more permissive
        url = django.forms.CharField(required=True, max_length=100)
        
    form = CodeRepositoryForm

class CodeCommitAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'repository')
    list_filter = ('repository',)
    search_fields = ('message',)

admin.site.register(Item, ItemAdmin)
admin.site.register(Bookmark, BookmarkAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(WebSearch, WebSearchAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(CodeRepository, CodeRepositoryAdmin)
admin.site.register(CodeCommit, CodeCommitAdmin)


########NEW FILE########
__FILENAME__ = jellyroll_update
import logging
import optparse
import jellyroll.providers
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        optparse.make_option(
            "-p", "--provider", 
            dest="providers", 
            action="append", 
            help="Only use certain provider(s)."
        ),
        optparse.make_option(
            "-l", "--list-providers", 
            action="store_true", 
            help="Display a list of active data providers."
        ),
    )
    
    def handle(self, *args, **options):
        level = {
            '0': logging.WARN, 
            '1': logging.INFO, 
            '2': logging.DEBUG
        }[options.get('verbosity', '0')]
        logging.basicConfig(level=level, format="%(name)s: %(levelname)s: %(message)s")

        if options['list_providers']:
            self.print_providers()
            return 0

        if options['providers']:
            for provider in options['providers']:
                if provider not in self.available_providers():
                    print "Invalid provider: %r" % provider
                    self.print_providers()
                    return 0

        jellyroll.providers.update(options['providers'])

    def available_providers(self):
        return jellyroll.providers.active_providers()

    def print_providers(self):
        available = sorted(self.available_providers().keys())
        print "Available data providers:"
        for provider in available:
            print "   ", provider
        

########NEW FILE########
__FILENAME__ = managers
import datetime
from django.db import models
from django.db.models import signals
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from tagging.fields import TagField

class ItemManager(models.Manager):
    
    def __init__(self):
        super(ItemManager, self).__init__()
        self.models_by_name = {}
    
    def create_or_update(self, instance, timestamp=None, url=None, tags="", source="INTERACTIVE", source_id="", **kwargs):
        """
        Create or update an Item from some instace.
        """
        # If the instance hasn't already been saved, save it first. This
        # requires disconnecting the post-save signal that might be sent to
        # this function (otherwise we could get an infinite loop).
        if instance._get_pk_val() is None:
            try:
                signals.post_save.disconnect(self.create_or_update, sender=type(instance))
            except Exception, err:
                reconnect = False
            else:
                reconnect = True
            instance.save()
            if reconnect:
                signals.post_save.connect(self.create_or_update, sender=type(instance))
        
        # Make sure the item "should" be registered.
        if not getattr(instance, "jellyrollable", True):
            return
        
        # Check to see if the timestamp is being updated, possibly pulling
        # the timestamp from the instance.
        if hasattr(instance, "timestamp"):
            timestamp = instance.timestamp
        if timestamp is None:
            update_timestamp = False
            timestamp = datetime.datetime.now()
        else:
            update_timestamp = True
                    
        # Ditto for tags.
        if not tags:
            for f in instance._meta.fields:
                if isinstance(f, TagField):
                    tags = getattr(instance, f.attname)
                    break

        if not url:
            if hasattr(instance,'url'):
                url = instance.url

        # Create the Item object.
        ctype = ContentType.objects.get_for_model(instance)
        item, created = self.get_or_create(
            content_type = ctype, 
            object_id = force_unicode(instance._get_pk_val()),
            defaults = dict(
                timestamp = timestamp,
                source = source,
                source_id = source_id,
                tags = tags,
                url = url,
            )
        )        
        item.tags = tags
        item.source = source
        item.source_id = source_id
        if update_timestamp:
            item.timestamp = timestamp
            
        # Save and return the item.
        item.save()
        return item
        
    def follow_model(self, model):
        """
        Follow a particular model class, updating associated Items automatically.
        """
        self.models_by_name[model.__name__.lower()] = model
        signals.post_save.connect(self.create_or_update, sender=model)
        
    def get_for_model(self, model):
        """
        Return a QuerySet of only items of a certain type.
        """
        return self.filter(content_type=ContentType.objects.get_for_model(model))
        
    def get_last_update_of_model(self, model, **kwargs):
        """
        Return the last time a given model's items were updated. Returns the
        epoch if the items were never updated.
        """
        qs = self.get_for_model(model)
        if kwargs:
            qs = qs.filter(**kwargs)
        try:
            return qs.order_by('-timestamp')[0].timestamp
        except IndexError:
            return datetime.datetime.fromtimestamp(0)

########NEW FILE########
__FILENAME__ = models
import urllib
import urlparse
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.utils import simplejson, text
from django.utils.encoding import smart_unicode
from jellyroll.managers import ItemManager
from tagging.fields import TagField

class Item(models.Model):
    """
    A generic jellyroll item. Slightly denormalized for performance.
    """
    
    # Generic relation to the object.
    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField()
    object = generic.GenericForeignKey('content_type', 'object_id')
    
    # "Standard" metadata each object provides.
    url = models.URLField(blank=True, max_length=1000)
    timestamp = models.DateTimeField()
    tags = TagField(max_length=2500)
    
    # Metadata about where the object "came from" -- used by data providers to
    # figure out which objects to update when asked.
    source = models.CharField(max_length=100, blank=True)
    source_id = models.TextField(blank=True)
    
    # Denormalized object __unicode__, for performance 
    object_str = models.TextField(blank=True)
    
    objects = ItemManager()
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = [("content_type", "object_id")]
    
    def __unicode__(self):
        return "%s: %s" % (self.content_type.model_class().__name__, self.object_str)
        
    def __cmp__(self, other):
        return cmp(self.timestamp, other.timestamp)
    
    def save(self, *args, **kwargs):
        ct = "%s_%s" % (self.content_type.app_label, self.content_type.model.lower())
        self.object_str = smart_unicode(self.object)
        super(Item, self).save(*args, **kwargs)

class Bookmark(models.Model):
    """
    A bookmarked link. The model is based on del.icio.us, with the added
    thumbnail field for ma.gnolia users.
    """
    
    url           = models.URLField(unique=True, max_length=1000)
    description   = models.CharField(max_length=255)
    extended      = models.TextField(blank=True)
    thumbnail     = models.ImageField(upload_to="img/jellyroll/bookmarks/%Y/%m", blank=True)
    thumbnail_url = models.URLField(blank=True, verify_exists=False, max_length=1000)
    
    def __unicode__(self):
        return self.url

class Track(models.Model):
    """A track you listened to. The model is based on last.fm."""
    
    artist_name = models.CharField(max_length=250)
    track_name  = models.CharField(max_length=250)
    url         = models.URLField(blank=True, max_length=1000)
    track_mbid  = models.CharField("MusicBrainz Track ID", max_length=36, blank=True)
    artist_mbid = models.CharField("MusicBrainz Artist ID", max_length=36, blank=True)
    
    def __unicode__(self):
        return "%s - %s" % (self.artist_name, self.track_name)

CC_LICENSES = (
    ('http://creativecommons.org/licenses/by/2.0/',         'CC Attribution'),
    ('http://creativecommons.org/licenses/by-nd/2.0/',      'CC Attribution-NoDerivs'),
    ('http://creativecommons.org/licenses/by-nc-nd/2.0/',   'CC Attribution-NonCommercial-NoDerivs'),
    ('http://creativecommons.org/licenses/by-nc/2.0/',      'CC Attribution-NonCommercial'),
    ('http://creativecommons.org/licenses/by-nc-sa/2.0/',   'CC Attribution-NonCommercial-ShareAlike'),
    ('http://creativecommons.org/licenses/by-sa/2.0/',      'CC Attribution-ShareAlike'),
)

class Photo(models.Model):
    """
    A photo someone took. This person could be you, in which case you can
    obviously do whatever you want with it. However, it could also have been
    taken by someone else, so in that case there's a few fields for storing the
    object's rights.
    
    The model is based on Flickr, and won't work with anything else :(
    """
    
    # Key Flickr info
    photo_id    = models.CharField(unique=True, primary_key=True, max_length=50)
    farm_id     = models.PositiveSmallIntegerField(null=True)
    server_id   = models.PositiveSmallIntegerField()
    secret      = models.CharField(max_length=30, blank=True)

    # Rights metadata
    taken_by    = models.CharField(max_length=100, blank=True)
    cc_license  = models.URLField(blank=True, choices=CC_LICENSES)
    
    # Main metadata
    title           = models.CharField(max_length=250)
    description     = models.TextField(blank=True)
    comment_count   = models.PositiveIntegerField(max_length=5, default=0)
    
    # Date metadata
    date_uploaded = models.DateTimeField(blank=True, null=True)
    date_updated  = models.DateTimeField(blank=True, null=True)
    
    # EXIF metadata
    _exif = models.TextField(blank=True)
    def _set_exif(self, d):
        self._exif = simplejson.dumps(d)
    def _get_exif(self):
        if self._exif:
            return simplejson.loads(self._exif)
        else:
            return {}
    exif = property(_get_exif, _set_exif, "Photo EXIF data, as a dict.")
    
    def _get_farm(self):
        if self.farm_id:
            return ''.join(["farm",str(self.farm_id),"."])
        return ''
    farm = property(_get_farm)

    def __unicode__(self):
        return self.title
    
    def url(self):
        return "http://www.flickr.com/photos/%s/%s/" % (self.taken_by, self.photo_id)
    url = property(url)
        
    def timestamp(self):
        return self.date_uploaded
    timestamp = property(timestamp)
    
    ### Image URLs ###
    
    def get_image_url(self, size=None):
        if size in list('mstbo'):
            return "http://%sstatic.flickr.com/%s/%s_%s_%s.jpg" % \
                (self.farm, self.server_id, self.photo_id, self.secret, size)
        else:
            return "http://%sstatic.flickr.com/%s/%s_%s.jpg" % \
                (self.farm, self.server_id, self.photo_id, self.secret)
    
    image_url       = property(lambda self: self.get_image_url())
    square_url      = property(lambda self: self.get_image_url('s'))
    thumbnail_url   = property(lambda self: self.get_image_url('t'))
    small_url       = property(lambda self: self.get_image_url('m'))
    large_url       = property(lambda self: self.get_image_url('b'))
    original_url    = property(lambda self: self.get_image_url('o'))
    
    ### Rights ###
    
    def license_code(self):
        if not self.cc_license:
            return None
        path = urlparse.urlparse(self.cc_license)[2]
        return path.split("/")[2]
    license_code = property(license_code)
    
    def taken_by_me(self):
        return self.taken_by == getattr(settings, "FLICKR_USERNAME", "")
    taken_by_me = property(taken_by_me)
    
    def can_republish(self):
        """
        Is it OK to republish this photo, or must it be linked only?
        """
        
        # If I took the photo, then it's always OK to republish.
        if self.taken_by_me:
            return True
        
        # If the photo has no CC license, then it's never OK to republish.
        elif self.license_code is None:
            return False
        
        # If the settings flags this site as "commercial" and it's an NC
        # license, then no republish for you.
        elif getattr(settings, "SITE_IS_COMMERCIAL", False) and "nc" in self.license_code:
            return False
        
        # Otherwise, we're OK to republish it.
        else:
            return True
    can_republish = property(can_republish)
    
    def derivative_ok(self):
        """Is it OK to produce derivative works?"""
        return self.can_republish and "nd" not in self.license_code
    derivative_ok = property(derivative_ok)
    
    def must_share_alike(self):
        """Must I share derivative works?"""
        return self.can_republish and "sa" in self.license_code
    must_share_alike = property(must_share_alike)

class SearchEngine(models.Model):
    """
    Simple encapsulation of a search engine.
    """
    name = models.CharField(max_length=200)
    home = models.URLField()
    search_template = models.URLField()
    
    def __unicode__(self):
        return self.name
        
class WebSearch(models.Model):
    """
    A search made with a search engine. Modeled after Google's search history,
    but (may/could/will) work with other sources.
    """
    engine = models.ForeignKey(SearchEngine, related_name="searches")
    query = models.CharField(max_length=250)
    
    class Meta:
        verbose_name_plural = "web searches"

    def __unicode__(self):
        return self.query
        
    def url(self):
        return self.engine.search_template % (urllib.quote_plus(self.query))
    url = property(url)
        
class WebSearchResult(models.Model):
    """
    A page viewed as a result of a WebSearch
    """
    search = models.ForeignKey(WebSearch, related_name="results")
    title  = models.CharField(max_length=250)
    url    = models.URLField()

    def __unicode__(self):
        return self.title

class VideoSource(models.Model):
    """
    A place you might view videos. Basically just an encapsulation for the
    "embed template" bit.
    """
    name = models.CharField(max_length=200)
    home = models.URLField()
    embed_template = models.URLField()
    
    def __unicode__(self):
        return self.name

class Video(models.Model):
    """A video you viewed."""
    
    source = models.ForeignKey(VideoSource, related_name="videos")
    title  = models.CharField(max_length=250)
    url    = models.URLField()

    def __unicode__(self):
        return self.title
        
    def docid(self):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(self.url)
        return query.split("=")[-1]
    docid = property(docid)
        
    def embed_url(self):
        return self.source.embed_template % self.docid
    embed_url = property(embed_url)

SCM_CHOICES = (
    ("svn", "Subversion"),
    ("git", "Git"),
)

class CodeRepository(models.Model):
    """
    A code repository that you check code into somewhere. Currently only SVN
    is supported, but other forms should be hard to support.
    """
    type = models.CharField(max_length=10, choices=SCM_CHOICES)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    username = models.CharField(max_length=100, help_text="Your username/email for this SCM.")
    public_changeset_template = models.URLField(
        verify_exists = False, blank = True,
        help_text = "Template for viewing a changeset publically. Use '%s' for the revision number")
    url = models.URLField()

    class Meta:
        verbose_name_plural = "code repositories"

    def __unicode__(self):
        return self.name

class CodeCommit(models.Model):
    """
    A code change you checked in.
    """
    repository = models.ForeignKey(CodeRepository, related_name="commits")
    revision = models.CharField(max_length=200)
    message = models.TextField()

    class Meta:
        ordering = ["-revision"]

    def __unicode__(self):
        return "[%s] %s" % (self.format_revision(), text.truncate_words(self.message, 10))

    def format_revision(self):
        """
        Shorten hashed revisions for nice reading.
        """
        try:
            return str(int(self.revision))
        except ValueError:
            return self.revision[:7]
    
    @property
    def url(self):
        if self.repository.public_changeset_template:
            return self.repository.public_changeset_template % self.revision
        return ""
    
class Message(models.Model):
    """
    A message, status update, or "tweet".
    """
    message = models.TextField()
    links = models.ManyToManyField('ContentLink',blank=True,null=True)
    
    def __unicode__(self):
        return text.truncate_words(self.message, 30)

class ContentLink(models.Model):
    """
    A non-resource reference to be associated with
    a model. 

    In other words, not the canonical location
    for a resource defined by a jellyroll model, but 
    instead a topical resource given in the resource 
    body itself in a format that varies across model
    type.

    """
    url = models.URLField()
    identifier = models.CharField(max_length=128)

    def __unicode__(self):
        return self.identifier

class Location(models.Model):
    """
    Where you are at a given moment in time.
    """
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    name = models.CharField(max_length=200, blank=True)
    
    def __unicode__(self):
        if self.name:
            return self.name
        else:
            return "(%s, %s)" % (self.longitude, self.latitude)
            
    @property
    def url(self):
        return "http://maps.google.com/maps?q=%s,%s" % (self.longitude, self.latitude)
        
# Register item objects to be "followed"
Item.objects.follow_model(Bookmark)
Item.objects.follow_model(Track)
Item.objects.follow_model(Photo)
Item.objects.follow_model(WebSearch)
Item.objects.follow_model(Video)
Item.objects.follow_model(CodeCommit)
Item.objects.follow_model(Message)
Item.objects.follow_model(Location)
########NEW FILE########
__FILENAME__ = delicious
import time
import dateutil.parser
import dateutil.tz
import logging
import urllib
from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode
from jellyroll.models import Item, Bookmark
from jellyroll.providers import utils

#
# Super-mini Delicious API
#
class DeliciousClient(object):
    """
    A super-minimal delicious client :)
    """

    lastcall = 0

    def __init__(self, username, password, method='v1'):
        self.username, self.password = username, password
        self.method = method

    def __getattr__(self, method):
        return DeliciousClient(self.username, self.password, '%s/%s' % (self.method, method))

    def __repr__(self):
        return "<DeliciousClient: %s>" % self.method

    def __call__(self, **params):
        # Enforce Yahoo's "no calls quicker than every 1 second" rule
        delta = time.time() - DeliciousClient.lastcall
        if delta < 2:
            time.sleep(2 - delta)
        DeliciousClient.lastcall = time.time()
        url = ("https://api.del.icio.us/%s?" % self.method) + urllib.urlencode(params)        
        return utils.getxml(url, username=self.username, password=self.password)

#
# Public API
#

log = logging.getLogger("jellyroll.providers.delicious")

def enabled():
    ok = hasattr(settings, 'DELICIOUS_USERNAME') and hasattr(settings, 'DELICIOUS_PASSWORD')
    if not ok:
        log.warn('The Delicious provider is not available because the '
                 'DELICIOUS_USERNAME and/or DELICIOUS_PASSWORD settings are '
                 'undefined.')
    return ok

def update():
    delicious = DeliciousClient(settings.DELICIOUS_USERNAME, settings.DELICIOUS_PASSWORD)

    # Check to see if we need an update
    last_update_date = Item.objects.get_last_update_of_model(Bookmark)
    last_post_date = utils.parsedate(delicious.posts.update().get("time"))
    if last_post_date <= last_update_date:
        log.info("Skipping update: last update date: %s; last post date: %s", last_update_date, last_post_date)
        return

    for datenode in reversed(list(delicious.posts.dates().getiterator('date'))):
        dt = utils.parsedate(datenode.get("date"))
        if dt > last_update_date:
            log.debug("There is a record indicating bookmarks have been added after our last update")
            _update_bookmarks_from_date(delicious, dt)

#
# Private API
#

def _update_bookmarks_from_date(delicious, dt):
    log.debug("Reading bookmarks from %s", dt)
    xml = delicious.posts.get(dt=dt.strftime("%Y-%m-%d"))
    for post in xml.getiterator('post'):
        info = dict((k, smart_unicode(post.get(k))) for k in post.keys())
        if (info.has_key("shared") and settings.DELICIOUS_GETDNS) or (not info.has_key("shared")):
            log.debug("Handling bookmark for %r", info["href"])
            _handle_bookmark(info)
        else:
            log.debug("Skipping bookmark for %r, app settings indicate to ignore bookmarks marked \"Do Not Share\"", info["href"])
_update_bookmarks_from_date = transaction.commit_on_success(_update_bookmarks_from_date)

def _handle_bookmark(info):
    b, created = Bookmark.objects.get_or_create(
        url = info['href'],
        defaults = dict(
            description = info['description'],
            extended = info.get('extended', ''),
        )
    )
    if not created:
        b.description = info['description']
        b.extended = info.get('extended', '')
        b.save()
    return Item.objects.create_or_update(
        instance = b, 
        timestamp = utils.parsedate(info['time']), 
        tags = info.get('tag', ''),
        source = __name__,
        source_id = info['hash'],
    )

########NEW FILE########
__FILENAME__ = flickr
import datetime
import logging
import urllib
from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode
from jellyroll.models import Item, Photo
from jellyroll.providers import utils

log = logging.getLogger("jellyroll.providers.flickr")

#
# Mini FlickrClient API
#

class FlickrError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
    def __str__(self):
        return 'FlickrError %s: %s' % (self.code, self.message)

class FlickrClient(object):
    def __init__(self, api_key, method='flickr'):
        self.api_key = api_key
        self.method = method
        
    def __getattr__(self, method):
        return FlickrClient(self.api_key, '%s.%s' % (self.method, method))
        
    def __repr__(self):
        return "<FlickrClient: %s>" % self.method
        
    def __call__(self, **params):
        params['method'] = self.method
        params['api_key'] = self.api_key
        params['format'] = 'json'
        params['nojsoncallback'] = '1'
        url = "http://flickr.com/services/rest/?" + urllib.urlencode(params)
        json = utils.getjson(url)
        if json.get("stat", "") == "fail":
            raise FlickrError(json["code"], json["message"])
        return json

#
# Public API
#
def enabled():
    ok = (hasattr(settings, "FLICKR_API_KEY") and
          hasattr(settings, "FLICKR_USER_ID") and
          hasattr(settings, "FLICKR_USERNAME"))
    if not ok:
      log.warn('The Flickr provider is not available because the '
               'FLICKR_API_KEY, FLICKR_USER_ID, and/or FLICKR_USERNAME settings '
               'are undefined.')
    return ok

def update():
    flickr = FlickrClient(settings.FLICKR_API_KEY)
    
    # Preload the list of licenses
    licenses = licenses = flickr.photos.licenses.getInfo()
    licenses = dict((l["id"], smart_unicode(l["url"])) for l in licenses["licenses"]["license"])
    
    # Handle update by pages until we see photos we've already handled
    last_update_date = Item.objects.get_last_update_of_model(Photo)
    page = 1
    while True:
        log.debug("Fetching page %s of photos", page)
        resp = flickr.people.getPublicPhotos(user_id=settings.FLICKR_USER_ID, extras="license,date_taken", per_page="500", page=str(page))
        photos = resp["photos"]
        if page > photos["pages"]:
            log.debug("Ran out of photos; stopping.")
            break
            
        for photodict in photos["photo"]:
            timestamp = utils.parsedate(str(photodict["datetaken"]))
            if timestamp < last_update_date:
                log.debug("Hit an old photo (taken %s; last update was %s); stopping.", timestamp, last_update_date)
                break
            
            photo_id = utils.safeint(photodict["id"])
            license = licenses[photodict["license"]]
            secret = smart_unicode(photodict["secret"])
            _handle_photo(flickr, photo_id, secret, license, timestamp)
            
        page += 1
        
#
# Private API
#

def _handle_photo(flickr, photo_id, secret, license, timestamp):
    info = flickr.photos.getInfo(photo_id=photo_id, secret=secret)["photo"]
    server_id = utils.safeint(info["server"])
    farm_id = utils.safeint(info["farm"])
    taken_by = smart_unicode(info["owner"]["username"])
    title = smart_unicode(info["title"]["_content"])
    description = smart_unicode(info["description"]["_content"])
    comment_count = utils.safeint(info["comments"]["_content"])
    date_uploaded = datetime.datetime.fromtimestamp(utils.safeint(info["dates"]["posted"]))
    date_updated = datetime.datetime.fromtimestamp(utils.safeint(info["dates"]["lastupdate"]))
    
    log.debug("Handling photo: %r (taken %s)" % (title, timestamp))
    photo, created = Photo.objects.get_or_create(
        photo_id      = str(photo_id),
        defaults = dict(
            server_id     = server_id,
            farm_id       = farm_id,
            secret        = secret,
            taken_by      = taken_by,
            cc_license    = license,
            title         = title,
            description   = description,
            comment_count = comment_count,
            date_uploaded = date_uploaded,
            date_updated  = date_updated,
        )
    )
    if created:
        photo.exif = _convert_exif(flickr.photos.getExif(photo_id=photo_id, secret=secret))
    else:
        photo.server_id     = server_id
        photo.farm_id       = farm_id
        photo.secret        = secret
        photo.taken_by      = taken_by
        photo.cc_license    = license
        photo.title         = title
        photo.description   = description
        photo.comment_count = comment_count
        photo.date_uploaded = date_uploaded
        photo.date_updated  = date_updated
    photo.save()
    
    return Item.objects.create_or_update(
        instance = photo, 
        timestamp = timestamp,
        tags = _convert_tags(info["tags"]),
        source = __name__,
    )
_handle_photo = transaction.commit_on_success(_handle_photo)

def _convert_exif(exif):
    converted = {}
    for e in exif["photo"]["exif"]:
        key = smart_unicode(e["label"])
        val = e.get("clean", e["raw"])["_content"]
        val = smart_unicode(val)
        converted[key] = val
    return converted

def _convert_tags(tags):
    return " ".join(set(t["_content"] for t in tags["tag"] if not t["machine_tag"]))

########NEW FILE########
__FILENAME__ = gitscm
import re
import time
import logging
import datetime
import shutil
import tempfile
from unipath import FSPath as Path
from django.db import transaction
from django.utils.encoding import smart_unicode
from jellyroll.models import Item, CodeRepository, CodeCommit
from jellyroll.providers import utils

try:
    import git
except ImportError:
    git = None


log = logging.getLogger("jellyroll.providers.gitscm")

#
# Public API
#
def enabled():
    ok = git is not None
    if not ok:
        log.warn("The GIT provider is not available because the GitPython module "
                 "isn't installed.")
    return ok

def update():
    for repository in CodeRepository.objects.filter(type="git"):
        _update_repository(repository)
        
#
# Private API
#

def _update_repository(repository):
    source_identifier = "%s:%s" % (__name__, repository.url)
    last_update_date = Item.objects.get_last_update_of_model(CodeCommit, source=source_identifier)
    log.info("Updating changes from %s since %s", repository.url, last_update_date)

    # Git chokes on the 1969-12-31 sentinal returned by 
    # get_last_update_of_model, so fix that up.
    if last_update_date.date() == datetime.date(1969, 12, 31):
        last_update_date = datetime.datetime(1970, 1, 1)

    working_dir, repo = _create_local_repo(repository)
    commits = repo.commits_since(since=last_update_date.strftime("%Y-%m-%d"))
    log.debug("Handling %s commits", len(commits))
    for commit in reversed(commits):
        if commit.author.email == repository.username:
            _handle_revision(repository, commit)
            
    log.debug("Removing working dir %s.", working_dir)
    shutil.rmtree(working_dir)

def _create_local_repo(repository):
    working_dir = tempfile.mkdtemp()
    g = git.Git(working_dir)

    log.debug("Cloning %s into %s", repository.url, working_dir)
    res = g.clone(repository.url)
    
    # This is pretty nasty.
    m = re.match('^Initialized empty Git repository in (.*)', res)
    repo_location = Path(m.group(1).rstrip('/'))
    if repo_location.name == ".git":
        repo_location = repo_location.parent
    return working_dir, git.Repo(repo_location)

@transaction.commit_on_success
def _handle_revision(repository, commit):
    log.debug("Handling [%s] from %s", commit.id[:7], repository.url)
    ci, created = CodeCommit.objects.get_or_create(
        revision = commit.id,
        repository = repository,
        defaults = {"message": smart_unicode(commit.message)}
    )
    if created:
        # stored as UTC
        timestamp = datetime.datetime.fromtimestamp(time.mktime(commit.committed_date))
        if utils.JELLYROLL_ADJUST_DATETIME:
            return utils.utc_to_local_timestamp(time.mktime(commit.committed_date))

        return Item.objects.create_or_update(
            instance = ci, 
            timestamp = timestamp,
            source = "%s:%s" % (__name__, repository.url),
        )

########NEW FILE########
__FILENAME__ = gsearch
import datetime
import feedparser
import urlparse
import logging
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import tzinfo
from django.utils.encoding import smart_unicode
from jellyroll.models import Item, SearchEngine, WebSearch, WebSearchResult
from jellyroll.models import VideoSource, Video
from jellyroll.providers import utils

RSS_URL = "https://%s:%s@www.google.com/searchhistory/?output=rss"
VIDEO_TAG_URL = "http://video.google.com/tags?docid=%s"

# Monkeypatch feedparser to understand smh:query_guid elements
feedparser._FeedParserMixin._start_smh_query_guid = lambda self, attrs: self.push("query_guid", 1)

log = logging.getLogger("jellyroll.providers.gsearch")

#
# Public API
#

def enabled():
    ok = hasattr(settings, 'GOOGLE_USERNAME') and hasattr(settings, 'GOOGLE_PASSWORD')
    if not ok:
        log.warn('The Google Search provider is not available because the '
                 'GOOGLE_USERNAME and/or GOOGLE_PASSWORD settings are '
                 'undefined.')
    return ok

def update():
    feed = feedparser.parse(RSS_URL % (settings.GOOGLE_USERNAME, settings.GOOGLE_PASSWORD))
    for entry in feed.entries:
        if entry.tags[0].term == "web query":
            _handle_query(entry)
        elif entry.tags[0].term == "web result":
            _handle_result(entry)
        elif entry.tags[0].term == "video result":
            _handle_video(entry)
        
#
# Private API
#

# Shortcut
CT = ContentType.objects.get_for_model

def _handle_query(entry):
    engine = SearchEngine.objects.get(name="Google")
    guid = smart_unicode(urlparse.urlsplit(entry.guid)[2].replace("/searchhistory/", ""))
    query = smart_unicode(entry.title)
    timestamp = datetime.datetime(tzinfo=tzinfo.FixedOffset(0), *entry.updated_parsed[:6])
    
    log.debug("Handling Google query for %r", query)
    try:
        item = Item.objects.get(
            content_type = CT(WebSearch),
            source = __name__,
            source_id = guid
        )
    except Item.DoesNotExist:
        item = Item.objects.create_or_update(
            instance = WebSearch(engine=engine, query=query), 
            timestamp = timestamp,
            source = __name__,
            source_id = guid,
        )
_handle_query = transaction.commit_on_success(_handle_query)
    
def _handle_result(entry):
    guid = smart_unicode(entry.query_guid)
    title = smart_unicode(entry.title)
    url = smart_unicode(entry.link)

    log.debug("Adding search result: %r" % url)
    try:
        item = Item.objects.get(
            content_type = CT(WebSearch),
            source = __name__,
            source_id = guid
        )
    except Item.DoesNotExist:
        log.debug("Skipping unknown query GUID: %r" % guid)
        return
    
    WebSearchResult.objects.get_or_create(
        search = item.object,
        url = url,
        defaults = {'title' : title},
    )
_handle_result = transaction.commit_on_success(_handle_result)
    
def _handle_video(entry):
    vs = VideoSource.objects.get(name="Google")
    url = smart_unicode(entry.link)
    title = smart_unicode(entry.title)
    timestamp = datetime.datetime(tzinfo=tzinfo.FixedOffset(0), *entry.updated_parsed[:6])
    
    log.debug("Adding viewed video: %r" % title)
    vid, created = Video.objects.get_or_create(
        source = vs,
        url = url,
        defaults = {'title' : title},
    )
    return Item.objects.create_or_update(
        instance = vid, 
        timestamp = timestamp,
        source = __name__,
    )
_handle_video = transaction.commit_on_success(_handle_video)

########NEW FILE########
__FILENAME__ = lastfm
import datetime
import hashlib
import logging
from django.conf import settings
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.functional import memoize
from django.utils.http import urlquote
from django.utils.encoding import smart_str, smart_unicode
from httplib2 import HttpLib2Error
from jellyroll.models import Item, Track
from jellyroll.providers import utils

#
# API URLs
#

RECENT_TRACKS_URL = "http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.xml?limit=100"
TRACK_TAGS_URL    = "http://ws.audioscrobbler.com/1.0/track/%s/%s/toptags.xml"
ARTIST_TAGS_URL   = "http://ws.audioscrobbler.com/1.0/artist/%s/toptags.xml"

#
# Public API
#

log = logging.getLogger("jellyroll.providers.lastfm")

def enabled():
    ok = hasattr(settings, 'LASTFM_USERNAME')
    if not ok:
        log.warn('The Last.fm provider is not available because the '
                 'LASTFM_USERNAME settings is undefined.')
    return ok

def update():
    last_update_date = Item.objects.get_last_update_of_model(Track)
    log.debug("Last update date: %s", last_update_date)
    
    xml = utils.getxml(RECENT_TRACKS_URL % settings.LASTFM_USERNAME)
    for track in xml.getiterator("track"):
        artist      = track.find('artist')
        artist_name = smart_unicode(artist.text)
        artist_mbid = artist.get('mbid')
        track_name  = smart_unicode(track.find('name').text)
        track_mbid  = smart_unicode(track.find('mbid').text)
        url         = smart_unicode(track.find('url').text)

        # date delivered as UTC
        timestamp = datetime.datetime.fromtimestamp(int(track.find('date').get('uts')))
        if utils.JELLYROLL_ADJUST_DATETIME:
            timestamp = utils.utc_to_local_timestamp(int(track.find('date').get('uts')))

        if not _track_exists(artist_name, track_name, timestamp):
            tags = _tags_for_track(artist_name, track_name)
            _handle_track(artist_name, artist_mbid, track_name, track_mbid, url, timestamp, tags)

#
# Private API
#

def _tags_for_track(artist_name, track_name):
    """
    Get the top tags for a track. Also fetches tags for the artist. Only
    includes tracks that break a certain threshold of usage, defined by
    settings.LASTFM_TAG_USAGE_THRESHOLD (which defaults to 15).
    """
    
    urls = [
        ARTIST_TAGS_URL % (urlquote(artist_name)),
        TRACK_TAGS_URL % (urlquote(artist_name), urlquote(track_name)),
    ]
    tags = set()
    for url in urls:
        tags.update(_tags_for_url(url))
        
def _tags_for_url(url):
    tags = set()
    try:
        xml = utils.getxml(url)
    except HttpLib2Error, e:
        if e.code == 408:
            return ""
        else:
            raise
    except SyntaxError:
        return ""
    for t in xml.getiterator("tag"):
        count = utils.safeint(t.find("count").text)
        if count >= getattr(settings, 'LASTFM_TAG_USAGE_THRESHOLD', 15):
            tag = slugify(smart_unicode(t.find("name").text))
            tags.add(tag[:50])
    
    return tags
            
# Memoize tags to avoid unnecessary API calls.
_tag_cache = {}
_tags_for_url = memoize(_tags_for_url, _tag_cache, 1)

@transaction.commit_on_success
def _handle_track(artist_name, artist_mbid, track_name, track_mbid, url, timestamp, tags):
    t = Track(
        artist_name = artist_name,
        track_name  = track_name,
        url         = url,
        track_mbid  = track_mbid is not None and track_mbid or '',
        artist_mbid = artist_mbid is not None and artist_mbid or '',
    )
    if not _track_exists(artist_name, track_name, timestamp):
        log.debug("Saving track: %r - %r", artist_name, track_name)
        return Item.objects.create_or_update(
            instance = t,
            timestamp = timestamp,
            tags = tags,
            source = __name__,
            source_id = _source_id(artist_name, track_name, timestamp),
        )
        
def _source_id(artist_name, track_name, timestamp):
    return hashlib.md5(smart_str(artist_name) + smart_str(track_name) + str(timestamp)).hexdigest()
    
def _track_exists(artist_name, track_name, timestamp):
    id = _source_id(artist_name, track_name, timestamp)
    try:
        Item.objects.get(source=__name__, source_id=id)
    except Item.DoesNotExist:
        return False
    else:
        return True


########NEW FILE########
__FILENAME__ = latitude
"""
Provide location from Google Latitude.

Requires that you've turned on public location at
http://www.google.com/latitude/apps/badge.
"""

import datetime
import logging
from django.conf import settings
from django.db import transaction
from jellyroll.models import Location, Item
from jellyroll.providers import utils

log = logging.getLogger("jellyroll.providers.latitude")

#
# Public API
#
def enabled():
    ok = hasattr(settings, 'GOOGLE_LATITUDE_USER_ID')
    if not ok:
        log.warn('The Latitude provider is not available because the '
                 'GOOGLE_LATITUDE_USER_ID settings is undefined.')
    return ok

def update():
    last_update_date = Item.objects.get_last_update_of_model(Location)
    log.debug("Last update date: %s", last_update_date)
    _update_location(settings.GOOGLE_LATITUDE_USER_ID, since=last_update_date)
        
#
# Private API
#

@transaction.commit_on_success
def _update_location(user_id, since):
    json = utils.getjson('http://www.google.com/latitude/apps/badge/api?user=%s&type=json' % user_id)
    feature = json['features'][0]
    
    lat, lng = map(str, feature['geometry']['coordinates'])
    name = feature['properties']['reverseGeocode']
    timestamp = datetime.datetime.fromtimestamp(feature['properties']['timeStamp'])
    if timestamp > since:
        log.debug("New location: %s", name)
        loc = Location(latitude=lat, longitude=lng, name=name)
        return Item.objects.create_or_update(
            instance = loc,
            timestamp = timestamp,
            source = __name__,
            source_id = str(feature['properties']['timeStamp']),
        )
########NEW FILE########
__FILENAME__ = svn
import time
import logging
import datetime
from django.db import transaction
from django.utils.encoding import smart_unicode
from jellyroll.models import Item, CodeRepository, CodeCommit
from jellyroll.providers import utils


try:
    import pysvn
except ImportError:
    pysvn = None

log = logging.getLogger("jellyroll.providers.svn")

#
# Public API
#
def enabled():
    ok = pysvn is not None
    if not ok:
        log.warn("The SVN provider is not available because the pysvn module "
                 "isn't installed.")
    return ok

def update():
    for repository in CodeRepository.objects.filter(type="svn"):
        _update_repository(repository)
        
#
# Private API
#

def _update_repository(repository):
    source_identifier = "%s:%s" % (__name__, repository.url)
    last_update_date = Item.objects.get_last_update_of_model(CodeCommit, source=source_identifier)
    log.info("Updating changes from %s since %s", repository.url, last_update_date)
    rev = pysvn.Revision(pysvn.opt_revision_kind.date, time.mktime(last_update_date.timetuple()))
    c = pysvn.Client()
    for revision in reversed(c.log(repository.url, revision_end=rev)):
        if revision.author == repository.username:
            _handle_revision(repository, revision)

def _handle_revision(repository, r):
    log.debug("Handling [%s] from %s" % (r.revision.number, repository.url))
    ci, created = CodeCommit.objects.get_or_create(
        revision = str(r.revision.number),
        repository = repository,
        defaults = {"message": smart_unicode(r.message)}
    )
    if created:
        return Item.objects.create_or_update(
            instance = ci, 
            timestamp = datetime.datetime.fromtimestamp(r.date),
            source = "%s:%s" % (__name__, repository.url),
        )
_handle_revision = transaction.commit_on_success(_handle_revision)

########NEW FILE########
__FILENAME__ = twitter
import hashlib
import datetime
import logging
import dateutil
import re
from django.conf import settings
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.functional import memoize
from django.utils.http import urlquote
from django.utils.encoding import smart_str, smart_unicode
from httplib2 import HttpLib2Error
from jellyroll.providers import utils
from jellyroll.models import Item, Message, ContentLink


#
# API URLs
#

RECENT_STATUSES_URL = "http://twitter.com/statuses/user_timeline/%s.rss"
USER_URL = "http://twitter.com/%s"

#
# Public API
#

log = logging.getLogger("jellyroll.providers.twitter")

def enabled():
    return True

def update():
    last_update_date = Item.objects.get_last_update_of_model(Message)
    log.debug("Last update date: %s", last_update_date)
    
    xml = utils.getxml(RECENT_STATUSES_URL % settings.TWITTER_USERNAME)
    for status in xml.getiterator("item"):
        message      = status.find('title')
        message_text = smart_unicode(message.text)
        url          = smart_unicode(status.find('link').text)

        # pubDate delivered as UTC
        timestamp    = dateutil.parser.parse(status.find('pubDate').text)
        if utils.JELLYROLL_ADJUST_DATETIME:
            timestamp = utils.utc_to_local_datetime(timestamp)

        if not _status_exists(message_text, url, timestamp):
            _handle_status(message_text, url, timestamp)

#
# GLOBAL CLUTTER
#

TWITTER_TRANSFORM_MSG = False
TWITTER_RETWEET_TXT = "Forwarding from %s: "
try:
    TWITTER_TRANSFORM_MSG = settings.TWITTER_TRANSFORM_MSG
    TWITTER_RETWEET_TXT = settings.TWITTER_RETWEET_TXT
except AttributeError:
    pass

if TWITTER_TRANSFORM_MSG:
    USER_LINK_TPL = '<a href="%s" title="%s">%s</a>'
    TAG_RE = re.compile(r'(?P<tag>\#\w+)')
    USER_RE = re.compile(r'(?P<username>@\w+)')
    RT_RE = re.compile(r'RT\s+(?P<username>@\w+)')
    USERNAME_RE = re.compile(r'^%s:'%settings.TWITTER_USERNAME)

    # modified from django.forms.fields.url_re
    URL_RE = re.compile(
        r'https?://'
        r'(?:(?:[A-Z0-9-]+\.)+[A-Z]{2,6}|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/\S+|/?)', re.IGNORECASE)

    def _transform_retweet(matchobj):
        if '%s' in TWITTER_RETWEET_TXT:
            return TWITTER_RETWEET_TXT % matchobj.group('username')
        return TWITTER_RETWEET_TXT

    def _transform_user_ref_to_link(matchobj):
        user = matchobj.group('username')[1:]
        link = USER_URL % user
        return USER_LINK_TPL % \
            (link,user,''.join(['@',user]))

    def _parse_message(message_text):
        """
        Parse out some semantics for teh lulz.
        
        """
        links = list()
        tags = ""

        # remove newlines
        message_text = message_text.replace('\n','')
        # generate link list for ContentLink
        links = [ link for link in URL_RE.findall(message_text) ]
        link_ctr = 1
        link_dict = {}
        for link in URL_RE.finditer(message_text):
            link_dict[link.group(0)] = link_ctr
            link_ctr += 1
        generate_link_num = lambda obj: "[%d]"%link_dict[obj.group(0)]
        # remove URLs referenced in message content
        if not hasattr(settings, 'TWITTER_REMOVE_LINKS') or settings.TWITTER_REMOVE_LINKS == True:
        	message_text = URL_RE.sub(generate_link_num,message_text)
        # remove leading username
        message_text = USERNAME_RE.sub('',message_text)
        # check for RT-type retweet syntax
        message_text = RT_RE.sub(_transform_retweet,message_text)
        # replace @user references with links to their timeline
        message_text = USER_RE.sub(_transform_user_ref_to_link,message_text)
        # generate tags list
        tags = ' '.join( [tag[1:] for tag in TAG_RE.findall(message_text)] )
        # extract defacto #tag style tweet tags
        if not hasattr(settings, 'TWITTER_REMOVE_TAGS') or settings.TWITTER_REMOVE_TAGS == True:
            message_text = TAG_RE.sub('',message_text)

        return (message_text.strip(),links,tags)

    log.info("Enabling message transforms")
else:
    _parse_message = lambda msg: (msg,list(),"")
    log.info("Disabling message transforms")

#
# Private API
#

@transaction.commit_on_success
def _handle_status(message_text, url, timestamp):
    message_text, links, tags = _parse_message(message_text)

    t = Message(
        message = message_text,
        )

    if not _status_exists(message_text, url, timestamp):
        log.debug("Saving message: %r", message_text)
        item = Item.objects.create_or_update(
            instance = t,
            timestamp = timestamp,
            source = __name__,
            source_id = _source_id(message_text, url, timestamp),
            url = url,
            tags = tags,
            )
        item.save()

        for link in links:
            l = ContentLink(
                url = link,
                identifier = link,
                )
            l.save()
            t.links.add(l)

def _source_id(message_text, url, timestamp):
    return hashlib.md5(smart_str(message_text) + smart_str(url) + str(timestamp)).hexdigest()
    
def _status_exists(message_text, url, timestamp):
    id = _source_id(message_text, url, timestamp)
    try:
        Item.objects.get(source=__name__, source_id=id)
    except Item.DoesNotExist:
        return False
    else:
        return True

########NEW FILE########
__FILENAME__ = anyetree
"""
Get an Etree library.  Usage::

    >>> from anyetree import etree

Returns some etree library. Looks for (in order of decreasing preference):

    * ``lxml.etree`` (http://cheeseshop.python.org/pypi/lxml/)
    * ``xml.etree.cElementTree`` (built into Python 2.5)
    * ``cElementTree`` (http://effbot.org/zone/celementtree.htm)
    * ``xml.etree.ElementTree`` (built into Python 2.5)
    * ``elementree.ElementTree (http://effbot.org/zone/element-index.htm)
"""

__all__ = ['etree']

SEARCH_PATHS = [
    "lxml.etree",
    "xml.etree.cElementTree",
    "cElementTree",
    "xml.etree.ElementTree",
    "elementtree.ElementTree",
]

etree = None

for name in SEARCH_PATHS:
    try:
        etree = __import__(name, '', '', [''])
        break
    except ImportError:
        continue

if etree is None:
    raise ImportError("No suitable ElementTree implementation found.")
########NEW FILE########
__FILENAME__ = youtube
import datetime
import logging
import feedparser
from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode, smart_str
from django.utils.encoding import DjangoUnicodeDecodeError
from jellyroll.models import Item, VideoSource, Video
from jellyroll.providers import utils

TAG_SCHEME = 'http://gdata.youtube.com/schemas/2007/keywords.cat'
FEED_URL = 'http://gdata.youtube.com/feeds/api/users/%s/favorites?v=2&start-index=%s&max-results=%s'

log = logging.getLogger("jellyroll.providers.youtube")

#
# Public API
#
def enabled():
    ok = hasattr(settings, "YOUTUBE_USERNAME")
    if not ok:
        log.warn('The Youtube provider is not available because the '
                 'YOUTUBE_USERNAME settings is undefined undefined.')
    return ok

def update():    
    start_index = 1
    max_results = 50
    while True:
        log.debug("Fetching videos %s - %s" % (start_index, start_index+max_results-1))
        feed = feedparser.parse(FEED_URL % (settings.YOUTUBE_USERNAME, start_index, max_results))
        for entry in feed.entries:            
            if 'link' in entry:
                url = entry.link
            elif 'yt_videoid' in entry:
                url = 'http://www.youtube.com/watch?v=%s' % entry.yt_videoid
            else:
                log.error("Video '%s' appears to have no link" % (entry.tite))
                continue
                
            _handle_video(
                title = entry.title, 
                url = url,
                tags = " ".join(t['term'] for t in entry.tags if t['scheme'] == TAG_SCHEME),
                timestamp = datetime.datetime(*entry.published_parsed[:6]),
            )
        if len(feed.entries) < max_results:
            log.debug("Ran out of results; finishing.")
            break
            
        start_index += max_results
#
# Private API
#

@transaction.commit_on_success
def _handle_video(title, url, tags, timestamp):
    log.debug("Handling video: %s" % smart_str(title))
    source = VideoSource.objects.get(name="YouTube")
    
    # For some strange reason sometimes the YouTube API returns
    # corrupted titles...
    try:
        title = smart_unicode(title)
    except DjangoUnicodeDecodeError:
        return
        
    vid, created = Video.objects.get_or_create(
        url = url, 
        defaults = {
            'title': title, 
            'source': source
        }
    )
    if created:
        return Item.objects.create_or_update(
            instance = vid, 
            timestamp = timestamp,
            tags = tags,
            source = __name__,
        )

########NEW FILE########
__FILENAME__ = jellyroll
import datetime
import dateutil.parser
import urllib
from django import template
from django.db import models
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType

try:
    from collections import defaultdict
except ImportError:
    defaultdict = None


# Hack until relative imports
Item = models.get_model("jellyroll", "item")

register = template.Library()

def jellyrender(parser, token):
    """
    Render a jellyroll ``Item`` by passing it through a snippet template.
    
    ::
    
        {% jellyrender <item> [using <template>] [as <varname>] %}
    
    A sub-template will be used to render the item. Templates will be searched
    in this order:

        * The template given with the ``using <template>`` clause, if given.
    
        * ``jellyroll/snippets/<classname>.html``, where ``classname`` is the
          name of the specific item class (i.e. ``photo``).
          
        * ``jellyroll/snippets/item.html``.
        
    The template will be passed a context containing:
    
        ``item``
            The jellyroll ``Item`` object
    
        ``object``
            The actual object (i.e. ``item.object``).
            
    The rendered content will be displayed in the template unless the ``as
    <varname>`` clause is used to redirect the output into a context variable.
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise template.TemplateSyntaxError("%r tag takes at least one argument" % bits[0])
    
    item = bits[1]
    args = {}
    
    # Parse out extra clauses if given
    if len(bits) > 2:
        biter = iter(bits[2:])
        for bit in biter:
            if bit == "using":
                args["using"] = biter.next()
            elif bit == "as":
                args["asvar"] = biter.next()
            else:
                raise template.TemplateSyntaxError("%r tag got an unknown argument: %r" % (bits[0], bit))
            
    return JellyrenderNode(item, **args)
jellyrender = register.tag(jellyrender)
    
class JellyrenderNode(template.Node):
        
    def __init__(self, item, using=None, asvar=None):
        self.item = item
        self.using = using
        self.asvar = asvar
        
    def render(self, context):
        try:
            item = template.resolve_variable(self.item, context)
        except template.VariableDoesNotExist:
            return ""
                
        if isinstance(item, Item):
            object = item.object
        
        # If the item isn't an Item, try to look one up.
        else:
            object = item
            ct = ContentType.objects.get_for_model(item)
            try:
                item = Item.objects.get(content_type=ct, object_id=object._get_pk_val())
            except Item.DoesNotExist:
                return ""
                
        # Figure out which templates to use
        template_list = [
            "jellyroll/snippets/%s.html" % type(object).__name__.lower(), 
            "jellyroll/snippets/item.html"
        ]
        if self.using:
            try:
                using = template.resolve_variable(self.using, context)
            except template.VariableDoesNotExist:
                pass
            else:
                template_list.insert(0, using)
                
        # Render content, and save to self.asvar if requested
        context.push()
        context.update({
            "item" : item,
            "object" : object
        })
        rendered = render_to_string(template_list, context)
        context.pop()
        if self.asvar:
            context[self.asvar] = rendered
            return ""
        else:
            return rendered
            
def get_jellyroll_items(parser, token):
    """
    Load jellyroll ``Item`` objects into the context.In the simplest mode, the
    most recent N items will be returned.
    
    ::
    
        {# Fetch 10 most recent items #}
        {% get_jellyroll_items limit 10 as items %}
        
    Newer items will be first in the list (i.e. ordered by timstamp descending)
    unless you ask for them to be reversed::
    
        {# Fetch the 10 earliest items #}
        {% get_jellyroll_items limit 10 reversed as items %}
    
    You can also fetch items between two given dates::
    
        {% get_jellyroll_items between "2007-01-01" and "2007-01-31" as items %}
        
    Dates can be in any format understood by ``dateutil.parser``, and can of
    course be variables. Items must be limited in some way; you must either pass
    ``limit`` or ``between``.
    
    Dates can also be the magic strings "now" or "today"::
    
        {% get_jellyroll_items between "2007-01-01" and "today" as items %}
    
    You can also limit items by type::
    
        {# Fetch the 10 most recent videos and photos #}
        {% get_jellyroll_items oftype video oftype photo limit 10 as items %}
    
    ``oftype`` can be given as many times as you like; only those types will be
    returned. The arguments to ``oftype`` are the lowercased class names of
    jellyroll'd items. 
    
    You can similarly exclude types using ``excludetype``::
    
        {# Fetch the 10 most items that are not videos #}
        {% get_jellyroll_items excludetype video limit 10 as items %}
        
    You can give ``excludetype`` as many times as you like, but it is an error
    to use both ``oftype`` and ``excludetype`` in the same tag invocation.
    """
    
    # Parse out the arguments
    bits = token.split_contents()
    tagname = bits[0]
    bits = iter(bits[1:])
    args = {}
    for bit in bits:
        try:
            if bit == "limit":
                try:
                    args["limit"] = int(bits.next())
                except ValueError:
                    raise template.TemplateSyntaxError("%r tag: 'limit' requires an integer argument" % tagname)
            elif bit == "between":
                args["start"] = bits.next()
                and_ = bits.next()
                args["end"] = bits.next()
                if and_ != "and":
                    raise template.TemplateSyntaxError("%r tag: expected 'and' in 'between' clause, but got %r" % (tagname, and_))
            elif bit == "oftype":
                args.setdefault("oftypes", []).append(bits.next())
            elif bit == "excludetype":
                args.setdefault("excludetypes", []).append(bits.next())
            elif bit == "reversed":
                args["reversed"] = True
            elif bit == "as":
                args["asvar"] = bits.next()
            else:
                raise template.TemplateSyntaxError("%r tag: unknown argument: %r" % (tagname, bit))
        except StopIteration:
            raise template.TemplateSyntaxError("%r tag: an out of arguments when parsing %r clause" % (tagname, bit))
    
    # Make sure "as" was given
    if "asvar" not in args:
        raise template.TemplateSyntaxError("%r tag: missing 'as'" % tagname)
    
    # Either "limit" or "between" has to be specified
    if "limit" not in args and ("start" not in args or "end" not in args):
        raise template.TemplateSyntaxError("%r tag: 'limit' or a full 'between' clause is required" % tagname)
    
    # It's an error to have both "oftype" and "excludetype"
    if "oftype" in args and "excludetype" in args:
        raise template.TemplateSyntaxError("%r tag: can't handle both 'oftype' and 'excludetype'" % tagname)
    
    # Each of the "oftype" and "excludetype" arguments has be a valid model
    for arg in ("oftypes", "excludetypes"):
        if arg in args:
            model_list = []
            for name in args[arg]:
                try:
                    model_list.append(Item.objects.models_by_name[name])
                except KeyError:
                    raise template.TemplateSyntaxError("%r tag: invalid model name: %r" % (tagname, name))
            args[arg] = model_list
    
    return GetJellyrollItemsNode(**args)
get_jellyroll_items = register.tag(get_jellyroll_items)

class GetJellyrollItemsNode(template.Node):
    def __init__(self, asvar, limit=None, start=None, end=None, oftypes=[], excludetypes=[], reversed=False):
        self.asvar = asvar
        self.limit = limit
        self.start = start
        self.end = end
        self.oftypes = oftypes
        self.excludetypes = excludetypes
        self.reversed = reversed
        
    def render(self, context):
        qs = Item.objects.all()
        
        # Handle start/end dates if given
        if self.start:
            start = self.resolve_date(self.start, context)
            end = self.resolve_date(self.end, context)
            if start is None or end is None:
                return ""
            qs = qs.filter(timestamp__range=(start, end))
            
        # Handle types
        CT = ContentType.objects.get_for_model
        if self.oftypes:
            qs = qs.filter(content_type__id__in=[CT(m).id for m in self.oftypes])
        if self.excludetypes:
            qs = qs.exclude(content_type__id__in=[CT(m).id for m in self.excludetypes])
            
        # Handle reversed
        if self.reversed:
            qs = qs.order_by("timestamp")
        else:
            qs = qs.order_by("-timestamp")
            
        # Handle limit
        if self.limit:
            qs = qs[:self.limit]
            
        # Set the context
        context[self.asvar] = list(qs)
        return ""
        
    def resolve_date(self, d, context):
        """Resolve start/end, handling literals"""
        try:
            d = template.resolve_variable(d, context)
        except template.VariableDoesNotExist:
            return None
        
        # Handle date objects
        if isinstance(d, (datetime.date, datetime.datetime)):
            return d
        
        # Assume literals or strings
        if d == "now":
            return datetime.datetime.now()
        if d == "today":
            return datetime.date.today()
        try:
            return dateutil.parser.parse(d)
        except ValueError:
            return None

def get_jellyroll_recent_traffic(parser, token):
    oftypes = []
    bits = token.split_contents()
    if len(bits) < 4 or len(bits) > 5:
        raise template.TemplateSyntaxError("%r tag takes three arguments" % bits[0])
    elif bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to %r tag should be 'as'" % bits[0])
    if len(bits) > 4:
        oftypes = bits[4]
    return JellyrollRecentTrafficNode(bits[1],bits[3],oftypes)
get_jellyroll_recent_traffic = register.tag(get_jellyroll_recent_traffic)

class JellyrollRecentTrafficNode(template.Node):
    def __init__(self, days, context_var, oftypes=[]):
        self.days = int(days)
        self.oftypes = oftypes.split(",")
        self.context_var = context_var

    def render(self, context):
        CT = ContentType.objects.get_for_model
        dt_start = datetime.date.today()
        data = []

        if self.oftypes:
            if defaultdict:
                data = defaultdict(list)
            else:
                for item_type in self.oftypes: data[item_type] = []

        for offset in range(0,self.days):
            dt = dt_start - datetime.timedelta(days=offset)
            step = datetime.timedelta(days=1)
            if self.oftypes:
                for item_type in self.oftypes:
                    qs = Item.objects.filter(content_type__id=CT(Item.objects.models_by_name[item_type]).id)
                    data[item_type].append(
                        qs.filter(timestamp__range=(dt-step,dt)).count()
                        )
            else:
                data.append(
                    Item.objects.filter(timestamp__range=(dt-step,dt)).count()
                    )

        context[self.context_var] = data
        return ''

########NEW FILE########
__FILENAME__ = test_delicious
import mock
import datetime
import unittest
from django.conf import settings
from django.test import TestCase
from jellyroll.models import Item, Bookmark
from jellyroll.providers import delicious
from jellyroll.providers.utils.anyetree import etree

class DeliciousClientTests(unittest.TestCase):
    
    def test_client_getattr(self):
        c = delicious.DeliciousClient('username', 'password')
        self.assertEqual(c.username, 'username')
        self.assertEqual(c.password, 'password')
        self.assertEqual(c.method, 'v1')
        
        c2 = c.foo.bar.baz
        self.assertEqual(c2.username, 'username')
        self.assertEqual(c2.password, 'password')
        self.assertEqual(c2.method, 'v1/foo/bar/baz')
        
    @mock.patch('jellyroll.providers.utils.getxml')
    def test_client_call(self, mocked):
        c = delicious.DeliciousClient('username', 'password')
        res = c.foo.bar(a=1, b=2)
        
        mocked.assert_called_with(
            'https://api.del.icio.us/v1/foo/bar?a=1&b=2',
            username = 'username',
            password = 'password'
        )

#    
# Fake delicious client that mocks all the calls update() makes.
#

# Quick 'n' dirty XML etree maker
xml = lambda s: etree.fromstring(s.strip())

FakeClient = mock.Mock()

# This makes FakeClient.__init__ do the right thing w/r/t mocking
FakeClient.return_value = FakeClient

FakeClient.posts.update.return_value = xml(
    '<update time="2009-08-18T15:30:16Z" inboxnew="0"/>'
)

FakeClient.posts.dates.return_value = xml('''
    <dates tag="" user="jellyroll">
        <date count="1" date="2009-08-18"/>
    </dates>
''')

FakeClient.posts.get.return_value = xml('''
    <posts user="jellyroll" dt="2009-08-18T15:30:16Z">
        <post href="http://jacobian.org/"
              hash="151ebb66839faa8ed073b27fb897b166"
              description="Me!"
              time="2009-08-18T15:30:16Z"
              extended="I'm awesome."
              tag="me jacob jacobian"
        />
    </posts>
''')

class DeliciousProviderTests(TestCase):
    
    def test_enabled(self):
        self.assertEqual(delicious.enabled(), True)
        
    @mock.patch_object(delicious, 'DeliciousClient', FakeClient)
    def test_update(self):
        delicious.update()
        
        # Check that the calls to the API match what we expect
        FakeClient.assert_called_with(settings.DELICIOUS_USERNAME, settings.DELICIOUS_PASSWORD)
        FakeClient.posts.update.assert_called_with()
        FakeClient.posts.dates.assert_called_with()
        FakeClient.posts.get.assert_called_with(dt='2009-08-18')
        
        # Check that the bookmark exists
        b = Bookmark.objects.get(url="http://jacobian.org/")
        self.assertEqual(b.description, "Me!")
        
        # Check that the Item exists
        i = Item.objects.get(content_type__model='bookmark', object_id=b.pk)
        self.assertEqual(i.timestamp.date(), datetime.date(2009, 8, 18))
        self.assertEqual(i.tags, 'me jacob jacobian')
    
    @mock.patch_object(delicious, 'DeliciousClient', FakeClient)
    @mock.patch_object(delicious, 'log')
    def test_update_skipped_second_time(self, mocked):
        delicious.update()
        delicious.update()
        self.assert_(mocked.info.called)

########NEW FILE########
__FILENAME__ = test_flickr
from __future__ import with_statement

import mock
import datetime
import unittest
from django.conf import settings
from django.test import TestCase
from jellyroll.models import Item, Photo
from jellyroll.providers import flickr, utils

class FlickrClientTests(unittest.TestCase):
    
    def test_client_getattr(self):
        c = flickr.FlickrClient('apikey')
        self.assertEqual(c.api_key, 'apikey')
        self.assertEqual(c.method, 'flickr')
        
        c2 = c.foo.bar.baz
        self.assertEqual(c2.api_key, 'apikey')
        self.assertEqual(c2.method, 'flickr.foo.bar.baz')
    
    def test_client_call(self):
        mock_getjson = mock.Mock(return_value={})
        with mock.patch_object(utils, 'getjson', mock_getjson) as mocked:
            c = flickr.FlickrClient('apikey')
            res = c.foo.bar(a=1, b=2)
            self.assert_(mocked.called)
        
    def test_client_call_fail(self):
        failure = {'stat': 'fail', 'code': 1, 'message': 'fail'}
        mock_getjson = mock.Mock(return_value=failure)
        with mock.patch_object(utils, 'getjson', mock_getjson):
            c = flickr.FlickrClient('apikey')
            self.assertRaises(flickr.FlickrError, c.foo)

#
# Mock Flickr client
#

FakeClient = mock.Mock()
FakeClient.return_value = FakeClient

FakeClient.photos.licenses.getInfo.return_value = {
    'licenses': {
        "license": [{'id':'1', 'name':'All Rights Reserved', 'url':''}]
    }
}

FakeClient.people.getPublicPhotos.return_value = {
    'photos': {
        'page': 1,
        'pages': 1,
        'perpage': 500,
        'total': 1,
        'photo': [{
            "id":"3743398102",
            "owner":"81931330@N00",
            "secret":"2be7a25bfb",
            "server":"2589",
            "farm":3,
            "title":"Burrito",
            "ispublic":1,
            "isfriend":0,
            "isfamily":0,
            "license":"1",
            "datetaken":"2009-07-21 11:45:06", 
            "datetakengranularity":"0"}
        ]
    }
}

FakeClient.photos.getInfo.return_value = {
    "photo": {
        "id":"3743398102",
        "secret":"2be7a25bfb",
        "server":"2589",
        "farm":3,
        "dateuploaded":"1248194706",
        "isfavorite":0,
        "license":"1",
        "rotation":0,
        "originalsecret":"fef2098658",
        "originalformat":"jpg",
        "owner": {
            "nsid":"81931330@N00",
            "username":"jacobian",
            "realname":"Jacob Kaplan-Moss",
            "location":"Lawrence, KS"
        },
        "comments":{"_content":"0"},
        "title": {"_content":"Burrito"},
        "description": {"_content":"<i>This<\/i> is why I miss living in California!"},
        "dates": {
            "posted":"1248194706",
            "taken":"2009-07-21 11:45:06",
            "takengranularity":"0",
            "lastupdate":"1248194900"
        },
        "tags":{
            "tag":[
                {"id":"68660-3685776514-10052",
                 "author":"81931330@N00",
                 "raw":"burrito",
                 "_content":"burrito",
                 "machine_tag":0}
             ]
        },
        "urls":{
            "url":[
                {"type":"photopage", 
                 "_content":"http:\/\/www.flickr.com\/photos\/jacobian\/3743398102\/"}
            ]
        },
        "media":"photo"
    },
    "stat":"ok"
}

FakeClient.photos.getExif.return_value = {
    "photo": {
        "id":"3743398102",
        "secret":"2be7a25bfb",
        "server":"2589",
        "farm":3,
        "exif":[
            {"tagspace":"File",
             "tagspaceid":0,
             "tag":"FileSize",
             "label":"File Size",
             "raw":{"_content":"381 kB"}}
        ]
    }
}

class FlickrProviderTests(TestCase):
    
    def test_enabled(self):
        self.assertEqual(flickr.enabled(), True)
        
    @mock.patch_object(flickr, 'FlickrClient', FakeClient)
    def test_update(self):
        flickr.update()

        FakeClient.assert_called_with(settings.FLICKR_API_KEY)
        FakeClient.photos.licenses.getInfo.assert_called_with()
        FakeClient.people.getPublicPhotos.assert_called_with(
            user_id = settings.FLICKR_USER_ID,
            extras = "license,date_taken",
            per_page = "500",
            page = "2"
        )
        FakeClient.photos.getInfo.assert_called_with(photo_id=3743398102,
                                                     secret="2be7a25bfb")
        
        FakeClient.photos.getExif.assert_called_with(photo_id=3743398102,
                                                     secret="2be7a25bfb")
        
        # Check that the bookmark exists
        p = Photo.objects.get(pk="3743398102")
        self.assertEqual(p.server_id, 2589)
        self.assertEqual(p.farm_id, 3)
        self.assertEqual(p.secret, "2be7a25bfb")
        self.assertEqual(p.taken_by, "jacobian")
        self.assertEqual(p.cc_license, "")
        self.assertEqual(p.title, "Burrito")
        self.assertEqual(p.description, "<i>This<\/i> is why I miss living in California!")
        self.assertEqual(p.comment_count, 0)
        
        # Check that the Item exists
        i = Item.objects.get(content_type__model='photo', object_id=p.pk)
        self.assertEqual(i.timestamp.date(), datetime.date(2009, 7, 21))
        self.assertEqual(i.tags, 'burrito')
    


########NEW FILE########
__FILENAME__ = test_latitude
import mock
import decimal
from django.test import TestCase
from jellyroll.providers import latitude
from jellyroll.models import Item

# The Latitude "API" response
LOCATION_INFO = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-95.260607, 38.942639]
        },
        "properties": {
            "id": "8256516920795551601",
            "accuracyInMeters": 0,
            "timeStamp": 1250601047,
            "reverseGeocode": "Lawrence, KS, USA",
            "photoUrl": "http://www.example.com/",
            "photoWidth": 96,
            "photoHeight": 96,
            "placardUrl": "http://www.example.com/",
            "placardWidth": 56,
            "placardHeight": 59
        }
    }]
}

mock_getjson = mock.Mock()
mock_getjson.return_value = LOCATION_INFO

class LatitudeProviderTests(TestCase):
    
    def test_enabled(self):
        self.assertEqual(latitude.enabled(), True)
    
    @mock.patch('jellyroll.providers.utils.getjson', mock_getjson)
    def test_update(self):
        latitude.update()
        items = Item.objects.filter(content_type__model='location').order_by('-timestamp')        
        loc = items[0].object
        self.assertEqual(loc.latitude, decimal.Decimal('-95.260607'))
        self.assertEqual(loc.longitude, decimal.Decimal('38.942639'))
        self.assertEqual(loc.name, "Lawrence, KS, USA")
        
    @mock.patch('jellyroll.providers.utils.getjson', mock_getjson)
    def test_update_no_duplicates(self):
        """Multiple updates shouldn't return duplicates."""
        latitude.update()
        latitude.update()
        items = Item.objects.filter(content_type__model='location')
        self.assertEqual(len(items), 1)
########NEW FILE########
__FILENAME__ = test_items
from django.test import TestCase
from jellyroll.models import *
from tagging.models import Tag
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django import template

# shortcut
CT = ContentType.objects.get_for_model

class BookmarkTest(TestCase):
    fixtures = ["bookmarks.json"]
        
    def testItemWorkage(self):
        i = Item.objects.get(content_type=CT(Bookmark), object_id="1")
        self.assertEqual(i.url, i.object.url)
        self.assertEqual(i.object_str, str(i.object))
            
class TrackTest(TestCase):
    fixtures = ["tracks.json"]
        
    def testTrack(self):
        i = Item.objects.get(content_type=CT(Track), object_id="1")
        self.assertEqual(str(i), "Track: Outkast - The Train (feat. Scar & Sleepy Brown)")
        
class PhotosTest(TestCase):
    fixtures = ["photos.json"]     
    
    def setUp(self):
        settings.FLICKR_USERNAME = "jacobian"   

    def testPhotoItem(self):
        i = Item.objects.get(content_type=CT(Photo), object_id="1")
        self.assertEqual(i.url, "http://www.flickr.com/photos/jacobian/1/")
        
    def testImageURLs(self):
        p = Photo.objects.get(pk="1")
        self.assertEqual(p.image_url, "http://static.flickr.com/123/1_1234567890.jpg")
        self.assertEqual(p.square_url, "http://static.flickr.com/123/1_1234567890_s.jpg")
        self.assertEqual(p.thumbnail_url, "http://static.flickr.com/123/1_1234567890_t.jpg")
        self.assertEqual(p.small_url, "http://static.flickr.com/123/1_1234567890_m.jpg")
        self.assertEqual(p.large_url, "http://static.flickr.com/123/1_1234567890_b.jpg")
        self.assertEqual(p.original_url, "http://static.flickr.com/123/1_1234567890_o.jpg")
        
    def testRepublishRights(self):
        mine, cc_by, cc_no, cc_nc_nd, cc_sa = Photo.objects.order_by("photo_id")
        self.assertEqual(mine.can_republish, True)
        self.assertEqual(cc_by.can_republish, True)
        self.assertEqual(cc_no.can_republish, False)
        self.assertEqual(cc_nc_nd.can_republish, True)
        self.assertEqual(cc_sa.can_republish, True)

    def testDerivativeRights(self):
        mine, cc_by, cc_no, cc_nc_nd, cc_sa = Photo.objects.order_by("photo_id")
        self.assertEqual(mine.derivative_ok, True)
        self.assertEqual(cc_by.derivative_ok, True)
        self.assertEqual(cc_no.derivative_ok, False)
        self.assertEqual(cc_nc_nd.derivative_ok, False)
        self.assertEqual(cc_sa.derivative_ok, True)

    def testShareAlikeRights(self):
        mine, cc_by, cc_no, cc_nc_nd, cc_sa = Photo.objects.order_by("photo_id")
        self.assertEqual(mine.must_share_alike, False)
        self.assertEqual(cc_by.must_share_alike, False)
        self.assertEqual(cc_no.must_share_alike, False)
        self.assertEqual(cc_nc_nd.must_share_alike, False)
        self.assertEqual(cc_sa.must_share_alike, True)
        
    def testCommercialRepublishRights(self):
        cc_nc_nd = Photo.objects.get(pk="4")
        saved, settings.SITE_IS_COMMERCIAL = getattr(settings, 'SITE_IS_COMMERCIAL', False), True
        self.assertEqual(cc_nc_nd.can_republish, False)
        settings.SITE_IS_COMMERCIAL = saved
        
    def testEXIF(self):
        p = Photo.objects.get(pk="1")
        self.assertEqual(p.exif, {})
        p.exif = {"Make" : "Nokia 6682", "Aperture" : "f/3.2"}
        p.save()
        p = Photo.objects.get(pk="1")
        self.assertEqual(p.exif, {"Make" : "Nokia 6682", "Aperture" : "f/3.2"})
        
class CodeCommitTest(TestCase):
    fixtures = ["codecommits.json"]
            
    def testCommit(self):
        c = CodeCommit.objects.get(pk=1)
        self.assertEqual(c.url, "http://code.djangoproject.com/changeset/42")
        
class WebSearchTest(TestCase):
    fixtures = ["websearches.json"]
    
    def testSearch(self):
        s = WebSearch.objects.get(pk=1)
        self.assertEqual(s.url, "http://www.google.com/search?q=test")
        
    def testResults(self):
        s = WebSearch.objects.get(pk=1)
        self.assertEqual(s.results.all()[0].url, "http://www.test.com/")
        
class VideoTest(TestCase):
    fixtures = ["videos.json"]
    
    def testGoogle(self):
        v = Video.objects.get(pk=1)
        self.assertEqual(v.embed_url, "http://video.google.com/googleplayer.swf?docId=-1182786924290841590&hl=en")
        
    def testYouTube(self):
        v = Video.objects.get(pk=2)
        self.assertEqual(v.embed_url, "http://www.youtube.com/v/1gvGDsIYrrQ")
        
class ItemTest(TestCase):
    fixtures = ["bookmarks.json", "photos.json", "trac.json", "tracks.json", "videos.json", "websearches.json"]
    
    def testSorting(self):
        items = list(Item.objects.all())
        self.assertEqual(items, sorted(items, reverse=True))
        
    def testModelsByName(self):
        self.assertEqual(Item.objects.models_by_name["bookmark"], Bookmark)
        self.assertEqual(Item.objects.models_by_name["codecommit"], CodeCommit)
        self.assertEqual(Item.objects.models_by_name["photo"], Photo)
        self.assertEqual(Item.objects.models_by_name["track"], Track)
        self.assertEqual(Item.objects.models_by_name["video"], Video)
        self.assertEqual(Item.objects.models_by_name["websearch"], WebSearch)
        

########NEW FILE########
__FILENAME__ = test_misc
import unittest
import jellyroll.providers

class MiscTests(unittest.TestCase):
    def test_providers_expand_star(self):
        expanded = jellyroll.providers.expand_star("jellyroll.providers.*")
        expected = [
            'jellyroll.providers.delicious',
            'jellyroll.providers.flickr',
            'jellyroll.providers.gitscm',
            'jellyroll.providers.gsearch',
            'jellyroll.providers.lastfm',
            'jellyroll.providers.latitude',
            'jellyroll.providers.svn',
            'jellyroll.providers.twitter',
            'jellyroll.providers.youtube',
        ]
        expanded.sort()
        expected.sort()
        self.assertEqual(expanded, expected)
########NEW FILE########
__FILENAME__ = test_tags
from django import template
from django.test import TestCase
from jellyroll.models import *

class TagTestCase(TestCase):
    """Helper class with some tag helper functions"""
    
    def installTagLibrary(self, library):
        template.libraries[library] = __import__(library)
        
    def renderTemplate(self, tstr, **context):
        t = template.Template(tstr)
        c = template.Context(context)
        return t.render(c)

class RenderTagTest(TagTestCase):
    fixtures = ["videos.json"]
    
    def setUp(self):
        self.installTagLibrary('jellyroll.templatetags.jellyroll')
        
    def testRenderSimple(self):
        i = Item.objects.get(pk=1)
        o = self.renderTemplate("{% load jellyroll %}{% jellyrender i %}", i=i)
        self.assert_(o.startswith('<div class="jellyroll-item'), o)
        
    def testRenderUsing(self):
        i = Item.objects.get(pk=1)
        o = self.renderTemplate('{% load jellyroll %}{% jellyrender i using "jellyroll/snippets/item.txt" %}', i=i)
        self.assertEqual(str(i.object), o)
        
    def testRenderAs(self):
        i = Item.objects.get(pk=1)
        o = self.renderTemplate('{% load jellyroll %}{% jellyrender i as o using "jellyroll/snippets/item.txt" %} -- {{ o }}', i=i)
        self.assertEqual(" -- %s" % str(i.object), o)

class GetJellyrollItemsTagSyntaxTest(TestCase):
    
    def getNode(self, str):
        from jellyroll.templatetags.jellyroll import get_jellyroll_items
        return get_jellyroll_items(None, template.Token(template.TOKEN_BLOCK, str))
        
    def assertNodeException(self, str):
        self.assertRaises(template.TemplateSyntaxError, self.getNode, str)
    
    def testLimit(self):
        node = self.getNode("get_jellyroll_items limit 10 as items")
        self.assertEqual(node.limit, 10)
        self.assertEqual(node.start, None)
        self.assertEqual(node.end, None)
        self.assertEqual(node.asvar, "items")
    
    def testBetween(self):
        node = self.getNode("get_jellyroll_items between '2007-01-01' and '2007-01-31' as items")
        self.assertEqual(node.limit, None)
        self.assertEqual(node.start, "'2007-01-01'")
        self.assertEqual(node.end, "'2007-01-31'")
        
    def testReversed(self):
        node = self.getNode("get_jellyroll_items limit 10 reversed as items")
        self.assertEqual(node.reversed, True)
    
    def testOfType(self):
        node = self.getNode("get_jellyroll_items oftype video limit 10 as items")
        self.assertEqual(node.oftypes, [Video])

    def testOfTypes(self):
        node = self.getNode("get_jellyroll_items oftype video oftype photo limit 10 as items")
        self.assertEqual(node.oftypes, [Video, Photo])

    def testExcludeType(self):
        node = self.getNode("get_jellyroll_items excludetype video limit 10 as items")
        self.assertEqual(node.excludetypes, [Video])

    def testExcludeTypes(self):
        node = self.getNode("get_jellyroll_items excludetype video excludetype photo limit 10 as items")
        self.assertEqual(node.excludetypes, [Video, Photo])

    def testInvalidSyntax(self):
        self.assertNodeException("get_jellyroll_items")
        self.assertNodeException("get_jellyroll_items as")
        self.assertNodeException("get_jellyroll_items as items")
        self.assertNodeException("get_jellyroll_items limit")
        self.assertNodeException("get_jellyroll_items limit frog")
        self.assertNodeException("get_jellyroll_items between")
        self.assertNodeException("get_jellyroll_items between x")
        self.assertNodeException("get_jellyroll_items between x and")
        self.assertNodeException("get_jellyroll_items between x spam y")
        self.assertNodeException("get_jellyroll_items oftype")
        self.assertNodeException("get_jellyroll_items excludetype")
        
    def testInvalidTypes(self):
        self.assertNodeException("get_jellyroll_items limit 10 oftype frog as items")
        self.assertNodeException("get_jellyroll_items limit 10 excludetype frog as items")
        
class GetJellyrollItemsTagTest(TagTestCase):
    fixtures = ["bookmarks.json", "photos.json", "trac.json", "tracks.json", "videos.json", "websearches.json"]

    def setUp(self):
        self.installTagLibrary('jellyroll.templatetags.jellyroll')

    def testLimit(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items limit 5 as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "5")
        
    def testBetween1(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items between '2006' and 'now' as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "10")
        
    def testBetween2(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items between '2001' and '2002' as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "0")

    def testReversed(self):
        t1 = "{% load jellyroll %}"\
             "{% get_jellyroll_items limit 10 as forwards %}"\
             "{{ forwards.0.id }}"
        t2 = "{% load jellyroll %}"\
             "{% get_jellyroll_items limit 10 reversed as backwards %}"\
             "{{ backwards.9.id }}"
        self.assertEqual(self.renderTemplate(t1), self.renderTemplate(t2))
        
    def testOfType(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items oftype photo limit 10 as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "5")
        
    def testOfTypes(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items oftype photo oftype video limit 10 as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "7")

    def testExcludeType(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items excludetype photo limit 10 as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "5")

    def testExcludeTypes(self):
        o = self.renderTemplate("{% load jellyroll %}"\
                                "{% get_jellyroll_items excludetype photo excludetype video limit 10 as items %}"\
                                "{{ items|length }}")
        self.assertEqual(o, "3")

########NEW FILE########
__FILENAME__ = test_views
import datetime
from django.test import TestCase
from django.conf import settings
from jellyroll.models import Item

class CalendarViewTest(TestCase):
    fixtures = ["bookmarks.json", "photos.json", "trac.json", "tracks.json", "videos.json", "websearches.json"]
    
    def setUp(self):
        settings.ROOT_URLCONF = "jellyroll.urls.calendar"
        
    def callView(self, url):
        today = datetime.date.today()
        response = self.client.get(today.strftime(url).lower())
        if isinstance(response.context, list):
            context = response.context[0]
        else:
            context = response.context
        return today, response, context
        
    def testYearView(self):
        today, response, context = self.callView("/%Y/")
        self.assertEqual(context["year"], today.year)
        self.assertEqual(len(context["items"]), Item.objects.count())
        
    def testMonthView(self):
        today, response, context = self.callView("/%Y/%b/")
        self.assertEqual(context["month"].year, today.year)
        self.assertEqual(context["month"].month, today.month)
        self.assertEqual(len(context["items"]), Item.objects.count())
        
    def testDayView(self):
        today, response, context = self.callView("/%Y/%b/%d/")
        self.assertEqual(context["day"], today)
        self.assertEqual(len(context["items"]), Item.objects.count())
        
    def testTodayView(self):
        today, response, context = self.callView("/")
        self.assertEqual(context["day"], today)
        self.assertEqual(len(context["items"]), Item.objects.count())
        self.assertEqual(context["is_today"], True)
        self.assertTemplateUsed(response, "jellyroll/calendar/today.html")
        
    def testDayViewOrdering(self):
        today, response, context = self.callView("/%Y/%b/%d/")
        first = context["items"][0].timestamp
        last = list(context["items"])[-1].timestamp
        self.assert_(first < last, "first: %s, last: %s" % (first, last))
        
    def testTodayViewOrdering(self):
        today, response, context = self.callView("/")
        first = context["items"][0].timestamp
        last = list(context["items"])[-1].timestamp
        self.assert_(first > last, "first: %s, last: %s" % (first, last))
########NEW FILE########
__FILENAME__ = testsettings
import os

BASE = os.path.abspath(os.path.dirname(__file__))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/jellyroll.db'
INSTALLED_APPS = ['django.contrib.contenttypes', 'tagging', 'jellyroll']

JELLYROLL_PROVIDERS = ['jellyroll.providers.*']

# Jellyroll username auth creds. This is all fake; the test suite mocks all
# the APIs anyway.
DELICIOUS_USERNAME = FLICKR_USERNAME = GOOGLE_USERNAME = LASTFM_USERNAME \
                   = TWITTER_USERNAME = YOUTUBE_USERNAME \
                   = GOOGLE_LATITUDE_USER_ID = 'jellyroll'
DELICIOUS_PASSWORD = GOOGLE_PASSWORD = 'password'
FLICKR_API_KEY = 'apikey'
FLICKR_USER_ID = 'userid'

# Silence logging
import logging

class Silence(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger("jellyroll").addHandler(Silence())

# Coverage, if installed
try:
    from test_coverage.settings import *
except ImportError:
    pass
else:
    INSTALLED_APPS.append('test_coverage')
    
    COVERAGE_REPORT_HTML_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE)), 'coverage')
    COVERAGE_MODULE_EXCLUDES = ['^django\.', '^tagging\.', 'settings$', '\.templates$', '\.fixtures$']
    
    if not os.path.exists(COVERAGE_REPORT_HTML_OUTPUT_DIR):
        os.mkdir(COVERAGE_REPORT_HTML_OUTPUT_DIR)
########NEW FILE########
__FILENAME__ = calendar
"""
URLs for doing a jellyroll site by date (i.e. ``2007/``, ``2007/may/``, etc.)
"""

from django.conf.urls.defaults import *
from jellyroll.views import calendar

urlpatterns = patterns('', 
    url(
        regex = "^$",
        view  = calendar.today,
        name  = "jellyroll_calendar_today",
    ),
    url(
        regex = "^(?P<year>\d{4})/$",
        view  = calendar.year,
        name  = "jellyroll_calendar_year",
    ),
    url(
        regex = "^(?P<year>\d{4})/(?P<month>\w{3})/$",
        view  = calendar.month,
        name  = "jellyroll_calendar_month",
    ),
    url(
        regex = "^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{2})/$",
        view  = calendar.day,
        name  = "jellyroll_calendar_day",
    ),
)

########NEW FILE########
__FILENAME__ = tags
from django.conf.urls.defaults import *
from jellyroll.views import tags


urlpatterns = patterns('',

    url(r'^$', tags.tag_list, {}, name='jellyroll_tag_list'),
    url(r'^(?P<tag>[-\.\'\:\w]+)/$',tags.tag_item_list, {}, name="jellyroll_tag_item_list"),
)

########NEW FILE########
__FILENAME__ = calendar
"""
Views for looking at Jellyroll items by date.

These act as kinda-sorta generic views in that they take a number of the same
arguments as generic views do (i.e. ``template_name``, ``extra_context``, etc.)

They all also take an argument ``queryset`` which should be an ``Item``
queryset; it'll be used as the *starting point* for the the view in question
instead of ``Item.objects.all()``.
"""

import time
import datetime
from django.core import urlresolvers
from django.template import loader, RequestContext
from django.http import Http404, HttpResponse
from jellyroll.models import Item

def today(request, **kwargs):
    """
    Jellyroll'd items today
    
    See :view:`jellyroll.views.calendar.day`
    """
    y, m, d = datetime.date.today().strftime("%Y/%b/%d").lower().split("/")
    if "template_name" not in kwargs:
        kwargs['template_name'] = "jellyroll/calendar/today.html"
    return day(request, y, m, d, recent_first=True, **kwargs)

def year(request, year, queryset=None,
    template_name="jellyroll/calendar/year.html", template_loader=loader,
    extra_context=None, context_processors=None, mimetype=None):
    """
    Jellyroll'd items for a particular year.

    Works a bit like a generic view in that you can pass a bunch of optional
    keyword arguments which work just like they do in generic views. Those
    arguments are: ``template_name``, ``template_loader``, ``extra_context``,
    ``context_processors``, and ``mimetype``.
    
    You can also pass a ``queryset`` argument; see the module's docstring
    for information about how that works.

    Templates: ``jellyroll/calendar/year.html`` (default)
    Context:
        ``items``
            Items from the year, earliest first.
        ``year``
            The year.
        ``previous``
            The previous year; ``None`` if that year was before jellyrolling
            started..
        ``previous_link``
            Link to the previous year
        ``next``
            The next year; ``None`` if it's in the future.
        ``next_year``
            Link to the next year
    """
    # Make sure we've requested a valid year
    year = int(year)
    try:
        first = Item.objects.order_by("timestamp")[0]
    except IndexError:
        raise Http404("No items; no views.")
    today = datetime.date.today()
    if year < first.timestamp.year or year > today.year:
        raise Http404("Invalid year (%s .. %s)" % (first.timestamp.year, today.year))
    
    # Calculate the previous year
    previous = year - 1
    previous_link = urlresolvers.reverse("jellyroll.views.calendar.year", args=[previous])
    if previous < first.timestamp.year:
        previous = previous_link = None
    
    # And the next year
    next = year + 1
    next_link = urlresolvers.reverse("jellyroll.views.calendar.year", args=[next])
    if next > today.year:
        next = next_link = None
        
    # Handle the initial queryset
    if not queryset:
        queryset = Item.objects.all()
    queryset = queryset.filter(timestamp__year=year)
    if not queryset.query.order_by:
        queryset = queryset.order_by("timestamp")
        
    # Build the context
    context = RequestContext(request, {
        "items"         : queryset.filter(timestamp__year=year).order_by("timestamp"),
        "year"          : year,
        "previous"      : previous,
        "previous_link" : previous_link,
        "next"          : next,
        "next_link"     : next_link
    }, context_processors)
    if extra_context:
        for key, value in extra_context.items():
            if callable(value):
                context[key] = value()
            else:
                context[key] = value
    
    # Load, render, and return
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(context), mimetype=mimetype)

def month(request, year, month, queryset=None,
    template_name="jellyroll/calendar/month.html", template_loader=loader,
    extra_context=None, context_processors=None, mimetype=None):
    """
    Jellyroll'd items for a particular month.

    Works a bit like a generic view in that you can pass a bunch of optional
    keyword arguments which work just like they do in generic views. Those
    arguments are: ``template_name``, ``template_loader``, ``extra_context``,
    ``context_processors``, and ``mimetype``.
    
    You can also pass a ``queryset`` argument; see the module's docstring
    for information about how that works.

    Templates: ``jellyroll/calendar/month.html`` (default)
    Context:
        ``items``
            Items from the month, earliest first.
        ``month``
            The month (a ``datetime.date`` object).
        ``previous``
            The previous month; ``None`` if that month was before jellyrolling
            started.
        ``previous_link``
            Link to the previous month
        ``next``
            The next month; ``None`` if it's in the future.
        ``next_link``
            Link to the next month
    """
    # Make sure we've requested a valid month
    try:
        date = datetime.date(*time.strptime(year+month, '%Y%b')[:3])
    except ValueError:
        raise Http404("Invalid month string")
    try:
        first = Item.objects.order_by("timestamp")[0]
    except IndexError:
        raise Http404("No items; no views.")
    
    # Calculate first and last day of month, for use in a date-range lookup.
    today = datetime.date.today()
    first_day = date.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1)
    
    if first_day < first.timestamp.date().replace(day=1) or date > today:
        raise Http404("Invalid month (%s .. %s)" % (first.timestamp.date(), today))
    
    # Calculate the previous month
    previous = (first_day - datetime.timedelta(days=1)).replace(day=1)
    previous_link = urlresolvers.reverse("jellyroll.views.calendar.month", args=previous.strftime("%Y %b").lower().split())
    if previous < first.timestamp.date().replace(day=1):
        previous = None
    
    # And the next month
    next = last_day + datetime.timedelta(days=1)
    next_link = urlresolvers.reverse("jellyroll.views.calendar.month", args=next.strftime("%Y %b").lower().split())
    if next > today:
        next = None
        
    # Handle the initial queryset
    if not queryset:
        queryset = Item.objects.all()
    queryset = queryset.filter(timestamp__range=(first_day, last_day))
    if not queryset.query.order_by:
        queryset = queryset.order_by("timestamp")
    
    # Build the context
    context = RequestContext(request, {
        "items"         : queryset,
        "month"         : date,
        "previous"      : previous,
        "previous_link" : previous_link,
        "next"          : next,
        "next_link"     : next_link
    }, context_processors)
    if extra_context:
        for key, value in extra_context.items():
            if callable(value):
                context[key] = value()
            else:
                context[key] = value
    
    # Load, render, and return
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(context), mimetype=mimetype)
        
def day(request, year, month, day, queryset=None, recent_first=False,
    template_name="jellyroll/calendar/day.html", template_loader=loader,
    extra_context=None, context_processors=None, mimetype=None):
    """
    Jellyroll'd items for a particular day.

    Works a bit like a generic view in that you can pass a bunch of optional
    keyword arguments which work just like they do in generic views. Those
    arguments are: ``template_name``, ``template_loader``, ``extra_context``,
    ``context_processors``, and ``mimetype``.
    
    Also takes a ``recent_first`` param; if it's ``True`` the newest items
    will be displayed first; otherwise items will be ordered earliest first.

    You can also pass a ``queryset`` argument; see the module's docstring
    for information about how that works.

    Templates: ``jellyroll/calendar/day.html`` (default)
    Context:
        ``items``
            Items from the month, ordered according to ``recent_first``.
        ``day``
            The day (a ``datetime.date`` object).
        ``previous``
            The previous day; ``None`` if that day was before jellyrolling
            started.
        ``previous_link``
            Link to the previous day
        ``next``
            The next day; ``None`` if it's in the future.
        ``next_link``
            Link to the next day.
        ``is_today``
            ``True`` if this day is today.
    """
    # Make sure we've requested a valid month
    try:
        day = datetime.date(*time.strptime(year+month+day, '%Y%b%d')[:3])
    except ValueError:
        raise Http404("Invalid day string")
    try:
        first = Item.objects.order_by("timestamp")[0]
    except IndexError:
        raise Http404("No items; no views.")
    
    today = datetime.date.today()
    if day < first.timestamp.date() or day > today:
        raise Http404("Invalid day (%s .. %s)" % (first.timestamp.date(), today))
    
    # Calculate the previous day
    previous = day - datetime.timedelta(days=1)
    previous_link = urlresolvers.reverse("jellyroll.views.calendar.day", args=previous.strftime("%Y %b %d").lower().split())
    if previous < first.timestamp.date():
        previous = previous_link = None
    
    # And the next month
    next = day + datetime.timedelta(days=1)
    next_link = urlresolvers.reverse("jellyroll.views.calendar.day", args=next.strftime("%Y %b %d").lower().split())
    if next > today:
        next = next_link = None
    
    # Some lookup values...
    timestamp_range = (datetime.datetime.combine(day, datetime.time.min), 
                       datetime.datetime.combine(day, datetime.time.max))
    
    # Handle the initial queryset
    if not queryset:
       queryset = Item.objects.all()
    queryset = queryset.filter(timestamp__range=timestamp_range)
    if not queryset.query.order_by:
        if recent_first:
            queryset = queryset.order_by("-timestamp")
        else:
            queryset = queryset.order_by("timestamp")
    
    # Build the context
    context = RequestContext(request, {
        "items"         : queryset,
        "day"           : day,
        "previous"      : previous,
        "previous_link" : previous_link,
        "next"          : next,
        "next_link"     : next_link,
        "is_today"      : day == today,
    }, context_processors)
    if extra_context:
        for key, value in extra_context.items():
            if callable(value):
                context[key] = value()
            else:
                context[key] = value
    
    # Load, render, and return
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(context), mimetype=mimetype)

########NEW FILE########
__FILENAME__ = tags
"""
Views for looking at Jellyroll items by tag.

"""

from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.contenttypes.models import ContentType
from django.views.generic.list_detail import object_list
from django.template import RequestContext
from django.http import Http404
from jellyroll.models import Item
from tagging.models import TaggedItem, Tag


def tag_list(request):
    #tags = sorted( Tag.objects.usage_for_model(Item),
    #               cmp=lambda x,y: cmp(x.name.lower(),y.name.lower()) )
    item_ct = ContentType.objects.get_for_model(Item)
    tag_items = TaggedItem.objects.filter(content_type=item_ct)
    tags = Tag.objects.filter(pk__in=[ tag_item.tag.pk for tag_item in tag_items ])
    return object_list(request, tags, template_object_name='tag',
                       template_name='jellyroll/tags/tag_list.html')

def tag_item_list(request, tag):
    tag = get_object_or_404(Tag,name=tag)
    items = TaggedItem.objects.get_by_model(Item,tag)
    return object_list(request, items, template_object_name='item',
                       template_name='jellyroll/tags/tag_item_list.html', 
                       extra_context={'tag':tag})

########NEW FILE########
