__FILENAME__ = admin
from django.contrib import admin

from agora import models


class ForumThreadAdmin(admin.ModelAdmin):

    class ForumThreadReplyInline(admin.StackedInline):
        model = models.ForumReply
        extra = 1

    list_display = [
        "id",
        "title",
        "created",
        "author",
        "view_count",
        "reply_count",
        "subscriber_count",
    ]
    inlines = [
        ForumThreadReplyInline
    ]



admin.site.register(
    models.ForumCategory,
    list_display = [
        "title",
        "parent"
    ]
)
admin.site.register(
    models.Forum,
    list_display = [
        "id",
        "title",
        "parent",
        "category",
        "view_count",
        "post_count"
    ]
)
admin.site.register(models.ForumThread, ForumThreadAdmin)

########NEW FILE########
__FILENAME__ = callbacks
from django.utils.html import urlize, linebreaks, escape
from django.utils.safestring import mark_safe


def default_text(text):
    return mark_safe(linebreaks(urlize(escape(text))))

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings  # noqa
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib

from appconf import AppConf


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured("Error importing {0}: '{1}'".format(module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '{0}' does not define a '{1}'".format(module, attr))
    return attr


class AgoraAppConf(AppConf):

    PARSER = "agora.callbacks.default_text"
    EDIT_TIMEOUT = dict(minutes=3)

    def configure_parser(self, value):
        return load_path_attr(value)

########NEW FILE########
__FILENAME__ = forms
from django import forms

from agora.models import ForumThread, ForumReply


class PostForm(object):

    def __init__(self, *args, **kwargs):
        no_subscribe = kwargs.pop("no_subscribe", False)
        super(PostForm, self).__init__(*args, **kwargs)
        if no_subscribe:
            del self.fields["subscribe"]


class ThreadForm(PostForm, forms.ModelForm):

    subscribe = forms.BooleanField(required=False)

    class Meta:
        model = ForumThread
        fields = ["title", "content"]


class ReplyForm(PostForm, forms.ModelForm):

    subscribe = forms.BooleanField(required=False)

    class Meta:
        model = ForumReply
        fields = ["content"]

########NEW FILE########
__FILENAME__ = managers
from django.db import models


class ForumThreadPostQuerySet(models.query.QuerySet):

    def iterator(self):
        queryset = super(ForumThreadPostQuerySet, self).iterator()
        reverse = self._posts_manager_params["reverse"]
        thread = self._posts_manager_params["thread"]
        if not reverse:
            yield thread
        for obj in queryset:
            yield obj
        if reverse:
            yield thread

    def _clone(self, *args, **kwargs):
        kwargs["_posts_manager_params"] = self._posts_manager_params
        return super(ForumThreadPostQuerySet, self)._clone(*args, **kwargs)


class ForumThreadManager(models.Manager):

    def posts(self, thread, reverse=False):
        from agora.models import ForumReply  # @@@ this seems like a code smell
        queryset = ForumThreadPostQuerySet(ForumReply, using=self._db)
        queryset._posts_manager_params = {
            "reverse": reverse,
            "thread": thread,
        }
        queryset = queryset.filter(thread=thread)
        queryset = queryset.select_related("thread")
        queryset = queryset.order_by("{0}created".format(reverse and "-" or ""))
        return queryset

########NEW FILE########
__FILENAME__ = models
import datetime
import json

from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.html import conditional_escape

from django.contrib.auth.models import User

from agora.conf import settings
from agora.managers import ForumThreadManager


# this is the glue to the activity events framework, provided as a no-op here
def issue_update(kind, **kwargs):
    pass


class ForumCategory(models.Model):

    title = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="subcategories")

    # @@@ total descendant forum count?
    # @@@ make group-aware

    class Meta:
        verbose_name_plural = "forum categories"

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("agora_category", args=[self.pk])

    @property
    def forums(self):
        return self.forum_set.order_by("title")


class Forum(models.Model):

    title = models.CharField(max_length=100)
    description = models.TextField()
    closed = models.DateTimeField(null=True, blank=True)

    # must only have one of these (or neither):
    parent = models.ForeignKey("self",
        null=True,
        blank=True,
        related_name="subforums"
    )
    category = models.ForeignKey(ForumCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # @@@ make group-aware

    last_modified = models.DateTimeField(default=timezone.now, editable=False)
    last_thread = models.ForeignKey(
        "ForumThread",
        null=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    view_count = models.IntegerField(default=0, editable=False)
    post_count = models.IntegerField(default=0, editable=False)

    @property
    def thread_count(self):
        return self.threads.count()

    # this is what gets run normally
    def inc_views(self):
        self.view_count += 1
        self.save()

    # this can be used occasionally to get things back in sync
    def update_view_count(self):
        view_count = 0
        for thread in self.threads.all():
            view_count += thread.view_count
        self.view_count = view_count
        self.save()

    def update_post_count(self):
        post_count = 0
        for forum in self.subforums.all():
            forum.update_post_count()
            post_count += forum.post_count
        for thread in self.threads.all():
            thread.update_reply_count()
            post_count += thread.reply_count + 1  # add one for the thread itself
        self.post_count = post_count
        self.save()

    def new_post(self, post):
        self.post_count += 1  # if this gets out of sync run update_post_count
        self.last_modified = post.created
        self.last_thread = post.thread
        self.save()
        if self.parent:
            self.parent.new_post(post)

    def __unicode__(self):
        return self.title

    def update_last_thread(self):
        try:
            self.last_thread = self.threads.order_by("-created")[0]
        except IndexError:
            self.last_thread = None
        self.save()

    @property
    def last_post(self):
        if self.last_thread_id is None:
            return None
        else:
            return self.last_thread.last_post

    def export(self, out=None):
        if out is None:
            out = "forum-export-%d.json" % self.id
        data = {
            "self": {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "parent": self.parent_id,
                "category": self.category_id,
                "last_modified": self.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                "last_thread": self.last_thread_id,
                "view_count": self.view_count,
                "post_count": self.post_count
            },
            "threads": [
                {
                    "id": t.id,
                    "author": t.author_id,
                    "content": t.content,
                    "created": t.created.strftime("%Y-%m-%d %H:%M:%S"),
                    "forum": t.forum_id,
                    "title": t.title,
                    "last_modified": t.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_reply": t.last_reply_id,
                    "view_count": t.view_count,
                    "reply_count": t.reply_count,
                    "subscriber_count": t.subscriber_count,
                    "replies": [
                        {
                            "id": r.id,
                            "author": r.author_id,
                            "content": r.content,
                            "created": r.created.strftime("%Y-%m-%d %H:%M:%S"),
                            "thread": r.thread_id,
                        }
                        for r in t.replies.all()
                    ],
                    "subscriptions": [
                        {
                            "id": s.id,
                            "thread": s.thread_id,
                            "user": s.user_id,
                            "kind": s.kind,
                        }
                        for s in t.subscriptions.all()
                    ]
                }
                for t in self.threads.all()
            ]
        }
        json.dump(data, open(out, "wb"))

    @classmethod
    def restore(cls, in_):
        data = json.load(open(in_))
        forum = Forum(**dict(
            id=data["self"]["id"],
            title=data["self"]["title"],
            description=data["self"]["description"],
            parent_id=data["self"]["parent"],
            category_id=data["self"]["category"],
            last_modified=data["self"]["last_modified"],
            view_count=data["self"]["view_count"],
            post_count=data["self"]["post_count"]
        ))
        forum._importing = True
        forum.save()
        for thread_data in data["threads"]:
            thread = ForumThread(**dict(
                id=thread_data["id"],
                author_id=thread_data["author"],
                content=thread_data["content"],
                created=thread_data["created"],
                forum_id=thread_data["forum"],
                title=thread_data["title"],
                last_modified=thread_data["last_modified"],
                view_count=thread_data["view_count"],
                reply_count=thread_data["reply_count"],
                subscriber_count=thread_data["subscriber_count"]
            ))
            thread._importing = True
            thread.save()
            for reply_data in thread_data["replies"]:
                reply = ForumReply(**dict(
                    id=reply_data["id"],
                    author_id=reply_data["author"],
                    content=reply_data["content"],
                    created=reply_data["created"],
                    thread_id=reply_data["thread"],
                ))
                reply._importing = True
                reply.save()
            for subscriber_data in thread_data["subscriptions"]:
                ThreadSubscription(**dict(
                    id=subscriber_data["id"],
                    user_id=subscriber_data["user"],
                    thread_id=subscriber_data["thread"],
                    kind=subscriber_data["kind"],
                )).save()
            thread.last_reply_id = thread_data["last_reply"]
            thread.save()
        forum.last_thread_id = data["self"]["last_thread"]
        forum.save()


class ForumPost(models.Model):

    author = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_related")
    content = models.TextField()
    content_html = models.TextField()
    created = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        self.content_html = conditional_escape(settings.AGORA_PARSER(self.content))
        super(ForumPost, self).save(**kwargs)

    # allow editing for short period after posting
    def editable(self, user):
        if user == self.author:
            if timezone.now() < self.created + datetime.timedelta(**settings.AGORA_EDIT_TIMEOUT):
                return True
        return False


class ForumThread(ForumPost):

    # used for code that needs to know the kind of post this object is.
    kind = "thread"

    forum = models.ForeignKey(Forum, related_name="threads")
    title = models.CharField(max_length=100)
    last_modified = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    last_reply = models.ForeignKey(
        "ForumReply",
        null=True,
        editable=False,
        on_delete=models.SET_NULL
    )
    sticky = models.IntegerField(default=0)
    closed = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0, editable=False)
    reply_count = models.IntegerField(default=0, editable=False)
    subscriber_count = models.IntegerField(default=0, editable=False)

    objects = ForumThreadManager()

    def inc_views(self):
        self.view_count += 1
        self.save()
        self.forum.inc_views()

    def update_reply_count(self):
        self.reply_count = self.replies.all().count()
        self.save()

    def update_subscriber_count(self):
        self.subscriber_count = self.subscriptions.filter(kind="email").count()
        self.save()

    def new_reply(self, reply):
        self.reply_count += 1
        self.last_modified = reply.created
        self.last_reply = reply
        self.save()
        self.forum.new_post(reply)

    def subscribe(self, user, kind):
        """
        Subscribes the given user to this thread (handling duplicates)
        """
        ThreadSubscription.objects.get_or_create(thread=self, user=user, kind=kind)

    def unsubscribe(self, user, kind):
        try:
            subscription = ThreadSubscription.objects.get(thread=self, user=user, kind=kind)
        except ThreadSubscription.DoesNotExist:
            return
        else:
            subscription.delete()

    def subscribed(self, user, kind):
        if user.is_anonymous():
            return False
        try:
            ThreadSubscription.objects.get(thread=self, user=user, kind=kind)
        except ThreadSubscription.DoesNotExist:
            return False
        else:
            return True

    def __unicode__(self):
        return self.title

    def update_last_reply(self):
        try:
            self.last_reply = self.replies.order_by("-created")[0]
        except IndexError:
            self.last_reply = None
        self.save()

    @property
    def last_post(self):
        if self.last_reply_id is None:
            return self
        else:
            return self.last_reply

    @property
    def thread(self):
        return self


class ForumReply(ForumPost):

    # used for code that needs to know the kind of post this object is.
    kind = "reply"

    thread = models.ForeignKey(ForumThread, related_name="replies")

    class Meta:
        verbose_name = "forum reply"
        verbose_name_plural = "forum replies"


class UserPostCount(models.Model):

    user = models.ForeignKey(User, related_name="post_count")
    count = models.IntegerField(default=0)

    @classmethod
    def calculate(cls):
        for user in User.objects.all():
            thread_count = ForumThread.objects.filter(author=user).count()
            reply_count = ForumReply.objects.filter(author=user).count()
            count = thread_count + reply_count
            upc, created = cls._default_manager.get_or_create(
                user=user,
                defaults=dict(
                    count=count
                )
            )
            if not created:
                upc.count = count
                upc.save()


class ThreadSubscription(models.Model):

    thread = models.ForeignKey(ForumThread, related_name="subscriptions")
    user = models.ForeignKey(User, related_name="forum_subscriptions")
    kind = models.CharField(max_length=15)

    class Meta:
        unique_together = [("thread", "user", "kind")]

    @classmethod
    def setup_onsite(cls):
        for user in User.objects.all():
            threads = ForumThread.objects.filter(author=user).values_list("pk", flat=True)
            threads_by_replies = ForumReply.objects.filter(author=user).distinct().values_list("thread", flat=True)
            for thread in set(threads).union(threads_by_replies):
                ForumThread.objects.get(pk=thread).subscribe(user, "onsite")

########NEW FILE########
__FILENAME__ = receivers
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from agora.models import ForumThread, ForumReply, ThreadSubscription, UserPostCount


@receiver(post_save, sender=ForumThread)
def forum_thread_save(sender, instance=None, created=False, **kwargs):
    if instance and created:
        forum = instance.forum
        forum.new_post(instance)

        # @@@ this next part could be manager method
        post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
        post_count.count += 1
        post_count.save()


@receiver(post_save, sender=ForumReply)
def forum_reply_save(sender, instance=None, created=False, **kwargs):
    if instance and created:
        thread = instance.thread
        thread.new_reply(instance)

        # @@@ this next part could be manager method
        post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
        post_count.count += 1
        post_count.save()


@receiver(pre_delete, sender=ForumThread)
def forum_thread_delete(sender, **kwargs):
    thread = kwargs["instance"]
    if thread.id == thread.forum.last_thread_id:
        thread.forum.update_last_thread()
    thread.forum.update_view_count()
    thread.forum.update_post_count()


@receiver(pre_delete, sender=ForumReply)
def forum_reply_delete(sender, **kwargs):
    reply = kwargs["instance"]
    if reply.id == reply.thread.last_reply_id:
        reply.thread.update_last_reply()
    reply.thread.forum.update_post_count()


@receiver(post_save, sender=ThreadSubscription)
def forum_subscription_update(sender, instance=None, created=False, **kwargs):
    if instance and created:
        thread = instance.thread
        thread.update_subscriber_count()

########NEW FILE########
__FILENAME__ = agora_tags
from django import template
from django.core.urlresolvers import reverse

from agora.models import ThreadSubscription


register = template.Library()


class SubscriptionNode(template.Node):

    def __init__(self, user, varname, thread_list=None):
        self.user = template.Variable(user)
        if thread_list:
            self.thread_list = [template.Variable(t) for t in thread_list]
        self.varname = varname

    def render(self, context):
        user = self.user.resolve(context)
        threads = ThreadSubscription.objects.filter(user=user)
        if self.thread_list:
            threads = threads.filter(thread__in=self.thread_list)
        context[self.varname] = threads
        return ""


@register.tag
def subscriptions(parser, token):
    """
    {% subscriptions for user as varname %}
    """
    tag, _, user, _, varname = token.split_contents()
    return SubscriptionNode(user, varname)


@register.tag
def filter_subscriptions(parser, token):
    """
    {% filter_subscriptions user thread_list as subscribed_threads %}
    """
    tag, user, thread_list, _, varname = token.split_contents()
    return SubscriptionNode(user, varname, thread_list)


class SubscribeUrlNode(template.Node):

    def __init__(self, user, thread, varname, subscribe=True):
        self.user = template.Variable(user)
        self.thread = template.Variable(thread)
        self.varname = varname
        self.viewname = "agora_unsubscribe"
        if subscribe:
            self.viewname = "agora_subscribe"

    def render(self, context):
        user = self.user.resolve(context)
        thread = self.thread.resolve(context)
        context[self.varname] = reverse(self.viewname, kwargs={
            "user_id": user.id,
            "thread_id": thread.id
        })
        return ""


@register.tag
def subscribe_url(parser, token):
    """
    {% subscribe_url user_obj thread_obj as theurl %}
    """
    tag, user, _, thread, _, varname = token.split_contents()
    return SubscribeUrlNode(user, thread, varname)


@register.tag
def unsubscribe_url(parser, token):
    """
    {% unsubscribe_url user_obj thread_obj as theurl %}
    """
    tag, user, _, thread, _, varname = token.split_contents()
    return SubscribeUrlNode(user, thread, varname, subscribe=False)


@register.filter
def post_editable(post, user):
    return post.editable(user)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns(
    "agora.views",
    url(r"^$", "forums", name="agora_forums"),
    url(r"^category/(\d+)/$", "forum_category", name="agora_category"),
    url(r"^forum/(\d+)/$", "forum", name="agora_forum"),
    url(r"^thread/(\d+)/$", "forum_thread", name="agora_thread"),
    url(r"^new_post/(\d+)/$", "post_create", name="agora_post_create"),
    url(r"^reply/(\d+)/$", "reply_create", name="agora_reply_create"),
    url(r"^post_edit/(thread|reply)/(\d+)/$", "post_edit", name="agora_post_edit"),
    url(r"^subscribe/(\d+)/$", "subscribe", name="agora_subscribe"),
    url(r"^unsubscribe/(\d+)/$", "unsubscribe", name="agora_unsubscribe"),
    url(r"^thread_updates/$", "thread_updates", name="agora_thread_updates"),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from agora.forms import ThreadForm, ReplyForm
from agora.models import (
    Forum,
    ForumCategory,
    ForumReply,
    ForumThread,
    ThreadSubscription,
    UserPostCount
)


def forums(request):

    categories = ForumCategory.objects.filter(parent__isnull=True)
    categories = categories.order_by("title")

    most_active_forums = Forum.objects.order_by("-post_count")[:5]
    most_viewed_forums = Forum.objects.order_by("-view_count")[:5]
    most_active_members = UserPostCount.objects.order_by("-count")[:5]

    latest_posts = ForumReply.objects.order_by("-created")[:10]
    latest_threads = ForumThread.objects.order_by("-last_modified")
    most_active_threads = ForumThread.objects.order_by("-reply_count")
    most_viewed_threads = ForumThread.objects.order_by("-view_count")

    return render_to_response("agora/forums.html", {
        "categories": categories,
        "most_active_forums": most_active_forums,
        "most_viewed_forums": most_viewed_forums,
        "most_active_members": most_active_members,
        "latest_posts": latest_posts,
        "latest_threads": latest_threads,
        "most_active_threads": most_active_threads,
        "most_viewed_threads": most_viewed_threads,
    }, context_instance=RequestContext(request))


def forum_category(request, category_id):

    category = get_object_or_404(ForumCategory, id=category_id)
    forums = category.forums.order_by("title")

    return render_to_response("agora/category.html", {
        "category": category,
        "forums": forums,
    }, context_instance=RequestContext(request))


def forum(request, forum_id):

    forum = get_object_or_404(Forum, id=forum_id)
    threads = forum.threads.order_by("-sticky", "-last_modified")

    can_create_thread = all([
        request.user.has_perm("agora.add_forumthread", obj=forum),
        not forum.closed,
    ])

    return render_to_response("agora/forum.html", {
        "forum": forum,
        "threads": threads,
        "can_create_thread": can_create_thread,
    }, context_instance=RequestContext(request))


def forum_thread(request, thread_id):
    qs = ForumThread.objects.select_related("forum")
    thread = get_object_or_404(qs, id=thread_id)

    can_create_reply = all([
        request.user.has_perm("agora.add_forumreply", obj=thread),
        not thread.closed,
        not thread.forum.closed,
    ])

    if can_create_reply:
        if request.method == "POST":
            reply_form = ReplyForm(request.POST)

            if reply_form.is_valid():
                reply = reply_form.save(commit=False)
                reply.thread = thread
                reply.author = request.user
                reply.save()

                # subscribe the poster to the thread if requested (default value is True)
                if reply_form.cleaned_data["subscribe"]:
                    thread.subscribe(reply.author, "email")

                # all users are automatically subscribed to onsite
                thread.subscribe(reply.author, "onsite")

                return HttpResponseRedirect(reverse("agora_thread", args=[thread.id]))
        else:
            reply_form = ReplyForm()
    else:
        reply_form = None

    order_type = request.GET.get("order_type", "asc")
    posts = ForumThread.objects.posts(thread, reverse=(order_type == "desc"))
    thread.inc_views()

    return render_to_response("agora/thread.html", {
        "thread": thread,
        "posts": posts,
        "order_type": order_type,
        "subscribed": thread.subscribed(request.user, "email"),
        "reply_form": reply_form,
        "can_create_reply": can_create_reply,
    }, context_instance=RequestContext(request))


@login_required
def post_create(request, forum_id):

    member = request.user.get_profile()
    forum = get_object_or_404(Forum, id=forum_id)

    if forum.closed:
        messages.error(request, "This forum is closed.")
        return HttpResponseRedirect(reverse("agora_forum", args=[forum.id]))

    can_create_thread = request.user.has_perm("agora.add_forumthread", obj=forum)

    if not can_create_thread:
        messages.error(request, "You do not have permission to create a thread.")
        return HttpResponseRedirect(reverse("agora_forum", args=[forum.id]))

    if request.method == "POST":
        form = ThreadForm(request.POST)

        if form.is_valid():
            thread = form.save(commit=False)
            thread.forum = forum
            thread.author = request.user
            thread.save()

            # subscribe the poster to the thread if requested (default value is True)
            if form.cleaned_data["subscribe"]:
                thread.subscribe(thread.author, "email")

            # all users are automatically subscribed to onsite
            thread.subscribe(thread.author, "onsite")

            return HttpResponseRedirect(reverse("agora_thread", args=[thread.id]))
    else:
        form = ThreadForm()

    return render_to_response("agora/post_create.html", {
        "form": form,
        "member": member,
        "forum": forum
    }, context_instance=RequestContext(request))


@login_required
def reply_create(request, thread_id):

    member = request.user.get_profile()
    thread = get_object_or_404(ForumThread, id=thread_id)

    if thread.closed:
        messages.error(request, "This thread is closed.")
        return HttpResponseRedirect(reverse("agora_thread", args=[thread.id]))

    can_create_reply = request.user.has_perm("agora.add_forumreply", obj=thread)

    if not can_create_reply:
        messages.error(request, "You do not have permission to reply to this thread.")
        return HttpResponseRedirect(reverse("agora_thread", args=[thread.id]))

    if request.method == "POST":
        form = ReplyForm(request.POST)

        if form.is_valid():
            reply = form.save(commit=False)
            reply.thread = thread
            reply.author = request.user
            reply.save()

            # subscribe the poster to the thread if requested (default value is True)
            if form.cleaned_data["subscribe"]:
                thread.subscribe(reply.author, "email")

            # all users are automatically subscribed to onsite
            thread.subscribe(reply.author, "onsite")

            return HttpResponseRedirect(reverse("agora_thread", args=[thread_id]))
    else:
        quote = request.GET.get("quote") # thread id to quote
        initial = {}

        if quote:
            quote_reply = ForumReply.objects.get(id=int(quote))
            initial["content"] = "\"%s\"" % quote_reply.content

        form = ReplyForm(initial=initial)

    first_reply = not ForumReply.objects.filter(thread=thread, author=request.user).exists()

    return render_to_response("agora/reply_create.html", {
        "form": form,
        "member": member,
        "thread": thread,
        "subscribed": thread.subscribed(request.user, "email"),
        "first_reply": first_reply,
    }, context_instance=RequestContext(request))


@login_required
def post_edit(request, post_kind, post_id):

    if post_kind == "thread":
        post = get_object_or_404(ForumThread, id=post_id)
        thread_id = post.id
        form_class = ThreadForm
    elif post_kind == "reply":
        post = get_object_or_404(ForumReply, id=post_id)
        thread_id = post.thread.id
        form_class = ReplyForm
    else:
        raise Http404()

    if not post.editable(request.user):
        raise Http404()

    if request.method == "POST":
        form = form_class(request.POST, instance=post, no_subscribe=True)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("agora_thread", args=[thread_id]))
    else:
        form = form_class(instance=post, no_subscribe=True)

    return render_to_response("agora/post_edit.html", {
        "post": post,
        "form": form,
    }, context_instance=RequestContext(request))


@login_required
def subscribe(request, thread_id):
    user = request.user
    thread = get_object_or_404(ForumThread, pk=thread_id)

    if request.method == "POST":
        thread.subscribe(user, "email")
        return HttpResponseRedirect(reverse("agora_thread", args=[thread_id]))
    else:
        ctx = RequestContext(request, {"thread": thread})
        return render_to_response("agora/subscribe.html", ctx)


@login_required
def unsubscribe(request, thread_id):
    user = request.user
    thread = get_object_or_404(ForumThread, pk=thread_id)

    if request.method == "POST":
        thread.unsubscribe(user, "email")
        return HttpResponseRedirect(reverse("agora_thread", args=[thread_id]))
    else:
        ctx = RequestContext(request, {"thread": thread})
        return render_to_response("agora/unsubscribe.html", ctx)


@login_required
def thread_updates(request):
    subscriptions = ThreadSubscription.objects.filter(user=request.user, kind="onsite")
    subscriptions = subscriptions.select_related("thread", "user")
    subscriptions = subscriptions.order_by("-thread__last_modified")

    if request.method == "POST":
        subscriptions.filter(pk=request.POST["thread_id"]).delete()

    ctx = {
        "subscriptions": subscriptions,
    }
    ctx = RequestContext(request, ctx)
    return render_to_response("agora/thread_updates.html", ctx)

########NEW FILE########
