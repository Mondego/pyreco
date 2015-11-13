__FILENAME__ = admin
import logging

from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from forms import ArticleAdminForm
from models import Tag, Article, ArticleStatus, Attachment

log = logging.getLogger('articles.admin')

class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'article_count')

    def article_count(self, obj):
        return obj.article_set.count()
    article_count.short_description = _('Applied To')

class ArticleStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_live')
    list_filter = ('is_live',)
    search_fields = ('name',)

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 5
    max_num = 15

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'tag_count', 'status', 'author', 'publish_date',
                    'expiration_date', 'is_active')
    list_filter = ('author', 'status', 'is_active', 'publish_date',
                   'expiration_date', 'sites')
    list_per_page = 25
    search_fields = ('title', 'keywords', 'description', 'content')
    date_hierarchy = 'publish_date'
    form = ArticleAdminForm
    inlines = [
        AttachmentInline,
    ]

    fieldsets = (
        (None, {'fields': ('title', 'content', 'tags', 'auto_tag', 'markup', 'status')}),
        ('Metadata', {
            'fields': ('keywords', 'description',),
            'classes': ('collapse',)
        }),
        ('Relationships', {
            'fields': ('followup_for', 'related_articles'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {'fields': ('publish_date', 'expiration_date')}),
        ('AddThis Button Options', {
            'fields': ('use_addthis_button', 'addthis_use_author', 'addthis_username'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('slug', 'is_active', 'login_required', 'sites'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('tags', 'followup_for', 'related_articles')
    prepopulated_fields = {'slug': ('title',)}

    def tag_count(self, obj):
        return str(obj.tags.count())
    tag_count.short_description = _('Tags')

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_active.short_description = _('Mark select articles as active')

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_inactive.short_description = _('Mark select articles as inactive')

    def get_actions(self, request):
        actions = super(ArticleAdmin, self).get_actions(request)

        def dynamic_status(name, status):
            def status_func(self, request, queryset):
                queryset.update(status=status)

            status_func.__name__ = name
            status_func.short_description = _('Set status of selected to "%s"' % status)
            return status_func

        for status in ArticleStatus.objects.all():
            name = 'mark_status_%i' % status.id
            actions[name] = (dynamic_status(name, status), name, _('Set status of selected to "%s"' % status))

        def dynamic_tag(name, tag):
            def status_func(self, request, queryset):
                for article in queryset.iterator():
                    log.debug('Dynamic tagging: applying Tag "%s" to Article "%s"' % (tag, article))
                    article.tags.add(tag)
                    article.save()

            status_func.__name__ = name
            status_func.short_description = _('Apply tag "%s" to selected articles' % tag)
            return status_func

        for tag in Tag.objects.all():
            name = 'apply_tag_%s' % tag.pk
            actions[name] = (dynamic_tag(name, tag), name, _('Apply Tag: %s' % (tag.slug,)))

        return actions

    actions = [mark_active, mark_inactive]

    def save_model(self, request, obj, form, change):
        """Set the article's author based on the logged in user and make sure at least one site is selected"""

        try:
            author = obj.author
        except User.DoesNotExist:
            obj.author = request.user

        obj.save()

        # this requires an Article object already
        obj.do_auto_tag('default')
        form.cleaned_data['tags'] += list(obj.tags.all())

    def queryset(self, request):
        """Limit the list of articles to article posted by this user unless they're a superuser"""

        if request.user.is_superuser:
            return self.model._default_manager.all()
        else:
            return self.model._default_manager.filter(author=request.user)

admin.site.register(Tag, TagAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(ArticleStatus, ArticleStatusAdmin)


########NEW FILE########
__FILENAME__ = decorators
import functools
import logging
import time

log = logging.getLogger('articles.decorators')

def logtime(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if func.__class__.__name__ == 'function':
            executing = '%s.%s' % (func.__module__, func.__name__)
        elif 'method' in func.__class__.__name__:
            executing = '%s.%s.%s' % (func.__module__, func.__class__.__name__, func.__name__)
        else:
            executing = str(func)

        log.debug('Logging execution time for %s with args: %s; kwargs: %s' % (executing, args, kwargs))

        start = time.time()
        res = func(*args, **kwargs)
        duration = time.time() - start

        log.debug('Called %s... duration: %s seconds' % (executing, duration))
        return res

    return wrapped

def once_per_instance(func):
    """Makes it so an instance method is called at most once before saving"""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        if not hasattr(self, '__run_once_methods'):
            self.__run_once_methods = []

        name = func.__name__
        if name in self.__run_once_methods:
            log.debug('Method %s has already been called for %s... not calling again.' % (name, self))
            return False

        res = func(self, *args, **kwargs)

        self.__run_once_methods.append(name)
        return res

    return wrapped


########NEW FILE########
__FILENAME__ = directives
"""
The Pygments reStructuredText directive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fragment is a Docutils_ 0.4 directive that renders source code
(to HTML only, currently) via Pygments.

To use it, adjust the options below and copy the code into a module
that you import on initialization.  The code then automatically
registers a ``sourcecode`` directive that you can use instead of
normal code blocks like this::

    .. sourcecode:: python

        My code goes here.

If you want to have different code styles, e.g. one with line numbers
and one without, add formatters with their names in the VARIANTS dict
below.  You can invoke them instead of the DEFAULT one by using a
directive option::

    .. sourcecode:: python
        :linenos:

        My code goes here.

Look at the `directive documentation`_ to get all the gory details.

.. _Docutils: http://docutils.sf.net/
.. _directive documentation:
    http://docutils.sourceforge.net/docs/howto/rst-directives.html

:copyright: 2007 by Georg Brandl.
:license: BSD, see LICENSE for more details.
"""

# Options
# ~~~~~~~

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False

try:
    from pygments.formatters import HtmlFormatter

    # The default formatter
    DEFAULT = HtmlFormatter(noclasses=INLINESTYLES)

    # Add name -> formatter pairs for every variant you want to use
    VARIANTS = {
        'linenos': HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
    }

    from docutils import nodes
    from docutils.parsers.rst import directives

    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer

    def pygments_directive(name, arguments, options, content, lineno,
                        content_offset, block_text, state, state_machine):
        try:
            lexer = get_lexer_by_name(arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = options and VARIANTS[options.keys()[0]] or DEFAULT
        parsed = highlight(u'\n'.join(content), lexer, formatter)
        parsed = '<div class="codeblock">%s</div>' % parsed
        return [nodes.raw('', parsed, format='html')]

    pygments_directive.arguments = (1, 0, 1)
    pygments_directive.content = 1
    pygments_directive.options = dict([(key, directives.flag) for key in VARIANTS])

    directives.register_directive('sourcecode', pygments_directive)

    # create an alias, so we can use it with rst2pdf... leave the other for
    # backwards compatibility
    directives.register_directive('code-block', pygments_directive)
except:
    # the user probably doesn't have pygments installed
    pass



########NEW FILE########
__FILENAME__ = feeds
from django.conf import settings
from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.feedgenerator import Atom1Feed

from articles.models import Article, Tag

# default to 24 hours for feed caching
FEED_TIMEOUT = getattr(settings, 'ARTICLE_FEED_TIMEOUT', 86400)

class SiteMixin(object):

    @property
    def site(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()

        return self._site

class LatestEntries(Feed, SiteMixin):

    def title(self):
        return "%s Articles" % (self.site.name,)

    def link(self):
        return reverse('articles_archive')

    def items(self):
        key = 'latest_articles'
        articles = cache.get(key)

        if articles is None:
            articles = list(Article.objects.live().order_by('-publish_date')[:15])
            cache.set(key, articles, FEED_TIMEOUT)

        return articles

    def item_author_name(self, item):
        return item.author.username

    def item_pubdate(self, item):
        return item.publish_date

class TagFeed(Feed, SiteMixin):

    def get_object(self, request, slug):
        try:
            return Tag.objects.get(slug__iexact=slug)
        except Tag.DoesNotExist:
            raise FeedDoesNotExist

    def title(self, obj):
        return "%s: Newest Articles Tagged '%s'" % (self.site.name, obj.name)

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return "Articles Tagged '%s'" % obj.name

    def items(self, obj):
        return self.item_set(obj)[:10]

    def item_set(self, obj):
        key = 'articles_for_%s' % obj.name
        articles = cache.get(key)

        if articles is None:
            articles = list(obj.article_set.live().order_by('-publish_date'))
            cache.set(key, articles, FEED_TIMEOUT)

        return articles

    def item_author_name(self, item):
        return item.author.username

    def item_author_link(self, item):
        return reverse('articles_by_author', args=[item.author.username])

    def item_pubdate(self, item):
        return item.publish_date

class LatestEntriesAtom(LatestEntries):
    feed_type = Atom1Feed

class TagFeedAtom(TagFeed):
    feed_type = Atom1Feed

########NEW FILE########
__FILENAME__ = forms
import logging

from django import forms
from django.utils.translation import ugettext_lazy as _
from models import Article, Tag

log = logging.getLogger('articles.forms')

def tag(name):
    """Returns a Tag object for the given name"""

    slug = Tag.clean_tag(name)

    log.debug('Looking for Tag with slug "%s"...' % (slug,))
    t, created = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
    log.debug('Found Tag %s. Name: %s Slug: %s Created: %s' % (t.pk, t.name, t.slug, created))

    if not t.name:
        t.name = name
        t.save()

    return t

class ArticleAdminForm(forms.ModelForm):
    tags = forms.CharField(initial='', required=False,
                           widget=forms.TextInput(attrs={'size': 100}),
                           help_text=_('Words that describe this article'))

    def __init__(self, *args, **kwargs):
        """Sets the list of tags to be a string"""

        instance = kwargs.get('instance', None)
        if instance:
            init = kwargs.get('initial', {})
            init['tags'] = ' '.join([t.name for t in instance.tags.all()])
            kwargs['initial'] = init

        super(ArticleAdminForm, self).__init__(*args, **kwargs)

    def clean_tags(self):
        """Turns the string of tags into a list"""

        tags = [tag(t.strip()) for t in self.cleaned_data['tags'].split() if len(t.strip())]

        log.debug('Tagging Article %s with: %s' % (self.cleaned_data['title'], tags))
        self.cleaned_data['tags'] = tags
        return self.cleaned_data['tags']

    def save(self, *args, **kwargs):
        """Remove any old tags that may have been set that we no longer need"""
        if self.instance.pk:
            self.instance.tags.clear()
        return super(ArticleAdminForm, self).save(*args, **kwargs)

    class Meta:
        model = Article

    class Media:
        css = {
            'all': ('articles/css/jquery.autocomplete.css',),
        }
        js = (
            'articles/js/jquery-1.4.1.min.js',
            'articles/js/jquery.bgiframe.min.js',
            'articles/js/jquery.autocomplete.pack.js',
            'articles/js/tag_autocomplete.js',
        )


########NEW FILE########
__FILENAME__ = listeners
import logging

from django.db.models import signals, Q

from decorators import logtime
from models import Article, Tag

log = logging.getLogger('articles.listeners')

@logtime
def apply_new_tag(sender, instance, created, using='default', **kwargs):
    """Applies new tags to existing articles that are marked for auto-tagging"""

    # attempt to find all articles that contain the new tag
    # TODO: make sure this is standard enough... seems that both MySQL and
    # PostgreSQL support it...
    tag = r'[[:<:]]%s[[:>:]]' % instance.name

    log.debug('Searching for auto-tag Articles using regex: %s' % (tag,))
    applicable_articles = Article.objects.filter(
        Q(auto_tag=True),
        Q(content__iregex=tag) |
        Q(title__iregex=tag) |
        Q(description__iregex=tag) |
        Q(keywords__iregex=tag)
    )

    log.debug('Found %s matches' % len(applicable_articles))
    for article in applicable_articles:
        log.debug('Applying Tag "%s" (%s) to Article "%s" (%s)' % (instance, instance.pk, article.title, article.pk))
        article.tags.add(instance)
        article.save()

signals.post_save.connect(apply_new_tag, sender=Tag)

########NEW FILE########
__FILENAME__ = check_for_articles_from_email
from base64 import b64decode
from datetime import datetime
from email.parser import FeedParser
from email.utils import parseaddr, parsedate
from optparse import make_option
import socket
import sys
import time

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _

from articles.models import Article, Attachment, MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE

MB_IMAP4 = 'IMAP4'
MB_POP3 = 'POP3'
ACCEPTABLE_TYPES = ('text/plain', 'text/html')

class MailboxHandler(object):

    def __init__(self, host, port, username, password, keyfile, certfile, ssl):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.certfile = certfile
        self.ssl = ssl
        self._handle = None

        if self.port is None:
            if self.ssl:
                self.port = self.secure_port
            else:
                self.port = self.unsecure_port

    @staticmethod
    def get_handle(protocol, *args, **kwargs):
        """Returns an instance of a MailboxHandler based on the protocol"""

        if protocol == MB_IMAP4:
            return IMAPHandler(*args, **kwargs)
        elif protocol == MB_POP3:
            return POPHandler(*args, **kwargs)

        return None

    @property
    def secure_port(self):
        return -1

    @property
    def unsecure_port(self):
        return -1

    @property
    def handle(self):
        if not self._handle:
            self._handle = self.connect()

        return self._handle

    def parse_email(self, message):
        """Parses each email message"""

        fp = FeedParser()
        fp.feed(message)
        return fp.close()

    def connect(self):
        raise NotImplemented

    def fetch(self):
        raise NotImplemented

    def delete_messages(self, id_list):
        """Deletes a list of messages from the server"""

        for msg_id in id_list:
            self.delete_message(msg_id)

    def delete_message(self, msg_id):
        raise NotImplemented

    def disconnect(self):
        raise NotImplemented

class IMAPHandler(MailboxHandler):

    @property
    def secure_port(self):
        return 993

    @property
    def unsecure_port(self):
        return 143

    def connect(self):
        """Connects to and authenticates with an IMAP4 mail server"""

        import imaplib

        M = None
        try:
            if (self.keyfile and self.certfile) or self.ssl:
                M = imaplib.IMAP4_SSL(self.host, self.port, self.keyfile, self.certfile)
            else:
                M = imaplib.IMAP4(self.host, self.port)

            M.login(self.username, self.password)
            M.select()
        except socket.error, err:
            raise
        else:
            return M

    def fetch(self):
        """Fetches email messages from an IMAP4 server"""

        messages = {}

        typ, data = self.handle.search(None, 'ALL')
        for num in data[0].split():
            typ, data = self.handle.fetch(num, '(RFC822)')
            messages[num] = self.parse_email(data[0][1])

        return messages

    def delete_message(self, msg_id):
        """Deletes a message from the server"""

        self.handle.store(msg_id, '+FLAGS', '\\Deleted')

    def disconnect(self):
        """Closes the IMAP4 handle"""

        self.handle.expunge()
        self.handle.close()
        self.handle.logout()

class POPHandler(MailboxHandler):

    @property
    def secure_port(self):
        return 995

    @property
    def unsecure_port(self):
        return 110

    def connect(self):
        """Connects to and authenticates with a POP3 mail server"""

        import poplib

        M = None
        try:
            if (self.keyfile and self.certfile) or self.ssl:
                M = poplib.POP3_SSL(self.host, self.port, self.keyfile, self.certfile)
            else:
                M = poplib.POP3(self.host, self.port)

            M.user(self.username)
            M.pass_(self.password)
        except socket.error, err:
            raise
        else:
            return M

    def fetch(self):
        """Fetches email messages from a POP3 server"""

        messages = {}

        num = len(self.handle.list()[1])
        for i in range(num):
            message = '\n'.join([msg for msg in self.handle.retr(i + 1)[1]])
            messages[num] = self.parse_email(message)

        return messages

    def delete_message(self, msg_id):
        """Deletes a message from the server"""

        self.handle.dele(msg_id)

    def disconnect(self):
        """Closes the POP3 handle"""

        self.handle.quit()

class Command(BaseCommand):
    help = "Checks special e-mail inboxes for emails that should be posted as articles"

    option_list = BaseCommand.option_list + (
        make_option('--protocol', dest='protocol', default=MB_IMAP4, help='Protocol to use to check for email'),
        make_option('--host', dest='host', default=None, help='IP or name of mail server'),
        make_option('--port', dest='port', default=None, help='Port used to connect to mail server'),
        make_option('--keyfile', dest='keyfile', default=None, help='File containing a PEM formatted private key for SSL connections'),
        make_option('--certfile', dest='certfile', default=None, help='File containing a certificate chain for SSL connections'),
        make_option('--username', dest='username', default=None, help='Username to authenticate with mail server'),
        make_option('--password', dest='password', default=None, help='Password to authenticate with mail server'),
        make_option('--ssl', action='store_true', dest='ssl', default=False, help='Use to specify that the connection must be made using SSL'),
    )

    def log(self, message, level=2):
        if self.verbosity >= level:
            print message

    def handle(self, *args, **options):
        """Main entry point for the command"""

        # retrieve configuration options--give precedence to CLI parameters
        self.config = getattr(settings, 'ARTICLES_FROM_EMAIL', {})
        s = lambda k, d: self.config.get(k, d)

        protocol = options['protocol'] or s('protocol', MB_IMAP4)
        host = options['host'] or s('host', 'mail.yourhost.com')
        port = options['port'] or s('port', None)
        keyfile = options['keyfile'] or s('keyfile', None)
        certfile = options['certfile'] or s('certfile', None)
        username = options['username'] or s('user', None)
        password = options['password'] or s('password', None)
        ssl = options['ssl'] or s('ssl', False)

        self.verbosity = int(options.get('verbosity', 1))

        handle = None
        try:
            self.log('Creating mailbox handle')
            handle = MailboxHandler.get_handle(protocol, host, port, username, password, keyfile, certfile, ssl)

            self.log('Fetching messages')
            messages = handle.fetch()

            if len(messages):
                self.log('Creating articles')
                created = self.create_articles(messages)

                if len(created):
                    self.log('Deleting consumed messages')
                    handle.delete_messages(created)
                else:
                    self.log('No articles created')
            else:
                self.log('No messages fetched')
        except socket.error:
            self.log('Failed to communicate with mail server.  Please verify your settings.', 0)
        finally:
            if handle:
                try:
                    handle.disconnect()
                    self.log('Disconnected.')
                except socket.error:
                    # probably means we couldn't connect to begin with
                    pass

    def get_email_content(self, email):
        """Attempts to extract an email's content"""

        if email.is_multipart():
            self.log('Extracting email contents from multipart message')

            magic_type = 'multipart/alternative'
            payload_types = dict((p.get_content_type(), i) for i, p in enumerate(email.get_payload()))
            if magic_type in payload_types.keys():
                self.log('Found magic content type: %s' % magic_type)
                index = payload_types[magic_type]
                payload = email.get_payload()[index].get_payload()
            else:
                payload = email.get_payload()

            for pl in payload:
                if pl.get_filename() is not None:
                    # it's an attached file
                    continue

                if pl.get_content_type() in ACCEPTABLE_TYPES:
                    return pl.get_payload()
        else:
            return email.get_payload()

        return None

    def create_articles(self, emails):
        """Attempts to post new articles based on parsed email messages"""

        created = []
        site = Site.objects.get_current()

        ack = self.config.get('acknowledge', False)
        autopost = self.config.get('autopost', False)

        # make sure we have a valid default markup
        markup = self.config.get('markup', MARKUP_HTML)
        if markup not in (MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE):
            markup = MARKUP_HTML

        for num, email in emails.iteritems():

            name, sender = parseaddr(email['From'])

            try:
                author = User.objects.get(email=sender, is_active=True)
            except User.DoesNotExist:
                # unauthorized sender
                self.log('Not processing message from unauthorized sender.', 0)
                continue

            # get the attributes for the article
            title = email.get('Subject', '--- article from email ---')

            content = self.get_email_content(email)
            try:
                # try to grab the timestamp from the email message
                publish_date = datetime.fromtimestamp(time.mktime(parsedate(email['Date'])))
            except StandardError, err:
                self.log("An error occurred when I tried to convert the email's timestamp into a datetime object: %s" % (err,))
                publish_date = datetime.now()

            # post the article
            article = Article(
                author=author,
                title=title,
                content=content,
                markup=markup,
                publish_date=publish_date,
                is_active=autopost,
            )

            try:
                article.save()
                self.log('Article created.')
            except StandardError, err:
                # log it and move on to the next message
                self.log('Error creating article: %s' % (err,), 0)
                continue
            else:

                # handle attachments
                if email.is_multipart():
                    files = [pl for pl in email.get_payload() if pl.get_filename() is not None]
                    for att in files:
                        obj = Attachment(
                            article=article,
                            caption=att.get_filename(),
                        )
                        obj.attachment.save(obj.caption, ChunkyString(att.get_payload()))
                        obj.save()

                created.append(num)

            if ack:
                # notify the user when the article is posted
                subject = u'%s: %s' % (_("Article Posted"), title)
                message = _("""Your email (%(title)s) has been posted as an article on %(site_name)s.

    http://%(domain)s%(article_url)s""") % {
                    'title': title,
                    'site_name': site.name,
                    'domain': site.domain,
                    'article_url': article.get_absolute_url(),
                }

                self.log('Sending acknowledgment email to %s' % (author.email,))
                author.email_user(subject, message)

        return created

class ChunkyString(str):
    """Makes is possible to easily chunk attachments"""

    def chunks(self):
        i = 0
        decoded = b64decode(self)
        while True:
            l = i
            i += 1024
            yield decoded[l:i]

            if i > len(decoded):
                raise StopIteration


########NEW FILE########
__FILENAME__ = convert_categories_to_tags
from django.core.management.base import NoArgsCommand
from articles.models import Article, Tag

class Command(NoArgsCommand):
    help = """Converts our old categories into tags"""

    def handle_noargs(self, **opts):
        from django.db import connection

        c = connection.cursor()

        for article in Article.objects.all():
            c.execute("""SELECT c.slug
FROM articles_article_categories aac
JOIN articles_category c
ON aac.category_id = c.id
WHERE aac.article_id=%s""", (article.id,))

            names = [row[0] for row in c.fetchall()]
            tags = [Tag.objects.get_or_create(name=t)[0] for t in names]
            article.tags = tags
            article.save()


########NEW FILE########
__FILENAME__ = convert_comments_to_disqus
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.management.base import NoArgsCommand
from articles.models import Article
import simplejson as json
import re
import string
import sys
import urllib
import urllib2

NONPRINTABLE_RE = re.compile('[^%s]' % string.printable)

class Command(NoArgsCommand):
    help = """Imports any comments from django.contrib.comments into Disqus."""
    _forum_api_key = {}

    def handle_noargs(self, **opts):
        if hasattr(settings, 'DISQUS_USER_API_KEY'):
            self.forum_id = self.determine_forum()
            #print self.get_value_from_api('get_thread_list', {'forum_id': self.forum_id, 'limit': 1000})
            self.import_comments(self.forum_id)
        else:
            sys.exit('Please specify your DISQUS_USER_API_KEY in settings.py')

    def get_value_from_api(self, url, args={}, method='GET'):
        params = {
            'user_api_key': settings.DISQUS_USER_API_KEY,
            'api_version': '1.1',
        }
        params.update(args)

        # clean up the values
        for key, val in params.items():
            if isinstance(val, (str, unicode)):
                params[key] = NONPRINTABLE_RE.sub('', val)

        data = urllib.urlencode(params)
        additional = ''

        if method != 'POST':
            additional = '?%s' % data
            data = None

        url = 'http://disqus.com/api/%s/%s' % (url, additional)
        try:
            handle = urllib2.urlopen(url, data)
        except urllib2.HTTPError, err:
            print 'Failed to %s %s with args %s' % (method, url, args)
            return None
        else:
            json_obj = json.loads(handle.read())['message']
            handle.close()

            return json_obj

    def determine_forum(self):
        forums = self.get_value_from_api('get_forum_list')

        if len(forums) == 0:
            sys.exit('You have no forums on Disqus!')
        elif len(forums) == 1:
            forum_id = forums[0]['id']
        else:
            possible_ids = tuple(forum['id'] for forum in forums)
            forum_id = None
            while forum_id not in possible_ids:
                if forum_id is not None:
                    print 'Invalid forum ID.  Please try again.'

                print 'You have the following forums on Disqus:\n'

                for forum in forums:
                    print '\t%s. %s' % (forum['id'], forum['name'])

                forum_id = raw_input('\nInto which forum do you want to import your existing comments? ')

        return forum_id

    @property
    def forum_api_key(self):
        if not self._forum_api_key.get(self.forum_id, None):
            self._forum_api_key[self.forum_id] = self.get_value_from_api('get_forum_api_key', {'forum_id': self.forum_id})
        return self._forum_api_key[self.forum_id]

    def import_comments(self, forum_id):
        print 'Importing into forum %s' % self.forum_id

        article_ct = ContentType.objects.get_for_model(Article)
        for comment in Comment.objects.filter(content_type=article_ct):
            article = comment.content_object
            thread_obj = self.get_value_from_api('thread_by_identifier', {'identifier': article.id, 'title': article.title, 'forum_api_key': self.forum_api_key}, method='POST')

            thread = thread_obj['thread']
            if thread_obj['created']:
                # set the URL for this thread for good measure
                self.get_value_from_api('update_thread', {
                    'forum_api_key': self.forum_api_key,
                    'thread_id': thread['id'],
                    'title': article.title,
                    'url': 'http://%s%s' % (Site.objects.get_current().domain, article.get_absolute_url()),
                }, method='POST')
                print 'Created new thread for %s' % article.title

            # create the comment on disqus
            comment_obj = self.get_value_from_api('create_post', {
                'thread_id': thread['id'],
                'message': comment.comment,
                'author_name': comment.user_name,
                'author_email': comment.user_email,
                'forum_api_key': self.forum_api_key,
                'created_at': comment.submit_date.strftime('%Y-%m-%dT%H:%M'),
                'ip_address': comment.ip_address,
                'author_url': comment.user_url,
                'state': self.get_state(comment)
            }, method='POST')

            print 'Imported comment for %s by %s on %s' % (article, comment.user_name, comment.submit_date)

    def get_state(self, comment):
        """Determines a comment's state on Disqus based on its properties in Django"""

        if comment.is_public and not comment.is_removed:
            return 'approved'
        elif comment.is_public and comment.is_removed:
            return 'killed'
        elif not comment.is_public and not comment.is_removed:
            return 'unapproved'
        else:
            return 'spam'


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Tag'
        db.create_table('articles_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
        ))
        db.send_create_signal('articles', ['Tag'])

        # Adding model 'ArticleStatus'
        db.create_table('articles_articlestatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('ordering', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('is_live', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('articles', ['ArticleStatus'])

        # Adding model 'Article'
        db.create_table('articles_article', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['articles.ArticleStatus'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('keywords', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('markup', self.gf('django.db.models.fields.CharField')(default='h', max_length=1)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('rendered_content', self.gf('django.db.models.fields.TextField')()),
            ('publish_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('expiration_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('login_required', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('use_addthis_button', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('addthis_use_author', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('addthis_username', self.gf('django.db.models.fields.CharField')(default=None, max_length=50, blank=True)),
        ))
        db.send_create_signal('articles', ['Article'])

        # Adding M2M table for field sites on 'Article'
        db.create_table('articles_article_sites', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm['articles.article'], null=False)),
            ('site', models.ForeignKey(orm['sites.site'], null=False))
        ))
        db.create_unique('articles_article_sites', ['article_id', 'site_id'])

        # Adding M2M table for field tags on 'Article'
        db.create_table('articles_article_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm['articles.article'], null=False)),
            ('tag', models.ForeignKey(orm['articles.tag'], null=False))
        ))
        db.create_unique('articles_article_tags', ['article_id', 'tag_id'])

        # Adding M2M table for field followup_for on 'Article'
        db.create_table('articles_article_followup_for', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_article', models.ForeignKey(orm['articles.article'], null=False)),
            ('to_article', models.ForeignKey(orm['articles.article'], null=False))
        ))
        db.create_unique('articles_article_followup_for', ['from_article_id', 'to_article_id'])

        # Adding M2M table for field related_articles on 'Article'
        db.create_table('articles_article_related_articles', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_article', models.ForeignKey(orm['articles.article'], null=False)),
            ('to_article', models.ForeignKey(orm['articles.article'], null=False))
        ))
        db.create_unique('articles_article_related_articles', ['from_article_id', 'to_article_id'])

        # Adding model 'Attachment'
        db.create_table('articles_attachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['articles.Article'])),
            ('attachment', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('caption', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('articles', ['Attachment'])


    def backwards(self, orm):
        
        # Deleting model 'Tag'
        db.delete_table('articles_tag')

        # Deleting model 'ArticleStatus'
        db.delete_table('articles_articlestatus')

        # Deleting model 'Article'
        db.delete_table('articles_article')

        # Removing M2M table for field sites on 'Article'
        db.delete_table('articles_article_sites')

        # Removing M2M table for field tags on 'Article'
        db.delete_table('articles_article_tags')

        # Removing M2M table for field followup_for on 'Article'
        db.delete_table('articles_article_followup_for')

        # Removing M2M table for field related_articles on 'Article'
        db.delete_table('articles_article_related_articles')

        # Deleting model 'Attachment'
        db.delete_table('articles_attachment')


    models = {
        'articles.article': {
            'Meta': {'ordering': "('-publish_date', 'title')", 'object_name': 'Article'},
            'addthis_use_author': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'addthis_username': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followup_for': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followups'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'h'", 'max_length': '1'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related_articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_articles_rel_+'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'rendered_content': ('django.db.models.fields.TextField', [], {}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['articles.ArticleStatus']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['articles.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_addthis_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'articles.articlestatus': {
            'Meta': {'ordering': "('ordering', 'name')", 'object_name': 'ArticleStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'articles.attachment': {
            'Meta': {'ordering': "('-article', 'id')", 'object_name': 'Attachment'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['articles.Article']"}),
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'articles.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['articles']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_article_auto_tag
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Article.auto_tag'
        db.add_column('articles_article', 'auto_tag', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Article.auto_tag'
        db.delete_column('articles_article', 'auto_tag')


    models = {
        'articles.article': {
            'Meta': {'ordering': "('-publish_date', 'title')", 'object_name': 'Article'},
            'addthis_use_author': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'addthis_username': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'auto_tag': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followup_for': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followups'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'h'", 'max_length': '1'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related_articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_articles_rel_+'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'rendered_content': ('django.db.models.fields.TextField', [], {}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['articles.ArticleStatus']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['articles.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_addthis_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'articles.articlestatus': {
            'Meta': {'ordering': "('ordering', 'name')", 'object_name': 'ArticleStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'articles.attachment': {
            'Meta': {'ordering': "('-article', 'id')", 'object_name': 'Attachment'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['articles.Article']"}),
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'articles.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['articles']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_tag_slug
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Tag.slug'
        db.add_column('articles_tag', 'slug', self.gf('django.db.models.fields.CharField')(default='', max_length=64, null=True, blank=True), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'Tag.slug'
        db.delete_column('articles_tag', 'slug')


    models = {
        'articles.article': {
            'Meta': {'ordering': "('-publish_date', 'title')", 'object_name': 'Article'},
            'addthis_use_author': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'addthis_username': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'auto_tag': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followup_for': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followups'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'h'", 'max_length': '1'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related_articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_articles_rel_+'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'rendered_content': ('django.db.models.fields.TextField', [], {}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['articles.ArticleStatus']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['articles.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_addthis_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'articles.articlestatus': {
            'Meta': {'ordering': "('ordering', 'name')", 'object_name': 'ArticleStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'articles.attachment': {
            'Meta': {'ordering': "('-article', 'id')", 'object_name': 'Attachment'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['articles.Article']"}),
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'articles.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['articles']

########NEW FILE########
__FILENAME__ = 0004_set_tag_slugs
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    no_dry_run = True

    def forwards(self, orm):
        """Finds all tags with an empty slug and populates it"""

        for tag in orm.Tag.objects.filter(slug__isnull=True):
            tag.save()

        for tag in orm.Tag.objects.filter(slug=''):
            tag.save()

    def backwards(self, orm):
        """Not important this time"""

        pass


    models = {
        'articles.article': {
            'Meta': {'ordering': "('-publish_date', 'title')", 'object_name': 'Article'},
            'addthis_use_author': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'addthis_username': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'auto_tag': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followup_for': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followups'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'h'", 'max_length': '1'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related_articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_articles_rel_+'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'rendered_content': ('django.db.models.fields.TextField', [], {}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['articles.ArticleStatus']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['articles.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_addthis_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'articles.articlestatus': {
            'Meta': {'ordering': "('ordering', 'name')", 'object_name': 'ArticleStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'articles.attachment': {
            'Meta': {'ordering': "('-article', 'id')", 'object_name': 'Attachment'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['articles.Article']"}),
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'articles.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['articles']

########NEW FILE########
__FILENAME__ = 0005_make_slugs_unique
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        """Adds the unique constraint on tag slugs"""

        db.alter_column('articles_tag', 'slug', self.gf('django.db.models.fields.CharField')(default='', unique=True, max_length=64, null=True, blank=True))


    def backwards(self, orm):
        """Drops the unique constraint"""

        db.alter_column('articles_tag', 'slug', self.gf('django.db.models.fields.CharField')(default='', unique=False, max_length=64, null=True, blank=True))


    models = {
        'articles.article': {
            'Meta': {'ordering': "('-publish_date', 'title')", 'object_name': 'Article'},
            'addthis_use_author': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'addthis_username': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'auto_tag': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followup_for': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followups'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'h'", 'max_length': '1'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related_articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_articles_rel_+'", 'blank': 'True', 'to': "orm['articles.Article']"}),
            'rendered_content': ('django.db.models.fields.TextField', [], {}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['articles.ArticleStatus']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['articles.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_addthis_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'articles.articlestatus': {
            'Meta': {'ordering': "('ordering', 'name')", 'object_name': 'ArticleStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_live': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'articles.attachment': {
            'Meta': {'ordering': "('-article', 'id')", 'object_name': 'Attachment'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['articles.Article']"}),
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'articles.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['articles']

########NEW FILE########
__FILENAME__ = models
from hashlib import sha1
from datetime import datetime
import logging
import mimetypes
import re
import urllib

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.markup.templatetags import markup
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.conf import settings
from django.template.defaultfilters import slugify, striptags
from django.utils.translation import ugettext_lazy as _
from django.utils.text import truncate_html_words

from decorators import logtime, once_per_instance

WORD_LIMIT = getattr(settings, 'ARTICLES_TEASER_LIMIT', 75)
AUTO_TAG = getattr(settings, 'ARTICLES_AUTO_TAG', True)
DEFAULT_DB = getattr(settings, 'ARTICLES_DEFAULT_DB', 'default')
LOOKUP_LINK_TITLE = getattr(settings, 'ARTICLES_LOOKUP_LINK_TITLE', True)

MARKUP_HTML = 'h'
MARKUP_MARKDOWN = 'm'
MARKUP_REST = 'r'
MARKUP_TEXTILE = 't'
MARKUP_OPTIONS = getattr(settings, 'ARTICLE_MARKUP_OPTIONS', (
        (MARKUP_HTML, _('HTML/Plain Text')),
        (MARKUP_MARKDOWN, _('Markdown')),
        (MARKUP_REST, _('ReStructured Text')),
        (MARKUP_TEXTILE, _('Textile'))
    ))
MARKUP_DEFAULT = getattr(settings, 'ARTICLE_MARKUP_DEFAULT', MARKUP_HTML)

USE_ADDTHIS_BUTTON = getattr(settings, 'USE_ADDTHIS_BUTTON', True)
ADDTHIS_USE_AUTHOR = getattr(settings, 'ADDTHIS_USE_AUTHOR', True)
DEFAULT_ADDTHIS_USER = getattr(settings, 'DEFAULT_ADDTHIS_USER', None)

# regex used to find links in an article
LINK_RE = re.compile('<a.*?href="(.*?)".*?>(.*?)</a>', re.I|re.M)
TITLE_RE = re.compile('<title.*?>(.*?)</title>', re.I|re.M)
TAG_RE = re.compile('[^a-z0-9\-_\+\:\.]?', re.I)

log = logging.getLogger('articles.models')

def get_name(user):
    """
    Provides a way to fall back to a user's username if their full name has not
    been entered.
    """

    key = 'username_for_%s' % user.id

    log.debug('Looking for "%s" in cache (%s)' % (key, user))
    name = cache.get(key)
    if not name:
        log.debug('Name not found')

        if len(user.get_full_name().strip()):
            log.debug('Using full name')
            name = user.get_full_name()
        else:
            log.debug('Using username')
            name = user.username

        log.debug('Caching %s as "%s" for a while' % (key, name))
        cache.set(key, name, 86400)

    return name
User.get_name = get_name

class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __unicode__(self):
        return self.name

    @staticmethod
    def clean_tag(name):
        """Replace spaces with dashes, in case someone adds such a tag manually"""

        name = name.replace(' ', '-').encode('ascii', 'ignore')
        name = TAG_RE.sub('', name)
        clean = name.lower().strip(", ")

        log.debug('Cleaned tag "%s" to "%s"' % (name, clean))
        return clean

    def save(self, *args, **kwargs):
        """Cleans up any characters I don't want in a URL"""

        log.debug('Ensuring that tag "%s" has a slug' % (self,))
        self.slug = Tag.clean_tag(self.name)
        super(Tag, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('articles_display_tag', (self.cleaned,))

    @property
    def cleaned(self):
        """Returns the clean version of the tag"""

        return self.slug or Tag.clean_tag(self.name)

    @property
    def rss_name(self):
        return self.cleaned

    class Meta:
        ordering = ('name',)

class ArticleStatusManager(models.Manager):

    def default(self):
        default = self.all()[:1]

        if len(default) == 0:
            return None
        else:
            return default[0]

class ArticleStatus(models.Model):
    name = models.CharField(max_length=50)
    ordering = models.IntegerField(default=0)
    is_live = models.BooleanField(default=False, blank=True)

    objects = ArticleStatusManager()

    class Meta:
        ordering = ('ordering', 'name')
        verbose_name_plural = _('Article statuses')

    def __unicode__(self):
        if self.is_live:
            return u'%s (live)' % self.name
        else:
            return self.name

class ArticleManager(models.Manager):

    def active(self):
        """
        Retrieves all active articles which have been published and have not
        yet expired.
        """
        now = datetime.now()
        return self.get_query_set().filter(
                Q(expiration_date__isnull=True) |
                Q(expiration_date__gte=now),
                publish_date__lte=now,
                is_active=True)

    def live(self, user=None):
        """Retrieves all live articles"""

        qs = self.active()

        if user is not None and user.is_superuser:
            # superusers get to see all articles
            return qs
        else:
            # only show live articles to regular users
            return qs.filter(status__is_live=True)

MARKUP_HELP = _("""Select the type of markup you are using in this article.
<ul>
<li><a href="http://daringfireball.net/projects/markdown/basics" target="_blank">Markdown Guide</a></li>
<li><a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html" target="_blank">ReStructured Text Guide</a></li>
<li><a href="http://thresholdstate.com/articles/4312/the-textile-reference-manual" target="_blank">Textile Guide</a></li>
</ul>""")

class Article(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique_for_year='publish_date')
    status = models.ForeignKey(ArticleStatus, default=ArticleStatus.objects.default)
    author = models.ForeignKey(User)
    sites = models.ManyToManyField(Site, blank=True)

    keywords = models.TextField(blank=True, help_text=_("If omitted, the keywords will be the same as the article tags."))
    description = models.TextField(blank=True, help_text=_("If omitted, the description will be determined by the first bit of the article's content."))

    markup = models.CharField(max_length=1, choices=MARKUP_OPTIONS, default=MARKUP_DEFAULT, help_text=MARKUP_HELP)
    content = models.TextField()
    rendered_content = models.TextField()

    tags = models.ManyToManyField(Tag, help_text=_('Tags that describe this article'), blank=True)
    auto_tag = models.BooleanField(default=AUTO_TAG, blank=True, help_text=_('Check this if you want to automatically assign any existing tags to this article based on its content.'))
    followup_for = models.ManyToManyField('self', symmetrical=False, blank=True, help_text=_('Select any other articles that this article follows up on.'), related_name='followups')
    related_articles = models.ManyToManyField('self', blank=True)

    publish_date = models.DateTimeField(default=datetime.now, help_text=_('The date and time this article shall appear online.'))
    expiration_date = models.DateTimeField(blank=True, null=True, help_text=_('Leave blank if the article does not expire.'))

    is_active = models.BooleanField(default=True, blank=True)
    login_required = models.BooleanField(blank=True, help_text=_('Enable this if users must login before they can read this article.'))

    use_addthis_button = models.BooleanField(_('Show AddThis button'), blank=True, default=USE_ADDTHIS_BUTTON, help_text=_('Check this to show an AddThis bookmark button when viewing an article.'))
    addthis_use_author = models.BooleanField(_("Use article author's username"), blank=True, default=ADDTHIS_USE_AUTHOR, help_text=_("Check this if you want to use the article author's username for the AddThis button.  Respected only if the username field is left empty."))
    addthis_username = models.CharField(_('AddThis Username'), max_length=50, blank=True, default=DEFAULT_ADDTHIS_USER, help_text=_('The AddThis username to use for the button.'))

    objects = ArticleManager()

    def __init__(self, *args, **kwargs):
        """Makes sure that we have some rendered content to use"""

        super(Article, self).__init__(*args, **kwargs)

        self._next = None
        self._previous = None
        self._teaser = None

        if self.id:
            # mark the article as inactive if it's expired and still active
            if self.expiration_date and self.expiration_date <= datetime.now() and self.is_active:
                self.is_active = False
                self.save()

            if not self.rendered_content or not len(self.rendered_content.strip()):
                self.save()

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Renders the article using the appropriate markup language."""

        using = kwargs.get('using', DEFAULT_DB)

        self.do_render_markup()
        self.do_addthis_button()
        self.do_meta_description()
        self.do_unique_slug(using)

        super(Article, self).save(*args, **kwargs)

        # do some things that require an ID first
        requires_save = self.do_auto_tag(using)
        requires_save |= self.do_tags_to_keywords()
        requires_save |= self.do_default_site(using)

        if requires_save:
            # bypass the other processing
            super(Article, self).save()

    def do_render_markup(self):
        """Turns any markup into HTML"""

        original = self.rendered_content
        if self.markup == MARKUP_MARKDOWN:
            self.rendered_content = markup.markdown(self.content)
        elif self.markup == MARKUP_REST:
            self.rendered_content = markup.restructuredtext(self.content)
        elif self.markup == MARKUP_TEXTILE:
            self.rendered_content = markup.textile(self.content)
        else:
            self.rendered_content = self.content

        return (self.rendered_content != original)

    def do_addthis_button(self):
        """Sets the AddThis username for this post"""

        # if the author wishes to have an "AddThis" button on this article,
        # make sure we have a username to go along with it.
        if self.use_addthis_button and self.addthis_use_author and not self.addthis_username:
            self.addthis_username = self.author.username
            return True

        return False

    def do_unique_slug(self, using=DEFAULT_DB):
        """
        Ensures that the slug is always unique for the year this article was
        posted
        """

        if not self.id:
            # make sure we have a slug first
            if not len(self.slug.strip()):
                self.slug = slugify(self.title)

            self.slug = self.get_unique_slug(self.slug, using)
            return True

        return False

    def do_tags_to_keywords(self):
        """
        If meta keywords is empty, sets them using the article tags.

        Returns True if an additional save is required, False otherwise.
        """

        if len(self.keywords.strip()) == 0:
            self.keywords = ', '.join([t.name for t in self.tags.all()])
            return True

        return False

    def do_meta_description(self):
        """
        If meta description is empty, sets it to the article's teaser.

        Returns True if an additional save is required, False otherwise.
        """

        if len(self.description.strip()) == 0:
            self.description = self.teaser
            return True

        return False

    @logtime
    @once_per_instance
    def do_auto_tag(self, using=DEFAULT_DB):
        """
        Performs the auto-tagging work if necessary.

        Returns True if an additional save is required, False otherwise.
        """

        if not self.auto_tag:
            log.debug('Article "%s" (ID: %s) is not marked for auto-tagging. Skipping.' % (self.title, self.pk))
            return False

        # don't clobber any existing tags!
        existing_ids = [t.id for t in self.tags.all()]
        log.debug('Article %s already has these tags: %s' % (self.pk, existing_ids))

        unused = Tag.objects.all()
        if hasattr(unused, 'using'):
            unused = unused.using(using)
        unused = unused.exclude(id__in=existing_ids)

        found = False
        to_search = (self.content, self.title, self.description, self.keywords)
        for tag in unused:
            regex = re.compile(r'\b%s\b' % tag.name, re.I)
            if any(regex.search(text) for text in to_search):
                log.debug('Applying Tag "%s" (%s) to Article %s' % (tag, tag.pk, self.pk))
                self.tags.add(tag)
                found = True

        return found

    def do_default_site(self, using=DEFAULT_DB):
        """
        If no site was selected, selects the site used to create the article
        as the default site.

        Returns True if an additional save is required, False otherwise.
        """

        if not len(self.sites.all()):
            sites = Site.objects.all()
            if hasattr(sites, 'using'):
                sites = sites.using(using)
            self.sites.add(sites.get(pk=settings.SITE_ID))
            return True

        return False

    def get_unique_slug(self, slug, using=DEFAULT_DB):
        """Iterates until a unique slug is found"""

        # we need a publish date before we can do anything meaningful
        if type(self.publish_date) is not datetime:
            return slug

        orig_slug = slug
        year = self.publish_date.year
        counter = 1

        while True:
            not_unique = Article.objects.all()
            if hasattr(not_unique, 'using'):
                not_unique = not_unique.using(using)
            not_unique = not_unique.filter(publish_date__year=year, slug=slug)

            if len(not_unique) == 0:
                return slug

            slug = '%s-%s' % (orig_slug, counter)
            counter += 1

    def _get_article_links(self):
        """
        Find all links in this article.  When a link is encountered in the
        article text, this will attempt to discover the title of the page it
        links to.  If there is a problem with the target page, or there is no
        title (ie it's an image or other binary file), the text of the link is
        used as the title.  Once a title is determined, it is cached for a week
        before it will be requested again.
        """

        links = []

        # find all links in the article
        log.debug('Locating links in article: %s' % (self,))
        for link in LINK_RE.finditer(self.rendered_content):
            url = link.group(1)
            log.debug('Do we have a title for "%s"?' % (url,))
            key = 'href_title_' + sha1(url).hexdigest()

            # look in the cache for the link target's title
            title = cache.get(key)
            if title is None:
                log.debug('Nope... Getting it and caching it.')
                title = link.group(2)

                if LOOKUP_LINK_TITLE:
                    try:
                        log.debug('Looking up title for URL: %s' % (url,))
                        # open the URL
                        c = urllib.urlopen(url)
                        html = c.read()
                        c.close()

                        # try to determine the title of the target
                        title_m = TITLE_RE.search(html)
                        if title_m:
                            title = title_m.group(1)
                            log.debug('Found title: %s' % (title,))
                    except:
                        # if anything goes wrong (ie IOError), use the link's text
                        log.warn('Failed to retrieve the title for "%s"; using link text "%s"' % (url, title))

                # cache the page title for a week
                log.debug('Using "%s" as title for "%s"' % (title, url))
                cache.set(key, title, 604800)

            # add it to the list of links and titles
            if url not in (l[0] for l in links):
                links.append((url, title))

        return tuple(links)
    links = property(_get_article_links)

    def _get_word_count(self):
        """Stupid word counter for an article."""

        return len(striptags(self.rendered_content).split(' '))
    word_count = property(_get_word_count)

    @models.permalink
    def get_absolute_url(self):
        return ('articles_display_article', (self.publish_date.year, self.slug))

    def _get_teaser(self):
        """
        Retrieve some part of the article or the article's description.
        """
        if not self._teaser:
            if len(self.description.strip()):
                self._teaser = self.description
            else:
                self._teaser = truncate_html_words(self.rendered_content, WORD_LIMIT)

        return self._teaser
    teaser = property(_get_teaser)

    def get_next_article(self):
        """Determines the next live article"""

        if not self._next:
            try:
                qs = Article.objects.live().exclude(id__exact=self.id)
                article = qs.filter(publish_date__gte=self.publish_date).order_by('publish_date')[0]
            except (Article.DoesNotExist, IndexError):
                article = None
            self._next = article

        return self._next

    def get_previous_article(self):
        """Determines the previous live article"""

        if not self._previous:
            try:
                qs = Article.objects.live().exclude(id__exact=self.id)
                article = qs.filter(publish_date__lte=self.publish_date).order_by('-publish_date')[0]
            except (Article.DoesNotExist, IndexError):
                article = None
            self._previous = article

        return self._previous

    class Meta:
        ordering = ('-publish_date', 'title')
        get_latest_by = 'publish_date'

class Attachment(models.Model):
    upload_to = lambda inst, fn: 'attach/%s/%s/%s' % (datetime.now().year, inst.article.slug, fn)

    article = models.ForeignKey(Article, related_name='attachments')
    attachment = models.FileField(upload_to=upload_to)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('-article', 'id')

    def __unicode__(self):
        return u'%s: %s' % (self.article, self.caption)

    @property
    def filename(self):
        return self.attachment.name.split('/')[-1]

    @property
    def content_type_class(self):
        mt = mimetypes.guess_type(self.attachment.path)[0]
        if mt:
            content_type = mt.replace('/', '_')
        else:
            # assume everything else is text/plain
            content_type = 'text_plain'

        return content_type


########NEW FILE########
__FILENAME__ = article_tags
from django import template
from django.core.cache import cache
from django.core.urlresolvers import resolve, reverse, Resolver404
from django.db.models import Count
from articles.models import Article, Tag
from datetime import datetime
import math

register = template.Library()

class GetCategoriesNode(template.Node):
    """
    Retrieves a list of live article tags and places it into the context
    """
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        tags = Tag.objects.all()
        context[self.varname] = tags
        return ''

def get_article_tags(parser, token):
    """
    Retrieves a list of live article tags and places it into the context
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 3 and args[1] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('get_article_tags syntax: {% get_article_tags as varname %}')

    return GetCategoriesNode(args[2])

class GetArticlesNode(template.Node):
    """
    Retrieves a set of article objects.

    Usage::

        {% get_articles 5 as varname %}

        {% get_articles 5 as varname asc %}

        {% get_articles 1 to 5 as varname %}

        {% get_articles 1 to 5 as varname asc %}
    """
    def __init__(self, varname, count=None, start=None, end=None, order='desc'):
        self.count = count
        self.start = start
        self.end = end
        self.order = order
        self.varname = varname.strip()

    def render(self, context):
        # determine the order to sort the articles
        if self.order and self.order.lower() == 'desc':
            order = '-publish_date'
        else:
            order = 'publish_date'

        user = context.get('user', None)

        # get the live articles in the appropriate order
        articles = Article.objects.live(user=user).order_by(order).select_related()

        if self.count:
            # if we have a number of articles to retrieve, pull the first of them
            articles = articles[:int(self.count)]
        else:
            # get a range of articles
            articles = articles[(int(self.start) - 1):int(self.end)]

        # don't send back a list when we really don't need/want one
        if len(articles) == 1 and not self.start and int(self.count) == 1:
            articles = articles[0]

        # put the article(s) into the context
        context[self.varname] = articles
        return ''

def get_articles(parser, token):
    """
    Retrieves a list of Article objects for use in a template.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc in (4,6) or (argc in (5,7) and args[-1].lower() in ('desc', 'asc'))
    except AssertionError:
        raise template.TemplateSyntaxError('Invalid get_articles syntax.')

    # determine what parameters to use
    order = 'desc'
    count = start = end = varname = None
    if argc == 4: t, count, a, varname = args
    elif argc == 5: t, count, a, varname, order = args
    elif argc == 6: t, start, t, end, a, varname = args
    elif argc == 7: t, start, t, end, a, varname, order = args

    return GetArticlesNode(count=count,
                           start=start,
                           end=end,
                           order=order,
                           varname=varname)

class GetArticleArchivesNode(template.Node):
    """
    Retrieves a list of years and months in which articles have been posted.
    """
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        cache_key = 'article_archive_list'
        dt_archives = cache.get(cache_key)
        if dt_archives is None:
            archives = {}
            user = context.get('user', None)

            # iterate over all live articles
            for article in Article.objects.live(user=user).select_related():
                pub = article.publish_date

                # see if we already have an article in this year
                if not archives.has_key(pub.year):
                    # if not, initialize a dict for the year
                    archives[pub.year] = {}

                # make sure we know that we have an article posted in this month/year
                archives[pub.year][pub.month] = True

            dt_archives = []

            # now sort the years, so they don't appear randomly on the page
            years = list(int(k) for k in archives.keys())
            years.sort()

            # more recent years will appear first in the resulting collection
            years.reverse()

            # iterate over all years
            for year in years:
                # sort the months of this year in which articles were posted
                m = list(int(k) for k in archives[year].keys())
                m.sort()

                # now create a list of datetime objects for each month/year
                months = [datetime(year, month, 1) for month in m]

                # append this list to our final collection
                dt_archives.append( ( year, tuple(months) ) )

            cache.set(cache_key, dt_archives)

        # put our collection into the context
        context[self.varname] = dt_archives
        return ''

def get_article_archives(parser, token):
    """
    Retrieves a list of years and months in which articles have been posted.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 3 and args[1] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('get_article_archives syntax: {% get_article_archives as varname %}')

    return GetArticleArchivesNode(args[2])

class DivideObjectListByNode(template.Node):
    """
    Divides an object list by some number to determine now many objects will
    fit into, say, a column.
    """
    def __init__(self, object_list, divisor, varname):
        self.object_list = template.Variable(object_list)
        self.divisor = template.Variable(divisor)
        self.varname = varname

    def render(self, context):
        # get the actual object list from the context
        object_list = self.object_list.resolve(context)

        # get the divisor from the context
        divisor = int(self.divisor.resolve(context))

        # make sure we don't divide by 0 or some negative number!!!!!!
        assert divisor > 0

        context[self.varname] = int(math.ceil(len(object_list) / float(divisor)))
        return ''

def divide_object_list(parser, token):
    """
    Divides an object list by some number to determine now many objects will
    fit into, say, a column.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 6 and args[2] == 'by' and args[4] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('divide_object_list syntax: {% divide_object_list object_list by divisor as varname %}')

    return DivideObjectListByNode(args[1], args[3], args[5])

class GetPageURLNode(template.Node):
    """
    Determines the URL of a pagination page link based on the page from which
    this tag is called.
    """
    def __init__(self, page_num, varname=None):
        self.page_num = template.Variable(page_num)
        self.varname = varname

    def render(self, context):
        url = None

        # get the page number we're linking to from the context
        page_num = self.page_num.resolve(context)

        try:
            # determine what view we are using based upon the path of this page
            view, args, kwargs = resolve(context['request'].path)
        except (Resolver404, KeyError):
            raise ValueError('Invalid pagination page.')
        else:
            # set the page parameter for this view
            kwargs['page'] = page_num

            # get the new URL from Django
            url = reverse(view, args=args, kwargs=kwargs)

        if self.varname:
            # if we have a varname, put the URL into the context and return nothing
            context[self.varname] = url
            return ''

        # otherwise, return the URL directly
        return url

def get_page_url(parser, token):
    """
    Determines the URL of a pagination page link based on the page from which
    this tag is called.
    """
    args = token.split_contents()
    argc = len(args)
    varname = None

    try:
        assert argc in (2, 4)
    except AssertionError:
        raise template.TemplateSyntaxError('get_page_url syntax: {% get_page_url page_num as varname %}')

    if argc == 4: varname = args[3]

    return GetPageURLNode(args[1], varname)

def tag_cloud():
    """Provides the tags with a "weight" attribute to build a tag cloud"""

    cache_key = 'tag_cloud_tags'
    tags = cache.get(cache_key)
    if tags is None:
        MAX_WEIGHT = 7
        tags = Tag.objects.annotate(count=Count('article'))

        if len(tags) == 0:
            # go no further
            return {}

        min_count = max_count = tags[0].article_set.count()
        for tag in tags:
            if tag.count < min_count:
                min_count = tag.count
            if max_count < tag.count:
                max_count = tag.count

        # calculate count range, and avoid dbz
        _range = float(max_count - min_count)
        if _range == 0.0:
            _range = 1.0

        # calculate tag weights
        for tag in tags:
            tag.weight = int(MAX_WEIGHT * (tag.count - min_count) / _range)

        cache.set(cache_key, tags)

    return {'tags': tags}

# register dem tags!
register.tag(get_articles)
register.tag(get_article_tags)
register.tag(get_article_archives)
register.tag(divide_object_list)
register.tag(get_page_url)
register.inclusion_tag('articles/_tag_cloud.html')(tag_cloud)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from models import Article, ArticleStatus, Tag, get_name, MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE

class ArticleUtilMixin(object):

    @property
    def superuser(self):
        if not hasattr(self, '_superuser'):
            self._superuser = User.objects.filter(is_superuser=True)[0]

        return self._superuser

    def new_article(self, title, content, tags=[], author=None, **kwargs):
        a = Article(
            title=title,
            content=content,
            author=author or self.superuser,
            **kwargs
        )
        a.save()

        if tags:
            a.tags = tags
            a.save()

        return a

class TagTestCase(TestCase):
    fixtures = ['tags']

    def setUp(self):
        self.client = Client()

    def test_unicode_tag(self):
        """Unicode characters in tags (issue #10)"""

        name = u'Căutare avansată'
        t = Tag.objects.create(name=name)
        self.assertEqual(t.slug, 'cutare-avansat')

        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # make sure older tags still work
        t2 = Tag.objects.get(pk=2)
        response = self.client.get(t2.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_tag_save(self):
        """Makes sure the overridden save method works for Tags"""

        t = Tag.objects.create(name='wasabi')
        t.name = 'DERP'
        t.save()

        self.assertEqual(t.slug, 'derp')

    def test_get_absolute_url(self):
        name = 'Hi There'
        t = Tag.objects.create(name=name)
        self.assertEqual(t.get_absolute_url(), reverse('articles_display_tag', args=[Tag.clean_tag(name)]))

class ArticleStatusTestCase(TestCase):

    def setUp(self):
        pass

    def test_instantiation(self):
        _as = ArticleStatus(name='Fake', ordering=5, is_live=True)
        self.assertEqual(unicode(_as), u'Fake (live)')

        _as.is_live = False
        self.assertEqual(unicode(_as), u'Fake')

class ArticleTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users']

    def setUp(self):
        pass

    def test_unique_slug(self):
        """Unique slugs"""

        a1 = self.new_article('Same Slug', 'Some content')
        a2 = self.new_article('Same Slug', 'Some more content')

        self.assertNotEqual(a1.slug, a2.slug)

    def test_active_articles(self):
        """Active articles"""

        a1 = self.new_article('New Article', 'This is a new article')
        a2 = self.new_article('New Article', 'This is a new article', is_active=False)

        self.assertEquals(Article.objects.active().count(), 1)

    def test_default_status(self):
        """Default status selection"""

        default_status = ArticleStatus.objects.default()
        other_status = ArticleStatus.objects.exclude(id=default_status.id)[0]

        self.assertTrue(default_status.ordering < other_status.ordering)

    def test_tagged_article_status(self):
        """Tagged article status"""

        t = Tag.objects.create(name='Django')

        draft = ArticleStatus.objects.filter(is_live=False)[0]
        finished = ArticleStatus.objects.filter(is_live=True)[0]

        a1 = self.new_article('Tagged', 'draft', status=draft, tags=[t])
        a2 = self.new_article('Tagged', 'finished', status=finished, tags=[t])

        self.assertEqual(t.article_set.live().count(), 1)
        self.assertEqual(t.article_set.active().count(), 2)

    def test_new_article_status(self):
        """New article status is default"""

        default_status = ArticleStatus.objects.default()
        article = self.new_article('New Article', 'This is a new article')
        self.failUnless(article.status == default_status)

    def test_live_articles(self):
        """Only live articles"""

        live_status = ArticleStatus.objects.filter(is_live=True)[0]
        a1 = self.new_article('New Article', 'This is a new article')
        a2 = self.new_article('New Article', 'This is a new article', is_active=False)
        a3 = self.new_article('New Article', 'This is a new article', status=live_status)
        a4 = self.new_article('New Article', 'This is a new article', status=live_status)

        self.assertEquals(Article.objects.live().count(), 2)
        self.assertEquals(Article.objects.live(self.superuser).count(), 3)

    def test_auto_expire(self):
        """
        Makes sure that articles set to expire will actually be marked inactive
        """

        one_second_ago = datetime.now() - timedelta(seconds=1)
        a = self.new_article('Expiring Article', 'I expired one second ago', is_active=True, expiration_date=one_second_ago)

        self.assertTrue(a.is_active)

        b = Article.objects.latest()
        self.assertFalse(b.is_active)

    def test_markup_markdown(self):
        """Makes sure markdown works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_MARKDOWN)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_rest(self):
        """Makes sure reStructuredText works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_REST)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_textile(self):
        """Makes sure textile works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_TEXTILE)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_html(self):
        """Makes sure HTML works (derp)"""

        html = '''<h1>A First Level Header</h1>
<h2>A Second Level Header</h2>

<p>Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.</p>'''

        a = self.new_article('Demo', html, markup=MARKUP_HTML)
        a.do_render_markup()
        self.assertEqual(html, a.rendered_content)

class ArticleAdminTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users']

    def setUp(self):
        self.client = Client()

        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')

    def tearDown(self):
        pass

    def test_mark_active(self):
        """Creates some inactive articles and marks them active"""

        for i in range(5):
            self.new_article('Article %s' % (i,), 'Content for article %s' % (i,), is_active=False)

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 0)

        # mark some articles active
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': Article.objects.all().values_list('id', flat=True)[0:3],
            'index': 0,
            'action': 'mark_active',
        })

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 3)

    def test_mark_inactive(self):
        """Creates some active articles and marks them inactive"""

        for i in range(5):
            self.new_article('Article %s' % (i,), 'Content for article %s' % (i,))

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 5)

        # mark some articles inactive
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': Article.objects.all().values_list('id', flat=True)[0:3],
            'index': 0,
            'action': 'mark_inactive',
        })

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 2)

    def test_dynamic_status(self):
        """Sets the status for multiple articles to something dynamic"""

        default_status = ArticleStatus.objects.default()
        other_status = ArticleStatus.objects.exclude(id=default_status.id)[0]

        self.new_article('An Article', 'Some content')
        self.new_article('Another Article', 'Some content')

        # make sure we have articles with the default status
        self.assertEqual(Article.objects.filter(status=default_status).count(), 2)

        # mark them with the other status
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': Article.objects.all().values_list('id', flat=True),
            'index': 0,
            'action': 'mark_status_%s' % (other_status.id,),
        })

        # make sure we have articles with the other status
        self.assertEqual(Article.objects.filter(status=other_status).count(), 2)

    def test_automatic_author(self):
        """
        Makes sure the author of an article will be set automatically based on
        the user who is logged in
        """

        res = self.client.post(reverse('admin:articles_article_add'), {
            'title': 'A new article',
            'slug': 'new-article',
            'content': 'Some content',
            'tags': 'this is a test',
            'status': ArticleStatus.objects.default().id,
            'markup': MARKUP_HTML,
            'publish_date_0': '2011-08-15',
            'publish_date_1': '09:00:00',
            'attachments-TOTAL_FORMS': 5,
            'attachments-INITIAL_FORMS': 0,
            'attachments-MAX_NUM_FORMS': 15,
        })

        self.assertRedirects(res, reverse('admin:articles_article_changelist'))
        self.assertEqual(Article.objects.filter(author__username='admin').count(), 1)

    def test_non_superuser(self):
        """Makes sure that non-superuser users can only see articles they posted"""

        # add some articles as the superuser
        for i in range(5):
            self.new_article('This is a test', 'with some content')

        # now add some as a non-superuser
        joe = User.objects.create_user('joe', 'joe@bob.com', 'bob')
        joe.is_staff = True
        joe.user_permissions = Permission.objects.filter(codename__endswith='_article')
        joe.save()

        self.client.login(username='joe', password='bob')
        for i in range(5):
            self.new_article('I am not a super user', 'har har', author=joe)

        # display all articles that the non-superuser can see
        res = self.client.get(reverse('admin:articles_article_changelist'))
        self.assertEqual(res.content.count('_selected_action'), 5)

        # make sure the superuser can see all of them
        self.client.login(username='admin', password='admin')
        res = self.client.get(reverse('admin:articles_article_changelist'))
        self.assertEqual(res.content.count('_selected_action'), 10)

class FeedTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['tags', 'users']

    def setUp(self):
        self.client = Client()

        status = ArticleStatus.objects.filter(is_live=True)[0]
        self.new_article('This is a test!', 'Testing testing 1 2 3',
                         tags=Tag.objects.all(), status=status)

    def test_latest_entries(self):
        """Makes sure the latest entries feed works"""

        res = self.client.get(reverse('articles_rss_feed_latest'))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_atom_feed_latest'))
        self.assertEqual(res.status_code, 200)

    def test_tags(self):
        """Makes sure that the tags feed works"""

        res = self.client.get(reverse('articles_rss_feed_tag', args=['demo']))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_rss_feed_tag', args=['demox']))
        self.assertEqual(res.status_code, 404)

        res = self.client.get(reverse('articles_atom_feed_tag', args=['demo']))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_atom_feed_tag', args=['demox']))
        self.assertEqual(res.status_code, 404)

class FormTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users',]

    def setUp(self):
        self.client = Client()

        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')

    def tearDown(self):
        pass

    def test_article_admin_form(self):
        """Makes sure the ArticleAdminForm works as expected"""

        a = self.new_article('Sample', 'sample')
        res = self.client.get(reverse('admin:articles_article_change', args=[a.id]))
        self.assertEqual(res.status_code, 200)

class ListenerTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users', 'tags']

    def test_apply_new_tag(self):
        """Makes sure auto-tagging works"""

        a = self.new_article('Yay', 'This is just a demonstration of how awesome Django and Python are.', auto_tag=True)
        self.assertEqual(a.tags.count(), 0)

        Tag.objects.create(name='awesome')
        Tag.objects.create(name='Python')
        t = Tag.objects.create(name='Django')

        # make sure the tags were actually applied to our new article
        self.assertEqual(a.tags.count(), 3)

class MiscTestCase(TestCase):
    fixtures = ['users',]

    def test_get_name(self):
        u1 = User.objects.get(pk=1)
        u2 = User.objects.get(pk=2)

        self.assertEqual(get_name(u1), 'superuser')
        self.assertEqual(get_name(u2), 'Jim Bob')

        self.assertEqual(u1.get_name(), 'superuser')
        self.assertEqual(u2.get_name(), 'Jim Bob')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from articles import views
from articles.feeds import TagFeed, LatestEntries, TagFeedAtom, LatestEntriesAtom

tag_rss = TagFeed()
latest_rss = LatestEntries()
tag_atom = TagFeedAtom()
latest_atom = LatestEntriesAtom()

urlpatterns = patterns('',
    (r'^(?P<year>\d{4})/(?P<month>.{3})/(?P<day>\d{1,2})/(?P<slug>.*)/$', views.redirect_to_article),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_in_month_page'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$', views.display_blog_page, name='articles_in_month'),
)

urlpatterns += patterns('',
    url(r'^$', views.display_blog_page, name='articles_archive'),
    url(r'^page/(?P<page>\d+)/$', views.display_blog_page, name='articles_archive_page'),

    url(r'^tag/(?P<tag>.*)/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_display_tag_page'),
    url(r'^tag/(?P<tag>.*)/$', views.display_blog_page, name='articles_display_tag'),

    url(r'^author/(?P<username>.*)/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_by_author_page'),
    url(r'^author/(?P<username>.*)/$', views.display_blog_page, name='articles_by_author'),

    url(r'^(?P<year>\d{4})/(?P<slug>.*)/$', views.display_article, name='articles_display_article'),

    # AJAX
    url(r'^ajax/tag/autocomplete/$', views.ajax_tag_autocomplete, name='articles_tag_autocomplete'),

    # RSS
    url(r'^feeds/latest\.rss$', latest_rss, name='articles_rss_feed_latest'),
    url(r'^feeds/latest/$', latest_rss),
    url(r'^feeds/tag/(?P<slug>[\w_-]+)\.rss$', tag_rss, name='articles_rss_feed_tag'),
    url(r'^feeds/tag/(?P<slug>[\w_-]+)/$', tag_rss),

    # Atom
    url(r'^feeds/atom/latest\.xml$', latest_atom, name='articles_atom_feed_latest'),
    url(r'^feeds/atom/tag/(?P<slug>[\w_-]+)\.xml$', tag_atom, name='articles_atom_feed_tag'),

)

########NEW FILE########
__FILENAME__ = views
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect, Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from articles.models import Article, Tag
from datetime import datetime

ARTICLE_PAGINATION = getattr(settings, 'ARTICLE_PAGINATION', 20)

log = logging.getLogger('articles.views')

def display_blog_page(request, tag=None, username=None, year=None, month=None, page=1):
    """
    Handles all of the magic behind the pages that list articles in any way.
    Yes, it's dirty to have so many URLs go to one view, but I'd rather do that
    than duplicate a bunch of code.  I'll probably revisit this in the future.
    """

    context = {'request': request}
    if tag:
        try:
            tag = get_object_or_404(Tag, slug__iexact=tag)
        except Http404:
            # for backwards-compatibility
            tag = get_object_or_404(Tag, name__iexact=tag)

        articles = tag.article_set.live(user=request.user).select_related()
        template = 'articles/display_tag.html'
        context['tag'] = tag

    elif username:
        # listing articles by a particular author
        user = get_object_or_404(User, username=username)
        articles = user.article_set.live(user=request.user)
        template = 'articles/by_author.html'
        context['author'] = user

    elif year and month:
        # listing articles in a given month and year
        year = int(year)
        month = int(month)
        articles = Article.objects.live(user=request.user).select_related().filter(publish_date__year=year, publish_date__month=month)
        template = 'articles/in_month.html'
        context['month'] = datetime(year, month, 1)

    else:
        # listing articles with no particular filtering
        articles = Article.objects.live(user=request.user)
        template = 'articles/article_list.html'

    # paginate the articles
    paginator = Paginator(articles, ARTICLE_PAGINATION,
                          orphans=int(ARTICLE_PAGINATION / 4))
    try:
        page = paginator.page(page)
    except EmptyPage:
        raise Http404

    context.update({'paginator': paginator,
                    'page_obj': page})
    variables = RequestContext(request, context)
    response = render_to_response(template, variables)

    return response

def display_article(request, year, slug, template='articles/article_detail.html'):
    """Displays a single article."""

    try:
        article = Article.objects.live(user=request.user).get(publish_date__year=year, slug=slug)
    except Article.DoesNotExist:
        raise Http404

    # make sure the user is logged in if the article requires it
    if article.login_required and not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + request.path)

    variables = RequestContext(request, {
        'article': article,
        'disqus_forum': getattr(settings, 'DISQUS_FORUM_SHORTNAME', None),
    })
    response = render_to_response(template, variables)

    return response

def redirect_to_article(request, year, month, day, slug):
    # this is a little snippet to handle URLs that are formatted the old way.
    article = get_object_or_404(Article, publish_date__year=year, slug=slug)
    return HttpResponsePermanentRedirect(article.get_absolute_url())

def ajax_tag_autocomplete(request):
    """Offers a list of existing tags that match the specified query"""

    if 'q' in request.GET:
        q = request.GET['q']
        key = 'ajax_tag_auto_%s' % q
        response = cache.get(key)

        if response is not None:
            return response

        tags = list(Tag.objects.filter(name__istartswith=q)[:10])
        response = HttpResponse(u'\n'.join(tag.name for tag in tags))
        cache.set(key, response, 300)

        return response

    return HttpResponse()


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
__FILENAME__ = settings
# Django settings for articles_demo project.
import os
DIRNAME = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'demo.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(DIRNAME, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'e9gni^br@&+ypal%p)c4qps0w5^pv%rrcior)z3d=*42k-)_8m'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'articles_demo.urls'

TEMPLATE_DIRS = (
    os.path.join(DIRNAME, 'templates')
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.markup',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.syndication',

    'articles',
    'south',

    'django_coverage',
)

# Change this to be your Disqus site's short name
# DISQUS_FORUM_SHORTNAME = 'short_name'

# Put your Disqus API key here (only necessary if you're porting comments from django.contrib.comments)
# DISQUS_USER_API_KEY = 'short_name'

# Configure articles from email
# ARTICLES_FROM_EMAIL = {
#     'protocol': 'IMAP4',
#     'host': 'mail.yourserver.com',
#     'port': 9000,
#     'keyfile': '/path/to/keyfile',
#     'certfile': '/path/to/certfile',
#     'user': 'your_username',
#     'password': 'your_password',
#     'ssl': True,
#     'autopost': True,
#     'markup': 'r',
#     'acknowledge': True,
# }

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^static/(?P<path>.*)', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    (r'^', include('articles.urls')),
)


########NEW FILE########
