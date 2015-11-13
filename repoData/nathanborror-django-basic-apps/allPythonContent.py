__FILENAME__ = admin
from django.contrib import admin
from basic.blog.models import *


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Category, CategoryAdmin)

class PostAdmin(admin.ModelAdmin):
    list_display  = ('title', 'publish', 'status')
    list_filter   = ('publish', 'categories', 'status')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Post, PostAdmin)


class BlogRollAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'sort_order',)
    list_editable = ('sort_order',)
admin.site.register(BlogRoll)
########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import FeedDoesNotExist
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.core.urlresolvers import reverse
from basic.blog.models import Post, Category


class BlogPostsFeed(Feed):
    _site = Site.objects.get_current()
    title = '%s feed' % _site.name
    description = '%s posts feed.' % _site.name

    def link(self):
        return reverse('blog_index')

    def items(self):
        return Post.objects.published()[:10]

    def item_pubdate(self, obj):
        return obj.publish


class BlogPostsByCategory(Feed):
    _site = Site.objects.get_current()
    title = '%s posts category feed' % _site.name

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return Category.objects.get(slug__exact=bits[0])

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return "Posts recently categorized as %s" % obj.title

    def items(self, obj):
        return obj.post_set.published()[:10]

class CommentsFeed(Feed):
    _site = Site.objects.get_current()
    title = '%s comment feed' % _site.name
    description = '%s comments feed.' % _site.name

    def link(self):
        return reverse('blog_index')

    def items(self):
        ctype = ContentType.objects.get_for_model(Post)
        return Comment.objects.filter(content_type=ctype)[:10]

    def item_pubdate(self, obj):
        return obj.submit_date
########NEW FILE########
__FILENAME__ = managers
from django.db.models import Manager
import datetime


class PublicManager(Manager):
    """Returns published posts that are not in the future."""

    def published(self):
        return self.get_query_set().filter(status__gte=2, publish__lte=datetime.datetime.now())
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink
from django.contrib.auth.models import User
from django.conf import settings

from basic.blog.managers import PublicManager

import datetime
import tagging
from tagging.fields import TagField


class Category(models.Model):
    """Category model."""
    title = models.CharField(_('title'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        db_table = 'blog_categories'
        ordering = ('title',)

    def __unicode__(self):
        return u'%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('blog_category_detail', None, {'slug': self.slug})


class Post(models.Model):
    """Post model."""
    STATUS_CHOICES = (
        (1, _('Draft')),
        (2, _('Public')),
    )
    title = models.CharField(_('title'), max_length=200)
    slug = models.SlugField(_('slug'), unique_for_date='publish')
    author = models.ForeignKey(User, blank=True, null=True)
    body = models.TextField(_('body'), )
    tease = models.TextField(_('tease'), blank=True, help_text=_('Concise text suggested. Does not appear in RSS feed.'))
    status = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=2)
    allow_comments = models.BooleanField(_('allow comments'), default=True)
    publish = models.DateTimeField(_('publish'), default=datetime.datetime.now)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    categories = models.ManyToManyField(Category, blank=True)
    tags = TagField()
    objects = PublicManager()

    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')
        db_table  = 'blog_posts'
        ordering  = ('-publish',)
        get_latest_by = 'publish'

    def __unicode__(self):
        return u'%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('blog_detail', None, {
            'year': self.publish.year,
            'month': self.publish.strftime('%b').lower(),
            'day': self.publish.day,
            'slug': self.slug
        })

    def get_previous_post(self):
        return self.get_previous_by_publish(status__gte=2)

    def get_next_post(self):
        return self.get_next_by_publish(status__gte=2)


class BlogRoll(models.Model):
    """Other blogs you follow."""
    name = models.CharField(max_length=100)
    url = models.URLField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('sort_order', 'name',)
        verbose_name = _('blog roll')
        verbose_name_plural = _('blog roll')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return self.url
########NEW FILE########
__FILENAME__ = sitemap
from django.contrib.sitemaps import Sitemap
from basic.blog.models import Post


class BlogSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Post.objects.published()

    def lastmod(self, obj):
        return obj.publish
########NEW FILE########
__FILENAME__ = archive
import re
from django import template
from basic.blog.models import Post

register = template.Library()


class PostArchive(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        dates = Post.objects.published().dates('publish', 'month', order='DESC')
        if dates:
            context[self.var_name] = dates
        return ''


@register.tag
def get_post_archive(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m = re.search(r'as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    var_name = m.groups()[0]
    return PostArchive(var_name)


########NEW FILE########
__FILENAME__ = blog
import re

from django import template
from django.conf import settings
from django.db import models

Post = models.get_model('blog', 'post')
Category = models.get_model('blog', 'category')
BlogRoll = models.get_model('blog', 'blogroll')

register = template.Library()


class LatestPosts(template.Node):
    def __init__(self, limit, var_name):
        self.limit = int(limit)
        self.var_name = var_name

    def render(self, context):
        posts = Post.objects.published()[:self.limit]
        if posts and (self.limit == 1):
            context[self.var_name] = posts[0]
        else:
            context[self.var_name] = posts
        return ''


@register.tag
def get_latest_posts(parser, token):
    """
    Gets any number of latest posts and stores them in a varable.

    Syntax::

        {% get_latest_posts [limit] as [var_name] %}

    Example usage::

        {% get_latest_posts 10 as latest_post_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    format_string, var_name = m.groups()
    return LatestPosts(format_string, var_name)


class BlogCategories(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        categories = Category.objects.all()
        context[self.var_name] = categories
        return ''


@register.tag
def get_blog_categories(parser, token):
    """
    Gets all blog categories.

    Syntax::

        {% get_blog_categories as [var_name] %}

    Example usage::

        {% get_blog_categories as category_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m = re.search(r'as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    var_name = m.groups()[0]
    return BlogCategories(var_name)


@register.filter
def get_links(value):
    """
    Extracts links from a ``Post`` body and returns a list.

    Template Syntax::

        {{ post.body|markdown:"safe"|get_links }}

    """
    try:
        try:
            from BeautifulSoup import BeautifulSoup
        except ImportError:
            from beautifulsoup import BeautifulSoup
        soup = BeautifulSoup(value)
        return soup.findAll('a')
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in 'get_links' filter: BeautifulSoup isn't installed."
    return value


class BlogRolls(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        blogrolls = BlogRoll.objects.all()
        context[self.var_name] = blogrolls
        return ''


@register.tag
def get_blogroll(parser, token):
    """
    Gets all blogroll links.

    Syntax::

        {% get_blogroll as [var_name] %}

    Example usage::

        {% get_blogroll as blogroll_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m = re.search(r'as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    var_name = m.groups()[0]
    return BlogRolls(var_name)
########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.test import Client
>>> from basic.blog.models import Post, Category
>>> import datetime
>>> from django.core.urlresolvers import reverse
>>> client = Client()

>>> category = Category(title='Django', slug='django')
>>> category.save()
>>> category2 = Category(title='Rails', slug='rails')
>>> category2.save()

>>> post = Post(title='DJ Ango', slug='dj-ango', body='Yo DJ! Turn that music up!', status=2, publish=datetime.datetime(2008,5,5,16,20))
>>> post.save()

>>> post2 = Post(title='Where my grails at?', slug='where', body='I Can haz Holy plez?', status=2, publish=datetime.datetime(2008,4,2,11,11))
>>> post2.save()

>>> post.categories.add(category)
>>> post2.categories.add(category2)

>>> response = client.get(reverse('blog_index'))
>>> response.context[0]['object_list']
[<Post: DJ Ango>, <Post: Where my grails at?>]
>>> response.status_code
200

>>> response = client.get(reverse('blog_category_list'))
>>> response.context[0]['object_list']
[<Category: Django>, <Category: Rails>]
>>> response.status_code
200

>>> response = client.get(category.get_absolute_url())
>>> response.context[0]['object_list']
[<Post: DJ Ango>]
>>> response.status_code
200

>>> response = client.get(post.get_absolute_url())
>>> response.context[0]['object']
<Post: DJ Ango>
>>> response.status_code
200

>>> response = client.get(reverse('blog_search'), {'q': 'DJ'})
>>> response.context[0]['object_list']
[<Post: DJ Ango>]
>>> response.status_code
200
>>> response = client.get(reverse('blog_search'), {'q': 'Holy'})
>>> response.context[0]['object_list']
[<Post: Where my grails at?>]
>>> response.status_code
200
>>> response = client.get(reverse('blog_search'), {'q': ''})
>>> response.context[0]['message']
'Search term was too vague. Please try again.'

>>> response = client.get(reverse('blog_detail', args=[2008, 'apr', 2, 'where']))
>>> response.context[0]['object']
<Post: Where my grails at?>
>>> response.status_code
200
"""


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('basic.blog.views',
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        view='post_detail',
        name='blog_detail'
    ),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{1,2})/$',
        view='post_archive_day',
        name='blog_archive_day'
    ),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/$',
        view='post_archive_month',
        name='blog_archive_month'
    ),
    url(r'^(?P<year>\d{4})/$',
        view='post_archive_year',
        name='blog_archive_year'
    ),
    url(r'^categories/(?P<slug>[-\w]+)/$',
        view='category_detail',
        name='blog_category_detail'
    ),
    url (r'^categories/$',
        view='category_list',
        name='blog_category_list'
    ),
    url(r'^tags/(?P<slug>[-\w]+)/$',
        view='tag_detail',
        name='blog_tag_detail'
    ),
    url (r'^search/$',
        view='search',
        name='blog_search'
    ),
    url(r'^page/(?P<page>\d+)/$',
        view='post_list',
        name='blog_index_paginated'
    ),
    url(r'^$',
        view='post_list',
        name='blog_index'
    ),
)

########NEW FILE########
__FILENAME__ = views
import datetime
import re

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from django.views.generic import date_based, list_detail
from django.db.models import Q
from django.conf import settings

from basic.blog.models import *
from basic.tools.constants import STOP_WORDS_RE
from tagging.models import Tag, TaggedItem


def post_list(request, page=0, paginate_by=20, **kwargs):
    page_size = getattr(settings,'BLOG_PAGESIZE', paginate_by)
    return list_detail.object_list(
        request,
        queryset=Post.objects.published(),
        paginate_by=page_size,
        page=page,
        **kwargs
    )
post_list.__doc__ = list_detail.object_list.__doc__


def post_archive_year(request, year, **kwargs):
    return date_based.archive_year(
        request,
        year=year,
        date_field='publish',
        queryset=Post.objects.published(),
        make_object_list=True,
        **kwargs
    )
post_archive_year.__doc__ = date_based.archive_year.__doc__


def post_archive_month(request, year, month, **kwargs):
    return date_based.archive_month(
        request,
        year=year,
        month=month,
        date_field='publish',
        queryset=Post.objects.published(),
        **kwargs
    )
post_archive_month.__doc__ = date_based.archive_month.__doc__


def post_archive_day(request, year, month, day, **kwargs):
    return date_based.archive_day(
        request,
        year=year,
        month=month,
        day=day,
        date_field='publish',
        queryset=Post.objects.published(),
        **kwargs
    )
post_archive_day.__doc__ = date_based.archive_day.__doc__


def post_detail(request, slug, year, month, day, **kwargs):
    """
    Displays post detail. If user is superuser, view will display 
    unpublished post detail for previewing purposes.
    """
    posts = None
    if request.user.is_superuser:
        posts = Post.objects.all()
    else:
        posts = Post.objects.published()
    return date_based.object_detail(
        request,
        year=year,
        month=month,
        day=day,
        date_field='publish',
        slug=slug,
        queryset=posts,
        **kwargs
    )
post_detail.__doc__ = date_based.object_detail.__doc__


def category_list(request, template_name = 'blog/category_list.html', **kwargs):
    """
    Category list

    Template: ``blog/category_list.html``
    Context:
        object_list
            List of categories.
    """
    return list_detail.object_list(
        request,
        queryset=Category.objects.all(),
        template_name=template_name,
        **kwargs
    )


def category_detail(request, slug, template_name = 'blog/category_detail.html', **kwargs):
    """
    Category detail

    Template: ``blog/category_detail.html``
    Context:
        object_list
            List of posts specific to the given category.
        category
            Given category.
    """
    category = get_object_or_404(Category, slug__iexact=slug)

    return list_detail.object_list(
        request,
        queryset=category.post_set.published(),
        extra_context={'category': category},
        template_name=template_name,
        **kwargs
    )


def tag_detail(request, slug, template_name = 'blog/tag_detail.html', **kwargs):
    """
    Tag detail

    Template: ``blog/tag_detail.html``
    Context:
        object_list
            List of posts specific to the given tag.
        tag
            Given tag.
    """
    tag = get_object_or_404(Tag, name__iexact=slug)

    return list_detail.object_list(
        request,
        queryset=TaggedItem.objects.get_by_model(Post,tag).filter(status=2),
        extra_context={'tag': tag},
        template_name=template_name,
        **kwargs
    )


def search(request, template_name='blog/post_search.html'):
    """
    Search for blog posts.

    This template will allow you to setup a simple search form that will try to return results based on
    given search strings. The queries will be put through a stop words filter to remove words like
    'the', 'a', or 'have' to help imporve the result set.

    Template: ``blog/post_search.html``
    Context:
        object_list
            List of blog posts that match given search term(s).
        search_term
            Given search term.
    """
    context = {}
    if request.GET:
        stop_word_list = re.compile(STOP_WORDS_RE, re.IGNORECASE)
        search_term = '%s' % request.GET['q']
        cleaned_search_term = stop_word_list.sub('', search_term)
        cleaned_search_term = cleaned_search_term.strip()
        if len(cleaned_search_term) != 0:
            post_list = Post.objects.published().filter(Q(title__icontains=cleaned_search_term) | Q(body__icontains=cleaned_search_term) | Q(tags__icontains=cleaned_search_term) | Q(categories__title__icontains=cleaned_search_term))
            context = {'object_list': post_list, 'search_term':search_term}
        else:
            message = 'Search term was too vague. Please try again.'
            context = {'message':message}
    return render_to_response(template_name, context, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.bookmarks.models import *


class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('url', 'description')
    search_fields = ('url', 'description', 'extended')
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Bookmark, BookmarkAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from tagging.fields import TagField


class Bookmark(models.Model):
    """Bookmarks model"""
    title = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(_('slug'), unique=True)
    url = models.URLField(_('url'), unique=True)
    description = models.TextField(_('description'), )
    extended = models.TextField(_('extended'), blank=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    tags = TagField()

    class Meta:
        verbose_name = _('bookmark')
        verbose_name_plural = _('bookmarks')
        db_table = "bookmarks"

    def __unicode__(self):
        return self.url

    def get_absolute_url(self):
        return self.url

########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.test import Client
>>> from basic.bookmarks.models import Bookmark
>>> from django.core.urlresolvers import reverse

>>> client = Client()

>>> response = client.get(reverse('bookmark_index'))
>>> response.status_code
200

>>> bookmark = Bookmark(url='http://www.google.com', description='Django book', extended='Great resource!')
>>> bookmark.save()

"""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('basic.bookmarks.views',
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<object_id>\d+)/$',
        view='bookmark_detail',
        name='bookmark_detail',
    ),
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 
        view='bookmark_archive_day',
        name='bookmark_archive_day',
    ),
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
        view='bookmark_archive_month',
        name='bookmark_archive_month',
    ),
    url(r'^(?P<year>\d{4})/$',
        view='bookmark_archive_year',
        name='bookmark_archive_year',
    ),
    url(r'^$',
        view='bookmark_list',
        name='bookmark_index',
    ),
)
########NEW FILE########
__FILENAME__ = views
from django.views.generic import date_based, list_detail
from basic.bookmarks.models import *


def bookmark_list(request, page=0):
    return list_detail.object_list(
        request,
        queryset=Bookmark.objects.all(),
        paginate_by=20,
        page=page,
    )
bookmark_list.__doc__ = list_detail.object_list.__doc__


def bookmark_archive_year(request, year):
    return date_based.archive_year(
        request,
        year=year,
        date_field='created',
        queryset=Bookmark.objects.published(),
        make_object_list=True,
  )
bookmark_archive_year.__doc__ = date_based.archive_year.__doc__


def bookmark_archive_month(request, year, month):
    return date_based.archive_month(
        request,
        year=year,
        month=month,
        date_field='created',
        queryset=Bookmark.objects.published(),
    )
bookmark_archive_month.__doc__ = date_based.archive_month.__doc__


def bookmark_archive_day(request, year, month, day):
    return date_based.archive_day(
        request,
        year=year,
        month=month,
        day=day,
        date_field='created',
        queryset=Bookmark.objects.published(),
    )
bookmark_archive_day.__doc__ = date_based.archive_day.__doc__


def bookmark_detail(request, object_id, year, month, day):
    return date_based.object_detail(
        request,
        year=year,
        month=month,
        day=day,
        date_field='created',
        object_id=object_id,
        queryset=Bookmark.objects.published(),
    )
bookmark_detail.__doc__ = date_based.object_detail.__doc__
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.books.models import *


class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Genre, GenreAdmin)


class PublisherAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Publisher, PublisherAdmin)


class BookAdmin(admin.ModelAdmin):
    list_display  = ('title', 'pages')
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Book, BookAdmin)


class HighlightAdmin(admin.ModelAdmin):
    list_display  = ('book', 'highlight')
    list_filter   = ('book',)
admin.site.register(Highlight, HighlightAdmin)


class PageAdmin(admin.ModelAdmin):
    list_display = ('book', 'current_page')
admin.site.register(Page, PageAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import permalink
from django.conf import settings
from django.contrib.auth.models import User
from basic.people.models import Person


class Genre(models.Model):
    """Genre model"""
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'book_genres'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('book_genre_detail', None, { 'slug': self.slug })


class Publisher(models.Model):
    """Publisher"""
    title = models.CharField(max_length=100)
    prefix = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = 'book_publishers'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('book_publisher_detail', None, { 'slug':self.slug })


class Book(models.Model):
    """Listing of books"""
    title = models.CharField(max_length=255)
    prefix = models.CharField(max_length=20, blank=True)
    subtitle = models.CharField(blank=True, max_length=255)
    slug = models.SlugField(unique=True)
    authors = models.ManyToManyField(Person, limit_choices_to={'person_types__slug__exact': 'author'}, related_name='books')
    isbn = models.CharField(max_length=14, blank=True)
    pages = models.PositiveSmallIntegerField(blank=True, null=True, default=0)
    publisher = models.ForeignKey(Publisher, blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    cover = models.FileField(upload_to='books', blank=True)
    description = models.TextField(blank=True)
    genre = models.ManyToManyField(Genre, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'books'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        if self.prefix:
            return '%s %s' % (self.prefix, self.title)
        else:
            return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('book_detail', None, { 'slug': self.slug })

    @property
    def amazon_url(self):
        if self.isbn:
            try:
                return 'http://www.amazon.com/dp/%s/?%s' % (self.isbn, settings.AMAZON_AFFILIATE_EXTENTION)
            except:
                return 'http://www.amazon.com/dp/%s/' % self.isbn
        return ''


class Highlight(models.Model):
    """Highlights from books"""
    user = models.ForeignKey(User)
    book = models.ForeignKey(Book)
    highlight = models.TextField()
    page = models.CharField(blank=True, max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'book_highlights'

    def __unicode__(self):
        return '%s' % self.highlight

    @permalink
    def get_absolute_url(self):
        return ('book_detail', None, { 'slug': self.book.slug })


class Page(models.Model):
    """Page model"""
    user = models.ForeignKey(User)
    book = models.ForeignKey(Book)
    current_page = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'book_read_pages'
        ordering = ('-created',)

    def __unicode__(self):
        return '%s' % self.current_page
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from basic.books.models import *


genre_list = {
    'queryset': Genre.objects.all(),
}
publisher_list = {
    'queryset': Publisher.objects.all(),
}
book_list = {
    'queryset': Book.objects.all(),
}


urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^genres/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=genre_list,
        name='book_genre_detail',
    ),
    url (r'^genres/$',
        view='object_list',
        kwargs=genre_list,
        name='book_genre_list',
    ),
    url(r'^publishers/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=publisher_list,
        name='book_publisher_detail',
    ),
    url (r'^publishers/$',
        view='object_list',
        kwargs=publisher_list,
        name='book_publisher_list',
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=book_list,
        name='book_detail',
    ),
    url (r'^$',
        view='object_list',
        kwargs=book_list,
        name='book_list',
    ),
)
########NEW FILE########
__FILENAME__ = admin
from django.contrib.comments.admin import *
########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm
from django.contrib.comments.models import Comment


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        exclude = ('content_type', 'object_pk', 'site', 'user', 'is_public',
            'user_name', 'user_email', 'user_url', 'submit_date', 'ip_address',
            'is_removed',)
########NEW FILE########
__FILENAME__ = models
from django.contrib.comments.models import *
########NEW FILE########
__FILENAME__ = comments
from django.contrib.comments.templatetags.comments import *

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib.comments.urls import urlpatterns


urlpatterns += patterns('basic.comments.views',
    url(r'^(?P<object_id>\d+)/edit/$',
        view='comment_edit',
        name='comments-edit'),

    url(r'^(?P<object_id>\d+)/remove/$',
        view='comment_remove',
        name='comments-remove'),
)

########NEW FILE########
__FILENAME__ = views
import datetime

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.comments.models import Comment

from basic.comments.forms import CommentForm
from basic.tools.shortcuts import render, redirect


DELTA = datetime.datetime.now() - datetime.timedelta(
            minutes=getattr(settings, 'COMMENT_ALTERATION_TIME_LIMIT', 15))


def comment_edit(request, object_id, template_name='comments/edit.html'):
    comment = get_object_or_404(Comment, pk=object_id, user=request.user)

    if DELTA > comment.submit_date:
         return comment_error(request)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect(request, comment.content_object)
    else:
        form = CommentForm(instance=comment)
    return render(request, template_name, {
        'form': form,
        'comment': comment,
    })


def comment_remove(request, object_id, template_name='comments/delete.html'):
    comment = get_object_or_404(Comment, pk=object_id, user=request.user)

    if DELTA > comment.submit_date:
         return comment_error(request)

    if request.method == 'POST':
        comment.delete()
        return redirect(request, comment.content_object)
    return render(request, template_name, {'comment': comment})


def comment_error(request, error_message='You can not change this comment.',
        template_name='comments/error.html'):
    return render(request, template_name, {'error_message': error_message})

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.events.models import *


class EventTimeInline(admin.StackedInline):
    model = EventTime
    fk = 'event'


class EventAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'place', 'created')
    inlines = [
        EventTimeInline
    ]
admin.site.register(Event, EventAdmin)
########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink
from django.contrib.auth.models import User
from tagging.fields import TagField
from basic.places.models import Place


class Event(models.Model):
    """Event model"""
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    place = models.ForeignKey(Place, blank=True, null=True)
    one_off_place = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    submitted_by = models.ForeignKey(User, blank=True, null=True)
    tags = TagField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        db_table = 'events'

    def __unicode__(self):
        return self.title


class EventTime(models.Model):
    """EventTime model"""
    event = models.ForeignKey(Event, related_name='event_times')
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)
    is_all_day = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('event time')
        verbose_name_plural = _('event times')
        db_table = 'event_times'

    @property
    def is_past(self):
        NOW = datetime.date.now()
        if self.start < NOW:
            return True
        return False

    def __unicode__(self):
        return u'%s' % self.event.title

    @permalink
    def get_absolute_url(self):
        return ('event_detail', None, {
            'year': self.start.year,
            'month': self.start.strftime('%b').lower(),
            'day': self.start.day,
            'slug': self.event.slug,
            'event_id': self.event.id
        })
########NEW FILE########
__FILENAME__ = events
import re

from django import template
from basic.events.models import Event, EventTime

register = template.Library()


class UpcomingEventsNode(template.Node):
    def __init__(self, var_name, limit=10):
        self.var_name = var_name
        self.limit = limit

    def render(self, context):
        context[self.var_name] = EventTime.objects.order_by('-start')[:self.limit]


@register.tag
def get_upcoming_events(parser, token):
    """
    Returns a node which alters the context to provide upcoming events
    The upcoming events are stored in the variable specified.

    Syntax:
        {% get_upcoming_events <limit> as <varname> %}

    Example:
        {% get_upcoming_events 10 as upcoming_events %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]
    matches = re.search(r'([0-9]+) as (\w+)', arg)
    if not matches:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    limit, var_name = matches.groups()
    return UpcomingEventsNode(var_name, limit)
########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.test import Client
>>> from basic.events.models import *
>>> from django.core.urlresolvers import reverse

>>> client = Client()

"""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('basic.events.views',
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/(?P<event_id>\d)/$',
        view='event_detail',
        name='event_detail'
    ),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{1,2})/$',
        view='event_archive_day',
        name='event_archive_day'
    ),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/$',
        view='event_archive_month',
        name='event_archive_month'
    ),
    url(r'^(?P<year>\d{4})/$',
        view='event_archive_year',
        name='event_archive_year'
    ),
    url(r'^$',
        view='event_list',
        name='event_index'
    ),
)
########NEW FILE########
__FILENAME__ = views
import re, datetime

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from django.views.generic import date_based, list_detail
from basic.events.models import *


def event_list(request, page=0):
    return list_detail.object_list(
        request,
        queryset=EventTime.objects.all(),
        paginate_by=20,
        page=page,
    )
event_list.__doc__ = list_detail.object_list.__doc__


def event_archive_year(request, year):
    return date_based.archive_year(
        request,
        year=year,
        date_field='start',
        queryset=EventTime.objects.all(),
        make_object_list=True,
        allow_future=True,
    )
event_archive_year.__doc__ = date_based.archive_year.__doc__


def event_archive_month(request, year, month):
    return date_based.archive_month(
        request,
        year=year,
        month=month,
        date_field='start',
        queryset=EventTime.objects.all(),
        allow_future=True,
    )
event_archive_month.__doc__ = date_based.archive_month.__doc__


def event_archive_day(request, year, month, day):
    return date_based.archive_day(
        request,
        year=year,
        month=month,
        day=day,
        date_field='start',
        queryset=EventTime.objects.all(),
        allow_future=True,
    )
event_archive_day.__doc__ = date_based.archive_day.__doc__


def event_detail(request, slug, year, month, day, event_id):
    return date_based.object_detail(
        request,
        year=year,
        month=month,
        day=day,
        date_field='start',
        object_id=event_id,
        queryset=EventTime.objects.all(),
        allow_future=True,
    )
event_detail.__doc__ = date_based.object_detail.__doc__
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.flagging.models import *


class FlagTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(FlagType, FlagTypeAdmin)


class FlagAdmin(admin.ModelAdmin):
    list_display = ('object', 'flag_type')
    list_filter = ('flag_type',)
    raw_id_fields = ('user',)
admin.site.register(Flag, FlagAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User


class FlagType(models.Model):
    """ FlagType model """
    title = models.CharField(_('title'), blank=False, max_length=255)
    slug = models.SlugField()
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('flag type')
        verbose_name_plural = _('flag types')
        db_table = 'flag_types'

    def __unicode__(self):
        return self.title


class Flag(models.Model):
    """ Flag model """
    content_type = models.ForeignKey(ContentType, related_name='flags')
    object_id = models.IntegerField()
    object = GenericForeignKey()
    flag_type = models.ForeignKey(FlagType)
    user = models.ForeignKey(User)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    class Meta:
        verbose_name = _('flag')
        verbose_name_plural = _('flags')
        db_table = 'flags'

    def __unicode__(self):
        return '<Flagged item>'
########NEW FILE########
__FILENAME__ = flagging
from django import template
from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from basic.tools.templatetags.utils import parse_ttag

Flag = models.get_model('flagging', 'flag')
register = template.Library()


@register.filter
def flag_url(obj, slug):
    """
    Returns a URL used to flag an object. Convenience filter instead of
    having to build the URL using the url template tag.

    Example:

        {{ object|flag_url:"flag-type-slug" }}

    """
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('flag', kwargs={
        'slug': slug,
        'app_label': content_type.app_label,
        'model': content_type.model,
        'object_id': obj.pk
    })


@register.filter
def unflag_url(obj, slug):
    """
    Returns a URL used to unflag an object. Convenience filter instead of
    having to build the URL using the url template tag.

    Example:

        {{ object|unflag_url:"flag-type-slug" }}

    """
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('unflag', kwargs={
        'slug': slug,
        'app_label': content_type.app_label,
        'model': content_type.model,
        'object_id': obj.pk
    })


@register.filter
def flagged_with(obj, slug):
    """
    Returns true of false based on whether the object is flagged one or more
    times with a particular flag type.
    """
    content_type = ContentType.objects.get_for_model(obj)
    flags = Flag.objects.filter(
        flag_type__slug=slug,
        content_type=content_type,
        object_id=obj.pk
    )
    return flags.count() != 0


class GetFlags(template.Node):
    def __init__(self, object_name, user, slug, varname):
        self.object_name = object_name
        self.user = user
        self.slug = slug
        self.varname = varname

    def render(self, context):
        obj = template.resolve_variable(self.object_name, context)
        user = template.resolve_variable(self.user, context)
        slug = template.resolve_variable(self.slug, context)
        content_type = ContentType.objects.get_for_model(obj)
        try:
            flag = Flag.objects.get(flag_type__slug=slug, content_type=content_type, object_id=obj.id, user=user)
        except Flag.DoesNotExist:
            flag = None
        context[self.varname] = flag
        return ''

@register.tag('get_flags')
def do_get_flags(parser, token):
    """
    Get flags for an object.

    Syntax:
        {% get_flags for [object] by [user] type [type-slug] as [varname] %}

    Example:
        {% get_flags for object by user type "favorites" as flag %}
    """
    tags = parse_ttag(token, ['for', 'by', 'type', 'as'])
    if len(tags) != 5:
        raise template.TemplateSyntaxError, '%r tag has invalid arguments' % tags['tag_name']
    return GetFlags(object_name=tags['for'], user=tags['by'], slug=tags['type'], varname=tags['as'])

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from basic.flagging.models import *


class FlaggingTestCase(TestCase):
    fixtures = ['flagging.json']

    def setUp(self):
        self.user = User.objects.get(username='nathanb')
        self.ctype = ContentType.objects.get_for_model(self.user)
        self.flag_type = FlagType.objects.create(title='Test flagging', slug='test-flagging')
        self.friend = User.objects.get(username='laurah')

    def test_flagging(self):
        self.client.login(username=self.user.username, password='n')

        kwargs = {
            'slug': self.flag_type.slug,
            'app_label': self.ctype.app_label,
            'model': self.ctype.model,
            'object_id': self.friend.pk,
        }
        response = self.client.get(reverse('flag', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('flag', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('unflag', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('unflag', kwargs=kwargs))
        #self.assertEqual(response.status_code, 200)

        kwargs = {
            'username': 'nathanb',
            'slug': 'test-flagging'
        }
        response = self.client.get(reverse('user_flags', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


urlpatterns = patterns('basic.flagging.views',
    url(r'^flag/(?P<slug>[-\w]+)/(?P<app_label>\w+)/(?P<model>\w+)/(?P<object_id>\d+)/$',
        view='flag',
        name='flag'
    ),
    url(r'^unflag/(?P<slug>[-\w]+)/(?P<app_label>\w+)/(?P<model>\w+)/(?P<object_id>\d+)/$',
        view='unflag',
        name='unflag'
    ),
    url(r'^(?P<username>[-\w]+)/(?P<slug>[-\w]+)/$',
        view='user_flags',
        name='user_flags'
    ),
)
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.shortcuts import render_to_response, get_object_or_404
from django.utils import simplejson as json

from basic.flagging.models import *


@login_required
def flag(request, slug, app_label, model, object_id, 
        template_name='flagging/flag_confirm.html',
        success_template_name='flagging/flag_success.html'):
    """
    Flags an available flag type object.

    Templates: ``flagging/flag_confirm.html`` and ``flagging/flag_success.html``
    Context:
        object
            Object object
        flag_type
            FlagType object
    """
    flag_type = get_object_or_404(FlagType, slug=slug)
    content_type = ContentType.objects.get(app_label=app_label, model=model)
    model = content_type.model_class()
    obj = model.objects.get(pk=object_id)
    if request.method == 'POST':
        flag, created = Flag.objects.get_or_create(flag_type=flag_type,
                content_type=content_type, object_id=obj.pk, user=request.user)
        if request.is_ajax():
            response = {'success': 'Success'}
            return HttpResponse(json.dumps(response), mimetype="application/json")
        if request.GET.get('next', None):
            return HttpResponseRedirect(request.GET['next'])
        template_name = success_template_name
    return render_to_response(template_name, {
        'object': obj,
        'next': request.GET.get('next', None),
        'flag_type': flag_type
    }, context_instance=RequestContext(request))


@login_required
def unflag(request, slug, app_label, model, object_id,
        template_name='flagging/unflag_confirm.html',
        success_template_name='flagging/unflag_success.html'):
    """
    Unflag an available flag types object.

    Templates: ``flagging/unflag_confirm.html`` and ``flagging/unflag_success.html``
    Context:
        object
            Object object
        flag_type
            FlagType object
    """
    flag_type = get_object_or_404(FlagType, slug=slug)
    content_type = ContentType.objects.get(app_label=app_label, model=model)
    model = content_type.model_class()
    obj = model.objects.get(pk=object_id)
    if request.method == 'POST':
        flag = Flag.objects.get(flag_type=flag_type, content_type=content_type,
                object_id=obj.pk, user=request.user)
        flag.delete()
        if request.is_ajax():
            response = {'success': 'Success'}
            return HttpResponse(json.dumps(response), mimetype="application/json")
        if request.GET.get('next', None):
            return HttpResponseRedirect(request.GET['next'])
        template_name = success_template_name
    return render_to_response(template_name, {
        'object': obj,
        'next': request.GET.get('next', None),
        'flag_type': flag_type
    }, context_instance=RequestContext(request))


def user_flags(request, username, slug, template_name='flagging/flag_list.html'):
    """
    Returns a list of flagged items for a particular user.
    
    Templates: ``flagging/flag_list.html``
    Context:
        flag_list
            List of Flag objects
    """
    user = get_object_or_404(User, username=username)
    flag_type = get_object_or_404(FlagType, slug=slug)
    flag_list = Flag.objects.filter(user=user, flag_type=flag_type)
    return render_to_response(template_name, {
        'person': user,
        'flag_type': flag_type,
        'flag_list': flag_list
    }, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.groups.models import *


class GroupMemberInline(admin.TabularInline):
    raw_id_fields = ('user',)
    model = GroupMember
    fk = 'group'

class GroupMessageInline(admin.TabularInline):
    raw_id_fields = ('user',)
    model = GroupMessage
    fk = 'topic'

class GroupPageInline(admin.TabularInline):
    model = GroupPage
    fk = 'group'


class GroupAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('creator',)
    inlines = (
        GroupPageInline,
        GroupMemberInline
    )
admin.site.register(Group, GroupAdmin)


class GroupTopicAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'group')
    inlines = (GroupMessageInline,)
admin.site.register(GroupTopic, GroupTopicAdmin)


class GroupMemberAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'group')
    list_display = ('user', 'group', 'status', 'created')
admin.site.register(GroupMember, GroupMemberAdmin)
########NEW FILE########
__FILENAME__ = decorators
import datetime

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

from basic.groups.models import Group, GroupMember


def membership_required(function=None):
    """
    Decorator for views that require user to be a member of a group, 
    redirecting to the group join page if necessary.
    """
    def decorator(request, *args, **kwargs):
        group = get_object_or_404(Group, slug=kwargs['slug'])
        if request.user.is_anonymous():
            return HttpResponseRedirect(reverse('django.contrib.auth.views.login'))
        if GroupMember.objects.is_member(group, request.user):
            return function(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('groups:join', args=[group.slug]))
    return decorator


def ownership_required(function=None):
    """
    Decorator for views that require ownership status of a group.
    """
    def decorator(request, *args, **kwargs):
        group = get_object_or_404(Group, slug=kwargs['slug'])
        if request.user.is_anonymous():
            return HttpResponseRedirect(reverse('django.contrib.auth.views.login'))
        if GroupMember.objects.is_owner(group, request.user):
            return function(request, *args, **kwargs)
        else:
            raise Http404
    return decorator


def moderator_required(function=None):
    """
    Decorator for views that require moderator status of a group.
    """
    def decorator(request, *args, **kwargs):
        group = get_object_or_404(Group, slug=kwargs['slug'])
        if request.user.is_anonymous():
            return HttpResponseRedirect(reverse('django.contrib.auth.views.login'))
        if GroupMember.objects.is_moderator(group, request.user):
            return function(request, *args, **kwargs)
        else:
            raise Http404
    return decorator
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User

from basic.groups.models import *


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = ('creator', 'is_active')


class GroupTopicForm(forms.ModelForm):
    class Meta:
        model = GroupTopic
        exclude = ('group', 'user', 'is_active')


class GroupMessageForm(forms.ModelForm):
    class Meta:
        model = GroupMessage
        exclude = ('topic', 'user', 'is_active')


class GroupInviteForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.HiddenInput)
    group = forms.ModelChoiceField(queryset=Group.objects.all(), widget=forms.HiddenInput)
    name = forms.CharField()
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)


class GroupPageForm(forms.ModelForm):
    class Meta:
        model = GroupPage
        exclude = ('group',)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User
from django.conf import settings

from basic.tools.shortcuts import build_filename


GROUP_OWNER = 0
GROUP_MODERATOR = 1
GROUP_MEMBER = 2
GROUP_MEMBER_CHOICES = (
    (GROUP_OWNER, 'Owner'),
    (GROUP_MODERATOR, 'Moderator'),
    (GROUP_MEMBER, 'Member')
)


def get_icon_path(instance, filename):
    if instance.pk:
        group = Group.objects.get(pk=instance.pk)
        if group.icon:
            return group.icon.path.replace(settings.MEDIA_ROOT, '')
    return build_filename(instance, filename)


class Group(models.Model):
    """ Group model """
    title = models.CharField(blank=False, max_length=255)
    slug = models.SlugField(unique=True, help_text="Used for the Group URL: http://example.com/groups/the-club/")
    tease = models.TextField(blank=True, help_text="Brief explaination of what this group is. Shows up when the group is listed amoung other groups.")
    creator = models.ForeignKey(User, related_name='created_groups', help_text="Serves as a record as who the original creator was in case ownership is transfered.")
    icon = models.FileField(upload_to=get_icon_path, blank=True, help_text="Needs to be larger than 120x120 pixels.")
    invite_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title

    @permalink
    def get_absolute_url(self):
        return ('groups:group', None, {'slug': self.slug})

    def owners(self):
        return self.members.filter(status=0)

    def moderators(self):
        return self.members.filter(status=1)

    def is_member(self, user):
        try:
            member = self.members.get(user=user)
            return member
        except:
            return None


class GroupPage(models.Model):
    """ GroupPage model """
    group = models.ForeignKey(Group, related_name='pages')
    title = models.CharField(blank=True, max_length=100)
    slug = models.SlugField(help_text='Used for the page URL.')
    body = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title

    class Meta:
        unique_together = (('slug', 'group'),)

    @permalink
    def get_absolute_url(self):
        return ('groups:page', None, {
            'slug': self.group.slug,
            'page_slug': self.slug
        })


class GroupTopic(models.Model):
    """ GroupTopic model """
    group = models.ForeignKey(Group, related_name='topics')
    user = models.ForeignKey(User, related_name='group_topics')
    title = models.CharField(blank=False, max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-id',)

    def __unicode__(self):
        return self.title

    @permalink
    def get_absolute_url(self):
        return ('groups:topic', [self.group.slug, self.pk])

    @permalink
    def get_edit_url(self):
        return ('groups:topic_edit', [self.group.slug, self.pk])

    @permalink
    def get_remove_url(self):
        return ('groups:topic_remove', [self.group.slug, self.pk])


class GroupMessageManager(models.Manager):
    """Returns messages that are flagged as active."""

    def get_query_set(self):
        return super(GroupMessageManager, self).get_query_set().filter(is_active=True)


class GroupMessage(models.Model):
    """ GroupMessage model """
    topic = models.ForeignKey(GroupTopic, related_name="messages")
    user = models.ForeignKey(User)
    message = models.TextField(blank=False)
    is_active = models.BooleanField(default=True)
    objects = GroupMessageManager()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.message

    @permalink
    def get_absolute_url(self):
        return ('groups:message',
            [self.topic.group.slug, self.topic.pk, self.pk])

    @permalink
    def get_edit_url(self):
        return ('groups:message_edit',
            [self.topic.group.slug, self.topic.pk, self.pk])

    @permalink
    def get_remove_url(self):
        return ('groups:message_remove',
            [self.topic.group.slug, self.topic.pk, self.pk])


class GroupMemberManager(models.Manager):
    """Returns memebers that belong to a group"""
    def is_member(self, group, user):
        if user.is_anonymous():
            return False
        if self.filter(group=group, user=user).count() > 0:
            return True
        return False

    def is_owner(self, group, user):
        if user.is_anonymous():
            return False
        if self.filter(group=group, user=user, status=GROUP_OWNER).count() > 0:
            return True
        return False

    def is_moderator(self, group, user):
        if user.is_anonymous():
            return False
        if self.filter(group=group, user=user, status__in=(GROUP_MODERATOR, GROUP_OWNER)).count() > 0:
            return True
        return False


class GroupMember(models.Model):
    """ GroupMember model """
    user = models.ForeignKey(User, related_name='group_memberships')
    group = models.ForeignKey(Group, related_name='members')
    status = models.PositiveSmallIntegerField(choices=GROUP_MEMBER_CHOICES, default=GROUP_MEMBER)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    objects = GroupMemberManager()

    class Meta:
        unique_together = (('user', 'group'),)

    def __unicode__(self):
        return self.user.username

########NEW FILE########
__FILENAME__ = groups
from django import template
from django.db import models

GroupMember = models.get_model('groups', 'groupmember')
register = template.Library()


@register.filter
def is_member(group, user):
    return GroupMember.objects.is_member(group, user)


@register.filter
def is_owner(group, user):
    return GroupMember.objects.is_owner(group, user)


@register.filter
def is_moderator(group, user):
    return GroupMember.objects.is_moderator(group, user)
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.core import management
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from basic.groups.models import *


class GroupTestCase(TestCase):
    fixtures = ['groups.json', 'users.json']

    def setUp(self):
        self.user1 = User.objects.get(username='nathanb')
        self.user2 = User.objects.get(username='laurah')

        self.group = Group.objects.get(pk=1)
        self.topic = GroupTopic.objects.get(pk=1)
        self.message = GroupMessage.objects.get(pk=1)
        self.page = GroupPage.objects.get(pk=1)

        self.client.login(username=self.user1.username, password='n')

    def test_groups(self):
        group_args = [self.group.slug]

        response = self.client.get(reverse('groups:groups'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:group', args=group_args))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:create'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('groups:create'), {
            'title': 'My new group',
            'slug': 'my-new-group'
        })
        self.assertEqual(response.status_code, 302)

        group = Group.objects.get(pk=2)

        response = self.client.get(reverse('groups:edit', args=group_args))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('groups:edit', args=[group.slug]), {
            'title': 'My really new group',
            'slug': 'my-new-group'
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('groups:remove', args=[group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('groups:remove', args=[group.slug]))
        self.assertEqual(response.status_code, 302)

    def test_group_membership(self):
        response = self.client.get(reverse('groups:join', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:members', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:invite', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

    def test_pages(self):
        page_args = [self.group.slug, self.page.slug]

        response = self.client.get(reverse('groups:pages', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:page_create', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('groups:page_create', args=[self.group.slug]), {
            'title': 'Contact us',
            'slug': 'contact',
            'body': 'Lorem ipsum dolor sit amet, consectetur adipisicing elit.'
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('groups:page', args=page_args))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:page_edit', args=page_args))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('groups:page_edit', args=page_args), {
            'title': 'About our group',
            'slug': 'about'
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('groups:page_remove', args=page_args))
        self.assertEqual(response.status_code, 200)

    def test_topics(self):
        response = self.client.get(reverse('groups:topics', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('groups:topic_create', args=[self.group.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.topic.get_edit_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.topic.get_remove_url())
        self.assertEqual(response.status_code, 200)

    def test_messages(self):
        response = self.client.get(reverse('groups:message_create', args=[self.group.slug, self.topic.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.message.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.message.get_edit_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.message.get_remove_url())
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


GROUP_URL = r'(?P<slug>[-\w]+)/'
PAGE_URL = r'%spages/(?P<page_slug>[-\w]+)/' % GROUP_URL
TOPIC_URL = r'%stopics/(?P<topic_id>\d+)/' % GROUP_URL
MESSAGE_URL = r'%smessages/(?P<message_id>\d+)/' % TOPIC_URL


urlpatterns = patterns('basic.groups.views.groups',
    url(r'^create/$',                           'group_create',         name='create'),
    url(r'^%s$' % GROUP_URL,                    'group_detail',         name='group'),
    url(r'^%sedit/$' % GROUP_URL,               'group_edit',           name='edit'),
    url(r'^%sremove/$' % GROUP_URL,             'group_remove',         name='remove'),
    url(r'^%sjoin/$' % GROUP_URL,               'group_join',           name='join'),
    url(r'^%smembers/$' % GROUP_URL,            'group_members',        name='members'),
    url(r'^%sinvite/$' % GROUP_URL,             'group_invite',         name='invite'),
    url(r'^$',                                  'group_list',           name='groups'),
)

# Topics
urlpatterns += patterns('basic.groups.views.topics',
    url(r'^%stopics/create/$' % GROUP_URL,      'topic_create',         name='topic_create'),
    url(r'^%s$' % TOPIC_URL,                    'topic_detail',         name='topic'),
    url(r'^%sedit/$' % TOPIC_URL,               'topic_edit',           name='topic_edit'),
    url(r'^%sremove/$' % TOPIC_URL,             'topic_remove',         name='topic_remove'),
    url(r'^%stopics/$' % GROUP_URL,             'topic_list',           name='topics'),
)

# Pages
urlpatterns += patterns('basic.groups.views.pages',
    url(r'^%spages/create/$' % GROUP_URL,       'page_create',          name='page_create'),
    url(r'^%s$' % PAGE_URL,                     'page_detail',          name='page'),
    url(r'^%sedit/$' % PAGE_URL,                'page_edit',            name='page_edit'),
    url(r'^%sremove/$' % PAGE_URL,              'page_remove',          name='page_remove'),
    url(r'^%spages/$' % GROUP_URL,              'page_list',            name='pages'),
)

# Messages
urlpatterns += patterns('basic.groups.views.messages',
    url(r'^%smessages/create/$' % TOPIC_URL,    'message_create',       name='message_create'),
    url(r'^%s$' % MESSAGE_URL,                  'message_detail',       name='message'),
    url(r'^%sedit/$' % MESSAGE_URL,             'message_edit',         name='message_edit'),
    url(r'^%sremove/$' % MESSAGE_URL,           'message_remove',       name='message_remove'),
    url(r'^%smessages/$' % TOPIC_URL,           'message_list',         name='messages'),
)

########NEW FILE########
__FILENAME__ = groups
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from basic.groups.decorators import *
from basic.groups.models import *
from basic.groups.forms import *
from basic.tools.shortcuts import render, redirect


def group_list(request, username=None,
        template_name='groups/group_list.html'):
    """
    Returns a group list page.

    Templates: ``groups/group_list.html``
    Context:
        group_list
            Group object list
    """
    group_list = Group.objects.filter(is_active=True)
    if request.user.is_authenticated():
        membership_list = group_list.filter(members__user=request.user)
    else:
        membership_list = []
    return render(request, template_name, {
        'group_list': group_list,
        'membership_list': membership_list
    })


@login_required
def group_create(request, template_name='groups/group_form.html'):
    """
    Returns a group form page.

    Templates: ``groups/group_form.html``
    Context:
        form
            GroupForm object
    """
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()
            creator = GroupMember.objects.create(user=request.user, group=group, status=0)
            return redirect(request, group)
    else:
        form = GroupForm()
    return render(request, template_name, {'form': form})


def group_detail(request, slug, template_name='groups/group_detail.html'):
    """
    Returns a group detail page.

    Templates: ``groups/group_detail.html``
    Context:
        group
            Group object
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    if group.invite_only and not GroupMember.objects.is_member(group, request.user):
        return redirect(request, reverse('groups:join', kwargs={'slug': group.slug}))
    return render(request, template_name, {
        'group': group,
        'topic_list': group.topics.all(),
    })


@ownership_required
def group_edit(request, slug, template_name='groups/group_form.html'):
    """
    Returns a group form page.

    Templates: ``groups/group_form.html``
    Context:
        form
            GroupForm object
        group
            Group object
    """
    group = get_object_or_404(Group, slug=slug, creator=request.user)
    form = GroupForm(instance=group)

    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            return redirect(request, group)
    return render(request, template_name, {
        'form': form,
        'group': group
    })


@ownership_required
def group_remove(request, slug, template_name='groups/group_remove_confirm.html'):
    """
    Returns a group delete confirmation page.

    Templates: ``groups/group_remove_confirm.html``
    Context:
        group
            Group object
    """
    group = get_object_or_404(Group, slug=slug, creator=request.user)
    if request.method == 'POST':
        group.is_active = False
        group.save()
        return redirect(request, reverse('groups:groups'))
    return render(request, template_name, {'group': group})


def group_members(request, slug, template_name='groups/group_members.html'):
    """
    Returns members of a group.

    Templates: ``groups/group_members.html``
    Context:
        group
            Group object
        member_list
            User objects
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    member_list = group.members.all()
    return render(request, template_name, {
        'group': group,
        'member_list': member_list
    })


@login_required
def group_join(request, slug, template_name='groups/group_join_confirm.html'):
    """
    Returns a group join confirmation page.

    Templates: ``groups/group_join_confirm.html``
    Context:
        group
            Group object
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    if request.method == 'POST':
        membership = GroupMember(group=group, user=request.user)
        membership.save()
        return redirect(request, group)
    return render(request, template_name, {'group': group})


@membership_required
def group_invite(request, slug, template_name='groups/group_invite.html'):
    """
    Returns an invite form.
    
    Templates: ``groups/group_invite.html``
    Context:
        form
            GroupInviteForm object
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    form = GroupInviteForm(initial={'group': group.pk, 'user': request.user.pk})
    return render(request, template_name, {
        'group': group,
        'form': form
    })

########NEW FILE########
__FILENAME__ = messages
from django.shortcuts import get_object_or_404

from basic.groups.decorators import *
from basic.groups.models import *
from basic.groups.forms import *
from basic.tools.shortcuts import render, redirect


def message_list(request, slug, topic_id, template_name='groups/messages/message_list.html'):
    """
    Returns a group topic message list page.

    Templates: ``groups/messages/message_list.html``
    Context:
        group
            Group object
        topic
            GroupTopic object
        message_list
            List of GroupMessage objects
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    topic = get_object_or_404(GroupTopic, pk=topic_id, group=group, is_active=True)
    return render(request, template_name, {
        'group': group,
        'topic': topic,
        'message_list': topic.messages.all()
    })


def message_detail(request, slug, topic_id, message_id,
        template_name='groups/messages/message_detail.html'):
    """
    Returns a message detail page.

    Templates: ``groups/messages/message_detail.html``
    Context:
        group
            Group object
        topic
            GroupTopic object
        message
            GroupMessage object
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    topic = get_object_or_404(GroupTopic, pk=topic_id, is_active=True)
    message = get_object_or_404(GroupMessage, pk=message_id, is_active=True)
    return render(request, template_name, {
        'group': group,
        'topic': topic,
        'message': message
    })


@membership_required
def message_create(request, slug, topic_id,
        template_name='groups/messages/message_form.html'):
    """
    Returns a group message form.

    Templates: ``groups/messages/message_form.html``
    Context:
        group
            Group object
        topic
            GroupTopic object
        form
            GroupMessageForm object
    """
    group = get_object_or_404(Group, slug=slug)
    topic = get_object_or_404(GroupTopic, pk=topic_id, group=group)
    if request.method == 'POST':
        form = GroupMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.user = request.user
            message.topic = topic
            message.save()
            return redirect(request, topic)
    else:
        form = GroupMessageForm()
    return render(request, template_name, {
        'group': group,
        'topic': topic,
        'form': form,
    })


@membership_required
def message_edit(request, slug, topic_id, message_id,
        template_name='groups/messages/message_form.html'):
    """
    Returns a group message edit form.

    Templates: ``groups/messages/message_form.html``
    Context:
        group
            Group object
        topic
            GroupTopic object
        message
            GroupMessage object
        form
            GroupMessageForm object
    """
    message = get_object_or_404(GroupMessage, pk=message_id, is_active=True)
    if request.method == 'POST':
        form = GroupMessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            return redirect(request, message.topic)
    else:
        form = GroupMessageForm(instance=message)
    return render(request, template_name, {
        'group': message.topic.group,
        'topic': message.topic,
        'message': message,
        'form': form,
    })


@membership_required
def message_remove(request, slug, topic_id, message_id,
        template_name='groups/messages/message_remove_confirm.html'):
    """
    Returns a message delete confirmation page.

    Templates: ``groups/messages/message_remove_confirm.html``
    Context:
        group
            Group object
        topic
            GroupTopic object
        message
            GroupMessage object
    """
    message = get_object_or_404(GroupMessage, pk=message_id, is_active=True)
    if request.method == 'POST':
        message.is_active = False
        message.save()
        return redirect(request, message.topic)
    return render(request, template_name, {
        'group': message.topic.group,
        'topic': message.topic,
        'message': message,
    })

########NEW FILE########
__FILENAME__ = pages
from django.shortcuts import get_object_or_404

from basic.groups.decorators import *
from basic.groups.models import *
from basic.groups.forms import *
from basic.tools.shortcuts import render, redirect


def page_list(request, slug, template_name='groups/pages/page_list.html'):
    """
    Returns a list of pages for a group.

    Templates: ``groups/pages/page_list.html``
    Context:
        group
            Group object
        page_list
            List of GroupPage objects
    """
    group = get_object_or_404(Group, slug=slug)
    return render(request, template_name, {
        'group': group,
        'page_list': group.pages.all()
    })


def page_detail(request, slug, page_slug,
        template_name='groups/pages/page_detail.html'):
    """
    Returns a group page.

    Templates: ``groups/pages/page_detail.html``
    Context:
        group
            Group object
        page
            GroupPage object
    """
    group = get_object_or_404(Group, slug=slug)
    page = get_object_or_404(GroupPage, group=group, slug=page_slug)
    return render(request, template_name, {
        'group': group,
        'page': page
    })


@ownership_required
def page_create(request, slug, template_name='groups/pages/page_form.html'):
    """
    Creates a group page.

    Templates: ``groups/pages/page_form.html``
    Context:
        group
            Group object
        form
            PageForm object
    """
    group = get_object_or_404(Group, slug=slug)
    form = GroupPageForm(initial={'group': group})

    if request.method == 'POST':
        form = GroupPageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.group = group
            page.save()
            return redirect(request, page)

    return render(request, template_name, {
        'group': group,
        'form': form
    })


@ownership_required
def page_edit(request, slug, page_slug,
        template_name='groups/pages/page_form.html'):
    group = get_object_or_404(Group, slug=slug)
    page = get_object_or_404(GroupPage, group=group, slug=page_slug)
    form = GroupPageForm(instance=page)

    if request.method == 'POST':
        form = GroupPageForm(request.POST, instance=page)
        if form.is_valid():
            page = form.save()
            return redirect(request, page)

    return render(request, template_name, {
        'group': group,
        'page': page,
        'form': form
    })


@ownership_required
def page_remove(request, slug, page_slug,
        template_name='groups/pages/page_remove_confirm.html'):
    group = get_object_or_404(Group, slug=slug)
    page = get_object_or_404(GroupPage, group=group, slug=page_slug)

    if request.method == 'POST':
        page.delete()
        return redirect(request, group)

    return render(request, template_name, {
        'group': group,
        'page': page
    })

########NEW FILE########
__FILENAME__ = topics
from django.shortcuts import get_object_or_404

from basic.groups.decorators import *
from basic.groups.models import *
from basic.groups.forms import *
from basic.tools.shortcuts import render, redirect


def topic_list(request, slug, template_name='groups/topics/topic_list.html'):
    """
    Returns a group topic list page.

    Templates: ``groups/topics/topic_list.html``
    Context:
        group
            Group object
        topic_list
            GroupTopic object list
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    topic_list = GroupTopic.objects.filter(group=group, is_active=True)
    return render(request, template_name, {
        'group': group,
        'topic_list': topic_list
    })


@membership_required
def topic_create(request, slug, template_name='groups/topics/topic_form.html'):
    """
    Returns a group topic form page.

    Templates: ``groups/topics/topic_form.html``
    Context:
        form
            GroupTopicForm object
    """
    group = get_object_or_404(Group, slug=slug)
    if request.method == 'POST':
        form = GroupTopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.user = request.user
            topic.group = group
            topic.save()
            return redirect(request, topic)
    else:
        form = GroupTopicForm()
    return render(request, template_name, {
        'form': form,
        'group': group
    })


def topic_detail(request, slug, topic_id,
        template_name='groups/topics/topic_detail.html'):
    """
    Returns a group topic detail page.

    Templates: ``groups/topics/topic_detail.html``
    Context:
        topic
            GroupTopic object
        group
            Group object
    """
    group = get_object_or_404(Group, slug=slug, is_active=True)
    topic = get_object_or_404(GroupTopic, pk=topic_id, is_active=True)
    message_form = GroupMessageForm()
    return render(request, template_name, {
        'group': group,
        'topic': topic,
        'message_form': message_form,
    })


@membership_required
def topic_edit(request, slug, topic_id,
        template_name='groups/topics/topic_form.html'):
    """
    Returns a group topic form page.

    Templates: ``groups/topics/topic_form.html``
    Context:
        form
            GroupTopicForm object
        topic
            GroupTopic object
    """
    group = get_object_or_404(Group, slug=slug)
    topic = get_object_or_404(GroupTopic, pk=topic_id, group=group, user=request.user)
    if request.method == 'POST':
        form = GroupTopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            return redirect(request, topic)
    else:
        form = GroupTopicForm(instance=topic)
    return render(request, template_name, {
        'form': form,
        'group': group,
        'topic': topic
    })


@membership_required
def topic_remove(request, slug, topic_id,
        template_name='groups/topics/topic_remove_confirm.html'):
    """
    Returns a group topic delete confirmation page.

    Templates: ``groups/topics/topic_remove_confirm.html``
    Context:
        topic
            GroupTopic object
    """
    group = get_object_or_404(Group, slug=slug)
    topic = get_object_or_404(GroupTopic, pk=topic_id, group=group, user=request.user)
    if request.method == 'POST':
        topic.is_active = False
        topic.save()
        return redirect(request, group)
    return render(request, template_name, {'topic': topic})

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.inlines.models import *


admin.site.register(InlineType)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType


class InlineType(models.Model):
    """InlineType model"""
    title = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType)

    class Meta:
        db_table = 'inline_types'

    def __unicode__(self):
        return self.title
########NEW FILE########
__FILENAME__ = parser
from django.template import TemplateSyntaxError
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils.encoding import smart_unicode
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def inlines(value, return_list=False):
    try:
        from BeautifulSoup import BeautifulStoneSoup
    except ImportError:
        from beautifulsoup import BeautifulStoneSoup

    content = BeautifulStoneSoup(value, selfClosingTags=['inline','img','br','input','meta','link','hr'])
    inline_list = []

    if return_list:
        for inline in content.findAll('inline'):
            rendered_inline = render_inline(inline)
            inline_list.append(rendered_inline['context'])
        return inline_list
    else:
        for inline in content.findAll('inline'):
            rendered_inline = render_inline(inline)
            if rendered_inline:
                inline.replaceWith(render_to_string(rendered_inline['template'], rendered_inline['context']))
            else:
                inline.replaceWith('')
        return mark_safe(content)


def render_inline(inline):
    """
    Replace inline markup with template markup that matches the
    appropriate app and model.

    """

    # Look for inline type, 'app.model'
    try:
        app_label, model_name = inline['type'].split('.')
    except:
        if settings.DEBUG:
            raise TemplateSyntaxError, "Couldn't find the attribute 'type' in the <inline> tag."
        else:
            return ''

    # Look for content type
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model = content_type.model_class()
    except ContentType.DoesNotExist:
        if settings.DEBUG:
            raise TemplateSyntaxError, "Inline ContentType not found."
        else:
            return ''

    # Check for an inline class attribute
    try:
        inline_class = smart_unicode(inline['class'])
    except:
        inline_class = ''

    try:
        try:
            id_list = [int(i) for i in inline['ids'].split(',')]
            obj_list = model.objects.in_bulk(id_list)
            obj_list = list(obj_list[int(i)] for i in id_list)
            context = { 'object_list': obj_list, 'class': inline_class }
        except ValueError:
            if settings.DEBUG:
                raise ValueError, "The <inline> ids attribute is missing or invalid."
            else:
                return ''
    except KeyError:
        try:
            obj = model.objects.get(pk=inline['id'])
            context = { 'content_type':"%s.%s" % (app_label, model_name), 'object': obj, 'class': inline_class, 'settings': settings }
        except model.DoesNotExist:
            if settings.DEBUG:
                raise model.DoesNotExist, "%s with pk of '%s' does not exist" % (model_name, inline['id'])
            else:
                return ''
        except:
            if settings.DEBUG:
                raise TemplateSyntaxError, "The <inline> id attribute is missing or invalid."
            else:
                return ''

    template = ["inlines/%s_%s.html" % (app_label, model_name), "inlines/default.html"]
    rendered_inline = {'template':template, 'context':context}

    return rendered_inline
########NEW FILE########
__FILENAME__ = inlines
from django import template
from basic.inlines.parser import inlines
from basic.inlines.models import InlineType
import re

register = template.Library()


@register.filter
def render_inlines(value):
    """
    Renders inlines in a ``Post`` by passing them through inline templates.

    Template Syntax::

        {{ post.body|render_inlines|markdown:"safe" }}

    Inline Syntax (singular)::

        <inline type="<app_name>.<model_name>" id="<id>" class="med_left" />

    Inline Syntax (plural)::

        <inline type="<app_name>.<model_name>" ids="<id>, <id>, <id>" />

    An inline template will be used to render the inline. Templates will be
    locaed in the following maner:

        ``inlines/<app_name>_<model_name>.html``

    The template will be passed the following context:

        ``object``
            An object for the corresponding passed id.

    or

        ``object_list``
            A list of objects for the corresponding ids.

    It would be wise to anticipate both object_list and object unless
    you know for sure one or the other will only be present.
    """
    return inlines(value)

@register.filter
def extract_inlines(value):
    return inlines(value, True)


class InlineTypes(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        types = InlineType.objects.all()
        context[self.var_name] = types
        return ''

@register.tag(name='get_inline_types')
def do_get_inline_types(parser, token):
    """
    Gets all inline types.

    Syntax::

        {% get_inline_types as [var_name] %}

    Example usage::

        {% get_inline_types as inline_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m = re.search(r'as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    var_name = m.groups()[0]
    return InlineTypes(var_name)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from basic.invitations.models import Invitation, InvitationAllotment


class InvitationAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'email', 'name', 'status', 'created')
    list_filter = ('status',)
    raw_id_fields = ('from_user',)
admin.site.register(Invitation, InvitationAdmin)


class InvitationAllotmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount')
    raw_id_fields = ('user',)
admin.site.register(InvitationAllotment, InvitationAllotmentAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User

from basic.invitations.models import Invitation


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        exclude = ('status', 'from_user', 'site', 'token')

########NEW FILE########
__FILENAME__ = models
import random

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.hashcompat import sha_constructor

INVITATION_ALLOTMENT = getattr(settings, 'INVITATION_ALLOTMENT', 5)

INVITATION_STATUS_SENT = 0
INVITATION_STATUS_ACCEPTED = 1
INVITATION_STATUS_DECLINED = 2
INVITATION_STATUS_CHOICES = (
    (INVITATION_STATUS_SENT, 'Sent'),
    (INVITATION_STATUS_DECLINED, 'Accepted'),
    (INVITATION_STATUS_DECLINED, 'Declined'),
)


class InvitationManager(models.Manager):
    def get_invitation(self, token):
        try:
            return self.get(token=token, status=INVITATION_STATUS_SENT)
        except self.model.DoesNotExist:
            return False

    def create_token(self, email):
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        token = sha_constructor(salt+email).hexdigest()
        return token


class Invitation(models.Model):
    """ Invitation model """
    from_user = models.ForeignKey(User)
    token = models.CharField(max_length=40)
    name = models.CharField(blank=True, max_length=100)
    email = models.EmailField()
    message = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(choices=INVITATION_STATUS_CHOICES, default=0)
    site = models.ForeignKey(Site, default=settings.SITE_ID)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    objects = InvitationManager()

    def __unicode__(self):
        return '<Invite>'

    @models.permalink
    def get_absolute_url(self):
        return ('invitations:invitation', [self.token])


class InvitationAllotment(models.Model):
    """ InvitationAllotment model """
    user = models.OneToOneField(User, related_name='invitation_allotment')
    amount = models.IntegerField(default=INVITATION_ALLOTMENT)
    site = models.ForeignKey(Site, default=settings.SITE_ID)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '<Invitation Allotment>'

    def decrement(self, amount=1):
        self.amount = self.amount - amount
        self.save()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from basic.invitations.models import *


class InvitationTestCase(TestCase):
    fixtures = ['users.json', 'invitations.json']

    def setUp(self):
        self.user = User.objects.get(username='nathanb')
        self.client.login(username=self.user.username, password='n')

    def test_invitations(self):
        response = self.client.get(reverse('invitations:create'))
        self.assertEqual(response.status_code, 200)

        post = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'message': 'Test message',
        }
        response = self.client.post(reverse('invitations:create'), post)
        self.assertEqual(response.status_code, 200)

        invitation = Invitation.objects.get(pk=1)

        response = self.client.get(invitation.get_absolute_url())
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


urlpatterns = patterns('basic.invitations.views',
    url(r'^send/$',
        view='invitation_create',
        name='create'),

    url(r'^(?P<token>\w+)/$',
        view='invitation_detail',
        name='invitation'),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.sites.models import Site

from basic.invitations.models import Invitation, InvitationAllotment
from basic.invitations.forms import InvitationForm
from basic.tools.shortcuts import render, redirect

from registration.views import register


@login_required
def invitation_create(request, template_name='invitations/invitation_form.html',
        success_template_name='invitations/invitation_success.html'):
    """
    Returns a form for a user to send an invitation.

    Templates:
        ``invitations/invitation_form.html``
        ``invitations/invitation_success.html``

    Context:
        form
            InvitationForm object
    """
    try:
        allotment = request.user.invitation_allotment
        if allotment.amount == 0:
            return invitation_error(request)
    except InvitationAllotment.DoesNotExist:
        return invitation_error(request)

    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.token = Invitation.objects.create_token(invitation.email)
            invitation.from_user = request.user
            invitation.save()

            # Reduce user's invitation allotment
            allotment.decrement(1)

            # Send invitation email
            send_invitation_email(invitation)
            return render(request, success_template_name)
    else:
        form = InvitationForm()

    return render(request, template_name, {'form': form})


@login_required
def invitation_error(request, error_message='You do not have any invitations at this time.',
        template_name='invitations/invitation_error.html'):
    """
    Returns an error template.

    Template: ``invitations/invitation_error.html``

    Context:
        error_message
            String containing the error message.
    """
    return render(request, template_name, {
        'error_message': error_message
    })


def invitation_detail(request, token):
    """
    Returns a sign up form via the django-registration app if the URL is valid.
    """
    invitation = Invitation.objects.get_invitation(token)
    if not invitation:
        return invitation_error(request, "This invitation is no longer valid.")

    backend = getattr(settings, 'REGISTRATION_BACKEND', 'registration.backends.default.DefaultBackend')
    return register(request, backend)


def send_invitation_email(invitation):
    site = Site.objects.get_current()
    context = {'invitation': invitation, 'site': site}
    subject = render_to_string('invitations/invitation_subject.txt', context)
    message = render_to_string('invitations/invitation_message.txt', context)

    INVITATION_FROM_EMAIL = getattr(settings, 'INVITATION_FROM_EMAIL', '')

    email = EmailMessage(subject, message, INVITATION_FROM_EMAIL, ['%s' % invitation.email])
    email.send(fail_silently=True)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.media.models import *


class AudioSetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(AudioSet, AudioSetAdmin)


class AudioAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Audio, AudioAdmin)


class PhotoSetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(PhotoSet, PhotoSetAdmin)


class PhotoAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Photo, PhotoAdmin)


class VideoSetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(VideoSet, VideoSetAdmin)


class VideoAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Video, VideoAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import permalink
from django.conf import settings
from tagging.fields import TagField

import tagging


class AudioSet(models.Model):
    """AudioSet model"""
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    audios = models.ManyToManyField('Audio', related_name='audio_sets')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_audio_sets'

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('audio_set_detail', None, { 'slug': self.slug })


class Audio(models.Model):
    """Audio model"""
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    still = models.FileField(upload_to='audio_stills', blank=True, help_text='An image that will be used as a thumbnail.')
    audio = models.FilePathField(path=settings.MEDIA_ROOT+'audios/', recursive=True)
    description = models.TextField(blank=True)
    tags = TagField()
    uploaded = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_audio'
        verbose_name_plural = 'audios'

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
      return ('audio_detail', None, { 'slug': self.slug })


class PhotoSet(models.Model):
    """PhotoSet model"""
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    cover_photo = models.ForeignKey('Photo', blank=True, null=True)
    photos = models.ManyToManyField('Photo', related_name='photo_sets')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
      db_table = 'media_photo_sets'

    def __unicode__(self):
      return '%s' % self.title

    @permalink
    def get_absolute_url(self):
      return ('photo_set_detail', None, { 'slug': self.slug })


class Photo(models.Model):
    """Photo model"""
    LICENSES = (
        ('http://creativecommons.org/licenses/by/2.0/',         'CC Attribution'),
        ('http://creativecommons.org/licenses/by-nd/2.0/',      'CC Attribution-NoDerivs'),
        ('http://creativecommons.org/licenses/by-nc-nd/2.0/',   'CC Attribution-NonCommercial-NoDerivs'),
        ('http://creativecommons.org/licenses/by-nc/2.0/',      'CC Attribution-NonCommercial'),
        ('http://creativecommons.org/licenses/by-nc-sa/2.0/',   'CC Attribution-NonCommercial-ShareAlike'),
        ('http://creativecommons.org/licenses/by-sa/2.0/',      'CC Attribution-ShareAlike'),
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    photo = models.FileField(upload_to="photos")
    taken_by = models.CharField(max_length=100, blank=True)
    license = models.URLField(blank=True, choices=LICENSES)
    description = models.TextField(blank=True)
    tags = TagField()
    uploaded = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    _exif = models.TextField(blank=True) 

    class Meta:
        db_table = 'media_photos'

    def _set_exif(self, d):
        self._exif = simplejson.dumps(d)

    def _get_exif(self):
        if self._exif:
            return simplejson.loads(self._exif)
        else:
            return {}

    exif = property(_get_exif, _set_exif, "Photo EXIF data, as a dict.")

    def __unicode__(self):
        return '%s' % self.title

    @property
    def url(self):
        return '%s%s' % (settings.MEDIA_URL, self.photo)

    @permalink
    def get_absolute_url(self):
        return ('photo_detail', None, { 'slug': self.slug })


class VideoSet(models.Model):
    """VideoSet model"""
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    videos = models.ManyToManyField('Video', related_name='video_sets')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_video_sets'

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('video_set_detail', None, { 'slug': self.slug })


class Video(models.Model):
    """Video model"""
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    still = models.FileField(upload_to='video_stills', blank=True, help_text='An image that will be used as a thumbnail.')
    video = models.FilePathField(path=settings.MEDIA_ROOT+'videos/', recursive=True)
    description = models.TextField(blank=True)
    tags = TagField()
    uploaded = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_videos'

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('video_detail', None, { 'slug': self.slug })
########NEW FILE########
__FILENAME__ = photos
from django.conf.urls.defaults import *
from basic.media.models import *


photo_list = {
    'queryset': Photo.objects.all(),
}
photo_set_list = {
    'queryset': PhotoSet.objects.all(),
}


urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^sets/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=photo_set_list,
        name='photo_set_detail',
    ),
    url (r'^sets/$',
        view='object_list',
        kwargs=photo_set_list,
        name='photo_set_list',
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=photo_list,
        name='photo_detail',
    ),
    url (r'^$',
        view='object_list',
        kwargs=photo_list,
        name='photo_list',
    ),
)
########NEW FILE########
__FILENAME__ = videos
from django.conf.urls.defaults import *
from basic.media.models import *


video_list = {
    'queryset': Video.objects.all(),
}
video_set_list = {
    'queryset': VideoSet.objects.all(),
}


urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^sets/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=video_set_list,
        name='video_set_detail',
    ),
    url(r'^sets/$',
        view='object_list',
        kwargs=video_set_list,
        name='video_set_list',
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=video_list,
        name='video_detail',
    ),
    url (r'^$',
        view='object_list',
        kwargs=video_list,
        name='video_list',
    ),
)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.messages.models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'subject', 'to_status', 'from_status', 'created', 'content_type', 'object_id')
admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User

from basic.messages.models import Message


class MessageForm(forms.ModelForm):
    to_user = forms.CharField()

    class Meta:
        model = Message
        exclude = ('to_status', 'from_status', 'from_user', 'object_id', 'content_type')

    def clean_to_user(self):
        if self.cleaned_data['to_user']:
            try:
                user = User.objects.get(username=self.cleaned_data['to_user'])
                self.cleaned_data['to_user'] = user
                return self.cleaned_data['to_user']
            except User.DoesNotExist:
                pass
        raise forms.ValidationError(u'There are no users with this username.')

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink, Manager, Q
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

FROM_STATUS_DRAFT = 0
FROM_STATUS_SENT = 1
FROM_STATUS_DELETED = 2

TO_STATUS_NEW = 0
TO_STATUS_READ = 1
TO_STATUS_REPLIED = 2
TO_STATUS_DELETED = 3


class MessageManager(Manager):
    """Returns messages according to message status"""

    def new(self, user):
        return self.filter(to_user=user, to_status=TO_STATUS_NEW)

    def sent(self, user):
        return self.filter(from_user=user, from_status=FROM_STATUS_SENT)

    def trash(self, user):
        return self.filter(Q(to_user=user, to_status=TO_STATUS_DELETED) |
            Q(from_user=user, from_status=FROM_STATUS_DELETED))

    def archive(self, user):
        return self.filter(to_user=user).exclude(to_status=TO_STATUS_DELETED)


class Message(models.Model):
    """ Message model """
    FROM_STATUS_CHOICES = (
        (FROM_STATUS_DRAFT, 'Draft'),
        (FROM_STATUS_SENT, 'Sent'),
        (FROM_STATUS_DELETED, 'Deleted')
    )
    TO_STATUS_CHOICES = (
        (TO_STATUS_NEW, 'New'),
        (TO_STATUS_READ, 'Read'),
        (TO_STATUS_REPLIED, 'Replied'),
        (TO_STATUS_DELETED, 'Deleted')
    )
    from_user = models.ForeignKey(User, related_name='sent_messages')
    to_user = models.ForeignKey(User, related_name='messages')
    from_status = models.PositiveSmallIntegerField(choices=FROM_STATUS_CHOICES, blank=True, null=True, default=1)
    to_status = models.PositiveSmallIntegerField(choices=TO_STATUS_CHOICES, blank=True, null=True, default=0)
    subject = models.CharField(blank=True, max_length=255)
    message = models.TextField(blank=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    objects = MessageManager()

    content_type = models.ForeignKey(ContentType, blank=True, null=True, related_name='messages')
    object_id = models.IntegerField(blank=True, null=True)
    object = GenericForeignKey()

    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        db_table = 'messages'
        ordering = ('-id',)

    def __unicode__(self):
        return u'Message from %s' % self.from_user.username

    @permalink
    def get_absolute_url(self):
        return ('messages:message', None, {'object_id': self.pk})

    @property
    def is_new(self):
        if self.to_status == TO_STATUS_NEW:
            return True
        return False

    def save(self, *args, **kwargs):
        super(Message, self).save(*args, **kwargs)
        if not self.object:
            self.object = self
            self.save()

########NEW FILE########
__FILENAME__ = messages
from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models

from basic.tools.templatetags.utils import parse_ttag
from basic.tools.baseconv import base62

Message = models.get_model('messages', 'message')
register = template.Library()


@register.simple_tag
def message_url(obj):
    """
    Given an object, returns its "message to" URL.
    
    Example::
    
        {% message_url obj %}
        
    """
    try:
        content_type = ContentType.objects.get(app_label=obj._meta.app_label, model=obj._meta.module_name)
        return reverse('messages:create', kwargs={
                'content_type_id': base62.from_decimal(content_type.pk),
                'object_id': base62.from_decimal(obj.pk)
                })
    except AttributeError:
        return ''


class GetMessages(template.Node):
    def __init__(self, object_name, varname):
        self.object_name = object_name
        self.varname = varname

    def render(self, context):
        obj = template.resolve_variable(self.object_name, context)
        ctype = ContentType.objects.get_for_model(obj)
        message_list = Message.objects.filter(object_id=obj.id, content_type=ctype).order_by('id')
        context[self.varname] = message_list
        return ''

def do_get_messages(parser, token):
    """
    Get messages for an object.

    Syntax:
        {% get_messages for [object] as [varname] %}

    Example:
        {% get_messages for object as message_list %}
    """
    tags = parse_ttag(token, ['for', 'as'])
    if len(tags) != 3:
        raise template.TemplateSyntaxError, '%r tag has invalid arguments' % tags['tag_name']
    return GetMessages(object_name=tags['for'], varname=tags['as'])

register.tag('get_messages', do_get_messages)
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from basic.messages.models import *


class MessageTestCase(TestCase):
    fixtures = ['users.json']
    
    def setUp(self):
        self.user1 = User.objects.get(username='nathanb')
        self.user2 = User.objects.get(username='laurah')
        
    def test_messages(self):
        self.client.login(username=self.user1.username, password='n')
        
        response = self.client.get(reverse('messages:messages'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('messages:create'))
        self.assertEqual(response.status_code, 200)
        
        post = {
            'to_user': 'laurah',
            'subject': 'Test subject',
            'message': 'Test message',
        }
        response = self.client.post(reverse('messages:create'), post)
        self.assertEqual(response.status_code, 302)
        
        response = self.client.get(reverse('messages:messages', kwargs={'mailbox': 'sent'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context[0]['message_list']), '[<Message: Message from nathanb>]')
        self.assertEqual(str(response.context[0]['mailbox']), 'sent')
        
        self.client.login(username=self.user2.username, password='l')
        
        response = self.client.get(reverse('messages:messages'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context[0]['message_list']), '[<Message: Message from nathanb>]')
        self.assertEqual(str(response.context[0]['mailbox']), 'archive')
        
        message = response.context[0]['message_list'][0]
        response = self.client.get(message.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('messages:reply', kwargs={'object_id': message.pk}))
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


urlpatterns = patterns('basic.messages.views',
    url(r'(?P<mailbox>inbox|trash|sent)/$',
        view='message_list',
        name='messages'),

    url(r'compose(?:/(?P<content_type_id>\w+):(?P<object_id>\w+))?/$',
        view='message_create',
        name='create'),

    url(r'remove/(?P<object_id>\d+)/$',
        view='message_remove',
        name='remove'),

    url(r'(?P<object_id>\d+)/reply/$',
        view='message_reply',
        name='reply'),

    url(r'(?:(?P<mailbox>inbox|trash|sent)/)?(?P<object_id>\d+)/$',
        view='message_detail',
        name='message'),

    url(r'',
        view='message_list',
        name='messages'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404, HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

from basic.messages.models import Message, TO_STATUS_READ, TO_STATUS_DELETED, FROM_STATUS_DELETED
from basic.messages.forms import MessageForm
from basic.tools.baseconv import base62

@login_required
def message_list(request, mailbox=None, template_name='messages/message_list.html'):
    """
    Returns a list of user messages.

    Template:: ``messages/message_list.html``
    Context:
        message_list
            List of Message objects
        mailbox
            String representing the current 'mailbox'
    """
    message_list = _get_messages(request.user, mailbox)
    return render_to_response(template_name, {
        'message_list': message_list,
        'mailbox': mailbox or 'archive'
    }, context_instance=RequestContext(request))


@login_required
def message_create(request, content_type_id=None, object_id=None, 
                    template_name='messages/message_form.html'):
    """
    Handles a new message and displays a form.

    Template:: ``messages/message_form.html``
    Context:
        form
            MessageForm object
    """
    next = request.GET.get('next', None)
    if request.GET.get('to', None):
        to_user = get_object_or_404(User, username=request.GET['to'])
    else:
        to_user = None
    
    if content_type_id and object_id:
        content_type = ContentType.objects.get(pk=base62.to_decimal(content_type_id))
        Model = content_type.model_class()
        try:
            related_object = Model.objects.get(pk=base62.to_decimal(object_id))
        except ObjectDoesNotExist:
            raise Http404, "The object ID was invalid."
    else:
        related_object = None
    
    form = MessageForm(request.POST or None, initial={'to_user': to_user})
    if form.is_valid():
        message = form.save(commit=False)
        if related_object:
            message.object = related_object
        message.from_user = request.user
        message = form.save()
        return HttpResponseRedirect(next or reverse('messages:messages'))
    return render_to_response(template_name, {
        'form': form,
        'to_user': to_user,
        'related_object': related_object,
        'next': next,
    }, context_instance=RequestContext(request))


def message_reply(request, object_id, template_name='messages/message_form.html'):
    """
    Handles a reply to a specific message.
    """
    original_message = get_object_or_404(Message, pk=object_id)
    next = request.GET.get('next', None)
    initial = {
        'to_user': original_message.from_user,
        'subject': 'Re: %s' % original_message.subject
    }
    form = MessageForm(request.POST or None, initial=initial)
    if form.is_valid():
        message = form.save(commit=False)
        message.object = original_message.object
        message.from_user = request.user
        message = form.save()
        return HttpResponseRedirect(next or reverse('messages:messages'))
    return render_to_response(template_name, {
        'form': form,
        'message': original_message,
        'next': next,
    }, context_instance=RequestContext(request))


@login_required
def message_remove(request, object_id, template_name='messages/message_remove_confirm.html'):
    """
    Remove a message.
    """
    message = get_object_or_404(Message, pk=object_id)
    next = request.GET.get('next', None)
    if request.method == 'POST':
        if message.to_user == request.user:
            message.to_status = TO_STATUS_DELETED
        else:
            message.from_status = FROM_STATUS_DELETED
        message.save()
        return HttpResponseRedirect(next or reverse('messages:messages'))
    return render_to_response(template_name, {
        'message': message,
        'next': next,
    }, context_instance=RequestContext(request))


@login_required
def message_detail(request, object_id, mailbox=None, template_name='messages/message_detail.html'):
    """
    Return a message.
    """
    message = get_object_or_404(Message, pk=object_id)
    content_type = ContentType.objects.get_for_model(message)
    thread_list = Message.objects.filter(object_id=message.object.pk, content_type=content_type).order_by('id')
    message_list = _get_messages(request.user, mailbox)
    if message.to_user == request.user:
        message.to_status = TO_STATUS_READ
        message.save()
    return render_to_response(template_name, {
        'message': message,
        'thread_list': thread_list,
        'message_list': message_list,
    }, context_instance=RequestContext(request))


def _get_messages(user, mailbox):
    if mailbox == 'sent':
        return Message.objects.sent(user)
    elif mailbox == 'trash':
        return Message.objects.trash(user)
    else:
        return Message.objects.archive(user)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.movies.models import *


class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Genre, GenreAdmin)


class StudioAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Studio, StudioAdmin)


class MovieAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Movie, MovieAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import permalink
from django.conf import settings
from basic.people.models import Person


class Genre(models.Model):
    """Genre model"""
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'movie_genres'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('movie_genre_detail', None, { 'slug': self.slug })


class Studio(models.Model):
    """Studio model"""
    title = models.CharField(max_length=100)
    prefix = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = 'movie_studios'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('movie_studio_detail', None, { 'slug': self.slug })


class Movie(models.Model):
    """Movie model"""
    title = models.CharField(max_length=255)
    prefix = models.CharField(max_length=20, blank=True)
    subtitle = models.CharField(blank=True, max_length=255)
    slug = models.SlugField(unique=True)
    directors = models.ManyToManyField(Person, limit_choices_to={'person_types__slug__exact': 'director'}, blank=True)
    studio = models.ForeignKey(Studio, blank=True, null=True)
    released = models.DateField(blank=True, null=True)
    asin = models.CharField(blank=True, max_length=100)
    cover = models.FileField(upload_to='films', blank=True)
    review = models.TextField(blank=True)
    genre = models.ManyToManyField(Genre, blank=True)

    class Meta:
        db_table = 'movies'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('movie_detail', None, { 'slug': self.slug })

    @property
    def amazon_url(self):
        try:
            return 'http://www.amazon.com/dp/%s/?%s' % (self.asin, settings.AMAZON_AFFILIATE_EXTENTION)
        except:
            return 'http://www.amazon.com/dp/%s/' % self.asin

    @property
    def cover_url(self):
        return '%s%s' % (settings.MEDIA_URL, self.cover)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from basic.movies.models import *


genre_list = {
    'queryset': Genre.objects.all(),
}
movie_list = {
    'queryset': Movie.objects.all(),
}
studio_list = {
    'queryset': Studio.objects.all(),
}


urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^genres/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=genre_list,
        name='movie_genre_detail',
    ),
    url (r'^genres/$',
        view='object_list',
        kwargs=genre_list,
        name='movie_genre_list',
    ),
    url(r'^studios/(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=studio_list,
        name='movie_studio_detail',
    ),
    url (r'^studios/$',
        view='object_list',
        kwargs=studio_list,
        name='movie_studio_list',
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='object_detail',
        kwargs=movie_list,
        name='movie_detail',
    ),
    url (r'^$',
        view='object_list',
        kwargs=movie_list,
        name='movie_list',
    ),
)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.music.models import *


class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Genre, GenreAdmin)


class LabelAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Label, LabelAdmin)


class BandAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Band, BandAdmin)


class AlbumAdmin(admin.ModelAdmin):
    list_display  = ('title', 'band',)
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Album, AlbumAdmin)


class TrackAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Track, TrackAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import permalink
from django.conf import settings
from basic.people.models import Person


class Genre(models.Model):
    """Genre model"""
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'music_genres'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('music_genre_detail', None, { 'slug': self.slug })


class Label(models.Model):
    """Label model"""
    title = models.CharField(max_length=100)
    prefix = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = 'music_labels'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('music_label_detail', None, { 'slug': self.slug })


class Band(models.Model):
    """Band model"""
    title = models.CharField(max_length=100)
    prefix = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    musicians = models.ManyToManyField(Person, blank=True, limit_choices_to={'person_types__slug__exact': 'musician'})
    website = models.URLField(blank=True)

    class Meta:
        db_table = 'music_bands'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('music_band_detail', None, { 'slug': self.slug })


class Album(models.Model):
    """Album model"""
    title = models.CharField(max_length=255)
    prefix = models.CharField(max_length=20, blank=True)
    subtitle = models.CharField(blank=True, max_length=255)
    slug = models.SlugField()
    band = models.ForeignKey(Band, blank=True)
    label = models.ForeignKey(Label, blank=True)
    asin = models.CharField(max_length=14, blank=True)
    release_date = models.DateField(blank=True, null=True)
    cover = models.FileField(upload_to='albums', blank=True)
    review = models.TextField(blank=True)
    genre = models.ManyToManyField(Genre, blank=True)
    is_ep = models.BooleanField(default=False)
    is_compilation = models.BooleanField(default=False)

    class Meta:
        db_table = 'music_albums'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @permalink
    def get_absolute_url(self):
        return ('music_album_detail', None, { 'slug': self.slug })

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @property
    def cover_url(self):
        return '%s%s' % (settings.MEDIA_URL, self.cover)

    @property
    def amazon_url(self):
        try:
            return 'http://www.amazon.com/dp/%s/?%s' % (self.asin, settings.AMAZON_AFFILIATE_EXTENTION)
        except:
            return 'http://www.amazon.com/dp/%s/' % self.asin


class Track(models.Model):
    """Tracks model"""
    album = models.ForeignKey(Album, blank=True, null=True, related_name='tracks')
    band = models.ForeignKey(Band, blank=True, null=True, related_name='tracks')
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    mp3 = models.FilePathField(path=settings.MEDIA_ROOT+'tracks', match='.*\.mp3$')

    class Meta:
        db_table = 'music_tracks'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('music_track_detail', None, { 'slug': self.slug })

    @property
    def mp3_url(self):
        return self.mp3.replace(settings.MEDIA_ROOT, settings.MEDIA_URL)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('basic.music.views',
    url(r'^genres/(?P<slug>[-\w]+)/$',
        view='genre_detail',
        name='music_genre_detail',
    ),
    url (r'^genres/$',
        view='genre_list',
        name='music_genre_list',
    ),
    url(r'^labels/(?P<slug>[-\w]+)/$',
        view='label_detail',
        name='music_label_detail',
    ),
    url (r'^labels/$',
        view='label_list',
        name='music_label_list',
    ),
    url(r'^bands/(?P<slug>[-\w]+)/$',
        view='band_detail',
        name='music_band_detail',
    ),
    url (r'^bands/$',
        view='band_list',
        name='music_band_list',
    ),
    url(r'^albums/(?P<slug>[-\w]+)/$',
        view='album_detail',
        name='music_album_detail',
    ),
    url (r'^albums/$',
        view='album_list',
        name='music_album_list',
    ),
    url(r'^tracks/(?P<slug>[-\w]+)/$',
        view='track_detail',
        name='music_track_detail',
    ),
    url (r'^tracks/$',
        view='track_list',
        name='music_track_list',
    ),
)


urlpatterns += patterns('',
    url (r'^$',
        view='django.views.generic.simple.direct_to_template',
        kwargs={'template': 'music/index.html'},
        name='music_index',
    ),
)
########NEW FILE########
__FILENAME__ = views
from django.views.generic import list_detail
from basic.music.models import *


def genre_detail(request, slug):
  return list_detail.object_detail(
    request,
    queryset=Genre.objects.all(),
    slug=slug,
  )
genre_detail.__doc__ = list_detail.object_detail.__doc__


def genre_list(request):
  return list_detail.object_list(
    request,
    queryset=Genre.objects.all(),
    paginate_by=20,
  )
genre_list.__doc__ = list_detail.object_list.__doc__


def label_detail(request, slug):
  return list_detail.object_detail(
    request,
    queryset=Label.objects.all(),
    slug=slug,
  )
label_detail.__doc__ = list_detail.object_detail.__doc__


def label_list(request):
  return list_detail.object_list(
    request,
    queryset=Label.objects.all(),
    paginate_by=20,
  )
label_list.__doc__ = list_detail.object_list.__doc__


def band_detail(request, slug):
  return list_detail.object_detail(
    request,
    queryset=Band.objects.all(),
    slug=slug,
  )
band_detail.__doc__ = list_detail.object_detail.__doc__


def band_list(request):
  return list_detail.object_list(
    request,
    queryset=Band.objects.all(),
    paginate_by=20,
  )
band_list.__doc__ = list_detail.object_list.__doc__


def album_detail(request, slug):
  return list_detail.object_detail(
    request,
    queryset=Album.objects.all(),
    slug=slug,
  )
album_detail.__doc__ = list_detail.object_detail.__doc__


def album_list(request):
  return list_detail.object_list(
    request,
    queryset=Album.objects.all(),
    paginate_by=20,
  )
album_list.__doc__ = list_detail.object_list.__doc__


def track_detail(request, slug):
  return list_detail.object_detail(
    request,
    queryset=Track.objects.all(),
    slug=slug,
  )
track_detail.__doc__ = list_detail.object_detail.__doc__


def track_list(request):
  return list_detail.object_list(
    request,
    queryset=Track.objects.all(),
    paginate_by=20,
  )
track_list.__doc__ = list_detail.object_list.__doc__
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.people.models import *


class PersonTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(PersonType, PersonTypeAdmin)


class PersonAdmin(admin.ModelAdmin):
    list_filter = ('person_types',)
    search_fields = ('first_name', 'last_name')
    prepopulated_fields = {'slug': ('first_name','last_name')}
admin.site.register(Person, PersonAdmin)


class QuoteAdmin(admin.ModelAdmin):
    list_display = ('person','quote')
    list_filter = ('person',)
    search_fields = ('quote',)
admin.site.register(Quote, QuoteAdmin)


class ConversationItemInline(admin.StackedInline):
    model = ConversationItem
    fk = 'conversation'


class ConversationAdmin(admin.ModelAdmin):
    inlines = [
        ConversationItemInline
    ]
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(ConversationItem)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models import permalink
from django.contrib.auth.models import User
from tagging.fields import TagField

import datetime
import dateutil


class PersonType(models.Model):
    """Person type model."""
    title = models.CharField(_('title'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)

    class Meta:
        verbose_name = _('person type')
        verbose_name_plural = _('person types')
        db_table = 'people_types'
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('person_type_detail', None, {'slug': self.slug})


class Person(models.Model):
    """Person model."""
    GENDER_CHOICES = (
        (1, 'Male'),
        (2, 'Female'),
    )
    first_name = models.CharField(_('first name'), blank=True, max_length=100)
    middle_name = models.CharField(_('middle name'), blank=True, max_length=100)
    last_name = models.CharField(_('last name'), blank=True, max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    user = models.ForeignKey(User, blank=True, null=True, help_text='If the person is an existing user of your site.')
    gender = models.PositiveSmallIntegerField(_('gender'), choices=GENDER_CHOICES, blank=True, null=True)
    mugshot = models.FileField(_('mugshot'), upload_to='mugshots', blank=True)
    mugshot_credit = models.CharField(_('mugshot credit'), blank=True, max_length=200)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    person_types = models.ManyToManyField(PersonType, blank=True)
    website = models.URLField(_('website'), blank=True)

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('people')
        db_table = 'people'
        ordering = ('last_name', 'first_name',)

    def __unicode__(self):
        return u'%s' % self.full_name

    @property
    def full_name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    @property
    def age(self):
        TODAY = datetime.date.today()
        return u'%s' % dateutil.relativedelta(TODAY, self.birth_date).years

    @permalink
    def get_absolute_url(self):
        return ('person_detail', None, {'slug': self.slug})


class Quote(models.Model):
    """Quote model."""
    person = models.ForeignKey(Person)
    quote = models.TextField(_('quote'))
    source = models.CharField(_('source'), blank=True, max_length=255)

    class Meta:
        verbose_name = 'quote'
        verbose_name_plural = 'quotes'
        db_table = 'people_quotes'

    def __unicode__(self):
        return u'%s' % self.quote

    @permalink
    def get_absolute_url(self):
        return ('quote_detail', None, {'quote_id': self.pk})


class Conversation(models.Model):
    """A conversation between two or many people."""
    title = models.CharField(blank=True, max_length=200)

    def __unicode__(self):
        return self.title


class ConversationItem(models.Model):
    """An item within a conversation."""
    conversation      = models.ForeignKey(Conversation, related_name='items')
    order             = models.PositiveSmallIntegerField()
    speaker           = models.ForeignKey(Person)
    quote             = models.TextField()

    class Meta:
        ordering = ('conversation', 'order')
        unique_together = (('conversation', 'order'),)

    def __unicode__(self):
        return u'%s: %s' % (self.speaker.first_name, self.quote)
########NEW FILE########
__FILENAME__ = people
import re

from django import template
from django.db import models
from django.utils.safestring import mark_safe

Person = models.get_model('people', 'person')

register = template.Library()


class GetPeople(template.Node):
    def __init__(self, var_name, limit=None):
        self.var_name = var_name
        self.limit = limit

    def render(self, context):
        if self.limit:
            people = Person.objects.select_related()[:int(self.limit)]
        else:
            people = Person.objects.all()

        context[self.var_name] = people
        return ''

@register.tag
def get_people(parser, token):
    """
    Gets any number of latest posts and stores them in a varable.

    Syntax::

        {% get_people [limit] as [var_name] %}

    Example usage::

        {% get_people 10 as people_list %}

        {% get_people as people_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m1 = re.search(r'as (\w+)', arg)
    m2 = re.search(r'(.*?) as (\w+)', arg)

    if not m1:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    else:
        var_name = m1.groups()[0]
        return GetPeople(var_name)

    if not m2:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    else:
        format_string, var_name = m2.groups()
        return GetPeople(var_name, format_string[0])
########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.test import Client
>>> from basic.people.models import Person, Quote, PersonType
>>> from django.core.urlresolvers import reverse

>>> c = Client()
>>> p = Person.objects.create(first_name='Nathan', last_name='Borror', slug='nathan-borror')

>>> r = c.get(reverse('person_list'))
>>> r.status_code
200

>>> r = c.get(reverse('person_detail', kwargs={'slug': 'nathan-borror'}))
>>> r.status_code
200
"""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('basic.people.views',
    url(r'^types/(?P<slug>[-\w]+)/$',
        view='person_type_detail',
        name='person_type_detail'
    ),
    url (r'^types/$',
        view='person_type_list',
        name='person_type_list'
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='person_detail',
        name='person_detail'
    ),
    url (r'^$',
        view='person_list',
        name='person_list'
    ),
    url(r'^quotes/(?P<slug>[-\w]+)/$',
        view='person_quote_list',
        name='person_quote_list'
    ),
    url(r'^quote/(?P<quote_id>\d+)/$',
        view='quote_detail',
        name='quote_detail'
    ),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404
from django.views.generic import list_detail
from basic.people.models import *


def person_type_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=PersonType.objects.all(),
        slug=slug,
        **kwargs
    )
person_type_detail.__doc__ = list_detail.object_detail.__doc__


def person_type_list(request, paginate_by=20, **kwargs):
    return list_detail.object_list(
        request,
        queryset=PersonType.objects.all(),
        paginate_by=paginate_by,
        **kwargs
    )
person_type_list.__doc__ = list_detail.object_list.__doc__


def person_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=Person.objects.all(),
        slug=slug,
        **kwargs
    )
person_detail.__doc__ = list_detail.object_detail.__doc__


def person_list(request, paginate_by=20, **kwargs):
    return list_detail.object_list(
        request,
        queryset=Person.objects.all(),
        paginate_by=paginate_by,
        **kwargs
    )
person_list.__doc__ = list_detail.object_list.__doc__


def person_quote_list(request, slug, template_name='people/person_quote_list.html', paginate_by=20, **kwargs):
    person = get_object_or_404(Person, slug__iexact=slug)
    return list_detail.object_list(
        request,
        queryset=person.quote_set.all(),
        paginate_by=paginate_by,
        template_name=template_name,
        extra_context={'person': person},
        **kwargs
    )
person_quote_list.__doc__ = list_detail.object_list.__doc__


def quote_detail(request, quote_id, template_name='people/quote_detail.html', **kwargs):
    return list_detail.object_detail(
        request,
        queryset=Quote.objects.all(),
        object_id=quote_id,
        **kwargs
    )
quote_detail.__doc__ = list_detail.object_detail.__doc__
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.places.models import *


class PlaceTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(PlaceType, PlaceTypeAdmin)


class CityAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('city', 'state')}
admin.site.register(City, CityAdmin)


class PointAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'zip', 'latitude', 'longitude')
    list_filter = ('city',)
    search_fields = ('address',)
admin.site.register(Point, PointAdmin)


class PlaceAdmin(admin.ModelAdmin):
    list_display = ('title', 'point', 'city', 'status')
    list_filter = ('status', 'place_types')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Place, PlaceAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink
from django.contrib.localflavor.us.models import PhoneNumberField
from tagging.fields import TagField

import tagging


class PlaceType(models.Model):
    """Place types model."""
    title = models.CharField(_('title'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), unique=True)

    class Meta:
        verbose_name = _('place type')
        verbose_name_plural = _('place types')
        db_table = 'place_types'

    def __unicode__(self):
        return u'%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('place_type_detail', None, {'slug': self.slug})


class City(models.Model):
    """City model."""
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)

    class Meta:
        verbose_name = _('city')
        verbose_name_plural = _('cities')
        db_table = 'place_cities'
        unique_together = (('city', 'state',),)
        ordering = ('state', 'city',)

    def __unicode__(self):
        return u'%s, %s' % (self.city, self.state)

    @permalink
    def get_absolute_url(self):
        return ('place_city_detail', None, {'slug': self.slug})


class Point(models.Model):
    """Point model."""
    latitude = models.FloatField(_('latitude'), blank=True, null=True)
    longitude = models.FloatField(_('longitude'), blank=True, null=True)
    address = models.CharField(_('address'), max_length=200, blank=True)
    city = models.ForeignKey(City)
    zip = models.CharField(_('zip'), max_length=10, blank=True)
    country = models.CharField(_('country'), blank=True, max_length=100)

    class Meta:
        verbose_name = _('point')
        verbose_name_plural = _('points')
        db_table = 'place_points'
        ordering = ('address',)

    def __unicode__(self):
        return u'%s' % self.address


class Place(models.Model):
    """Place model."""
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (1, 'Active'),
    )
    point = models.ForeignKey(Point)
    prefix = models.CharField(_('Pre-name'), blank=True, max_length=20)
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'))
    nickname = models.CharField(_('nickname'), blank=True, max_length=100)
    unit = models.CharField(_('unit'), blank=True, max_length=100, help_text='Suite or Apartment #')
    phone = PhoneNumberField(_('phone'), blank=True)
    url = models.URLField(_('url'), blank=True)
    email = models.EmailField(_('email'), blank=True)
    description = models.TextField(_('description'), blank=True)
    status = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=1)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    place_types = models.ManyToManyField(PlaceType, blank=True)
    tags = TagField()

    class Meta:
        verbose_name = _('place')
        verbose_name_plural = _('places')
        db_table = 'places'
        ordering = ('title',)

    def __unicode__(self):
        return u'%s' % self.full_title

    @property
    def city(self):
        return u'%s' % self.point.city

    @property
    def full_title(self):
        return u'%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('place_detail', None, { 'slug': self.slug } )

    @property
    def longitude(self):
        return self.point.longitude

    @property
    def latitude(self):
        return self.point.latitude

    @property
    def address(self):
        return u'%s, %s %s' % (self.point.address, self.point.city, self.point.zip)
########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.test import Client
>>> from basic.places.models import PlaceType, City, Point, Place

>>> c = Client()
>>> type = PlaceType.objects.create(title='Coffeehouse', slug='coffeehouse')
>>> city = City.objects.create(city='Lawrence', state='KS', slug='lawrence-ks')
>>> point = Point.objects.create(city=city)
>>> place = Place.objects.create(point=point, title='Wheatfields', slug='wheatfields', status=1)
>>> place.place_types.add(type)
>>> place.save()

>>> r = c.get('/places/')
>>> r.status_code
200

>>> r = c.get('/places/wheatfields/')
>>> r.status_code
200

>>> r = c.get('/places/cities/')
>>> r.status_code
200

>>> r = c.get('/places/cities/lawrence-ks/')
>>> r.status_code
200

>>> r = c.get('/places/types/')
>>> r.status_code
200

>>> r = c.get('/places/types/coffeehouse/')
>>> r.status_code
200
"""
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


urlpatterns = patterns('basic.places.views',
    url(r'^cities/(?P<slug>[-\w]+)/$',
        view='city_detail',
        name='place_city_detail'
    ),
    url(r'^cities/$',
        view='city_list',
        name='place_city_list'
    ),
    url(r'^types/(?P<slug>[-\w]+)/$',
        view='place_type_detail',
        name='place_type_detail'
    ),
    url(r'^types/$',
        view='place_type_list',
        name='place_type_list'
    ),
    url(r'^(?P<slug>[-\w]+)/$',
        view='place_detail',
        name='place_detail'
    ),
    url(r'^$',
        view='place_list',
        name='place_list'
    ),
)
########NEW FILE########
__FILENAME__ = views
from django.views.generic import list_detail
from basic.places.models import *


def city_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=City.objects.all(),
        slug=slug,
        **kwargs
    )
city_detail.__doc__ = list_detail.object_detail.__doc__


def city_list(request, **kwargs):
    return list_detail.object_list(
        request,
        queryset=City.objects.all(),
        paginate_by=20,
        **kwargs
    )
city_list.__doc__ = list_detail.object_list.__doc__


def place_type_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=PlaceType.objects.all(),
        slug=slug,
        **kwargs
    )
place_type_detail.__doc__ = list_detail.object_detail.__doc__


def place_type_list(request, **kwargs):
    return list_detail.object_list(
        request,
        queryset=PlaceType.objects.all(),
        paginate_by=20,
        **kwargs
    )
place_type_list.__doc__ = list_detail.object_list.__doc__


def place_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=Place.objects.all(),
        slug=slug,
        **kwargs
    )
place_detail.__doc__ = list_detail.object_detail.__doc__


def place_list(request, **kwargs):
    return list_detail.object_list(
        request,
        queryset=Place.objects.all(),
        paginate_by=20,
        **kwargs
    )
place_list.__doc__ = list_detail.object_list.__doc__
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from basic.profiles.models import *


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city')
admin.site.register(Profile, ProfileAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('profile', 'service')
    list_filter = ('profile', 'service')
admin.site.register(Service, ServiceAdmin)


admin.site.register(MobileProvider)
admin.site.register(ServiceType)
admin.site.register(Link)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from django.contrib.auth.models import User
from basic.profiles.models import *


class ProfileForm(ModelForm):
    class Meta:
        model = Profile


ServiceFormSet  = inlineformset_factory(Profile, Service)
LinkFormSet     = inlineformset_factory(Profile, Link)


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')
########NEW FILE########
__FILENAME__ = models
import re, datetime
from dateutil import relativedelta

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink
from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import PhoneNumberField


class Profile(models.Model):
    """Profile model"""
    GENDER_CHOICES = (
        (1, 'Male'),
        (2, 'Female'),
    )
    user = models.ForeignKey(User, unique=True)
    gender = models.PositiveSmallIntegerField(_('gender'), choices=GENDER_CHOICES, blank=True, null=True)
    mugshot = models.FileField(_('mugshot'), upload_to='mugshots', blank=True)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    address1 = models.CharField(_('address1'), blank=True, max_length=100)
    address2 = models.CharField(_('address2'), blank=True, max_length=100)
    city = models.CharField(_('city'), blank=True, max_length=100)
    state = models.CharField(_('state'), blank=True, max_length=100, help_text='or Province')
    zip = models.CharField(_('zip'), blank=True, max_length=10)
    country = models.CharField(_('country'), blank=True, max_length=100)
    mobile = PhoneNumberField(_('mobile'), blank=True)
    mobile_provider = models.ForeignKey('MobileProvider', blank=True, null=True)

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
        db_table = 'user_profiles'

    def __unicode__(self):
        return u"%s" % self.user.get_full_name()

    @property
    def age(self):
        TODAY = datetime.date.today()
        if self.birth_date:
            return u"%s" % relativedelta.relativedelta(TODAY, self.birth_date).years
        else:
            return None

    @permalink
    def get_absolute_url(self):
        return ('profile_detail', None, { 'username': self.user.username })

    @property
    def sms_address(self):
        if (self.mobile and self.mobile_provider):
            return u"%s@%s" % (re.sub('-', '', self.mobile), self.mobile_provider.domain)


class MobileProvider(models.Model):
    """MobileProvider model"""
    title = models.CharField(_('title'), max_length=25)
    domain = models.CharField(_('domain'), max_length=50, unique=True)

    class Meta:
        verbose_name = _('mobile provider')
        verbose_name_plural = _('mobile providers')
        db_table = 'user_mobile_providers'

    def __unicode__(self):
        return u"%s" % self.title


class ServiceType(models.Model):
    """Service type model"""
    title = models.CharField(_('title'), blank=True, max_length=100)
    url = models.URLField(_('url'), blank=True, help_text='URL with a single \'{user}\' placeholder to turn a username into a service URL.')

    class Meta:
        verbose_name = _('service type')
        verbose_name_plural = _('service types')
        db_table = 'user_service_types'

    def __unicode__(self):
        return u"%s" % self.title


class Service(models.Model):
    """Service model"""
    service = models.ForeignKey(ServiceType)
    profile = models.ForeignKey(Profile)
    username = models.CharField(_('Name or ID'), max_length=100, help_text="Username or id to be inserted into the service url.")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('service')
        verbose_name_plural = _('services')
        db_table = 'user_services'

    def __unicode__(self):
        return u"%s" % self.username

    @property
    def service_url(self):
        return re.sub('{user}', self.username, self.service.url)

    @property
    def title(self):
        return u"%s" % self.service.title


class Link(models.Model):
    """Service type model"""
    profile = models.ForeignKey(Profile)
    title = models.CharField(_('title'), max_length=100)
    url = models.URLField(_('url'))

    class Meta:
        verbose_name = _('link')
        verbose_name_plural = _('links')
        db_table = 'user_links'

    def __unicode__(self):
        return u"%s" % self.title
########NEW FILE########
__FILENAME__ = profiles
import re

from django import template
from django.db import models
from django.utils.safestring import mark_safe

Profile = models.get_model('profiles', 'profile')

register = template.Library()


class GetProfiles(template.Node):
    def __init__(self, var_name, limit=None):
        self.var_name = var_name
        self.limit = limit

    def render(self, context):
        if self.limit:
            profiles = Profile.objects.select_related()[:int(self.limit)]
        else:
            profiles = Profile.objects.all()

        context[self.var_name] = profiles
        return ''


@register.tag
def get_profiles(parser, token):
    """
    Gets any number of latest posts and stores them in a varable.

    Syntax::

        {% get_profiles [limit] as [var_name] %}

    Example usage::

        {% get_profiles 10 as profile_list %}

        {% get_profiles as profile_list %}
    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%s tag requires arguments" % token.contents.split()[0]
    m1 = re.search(r'as (\w+)', arg)
    m2 = re.search(r'(.*?) as (\w+)', arg)

    if not m1:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    else:
        var_name = m1.groups()[0]
        return GetProfiles(var_name)

    if not m2:
        raise template.TemplateSyntaxError, "%s tag had invalid arguments" % tag_name
    else:
        format_string, var_name = m2.groups()
        return GetProfiles(var_name, format_string[0])
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


USERNAME = r'(?P<username>[-.\w]+)'

urlpatterns = patterns('basic.profiles.views',
    url(r'^edit/$',
        view='profile_edit',
        name='profile_edit',
    ),
    url(r'^%s/$' % USERNAME,
        view='profile_detail',
        name='profile_detail',
    ),
    url (r'^$',
        view='profile_list',
        name='profile_list',
    ),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect
from django.views.generic import list_detail
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from basic.profiles.models import *
from basic.profiles.forms import *


def profile_list(request):
    return list_detail.object_list(
        request,
        queryset=Profile.objects.all(),
        paginate_by=20,
    )
profile_list.__doc__ = list_detail.object_list.__doc__


def profile_detail(request, username):
    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        raise Http404
    profile = Profile.objects.get(user=user)
    context = { 'object':profile }
    return render_to_response('profiles/profile_detail.html', context, context_instance=RequestContext(request))


@login_required
def profile_edit(request, template_name='profiles/profile_form.html'):
    """Edit profile."""

    if request.POST:
        profile = Profile.objects.get(user=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserForm(request.POST, instance=request.user)
        service_formset = ServiceFormSet(request.POST, instance=profile)
        link_formset = LinkFormSet(request.POST, instance=profile)

        if profile_form.is_valid() and user_form.is_valid() and service_formset.is_valid() and link_formset.is_valid():
            profile_form.save()
            user_form.save()
            service_formset.save()
            link_formset.save()
            return HttpResponseRedirect(reverse('profile_detail', kwargs={'username': request.user.username}))
        else:
            context = {
                'profile_form': profile_form,
                'user_form': user_form,
                'service_formset': service_formset,
                'link_formset': link_formset
            }
    else:
        profile = Profile.objects.get(user=request.user)
        service_formset = ServiceFormSet(instance=profile)
        link_formset = LinkFormSet(instance=profile)
        context = {
            'profile_form': ProfileForm(instance=profile),
            'user_form': UserForm(instance=request.user),
            'service_formset': service_formset,
            'link_formset': link_formset
        }
    return render_to_response(template_name, context, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.conf import settings


RELATIONSHIP_CACHE = getattr(settings, 'RELATIONSHIP_CACHE', 60*60*24*7)
RELATIONSHIP_CACHE_KEYS = {
    'FRIENDS': 'friends',
    'FOLLOWERS': 'followers',
    'BLOCKERS': 'blockers',
    'FANS': 'fans'
}


class RelationshipManager(models.Manager):
    def _set_cache(self, user, user_list, relationship_type, flat=False, flat_attr='to_user'):
        cache_key = 'user_%s_%s' % (user.pk, relationship_type)
        if flat:
            cache_key = cache_key+'_flat'
            user_list = user_list.values_list(flat_attr, flat=True)
        if not cache.get(cache_key):
            cache.set(cache_key, list(user_list), RELATIONSHIP_CACHE)
        return user_list

    def get_blockers_for_user(self, user, flat=False):
        """Returns list of people blocking user."""
        user_list = self.filter(to_user=user, is_blocked=True)
        return self._set_cache(user, user_list, RELATIONSHIP_CACHE_KEYS['BLOCKERS'], flat=flat, flat_attr='from_user')

    def get_friends_for_user(self, user, flat=False):
        """Returns people user is following sans people blocking user."""
        blocked_id_list = self.get_blockers_for_user(user, flat=True)
        user_list = self.filter(from_user=user, is_blocked=False).exclude(to_user__in=blocked_id_list)
        return self._set_cache(user, user_list, RELATIONSHIP_CACHE_KEYS['FRIENDS'], flat=flat)

    def get_followers_for_user(self, user, flat=False):
        """Returns people following user."""
        user_list = self.filter(to_user=user, is_blocked=False)
        return self._set_cache(user, user_list, RELATIONSHIP_CACHE_KEYS['FOLLOWERS'], flat=flat, flat_attr='from_user')

    def get_fans_for_user(self, user, flat=False):
        """Returns people following user but user isn't following."""
        friend_id_list = self.get_friends_for_user(user, flat=True)
        user_list = self.filter(to_user=user, is_blocked=False).exclude(from_user__in=friend_id_list)
        return self._set_cache(user, user_list, RELATIONSHIP_CACHE_KEYS['FANS'], flat=flat, flat_attr='from_user')

    def get_relationship(self, from_user, to_user):
        try:
            relationship = self.get(from_user=from_user, to_user=to_user)
        except:
            return None
        return relationship

    def blocking(self, from_user, to_user):
        """Returns True if from_user is blocking to_user."""
        try:
            relationship = self.get(from_user=from_user, to_user=to_user)
            if relationship.is_blocked:
                return True
        except:
            return False
        return False

class Relationship(models.Model):
    """Relationship model"""
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='from_users')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='to_users')
    created = models.DateTimeField(auto_now_add=True)
    is_blocked = models.BooleanField(default=False)
    objects = RelationshipManager()

    class Meta:
        unique_together = (('from_user', 'to_user'),)
        verbose_name = _('relationship')
        verbose_name_plural = _('relationships')
        db_table = 'relationships'

    def __unicode__(self):
        if self.is_blocked:
            return u'%s is blocking %s' % (self.from_user, self.to_user)
        return u'%s is connected to %s' % (self.from_user, self.to_user)

    def save(self, *args, **kwargs):
        self._delete_cache_keys()
        super(Relationship, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._delete_cache_keys()
        super(Relationship, self).delete(*args, **kwargs)

    def _delete_cache_keys(self):
        for key in RELATIONSHIP_CACHE_KEYS:
            cache.delete('user_%s_%s' % (self.from_user.pk, RELATIONSHIP_CACHE_KEYS[key]))
            cache.delete('user_%s_%s_flat' % (self.from_user.pk, RELATIONSHIP_CACHE_KEYS[key]))
########NEW FILE########
__FILENAME__ = relationships
from django import template
from django.db import models

Relationship = models.get_model('relationships', 'relationship')
register = template.Library()


# Expose RelationshipManager functionality as template filters.

@register.filter
def blockers(user):
    """Returns list of people blocking user."""
    try:
        return Relationship.objects.get_blockers_for_user(user)
    except AttributeError:
        return []

@register.filter
def friends(user):
    """Returns people user is following sans people blocking user."""
    try:
        return Relationship.objects.get_friends_for_user(user)
    except AttributeError:
        return []

@register.filter
def followers(user):
    """Returns people following user."""
    try:
        return Relationship.objects.get_followers_for_user(user)
    except AttributeError:
        pass

@register.filter
def fans(user):
    """Returns people following user but user isn't following."""
    try:
        return Relationship.objects.get_fans_for_user(user)
    except AttributeError:
        pass

# Comparing two users.

@register.filter
def follows(from_user, to_user):
    """Returns ``True`` if the first user follows the second, ``False`` otherwise.  Example: {% if user|follows:person %}{% endif %}"""
    try:
        relationship = Relationship.objects.get_relationship(from_user, to_user)
        if relationship and not relationship.is_blocked:
            return True
        else:
            return False
    except AttributeError:
        return False

@register.filter
def get_relationship(from_user, to_user):
    """Get relationship between two users."""
    try:
        return Relationship.objects.get_relationship(from_user, to_user)
    except AttributeError:
        return None

# get_relationship templatetag.

class GetRelationship(template.Node):
    def __init__(self, from_user, to_user, varname='relationship'):
        self.from_user = from_user
        self.to_user = to_user
        self.varname = varname

    def render(self, context):
        from_user = template.resolve_variable(self.from_user, context)
        to_user = template.resolve_variable(self.to_user, context)

        relationship = Relationship.objects.get_relationship(from_user, to_user)
        context[self.varname] = relationship

        return ''

def do_get_relationship(parser, token):
    """
    Get relationship between two users.

    Example:
        {% get_relationship from_user to_user as relationship %}
    """
    bits = token.contents.split()
    if len(bits) == 3:
        return GetRelationship(bits[1], bits[2])
    if len(bits) == 5:
        return GetRelationship(bits[1], bits[2], bits[4])
    if len(bits) == 4:
        raise template.TemplateSyntaxError, "The tag '%s' needs an 'as' as its third argument." % bits[0]
    if len(bits) < 3:
        raise template.TemplateSyntaxError, "The tag '%s' takes two arguments" % bits[0]

register.tag('get_relationship', do_get_relationship)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase, override_settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from basic.relationships.models import *


class RelationshipTestCase(TestCase):

    @override_settings(AUTH_USER_MODEL='auth.User')
    def setUp(self):
        self.user1 = User.objects.create_user('nathanb', email='nathanb@example.com', password='n')
        self.user2 = User.objects.create_user('laurah', email='laurah@example.com', password='l')
        
    @override_settings(AUTH_USER_MODEL='auth.User')
    def test_follow(self):
        self.client.login(username=self.user1.username, password='n')

        kwargs = {'username': self.user2.username}

        # GET request displays confirmation form
        response = self.client.get(reverse('relationship_follow', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        # POST request saves relationship
        response = self.client.post(reverse('relationship_follow', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        friends = Relationship.objects.get_friends_for_user(self.user1)
        self.assertEqual(len(friends), 1)

        followers = Relationship.objects.get_followers_for_user(self.user2)
        self.assertEqual(len(followers), 1)

        fans = Relationship.objects.get_fans_for_user(self.user2)
        self.assertEqual(len(fans), 1)
        
    @override_settings(AUTH_USER_MODEL='auth.User')
    def test_block(self):
        self.client.login(username=self.user1.username, password='n')

        kwargs = {'username': self.user2.username}

        # GET request displays confirmation form
        response = self.client.get(reverse('relationship_block', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        # POST request saves block
        response = self.client.post(reverse('relationship_block', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

        blocked = Relationship.objects.get_blockers_for_user(self.user2)
        self.assertEqual(len(blocked), 1)

        # Login as different user
        self.client.login(username=self.user2.username, password='l')

        # POST request saves relationship
        response = self.client.post(reverse('relationship_follow', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, 200)

        friends = Relationship.objects.get_friends_for_user(self.user2)
        self.assertEqual(len(friends), 0)
        
    @override_settings(AUTH_USER_MODEL='auth.User')
    def test_following(self):
        kwargs = {'username': self.user1.username}
        
        # Test with no relations.
        response = self.client.get(reverse('relationship_following', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([following.id for following in response.context['page'].object_list], [])
        
        # Setup a relationship.
        Relationship.objects.create(from_user=self.user1, to_user=self.user2)
        
        # Test the relationship.
        response = self.client.get(reverse('relationship_following', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([following.id for following in response.context['page'].object_list], [self.user2.pk])
        
    @override_settings(AUTH_USER_MODEL='auth.User')
    def test_followers(self):
        kwargs = {'username': self.user2.username}
        
        # Test with no relations.
        response = self.client.get(reverse('relationship_followers', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([following.id for following in response.context['page'].object_list], [])
        
        # Setup a relationship.
        Relationship.objects.create(from_user=self.user1, to_user=self.user2)
        
        # Test the relationship.
        response = self.client.get(reverse('relationship_followers', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([following.id for following in response.context['page'].object_list], [self.user1.pk])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


USERNAME = r'(?P<username>[-.\w]+)'

urlpatterns = patterns('basic.relationships.views',
    url(r'^following/%s/$' % USERNAME,
        view='following',
        name='relationship_following'
    ),
    url(r'^followers/%s/$' % USERNAME,
        view='followers',
        name='relationship_followers'
    ),
    url(r'^follow/%s/$' % USERNAME,
        view='follow',
        name='relationship_follow'
    ),
    url(r'^unfollow/%s/$' % USERNAME,
        view='unfollow',
        name='relationship_unfollow'
    ),
    url(r'^block/%s/$' % USERNAME,
        view='block',
        name='relationship_block'
    ),
    url(r'^unblock/%s/$' % USERNAME,
        view='unblock',
        name='relationship_unblock'
    ),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string

Relationship = models.get_model('relationships', 'relationship')


FOLLOWING_PER_PAGE = getattr(settings, 'RELATIONSHIPS_FOLLOWING_PER_PAGE', 20)
FOLLOWERS_PER_PAGE = getattr(settings, 'RELATIONSHIPS_FOLLOWERS_PER_PAGE', 20)


def following(request, username,
              template_name='relationships/relationship_following.html',
              flat=True):
    from_user = get_object_or_404(User, username=username)
    following_ids = Relationship.objects.get_friends_for_user(from_user, flat=flat)
    following = User.objects.filter(pk__in=following_ids)
    paginator = Paginator(following, FOLLOWING_PER_PAGE)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page.")

    return render_to_response(template_name, {
        'person': from_user,
        'page': page,
        'paginator': paginator,
    }, context_instance=RequestContext(request))


def followers(request, username,
              template_name='relationships/relationship_followers.html',
              flat=True):
    to_user = get_object_or_404(User, username=username)
    followers_ids = Relationship.objects.get_followers_for_user(to_user, flat=True)
    followers = User.objects.filter(pk__in=followers_ids)
    paginator = Paginator(followers, FOLLOWERS_PER_PAGE)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page.")

    return render_to_response(template_name, {
        'person': to_user,
        'page': page,
        'paginator': paginator,
    }, context_instance=RequestContext(request))


@login_required
def follow(request, username,
            template_name='relationships/relationship_add_confirm.html', 
            success_template_name='relationships/relationship_add_success.html', 
            content_type='text/html'):
    """
    Allows a user to follow another user.
    
    Templates: ``relationships/relationship_add_confirm.html`` and ``relationships/relationship_add_success.html``
    Context:
        to_user
            User object
    """
    to_user = get_object_or_404(User, username=username)
    from_user = request.user
    next = request.GET.get('next', None)

    if request.method == 'POST':
        relationship, created = Relationship.objects.get_or_create(from_user=from_user, to_user=to_user)

        if request.is_ajax():
            response = {
                'success': 'Success',
                'to_user': {
                    'username': to_user.username,
                    'user_id': to_user.pk
                },
                'from_user': {
                    'username': from_user.username,
                    'user_id': from_user.pk
                }
            }
            return HttpResponse(json.dumps(response), content_type="application/json")
        if next:
            return HttpResponseRedirect(next)
        template_name = success_template_name

    context = {
        'to_user': to_user,
        'next': next
    }
    return render_to_response(template_name, context, context_instance=RequestContext(request), content_type=content_type)


@login_required
def unfollow(request, username,
            template_name='relationships/relationship_delete_confirm.html', 
            success_template_name='relationships/relationship_delete_success.html', 
            content_type='text/html'):
    """
    Allows a user to stop following another user.

    Templates: ``relationships/relationship_delete_confirm.html`` and ``relationships/relationship_delete_success.html``
    Context:
        to_user
            User object
    """
    to_user = get_object_or_404(User, username=username)
    from_user = request.user
    next = request.GET.get('next', None)

    if request.method == 'POST':
        relationship = get_object_or_404(Relationship, to_user=to_user, from_user=from_user)
        relationship.delete()

        if request.is_ajax():
            response = {
                'success': 'Success',
                'to_user': {
                    'username': to_user.username,
                    'user_id': to_user.pk
                },
                'from_user': {
                    'username': from_user.username,
                    'user_id': from_user.pk
                }
            }
            return HttpResponse(json.dumps(response), content_type="application/json")
        if next:
            return HttpResponseRedirect(next)
        template_name = success_template_name

    context = {
        'to_user': to_user,
        'next': next
    }
    return render_to_response(template_name, context, context_instance=RequestContext(request), content_type=content_type)


@login_required
def block(request, username,
            template_name='relationships/block_confirm.html', 
            success_template_name='relationships/block_success.html', 
            content_type='text/html'):
    """
    Allows a user to block another user.

    Templates: ``relationships/block_confirm.html`` and ``relationships/block_success.html``
    Context:
        user_to_block
            User object
    """
    user_to_block = get_object_or_404(User, username=username)
    user = request.user
    next = request.GET.get('next', None)

    if request.method == 'POST':
        relationship, created = Relationship.objects.get_or_create(to_user=user_to_block, from_user=user)
        relationship.is_blocked = True
        relationship.save()

        if request.is_ajax():
            response = {'success': 'Success'}
            return HttpResponse(json.dumps(response), content_type="application/json")
        if next:
            return HttpResponseRedirect(next)
        template_name = success_template_name

    context = {
        'user_to_block': user_to_block,
        'next': next
    }
    return render_to_response(template_name, context, context_instance=RequestContext(request), content_type=content_type)


@login_required
def unblock(request, username,
            template_name='relationships/block_delete_confirm.html', 
            success_template_name='relationships/block_delete_success.html', 
            content_type='text/html'):
    """
    Allows a user to stop blocking another user.

    Templates: ``relationships/block_delete_confirm.html`` and ``relationships/block_delete_success.html``
    Context:
        user_to_block
            User object
    """
    user_to_block = get_object_or_404(User, username=username)
    user = request.user

    if request.method == 'POST':
        relationship = get_object_or_404(Relationship, to_user=user_to_block, from_user=user, is_blocked=True)
        relationship.delete()

        if request.is_ajax():
            response = {'success': 'Success'}
            return HttpResponse(json.dumps(response), content_type="application/json")
        else:
            template_name = success_template_name

    context = {'user_to_block': user_to_block}
    return render_to_response(template_name, context, context_instance=RequestContext(request), content_type=content_type)

########NEW FILE########
__FILENAME__ = baseconv
"""
Convert numbers from base 10 integers to base X strings and back again.

Original: http://www.djangosnippets.org/snippets/1431/

Sample usage:

>>> base20 = BaseConverter('0123456789abcdefghij')
>>> base20.from_decimal(1234)
'31e'
>>> base20.from_decimal('31e')
1234
"""

class BaseConverter(object):
    decimal_digits = "0123456789"
    
    def __init__(self, digits):
        self.digits = digits
    
    def from_decimal(self, i):
        return self.convert(i, self.decimal_digits, self.digits)
    
    def to_decimal(self, s):
        return int(self.convert(s, self.digits, self.decimal_digits))
    
    def convert(number, fromdigits, todigits):
        # Based on http://code.activestate.com/recipes/111286/
        if str(number)[0] == '-':
            number = str(number)[1:]
            neg = 1
        else:
            neg = 0

        # make an integer out of the number
        x = 0
        for digit in str(number):
           x = x * len(fromdigits) + fromdigits.index(digit)
    
        # create the result in base 'len(todigits)'
        if x == 0:
            res = todigits[0]
        else:
            res = ""
            while x > 0:
                digit = x % len(todigits)
                res = todigits[digit] + res
                x = int(x / len(todigits))
            if neg:
                res = '-' + res
        return res
    convert = staticmethod(convert)

bin = BaseConverter('01')
hexconv = BaseConverter('0123456789ABCDEF')
base62 = BaseConverter(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz'
)

########NEW FILE########
__FILENAME__ = constants
import re

# Stop Words courtesy of http://www.dcs.gla.ac.uk/idom/ir_resources/linguistic_utils/stop_words
STOP_WORDS = r"""\b(a|about|above|across|after|afterwards|again|against|all|almost|alone|along|already|also|
although|always|am|among|amongst|amoungst|amount|an|and|another|any|anyhow|anyone|anything|anyway|anywhere|are|
around|as|at|back|be|became|because|become|becomes|becoming|been|before|beforehand|behind|being|below|beside|
besides|between|beyond|bill|both|bottom|but|by|call|can|cannot|cant|co|computer|con|could|couldnt|cry|de|describe|
detail|do|done|down|due|during|each|eg|eight|either|eleven|else|elsewhere|empty|enough|etc|even|ever|every|everyone|
everything|everywhere|except|few|fifteen|fify|fill|find|fire|first|five|for|former|formerly|forty|found|four|from|
front|full|further|get|give|go|had|has|hasnt|have|he|hence|her|here|hereafter|hereby|herein|hereupon|hers|herself|
him|himself|his|how|however|hundred|i|ie|if|in|inc|indeed|interest|into|is|it|its|itself|keep|last|latter|latterly|
least|less|ltd|made|many|may|me|meanwhile|might|mill|mine|more|moreover|most|mostly|move|much|must|my|myself|name|
namely|neither|never|nevertheless|next|nine|no|nobody|none|noone|nor|not|nothing|now|nowhere|of|off|often|on|once|
one|only|onto|or|other|others|otherwise|our|ours|ourselves|out|over|own|part|per|perhaps|please|put|rather|re|same|
see|seem|seemed|seeming|seems|serious|several|she|should|show|side|since|sincere|six|sixty|so|some|somehow|someone|
something|sometime|sometimes|somewhere|still|such|system|take|ten|than|that|the|their|them|themselves|then|thence|
there|thereafter|thereby|therefore|therein|thereupon|these|they|thick|thin|third|this|those|though|three|through|
throughout|thru|thus|to|together|too|top|toward|towards|twelve|twenty|two|un|under|until|up|upon|us|very|via|was|
we|well|were|what|whatever|when|whence|whenever|where|whereafter|whereas|whereby|wherein|whereupon|wherever|whether|
which|while|whither|who|whoever|whole|whom|whose|why|will|with|within|without|would|yet|you|your|yours|yourself|
yourselves)\b"""

STOP_WORDS_RE = re.compile(STOP_WORDS, re.IGNORECASE)
########NEW FILE########
__FILENAME__ = context_processors
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site


def site(request):
    """
    Adds the current site to the context.
    """
    return {'site': Site.objects.get(id=settings.SITE_ID)}


def now(request):
    """
    Add current datetime to template context.
    """
    return {'now': datetime.now()}

########NEW FILE########
__FILENAME__ = fields
from django.forms.widgets import Widget, HiddenInput, TextInput
from django.utils.safestring import mark_safe


class AutoCompleteWidget(Widget):
    """
    Widget that presents an <input> field that can be used to search for
    objects instead of a giant <select> field

    You will need to include jQuery UI with autocomplete which can be found here:
    http://jqueryui.com/demos/autocomplete/

    Include media:

        basic/tools/media/stylesheets/autocomplete.css
        basic/tools/media/javascript/autocomplete.js

    Example form:

        from basic.tools.forms import fields

        class BookForm(forms.Form):
            authors = forms.ModelMultipleChoiceField(
                queryset=Author.objects.all(),
                widget=fields.AutoCompleteWidget(model=Author, url='/autocomplete/')
            )

    Add data URL:

        url(r'^autocomplete/$',
            view='basic.tools.views.generic.auto_complete',
            kwargs={
                'queryset': Author.objects.all()
                'fields': ('first_name__icontains', 'last_name__icontains')
            }
        )

    """
    text_field = '%s_auto_complete'
    hidden_field = '%s'

    def __init__(self, model, url, attrs=None, required=True):
        self.attrs = attrs or {}
        self.required = required
        self.Model = model
        self.url = url

    def render(self, name, value, attrs=None):
        text_html = self.create_input(TextInput, name, self.text_field)
        hidden_html = self.create_input(HiddenInput, name, self.hidden_field, value)

        results = ''
        if value:
            object_list = self.Model.objects.filter(pk__in=value)
            for obj in object_list:
                results += '<span class="ui-autocomplete-result"><a href="#%s">x</a>%s</span>\n' % (obj.pk, obj.__unicode__())

        script = '<script type="text/javascript">new AutoCompleteWidget("id_%s", "%s");</script>' % (self.text_field % name, self.url)
        return mark_safe(u'\n'.join([text_html, results, hidden_html, script]))

    def create_input(self, Input, name, field, value=''):
        id_ = 'id_%s' % name
        local_attrs = self.build_attrs(id=field % id_)
        i = Input()
        if type(value) == list:
            value = ','.join(['%s' % v for v in value])
        input_html = i.render(field % name, value, local_attrs)
        return input_html

    def value_from_datadict(self, data, files, name):
        hidden_data = data.get(self.hidden_field % name)
        if hidden_data:
            return hidden_data.split(',')
        return data.get(name, None)

########NEW FILE########
__FILENAME__ = shortcuts
import os.path
import hashlib
import datetime

from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.http import HttpResponseRedirect


def build_filename(instance, filename):
    """
    Converts an image filename to a hash.
    """
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    name = hashlib.md5('%s' % now).hexdigest()
    ext = os.path.splitext(filename)
    return os.path.join('%s/%s' % (instance._meta.app_label, instance._meta.module_name), '%s%s' % (name, ext[1]))


def render(request, *args, **kwargs):
    """
    Simple wrapper for render_to_response.
    """
    kwargs['context_instance'] = RequestContext(request)
    return render_to_response(*args, **kwargs)


def redirect(request, obj=None):
    """
    Simple wrapper for HttpResponseRedirect that checks the request for a
    'next' GET parameter then falls back to a given object or url string.
    """
    next = request.GET.get('next', None)
    redirect_url = '/'

    if next:
        redirect_url = next
    elif isinstance(obj, str):
        redirect_url = obj
    elif obj and hasattr(obj, 'get_absolute_url'):
        redirect_url = obj.get_absolute_url()
    return HttpResponseRedirect(redirect_url)
########NEW FILE########
__FILENAME__ = capture
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

class CaptureNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = mark_safe(output.strip())
        return ''


@register.tag('capture')
def do_capture(parser, token):
    """
    Captures content into a context variable.
    
    Syntax:

        {% capture as [foo] %}{% endcapture %}

    Usage:
        
        {% capture as content %}
            {% block content %}{% endblock %}
        {% endcapture %}
    """
    bits = token.split_contents()
    if len(bits) != 3:
        raise template.TemplateSyntaxError("'capture' node requires `as (variable name)`.")
    nodelist = parser.parse(('endcapture',))
    parser.delete_first_token()
    return CaptureNode(nodelist, bits[2])
########NEW FILE########
__FILENAME__ = comparison
from django.template import Library
from django.template.defaultfilters import lower
from django.utils.safestring import mark_safe

register = Library()


@register.filter
def is_content_type(obj, arg):
    try:
        ct = lower(obj._meta.object_name)
        return ct == arg
    except AttributeError:
        return ''


@register.filter
def app_label(obj):
    """
    Returns an objects app label.
    """
    try:
        return lower(obj._meta.object_name)
    except AttributeError:
        return ''


@register.filter
def round(obj):
    """
    Returns a number rounded.
    """
    try:
        return round(obj)
    except (ValueError,TypeError):
        return ''


@register.filter
def is_string(obj):
    return isinstance(obj, str)


@register.filter
def is_number(obj):
    return isinstance(obj, int)


@register.filter
def is_on(obj1, obj2):
    """
    Shortcut to render an 'on' class.
    """
    if obj1 == obj2:
        return mark_safe(' class="on"')
    return ''

########NEW FILE########
__FILENAME__ = listutils
from django.template import Library

register = Library()


@register.filter
def remaining(item_list, total):
    """
    Returns a null list of remaining items derived from the total. Usefull in
    situations where you want exactly ten items in an interface and you may only
    have eight items. 
    """
    list_length = len(item_list)
    expected_total = int(total)
    if list_length != expected_total:
        return range(0, expected_total-list_length)
    return ''


@register.filter
def pop_from_GET(obj, attr):
    """
    Returns GET parameters sans specified attribute.
    """
    if obj.get(attr, None):
        obj_copy = obj.copy()
        del obj_copy[attr]
        return '&%s' % obj_copy.urlencode()
    if not obj:
        return ''
    return '&%s' % obj.urlencode()


@register.filter
def empty_items(item_list, total):
    """
    Returns a list of null objects. Useful when you want to always show n
    results and you have a list of < n.
    """
    list_length = len(item_list)
    expected_total = int(total)
    if list_length != expected_total:
        return range(0, expected_total-list_length)
    return ''

########NEW FILE########
__FILENAME__ = mathutils
from django import template
from django.template import Library
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = Library()


@register.filter
def min_value(object_list, field):
    """
    Returns the min value given an object_list and a field.

    Example:
        {{ forecast|min:"high_temp" }}
    """
    value_list = [getattr(o, field, None) for o in object_list]
    return min(value_list)


@register.filter
def max_value(object_list, field):
    """
    Returns the max value given an object_list and a field.

    Example:
        {{ forecast|max:"high_temp" }}
    """
    value_list = [getattr(o, field, None) for o in object_list]
    return max(value_list)


class RatioNode(template.Node):
    def __init__(self, val_expr, min_expr, max_expr, max_width):
        self.val_expr = val_expr
        self.min_expr = min_expr
        self.max_expr = max_expr
        self.max_width = max_width

    def render(self, context):
        try:
            value = self.val_expr.resolve(context)
            minvalue = self.min_expr.resolve(context)
            maxvalue = self.max_expr.resolve(context)
            max_width = int(self.max_width.resolve(context))
        except VariableDoesNotExist:
            return ''
        except ValueError:
            raise TemplateSyntaxError("widthratio final argument must be an number")
        try:
            value = float(max(value, minvalue))
            maxvalue = float(maxvalue)
            minvalue = float(minvalue)
            #ratio = (value / maxvalue) * max_width
            ratio = (value - minvalue)/(maxvalue - minvalue)*max_width
        except (ValueError, ZeroDivisionError):
            return ''
        return str(int(round(ratio)))


@register.tag
def ratio(parser, token):
    """
    For creating bar charts and such, this tag calculates the ratio of a given
    value to a maximum value, and then applies that ratio to a constant.

    For example::

        {% ratio this_value min_value max_value 100 %}
        {% ratio 55 40 90 100 %}
    """
    bits = token.contents.split()
    if len(bits) != 5:
        raise TemplateSyntaxError("widthratio takes three arguments")
    tag, this_value_expr, min_value_expr, max_value_expr, max_width = bits

    return RatioNode(parser.compile_filter(this_value_expr),
                          parser.compile_filter(min_value_expr),
                          parser.compile_filter(max_value_expr),
                          parser.compile_filter(max_width))

########NEW FILE########
__FILENAME__ = objectutils
from django import template
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from basic.tools.templatetags.utils import parse_ttag

register = template.Library()


class RenderTemplateNode(template.Node):
    def __init__(self, object_name, template_dir):
        self.object_name = object_name
        self.template_dir = template_dir.rstrip('/').strip('"').strip("'")

    def render(self, context):
        try:
            obj = template.resolve_variable(self.object_name, context)
            template_name = '%s.%s.html' % (obj._meta.app_label, obj._meta.module_name)
            template_list = [
                '%s/%s' % (self.template_dir, template_name),
                '%s/default.html' % self.template_dir
            ]
            context['object'] = obj
            return render_to_string(template_list, context)
        except AttributeError:
            if (type(obj) in (int, unicode, str)):
                return obj
            return ''
        except template.VariableDoesNotExist:
            return ''


@register.tag()
def render_template(parser, token):
    """
    Returns the proper template based on the objects content_type. If an
    template doesn't exist it'll fallback to default.html.

    Syntax:

        {% render_template for [object] in [path to templates] %}

    Usage:

        {% render_template for entry in "includes/lists" %}
    """
    tags = parse_ttag(token, ['for', 'in'])
    if len(tags) != 3:
        raise template.TemplateSyntaxError, '%r tag has invalid arguments' % tags['tag_name']
    return RenderTemplateNode(object_name=tags['for'], template_dir=tags['in'])

########NEW FILE########
__FILENAME__ = stringutils
import re

from django.template import Library, Template, Context
from django.template.defaultfilters import urlizetrunc
from django.utils.safestring import mark_safe

register = Library()


@register.filter
def twitterize(value):
    try:
        new_value = re.sub(r'(@)(\w+)', '\g<1><a href="/\g<2>/">\g<2></a>', value)
        return mark_safe(new_value)
    except:
        return value


@register.filter
def strip(value, arg):
    return value.strip(arg)


@register.filter
def smarty(value):
    from smartypants import smartyPants
    return value


@register.filter
def format_text(value):
    return twitterize(urlizetrunc(value, 30))


@register.filter
def format_field(field):
    t = Template("""
    <p class="ui-field{% if field.errors %} ui-error{% endif %}" {% if field.is_hidden %} style="display:none;"{% endif %}>
      {{ field.label_tag }}
      <span class="field">
        {% if field.errors %}<span class="ui-field-error">{{ field.errors|join:", " }}</span>{% endif %}
        {{ field }}
        {% if field.help_text %}<span class="ui-field-help">{{ field.help_text }}</span>{% endif %}
      </span>
    </p>
    """)
    return t.render(Context({'field': field}))


@register.filter
def format_fields(form):
    t = Template("""
    {% load stringutils %}
    {% for field in form %}
      {{ field|format_field }}
    {% endfor %}
    """)
    return t.render(Context({'form': form}))


@register.filter
def placeholder(field, text):
    return mark_safe(re.sub('<input ', '<input placeholder="%s" ' % text, field))

########NEW FILE########
__FILENAME__ = thumbnail
from django import template
from django.conf import settings
register = template.Library()


# Tags
@register.filter
def thumbnail(url, size='200x200'):
    """
    Given a URL (local or remote) to an image, creates a thumbnailed version of the image, saving
    it locally and then returning the URL to the new, smaller version. If the argument passed is a
    single integer, like "200", will output a version of the image no larger than 200px wide. If the
    argument passed is two integers, like, "200x300", will output a cropped version of the image that
    is exactly 200px wide by 300px tall.

    Examples:

    {{ story.leadphoto.url|thumbnail:"200" }}
    {{ story.leadphoto.url|thumbnail:"300x150" }}

    """
    import os

    if url.startswith(settings.MEDIA_URL):
        url = url[len(settings.MEDIA_URL):]
    original_path = settings.MEDIA_ROOT + url

    # Define the thumbnail's filename, file path, and URL.
    try:
        basename, format = original_path.rsplit('.', 1)
    except ValueError:
        return os.path.join(settings.MEDIA_URL, url)
    thumbnail = basename + '_t' + size + '.' +  format
    thumbnail_url = '%s%s' % (settings.MEDIA_URL, thumbnail[len(settings.MEDIA_ROOT):])

    # Find out if a thumbnail in this size already exists. If so, we'll not remake it.
    if not os.path.exists(thumbnail):
        import Image

        # Open the image.
        try:
            image = Image.open(original_path)
        except IOError:
            return os.path.join(settings.MEDIA_URL, url)

        # Make a copy of the original image so we can access its attributes, even
        # after we've changed some of them.
        original_image = image.copy()

        # Find the size of the original image.
        original_width = original_image.size[0]
        original_height = original_image.size[1]

        # Parse the size argument into integers.
        try:
            # See if both height and width exist (i.e. "200x100")
            desired_width, desired_height = [int(x) for x in size.split('x')]
            new_size = (desired_width, desired_height)
            # Flag this image for cropping, since we want an explicit width AND height.
            crop = True
        except ValueError:
            # If only one exists ( i.e. "200"), use the value as the desired width.
            if size[0] == 'x':
                desired_height = int(size[1:])
                new_size = (original_width, desired_height)
                crop = False
            else:
                desired_width = int(size)
                new_size = (desired_width, original_height)
                crop = False

        # If we are to crop this image, we'll thumbnail it, and then figure out the proper crop area
        # Crops are done from the center of the image.
        if crop:
            if (original_height / (original_width / float(desired_width))) < desired_height:
                image.thumbnail((original_width, desired_height), Image.ANTIALIAS)
            else:
                image.thumbnail((desired_width, original_height), Image.ANTIALIAS)

            if (image.size[0] >= desired_width) and (image.size[1] >= desired_height):
                left = (image.size[0] - desired_width) / 2
                top  = (image.size[1] - desired_height) / 2
                right = left + desired_width
                bottom = top + desired_height
                cropped_image = image.crop((left, top, right, bottom))
                image = cropped_image
        else:
            # If we are not to crop this image, simply thumbnail it down to the desired width.
            image.thumbnail(new_size, Image.ANTIALIAS)

        # Finally, save the image.
        try:
            image.save(thumbnail, image.format, quality=85)
        except KeyError:
            return ''

    # And return the URL to the new thumbnailed version.
    return thumbnail_url
########NEW FILE########
__FILENAME__ = utils
from django import template


def parse_ttag(token, required_tags):
    """
    A function to parse a template tag.
    Pass in the token to parse, and a list of keywords to look for.
    It sets the name of the tag to 'tag_name' in the hash returned.

    >>> from test_utils.templatetags.utils import parse_ttag
    >>> parse_ttag('super_cool_tag for my_object as bob', ['as'])
    {'tag_name': u'super_cool_tag', u'as': u'bob'}
    >>> parse_ttag('super_cool_tag for my_object as bob', ['as', 'for'])
    {'tag_name': u'super_cool_tag', u'as': u'bob', u'for': u'my_object'}

    Author:     Eric Holscher
    URL:        http://github.com/ericholscher/
    """

    if isinstance(token, template.Token):
        bits = token.split_contents()
    else:
        bits = token.split(' ')
    tags = {'tag_name': bits.pop(0)}
    for index, bit in enumerate(bits):
        bit = bit.strip()
        if bit in required_tags:
            if len(bits) != index-1:
                tags[bit.strip()] = bits[index+1]
    return tags
########NEW FILE########
__FILENAME__ = generic
from django.db.models import Q
from django.utils import simplejson as json
from django.http import HttpResponse


def auto_complete(request, queryset, fields=None):
    """
    Returns a JSON list to be used with the AutoCompleteWidget javascript.

    Example:

        url(r'^autocomplete/$',
            view='basic.tools.views.generic.auto_complete',
            kwargs={
                'queryset': Author.objects.all()
                'fields': ('first_name__icontains', 'last_name__icontains')
            }
        )

    """
    object_list = []
    limit = request.GET.get('limit', 10)
    query = request.GET.get('term', '')
    if fields:
        q_object = Q()
        for field in fields:
            q_object |= Q(**{field: query})
        queryset = queryset.filter(q_object)

    for obj in queryset[:limit]:
        object_list.append({'text': obj.__unicode__(), 'id': obj.pk})
    return HttpResponse(json.dumps(object_list), mimetype='application/json')
########NEW FILE########
