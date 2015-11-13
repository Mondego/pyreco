__FILENAME__ = api
from urllib import urlencode
import urllib2

from django.utils import simplejson as json

# A custom ProxyHandler for the urllib2 module that will not
# auto-detect proxy settings
proxy_support = urllib2.ProxyHandler({})
opener = urllib2.build_opener(proxy_support)
urllib2.install_opener(opener)

class DisqusException(Exception):
    """Exception raised for errors with the DISQUS API."""
    pass

class DisqusClient(object):
    """
    Client for the DISQUS API.

    Example:
        >>> client = DisqusClient()
        >>> json = client.get_forum_list(user_api_key=DISQUS_API_KEY)
    """
    METHODS = {
        'create_post': 'POST',
        'get_forum_api_key': 'GET',
        'get_forum_list': 'GET',
        'get_forum_posts': 'GET',
        'get_num_posts': 'GET',
        'get_thread_by_url': 'GET',
        'get_thread_list': 'GET',
        'get_thread_posts': 'GET',
        'get_updated_threads': 'GET',
        'get_user_name': 'POST',
        'moderate_post': 'POST',
        'thread_by_identifier': 'POST',
        'update_thread': 'POST',
    }

    def __init__(self, **kwargs):
        self.api_url = 'http://disqus.com/api/%s/?api_version=1.1'
        self.__dict__.update(kwargs)

    def __getattr__(self, attr):
        """
        Called when an attribute is not found in the usual places
        (__dict__, class tree) this method will check if the attribute
        name is a DISQUS API method and call the `call` method.
        If it isn't in the METHODS dict, it will raise an AttributeError.
        """
        if attr in self.METHODS:
            def call_method(**kwargs):
                return self.call(attr, **kwargs)
            return call_method
        raise AttributeError

    def _get_request(self, request_url, request_method, **params):
        """
        Return a urllib2.Request object that has the GET parameters
        attached to the url or the POST data attached to the object.
        """
        if request_method == 'GET':
            if params:
                request_url += '&%s' % urlencode(params)
            request = urllib2.Request(request_url)
        elif request_method == 'POST':
            request = urllib2.Request(request_url, urlencode(params,doseq=1))
        return request

    def call(self, method, **params):
        """
        Call the DISQUS API and return the json response.
        URLError is raised when the request failed.
        DisqusException is raised when the query didn't succeed.
        """
        url = self.api_url % method
        request = self._get_request(url, self.METHODS[method], **params)
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            raise
        else:
            response_json = json.loads(response.read())
            if not response_json['succeeded']:
                raise DisqusException(response_json['message'])
            return response_json['message']

########NEW FILE########
__FILENAME__ = disqus_dumpdata
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
from django.utils import simplejson as json

from disqus.api import DisqusClient


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--indent', default=None, dest='indent', type='int',
            help='Specifies the indent level to use when pretty-printing output'),
        make_option('--filter', default='', dest='filter', type='str',
            help='Type of entries that should be returned'),
        make_option('--exclude', default='', dest='exclude', type='str',
            help='Type of entries that should be excluded from the response'),
    )
    help = 'Output DISQUS data in JSON format'
    requires_model_validation = False

    def handle(self, **options):
        from django.conf import settings

        client = DisqusClient()
        indent = options.get('indent')
        filter_ = options.get('filter')
        exclude = options.get('exclude')

        # Get a list of all forums for an API key. Each API key can have 
        # multiple forums associated. This application only supports the one 
        # set in the DISQUS_WEBSITE_SHORTNAME variable
        forum_list = client.get_forum_list(user_api_key=settings.DISQUS_API_KEY)
        try:
            forum = [f for f in forum_list\
                     if f['shortname'] == settings.DISQUS_WEBSITE_SHORTNAME][0]
        except IndexError:
            raise CommandError("Could not find forum. " +
                               "Please check your " +
                               "'DISQUS_WEBSITE_SHORTNAME' setting.")
        posts = []
        has_new_posts = True
        start = 0
        step = 100
        while has_new_posts:
            new_posts = client.get_forum_posts(
                user_api_key=settings.DISQUS_API_KEY,
                forum_id=forum['id'],
                start=start,
                limit=start+step,
                filter=filter_,
                exclude=exclude)
            if not new_posts:
                has_new_posts = False
            else:
                start += step
                posts.append(new_posts)
        print json.dumps(posts, indent=indent)

########NEW FILE########
__FILENAME__ = disqus_export
from optparse import make_option
import os.path

from django.conf import settings
from django.contrib import comments
from django.contrib.sites.models import Site
from django.core.management.base import NoArgsCommand
from django.utils import simplejson as json

from disqus.api import DisqusClient


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('-d', '--dry-run', action="store_true", dest="dry_run",
                    help='Does not export any comments, but merely outputs' +
                         'the comments which would have been exported.'),
        make_option('-s', '--state-file', action="store", dest="state_file",
                    help="Saves the state of the export in the given file " +
                         "and auto-resumes from this file if possible."),
    )
    help = 'Export comments from contrib.comments to DISQUS'
    requires_model_validation = False

    def _get_comments_to_export(self, last_export_id=None):
        """Return comments which should be exported."""
        qs = comments.get_model().objects.order_by('pk')\
                .filter(is_public=True, is_removed=False)
        if last_export_id is not None:
            print "Resuming after comment %s" % str(last_export_id)
            qs = qs.filter(id__gt=last_export_id)
        return qs

    def _get_last_state(self, state_file):
        """Checks the given path for the last exported comment's id"""
        state = None
        fp = open(state_file)
        try:
            state = int(fp.read())
            print "Found previous state: %d" % (state,)
        finally:
            fp.close()
        return state

    def _save_state(self, state_file, last_pk):
        """Saves the last_pk into the given state_file"""
        fp = open(state_file, 'w+')
        try:
            fp.write(str(last_pk))
        finally:
            fp.close()

    def handle(self, **options):
        current_site = Site.objects.get_current()
        client = DisqusClient()
        verbosity = int(options.get('verbosity'))
        dry_run = bool(options.get('dry_run'))
        state_file = options.get('state_file')
        last_exported_id = None

        if state_file is not None and os.path.exists(state_file):
            last_exported_id = self._get_last_state(state_file)

        comments = self._get_comments_to_export(last_exported_id)
        comments_count = comments.count()
        if verbosity >= 1:
            print "Exporting %d comment(s)" % comments_count

        # if this is a dry run, we output the comments and exit
        if dry_run:
            print comments
            return
        # if no comments were found we also exit
        if not comments_count:
            return

        # Get a list of all forums for an API key. Each API key can have 
        # multiple forums associated. This application only supports the one 
        # set in the DISQUS_WEBSITE_SHORTNAME variable
        forum_list = client.get_forum_list(user_api_key=settings.DISQUS_API_KEY)
        try:
            forum = [f for f in forum_list\
                     if f['shortname'] == settings.DISQUS_WEBSITE_SHORTNAME][0]
        except IndexError:
            raise CommandError("Could not find forum. " +
                               "Please check your " +
                               "'DISQUS_WEBSITE_SHORTNAME' setting.")

        # Get the forum API key
        forum_api_key = client.get_forum_api_key(
            user_api_key=settings.DISQUS_API_KEY,
            forum_id=forum['id'])

        for comment in comments:
            if verbosity >= 1:
                print "Exporting comment '%s'" % comment

            # Try to find a thread with the comments URL.
            url = 'http://%s%s' % (
                current_site.domain,
                comment.content_object.get_absolute_url())
            thread = client.get_thread_by_url(
                url=url,
                forum_api_key=forum_api_key)

            # if no thread with the URL could be found, we create a new one.
            # to do this, we first need to create the thread and then 
            # update the thread with a URL.
            if not thread:
                thread = client.thread_by_identifier(
                    forum_api_key=forum_api_key,
                    identifier=unicode(comment.content_object),
                    title=unicode(comment.content_object),
                )['thread']
                client.update_thread(
                    forum_api_key=forum_api_key,
                    thread_id=thread['id'],
                    url=url)

            # name and email are optional in contrib.comments but required
            # in DISQUS. If they are not set, dummy values will be used
            client.create_post(
                forum_api_key=forum_api_key,
                thread_id=thread['id'],
                message=comment.comment.encode('utf-8'),
                author_name=comment.userinfo.get('name',
                                                 'nobody').encode('utf-8'),
                author_email=comment.userinfo.get('email',
                                                  'nobody@example.org'),
                author_url=comment.userinfo.get('url', ''),
                created_at=comment.submit_date.strftime('%Y-%m-%dT%H:%M'))
            if state_file is not None:
                self._save_state(state_file, comment.pk)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = disqus_tags
from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.functional import curry
from django.utils.encoding import force_unicode

register = template.Library()

class ContextSetterNode(template.Node):
    def __init__(self, var_name, var_value):
        self.var_name = var_name
        self.var_value = var_value
    
    def _get_value(self, value, context):
        """
        Attempts to resolve the value as a variable. Failing that, it returns
        its actual value
        """
        try:
            var_value = template.Variable(value).resolve(context)
        except template.VariableDoesNotExist:
            var_value = self.var_value.var
        return var_value
    
    def render(self, context):
        if isinstance(self.var_value, (list, tuple)):
            var_value = ''.join([force_unicode(self._get_value(x, context)) for x in self.var_value])
        else:
            var_value = self._get_value(self.var_value, context)
        context[self.var_name] = var_value
        return ''

def generic_setter_compiler(var_name, name, node_class, parser, token):
    """
    Returns a ContextSetterNode.
    
    For calls like {% set_this_value "My Value" %}
    """
    bits = token.split_contents()
    if(len(bits) < 2):
        message = "%s takes at least one argument" % name
        raise template.TemplateSyntaxError(message)
    return node_class(var_name, bits[1:])

# Set the disqus_developer variable to 0/1. Default is 0
set_disqus_developer = curry(generic_setter_compiler, 'disqus_developer', 'set_disqus_developer', ContextSetterNode)

# Set the disqus_identifier variable to some unique value. Defaults to page's URL
set_disqus_identifier = curry(generic_setter_compiler, 'disqus_identifier', 'set_disqus_identifier', ContextSetterNode)

# Set the disqus_url variable to some value. Defaults to page's location
set_disqus_url = curry(generic_setter_compiler, 'disqus_url', 'set_disqus_url', ContextSetterNode)

# Set the disqus_title variable to some value. Defaults to page's title or URL
set_disqus_title = curry(generic_setter_compiler, 'disqus_title', 'set_disqus_title', ContextSetterNode)

def get_config(context):
    """
    return the formatted javascript for any disqus config variables
    """
    conf_vars = ['disqus_developer', 'disqus_identifier', 'disqus_url', 'disqus_title']
    
    output = []
    for item in conf_vars:
        if item in context:
            output.append('\tvar %s = "%s";' % (item, context[item]))
    return '\n'.join(output)

def disqus_dev():
    """
    Return the HTML/js code to enable DISQUS comments on a local
    development server if settings.DEBUG is True.
    """
    if settings.DEBUG:
        return """<script type="text/javascript">
    var disqus_developer = 1;
    var disqus_url = 'http://%s/';
</script>""" % Site.objects.get_current().domain
    return ""

def disqus_num_replies(context, shortname=''):
    """
    Return the HTML/js code which transforms links that end with an
    #disqus_thread anchor into the threads comment count.
    """
    shortname = getattr(settings, 'DISQUS_WEBSITE_SHORTNAME', shortname)
    
    return {
        'shortname': shortname,
        'config': get_config(context),
    }

def disqus_recent_comments(context, shortname='', num_items=5, excerpt_length=200, hide_avatars=0, avatar_size=32):
    """
    Return the HTML/js code which shows recent comments.

    """
    shortname = getattr(settings, 'DISQUS_WEBSITE_SHORTNAME', shortname)
    
    return {
        'shortname': shortname,
        'num_items': num_items,
        'hide_avatars': hide_avatars,
        'avatar_size': avatar_size,
        'excerpt_length': excerpt_length,
        'config': get_config(context),
    }

def disqus_show_comments(context, shortname=''):
    """
    Return the HTML code to display DISQUS comments.
    """
    shortname = getattr(settings, 'DISQUS_WEBSITE_SHORTNAME', shortname)
    return {
        'shortname': shortname,
        'config': get_config(context),
    }

register.tag('set_disqus_developer', set_disqus_developer)
register.tag('set_disqus_identifier', set_disqus_identifier)
register.tag('set_disqus_url', set_disqus_url)
register.tag('set_disqus_title', set_disqus_title)
register.simple_tag(disqus_dev)
register.inclusion_tag('disqus/num_replies.html', takes_context=True)(disqus_num_replies)
register.inclusion_tag('disqus/recent_comments.html', takes_context=True)(disqus_recent_comments)
register.inclusion_tag('disqus/show_comments.html', takes_context=True)(disqus_show_comments)

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.core.management.base import CommandError

from disqus.api import DisqusClient

__test__ = {'API_TESTS': """

First, we test if the DisqusClient class can be initialized
and parameters that were passed are set correctly.

>>> c = DisqusClient(foo='bar', bar='foo')
>>> c.foo
'bar'
>>> c.bar
'foo'
>>> c.baz
Traceback (most recent call last):
    ...
AttributeError


When a DISQUS API method is called, the call method should be used.

>>> c.get_forum_list
<function call_method at ...>
""",
}


########NEW FILE########
__FILENAME__ = wxr_feed
import datetime

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed, add_domain
from django.utils import feedgenerator, tzinfo
from django.utils.encoding import force_unicode, iri_to_uri

USE_SINGLE_SIGNON = getattr(settings, "DISQUS_USE_SINGLE_SIGNON", False)

class WxrFeedType(feedgenerator.Rss201rev2Feed):
    def rss_attributes(self):
        return {
            u"version": self._version,
            u'xmlns:content': u"http://purl.org/rss/1.0/modules/content/",
            u'xmlns:dsq': u"http://www.disqus.com/",
            u'xmlns:dc': u"http://purl.org/dc/elements/1.1/",
            u'xmlns:wp': u"http://wordpress.org/export/1.0/",
        }
    
    def format_date(self, date):
        return date.strftime('%Y-%m-%d %H:%M:%S')
    
    def add_item(self, title, link, description, author_email=None,
        author_name=None, author_link=None, pubdate=None, comments=None,
        unique_id=None, enclosure=None, categories=(), item_copyright=None,
        ttl=None, **kwargs):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        to_unicode = lambda s: force_unicode(s, strings_only=True)
        if categories:
            categories = [to_unicode(c) for c in categories]
        if ttl is not None:
            # Force ints to unicode
            ttl = force_unicode(ttl)
        item = {
            'title': to_unicode(title),
            'link': iri_to_uri(link),
            'description': to_unicode(description),
            'author_email': to_unicode(author_email),
            'author_name': to_unicode(author_name),
            'author_link': iri_to_uri(author_link),
            'pubdate': pubdate,
            'comments': comments,
            'unique_id': to_unicode(unique_id),
            'enclosure': enclosure,
            'categories': categories or (),
            'item_copyright': to_unicode(item_copyright),
            'ttl': ttl,
        }
        item.update(kwargs)
        self.items.append(item)
    
    def add_root_elements(self, handler):
        pass
    
    def add_item_elements(self, handler, item):
        if item['comments'] is None:
            return
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", item['link'])
        handler.addQuickElement(u"content:encoded", item['description'])
        handler.addQuickElement(u'dsq:thread_identifier', item['unique_id'])
        handler.addQuickElement(u'wp:post_date_gmt', 
            self.format_date(item['pubdate']).decode('utf-8'))
        handler.addQuickElement(u'wp:comment_status', item['comment_status'])
        self.write_comments(handler, item['comments'])
        
    def add_comment_elements(self, handler, comment):
        if USE_SINGLE_SIGNON:
            handler.startElement(u"dsq:remote", {})
            handler.addQuickElement(u"dsq:id", comment['user_id'])
            handler.addQuickElement(u"dsq:avatar", comment['avatar'])
            handler.endElement(u"dsq:remote")
        handler.addQuickElement(u"wp:comment_id", comment['id'])
        handler.addQuickElement(u"wp:comment_author", comment['user_name'])
        handler.addQuickElement(u"wp:comment_author_email", comment['user_email'])
        handler.addQuickElement(u"wp:comment_author_url", comment['user_url'])
        handler.addQuickElement(u"wp:comment_author_IP", comment['ip_address'])
        handler.addQuickElement(u"wp:comment_date_gmt", 
            self.format_date(comment['submit_date']).decode('utf-8'))
        handler.addQuickElement(u"wp:comment_content", comment['comment'])
        handler.addQuickElement(u"wp:comment_approved", comment['is_approved'])
        if comment['parent'] is not None:
            handler.addQuickElement(u"wp:comment_parent", comment['parent'])
    
    def write_comments(self, handler, comments):
        for comment in comments:
            handler.startElement(u"wp:comment", {})
            self.add_comment_elements(handler, comment)
            handler.endElement(u"wp:comment")


class BaseWxrFeed(Feed):
    feed_type = WxrFeedType
    
    def get_feed(self, obj, request):
        current_site = Site.objects.get_current()
        
        link = self._Feed__get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link)
        feed = self.feed_type(
            title = self._Feed__get_dynamic_attr('title', obj),
            link = link,
            description = self._Feed__get_dynamic_attr('description', obj),
        )
        
        title_tmp = None
        if self.title_template is not None:
            try:
                title_tmp = template.loader.get_template(self.title_template)
            except template.TemplateDoesNotExist:
                pass
        
        description_tmp = None
        if self.description_template is not None:
            try:
                description_tmp = template.loader.get_template(self.description_template)
            except template.TemplateDoesNotExist:
                pass
        
        for item in self._Feed__get_dynamic_attr('items', obj):
            if title_tmp is not None:
                title = title_tmp.render(
                    template.RequestContext(request, {
                        'obj': item, 'site': current_site
                    }))
            else:
                title = self._Feed__get_dynamic_attr('item_title', item)
            if description_tmp is not None:
                description = description_tmp.render(
                    template.RequestContext(request, {
                        'obj': item, 'site': current_site
                    }))
            else:
                description = self._Feed__get_dynamic_attr('item_description', item)
            link = add_domain(
                current_site.domain,
                self._Feed__get_dynamic_attr('item_link', item),
            )
            
            pubdate = self._Feed__get_dynamic_attr('item_pubdate', item)
            if pubdate and not hasattr(pubdate, 'tzinfo'):
                ltz = tzinfo.LocalTimezone(pubdate)
                pubdate = pubdate.replace(tzinfo=ltz)
            
            feed.add_item(
                title = title,
                link = link,
                description = description,
                unique_id = self._Feed__get_dynamic_attr('item_guid', item, link),
                pubdate = pubdate,
                comment_status = self._Feed__get_dynamic_attr('item_comment_status', item, 'open'),
                comments = self._get_comments(item)
            )
        return feed
    
    def _get_comments(self, item):
        cmts = self._Feed__get_dynamic_attr('item_comments', item)
        output = []
        for comment in cmts:
            output.append({
                'user_id': self._Feed__get_dynamic_attr('comment_user_id', comment),
                'avatar': self._Feed__get_dynamic_attr('comment_avatar', comment),
                'id': str(self._Feed__get_dynamic_attr('comment_id', comment)),
                'user_name': self._Feed__get_dynamic_attr('comment_user_name', comment),
                'user_email': self._Feed__get_dynamic_attr('comment_user_email', comment),
                'user_url': self._Feed__get_dynamic_attr('comment_user_url', comment),
                'ip_address': self._Feed__get_dynamic_attr('comment_ip_address', comment),
                'submit_date': self._Feed__get_dynamic_attr('comment_submit_date', comment),
                'comment': self._Feed__get_dynamic_attr('comment_comment', comment),
                'is_approved': str(self._Feed__get_dynamic_attr('comment_is_approved', comment)),
                'parent': str(self._Feed__get_dynamic_attr('comment_parent', comment)),
            })
        return output
        

class ContribCommentsWxrFeed(BaseWxrFeed):
    link = "/"
    
    def item_comments(self, item):
        from django.contrib.comments.models import Comment
        
        ctype = ContentType.objects.get_for_model(item)
        return Comment.objects.filter(content_type=ctype, object_pk=item.pk)
    
    def item_guid(self, item):
        ctype = ContentType.objects.get_for_model(item)
        return "%s_%s" % (ctype.name, item.pk)
    
    def comment_id(self, comment):
        return comment.pk
    
    def comment_user_id(self, comment):
        return force_unicode(comment.user_id)
    
    def comment_user_name(self, comment):
        return force_unicode(comment.user_name)
    
    def comment_user_email(self, comment):
        return force_unicode(comment.user_email)
    
    def comment_user_url(self, comment):
        return force_unicode(comment.user_url)
    
    def comment_ip_address(self, comment):
        return force_unicode(comment.ip_address)
    
    def comment_submit_date(self, comment):
        return comment.submit_date
    
    def comment_comment(self, comment):
        return comment.comment
    
    def comment_is_approved(self, comment):
        return int(comment.is_public)
    
    comment_parent = 0
    
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-disqus documentation build configuration file, created by
# sphinx-quickstart on Sat Mar  6 13:42:08 2010.
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
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-disqus'
copyright = u'2011, Arthur Koziel'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.4.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-disqusdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-disqus.tex', u'django-disqus Documentation',
   u'Arthur Koziel', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import logging
import sys
from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.contenttypes',
            'disqus',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['disqus']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
########NEW FILE########
