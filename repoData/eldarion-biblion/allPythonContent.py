__FILENAME__ = admin
from django.contrib import admin
from django.utils.functional import curry

from biblion.forms import AdminPostForm
from biblion.models import Post, Image, ReviewComment
from biblion.utils import can_tweet


class ImageInline(admin.TabularInline):
    model = Image
    fields = ["image_path"]


class ReviewInline(admin.TabularInline):
    model = ReviewComment


class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "published_flag", "section", "show_secret_share_url"]
    list_filter = ["section"]
    form = AdminPostForm
    fields = [
        "section",
        "title",
        "slug",
        "author",
        "markup",
        "teaser",
        "content",
        "sharable_url",
        "publish",
    ]
    readonly_fields = ["sharable_url"]

    if can_tweet():
        fields.append("tweet")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        ImageInline,
        ReviewInline,
    ]

    def show_secret_share_url(self, obj):
        return '<a href="%s">%s</a>' % (obj.sharable_url, obj.sharable_url)
    show_secret_share_url.short_description = "Share this url"
    show_secret_share_url.allow_tags = True

    def published_flag(self, obj):
        return bool(obj.published)
    published_flag.short_description = "Published"
    published_flag.boolean = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        request = kwargs.get("request")
        if db_field.name == "author":
            ff = super(PostAdmin, self).formfield_for_dbfield(db_field, **kwargs)
            ff.initial = request.user.id
            return ff
        return super(PostAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        kwargs.update({
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
        })
        return super(PostAdmin, self).get_form(request, obj, **kwargs)

    def save_form(self, request, form, change):
        # this is done for explicitness that we want form.save to commit
        # form.save doesn't take a commit kwarg for this reason
        return form.save()


admin.site.register(Post, PostAdmin)
admin.site.register(Image)

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


DEFAULT_MARKUP_CHOICE_MAP = {
    "creole": {"label": "Creole", "parser": "biblion.parsers.creole_parser.parse"},
    "markdown": {"label": "Markdown", "parser": "biblion.parsers.markdown_parser.parse"}
}


class BiblionAppConf(AppConf):

    ALL_SECTION_NAME = "all"
    SECTIONS = []
    MARKUP_CHOICE_MAP = DEFAULT_MARKUP_CHOICE_MAP
    MARKUP_CHOICES = DEFAULT_MARKUP_CHOICE_MAP

    def configure_markup_choices(self, value):
        return [
            (key, value[key]["label"])
            for key in value.keys()
        ]

########NEW FILE########
__FILENAME__ = exceptions

class InvalidSection(Exception):
    pass

########NEW FILE########
__FILENAME__ = forms
from datetime import datetime

from django import forms
from django.utils.functional import curry

from biblion.conf import settings
from biblion.models import Post, Revision
from biblion.utils import can_tweet, load_path_attr
from biblion.signals import post_published


class AdminPostForm(forms.ModelForm):

    title = forms.CharField(
        max_length=90,
        widget=forms.TextInput(attrs={"style": "width: 50%;"}),
    )
    slug = forms.CharField(
        widget=forms.TextInput(attrs={"style": "width: 50%;"})
    )
    teaser = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 80%;"}),
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 80%; height: 300px;"})
    )
    publish = forms.BooleanField(
        required=False,
        help_text="Checking this will publish this articles on the site",
    )

    if can_tweet():
        tweet = forms.BooleanField(
            required=False,
            help_text="Checking this will send out a tweet for this post",
        )

    class Meta:
        model = Post

    def __init__(self, *args, **kwargs):
        super(AdminPostForm, self).__init__(*args, **kwargs)

        post = self.instance

        # grab the latest revision of the Post instance
        latest_revision = post.latest()

        if latest_revision:
            # set initial data from the latest revision
            self.fields["teaser"].initial = latest_revision.teaser
            self.fields["content"].initial = latest_revision.content

            # @@@ can a post be unpublished then re-published? should be pulled
            # from latest revision maybe?
            self.fields["publish"].initial = bool(post.published)

    def save(self):
        published = False
        post = super(AdminPostForm, self).save(commit=False)

        if post.pk is None:
            if self.cleaned_data["publish"]:
                post.published = datetime.now()
                published = True
        else:
            if Post.objects.filter(pk=post.pk, published=None).count():
                if self.cleaned_data["publish"]:
                    post.published = datetime.now()
                    published = True

        render_func = curry(
            load_path_attr(
                settings.BIBLION_MARKUP_CHOICE_MAP[self.cleaned_data["markup"]]["parser"]
            )
        )

        post.teaser_html = render_func(self.cleaned_data["teaser"])
        post.content_html = render_func(self.cleaned_data["content"])
        post.updated = datetime.now()
        post.save()

        r = Revision()
        r.post = post
        r.title = post.title
        r.teaser = self.cleaned_data["teaser"]
        r.content = self.cleaned_data["content"]
        r.author = post.author
        r.updated = post.updated
        r.published = post.published
        r.save()

        if can_tweet() and self.cleaned_data["tweet"]:
            post.tweet()

        if published:
            post_published.send(sender=Post, post=post)

        return post

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models.query import Q

from biblion.conf import settings
from biblion.exceptions import InvalidSection


class PostManager(models.Manager):

    def published(self):
        return self.exclude(published=None)

    def current(self):
        return self.published().order_by("-published")

    def section(self, value, queryset=None):

        if queryset is None:
            queryset = self.published()

        if not value:
            return queryset
        else:
            try:
                section_idx = self.model.section_idx(value)
            except KeyError:
                raise InvalidSection
            all_sections = Q(section=self.model.section_idx(settings.BIBLION_ALL_SECTION_NAME))
            return queryset.filter(all_sections | Q(section=section_idx))

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf8 -*-
import json
try:
    from urllib2 import urlopen  # noqa
except ImportError:
    from urllib.request import urlopen  # noqa

from datetime import datetime

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.contrib.sites.models import Site

try:
    import twitter
except ImportError:
    twitter = None

from biblion.conf import settings
from biblion.managers import PostManager
from biblion.utils import can_tweet

from string import letters
from random import choice


def ig(L, i):
    for x in L:
        yield x[i]


class Post(models.Model):

    SECTION_CHOICES = [(1, settings.BIBLION_ALL_SECTION_NAME)] + \
        zip(
            range(2, 2 + len(settings.BIBLION_SECTIONS)),
            ig(settings.BIBLION_SECTIONS, 1)
        )

    section = models.IntegerField(choices=SECTION_CHOICES)

    title = models.CharField(max_length=90)
    slug = models.SlugField()
    author = models.ForeignKey(User, related_name="posts")

    markup = models.CharField(max_length=25, choices=settings.BIBLION_MARKUP_CHOICES)

    teaser_html = models.TextField(editable=False)
    content_html = models.TextField(editable=False)

    tweet_text = models.CharField(max_length=140, editable=False)

    created = models.DateTimeField(default=datetime.now, editable=False)  # when first revision was created
    updated = models.DateTimeField(null=True, blank=True, editable=False)  # when last revision was created (even if not published)
    published = models.DateTimeField(null=True, blank=True, editable=False)  # when last published

    secret_key = models.CharField(
        max_length=8,
        blank=True,
        unique=True,
        help_text="allows url for sharing unpublished posts to unauthenticated users"
    )

    view_count = models.IntegerField(default=0, editable=False)

    @staticmethod
    def section_idx(slug):
        """
        given a slug return the index for it
        """
        if slug == settings.BIBLION_ALL_SECTION_NAME:
            return 1
        return dict(zip(ig(settings.BIBLION_SECTIONS, 0), range(2, 2 + len(settings.BIBLION_SECTIONS))))[slug]

    @property
    def section_slug(self):
        """
        an IntegerField is used for storing sections in the database so we
        need a property to turn them back into their slug form
        """
        if self.section == 1:
            return settings.BIBLION_ALL_SECTION_NAME
        return dict(zip(range(2, 2 + len(settings.BIBLION_SECTIONS)), ig(settings.BIBLION_SECTIONS, 0)))[self.section]

    def rev(self, rev_id):
        return self.revisions.get(pk=rev_id)

    def current(self):
        "the currently visible (latest published) revision"
        return self.revisions.exclude(published=None).order_by("-published")[0]

    def latest(self):
        "the latest modified (even if not published) revision"
        try:
            return self.revisions.order_by("-updated")[0]
        except IndexError:
            return None

    class Meta:
        ordering = ("-published",)
        get_latest_by = "published"

    objects = PostManager()

    def __unicode__(self):
        return self.title

    def as_tweet(self):
        if not self.tweet_text:
            current_site = Site.objects.get_current()
            api_url = "http://api.tr.im/api/trim_url.json"
            u = urlopen("%s?url=http://%s%s" % (
                api_url,
                current_site.domain,
                self.get_absolute_url(),
            ))
            result = json.loads(u.read())
            self.tweet_text = "%s %s — %s" % (
                settings.TWITTER_TWEET_PREFIX,
                self.title,
                result["url"],
            )
        return self.tweet_text

    def tweet(self):
        if can_tweet():
            account = twitter.Api(
                username=settings.TWITTER_USERNAME,
                password=settings.TWITTER_PASSWORD,
            )
            account.PostUpdate(self.as_tweet())
        else:
            raise ImproperlyConfigured(
                "Unable to send tweet due to either "
                "missing python-twitter or required settings."
            )

    def save(self, **kwargs):
        self.updated_at = datetime.now()
        if not self.secret_key:
            # Generate a random secret key
            self.secret_key = "".join(choice(letters) for _ in xrange(8))
        super(Post, self).save(**kwargs)

    @property
    def sharable_url(self):
        """
        An url to reach this post (there is a secret url for sharing unpublished
        posts to outside users).
        """
        if not self.published:
            if self.secret_key:
                return reverse("blog_post_secret", kwargs={"post_secret_key": self.secret_key})
            else:
                return "A secret sharable url for non-authenticated users is generated when you save this post."
        else:
            return self.get_absolute_url()

    def get_absolute_url(self):
        if self.published:
            name = "blog_post"
            kwargs = {
                "year": self.published.strftime("%Y"),
                "month": self.published.strftime("%m"),
                "day": self.published.strftime("%d"),
                "slug": self.slug,
            }
        else:
            name = "blog_post_pk"
            kwargs = {
                "post_pk": self.pk,
            }
        return reverse(name, kwargs=kwargs)

    def inc_views(self):
        self.view_count += 1
        self.save()
        self.current().inc_views()


class Revision(models.Model):

    post = models.ForeignKey(Post, related_name="revisions")

    title = models.CharField(max_length=90)
    teaser = models.TextField()

    content = models.TextField()

    author = models.ForeignKey(User, related_name="revisions")

    updated = models.DateTimeField(default=datetime.now)
    published = models.DateTimeField(null=True, blank=True)

    view_count = models.IntegerField(default=0, editable=False)

    def __unicode__(self):
        return "Revision %s for %s" % (self.updated.strftime('%Y%m%d-%H%M'), self.post.slug)

    def inc_views(self):
        self.view_count += 1
        self.save()


class Image(models.Model):

    post = models.ForeignKey(Post, related_name="images")

    image_path = models.ImageField(upload_to="images/%Y/%m/%d")
    url = models.CharField(max_length=150, blank=True)

    timestamp = models.DateTimeField(default=datetime.now, editable=False)

    def __unicode__(self):
        if self.pk is not None:
            return "{{ %d }}" % self.pk
        else:
            return "deleted image"


class FeedHit(models.Model):

    request_data = models.TextField()
    created = models.DateTimeField(default=datetime.now)


class ReviewComment(models.Model):

    post = models.ForeignKey(Post, related_name="review_comments")

    review_text = models.TextField()
    timestamp = models.DateTimeField(default=datetime.now)
    addressed = models.BooleanField(default=False)

########NEW FILE########
__FILENAME__ = creole_parser
import re

from creole import Parser
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.util import ClassNotFound

from biblion.models import Image


class Rules:
    # For the link targets:
    proto = r"http|https|ftp|nntp|news|mailto|telnet|file|irc"
    extern = r"(?P<extern_addr>(?P<extern_proto>{0}):.*)".format(proto)
    interwiki = r"""
            (?P<inter_wiki> [A-Z][a-zA-Z]+ ) :
            (?P<inter_page> .* )
    """


class HtmlEmitter(object):
    """
    Generate HTML output for the document
    tree consisting of DocNodes.
    """

    addr_re = re.compile(
        "|".join([Rules.extern, Rules.interwiki]),
        re.X | re.U
    )  # for addresses

    def __init__(self, root):
        self.root = root

    def get_text(self, node):
        """Try to emit whatever text is in the node."""
        try:
            return node.children[0].content or ""
        except:
            return node.content or ""

    def html_escape(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def attr_escape(self, text):
        return self.html_escape(text).replace("\"", "&quot")

    # *_emit methods for emitting nodes of the document

    def document_emit(self, node):
        return self.emit_children(node)

    def text_emit(self, node):
        return self.html_escape(node.content)

    def separator_emit(self, node):
        return "<hr>"

    def paragraph_emit(self, node):
        return "<p>%s</p>\n" % self.emit_children(node)

    def bullet_list_emit(self, node):
        return "<ul>\n%s</ul>\n" % self.emit_children(node)

    def number_list_emit(self, node):
        return "<ol>\n%s</ol>\n" % self.emit_children(node)

    def list_item_emit(self, node):
        return "<li>%s</li>\n" % self.emit_children(node)

    def table_emit(self, node):
        return "<table>\n%s</table>\n" % self.emit_children(node)

    def table_row_emit(self, node):
        return "<tr>%s</tr>\n" % self.emit_children(node)

    def table_cell_emit(self, node):
        return "<td>%s</td>" % self.emit_children(node)

    def table_head_emit(self, node):
        return "<th>%s</th>" % self.emit_children(node)

    def emphasis_emit(self, node):
        return "<i>%s</i>" % self.emit_children(node)

    def strong_emit(self, node):
        return "<b>%s</b>" % self.emit_children(node)

    def header_emit(self, node):
        return "<h%d>%s</h%d>\n" % (
            node.level, self.html_escape(node.content), node.level)

    def code_emit(self, node):
        return "<tt>%s</tt>" % self.html_escape(node.content)

    def link_emit(self, node):
        target = node.content
        if node.children:
            inside = self.emit_children(node)
        else:
            inside = self.html_escape(target)
        m = self.addr_re.match(target)
        if m:
            if m.group("extern_addr"):
                return "<a href=\"%s\">%s</a>" % (
                    self.attr_escape(target), inside)
            elif m.group("inter_wiki"):
                raise NotImplementedError
        return "<a href=\"%s\">%s</a>" % (
            self.attr_escape(target), inside)

    def image_emit(self, node):
        target = node.content
        text = self.get_text(node)
        m = self.addr_re.match(target)
        if m:
            if m.group("extern_addr"):
                return "<img src=\"%s\" alt=\"%s\">" % (
                    self.attr_escape(target), self.attr_escape(text))
            elif m.group("inter_wiki"):
                raise NotImplementedError
        return "<img src=\"%s\" alt=\"%s\">" % (
            self.attr_escape(target), self.attr_escape(text))

    def macro_emit(self, node):
        raise NotImplementedError

    def break_emit(self, node):
        return "<br>"

    def preformatted_emit(self, node):
        return "<pre>%s</pre>" % self.html_escape(node.content)

    def default_emit(self, node):
        """Fallback function for emitting unknown nodes."""
        raise TypeError

    def emit_children(self, node):
        """Emit all the children of a node."""
        return "".join([self.emit_node(child) for child in node.children])

    def emit_node(self, node):
        """Emit a single node."""
        emit = getattr(self, "%s_emit" % node.kind, self.default_emit)
        return emit(node)

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        return self.emit_node(self.root)


class PygmentsHtmlEmitter(HtmlEmitter):

    def preformatted_emit(self, node):
        content = node.content
        lines = content.split("\n")
        if lines[0].startswith("#!code"):
            lexer_name = lines[0].split()[1]
            del lines[0]
        else:
            lexer_name = None
        content = "\n".join(lines)
        try:
            lexer = get_lexer_by_name(lexer_name)
        except ClassNotFound:
            lexer = TextLexer()
        return highlight(content, lexer, HtmlFormatter(cssclass="syntax")).strip()


class ImageLookupHtmlEmitter(HtmlEmitter):

    def image_emit(self, node):
        target = node.content
        if not re.match(r"^\d+$", target):
            return super(ImageLookupHtmlEmitter, self).image_emit(node)
        else:
            try:
                image = Image.objects.get(pk=int(target))
            except Image.DoesNotExist:
                # @@@ do something better here
                return ""
            return "<img src=\"%s\" />" % (image.image_path.url,)


class BiblionHtmlEmitter(PygmentsHtmlEmitter, ImageLookupHtmlEmitter):
    pass


def parse(text, emitter=BiblionHtmlEmitter):
    return emitter(Parser(text).parse()).emit()


def parse_with_highlighting(text, emitter=PygmentsHtmlEmitter):
    return parse(text, emitter=emitter)

########NEW FILE########
__FILENAME__ = markdown_parser
from markdown import Markdown
from markdown.inlinepatterns import ImagePattern, IMAGE_LINK_RE

from biblion.models import Image


class ImageLookupImagePattern(ImagePattern):

    def sanitize_url(self, url):
        if url.startswith("http"):
            return url
        else:
            try:
                image = Image.objects.get(pk=int(url))
                return image.image_path.url
            except Image.DoesNotExist:
                pass
        return ""


def parse(text):
    md = Markdown(extensions=["codehilite"])
    md.inlinePatterns["image_link"] = ImageLookupImagePattern(IMAGE_LINK_RE, md)
    html = md.convert(text)
    return html

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


post_viewed = django.dispatch.Signal(providing_args=["post", "request"])
post_published = django.dispatch.Signal(providing_args=["post"])

########NEW FILE########
__FILENAME__ = biblion_tags
from django import template

from biblion.models import Post
from biblion.conf import settings


register = template.Library()


class LatestBlogPostsNode(template.Node):

    def __init__(self, context_var):
        self.context_var = context_var

    def render(self, context):
        latest_posts = Post.objects.current()[:5]
        context[self.context_var] = latest_posts
        return ""


@register.tag
def latest_blog_posts(parser, token):
    bits = token.split_contents()
    return LatestBlogPostsNode(bits[2])


class LatestBlogPostNode(template.Node):

    def __init__(self, context_var):
        self.context_var = context_var

    def render(self, context):
        try:
            latest_post = Post.objects.current()[0]
        except IndexError:
            latest_post = None
        context[self.context_var] = latest_post
        return ""


@register.tag
def latest_blog_post(parser, token):
    bits = token.split_contents()
    return LatestBlogPostNode(bits[2])


class LatestSectionPostNode(template.Node):

    def __init__(self, section, context_var):
        self.section = template.Variable(section)
        self.context_var = context_var

    def render(self, context):
        section = self.section.resolve(context)
        post = Post.objects.section(section, queryset=Post.objects.current())
        try:
            post = post[0]
        except IndexError:
            post = None
        context[self.context_var] = post
        return ""


@register.tag
def latest_section_post(parser, token):
    """
        {% latest_section_post "articles" as latest_article_post %}
    """
    bits = token.split_contents()
    return LatestSectionPostNode(bits[1], bits[3])


class BlogSectionsNode(template.Node):

    def __init__(self, context_var):
        self.context_var = context_var

    def render(self, context):
        sections = [(settings.BIBLION_ALL_SECTION_NAME, "All")]
        sections += settings.BIBLION_SECTIONS
        context[self.context_var] = sections
        return ""


@register.tag
def blog_sections(parser, token):
    """
        {% blog_sections as blog_sections %}
    """
    bits = token.split_contents()
    return BlogSectionsNode(bits[2])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase


class Tests(TestCase):

    def setUp(self):
        pass

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include


urlpatterns = patterns(
    "",
    (r"^", include("biblion.urls")),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns


urlpatterns = patterns(
    "",
    url(r'^$', "biblion.views.blog_index", name="blog"),
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)/$', "biblion.views.blog_post_detail", name="blog_post"),
    url(r'^post/(?P<post_pk>\d+)/$', "biblion.views.blog_post_detail", name="blog_post_pk"),
    url(r'^post/(?P<post_secret_key>\w+)/$', "biblion.views.blog_post_detail", name="blog_post_secret"),
    url(r'^(?P<section>[-\w]+)/$', "biblion.views.blog_section_list", name="blog_section"),
)

########NEW FILE########
__FILENAME__ = utils
from django.core.exceptions import ImproperlyConfigured
try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

try:
    import twitter
except ImportError:
    twitter = None


from biblion.conf import settings


def can_tweet():
    creds_available = (hasattr(settings, "TWITTER_USERNAME") and
                       hasattr(settings, "TWITTER_PASSWORD"))
    return twitter and creds_available


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (module, attr))
    return attr

########NEW FILE########
__FILENAME__ = views
import json

from datetime import datetime

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string

from django.contrib.sites.models import Site

from biblion.conf import settings
from biblion.exceptions import InvalidSection
from biblion.models import Post, FeedHit
from biblion.signals import post_viewed


def blog_index(request):

    posts = Post.objects.current()

    return render_to_response("biblion/blog_list.html", {
        "posts": posts,
    }, context_instance=RequestContext(request))


def blog_section_list(request, section):

    try:
        posts = Post.objects.section(section)
    except InvalidSection:
        raise Http404()

    return render_to_response("biblion/blog_section_list.html", {
        "section_slug": section,
        "section_name": dict(Post.SECTION_CHOICES)[Post.section_idx(section)],
        "posts": posts,
    }, context_instance=RequestContext(request))


def blog_post_detail(request, **kwargs):

    if "post_pk" in kwargs:
        if request.user.is_authenticated() and request.user.is_staff:
            queryset = Post.objects.all()
            post = get_object_or_404(queryset, pk=kwargs["post_pk"])
        else:
            raise Http404()
    elif "post_secret_key" in kwargs:
        post = get_object_or_404(Post, secret_key=kwargs["post_secret_key"])
    else:
        queryset = Post.objects.current()
        queryset = queryset.filter(
            published__year=int(kwargs["year"]),
            published__month=int(kwargs["month"]),
            published__day=int(kwargs["day"]),
        )
        post = get_object_or_404(queryset, slug=kwargs["slug"])
        post_viewed.send(sender=post, post=post, request=request)

    return render_to_response("biblion/blog_post.html", {
        "post": post,
    }, context_instance=RequestContext(request))


def serialize_request(request):
    data = {
        "path": request.path,
        "META": {
            "QUERY_STRING": request.META.get("QUERY_STRING"),
            "REMOTE_ADDR": request.META.get("REMOTE_ADDR"),
        }
    }
    for key in request.META:
        if key.startswith("HTTP"):
            data["META"][key] = request.META[key]
    return json.dumps(data)


def blog_feed(request, section=None):

    try:
        posts = Post.objects.section(section)
    except InvalidSection:
        raise Http404()

    if section is None:
        section = settings.BIBLION_ALL_SECTION_NAME

    current_site = Site.objects.get_current()

    feed_title = "%s Blog: %s" % (current_site.name, section[0].upper() + section[1:])

    blog_url = "http://%s%s" % (current_site.domain, reverse("blog"))

    url_name, kwargs = "blog_feed", {"section": section}
    feed_url = "http://%s%s" % (current_site.domain, reverse(url_name, kwargs=kwargs))

    if posts:
        feed_updated = posts[0].published
    else:
        feed_updated = datetime(2009, 8, 1, 0, 0, 0)

    # create a feed hit
    hit = FeedHit()
    hit.request_data = serialize_request(request)
    hit.save()

    atom = render_to_string("biblion/atom_feed.xml", {
        "feed_id": feed_url,
        "feed_title": feed_title,
        "blog_url": blog_url,
        "feed_url": feed_url,
        "feed_updated": feed_updated,
        "entries": posts,
        "current_site": current_site,
    })
    return HttpResponse(atom, content_type="application/atom+xml")

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals

import os
import sys


extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
project = "biblion"
copyright_holder = "Eldarion, Inc."
copyright = "2014, {0}".format(copyright_holder)
exclude_patterns = ["_build"]
pygments_style = "sphinx"
html_theme = "default"
htmlhelp_basename = "{0}doc".format(project)
latex_documents = [(
    "index",
    "{0}.tex".format(project),
    "{0} Documentation".format(project),
    "Pinax",
    "manual"
),]
man_pages = [(
    "index",
    project,
    "{0} Documentation".format(project),
    ["Pinax"],
    1
),]

sys.path.insert(0, os.pardir)
m = __import__("biblion")

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

import django

from django.conf import settings


DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "biblion",
        "biblion.tests"
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    SITE_ID=1,
    ROOT_URLCONF="biblion.tests.urls",
    SECRET_KEY="notasecret",
)


def runtests(*test_args):
    if not settings.configured:
        settings.configure(**DEFAULT_SETTINGS)

    # Compatibility with Django 1.7's stricter initialization
    if hasattr(django, "setup"):
        django.setup()

    if not test_args:
        test_args = ["tests"]

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(
        verbosity=1, interactive=True, failfast=False).run_tests(test_args)
    sys.exit(failures)


if __name__ == "__main__":
    runtests(*sys.argv[1:])

########NEW FILE########
