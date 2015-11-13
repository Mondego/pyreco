__FILENAME__ = admin
from django.contrib import admin
from wordpress.models import (
    Option, Comment, Link, Post,
    PostMeta, Taxonomy, Term, User, UserMeta
)


class OptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')


class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author_name', 'post_date')
    list_filter = ('comment_type', 'approved')
    search_fields = ('author_name', 'author_email', 'post__title')


class LinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'description')
    list_filter = ('visible',)
    search_fields = ('name', 'url', 'description')


class PostMetaInline(admin.TabularInline):
    model = PostMeta


class PostAdmin(admin.ModelAdmin):
    inlines = (PostMetaInline,)
    list_display = ('id', 'title', 'author', 'post_date')
    list_filter = ('status', 'post_type', 'comment_status', 'ping_status', 'author')
    search_fields = ('title',)


class UserMetaInline(admin.TabularInline):
    model = UserMeta


class UserAdmin(admin.ModelAdmin):
    inlines = (UserMetaInline,)
    list_display = ('id', 'display_name', 'email', 'status')
    list_filter = ('status',)
    search_fields = ('login', 'username', 'display_name', 'email')


class TaxonomyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'term')
    list_filter = ('name',)


class TermAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


admin.site.register(Option, OptionAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Link, LinkAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Taxonomy, TaxonomyAdmin)
admin.site.register(Term, TermAdmin)
admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = wpexport
import sys

from django.core.management.base import NoArgsCommand
from django.template.loader import render_to_string

from wordpress.models import Post, Author
import wordpress


class Command(NoArgsCommand):

    def handle_noargs(self, **options):

        context = {
            'authors': Author.objects.all(),
            'posts': Post.objects.published(),
            'generator': 'http://github.com/sunlightlabs/django-wordpress#%s' % wordpress.__version__,
        }

        sys.stdout.write(render_to_string("wordpress/wxr.xml", context))

########NEW FILE########
__FILENAME__ = wpexportauthors
import csv
import sys

from django.core.management.base import NoArgsCommand
from wordpress.models import User

HEADERS = ("id", "username", "display_name", "email")


class Command(NoArgsCommand):

    def handle_noargs(self, **options):

        writer = csv.writer(sys.stdout)
        writer.writerow(HEADERS)

        for author in User.objects.all():
            row = (
                author.pk,
                author.login,
                author.display_name,
                author.email,
            )
            writer.writerow(row)

########NEW FILE########
__FILENAME__ = models
import collections
import datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


STATUS_CHOICES = (
    ('closed', 'closed'),
    ('open', 'open'),
)

POST_STATUS_CHOICES = (
    ('draft', 'draft'),
    ('inherit', 'inherit'),
    ('private', 'private'),
    ('publish', 'publish'),
)

POST_TYPE_CHOICES = (
    ('attachment', 'attachment'),
    ('page', 'page'),
    ('post', 'post'),
    ('revision', 'revision'),
)

USER_STATUS_CHOICES = (
    (0, "active"),
)

READ_ONLY = getattr(settings, "WP_READ_ONLY", True)
TABLE_PREFIX = getattr(settings, "WP_TABLE_PREFIX", "wp")


#
# Exceptions
#

class WordPressException(Exception):
    """
    Exception that is thrown when attempting to save a read-only object.
    """
    pass


#
# Base managers
#

class WordPressManager(models.Manager):
    """
    Base manager for wordpress queries.
    """
    pass


#
# Base models
#

class WordPressModel(models.Model):
    """
    Base model for all WordPress objects.

    Overrides save and delete methods to enforce read-only setting.
    Overrides self.objects to enforce WP_DATABASE setting.
    """

    objects = WordPressManager()

    class Meta:
        abstract = True
        managed = False

    def _get_object(self, model, obj_id):
        try:
            return model.objects.get(pk=obj_id)
        except model.DoesNotExist:
            pass

    def save(self, override=False, **kwargs):
        if READ_ONLY and not override:
            raise WordPressException("object is read-only")
        super(WordPressModel, self).save(**kwargs)

    def delete(self, override=False):
        if READ_ONLY and not override:
            raise WordPressException("object is read-only")
        super(WordPressModel, self).delete()


#
# WordPress models
#

class OptionManager(WordPressManager):
    def get_value(self, name):
        try:
            o = self.get(name=name)
            return o.value
        except ObjectDoesNotExist:
            pass


class Option(WordPressModel):

    objects = OptionManager()

    id = models.IntegerField(db_column='option_id', primary_key=True)
    name = models.CharField(max_length=64, db_column='option_name')
    value = models.TextField(db_column='option_value')
    autoload = models.CharField(max_length=20)

    class Meta:
        db_table = '%s_options' % TABLE_PREFIX
        ordering = ["name"]
        managed = False

    def __unicode__(self):
        return u"%s: %s" % (self.name, self.value)


class User(WordPressModel):
    """
    User object. Referenced by Posts, Comments, and Links
    """

    login = models.CharField(max_length=60, db_column='user_login')
    password = models.CharField(max_length=64, db_column='user_pass')
    username = models.CharField(max_length=255, db_column='user_nicename')
    email = models.CharField(max_length=100, db_column='user_email')
    url = models.URLField(max_length=100, db_column='user_url', blank=True)
    date_registered = models.DateTimeField(auto_now_add=True, db_column='user_registered')
    activation_key = models.CharField(max_length=60, db_column='user_activation_key')
    status = models.IntegerField(default=0, choices=USER_STATUS_CHOICES, db_column='user_status')
    display_name = models.CharField(max_length=255, db_column='display_name')

    class Meta:
        db_table = '%s_users' % TABLE_PREFIX
        ordering = ["display_name"]
        managed = False

    def __unicode__(self):
        return self.display_name


class UserMeta(WordPressModel):
    """
    Meta information about a user.
    """

    id = models.IntegerField(db_column='umeta_id', primary_key=True)
    user = models.ForeignKey(User, related_name="meta", db_column='user_id')
    key = models.CharField(max_length=255, db_column='meta_key')
    value = models.TextField(db_column='meta_value')

    class Meta:
        db_table = '%s_usermeta' % TABLE_PREFIX
        managed = False

    def __unicode__(self):
        return u"%s: %s" % (self.key, self.value)


class Link(WordPressModel):
    """
    An external link.
    """

    id = models.IntegerField(db_column='link_id', primary_key=True)
    url = models.URLField(max_length=255, db_column='link_url')
    name = models.CharField(max_length=255, db_column='link_name')
    image = models.CharField(max_length=255, db_column='link_image')
    target = models.CharField(max_length=25, db_column='link_target')
#    category_id = models.IntegerField(default=0, db_column='link_category')
    description = models.CharField(max_length=255, db_column='link_description')
    visible = models.CharField(max_length=20, db_column='link_visible')
    owner = models.ForeignKey(User, related_name='links', db_column='link_owner')
    rating = models.IntegerField(default=0, db_column='link_rating')
    updated = models.DateTimeField(blank=True, null=True, db_column='link_updated')
    rel = models.CharField(max_length=255, db_column='link_rel')
    notes = models.TextField(db_column='link_notes')
    rss = models.CharField(max_length=255, db_column='link_rss')

    class Meta:
        db_table = '%s_links' % TABLE_PREFIX
        managed = False

    def __unicode__(self):
        return u"%s %s" % (self.name, self.url)

    def is_visible(self):
        return self.visible == 'Y'


class PostManager(WordPressManager):
    """
    Provides convenience methods for filtering posts by status.
    """

    def _by_status(self, status, post_type='post'):
        return self.filter(status=status, post_type=post_type)\
            .select_related().prefetch_related('meta')

    def drafts(self, post_type='post'):
        return self._by_status('draft', post_type)

    def private(self, post_type='post'):
        return self._by_status('private', post_type)

    def published(self, post_type='post'):
        return self._by_status('publish', post_type)

    def term(self, terms, taxonomy='post_tag'):
        """
        @arg terms Can either be a string (name of the term) or an list of term names.
        """

        terms = terms if isinstance(terms, (list, tuple)) else [terms]

        try:
            tx = Taxonomy.objects.filter(name=taxonomy, term__slug__in=terms)
            post_ids = TermTaxonomyRelationship.objects.filter(term_taxonomy__in=tx).values_list('object_id', flat=True)

            return self.published().filter(pk__in=post_ids)
        except Taxonomy.DoesNotExist:
            return self.none()

    def from_path(self, path):

        (ymd, slug) = path.strip('/').rsplit('/', 1)

        start_date = datetime.datetime.strptime(ymd, "%Y/%m/%d")
        end_date = start_date + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)

        params = {
            'post_date__range': (start_date, end_date),
            'slug': slug,
        }

        try:
            return self.published().get(**params)
        except ObjectDoesNotExist:
            pass  # fall through to return None


class TermTaxonomyRelationship(WordPressModel):

    object_id = models.IntegerField()
    term_taxonomy = models.ForeignKey('Taxonomy', related_name='relationships', db_column='term_taxonomy_id')
    order = models.IntegerField(db_column='term_order')

    class Meta:
        db_table = '%s_term_relationships' % TABLE_PREFIX
        ordering = ['order']
        managed = False


class Post(WordPressModel):
    """
    The mother lode.
    The WordPress post.
    """

    objects = PostManager()

    id = models.AutoField(primary_key=True, db_column='ID')

    # post data
    guid = models.CharField(max_length=255)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES)
    status = models.CharField(max_length=20, db_column='post_status', choices=POST_STATUS_CHOICES)
    title = models.TextField(db_column='post_title')
    slug = models.SlugField(max_length=200, db_column="post_name")
    author = models.ForeignKey(User, related_name='posts', db_column='post_author')
    excerpt = models.TextField(db_column='post_excerpt')
    content = models.TextField(db_column='post_content')
    content_filtered = models.TextField(db_column='post_content_filtered')
    post_date = models.DateTimeField(db_column='post_date')
    modified = models.DateTimeField(db_column='post_modified')

    # comment stuff
    comment_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    comment_count = models.IntegerField(default=0)

    # ping stuff
    ping_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    to_ping = models.TextField()
    pinged = models.TextField()

    # statuses
    password = models.CharField(max_length=20, db_column="post_password")
#    category_id = models.IntegerField(db_column='post_category')

    # other various lame fields
    parent_id = models.IntegerField(default=0, db_column="post_parent")
    # parent = models.ForeignKey('self', related_name="children", db_column="post_parent", blank=True, null=True)
    menu_order = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, db_column='post_mime_type')

    term_cache = None
    child_cache = None

    class Meta:
        db_table = '%s_posts' % TABLE_PREFIX
        get_latest_by = 'post_date'
        ordering = ["-post_date"]
        managed = False

    def __unicode__(self):
        return self.title

    def save(self, **kwargs):
        if self.parent_id is None:
            self.parent_id = 0
        super(Post, self).save(**kwargs)
        self.child_cache = None
        self.term_cache = None

    @models.permalink
    def get_absolute_url(self):
        return ('wp_object_detail', (
            self.post_date.year,
            "%02i" % self.post_date.month,
            "%02i" % self.post_date.day,
            self.slug
        ))

    # cache stuff

    def _get_children(self):
        if self.child_cache is None:
            self.child_cache = list(Post.objects.filter(parent_id=self.pk))
        return self.child_cache

    def _get_terms(self, taxonomy):

        if not self.term_cache:

            self.term_cache = collections.defaultdict(list)

            qs = Taxonomy.objects.filter(relationships__object_id=self.id).select_related()
            qs = qs.order_by('relationships__order', 'term__name')

            term_ids = [tax.term_id for tax in qs]

            terms = {}
            for term in Term.objects.filter(id__in=term_ids):
                terms[term.id] = term

            for tax in qs:
                if tax.term_id in terms:
                    self.term_cache[tax.name].append(terms[tax.term_id])

        return self.term_cache.get(taxonomy)

    # properties

    @property
    def children(self):
        return self._get_children()

    @property
    def parent(self):
        if self.parent_id:
            return Post.objects.get(pk=self.parent_id)

    @parent.setter
    def parent(self, post):
        if post.pk is None:
            raise ValueError('parent post must have an ID')
        self.parent_id = post.pk

    # related objects

    def categories(self):
        return self._get_terms("category")

    def attachments(self):
        for post in self._get_children():
            if post.post_type == 'attachment':
                yield {
                    'id': post.id,
                    'slug': post.slug,
                    'timestamp': post.post_date,
                    'description': post.content,
                    'title': post.title,
                    'guid': post.guid,
                    'mimetype': post.mime_type,
                }

    def tags(self):
        return self._get_terms("post_tag")


class PostMeta(WordPressModel):
    """
    Post meta data.
    """

    id = models.IntegerField(db_column='meta_id', primary_key=True)
    post = models.ForeignKey(Post, related_name='meta', db_column='post_id')
    key = models.CharField(max_length=255, db_column='meta_key')
    value = models.TextField(db_column='meta_value')

    class Meta:
        db_table = '%s_postmeta' % TABLE_PREFIX
        managed = False

    def __unicode__(self):
        return u"%s: %s" % (self.key, self.value)


class Comment(WordPressModel):
    """
    Comments to Posts.
    """

    id = models.IntegerField(db_column='comment_id', primary_key=True)
    post = models.ForeignKey(Post, related_name="comments", db_column="comment_post_id")
    user_id = models.IntegerField(db_column='user_id', default=0)
    #user = models.ForeignKey(User, related_name="comments", blank=True, null=True, default=0 )
    parent_id = models.IntegerField(default=0, db_column='comment_parent')

    # author fields
    author_name = models.CharField(max_length=255, db_column='comment_author')
    author_email = models.EmailField(max_length=100, db_column='comment_author_email')
    author_url = models.URLField(blank=True, db_column='comment_author_url')
    author_ip = models.IPAddressField(db_column='comment_author_ip')

    # comment data
    post_date = models.DateTimeField(db_column='comment_date_gmt')
    content = models.TextField(db_column='comment_content')
    karma = models.IntegerField(default=0, db_column='comment_karma')
    approved = models.CharField(max_length=20, db_column='comment_approved')

    # other stuff
    agent = models.CharField(max_length=255, db_column='comment_agent')
    comment_type = models.CharField(max_length=20)

    class Meta:
        db_table = '%s_comments' % TABLE_PREFIX
        ordering = ['-post_date']
        managed = False

    def __unicode__(self):
        return u"%s on %s" % (self.author_name, self.post.title)

    def get_absolute_url(self):
        return "%s#comment-%i" % (self.post.get_absolute_url(), self.pk)

    def parent(self):
        return self._get_object(Comment, self.parent_id)

    """
    def user(self):
        return self._get_object(User, self.user_id)
    """

    def is_approved(self):
        return self.approved == '1'

    def is_spam(self):
        return self.approved == 'spam'


class Term(WordPressModel):

    id = models.IntegerField(db_column='term_id', primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    group = models.IntegerField(default=0, db_column='term_group')

    class Meta:
        db_table = '%s_terms' % TABLE_PREFIX
        ordering = ['name']
        managed = False

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('wp_archive_term', (self.slug, ))


class Taxonomy(WordPressModel):

    id = models.IntegerField(db_column='term_taxonomy_id', primary_key=True)
    term = models.ForeignKey(Term, related_name='taxonomies', blank=True, null=True)
    #term_id = models.IntegerField()
    name = models.CharField(max_length=32, db_column='taxonomy')
    description = models.TextField()
    parent_id = models.IntegerField(default=0, db_column='parent')
    count = models.IntegerField(default=0)

    class Meta:
        db_table = '%s_term_taxonomy' % TABLE_PREFIX
        ordering = ['name']
        managed = False

    def __unicode__(self):
        try:
            term = self.term
        except Term.DoesNotExist:
            term = ''
        return u"%s: %s" % (self.name, term)

    def parent(self):
        return self._get_object(Taxonomy, self.parent_id)

    #def term(self):
    #    return self._get_object(Term, self.term_id)

########NEW FILE########
__FILENAME__ = router
# -*- coding: utf-8 -*-

from django.conf import settings

DATABASE = getattr(settings, "WP_DATABASE", "default")


class WordpressRouter(object):
    """
    Overrides default wordpress database to WP_DATABASE setting.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'wordpress':
            return DATABASE
        return None

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

########NEW FILE########
__FILENAME__ = wp
from django import template
from django.template import Context
from wordpress.models import Post
import re

register = template.Library()


class PostsContextNode(template.Node):

    def __init__(self, queryset, var_name):
        self.queryset = queryset
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = self.queryset
        return ''


class PostsTemplateNode(template.Node):

    def __init__(self, queryset, nodelist):
        self.queryset = queryset
        self.nodelist = nodelist

    def render(self, context):
        content = ''
        for post in self.queryset:
            content += self.nodelist.render(Context({'post': post})) + '\n'
        return content


def _posts(parser, token, queryset):

    m = re.search(r'(?P<tag>\w+)(?: (?P<count>\d{1,4}))?(?: as (?P<var_name>\w+))?', token.contents)
    args = m.groupdict()

    if args['count']:
        try:
            queryset = queryset[:int(args['count'])]
        except ValueError:
            raise template.TemplateSyntaxError, "count argument must be an integer"

    if args['var_name']:
        return PostsContextNode(queryset, args['var_name'])

    else:
        nodelist = parser.parse(('end%s' % args['tag'],))
        parser.delete_first_token()
        return PostsTemplateNode(queryset, nodelist)


@register.tag(name="recentposts")
def do_recent_posts(parser, token):
    qs = Post.objects.published()
    return _posts(parser, token, qs)


# popular tags
"""
SELECT COUNT(1) as cnt, t.name, t.slug
FROM sf_terms t
JOIN sf_term_taxonomy tt ON t.term_id = tt.term_id
JOIN sf_term_relationships tr ON tt.term_taxonomy_id = tr.term_taxonomy_id
JOIN sf_posts p ON tr.object_id = p.id
WHERE p.post_status = 'publish'
    AND p.post_type = 'post'
    AND t.slug <> 'uncategorized'
GROUP BY t.name, t.slug
ORDER BY cnt DESC
LIMIT 10
"""

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from wordpress.views import *

urlpatterns = patterns('wordpress.views',

    url(r'^author/(?P<username>[\w-]+)/$',
        AuthorArchive.as_view(), name='wp_author'),

    url(r'^category/(?P<term>.+)/$',
        TaxonomyArchive.as_view(), {'taxonomy': 'category'}, name='wp_taxonomy_category'),
    url(r'^tag/(?P<term>.+)/$',
        TaxonomyArchive.as_view(), {'taxonomy': 'term'}, name='wp_taxonomy_term'),
    url(r'^taxonomy/(?P<taxonomy>term|category)/(?P<term>.+)/$',
        TaxonomyArchive.as_view(), name='wp_taxonomy'),

    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[^/]+)/(?P<attachment_slug>[^/]+)/$',
        PostAttachment.as_view(), name='wp_object_attachment'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[^/]+)/$',
        PostDetail.as_view(), name='wp_object_detail'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        DayArchive.as_view(), name='wp_archive_day'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        MonthArchive.as_view(), name='wp_archive_month'),
    url(r'^(?P<year>\d{4})/$',
        YearArchive.as_view(), name='wp_archive_year'),

    url(r'^post/tag/(?P<term_slug>.+)/$',
        TermArchive.as_view(), name='wp_archive_term'),
    url(r'^$',
        Archive.as_view(), name='wp_archive_index'),

)

########NEW FILE########
__FILENAME__ = views
import urllib
import warnings

from django.conf import settings
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.views import generic
from wordpress.models import Post, Term, User

PER_PAGE = getattr(settings, 'WP_PER_PAGE', 10)

TAXONOMIES = {
    'term': 'post_tag',
    'category': 'category',
    'link_category': 'link_category',
}


class AuthorArchive(generic.list.ListView):

    allow_empty = True
    context_object_name = "post_list"
    paginate_by = PER_PAGE
    template_name = "wordpress/post_archive_author.html"

    def get(self, request, *args, **kwargs):
        try:
            self.author = User.objects.get(login=self.kwargs['username'])
        except User.DoesNotExist:
            raise Http404
        return super(AuthorArchive, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Post.objects.published().filter(author=self.author)

    def get_context_data(self, **kwargs):
        context = super(AuthorArchive, self).get_context_data(**kwargs)
        context['author'] = self.author
        return context


class Preview(generic.detail.DetailView):

    context_object_name = 'post'
    pk_url_kwarg = 'p'
    queryset = Post.objects.all()

    def get_context_data(self, **kwargs):
        context = super(Preview, self).get_context_data(**kwargs)
        context.update({'preview': True})
        return context


class PostDetail(generic.dates.DateDetailView):

    allow_future = True
    context_object_name = 'post'
    date_field = 'post_date'
    month_format = "%m"
    queryset = Post.objects.published()

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data(**kwargs)
        context.update({'post_url': self.request.build_absolute_uri(self.request.path)})
        return context

    def get_object(self):
        self.kwargs['slug'] = urllib.quote(self.kwargs['slug'].encode('utf-8')).lower()
        return super(PostDetail, self).get_object()

    def get(self, request, *args, **kwargs):
        return super(PostDetail, self).get(request, *args, **kwargs)


class PostAttachment(PostDetail):

    def get(self, request, *args, **kwargs):
        post = self.get_object()
        attachment = get_object_or_404(Post, post_type='attachment', slug=self.kwargs['attachment_slug'], parent_id=post.pk)
        return HttpResponseRedirect(attachment.guid)


class DayArchive(generic.dates.DayArchiveView):
    context_object_name = 'post_list'
    date_field = 'post_date'
    month_format = '%m'
    paginate_by = PER_PAGE
    queryset = Post.objects.published()


class MonthArchive(generic.dates.MonthArchiveView):
    context_object_name = 'post_list'
    date_field = 'post_date'
    month_format = '%m'
    paginate_by = PER_PAGE
    queryset = Post.objects.published()


class YearArchive(generic.dates.YearArchiveView):
    date_field = 'post_date'
    queryset = Post.objects.published()


class Archive(generic.dates.ArchiveIndexView):

    allow_empty = True
    context_object_name = 'post_list'
    paginate_by = PER_PAGE
    template_name = 'wordpress/post_archive.html'
    date_field = 'post_date'

    def get(self, request, *args, **kwargs):
        p = request.GET.get('p')
        if p:
            return Preview.as_view()(request, p=p)
        return super(Archive, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Post.objects.published().select_related()


class TaxonomyArchive(generic.list.ListView):

    allow_empty = True
    context_object_name = "post_list"
    paginate_by = PER_PAGE
    template_name = "wordpress/post_term.html"

    def get_context_data(self, **kwargs):
        context = super(TaxonomyArchive, self).get_context_data(**kwargs)
        context.update({
            'tag': get_object_or_404(Term, slug=self.kwargs['term']),
            self.kwargs['taxonomy']: self.kwargs['term'],
        })
        return context

    def get_queryset(self):
        taxonomy = TAXONOMIES.get(self.kwargs['taxonomy'], None)
        if taxonomy:
            return Post.objects.term(self.kwargs['term'], taxonomy=taxonomy).select_related()


class TermArchive(generic.list.ListView):
    pass


#
# *** DEPRECATED ***
# Method-based views for compatibilty with older code.
#

deprecation_msg = "Method-based views are deprecated and will be removed in a near-future version."


def author_list(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return AuthorArchive.as_view()(request, *args, **kwargs)


def preview(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return Preview.as_view()(request, *args, **kwargs)


def object_detail(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return PostDetail.as_view()(request, *args, **kwargs)


def object_attachment(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return PostAttachment.as_view()(request, *args, **kwargs)


def archive_day(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return DayArchive.as_view()(request, *args, **kwargs)


def archive_month(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return MonthArchive.as_view()(request, *args, **kwargs)


def archive_year(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return YearArchive.as_view()(request, *args, **kwargs)


def archive_index(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return Archive.as_view()(request, *args, **kwargs)


def taxonomy(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return TaxonomyArchive.as_view()(request, *args, **kwargs)


def archive_term(request, *args, **kwargs):
    warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
    return TermArchive.as_view()(request, *args, **kwargs)

########NEW FILE########
