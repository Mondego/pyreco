__FILENAME__ = admin
from django.contrib import admin

from notification.models import NoticeType, NoticeSetting, Notice, ObservedItem, NoticeQueueBatch


class NoticeTypeAdmin(admin.ModelAdmin):
    list_display = ["label", "display", "description", "default"]


class NoticeSettingAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "notice_type", "medium", "send"]


class NoticeAdmin(admin.ModelAdmin):
    list_display = ["message", "recipient", "sender", "notice_type", "added", "unseen", "archived"]


admin.site.register(NoticeQueueBatch)
admin.site.register(NoticeType, NoticeTypeAdmin)
admin.site.register(NoticeSetting, NoticeSettingAdmin)
admin.site.register(Notice, NoticeAdmin)
admin.site.register(ObservedItem)

########NEW FILE########
__FILENAME__ = atomformat
# 
# django-atompub by James Tauber <http://jtauber.com/>
# http://code.google.com/p/django-atompub/
# An implementation of the Atom format and protocol for Django
# 
# For instructions on how to use this module to generate Atom feeds,
# see http://code.google.com/p/django-atompub/wiki/UserGuide
# 
# 
# Copyright (c) 2007, James Tauber
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 

from xml.sax.saxutils import XMLGenerator
from datetime import datetime


GENERATOR_TEXT = 'django-atompub'
GENERATOR_ATTR = {
    'uri': 'http://code.google.com/p/django-atompub/',
    'version': 'r33'
}



## based on django.utils.xmlutils.SimplerXMLGenerator
class SimplerXMLGenerator(XMLGenerator):
    def addQuickElement(self, name, contents=None, attrs=None):
        "Convenience method for adding an element with no children"
        if attrs is None: attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)



## based on django.utils.feedgenerator.rfc3339_date
def rfc3339_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')



## based on django.utils.feedgenerator.get_tag_uri
def get_tag_uri(url, date):
    "Creates a TagURI. See http://diveintomark.org/archives/2004/05/28/howto-atom-id"
    parts = urlparse.urlparse(url)
    date_part = ""
    if date is not None:
        date_part = ",%s:" % date.strftime("%Y-%m-%d")
    return "tag:%s%s%s/%s" % (
        parts.hostname,
        date_part,
        parts.path,
        parts.fragment,
    )



## based on django.contrib.syndication.feeds.Feed
class Feed(object):
    
    
    VALIDATE = True
    
    
    def __init__(self, slug, feed_url):
        # @@@ slug and feed_url are not used yet
        pass
    
    
    def __get_dynamic_attr(self, attname, obj, default=None):
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default
        if callable(attr):
            # Check func_code.co_argcount rather than try/excepting the
            # function and catching the TypeError, because something inside
            # the function may raise the TypeError. This technique is more
            # accurate.
            if hasattr(attr, 'func_code'):
                argcount = attr.func_code.co_argcount
            else:
                argcount = attr.__call__.func_code.co_argcount
            if argcount == 2: # one argument is 'self'
                return attr(obj)
            else:
                return attr()
        return attr
    
    
    def get_feed(self, extra_params=None):
        
        if extra_params:
            try:
                obj = self.get_object(extra_params.split('/'))
            except (AttributeError, LookupError):
                raise LookupError('Feed does not exist')
        else:
            obj = None
        
        feed = AtomFeed(
            atom_id = self.__get_dynamic_attr('feed_id', obj),
            title = self.__get_dynamic_attr('feed_title', obj),
            updated = self.__get_dynamic_attr('feed_updated', obj),
            icon = self.__get_dynamic_attr('feed_icon', obj),
            logo = self.__get_dynamic_attr('feed_logo', obj),
            rights = self.__get_dynamic_attr('feed_rights', obj),
            subtitle = self.__get_dynamic_attr('feed_subtitle', obj),
            authors = self.__get_dynamic_attr('feed_authors', obj, default=[]),
            categories = self.__get_dynamic_attr('feed_categories', obj, default=[]),
            contributors = self.__get_dynamic_attr('feed_contributors', obj, default=[]),
            links = self.__get_dynamic_attr('feed_links', obj, default=[]),
            extra_attrs = self.__get_dynamic_attr('feed_extra_attrs', obj),
            hide_generator = self.__get_dynamic_attr('hide_generator', obj, default=False)
        )
        
        items = self.__get_dynamic_attr('items', obj)
        if items is None:
            raise LookupError('Feed has no items field')
        
        for item in items:
            feed.add_item(
                atom_id = self.__get_dynamic_attr('item_id', item), 
                title = self.__get_dynamic_attr('item_title', item),
                updated = self.__get_dynamic_attr('item_updated', item),
                content = self.__get_dynamic_attr('item_content', item),
                published = self.__get_dynamic_attr('item_published', item),
                rights = self.__get_dynamic_attr('item_rights', item),
                source = self.__get_dynamic_attr('item_source', item),
                summary = self.__get_dynamic_attr('item_summary', item),
                authors = self.__get_dynamic_attr('item_authors', item, default=[]),
                categories = self.__get_dynamic_attr('item_categories', item, default=[]),
                contributors = self.__get_dynamic_attr('item_contributors', item, default=[]),
                links = self.__get_dynamic_attr('item_links', item, default=[]),
                extra_attrs = self.__get_dynamic_attr('item_extra_attrs', None, default={}),
            )
        
        if self.VALIDATE:
            feed.validate()
        return feed



class ValidationError(Exception):
    pass



## based on django.utils.feedgenerator.SyndicationFeed and django.utils.feedgenerator.Atom1Feed
class AtomFeed(object):
    
    
    mime_type = 'application/atom+xml'
    ns = u'http://www.w3.org/2005/Atom'
    
    
    def __init__(self, atom_id, title, updated=None, icon=None, logo=None, rights=None, subtitle=None,
        authors=[], categories=[], contributors=[], links=[], extra_attrs={}, hide_generator=False):
        if atom_id is None:
            raise LookupError('Feed has no feed_id field')
        if title is None:
            raise LookupError('Feed has no feed_title field')
        # if updated == None, we'll calculate it
        self.feed = {
            'id': atom_id,
            'title': title,
            'updated': updated,
            'icon': icon,
            'logo': logo,
            'rights': rights,
            'subtitle': subtitle,
            'authors': authors,
            'categories': categories,
            'contributors': contributors,
            'links': links,
            'extra_attrs': extra_attrs,
            'hide_generator': hide_generator,
        }
        self.items = []
    
    
    def add_item(self, atom_id, title, updated, content=None, published=None, rights=None, source=None, summary=None,
        authors=[], categories=[], contributors=[], links=[], extra_attrs={}):
        if atom_id is None:
            raise LookupError('Feed has no item_id method')
        if title is None:
            raise LookupError('Feed has no item_title method')
        if updated is None:
            raise LookupError('Feed has no item_updated method')
        self.items.append({
            'id': atom_id,
            'title': title,
            'updated': updated,
            'content': content,
            'published': published,
            'rights': rights,
            'source': source,
            'summary': summary,
            'authors': authors,
            'categories': categories,
            'contributors': contributors,
            'links': links,
            'extra_attrs': extra_attrs,
        })
    
    
    def latest_updated(self):
        """
        Returns the latest item's updated or the current time if there are no items.
        """
        updates = [item['updated'] for item in self.items]
        if len(updates) > 0:
            updates.sort()
            return updates[-1]
        else:
            return datetime.now() # @@@ really we should allow a feed to define its "start" for this case
    
    
    def write_text_construct(self, handler, element_name, data):
        if isinstance(data, tuple):
            text_type, text = data
            if text_type == 'xhtml':
                handler.startElement(element_name, {'type': text_type})
                handler._write(text) # write unescaped -- it had better be well-formed XML
                handler.endElement(element_name)
            else:
                handler.addQuickElement(element_name, text, {'type': text_type})
        else:
            handler.addQuickElement(element_name, data)
    
    
    def write_person_construct(self, handler, element_name, person):
        handler.startElement(element_name, {})
        handler.addQuickElement(u'name', person['name'])
        if 'uri' in person:
            handler.addQuickElement(u'uri', person['uri'])
        if 'email' in person:
            handler.addQuickElement(u'email', person['email'])
        handler.endElement(element_name)
    
    
    def write_link_construct(self, handler, link):
        if 'length' in link:
            link['length'] = str(link['length'])
        handler.addQuickElement(u'link', None, link)
    
    
    def write_category_construct(self, handler, category):
        handler.addQuickElement(u'category', None, category)
    
    
    def write_source(self, handler, data):
        handler.startElement(u'source', {})
        if data.get('id'):
            handler.addQuickElement(u'id', data['id'])
        if data.get('title'):
            self.write_text_construct(handler, u'title', data['title'])
        if data.get('subtitle'):
            self.write_text_construct(handler, u'subtitle', data['subtitle'])
        if data.get('icon'):
            handler.addQuickElement(u'icon', data['icon'])
        if data.get('logo'):
            handler.addQuickElement(u'logo', data['logo'])
        if data.get('updated'):
            handler.addQuickElement(u'updated', rfc3339_date(data['updated']))
        for category in data.get('categories', []):
            self.write_category_construct(handler, category)
        for link in data.get('links', []):
            self.write_link_construct(handler, link)
        for author in data.get('authors', []):
            self.write_person_construct(handler, u'author', author)
        for contributor in data.get('contributors', []):
            self.write_person_construct(handler, u'contributor', contributor)
        if data.get('rights'):
            self.write_text_construct(handler, u'rights', data['rights'])
        handler.endElement(u'source')
    
    
    def write_content(self, handler, data):
        if isinstance(data, tuple):
            content_dict, text = data
            if content_dict.get('type') == 'xhtml':
                handler.startElement(u'content', content_dict)
                handler._write(text) # write unescaped -- it had better be well-formed XML
                handler.endElement(u'content')
            else:
                handler.addQuickElement(u'content', text, content_dict)
        else:
            handler.addQuickElement(u'content', data)
    
    
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        feed_attrs = {u'xmlns': self.ns}
        if self.feed.get('extra_attrs'):
            feed_attrs.update(self.feed['extra_attrs'])
        handler.startElement(u'feed', feed_attrs)
        handler.addQuickElement(u'id', self.feed['id'])
        self.write_text_construct(handler, u'title', self.feed['title'])
        if self.feed.get('subtitle'):
            self.write_text_construct(handler, u'subtitle', self.feed['subtitle'])
        if self.feed.get('icon'):
            handler.addQuickElement(u'icon', self.feed['icon'])
        if self.feed.get('logo'):
            handler.addQuickElement(u'logo', self.feed['logo'])
        if self.feed['updated']:
            handler.addQuickElement(u'updated', rfc3339_date(self.feed['updated']))
        else:
            handler.addQuickElement(u'updated', rfc3339_date(self.latest_updated()))
        for category in self.feed['categories']:
            self.write_category_construct(handler, category)
        for link in self.feed['links']:
            self.write_link_construct(handler, link)
        for author in self.feed['authors']:
            self.write_person_construct(handler, u'author', author)
        for contributor in self.feed['contributors']:
            self.write_person_construct(handler, u'contributor', contributor)
        if self.feed.get('rights'):
            self.write_text_construct(handler, u'rights', self.feed['rights'])
        if not self.feed.get('hide_generator'):
            handler.addQuickElement(u'generator', GENERATOR_TEXT, GENERATOR_ATTR)
        
        self.write_items(handler)
        
        handler.endElement(u'feed')
    
    
    def write_items(self, handler):
        for item in self.items:
            entry_attrs = item.get('extra_attrs', {})
            handler.startElement(u'entry', entry_attrs)
            
            handler.addQuickElement(u'id', item['id'])
            self.write_text_construct(handler, u'title', item['title'])
            handler.addQuickElement(u'updated', rfc3339_date(item['updated']))
            if item.get('published'):
                handler.addQuickElement(u'published', rfc3339_date(item['published']))
            if item.get('rights'):
                self.write_text_construct(handler, u'rights', item['rights'])
            if item.get('source'):
                self.write_source(handler, item['source'])
            
            for author in item['authors']:
                self.write_person_construct(handler, u'author', author)
            for contributor in item['contributors']:
                self.write_person_construct(handler, u'contributor', contributor)
            for category in item['categories']:
                self.write_category_construct(handler, category)
            for link in item['links']:
                self.write_link_construct(handler, link)
            if item.get('summary'):
                self.write_text_construct(handler, u'summary', item['summary'])
            if item.get('content'):
                self.write_content(handler, item['content'])
            
            handler.endElement(u'entry')
    
    
    def validate(self):
        
        def validate_text_construct(obj):
            if isinstance(obj, tuple):
                if obj[0] not in ['text', 'html', 'xhtml']:
                    return False
            # @@@ no validation is done that 'html' text constructs are valid HTML
            # @@@ no validation is done that 'xhtml' text constructs are well-formed XML or valid XHTML
            
            return True
        
        if not validate_text_construct(self.feed['title']):
            raise ValidationError('feed title has invalid type')
        if self.feed.get('subtitle'):
            if not validate_text_construct(self.feed['subtitle']):
                raise ValidationError('feed subtitle has invalid type')
        if self.feed.get('rights'):
            if not validate_text_construct(self.feed['rights']):
                raise ValidationError('feed rights has invalid type')
        
        alternate_links = {}
        for link in self.feed.get('links'):
            if link.get('rel') == 'alternate' or link.get('rel') == None:
                key = (link.get('type'), link.get('hreflang'))
                if key in alternate_links:
                    raise ValidationError('alternate links must have unique type/hreflang')
                alternate_links[key] = link
        
        if self.feed.get('authors'):
            feed_author = True
        else:
            feed_author = False
        
        for item in self.items:
            if not feed_author and not item.get('authors'):
                if item.get('source') and item['source'].get('authors'):
                    pass
                else:
                    raise ValidationError('if no feed author, all entries must have author (possibly in source)')
            
            if not validate_text_construct(item['title']):
                raise ValidationError('entry title has invalid type')
            if item.get('rights'):
                if not validate_text_construct(item['rights']):
                    raise ValidationError('entry rights has invalid type')
            if item.get('summary'):
                if not validate_text_construct(item['summary']):
                    raise ValidationError('entry summary has invalid type')
            source = item.get('source')
            if source:
                if source.get('title'):
                    if not validate_text_construct(source['title']):
                        raise ValidationError('source title has invalid type')
                if source.get('subtitle'):
                    if not validate_text_construct(source['subtitle']):
                        raise ValidationError('source subtitle has invalid type')
                if source.get('rights'):
                    if not validate_text_construct(source['rights']):
                        raise ValidationError('source rights has invalid type')
            
            alternate_links = {}
            for link in item.get('links'):
                if link.get('rel') == 'alternate' or link.get('rel') == None:
                    key = (link.get('type'), link.get('hreflang'))
                    if key in alternate_links:
                        raise ValidationError('alternate links must have unique type/hreflang')
                    alternate_links[key] = link
            
            if not item.get('content'):
                if not alternate_links:
                    raise ValidationError('if no content, entry must have alternate link')
            
            if item.get('content') and isinstance(item.get('content'), tuple):
                content_type = item.get('content')[0].get('type')
                if item.get('content')[0].get('src'):
                    if item.get('content')[1]:
                        raise ValidationError('content with src should be empty')
                    if not item.get('summary'):
                        raise ValidationError('content with src requires a summary too')
                    if content_type in ['text', 'html', 'xhtml']:
                        raise ValidationError('content with src cannot have type of text, html or xhtml')
                if content_type:
                    if '/' in content_type and \
                        not content_type.startswith('text/') and \
                        not content_type.endswith('/xml') and not content_type.endswith('+xml') and \
                        not content_type in ['application/xml-external-parsed-entity', 'application/xml-dtd']:
                        # @@@ check content is Base64
                        if not item.get('summary'):
                            raise ValidationError('content in Base64 requires a summary too')
                    if content_type not in ['text', 'html', 'xhtml'] and '/' not in content_type:
                        raise ValidationError('content type does not appear to be valid')
                    
                    # @@@ no validation is done that 'html' text constructs are valid HTML
                    # @@@ no validation is done that 'xhtml' text constructs are well-formed XML or valid XHTML
                    
                    return
        
        return



class LegacySyndicationFeed(AtomFeed):
    """
    Provides an SyndicationFeed-compatible interface in its __init__ and
    add_item but is really a new AtomFeed object.
    """
    
    def __init__(self, title, link, description, language=None, author_email=None,
            author_name=None, author_link=None, subtitle=None, categories=[],
            feed_url=None, feed_copyright=None):
        
        atom_id = link
        title = title
        updated = None # will be calculated
        rights = feed_copyright
        subtitle = subtitle
        author_dict = {'name': author_name}
        if author_link:
            author_dict['uri'] = author_uri
        if author_email:
            author_dict['email'] = author_email
        authors = [author_dict]
        if categories:
            categories = [{'term': term} for term in categories]
        links = [{'rel': 'alternate', 'href': link}]
        if feed_url:
            links.append({'rel': 'self', 'href': feed_url})
        if language:
            extra_attrs = {'xml:lang': language}
        else:
            extra_attrs = {}
        
        # description ignored (as with Atom1Feed)
        
        AtomFeed.__init__(self, atom_id, title, updated, rights=rights, subtitle=subtitle,
                authors=authors, categories=categories, links=links, extra_attrs=extra_attrs)
    
    
    def add_item(self, title, link, description, author_email=None,
            author_name=None, author_link=None, pubdate=None, comments=None,
            unique_id=None, enclosure=None, categories=[], item_copyright=None):
        
        if unique_id:
            atom_id = unique_id
        else:
            atom_id = get_tag_uri(link, pubdate)
        title = title
        updated = pubdate
        if item_copyright:
            rights = item_copyright
        else:
            rights = None
        if description:
            summary = 'html', description
        else:
            summary = None
        author_dict = {'name': author_name}
        if author_link:
            author_dict['uri'] = author_uri
        if author_email:
            author_dict['email'] = author_email
        authors = [author_dict]
        categories = [{'term': term} for term in categories]
        links = [{'rel': 'alternate', 'href': link}]
        if enclosure:
            links.append({'rel': 'enclosure', 'href': enclosure.url, 'length': enclosure.length, 'type': enclosure.mime_type})
        
        AtomFeed.add_item(self, atom_id, title, updated, rights=rights, summary=summary,
                authors=authors, categories=categories, links=links)

########NEW FILE########
__FILENAME__ = base

from django.template.loader import render_to_string

class BaseBackend(object):
    """
    The base backend.
    """
    def __init__(self, medium_id, spam_sensitivity=None):
        self.medium_id = medium_id
        if spam_sensitivity is not None:
            self.spam_sensitivity = spam_sensitivity
    
    def can_send(self, user, notice_type):
        """
        Determines whether this backend is allowed to send a notification to
        the given user and notice_type.
        """
        from notification.models import should_send
        if should_send(user, notice_type, self.medium_id):
            return True
        return False
    
    def deliver(self, recipient, notice_type, extra_context):
        """
        Deliver a notification to the given recipient.
        """
        raise NotImplemented()
    
    def get_formatted_messages(self, formats, label, context):
        """
        Returns a dictionary with the format identifier as the key. The values are
        are fully rendered templates with the given context.
        """
        format_templates = {}
        for format in formats:
            # conditionally turn off autoescaping for .txt extensions in format
            if format.endswith(".txt"):
                context.autoescape = False
            format_templates[format] = render_to_string((
                "notification/%s/%s" % (label, format),
                "notification/%s" % format), context_instance=context)
        return format_templates

########NEW FILE########
__FILENAME__ = email
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db.models.loading import get_app
from django.template import Context
from django.template.loader import render_to_string
from django.utils.translation import ugettext
from django.core.exceptions import ImproperlyConfigured

from django.contrib.sites.models import Site

from notification import backends
from notification.message import message_to_text


class EmailBackend(backends.BaseBackend):
    spam_sensitivity = 2
    
    def can_send(self, user, notice_type):
        can_send = super(EmailBackend, self).can_send(user, notice_type)
        if can_send and user.email:
            return True
        return False
        
    def deliver(self, recipient, sender, notice_type, extra_context):
        # TODO: require this to be passed in extra_context
        current_site = Site.objects.get_current()
        notices_url = u"http://%s%s" % (
            unicode(Site.objects.get_current()),
            reverse("notification_notices"),
        )
        
        # update context with user specific translations
        context = Context({
            "recipient": recipient,
            "sender": sender,
            "notice": ugettext(notice_type.display),
            "notices_url": notices_url,
            "current_site": current_site,
        })
        context.update(extra_context)
        
        messages = self.get_formatted_messages((
            "short.txt",
            "full.txt"
        ), notice_type.label, context)
        
        subject = "".join(render_to_string("notification/email_subject.txt", {
            "message": messages["short.txt"],
        }, context).splitlines())
        
        body = render_to_string("notification/email_body.txt", {
            "message": messages["full.txt"],
        }, context)
        
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient.email])

########NEW FILE########
__FILENAME__ = context_processors
from notification.models import Notice


def notification(request):
    if request.user.is_authenticated():
        return {
            "notice_unseen_count": Notice.objects.unseen_count_for(request.user, on_site=True),
        }
    else:
        return {}

########NEW FILE########
__FILENAME__ = decorators
from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.conf import settings

from django.contrib.auth import authenticate, login


def simple_basic_auth_callback(request, user, *args, **kwargs):
    """
    Simple callback to automatically login the given user after a successful
    basic authentication.
    """
    login(request, user)
    request.user = user


def basic_auth_required(realm=None, test_func=None, callback_func=None):
    """
    This decorator should be used with views that need simple authentication
    against Django's authentication framework.
    
    The ``realm`` string is shown during the basic auth query.
    
    It takes a ``test_func`` argument that is used to validate the given
    credentials and return the decorated function if successful.
    
    If unsuccessful the decorator will try to authenticate and checks if the
    user has the ``is_active`` field set to True.
    
    In case of a successful authentication  the ``callback_func`` will be
    called by passing the ``request`` and the ``user`` object. After that the
    actual view function will be called.
    
    If all of the above fails a "Authorization Required" message will be shown.
    """
    if realm is None:
        realm = getattr(settings, "HTTP_AUTHENTICATION_REALM", _("Restricted Access"))
    if test_func is None:
        test_func = lambda u: u.is_authenticated()
    
    def decorator(view_func):
        def basic_auth(request, *args, **kwargs):
            # Just return the original view because already logged in
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            
            # Not logged in, look if login credentials are provided
            if "HTTP_AUTHORIZATION" in request.META:
                auth_method, auth = request.META["HTTP_AUTHORIZATION"].split(" ", 1)
                if "basic" == auth_method.lower():
                    auth = auth.strip().decode("base64")
                    username, password = auth.split(":",1)
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        if user.is_active:
                            if callback_func is not None and callable(callback_func):
                                callback_func(request, user, *args, **kwargs)
                            return view_func(request, *args, **kwargs)
            
            response =  HttpResponse(_("Authorization Required"), mimetype="text/plain")
            response.status_code = 401
            response["WWW-Authenticate"] = "Basic realm='%s'" % realm
            return response
        return basic_auth
    return decorator

########NEW FILE########
__FILENAME__ = engine
import sys
import time
import logging
import traceback

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.core.mail import mail_admins
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from lockfile import FileLock, AlreadyLocked, LockTimeout

from notification.models import NoticeQueueBatch
from notification import models as notification

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "NOTIFICATION_LOCK_WAIT_TIMEOUT", -1)


def send_all():
    lock = FileLock("send_notices")
    
    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")
    
    batches, sent = 0, 0
    start_time = time.time()
    
    try:
        # nesting the try statement to be Python 2.4
        try:
            for queued_batch in NoticeQueueBatch.objects.all():
                notices = pickle.loads(str(queued_batch.pickled_data).decode("base64"))
                for user, label, extra_context, on_site, sender in notices:
                    try:
                        user = User.objects.get(pk=user)
                        logging.info("emitting notice %s to %s" % (label, user))
                        # call this once per user to be atomic and allow for logging to
                        # accurately show how long each takes.
                        notification.send_now([user], label, extra_context, on_site, sender)
                    except User.DoesNotExist:
                        # Ignore deleted users, just warn about them
                        logging.warning("not emitting notice %s to user %s since it does not exist" % (label, user))
                    sent += 1
                queued_batch.delete()
                batches += 1
        except:
            # get the exception
            exc_class, e, t = sys.exc_info()
            # email people
            current_site = Site.objects.get_current()
            subject = "[%s emit_notices] %r" % (current_site.name, e)
            message = "%s" % ("\n".join(traceback.format_exception(*sys.exc_info())),)
            mail_admins(subject, message, fail_silently=True)
            # log it as critical
            logging.critical("an exception occurred: %r" % e)
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")
    
    logging.info("")
    logging.info("%s batches, %s sent" % (batches, sent,))
    logging.info("done in %.2f seconds" % (time.time() - start_time))

########NEW FILE########
__FILENAME__ = feeds
import datetime

from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaks, escape, striptags
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from notification.models import Notice
from notification.atomformat import Feed


ITEMS_PER_FEED = getattr(settings, "ITEMS_PER_FEED", 20)
DEFAULT_HTTP_PROTOCOL = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")


class BaseNoticeFeed(Feed):
    
    def item_id(self, notification):
        return "%s://%s%s" % (
            DEFAULT_HTTP_PROTOCOL,
            Site.objects.get_current().domain,
            notification.get_absolute_url(),
        )
    
    def item_title(self, notification):
        return striptags(notification.message)
    
    def item_updated(self, notification):
        return notification.added
    
    def item_published(self, notification):
        return notification.added
    
    def item_content(self, notification):
        return {"type": "html"}, linebreaks(escape(notification.message))
    
    def item_links(self, notification):
        return [{"href": self.item_id(notification)}]
    
    def item_authors(self, notification):
        return [{"name": notification.recipient.username}]


class NoticeUserFeed(BaseNoticeFeed):
    
    def get_object(self, params):
        return get_object_or_404(User, username=params[0].lower())
    
    def feed_id(self, user):
        return "%s://%s%s" % (
            DEFAULT_HTTP_PROTOCOL,
            Site.objects.get_current().domain,
            reverse("notification_feed_for_user"),
        )
    
    def feed_title(self, user):
        return _("Notices Feed")
    
    def feed_updated(self, user):
        qs = Notice.objects.filter(recipient=user)
        # We return an arbitrary date if there are no results, because there
        # must be a feed_updated field as per the Atom specifications, however
        # there is no real data to go by, and an arbitrary date can be static.
        if qs.count() == 0:
            return datetime.datetime(year=2008, month=7, day=1)
        return qs.latest("added").added
    
    def feed_links(self, user):
        complete_url = "%s://%s%s" % (
            DEFAULT_HTTP_PROTOCOL,
            Site.objects.get_current().domain,
            reverse("notification_notices"),
        )
        return ({"href": complete_url},)
    
    def items(self, user):
        return Notice.objects.notices_for(user).order_by("-added")[:ITEMS_PER_FEED]

########NEW FILE########
__FILENAME__ = lockfile
"""
lockfile.py - Platform-independent advisory file locks.

Requires Python 2.5 unless you apply 2.4.diff
Locking is done on a per-thread basis instead of a per-process basis.

Usage:

>>> lock = FileLock('somefile')
>>> try:
...     lock.acquire()
... except AlreadyLocked:
...     print 'somefile', 'is locked already.'
... except LockFailed:
...     print 'somefile', 'can\\'t be locked.'
... else:
...     print 'got lock'
got lock
>>> print lock.is_locked()
True
>>> lock.release()

>>> lock = FileLock('somefile')
>>> print lock.is_locked()
False
>>> with lock:
...    print lock.is_locked()
True
>>> print lock.is_locked()
False
>>> # It is okay to lock twice from the same thread...
>>> with lock:
...     lock.acquire()
...
>>> # Though no counter is kept, so you can't unlock multiple times...
>>> print lock.is_locked()
False

Exceptions:

    Error - base class for other exceptions
        LockError - base class for all locking exceptions
            AlreadyLocked - Another thread or process already holds the lock
            LockFailed - Lock failed for some other reason
        UnlockError - base class for all unlocking exceptions
            AlreadyUnlocked - File was not locked.
            NotMyLock - File was locked but not by the current thread/process
"""

from __future__ import division

import sys
import socket
import os
import thread
import threading
import time
import errno
import urllib

# Work with PEP8 and non-PEP8 versions of threading module.
if not hasattr(threading, "current_thread"):
    threading.current_thread = threading.currentThread
if not hasattr(threading.Thread, "get_name"):
    threading.Thread.get_name = threading.Thread.getName

__all__ = ['Error', 'LockError', 'LockTimeout', 'AlreadyLocked',
           'LockFailed', 'UnlockError', 'NotLocked', 'NotMyLock',
           'LinkFileLock', 'MkdirFileLock', 'SQLiteFileLock']

class Error(Exception):
    """
    Base class for other exceptions.

    >>> try:
    ...   raise Error
    ... except Exception:
    ...   pass
    """
    pass

class LockError(Error):
    """
    Base class for error arising from attempts to acquire the lock.

    >>> try:
    ...   raise LockError
    ... except Error:
    ...   pass
    """
    pass

class LockTimeout(LockError):
    """Raised when lock creation fails within a user-defined period of time.

    >>> try:
    ...   raise LockTimeout
    ... except LockError:
    ...   pass
    """
    pass

class AlreadyLocked(LockError):
    """Some other thread/process is locking the file.

    >>> try:
    ...   raise AlreadyLocked
    ... except LockError:
    ...   pass
    """
    pass

class LockFailed(LockError):
    """Lock file creation failed for some other reason.

    >>> try:
    ...   raise LockFailed
    ... except LockError:
    ...   pass
    """
    pass

class UnlockError(Error):
    """
    Base class for errors arising from attempts to release the lock.

    >>> try:
    ...   raise UnlockError
    ... except Error:
    ...   pass
    """
    pass

class NotLocked(UnlockError):
    """Raised when an attempt is made to unlock an unlocked file.

    >>> try:
    ...   raise NotLocked
    ... except UnlockError:
    ...   pass
    """
    pass

class NotMyLock(UnlockError):
    """Raised when an attempt is made to unlock a file someone else locked.

    >>> try:
    ...   raise NotMyLock
    ... except UnlockError:
    ...   pass
    """
    pass

class LockBase:
    """Base class for platform-specific lock classes."""
    def __init__(self, path, threaded=True):
        """
        >>> lock = LockBase('somefile')
        >>> lock = LockBase('somefile', threaded=False)
        """
        self.path = path
        self.lock_file = os.path.abspath(path) + ".lock"
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        if threaded:
            name = threading.current_thread().get_name()
            tname = "%s-" % urllib.quote(name, safe="")
        else:
            tname = ""
        dirname = os.path.dirname(self.lock_file)
        self.unique_name = os.path.join(dirname,
                                        "%s.%s%s" % (self.hostname,
                                                     tname,
                                                     self.pid))

    def acquire(self, timeout=None):
        """
        Acquire the lock.

        * If timeout is omitted (or None), wait forever trying to lock the
          file.

        * If timeout > 0, try to acquire the lock for that many seconds.  If
          the lock period expires and the file is still locked, raise
          LockTimeout.

        * If timeout <= 0, raise AlreadyLocked immediately if the file is
          already locked.
        """
        raise NotImplemented("implement in subclass")

    def release(self):
        """
        Release the lock.

        If the file is not locked, raise NotLocked.
        """
        raise NotImplemented("implement in subclass")

    def is_locked(self):
        """
        Tell whether or not the file is locked.
        """
        raise NotImplemented("implement in subclass")

    def i_am_locking(self):
        """
        Return True if this object is locking the file.
        """
        raise NotImplemented("implement in subclass")

    def break_lock(self):
        """
        Remove a lock.  Useful if a locking thread failed to unlock.
        """
        raise NotImplemented("implement in subclass")

    def __enter__(self):
        """
        Context manager support.
        """
        self.acquire()
        return self

    def __exit__(self, *_exc):
        """
        Context manager support.
        """
        self.release()

class LinkFileLock(LockBase):
    """Lock access to a file using atomic property of link(2)."""

    def acquire(self, timeout=None):
        try:
            open(self.unique_name, "wb").close()
        except IOError:
            raise LockFailed("failed to create %s" % self.unique_name)

        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        while True:
            # Try and create a hard link to it.
            try:
                os.link(self.unique_name, self.lock_file)
            except OSError:
                # Link creation failed.  Maybe we've double-locked?
                nlinks = os.stat(self.unique_name).st_nlink
                if nlinks == 2:
                    # The original link plus the one I created == 2.  We're
                    # good to go.
                    return
                else:
                    # Otherwise the lock creation failed.
                    if timeout is not None and time.time() > end_time:
                        os.unlink(self.unique_name)
                        if timeout > 0:
                            raise LockTimeout
                        else:
                            raise AlreadyLocked
                    time.sleep(timeout is not None and timeout/10 or 0.1)
            else:
                # Link creation succeeded.  We're good to go.
                return

    def release(self):
        if not self.is_locked():
            raise NotLocked
        elif not os.path.exists(self.unique_name):
            raise NotMyLock
        os.unlink(self.unique_name)
        os.unlink(self.lock_file)

    def is_locked(self):
        return os.path.exists(self.lock_file)

    def i_am_locking(self):
        return (self.is_locked() and
                os.path.exists(self.unique_name) and
                os.stat(self.unique_name).st_nlink == 2)

    def break_lock(self):
        if os.path.exists(self.lock_file):
            os.unlink(self.lock_file)

class MkdirFileLock(LockBase):
    """Lock file by creating a directory."""
    def __init__(self, path, threaded=True):
        """
        >>> lock = MkdirFileLock('somefile')
        >>> lock = MkdirFileLock('somefile', threaded=False)
        """
        LockBase.__init__(self, path, threaded)
        if threaded:
            tname = "%x-" % thread.get_ident()
        else:
            tname = ""
        # Lock file itself is a directory.  Place the unique file name into
        # it.
        self.unique_name  = os.path.join(self.lock_file,
                                         "%s.%s%s" % (self.hostname,
                                                      tname,
                                                      self.pid))

    def acquire(self, timeout=None):
        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        if timeout is None:
            wait = 0.1
        else:
            wait = max(0, timeout / 10)

        while True:
            try:
                os.mkdir(self.lock_file)
            except OSError:
                err = sys.exc_info()[1]
                if err.errno == errno.EEXIST:
                    # Already locked.
                    if os.path.exists(self.unique_name):
                        # Already locked by me.
                        return
                    if timeout is not None and time.time() > end_time:
                        if timeout > 0:
                            raise LockTimeout
                        else:
                            # Someone else has the lock.
                            raise AlreadyLocked
                    time.sleep(wait)
                else:
                    # Couldn't create the lock for some other reason
                    raise LockFailed("failed to create %s" % self.lock_file)
            else:
                open(self.unique_name, "wb").close()
                return

    def release(self):
        if not self.is_locked():
            raise NotLocked
        elif not os.path.exists(self.unique_name):
            raise NotMyLock
        os.unlink(self.unique_name)
        os.rmdir(self.lock_file)

    def is_locked(self):
        return os.path.exists(self.lock_file)

    def i_am_locking(self):
        return (self.is_locked() and
                os.path.exists(self.unique_name))

    def break_lock(self):
        if os.path.exists(self.lock_file):
            for name in os.listdir(self.lock_file):
                os.unlink(os.path.join(self.lock_file, name))
            os.rmdir(self.lock_file)

class SQLiteFileLock(LockBase):
    "Demonstration of using same SQL-based locking."

    import tempfile
    _fd, testdb = tempfile.mkstemp()
    os.close(_fd)
    os.unlink(testdb)
    del _fd, tempfile

    def __init__(self, path, threaded=True):
        LockBase.__init__(self, path, threaded)
        self.lock_file = unicode(self.lock_file)
        self.unique_name = unicode(self.unique_name)

        import sqlite3
        self.connection = sqlite3.connect(SQLiteFileLock.testdb)
        
        c = self.connection.cursor()
        try:
            c.execute("create table locks"
                      "("
                      "   lock_file varchar(32),"
                      "   unique_name varchar(32)"
                      ")")
        except sqlite3.OperationalError:
            pass
        else:
            self.connection.commit()
            import atexit
            atexit.register(os.unlink, SQLiteFileLock.testdb)

    def acquire(self, timeout=None):
        end_time = time.time()
        if timeout is not None and timeout > 0:
            end_time += timeout

        if timeout is None:
            wait = 0.1
        elif timeout <= 0:
            wait = 0
        else:
            wait = timeout / 10

        cursor = self.connection.cursor()

        while True:
            if not self.is_locked():
                # Not locked.  Try to lock it.
                cursor.execute("insert into locks"
                               "  (lock_file, unique_name)"
                               "  values"
                               "  (?, ?)",
                               (self.lock_file, self.unique_name))
                self.connection.commit()

                # Check to see if we are the only lock holder.
                cursor.execute("select * from locks"
                               "  where unique_name = ?",
                               (self.unique_name,))
                rows = cursor.fetchall()
                if len(rows) > 1:
                    # Nope.  Someone else got there.  Remove our lock.
                    cursor.execute("delete from locks"
                                   "  where unique_name = ?",
                                   (self.unique_name,))
                    self.connection.commit()
                else:
                    # Yup.  We're done, so go home.
                    return
            else:
                # Check to see if we are the only lock holder.
                cursor.execute("select * from locks"
                               "  where unique_name = ?",
                               (self.unique_name,))
                rows = cursor.fetchall()
                if len(rows) == 1:
                    # We're the locker, so go home.
                    return
                    
            # Maybe we should wait a bit longer.
            if timeout is not None and time.time() > end_time:
                if timeout > 0:
                    # No more waiting.
                    raise LockTimeout
                else:
                    # Someone else has the lock and we are impatient..
                    raise AlreadyLocked

            # Well, okay.  We'll give it a bit longer.
            time.sleep(wait)

    def release(self):
        if not self.is_locked():
            raise NotLocked
        if not self.i_am_locking():
            raise NotMyLock((self._who_is_locking(), self.unique_name))
        cursor = self.connection.cursor()
        cursor.execute("delete from locks"
                       "  where unique_name = ?",
                       (self.unique_name,))
        self.connection.commit()

    def _who_is_locking(self):
        cursor = self.connection.cursor()
        cursor.execute("select unique_name from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        return cursor.fetchone()[0]
        
    def is_locked(self):
        cursor = self.connection.cursor()
        cursor.execute("select * from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        rows = cursor.fetchall()
        return not not rows

    def i_am_locking(self):
        cursor = self.connection.cursor()
        cursor.execute("select * from locks"
                       "  where lock_file = ?"
                       "    and unique_name = ?",
                       (self.lock_file, self.unique_name))
        return not not cursor.fetchall()

    def break_lock(self):
        cursor = self.connection.cursor()
        cursor.execute("delete from locks"
                       "  where lock_file = ?",
                       (self.lock_file,))
        self.connection.commit()

if hasattr(os, "link"):
    FileLock = LinkFileLock
else:
    FileLock = MkdirFileLock

########NEW FILE########
__FILENAME__ = emit_notices

import logging

from django.core.management.base import NoArgsCommand

from notification.engine import send_all

class Command(NoArgsCommand):
    help = "Emit queued notices."
    
    def handle_noargs(self, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        send_all()
    
########NEW FILE########
__FILENAME__ = message
from django.db.models import get_model
from django.utils.translation import ugettext

# a notice like "foo and bar are now friends" is stored in the database
# as "{auth.User.5} and {auth.User.7} are now friends".
#
# encode_object takes an object and turns it into "{app.Model.pk}" or
# "{app.Model.pk.msgid}" if named arguments are used in send()
# decode_object takes "{app.Model.pk}" and turns it into the object
#
# encode_message takes either ("%s and %s are now friends", [foo, bar]) or
# ("%(foo)s and %(bar)s are now friends", {'foo':foo, 'bar':bar}) and turns
# it into "{auth.User.5} and {auth.User.7} are now friends".
#
# decode_message takes "{auth.User.5} and {auth.User.7}" and converts it
# into a string using the given decode function to convert the object to
# string representation
#
# message_to_text and message_to_html use decode_message to produce a
# text and html version of the message respectively.

def encode_object(obj, name=None):
    encoded = "%s.%s.%s" % (obj._meta.app_label, obj._meta.object_name, obj.pk)
    if name:
        encoded = "%s.%s" % (encoded, name)
    return "{%s}" % encoded


def encode_message(message_template, objects):
    if objects is None:
        return message_template
    if isinstance(objects, list) or isinstance(objects, tuple):
        return message_template % tuple(encode_object(obj) for obj in objects)
    if type(objects) is dict:
        return message_template % dict((name, encode_object(obj, name)) for name, obj in objects.iteritems())
    return ""


def decode_object(ref):
    decoded = ref.split(".")
    if len(decoded) == 4:
        app, name, pk, msgid = decoded
        return get_model(app, name).objects.get(pk=pk), msgid
    app, name, pk = decoded
    return get_model(app, name).objects.get(pk=pk), None


class FormatException(Exception):
    pass


def decode_message(message, decoder):
    out = []
    objects = []
    mapping = {}
    in_field = False
    prev = 0
    for index, ch in enumerate(message):
        if not in_field:
            if ch == "{":
                in_field = True
                if prev != index:
                    out.append(message[prev:index])
                prev = index
            elif ch == "}":
                raise FormatException("unmatched }")
        elif in_field:
            if ch == "{":
                raise FormatException("{ inside {}")
            elif ch == "}":
                in_field = False
                obj, msgid = decoder(message[prev+1:index])
                if msgid is None:
                    objects.append(obj)
                    out.append("%s")
                else:
                    mapping[msgid] = obj
                    out.append("%("+msgid+")s")
                prev = index + 1
    if in_field:
        raise FormatException("unmatched {")
    if prev <= index:
        out.append(message[prev:index+1])
    result = "".join(out)
    if mapping:
        args = mapping
    else:
        args = tuple(objects)
    return ugettext(result) % args


def message_to_text(message):
    def decoder(ref):
        obj, msgid = decode_object(ref)
        return unicode(obj), msgid
    return decode_message(message, decoder)


def message_to_html(message):
    def decoder(ref):
        obj, msgid = decode_object(ref)
        if hasattr(obj, "get_absolute_url"): # don't fail silenty if get_absolute_url hasn't been defined
            return u"""<a href="%s">%s</a>""" % (obj.get_absolute_url(), unicode(obj)), msgid
        else:
            return unicode(obj), msgid
    return decode_message(message, decoder)
    
########NEW FILE########
__FILENAME__ = models
import datetime

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.db import models
from django.db.models.query import QuerySet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, get_language, activate

from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from notification import backends
from notification.message import encode_message


QUEUE_ALL = getattr(settings, "NOTIFICATION_QUEUE_ALL", False)


class LanguageStoreNotAvailable(Exception):
    pass


class NoticeType(models.Model):
    
    label = models.CharField(_("label"), max_length=40)
    display = models.CharField(_("display"), max_length=50)
    description = models.CharField(_("description"), max_length=100)
    
    # by default only on for media with sensitivity less than or equal to this number
    default = models.IntegerField(_("default"))
    
    def __unicode__(self):
        return self.label
    
    class Meta:
        verbose_name = _("notice type")
        verbose_name_plural = _("notice types")


NOTIFICATION_BACKENDS = backends.load_backends()

NOTICE_MEDIA = []
NOTICE_MEDIA_DEFAULTS = {}
for key, backend in NOTIFICATION_BACKENDS.items():
    # key is a tuple (medium_id, backend_label)
    NOTICE_MEDIA.append(key)
    NOTICE_MEDIA_DEFAULTS[key[0]] = backend.spam_sensitivity


class NoticeSetting(models.Model):
    """
    Indicates, for a given user, whether to send notifications
    of a given type to a given medium.
    """
    
    user = models.ForeignKey(User, verbose_name=_("user"))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_("notice type"))
    medium = models.CharField(_("medium"), max_length=1, choices=NOTICE_MEDIA)
    send = models.BooleanField(_("send"))
    
    class Meta:
        verbose_name = _("notice setting")
        verbose_name_plural = _("notice settings")
        unique_together = ("user", "notice_type", "medium")


def get_notification_setting(user, notice_type, medium):
    try:
        return NoticeSetting.objects.get(user=user, notice_type=notice_type, medium=medium)
    except NoticeSetting.DoesNotExist:
        default = (NOTICE_MEDIA_DEFAULTS[medium] <= notice_type.default)
        setting = NoticeSetting(user=user, notice_type=notice_type, medium=medium, send=default)
        setting.save()
        return setting


def should_send(user, notice_type, medium):
    return get_notification_setting(user, notice_type, medium).send


class NoticeManager(models.Manager):
    
    def notices_for(self, user, archived=False, unseen=None, on_site=None, sent=False):
        """
        returns Notice objects for the given user.
        
        If archived=False, it only include notices not archived.
        If archived=True, it returns all notices for that user.
        
        If unseen=None, it includes all notices.
        If unseen=True, return only unseen notices.
        If unseen=False, return only seen notices.
        """
        if sent:
            lookup_kwargs = {"sender": user}
        else:
            lookup_kwargs = {"recipient": user}
        qs = self.filter(**lookup_kwargs)
        if not archived:
            self.filter(archived=archived)
        if unseen is not None:
            qs = qs.filter(unseen=unseen)
        if on_site is not None:
            qs = qs.filter(on_site=on_site)
        return qs
    
    def unseen_count_for(self, recipient, **kwargs):
        """
        returns the number of unseen notices for the given user but does not
        mark them seen
        """
        return self.notices_for(recipient, unseen=True, **kwargs).count()
    
    def received(self, recipient, **kwargs):
        """
        returns notices the given recipient has recieved.
        """
        kwargs["sent"] = False
        return self.notices_for(recipient, **kwargs)
    
    def sent(self, sender, **kwargs):
        """
        returns notices the given sender has sent
        """
        kwargs["sent"] = True
        return self.notices_for(sender, **kwargs)


class Notice(models.Model):
    
    recipient = models.ForeignKey(User, related_name="recieved_notices", verbose_name=_("recipient"))
    sender = models.ForeignKey(User, null=True, related_name="sent_notices", verbose_name=_("sender"))
    message = models.TextField(_("message"))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_("notice type"))
    added = models.DateTimeField(_("added"), default=datetime.datetime.now)
    unseen = models.BooleanField(_("unseen"), default=True)
    archived = models.BooleanField(_("archived"), default=False)
    on_site = models.BooleanField(_("on site"))
    
    objects = NoticeManager()
    
    def __unicode__(self):
        return self.message
    
    def archive(self):
        self.archived = True
        self.save()
    
    def is_unseen(self):
        """
        returns value of self.unseen but also changes it to false.
        
        Use this in a template to mark an unseen notice differently the first
        time it is shown.
        """
        unseen = self.unseen
        if unseen:
            self.unseen = False
            self.save()
        return unseen
    
    class Meta:
        ordering = ["-added"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")
    
    def get_absolute_url(self):
        return reverse("notification_notice", args=[str(self.pk)])


class NoticeQueueBatch(models.Model):
    """
    A queued notice.
    Denormalized data for a notice.
    """
    pickled_data = models.TextField()


def create_notice_type(label, display, description, default=2, verbosity=1):
    """
    Creates a new NoticeType.
    
    This is intended to be used by other apps as a post_syncdb manangement step.
    """
    try:
        notice_type = NoticeType.objects.get(label=label)
        updated = False
        if display != notice_type.display:
            notice_type.display = display
            updated = True
        if description != notice_type.description:
            notice_type.description = description
            updated = True
        if default != notice_type.default:
            notice_type.default = default
            updated = True
        if updated:
            notice_type.save()
            if verbosity > 1:
                print "Updated %s NoticeType" % label
    except NoticeType.DoesNotExist:
        NoticeType(label=label, display=display, description=description, default=default).save()
        if verbosity > 1:
            print "Created %s NoticeType" % label


def get_notification_language(user):
    """
    Returns site-specific notification language for this user. Raises
    LanguageStoreNotAvailable if this site does not use translated
    notifications.
    """
    if getattr(settings, "NOTIFICATION_LANGUAGE_MODULE", False):
        try:
            app_label, model_name = settings.NOTIFICATION_LANGUAGE_MODULE.split(".")
            model = models.get_model(app_label, model_name)
            language_model = model._default_manager.get(user__id__exact=user.id)
            if hasattr(language_model, "language"):
                return language_model.language
        except (ImportError, ImproperlyConfigured, model.DoesNotExist):
            raise LanguageStoreNotAvailable
    raise LanguageStoreNotAvailable


def get_formatted_messages(formats, label, context):
    """
    Returns a dictionary with the format identifier as the key. The values are
    are fully rendered templates with the given context.
    """
    format_templates = {}
    for format in formats:
        # conditionally turn off autoescaping for .txt extensions in format
        if format.endswith(".txt"):
            context.autoescape = False
        else:
            context.autoescape = True
        format_templates[format] = render_to_string((
            "notification/%s/%s" % (label, format),
            "notification/%s" % format), context_instance=context)
    return format_templates


def send_now(users, label, extra_context=None, on_site=True, sender=None):
    """
    Creates a new notice.
    
    This is intended to be how other apps create new notices.
    
    notification.send(user, "friends_invite_sent", {
        "spam": "eggs",
        "foo": "bar",
    )
    
    You can pass in on_site=False to prevent the notice emitted from being
    displayed on the site.
    """
    if extra_context is None:
        extra_context = {}
    
    notice_type = NoticeType.objects.get(label=label)
    
    protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
    current_site = Site.objects.get_current()
    
    notices_url = u"%s://%s%s" % (
        protocol,
        unicode(current_site),
        reverse("notification_notices"),
    )
    
    current_language = get_language()
    
    formats = (
        "short.txt",
        "full.txt",
        "notice.html",
        "full.html",
    ) # TODO make formats configurable
    
    for user in users:
        recipients = []
        # get user language for user from language store defined in
        # NOTIFICATION_LANGUAGE_MODULE setting
        try:
            language = get_notification_language(user)
        except LanguageStoreNotAvailable:
            language = None
        
        if language is not None:
            # activate the user's language
            activate(language)
        
        for backend in NOTIFICATION_BACKENDS.values():
            if backend.can_send(user, notice_type):
                backend.deliver(user, sender, notice_type, extra_context)
    
    # reset environment to original language
    activate(current_language)


def send(*args, **kwargs):
    """
    A basic interface around both queue and send_now. This honors a global
    flag NOTIFICATION_QUEUE_ALL that helps determine whether all calls should
    be queued or not. A per call ``queue`` or ``now`` keyword argument can be
    used to always override the default global behavior.
    """
    queue_flag = kwargs.pop("queue", False)
    now_flag = kwargs.pop("now", False)
    assert not (queue_flag and now_flag), "'queue' and 'now' cannot both be True."
    if queue_flag:
        return queue(*args, **kwargs)
    elif now_flag:
        return send_now(*args, **kwargs)
    else:
        if QUEUE_ALL:
            return queue(*args, **kwargs)
        else:
            return send_now(*args, **kwargs)


def queue(users, label, extra_context=None, on_site=True, sender=None):
    """
    Queue the notification in NoticeQueueBatch. This allows for large amounts
    of user notifications to be deferred to a seperate process running outside
    the webserver.
    """
    if extra_context is None:
        extra_context = {}
    if isinstance(users, QuerySet):
        users = [row["pk"] for row in users.values("pk")]
    else:
        users = [user.pk for user in users]
    notices = []
    for user in users:
        notices.append((user, label, extra_context, on_site, sender))
    NoticeQueueBatch(pickled_data=pickle.dumps(notices).encode("base64")).save()


class ObservedItemManager(models.Manager):
    
    def all_for(self, observed, signal):
        """
        Returns all ObservedItems for an observed object,
        to be sent when a signal is emited.
        """
        content_type = ContentType.objects.get_for_model(observed)
        observed_items = self.filter(content_type=content_type, object_id=observed.id, signal=signal)
        return observed_items
    
    def get_for(self, observed, observer, signal):
        content_type = ContentType.objects.get_for_model(observed)
        observed_item = self.get(content_type=content_type, object_id=observed.id, user=observer, signal=signal)
        return observed_item


class ObservedItem(models.Model):
    
    user = models.ForeignKey(User, verbose_name=_("user"))
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    observed_object = generic.GenericForeignKey("content_type", "object_id")
    
    notice_type = models.ForeignKey(NoticeType, verbose_name=_("notice type"))
    
    added = models.DateTimeField(_("added"), default=datetime.datetime.now)
    
    # the signal that will be listened to send the notice
    signal = models.TextField(verbose_name=_("signal"))
    
    objects = ObservedItemManager()
    
    class Meta:
        ordering = ["-added"]
        verbose_name = _("observed item")
        verbose_name_plural = _("observed items")
    
    def send_notice(self, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update({"observed": self.observed_object})
        send([self.user], self.notice_type.label, extra_context)


def observe(observed, observer, notice_type_label, signal="post_save"):
    """
    Create a new ObservedItem.
    
    To be used by applications to register a user as an observer for some object.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    observed_item = ObservedItem(
        user=observer, observed_object=observed,
        notice_type=notice_type, signal=signal
    )
    observed_item.save()
    return observed_item


def stop_observing(observed, observer, signal="post_save"):
    """
    Remove an observed item.
    """
    observed_item = ObservedItem.objects.get_for(observed, observer, signal)
    observed_item.delete()


def send_observation_notices_for(observed, signal="post_save", extra_context=None):
    """
    Send a notice for each registered user about an observed object.
    """
    if extra_context is None:
        extra_context = {}
    observed_items = ObservedItem.objects.all_for(observed, signal)
    for observed_item in observed_items:
        observed_item.send_notice(extra_context)
    return observed_items


def is_observing(observed, observer, signal="post_save"):
    if isinstance(observer, AnonymousUser):
        return False
    try:
        observed_items = ObservedItem.objects.get_for(observed, observer, signal)
        return True
    except ObservedItem.DoesNotExist:
        return False
    except ObservedItem.MultipleObjectsReturned:
        return True


def handle_observations(sender, instance, *args, **kw):
    send_observation_notices_for(instance)

########NEW FILE########
__FILENAME__ = captureas_tag
from django import template

register = template.Library()

@register.tag(name='captureas')
def do_captureas(parser, token):
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)

class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from notification.views import notices, mark_all_seen, feed_for_user, single, notice_settings


urlpatterns = patterns("",
    url(r"^$", notices, name="notification_notices"),
    url(r"^settings/$", notice_settings, name="notification_notice_settings"),
    url(r"^(\d+)/$", single, name="notification_notice"),
    url(r"^feed/$", feed_for_user, name="notification_feed_for_user"),
    url(r"^mark_all_seen/$", mark_all_seen, name="notification_mark_all_seen"),
)
########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext

from django.contrib.auth.decorators import login_required
from django.contrib.syndication.views import feed

from notification.models import *
from notification.decorators import basic_auth_required, simple_basic_auth_callback
from notification.feeds import NoticeUserFeed


@basic_auth_required(realm="Notices Feed", callback_func=simple_basic_auth_callback)
def feed_for_user(request):
    """
    An atom feed for all unarchived :model:`notification.Notice`s for a user.
    """
    url = "feed/%s" % request.user.username
    return feed(request, url, {
        "feed": NoticeUserFeed,
    })


@login_required
def notices(request):
    """
    The main notices index view.
    
    Template: :template:`notification/notices.html`
    
    Context:
    
        notices
            A list of :model:`notification.Notice` objects that are not archived
            and to be displayed on the site.
    """
    notices = Notice.objects.notices_for(request.user, on_site=True)
    
    return render_to_response("notification/notices.html", {
        "notices": notices,
    }, context_instance=RequestContext(request))


@login_required
def notice_settings(request):
    """
    The notice settings view.
    
    Template: :template:`notification/notice_settings.html`
    
    Context:
        
        notice_types
            A list of all :model:`notification.NoticeType` objects.
        
        notice_settings
            A dictionary containing ``column_headers`` for each ``NOTICE_MEDIA``
            and ``rows`` containing a list of dictionaries: ``notice_type``, a
            :model:`notification.NoticeType` object and ``cells``, a list of
            tuples whose first value is suitable for use in forms and the second
            value is ``True`` or ``False`` depending on a ``request.POST``
            variable called ``form_label``, whose valid value is ``on``.
    """
    notice_types = NoticeType.objects.all()
    settings_table = []
    for notice_type in notice_types:
        settings_row = []
        for medium_id, medium_display in NOTICE_MEDIA:
            form_label = "%s_%s" % (notice_type.label, medium_id)
            setting = get_notification_setting(request.user, notice_type, medium_id)
            if request.method == "POST":
                if request.POST.get(form_label) == "on":
                    if not setting.send:
                        setting.send = True
                        setting.save()
                else:
                    if setting.send:
                        setting.send = False
                        setting.save()
            settings_row.append((form_label, setting.send))
        settings_table.append({"notice_type": notice_type, "cells": settings_row})
    
    if request.method == "POST":
        next_page = request.POST.get("next_page", ".")
        return HttpResponseRedirect(next_page)
    
    notice_settings = {
        "column_headers": [medium_display for medium_id, medium_display in NOTICE_MEDIA],
        "rows": settings_table,
    }
    
    return render_to_response("notification/notice_settings.html", {
        "notice_types": notice_types,
        "notice_settings": notice_settings,
    }, context_instance=RequestContext(request))


@login_required
def single(request, id, mark_seen=True):
    """
    Detail view for a single :model:`notification.Notice`.
    
    Template: :template:`notification/single.html`
    
    Context:
    
        notice
            The :model:`notification.Notice` being viewed
    
    Optional arguments:
    
        mark_seen
            If ``True``, mark the notice as seen if it isn't
            already.  Do nothing if ``False``.  Default: ``True``.
    """
    notice = get_object_or_404(Notice, id=id)
    if request.user == notice.recipient:
        if mark_seen and notice.unseen:
            notice.unseen = False
            notice.save()
        return render_to_response("notification/single.html", {
            "notice": notice,
        }, context_instance=RequestContext(request))
    raise Http404


@login_required
def archive(request, noticeid=None, next_page=None):
    """
    Archive a :model:`notices.Notice` if the requesting user is the
    recipient or if the user is a superuser.  Returns a
    ``HttpResponseRedirect`` when complete.
    
    Optional arguments:
    
        noticeid
            The ID of the :model:`notices.Notice` to be archived.
        
        next_page
            The page to redirect to when done.
    """
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.recipient or request.user.is_superuser:
                notice.archive()
            else:   # you can archive other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)


@login_required
def delete(request, noticeid=None, next_page=None):
    """
    Delete a :model:`notices.Notice` if the requesting user is the recipient
    or if the user is a superuser.  Returns a ``HttpResponseRedirect`` when
    complete.
    
    Optional arguments:
    
        noticeid
            The ID of the :model:`notices.Notice` to be archived.
        
        next_page
            The page to redirect to when done.
    """
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.recipient or request.user.is_superuser:
                notice.delete()
            else:   # you can delete other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)


@login_required
def mark_all_seen(request):
    """
    Mark all unseen notices for the requesting user as seen.  Returns a
    ``HttpResponseRedirect`` when complete. 
    """
    
    for notice in Notice.objects.notices_for(request.user, unseen=True):
        notice.unseen = False
        notice.save()
    return HttpResponseRedirect(reverse("notification_notices"))
########NEW FILE########
