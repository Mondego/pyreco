__FILENAME__ = admin
from django.contrib import admin
from dbe.blog.models import *


class PostAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    display_fields = "title created".split()

class CommentAdmin(admin.ModelAdmin):
    display_fields = "post author created".split()

admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.forms import *
from dbe.blog.models import *

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        exclude = ["post"]

    def clean_author(self):
        return self.cleaned_data.get("author") or "Anonymous"

########NEW FILE########
__FILENAME__ = models
from django.db.models import *
from django.contrib.auth.models import User
from django.contrib import admin
from django.core.mail import send_mail

from dbe.shared.utils import *

notify = False

class Post(BaseModel):
    title   = CharField(max_length=60)
    body    = TextField()
    created = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __unicode__(self):
        return self.title


class Comment(BaseModel):
    author  = CharField(max_length=60, blank=True)
    body    = TextField()
    post    = ForeignKey(Post, related_name="comments",  blank=True, null=True)
    created = DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"%s: %s" % (self.post, self.body[:60])

    def save(self, *args, **kwargs):
        """Email when a comment is added."""
        if notify:
            tpl            = "Comment was was added to '%s' by '%s': \n\n%s"
            message        = tpl % (self.post, self.author, self.body)
            from_addr      = "no-reply@mydomain.com"
            recipient_list = ["myemail@mydomain.com"]

            send_mail("New comment added", message, from_addr, recipient_list)
        super(Comment, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from dbe.blog.models import *
from dbe.blog.views import PostView, Main, ArchiveMonth

urlpatterns = patterns("dbe.blog.views",
   (r"^post/(?P<dpk>\d+)/$"          , PostView.as_view(), {}, "post"),
   (r"^archive_month/(\d+)/(\d+)/$"  , ArchiveMonth.as_view(), {}, "archive_month"),
   (r"^$"                            , Main.as_view(), {}, "main"),
   # (r"^delete_comment/(\d+)/$"       , "delete_comment", {}, "delete_comment"),
)

########NEW FILE########
__FILENAME__ = views
# Imports {{{
import time
from calendar import month_name

from dbe.blog.models import *
from dbe.blog.forms import *
from dbe.shared.utils import *

from dbe.mcbv.list import ListView
from dbe.mcbv.list_custom import DetailListCreateView
# }}}


class PostView(DetailListCreateView):
    """Show post, associated comments and an 'add comment' form."""
    detail_model    = Post
    list_model      = Comment
    modelform_class = CommentForm
    related_name    = "comments"
    fk_attr         = "post"
    template_name   = "blog/post.html"


class Main(ListView):
    list_model    = Post
    paginate_by   = 10
    template_name = "blog/list.html"

    def months(self):
        """Make a list of months to show archive links."""
        if not Post.obj.count(): return list()

        # set up variables
        current_year, current_month = time.localtime()[:2]
        first       = Post.obj.order_by("created")[0]
        first_year  = first.created.year
        first_month = first.created.month
        months      = list()

        # loop over years and months
        for year in range(current_year, first_year-1, -1):
            start, end = 12, 0
            if year == current_year : start = current_month
            if year == first_year   : end = first_month - 1

            for month in range(start, end, -1):
                if Post.obj.filter(created__year=year, created__month=month):
                    months.append((year, month, month_name[month]))
        return months


class ArchiveMonth(Main):
    paginate_by = None

    def get_list_queryset(self):
        year, month = self.args
        return Post.obj.filter(created__year=year, created__month=month).order_by("created")

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from dbe.bombquiz.models import *

class QuestionAdmin(admin.ModelAdmin):
    list_display = "question answer order".split()

class PlayerRecordAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "passed"]

class AnswerAdmin(admin.ModelAdmin):
    list_display = "answer player_record question correct".split()


admin.site.register(Question, QuestionAdmin)
admin.site.register(PlayerRecord, PlayerRecordAdmin)
admin.site.register(Answer, AnswerAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms as f
from django.forms.widgets import RadioSelect
from dbe.bombquiz.models import *

null_choice = [("---", "---")]
choices = [(c,c) for c in "yes no pass".split()]


class NewPlayerForm(f.ModelForm):
    class Meta:
        model   = PlayerRecord
        exclude = ["passed"]

class QuestionForm(f.Form):
    def __init__(self, *args, **kwargs):
        """Add the field for `question`."""
        question = kwargs.pop("question").question
        super(QuestionForm, self).__init__(*args, **kwargs)
        field = f.ChoiceField(choices=choices, widget=RadioSelect, help_text=question)
        self.fields["answer"] = field

########NEW FILE########
__FILENAME__ = models
from django.db.models import *
from dbe.shared.utils import *


class Question(BaseModel):
    question = CharField(max_length=200, unique=True)
    answer   = CharField(max_length=60)
    order    = IntegerField(unique=True)

    def __unicode__(self):
        return "%d. %s - %s" % (self.order, self.question, self.answer)

    class Meta:
        ordering = ["order"]


class PlayerRecord(BaseModel):
    name    = CharField(max_length=60)
    email   = EmailField(max_length=120)
    created = DateTimeField(auto_now_add=True)
    passed  = BooleanField(default=False)

    def __unicode__(self):
        return "%s - %s" % (self.name, self.email)

    class Meta:
        ordering        = ["created"]
        unique_together = [["name", "email"]]


class Answer(BaseModel):
    answer        = CharField(max_length=60)
    player_record = ForeignKey(PlayerRecord, related_name="answers")
    question      = ForeignKey(Question, related_name="answers")
    correct       = BooleanField()

    def __unicode__(self):
        return "%s, %s" % (self.answer, self.correct)

    class Meta:
        ordering        = ["question__order"]
        unique_together = [["question", "player_record"]]

########NEW FILE########
__FILENAME__ = todo
from django import template
from django.conf import settings

register = template.Library()

def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID

def get(value, arg):
    return value[arg]

def concat(value, arg):
    return value + arg


register.filter("getattribute", getattribute)
register.filter("get", get)
register.filter("concat", concat)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from dbe.bombquiz.views import *

urlpatterns = patterns("dbe.bombquiz.views",
    (r"^$"          , NewPlayer.as_view(), {}, "new_player"),
    (r"^question/$" , QuestionView.as_view(), {}, "question"),
    (r"^done/$"     , Done.as_view(), {}, "bqdone"),
    (r"^stats/$"    , Stats.as_view(), {}, "stats"),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse_lazy
from django.db.models import Count, Avg
from django.http import Http404

from dbe.shared.utils import *
from dbe.bombquiz.models import *
from dbe.bombquiz.forms import *

from dbe.mcbv.base import TemplateView
from dbe.mcbv.edit import CreateView, FormView

seconds       = 30
lose_question = 20


class NewPlayer(CreateView):
    """Create new player & add data to session."""
    form_model      = PlayerRecord
    modelform_class = NewPlayerForm
    success_url     = reverse_lazy("question")
    template_name   = "newplayer.html"

    def modelform_valid(self, modelform):
        resp = super(NewPlayer, self).modelform_valid(modelform)
        data = dict(player_record=self.modelform_object, question=1, left=seconds)
        self.request.session.update(data)
        return resp


class Stats(TemplateView):
    template_name = "stats.html"

    def add_context(self):
        records   = PlayerRecord.obj.filter(passed=False)
        answer    = records.annotate(anum=Count("answers"))
        aggregate = answer.aggregate(avg=Avg("anum"))
        return dict(ans_failed=aggregate)


class QuestionView(FormView):
    form_class    = QuestionForm
    template_name = "question.html"

    def get_form_kwargs(self):
        """Get current section (container), init the form based on questions in the section."""
        kwargs      = super(QuestionView, self).get_form_kwargs()
        session     = self.request.session
        self.player = session.get("player_record")
        self.qn     = session.get("question", 1)
        if not self.player: raise Http404

        self.questions = Question.obj.all()
        if not self.questions: raise Http404

        self.question = self.questions[self.qn-1]
        return dict(kwargs, question=self.question)

    def form_valid(self, form):
        """Create user answer records from form data."""
        session = self.request.session
        left    = session.get("left", seconds)
        answer  = form.cleaned_data.get("answer")
        correct = bool(answer == self.question.answer)

        # subtract time left and create the answer object
        if not correct:
            left -= lose_question
            session["left"] = left
        Answer.obj.create(question=self.question, player_record=self.player, correct=correct, answer=answer)

        # redirect to the next question or to 'done' page
        if self.qn >= self.questions.count() or left <= 0:
            self.player.update( passed=bool(left > 0) )
            return redir("bqdone")
        else:
            session["question"] = session.get("question", 1) + 1
            return redir("question")

    def add_context(self):
        session = self.request.session
        return dict(qnum=self.qn, total=self.questions.count(), left=session["left"])


class Done(TemplateView):
    template_name = "bombquiz/done.html"

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from dbe.forum.models import *

class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user"]

class ForumAdmin(admin.ModelAdmin):
    pass

class ThreadAdmin(admin.ModelAdmin):
    list_display = "title forum creator created".split()
    list_filter  = "forum creator".split()

class PostAdmin(admin.ModelAdmin):
    search_fields = "title creator".split()
    list_display  = "title thread creator created".split()


def create_user_profile(sender, **kwargs):
    """When creating a new user, make a profile for him."""
    user = kwargs["instance"]
    if not UserProfile.objects.filter(user=user):
        UserProfile(user=user).save()

post_save.connect(create_user_profile, sender=User)

admin.site.register(Forum, ForumAdmin)
admin.site.register(Thread, ThreadAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(UserProfile, ProfileAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm
from dbe.forum.models import *
from dbe.shared.utils import ContainerFormMixin

class ProfileForm(ModelForm):
    class Meta:
        model   = UserProfile
        exclude = ["posts", "user"]

class PostForm(ContainerFormMixin, ModelForm):
    class Meta:
        model   = Post
        exclude = ["creator", "thread"]

########NEW FILE########
__FILENAME__ = models
from django.db.models import *
from django.contrib.auth.models import User
from django.contrib import admin
from django.db.models.signals import post_save

from dbe.settings import MEDIA_URL
from dbe.shared.utils import *


class Forum(BaseModel):
    title = CharField(max_length=60)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse2("forum", dpk=self.pk)

    def num_posts(self):
        return sum([t.num_posts() for t in self.threads.all()])

    def last_post(self):
        """Go over the list of threads and find the most recent post."""
        threads = self.threads.all()
        last    = None
        for thread in threads:
            lastp = thread.last_post()
            if lastp and (not last or lastp.created > last.created):
                last = lastp
        return last


class Thread(BaseModel):
    title   = CharField(max_length=60)
    created = DateTimeField(auto_now_add=True)
    creator = ForeignKey(User, blank=True, null=True)
    forum   = ForeignKey(Forum, related_name="threads")

    class Meta:
        ordering = ["-created"]

    def __unicode__(self):
        return unicode("%s - %s" % (self.creator, self.title))

    def get_absolute_url(self) : return reverse2("thread", dpk=self.pk)
    def last_post(self)        : return first(self.posts.all())
    def num_posts(self)        : return self.posts.count()
    def num_replies(self)      : return self.posts.count() - 1


class Post(BaseModel):
    title   = CharField(max_length=60)
    created = DateTimeField(auto_now_add=True)
    creator = ForeignKey(User, blank=True, null=True)
    thread  = ForeignKey(Thread, related_name="posts")
    body    = TextField(max_length=10000)

    class Meta:
        ordering = ["created"]

    def __unicode__(self):
        return u"%s - %s - %s" % (self.creator, self.thread, self.title)

    def short(self):
        created = self.created.strftime("%b %d, %I:%M %p")
        return u"%s - %s\n%s" % (self.creator, self.title, created)

    def profile_data(self):
        p = self.creator.profile
        return p.posts, p.avatar


class UserProfile(BaseModel):
    avatar = ImageField("Profile Pic", upload_to="images/", blank=True, null=True)
    posts  = IntegerField(default=0)
    user   = OneToOneField(User, related_name="profile")

    def __unicode__(self):
        return unicode(self.user)

    def increment_posts(self):
        self.posts += 1
        self.save()

    def avatar_image(self):
        return (MEDIA_URL + self.avatar.name) if self.avatar else None

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from dbe.forum.models import *

class SimpleTest(TestCase):
    def setUp(self):
        forum  = Forum.objects.create(title="forum")
        user   = User.objects.create_user("ak", "ak@abc.org", "pwd")
        thread = Thread.objects.create(title="thread", creator=user, forum=forum)

        UserProfile.objects.create(user=user)
        Site.objects.create(domain="test.org", name="test.org")
        Post.objects.create(title="post", body="body", creator=user, thread=thread)

    def content_test(self, url, values):
        """Get content of url and test that each of items in `values` list is present."""
        r = self.c.get(url)
        self.assertEquals(r.status_code, 200)
        for v in values:
            self.assertTrue(v in r.content)

    def test(self):
        self.c = Client()
        self.c.login(username="ak", password="pwd")

        # test forum listing, thread listing and post page
        self.content_test("/forum/", ['<a href="/forum/forum/1/">forum</a>'])
        self.content_test("/forum/forum/1/", ['<a href="/forum/thread/1/">thread</a>', "ak - post"])

        self.content_test("/forum/thread/1/",
              ['<div class="ttitle">thread</div>',
               '<span class="title">post</span>',
               'body <br />', 'by ak |'])

        # test creation of a new thread and a reply
        r = self.c.post("/forum/new_topic/1/", {"title": "thread2", "body": "body2"})
        r = self.c.post("/forum/reply/2/", {"title": "post2", "body": "body3"})

        self.content_test("/forum/thread/2/",
                ['<div class="ttitle">thread2</div>',
                 '<span class="title">post2</span>',
                 'body2 <br />', 'body3 <br />'])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required as LR
from dbe.forum.models import *
from dbe.forum.views import *

urlpatterns = patterns("dbe.forum.views",
    (r"^forum/(?P<dpk>\d+)/$"             , ForumView.as_view(), {}, "forum"),
    (r"^thread/(?P<dpk>\d+)/$"            , ThreadView.as_view(), {}, "thread"),

    (r"^new_topic/(?P<dpk>\d+)/$"          , LR(NewTopic.as_view()), {}, "new_topic"),
    (r"^reply/(?P<dpk>\d+)/$"              , LR(Reply.as_view()), {}, "reply"),
    (r"^profile/(?P<mfpk>\d+)/$"           , LR(EditProfile.as_view()), {}, "profile"),

    (r""                                   , Main.as_view(), {}, "forum_main"),
)

########NEW FILE########
__FILENAME__ = views
# Imports {{{
from PIL import Image as PImage

from dbe.settings import MEDIA_URL
from dbe.forum.models import *
from dbe.shared.utils import *

from dbe.mcbv.detail import DetailView
from dbe.mcbv.edit import CreateView, UpdateView
from dbe.mcbv.list_custom import ListView, ListRelated

from forms import ProfileForm, PostForm
# }}}


class Main(ListView):
    list_model    = Forum
    template_name = "forum/list.html"

class ForumView(ListRelated):
    detail_model  = Forum
    list_model    = Thread
    related_name  = "threads"
    template_name = "forum.html"

class ThreadView(ListRelated):
    list_model    = Post
    detail_model  = Thread
    related_name  = "posts"
    template_name = "thread.html"


class EditProfile(UpdateView):
    form_model      = UserProfile
    modelform_class = ProfileForm
    success_url     = '#'
    template_name   = "profile.html"

    def modelform_valid(self, modelform):
        """Resize and save profile image."""
        # remove old image if changed
        name = modelform.cleaned_data.get("avatar")
        pk   = self.kwargs.get("mfpk")
        old  = UserProfile.obj.get(pk=pk).avatar

        if old.name and old.name != name:
            old.delete()

        # save new image to disk & resize new image
        self.modelform_object = modelform.save()
        if self.modelform_object.avatar:
            img = PImage.open(self.modelform_object.avatar.path)
            img.thumbnail((160,160), PImage.ANTIALIAS)
            img.save(img.filename, "JPEG")
        return redir(self.success_url)


class NewTopic(DetailView, CreateView):
    detail_model    = Forum
    form_model      = Post
    modelform_class = PostForm
    title           = "Start New Topic"
    template_name   = "forum/post.html"

    def get_thread(self, modelform):
        title = modelform.cleaned_data.title
        return Thread.obj.create(forum=self.get_detail_object(), title=title, creator=self.user)

    def modelform_valid(self, modelform):
        """Create new thread and its first post."""
        data   = modelform.cleaned_data
        thread = self.get_thread(modelform)

        Post.obj.create(thread=thread, title=data.title, body=data.body, creator=self.user)
        self.user.profile.increment_posts()
        return redir(self.get_success_url())

    def get_success_url(self):
        return self.get_detail_object().get_absolute_url()


class Reply(NewTopic):
    detail_model = Thread
    title        = "Reply"

    def get_thread(self, modelform):
        return self.get_detail_object()

    def get_success_url(self):
        return self.get_detail_object().get_absolute_url() + "?page=last"


def forum_context(request):
    return dict(media_url=MEDIA_URL)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from dbe.issues.models import *

class ProjectAdmin(admin.ModelAdmin):
    list_display = ["project"]

class TagsAdmin(admin.ModelAdmin):
    list_display = ["tag"]

class CommentAdmin(admin.ModelAdmin):
    pass
    # list_display = ["tag"]

class IssueAdmin(admin.ModelAdmin):
    list_display   = "name_ owner_ priority difficulty project_ created_ progress_ closed_ delete_".split()
    list_filter    = "priority difficulty project tags closed owner".split()
    date_hierarchy = "created"
    # search_fields = ["name", "tags"]

admin.site.register(Comment, CommentAdmin)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Tag, TagsAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms as f
from django.forms import widgets
from django.forms.widgets import *
from django.utils.safestring import mark_safe

from dbe.issues.models import *


class SelectAndTextInput(widgets.MultiWidget):
    """A Widget with select and text input field."""
    is_required = False
    input_fields = 1

    def __init__(self, choices=(), initial=None, attrs=None):
        widgets = self.get_widgets(choices, initial, attrs)
        super(SelectAndTextInput, self).__init__(widgets, attrs)

    def get_widgets(self, c, i, attrs):
        return [Select(attrs=attrs, choices=c), TextInput(attrs=attrs)]

    def decompress(self, value):
        return value or [None]*(self.input_fields+1)

    def format_output(self, rendered_widgets):
        return u' '.join(rendered_widgets)


class MultiSelectCreate(SelectAndTextInput):
    """Widget with multiple select and multiple input fields."""
    input_fields = 6

    def get_widgets(self, c, i, attrs):
        return [SelectMultiple(attrs=attrs, choices=c)] + [TextInput(attrs=attrs) for _ in range(self.input_fields)]

    def format_output(self, lst):
        lst.insert(0, "<table border='0'><tr><td>")
        lst.insert(2, "</td><td>")
        lst.append("</td></tr></table>")
        return u''.join(lst)


#### Fields

class SelectOrCreateField(f.MultiValueField):
    """SelectAndTextField - select from a dropdown or add new using text inputs."""
    widgetcls    = SelectAndTextInput
    extra_inputs = 1

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop("choices", ())
        initial = kwargs.pop("initial", {})
        fields = self.get_fields(choices, initial)
        super(SelectOrCreateField, self).__init__(fields, *args, **kwargs)
        self.widget = self.widgetcls(choices, initial)
        self.initial = [initial] + [u'']*self.extra_inputs
        self.required = False

    def get_fields(self, choices, initial):
        return [f.ChoiceField(choices=choices, initial=initial), f.CharField()]

    def to_python(self, value):
        return value

    def set_choices(self, choices):
        self.fields[0].choices = self.widget.widgets[0].choices = choices
        initial = choices[0][0]
        self.fields[0].initial = choices[0][0]
        self.widget.widgets[0].initial = choices[0][0]

    def compress(self, lst):
        choice, new = lst[0], lst[1].strip()
        return (new, True) if new else (choice, False)

class TagsSelectCreateField(SelectOrCreateField):
    widgetcls    = MultiSelectCreate
    extra_inputs = 6

    def get_fields(self, c, i):
        return [f.MultipleChoiceField(choices=c, initial=i)] + \
                [f.CharField() for _ in range(self.extra_inputs)]

    def compress(self, lst):
        return [lst[0]] + [x.strip() for x in lst[1:] if x.strip()] if lst else None


# FORMS

class CommentForm(f.ModelForm):
    class Meta:
        model   = Comment
        exclude = "creator issue created body_html".split()

    textarea = f.Textarea( attrs=dict(cols=65, rows=18) )
    body     = f.CharField(widget=textarea, required=False)


class CreateIssueForm(f.ModelForm):
    class Meta:
        model   = Issue
        exclude = "creator project tags closed body_html progress".split()

    def __init__(self, *args, **kwargs):
        """ Set choices filtered by current user, set initial values.

            TODO: change SelectOrCreateField to auto-load foreign key choices and select current one.
        """
        kwargs = copy.copy(kwargs)
        user = self.user = kwargs.pop("user", None)
        super(CreateIssueForm, self).__init__(*args, **kwargs)

        values = Project.obj.all().values_list("pk", "project")
        values = [(0, "---")] + list(values)
        self.fields["project_"] = SelectOrCreateField(choices=values, initial=0)

        values = Tag.obj.all().values_list("pk", "tag")
        if values: self.fields["tags_"].set_choices(values)

        # set initial values
        inst = self.instance
        if inst.pk:
            if inst.project:
                self.initial["project_"] = [inst.project.pk]
            self.initial["tags_"] = [ [t.pk for t in inst.tags.all()] ]

    def clean(self):
        """ Change instance based on selections, optionally create new records from text inputs.

            TODO: change SelectOrCreateField to be properly handled by ModelForm to create db entries.
        """
        data         = self.cleaned_data
        inst         = self.instance
        inst.creator = self.user

        proj, new = data["project_"]
        if new:
            inst.project = Project.obj.get_or_create(project=proj)[0]
        elif int(proj):
            inst.project = Project.obj.get(pk=proj)

        inst.save()
        tags = data["tags_"]
        if tags:
            selected, new = tags[0], tags[1:]
            inst.tags = [Tag.obj.get(pk=pk) for pk in selected]  # need this in case tags were deselected
            for tag in new:
                inst.tags.add( Tag.obj.get_or_create(tag=tag)[0] )

        return data


    fldorder   = "name body owner priority difficulty progress closed project_ tags_".split()
    s3widget   = f.TextInput(attrs=dict(size=3))

    priority   = f.IntegerField(widget=s3widget, required=False, initial=0)
    difficulty = f.IntegerField(widget=s3widget, required=False, initial=0)
    project_   = SelectOrCreateField()
    tags_      = TagsSelectCreateField()
    body       = f.CharField( widget=f.Textarea( attrs=dict(cols=80, rows=18) ), required=False )


class IssueForm(CreateIssueForm):
    """Like CreateIssueForm but with `progress` and `closed` fields."""
    class Meta:
        model   = Issue
        exclude = "creator project tags body_html".split()

    progress   = f.IntegerField(widget=CreateIssueForm.s3widget, required=False, initial=0)

########NEW FILE########
__FILENAME__ = models
from markdown import markdown

from django.template import loader
from django.db.models import *
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from settings import MEDIA_URL
from dbe.shared.utils import *

btn_tpl  = "<div class='%s' id='%s_%s'><img class='btn' src='%simg/admin/icon-%s.gif' /></div>"
namelink = "<a href='%s'>%s</a> <a style='float:right; font-size:0.6em;' href='%s'>edit</a>"
dellink  = "<a href='%s'>Delete</a>"


class Project(BaseModel):
    creator = ForeignKey(User, related_name="projects", blank=True, null=True)
    project = CharField(max_length=60)

    def __unicode__(self):
        return self.project

class Tag(BaseModel):
    creator = ForeignKey(User, related_name="tags", blank=True, null=True)
    tag     = CharField(max_length=30)

    def __unicode__(self):
        return self.tag


class Issue(BaseModel):
    name       = CharField(max_length=60)
    creator    = ForeignKey(User, related_name="created_issues", blank=True, null=True)
    body       = TextField(max_length=3000, default='', blank=True)
    body_html  = TextField(blank=True, null=True)

    owner      = ForeignKey(User, related_name="issues", blank=True, null=True)
    priority   = IntegerField(default=0, blank=True, null=True)
    difficulty = IntegerField(default=0, blank=True, null=True)
    progress   = IntegerField(default=0)

    closed     = BooleanField(default=False)
    created    = DateTimeField(auto_now_add=True)
    project    = ForeignKey(Project, related_name="issues", blank=True, null=True)
    tags       = ManyToManyField(Tag, related_name="issues", blank=True, null=True)

    def get_absolute_url(self):
        return reverse2("issue", dpk=self.pk)

    def save(self):
        self.body_html = markdown(self.body)
        super(Issue, self).save()

    def name_(self):
        link    = reverse2("issue", dpk=self.pk)
        editlnk = reverse2("update_issue_detail", mfpk=self.pk)
        return namelink % (link, self.name, editlnk)
    name_.allow_tags = True

    def progress_(self):
        return loader.render_to_string("progress.html", dict(pk=self.pk))
    progress_.allow_tags = True
    progress_.admin_order_field = "progress"

    def closed_(self):
        onoff = "on" if self.closed else "off"
        return btn_tpl % ("toggle closed", 'd', self.pk, MEDIA_URL, onoff)
    closed_.allow_tags = True
    closed_.admin_order_field = "closed"

    def created_(self):
        return self.created.strftime("%b %d %Y")
    created_.admin_order_field = "created"

    def owner_(self):
        return self.owner or ''
    owner_.admin_order_field = "owner"

    def project_(self):
        return self.project or ''
    project_.admin_order_field = "project"

    def delete_(self):
        return dellink % reverse2("update_issue", self.pk, "delete")
    delete_.allow_tags = True


class Comment(BaseModel):
    creator   = ForeignKey(User, related_name="comments", blank=True, null=True)
    issue     = ForeignKey(Issue, related_name="comments", blank=True, null=True)
    created   = DateTimeField(auto_now_add=True)
    body      = TextField(max_length=3000)
    body_html = TextField()

    def save(self):
        self.body_html = markdown(self.body)
        super(Comment, self).save()

    def __unicode__(self):
        return unicode(self.issue.name if self.issue else '') + " : " + self.body[:20]

########NEW FILE########
__FILENAME__ = issues
from django import template
from django.conf import settings

register = template.Library()

def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID

def get(value, arg):
    return value[arg]

def concat(value, arg):
    return value + arg


register.filter("getattribute", getattribute)
register.filter("get", get)
register.filter("concat", concat)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from dbe.issues.views import *
from django.contrib.auth.decorators import login_required

urlpatterns = patterns("dbe.issues.views",
    (r"^delete-comment/(\d+)/$", "delete_comment", {}, "delete_comment"),

    (r"^update-issue/(\d+)/(delete)/$", "update_issue", {}, "update_issue"),

    (r"^update-issue/(\d+)/(closed|progress)/(on|off|\d+)/$", "update_issue", {}, "update_issue"),


    (r"^update-issue-detail/(?P<mfpk>\d+)/$", UpdateIssue.as_view(), {}, "update_issue_detail"),

    (r"^issue/(?P<dpk>\d+)/$", ViewIssue.as_view(), {}, "issue"),

    (r"^update-comment/(?P<mfpk>\d+)/$", UpdateComment.as_view(), {}, "update_comment"),

    (r"^add-issues/$", login_required(AddIssues.as_view()), {}, "add_issues"),
)

########NEW FILE########
__FILENAME__ = views
from pprint import pprint
from django.http import HttpResponse
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.admin.views.decorators import staff_member_required
from django.forms import forms
from django.core.mail import send_mail

from dbe.shared.utils import *
from dbe.issues.models import *
from dbe.issues.forms import *

from dbe.mcbv.edit_custom import UpdateView, FormSetView
from dbe.mcbv.list_custom import DetailListCreateView


@staff_member_required
def update_issue(request, pk, mode=None, action=None):
    """AJAX view, toggle Done on/off, set progress or delete an issue."""
    issue = Issue.obj.get(pk=pk)
    if mode == "delete":
        issue.delete()
        return redir("admin:issues_issue_changelist")
    else:
        if mode == "progress" : val = int(action)
        else                  : val = bool(action=="on")
        setattr(issue, mode, val)
        issue.save()
        return HttpResponse('')

@staff_member_required
def delete_comment(request, pk):
    Comment.obj.get(pk=pk).delete()
    return redir(referer(request))


class UpdateIssue(UpdateView):
    form_model      = Issue
    modelform_class = IssueForm
    msg_tpl         = "Issue '%s' was updated <%s%s>\n\n%s"
    template_name   = "issue_form.html"

    def modelform_valid(self, modelform):
        """ If form was changed, send notification email the (new) issue owner.
            Note: at the start of the function, FK relationships are already updated in `self.object`.
        """
        if modelform.has_changed() and self.modelform_object.owner:
            notify_owner(self.request, self.modelform_object, "Issue Updated", self.msg_tpl)
        return super(UpdateIssue, self).modelform_valid(modelform)


class UpdateComment(UpdateView):
    form_model      = Comment
    modelform_class = CommentForm
    template_name   = "issues/comment_form.html"

    def get_success_url(self):
        return self.modelform_object.issue.get_absolute_url()


class ViewIssue(DetailListCreateView):
    """View issue, comments and new comment form."""
    detail_model               = Issue
    list_model                 = Comment
    modelform_class            = CommentForm
    related_name               = "comments"
    fk_attr                    = "issue"
    msg_tpl                    = "Comment was added to the Issue '%s' <%s%s>\n\n%s"
    template_name              = "issue.html"

    def modelform_valid(self, modelform):
        """Send notification email to the issue owner."""
        resp = super(ViewIssue, self).modelform_valid(modelform)
        obj  = self.modelform_object
        obj.update(creator=self.user)
        notify_owner(self.request, obj.issue, "New Comment", self.msg_tpl, comment_body=obj.body)
        return resp


class AddIssues(FormSetView):
    """Create new issues."""
    formset_model      = Issue
    formset_form_class = IssueForm
    success_url        = reverse_lazy("admin:issues_issue_changelist")
    msg_tpl            = "New Issue '%s' was created <%s%s>\n\n%s"
    extra              = 2
    template_name      = "add_issues.html"

    def process_form(self, form):
        form.save()
        notify_owner(self.request, form.instance, "New Issue", self.msg_tpl)


def notify_owner(request, obj, title, msg_tpl, comment_body=''):
    serv_root = request.META["HTTP_ORIGIN"]
    url       = reverse2("issue", dpk=obj.pk)
    lst       = [obj.name, serv_root, url, comment_body]
    msg       = msg_tpl % tuple(lst)

    if obj.owner:
        send_mail(title, msg, "IssuesApp", [obj.owner.email], fail_silently=False)

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals

import logging
from functools import update_wrapper

from django import http
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from django.utils.decorators import classonlymethod
from django.utils import six


logger = logging.getLogger('django.request')


class ContextMixin(object):
    """
    A default context mixin that passes the keyword arguments received by
    get_context_data as the template context.
    """
    def add_context(self):
        """Convenience method; may be overridden to add context by returning a dictionary."""
        return {}

    def get_context_data(self, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self
        kwargs.update(self.add_context())
        return kwargs


class View(object):
    """
    Intentionally simple parent class for all views. Only implements
    dispatch-by-method and simple sanity checking.
    """

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace']

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classonlymethod
    def as_view(cls, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.user    = request.user
            self.args    = args
            self.kwargs  = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def initsetup(self):
        pass

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.

        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        self.initsetup()
        return handler(request, *args, **kwargs)

    def http_method_not_allowed(self, request, *args, **kwargs):
        logger.warning('Method Not Allowed (%s): %s', request.method, request.path,
            extra={
                'status_code': 405,
                'request': self.request
            }
        )
        return http.HttpResponseNotAllowed(self._allowed_methods())

    def options(self, request, *args, **kwargs):
        """
        Handles responding to requests for the OPTIONS HTTP verb.
        """
        response = http.HttpResponse()
        response['Allow'] = ', '.join(self._allowed_methods())
        response['Content-Length'] = '0'
        return response

    def _allowed_methods(self):
        return [m.upper() for m in self.http_method_names if hasattr(self, m)]

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class TemplateResponseMixin(object):
    """
    A mixin that can be used to render a template.
    """
    template_name = None
    response_class = TemplateResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response, using the `response_class` for this
        view, with a template rendered with the given context.

        If any keyword arguments are provided, they will be
        passed to the constructor of the response class.
        """
        return self.response_class(
            request = self.request,
            template = self.get_template_names(),
            context = context,
            **response_kwargs
        )

    def get_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        if self.template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'")
        else:
            return [self.template_name]

    def get(self, request, *args, **kwargs):
        from detail import DetailView
        from edit import FormView, FormSetView, ModelFormSetView, CreateView, UpdateView
        from list import ListView

        args    = [request] + list(args)
        context = dict()
        update  = context.update

        if isinstance(self, DetailView)                      : update( self.detail_get(*args, **kwargs) )
        if isinstance(self, FormView)                        : update( self.form_get(*args, **kwargs) )
        if isinstance(self, (FormSetView, ModelFormSetView)) : update( self.formset_get(*args, **kwargs) )
        if isinstance(self, CreateView)                      : update( self.create_get(*args, **kwargs) )
        if isinstance(self, UpdateView)                      : update( self.update_get(*args, **kwargs) )
        if isinstance(self, ListView)                        : update( self.list_get(*args, **kwargs) )

        update(self.get_context_data(**kwargs))
        return self.render_to_response(context)


class TemplateView(TemplateResponseMixin, ContextMixin, View):
    """
    A view that renders a template.  This view will also pass into the context
    any keyword arguments passed by the url conf.
    """
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class RedirectView(View):
    """
    A view that provides a redirect on any GET request.
    """
    permanent = True
    url = None
    query_string = False

    def get_redirect_url(self, **kwargs):
        """
        Return the URL redirect to. Keyword arguments from the
        URL pattern match generating the redirect request
        are provided as kwargs to this method.
        """
        if self.url:
            url = self.url % kwargs
            args = self.request.META.get('QUERY_STRING', '')
            if args and self.query_string:
                url = "%s?%s" % (url, args)
            return url
        else:
            return None

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url:
            if self.permanent:
                return http.HttpResponsePermanentRedirect(url)
            else:
                return http.HttpResponseRedirect(url)
        else:
            logger.warning('Gone: %s', self.request.path,
                        extra={
                            'status_code': 410,
                            'request': self.request
                        })
            return http.HttpResponseGone()

    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = dates
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.views.generic.base import View
from django.views.generic.detail import BaseDetailView, SingleObjectTemplateResponseMixin
from django.views.generic.list import MultipleObjectMixin, MultipleObjectTemplateResponseMixin

class YearMixin(object):
    """
    Mixin for views manipulating year-based data.
    """
    year_format = '%Y'
    year = None

    def get_year_format(self):
        """
        Get a year format string in strptime syntax to be used to parse the
        year from url variables.
        """
        return self.year_format

    def get_year(self):
        """
        Return the year for which this view should display data.
        """
        year = self.year
        if year is None:
            try:
                year = self.kwargs['year']
            except KeyError:
                try:
                    year = self.request.GET['year']
                except KeyError:
                    raise Http404(_("No year specified"))
        return year

    def get_next_year(self, date):
        """
        Get the next valid year.
        """
        return _get_next_prev(self, date, is_previous=False, period='year')

    def get_previous_year(self, date):
        """
        Get the previous valid year.
        """
        return _get_next_prev(self, date, is_previous=True, period='year')

    def _get_next_year(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date.replace(year=date.year + 1, month=1, day=1)

    def _get_current_year(self, date):
        """
        Return the start date of the current interval.
        """
        return date.replace(month=1, day=1)


class MonthMixin(object):
    """
    Mixin for views manipulating month-based data.
    """
    month_format = '%b'
    month = None

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

    def get_month(self):
        """
        Return the month for which this view should display data.
        """
        month = self.month
        if month is None:
            try:
                month = self.kwargs['month']
            except KeyError:
                try:
                    month = self.request.GET['month']
                except KeyError:
                    raise Http404(_("No month specified"))
        return month

    def get_next_month(self, date):
        """
        Get the next valid month.
        """
        return _get_next_prev(self, date, is_previous=False, period='month')

    def get_previous_month(self, date):
        """
        Get the previous valid month.
        """
        return _get_next_prev(self, date, is_previous=True, period='month')

    def _get_next_month(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        if date.month == 12:
            return date.replace(year=date.year + 1, month=1, day=1)
        else:
            return date.replace(month=date.month + 1, day=1)

    def _get_current_month(self, date):
        """
        Return the start date of the previous interval.
        """
        return date.replace(day=1)


class DayMixin(object):
    """
    Mixin for views manipulating day-based data.
    """
    day_format = '%d'
    day = None

    def get_day_format(self):
        """
        Get a day format string in strptime syntax to be used to parse the day
        from url variables.
        """
        return self.day_format

    def get_day(self):
        """
        Return the day for which this view should display data.
        """
        day = self.day
        if day is None:
            try:
                day = self.kwargs['day']
            except KeyError:
                try:
                    day = self.request.GET['day']
                except KeyError:
                    raise Http404(_("No day specified"))
        return day

    def get_next_day(self, date):
        """
        Get the next valid day.
        """
        return _get_next_prev(self, date, is_previous=False, period='day')

    def get_previous_day(self, date):
        """
        Get the previous valid day.
        """
        return _get_next_prev(self, date, is_previous=True, period='day')

    def _get_next_day(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date + datetime.timedelta(days=1)

    def _get_current_day(self, date):
        """
        Return the start date of the current interval.
        """
        return date


class WeekMixin(object):
    """
    Mixin for views manipulating week-based data.
    """
    week_format = '%U'
    week = None

    def get_week_format(self):
        """
        Get a week format string in strptime syntax to be used to parse the
        week from url variables.
        """
        return self.week_format

    def get_week(self):
        """
        Return the week for which this view should display data
        """
        week = self.week
        if week is None:
            try:
                week = self.kwargs['week']
            except KeyError:
                try:
                    week = self.request.GET['week']
                except KeyError:
                    raise Http404(_("No week specified"))
        return week

    def get_next_week(self, date):
        """
        Get the next valid week.
        """
        return _get_next_prev(self, date, is_previous=False, period='week')

    def get_previous_week(self, date):
        """
        Get the previous valid week.
        """
        return _get_next_prev(self, date, is_previous=True, period='week')

    def _get_next_week(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date + datetime.timedelta(days=7 - self._get_weekday(date))

    def _get_current_week(self, date):
        """
        Return the start date of the current interval.
        """
        return date - datetime.timedelta(self._get_weekday(date))

    def _get_weekday(self, date):
        """
        Return the weekday for a given date.

        The first day according to the week format is 0 and the last day is 6.
        """
        week_format = self.get_week_format()
        if week_format == '%W':                 # week starts on Monday
            return date.weekday()
        elif week_format == '%U':               # week starts on Sunday
            return (date.weekday() + 1) % 7
        else:
            raise ValueError("unknown week format: %s" % week_format)


class DateMixin(object):
    """
    Mixin class for views manipulating date-based data.
    """
    date_field = None
    allow_future = False

    def get_date_field(self):
        """
        Get the name of the date field to be used to filter by.
        """
        if self.date_field is None:
            raise ImproperlyConfigured("%s.date_field is required." % self.__class__.__name__)
        return self.date_field

    def get_allow_future(self):
        """
        Returns `True` if the view should be allowed to display objects from
        the future.
        """
        return self.allow_future

    # Note: the following three methods only work in subclasses that also
    # inherit SingleObjectMixin or MultipleObjectMixin.

    @cached_property
    def uses_datetime_field(self):
        """
        Return `True` if the date field is a `DateTimeField` and `False`
        if it's a `DateField`.
        """
        model = self.get_queryset().model if self.model is None else self.model
        field = model._meta.get_field(self.get_date_field())
        return isinstance(field, models.DateTimeField)

    def _make_date_lookup_arg(self, value):
        """
        Convert a date into a datetime when the date field is a DateTimeField.

        When time zone support is enabled, `date` is assumed to be in the
        current time zone, so that displayed items are consistent with the URL.
        """
        if self.uses_datetime_field:
            value = datetime.datetime.combine(value, datetime.time.min)
            if settings.USE_TZ:
                value = timezone.make_aware(value, timezone.get_current_timezone())
        return value

    def _make_single_date_lookup(self, date):
        """
        Get the lookup kwargs for filtering on a single date.

        If the date field is a DateTimeField, we can't just filter on
        date_field=date because that doesn't take the time into account.
        """
        date_field = self.get_date_field()
        if self.uses_datetime_field:
            since = self._make_date_lookup_arg(date)
            until = self._make_date_lookup_arg(date + datetime.timedelta(days=1))
            return {
                '%s__gte' % date_field: since,
                '%s__lt' % date_field: until,
            }
        else:
            # Skip self._make_date_lookup_arg, it's a no-op in this branch.
            return {date_field: date}


class BaseDateListView(MultipleObjectMixin, DateMixin, View):
    """
    Abstract base class for date-based views displaying a list of objects.
    """
    allow_empty = False
    date_list_period = 'year'

    def get(self, request, *args, **kwargs):
        self.date_list, self.object_list, extra_context = self.get_dated_items()
        context = self.get_list_context_data(object_list=self.object_list,
                                             date_list=self.date_list)
        context.update(extra_context)
        return self.render_to_response(context)

    def get_dated_items(self):
        """
        Obtain the list of dates and items.
        """
        raise NotImplementedError('A DateView must provide an implementation of get_dated_items()')

    def get_dated_queryset(self, ordering=None, **lookup):
        """
        Get a queryset properly filtered according to `allow_future` and any
        extra lookup kwargs.
        """
        qs = self.get_queryset().filter(**lookup)
        date_field = self.get_date_field()
        allow_future = self.get_allow_future()
        allow_empty = self.get_allow_empty()
        paginate_by = self.get_paginate_by(qs)

        if ordering is not None:
            qs = qs.order_by(ordering)

        if not allow_future:
            now = timezone.now() if self.uses_datetime_field else timezone_today()
            qs = qs.filter(**{'%s__lte' % date_field: now})

        if not allow_empty:
            # When pagination is enabled, it's better to do a cheap query
            # than to load the unpaginated queryset in memory.
            is_empty = len(qs) == 0 if paginate_by is None else not qs.exists()
            if is_empty:
                raise Http404(_("No %(verbose_name_plural)s available") % {
                        'verbose_name_plural': force_text(qs.model._meta.verbose_name_plural)
                })

        return qs

    def get_date_list_period(self):
        """
        Get the aggregation period for the list of dates: 'year', 'month', or 'day'.
        """
        return self.date_list_period

    def get_date_list(self, queryset, date_type=None, ordering='ASC'):
        """
        Get a date list by calling `queryset.dates()`, checking along the way
        for empty lists that aren't allowed.
        """
        date_field = self.get_date_field()
        allow_empty = self.get_allow_empty()
        if date_type is None:
            date_type = self.get_date_list_period()

        date_list = queryset.dates(date_field, date_type, ordering)
        if date_list is not None and not date_list and not allow_empty:
            name = force_text(queryset.model._meta.verbose_name_plural)
            raise Http404(_("No %(verbose_name_plural)s available") %
                          {'verbose_name_plural': name})

        return date_list


class BaseArchiveIndexView(BaseDateListView):
    """
    Base class for archives of date-based items.

    Requires a response mixin.
    """
    context_object_name = 'latest'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        qs = self.get_dated_queryset(ordering='-%s' % self.get_date_field())
        date_list = self.get_date_list(qs, ordering='DESC')

        if not date_list:
            qs = qs.none()

        return (date_list, qs, {})


class ArchiveIndexView(MultipleObjectTemplateResponseMixin, BaseArchiveIndexView):
    """
    Top-level archive of date-based items.
    """
    template_name_suffix = '_archive'


class BaseYearArchiveView(YearMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    date_list_period = 'month'
    make_object_list = False

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format())

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_year(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(ordering='-%s' % date_field, **lookup_kwargs)
        date_list = self.get_date_list(qs)

        if not self.get_make_object_list():
            # We need this to be a queryset since parent classes introspect it
            # to find information about the model.
            qs = qs.none()

        return (date_list, qs, {
            'year': date,
            'next_year': self.get_next_year(date),
            'previous_year': self.get_previous_year(date),
        })

    def get_make_object_list(self):
        """
        Return `True` if this view should contain the full list of objects in
        the given year.
        """
        return self.make_object_list


class YearArchiveView(MultipleObjectTemplateResponseMixin, BaseYearArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_year'


class BaseMonthArchiveView(YearMixin, MonthMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    date_list_period = 'day'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format())

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_month(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)
        date_list = self.get_date_list(qs)

        return (date_list, qs, {
            'month': date,
            'next_month': self.get_next_month(date),
            'previous_month': self.get_previous_month(date),
        })


class MonthArchiveView(MultipleObjectTemplateResponseMixin, BaseMonthArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_month'


class BaseWeekArchiveView(YearMixin, WeekMixin, BaseDateListView):
    """
    List of objects published in a given week.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        week = self.get_week()

        date_field = self.get_date_field()
        week_format = self.get_week_format()
        week_start = {
            '%W': '1',
            '%U': '0',
        }[week_format]
        date = _date_from_string(year, self.get_year_format(),
                                 week_start, '%w',
                                 week, week_format)

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_week(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {
            'week': date,
            'next_week': self.get_next_week(date),
            'previous_week': self.get_previous_week(date),
        })


class WeekArchiveView(MultipleObjectTemplateResponseMixin, BaseWeekArchiveView):
    """
    List of objects published in a given week.
    """
    template_name_suffix = '_archive_week'


class BaseDayArchiveView(YearMixin, MonthMixin, DayMixin, BaseDateListView):
    """
    List of objects published on a given day.
    """
    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()

        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        return self._get_dated_items(date)

    def _get_dated_items(self, date):
        """
        Do the actual heavy lifting of getting the dated items; this accepts a
        date object so that TodayArchiveView can be trivial.
        """
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {
            'day': date,
            'previous_day': self.get_previous_day(date),
            'next_day': self.get_next_day(date),
            'previous_month': self.get_previous_month(date),
            'next_month': self.get_next_month(date)
        })


class DayArchiveView(MultipleObjectTemplateResponseMixin, BaseDayArchiveView):
    """
    List of objects published on a given day.
    """
    template_name_suffix = "_archive_day"


class BaseTodayArchiveView(BaseDayArchiveView):
    """
    List of objects published today.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        return self._get_dated_items(datetime.date.today())


class TodayArchiveView(MultipleObjectTemplateResponseMixin, BaseTodayArchiveView):
    """
    List of objects published today.
    """
    template_name_suffix = "_archive_day"


class BaseDateDetailView(YearMixin, MonthMixin, DayMixin, DateMixin, BaseDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    def get_detail_object(self, queryset=None):
        """
        Get the object this request displays.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        # Use a custom queryset if provided
        qs = queryset or self.get_detail_queryset()

        if not self.get_allow_future() and date > datetime.date.today():
            raise Http404(_("Future %(verbose_name_plural)s not available because %(class_name)s.allow_future is False.") % {
                'verbose_name_plural': qs.model._meta.verbose_name_plural,
                'class_name': self.__class__.__name__,
            })

        # Filter down a queryset from self.queryset using the date from the
        # URL. This'll get passed as the queryset to DetailView.get_object,
        # which'll handle the 404
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = qs.filter(**lookup_kwargs)

        return super(BaseDetailView, self).get_detail_object(queryset=qs)


class DateDetailView(SingleObjectTemplateResponseMixin, BaseDateDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    template_name_suffix = '_detail'


def _date_from_string(year, year_format, month='', month_format='', day='', day_format='', delim='__'):
    """
    Helper: get a datetime.date object given a format string and a year,
    month, and day (only year is mandatory). Raise a 404 for an invalid date.
    """
    format = delim.join((year_format, month_format, day_format))
    datestr = delim.join((year, month, day))
    try:
        return datetime.datetime.strptime(datestr, format).date()
    except ValueError:
        raise Http404(_("Invalid date string '%(datestr)s' given format '%(format)s'") % {
            'datestr': datestr,
            'format': format,
        })


def _get_next_prev(generic_view, date, is_previous, period):
    """
    Helper: Get the next or the previous valid date. The idea is to allow
    links on month/day views to never be 404s by never providing a date
    that'll be invalid for the given view.

    This is a bit complicated since it handles different intervals of time,
    hence the coupling to generic_view.

    However in essence the logic comes down to:

        * If allow_empty and allow_future are both true, this is easy: just
          return the naive result (just the next/previous day/week/month,
          reguardless of object existence.)

        * If allow_empty is true, allow_future is false, and the naive result
          isn't in the future, then return it; otherwise return None.

        * If allow_empty is false and allow_future is true, return the next
          date *that contains a valid object*, even if it's in the future. If
          there are no next objects, return None.

        * If allow_empty is false and allow_future is false, return the next
          date that contains a valid object. If that date is in the future, or
          if there are no next objects, return None.

    """
    date_field = generic_view.get_date_field()
    allow_empty = generic_view.get_allow_empty()
    allow_future = generic_view.get_allow_future()

    get_current = getattr(generic_view, '_get_current_%s' % period)
    get_next = getattr(generic_view, '_get_next_%s' % period)

    # Bounds of the current interval
    start, end = get_current(date), get_next(date)

    # If allow_empty is True, the naive result will be valid
    if allow_empty:
        if is_previous:
            result = get_current(start - datetime.timedelta(days=1))
        else:
            result = end

        if allow_future or result <= timezone_today():
            return result
        else:
            return None

    # Otherwise, we'll need to go to the database to look for an object
    # whose date_field is at least (greater than/less than) the given
    # naive result
    else:
        # Construct a lookup and an ordering depending on whether we're doing
        # a previous date or a next date lookup.
        if is_previous:
            lookup = {'%s__lt' % date_field: generic_view._make_date_lookup_arg(start)}
            ordering = '-%s' % date_field
        else:
            lookup = {'%s__gte' % date_field: generic_view._make_date_lookup_arg(end)}
            ordering = date_field

        # Filter out objects in the future if appropriate.
        if not allow_future:
            # Fortunately, to match the implementation of allow_future,
            # we need __lte, which doesn't conflict with __lt above.
            if generic_view.uses_datetime_field:
                now = timezone.now()
            else:
                now = timezone_today()
            lookup['%s__lte' % date_field] = now

        qs = generic_view.get_queryset().filter(**lookup).order_by(ordering)

        # Snag the first object from the queryset; if it doesn't exist that
        # means there's no next/previous link available.
        try:
            result = getattr(qs[0], date_field)
        except IndexError:
            return None

        # Convert datetimes to dates in the current time zone.
        if generic_view.uses_datetime_field:
            if settings.USE_TZ:
                result = timezone.localtime(result)
            result = result.date()

        # Return the first day of the period.
        return get_current(result)


def timezone_today():
    """
    Return the current date in the current time zone.
    """
    if settings.USE_TZ:
        return timezone.localtime(timezone.now()).date()
    else:
        return datetime.date.today()

########NEW FILE########
__FILENAME__ = detail
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.utils.translation import ugettext as _

from base import TemplateResponseMixin, ContextMixin, View


class SingleObjectMixin(ContextMixin):
    """
    Provides the ability to retrieve a single object for further manipulation.
    """
    detail_model               = None
    detail_context_object_name = None
    detail_queryset            = None
    detail_pk_url_kwarg        = 'dpk'
    slug_field                 = 'slug'
    slug_url_kwarg             = 'slug'

    def get_object(self, queryset=None, pk_url_kwarg=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(pk_url_kwarg, None)

        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_detail_object(self, queryset=None):
        return self.get_object( queryset or self.get_detail_queryset(), self.detail_pk_url_kwarg )

    def get_queryset(self, model):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if model:
            return model._default_manager.all()
        else:
            raise ImproperlyConfigured("%(cls)s is missing a queryset. Define "
                                       "%(cls)s.detail_model, %(cls)s.detail_queryset, or override "
                                       "%(cls)s.get_detail_queryset()." % {
                                            'cls': self.__class__.__name__
                                    })

    def get_detail_queryset(self):
        if self.detail_queryset:
            return self.detail_queryset._clone()
        else:
            return self.get_queryset(self.detail_model)

    def get_slug_field(self):
        """
        Get the name of a slug field to be used to look up by slug.
        """
        return self.slug_field

    def get_detail_context_object_name(self, obj):
        """
        Get the name to use for the object.
        """
        if self.detail_context_object_name:
            return self.detail_context_object_name
        elif isinstance(obj, models.Model):
            return obj._meta.object_name.lower()
        else:
            return None

    def get_detail_context_data(self, **kwargs):
        """
        Insert the single object into the context dict.
        """
        context = {}
        context_object_name = self.get_detail_context_object_name(self.detail_object)
        if context_object_name:
            context[context_object_name] = self.detail_object
        context.update(kwargs)
        return context

    def detail_absolute_url(self):
        return self.get_detail_object().get_absolute_url()


class BaseDetailView(SingleObjectMixin, View):
    """
    A base view for displaying a single object
    """
    def detail_get(self, request, *args, **kwargs):
        self.detail_object = self.get_detail_object()
        return self.get_detail_context_data(detail_object=self.detail_object)


class SingleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_field = None
    template_name_suffix = '_detail'

    def get_template_names(self):
        return self._get_template_names(self.detail_object, self.detail_model)

    def _get_template_names(self, object=None, model=None):
        """
        Return a list of template names to be used for the request. May not be
        called if render_to_response is overridden. Returns the following list:

        * the value of ``template_name`` on the view (if provided)
        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * ``<app_label>/<object_name><template_name_suffix>.html``
        """
        try:
            names = super(SingleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If self.template_name_field is set, grab the value of the field
        # of that name from the object; this is the most specific template
        # name, if given.
        if object and self.template_name_field:
            name = getattr(self.detail_object, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<model>_detail.html;
        # only use this if the object in question is a model.
        if isinstance(object, models.Model):
            names.append("%s/%s%s.html" % (
                object._meta.app_label,
                object._meta.object_name.lower(),
                self.template_name_suffix
            ))
        elif model is not None and issubclass(model, models.Model):
            names.append("%s/%s%s.html" % (
                model._meta.app_label,
                model._meta.object_name.lower(),
                self.template_name_suffix
            ))
        return names


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """

########NEW FILE########
__FILENAME__ = edit
from django.forms import models as model_forms
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.utils.encoding import force_text
from django.db import models
from django.contrib import messages

from django.utils.functional import curry
from django.forms.formsets import formset_factory, BaseFormSet, all_valid
from django.forms.models import modelformset_factory

from base import TemplateResponseMixin, ContextMixin, View
from detail import SingleObjectMixin, SingleObjectTemplateResponseMixin, BaseDetailView, DetailView
from list import MultipleObjectMixin, ListView


class FormMixin(ContextMixin):
    """
    A mixin that provides a way to show and handle a form in a request.
    """

    initial         = {}
    form_class      = None
    success_url     = None
    form_kwarg_user = False     # provide request user to form

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        return self.initial.copy()

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        return self.form_class

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        form_class = form_class or self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {'initial': self.get_initial()}
        if self.form_kwarg_user:
            kwargs['user'] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def form_valid(self, form):
        """
        If the form is valid, redirect to the supplied URL.
        """
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """
        If the form or modelform are invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.get_context_data(form=form)


class FormSetMixin(FormMixin):
    """A mixin that provides a way to show and handle a formset in a request."""
    formset_form_class = None
    formset_initial    = {}
    formset_class      = BaseFormSet
    extra              = 0
    can_delete         = False
    # ignore_get_args    = ("page", )     # TODO this may be better moved to the form class?

    formset_kwarg_user = False       # provide request user to form
    success_url        = None

    def get_formset_initial(self):
        return self.formset_initial.copy()

    def get_formset_class(self):
        return self.formset_class

    def get_formset_form_class(self):
        return self.formset_form_class

    def get_formset(self, form_class=None):
        form_class = form_class or self.formset_form_class
        kwargs     = dict()
        Formset    = formset_factory(form_class, extra=self.extra, can_delete=self.can_delete)

        if self.form_kwarg_user:
            kwargs["user"] = self.user

        Formset.form = staticmethod(curry(form_class, **kwargs))
        return Formset(**self.get_formset_kwargs())

    def get_formset_kwargs(self):
        kwargs = dict(initial=self.get_formset_initial())

        if self.formset_kwarg_user:
            kwargs["user"] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def formset_valid(self, formset):
        for form in formset:
            if form.has_changed():
                if form.cleaned_data.get("DELETE"):
                    self.process_delete(form)
                else:
                    self.process_form(form)
        return HttpResponseRedirect(self.get_success_url())

    def process_form(self, form):
        form.save()

    def process_delete(self, form):
        """Process checked 'delete' box."""
        pass

    def formset_invalid(self, formset):
        return self.get_context_data(formset=formset)


class ModelFormSetMixin(FormSetMixin):
    formset_model    = None
    formset_queryset = None

    def get_formset_queryset(self):
        if self.formset_queryset is not None:
            queryset = self.formset_queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.formset_model is not None:
            queryset = self.formset_model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'formset_queryset' or 'formset_model'"
                                        % self.__class__.__name__)
        return queryset

    def get_formset(self, form_class=None):
        form_class = form_class or self.formset_form_class
        kwargs     = dict()
        Formset    = modelformset_factory(self.formset_model, extra=self.extra, can_delete=self.can_delete)

        if self.form_kwarg_user:
            kwargs["user"] = self.user

        Formset.form = staticmethod(curry(form_class, **kwargs))
        return Formset(**self.get_formset_kwargs())

    def get_formset_kwargs(self):
        kwargs = {
                  'initial'  : self.get_formset_initial(),
                  'queryset' : self.get_formset_queryset(),
                  }

        if self.formset_kwarg_user:
            kwargs["user"] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def process_delete(self, form):
        """Process checked 'delete' box."""
        form.instance.delete()


class ModelFormMixin(FormMixin, SingleObjectMixin):
    """
    A mixin that provides a way to show and handle a modelform in a request.
    """
    form_model                    = None
    modelform_class               = None
    modelform_queryset            = None
    modelform_context_object_name = None
    modelform_pk_url_kwarg        = 'mfpk'
    modelform_valid_msg           = None

    def get_modelform_class(self):
        """Returns the form class to use in this view."""
        if self.modelform_class:
            return self.modelform_class
        else:
            if self.form_model is not None:
                # If a model has been explicitly provided, use it
                model = self.form_model
            elif hasattr(self, 'modelform_object') and self.modelform_object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.modelform_object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_modelform_queryset().model
            return model_forms.modelform_factory(model)

    def get_modelform(self, form_class=None):
        form_class = form_class or self.get_modelform_class()
        return form_class(**self.get_modelform_kwargs())

    def get_modelform_kwargs(self):
        """Returns the keyword arguments for instantiating the form."""
        kwargs = super(ModelFormMixin, self).get_form_kwargs()
        kwargs.update({'instance': self.modelform_object})
        return kwargs

    def get_success_url(self):
        """Returns the supplied URL."""
        if self.success_url:
            url = self.success_url % self.modelform_object.__dict__
        else:
            try:
                url = self.modelform_object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the Model.")
        return url

    def modelform_valid(self, modelform):
        self.modelform_object = modelform.save()
        if self.modelform_valid_msg:
            messages.info(self.request, self.modelform_valid_msg)
        return HttpResponseRedirect(self.get_success_url())

    def modelform_invalid(self, modelform):
        return self.get_context_data(modelform=modelform)

    def get_modelform_context_data(self, **kwargs):
        """
        If an object has been supplied, inject it into the context with the
        supplied modelform_context_object_name name.
        """
        context = {}
        obj = self.modelform_object
        if obj:
            context['modelform_object'] = obj
            if self.modelform_context_object_name:
                context[self.modelform_context_object_name] = obj
            elif isinstance(obj, models.Model):
                context[obj._meta.object_name.lower()] = obj
        context.update(kwargs)
        return context

    def get_modelform_object(self, queryset=None):
        return self.get_object( queryset or self.get_modelform_queryset(), self.modelform_pk_url_kwarg )

    def get_modelform_queryset(self):
        if self.modelform_queryset:
            return self.modelform_queryset._clone()
        else:
            return self.get_queryset(self.form_model)


class ProcessFormView(View):
    """
    A mixin that renders a form on GET and processes it on POST.
    """

    def form_get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        return self.get_context_data( form=self.get_form() )

    def formset_get(self, request, *args, **kwargs):
        return self.get_context_data( formset=self.get_formset() )

    def modelform_get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        return self.get_modelform_context_data( modelform=self.get_modelform() )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = formset = modelform = None

        if isinstance(self, DetailView):
            self.detail_object = self.get_detail_object()

        if isinstance(self, ListView):
            self.object_list = self.get_list_queryset()

        if isinstance(self, FormView):
            form = self.get_form()

        if isinstance(self, (FormSetView, ModelFormSetView)):
            formset = self.get_formset()

        if isinstance(self, UpdateView):
            self.update_post(request, *args, **kwargs)
            modelform = self.get_modelform()

        if isinstance(self, CreateView):
            self.create_post(request, *args, **kwargs)
            modelform = self.get_modelform()

        if (not form or form and form.is_valid()) and \
           (not modelform or modelform and modelform.is_valid()) and \
           (not formset or formset and formset.is_valid()):

            if isinstance(self, FormView)                        : resp = self.form_valid(form)
            if isinstance(self, (FormSetView, ModelFormSetView)) : resp = self.formset_valid(formset)
            if isinstance(self, (UpdateView, CreateView))        : resp = self.modelform_valid(modelform)
            return resp

        else:
            context = self.get_context_data()
            update  = context.update
            if isinstance(self, FormView)                        : update(self.form_invalid(form))
            if isinstance(self, (FormSetView, ModelFormSetView)) : update(self.formset_invalid(formset))
            if isinstance(self, (UpdateView, CreateView))        : update(self.modelform_invalid(modelform))
            return self.render_to_response(context)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class BaseFormView(FormMixin, ProcessFormView):
    """ A base view for displaying a form """

class FormView(TemplateResponseMixin, BaseFormView):
    """ A view for displaying a form, and rendering a template response. """

class BaseFormSetView(FormSetMixin, ProcessFormView):
    """A base view for displaying a formset."""

class FormSetView(TemplateResponseMixin, BaseFormSetView):
    """A view for displaying a formset, and rendering a template response."""


class BaseModelFormSetView(ModelFormSetMixin, ProcessFormView):
    """A base view for displaying a modelformset."""

class ModelFormSetView(TemplateResponseMixin, BaseModelFormSetView):
    """A view for displaying a modelformset, and rendering a template response."""



class BaseCreateView(ModelFormMixin, ProcessFormView):
    """
    Base view for creating an new object instance.

    Using this base class requires subclassing to provide a response mixin.
    """
    def create_get(self, request, *args, **kwargs):
        self.modelform_object = None
        return self.modelform_get(request, *args, **kwargs)

    def create_post(self, request, *args, **kwargs):
        self.modelform_object = None


class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    """
    View for creating a new object instance,
    with a response rendered by template.
    """
    template_name_suffix = '_modelform'

    def get_template_names(self):
        return self._get_template_names(self.modelform_object, self.form_model)


class BaseUpdateView(ModelFormMixin, ProcessFormView):
    """
    Base view for updating an existing object.

    Using this base class requires subclassing to provide a response mixin.
    """
    def update_get(self, request, *args, **kwargs):
        self.modelform_object = self.get_modelform_object()
        return self.modelform_get(request, *args, **kwargs)

    def update_post(self, request, *args, **kwargs):
        self.modelform_object = self.get_modelform_object()


class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    """
    View for updating an object,
    with a response rendered by template.
    """
    template_name_suffix = '_modelform'

    def get_template_names(self):
        return self._get_template_names(self.modelform_object, self.form_model)


class CreateUpdateView(CreateView):
    """Update object if modelform_pk_url_kwarg is in kwargs, otherwise create it."""
    modelform_create_class = None

    def get_modelform_class(self):
        if self.modelform_pk_url_kwarg in self.kwargs:
            return self.modelform_class
        else:
            return self.modelform_create_class

    def create_get(self, request, *args, **kwargs):
        if self.modelform_pk_url_kwarg in self.kwargs:
            self.modelform_object = self.get_modelform_object()
            return self.modelform_get(request, *args, **kwargs)
        else:
            return super(CreateUpdateView, self).create_get(request, *args, **kwargs)

    def create_post(self, request, *args, **kwargs):
        if self.modelform_pk_url_kwarg in self.kwargs:
            self.modelform_object = self.get_modelform_object()
        else:
            super(CreateUpdateView, self).create_post(request, *args, **kwargs)


class DeletionMixin(object):
    """
    A mixin providing the ability to delete objects
    """
    success_url = None

    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.
        """
        self.modelform_object = self.get_modelform_object()
        self.modelform_object.delete()
        return HttpResponseRedirect(self.get_success_url())

    # Add support for browsers which only accept GET and POST for now.
    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def get_success_url(self):
        if self.success_url:
            return self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")


class BaseDeleteView(DeletionMixin, BaseDetailView):
    """
    Base view for deleting an object.

    Using this base class requires subclassing to provide a response mixin.
    """


class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    """
    View for deleting an object retrieved with `self.get_object()`,
    with a response rendered by template.
    """
    template_name_suffix = '_confirm_delete'

########NEW FILE########
__FILENAME__ = edit_custom
from copy import copy
from django.forms import formsets
from django.contrib import messages
from django.db.models import Q
from django.forms.formsets import formset_factory, BaseFormSet, all_valid

from detail import *
from edit import *


class SearchFormViewMixin(BaseFormView):
    ignore_get_keys = ("page", )    # TODO this should be ignored in search form?

    def get_form_kwargs(self):
        """Returns the keyword arguments for instantiating the form."""
        req    = self.request
        kwargs = dict(initial=self.get_initial())

        if req.method in ("POST", "PUT"):
            kwargs.update(dict(data=req.POST, files=req.FILES))
        elif req.GET:
            # do get form processing if there's get data that's not in ignore list
            get = dict((k,v) for k,v in req.GET.items() if k not in self.ignore_get_keys)
            if get:
                kwargs = dict(kwargs, initial=get, data=get)
        return kwargs

    def form_get(self, request):
        form    = self.get_form()
        context = self.get_context_data(form=form)

        if self.request.GET:
            if form.is_valid() : context.update(self.form_valid(form))
            else               : context.update(self.form_invalid(form))
        return context


class SearchFormView(FormView, SearchFormViewMixin):
    """FormView for search pages."""


class OwnObjMixin(SingleObjectMixin):
    """Access object, checking that it belongs to current user."""
    item_name   = None          # used in permissions error message
    owner_field = "creator"     # object's field to compare to current user to check permission

    def permission_error(self):
        name = self.item_name or self.object.__class__.__name__
        return HttpResponse("You don't have permissions to access this %s." % name)

    def validate(self, obj):
        if getattr(obj, self.owner_field) == self.request.user:
            return True

    def get_object(self, queryset=None):
        obj = super(OwnObjMixin, self).get_object(queryset)
        return obj if self.validate(obj) else None


class DeleteOwnObjView(OwnObjMixin, DeleteView):
    """Delete object, checking that it belongs to current user."""


class UpdateOwnObjView(OwnObjMixin, UpdateView):
    """Update object, checking that it belongs to current user."""


class UpdateRelatedView(DetailView, UpdateView):
    """Update object related to detail object; create if does not exist."""
    detail_model = None
    form_model   = None
    fk_attr      = None
    related_name = None

    def get_modelform_object(self, queryset=None):
        """ Get related object: detail_model.<related_name>
            If does not exist, create: form_model.<fk_attr>
        """
        obj    = self.get_detail_object()
        kwargs = {self.fk_attr: obj}
        try:
            related_obj = getattr(obj, self.related_name)
        except self.form_model.DoesNotExist:
            related_obj = self.form_model.obj.create(**kwargs)
            setattr(obj, self.related_name, related_obj)
        return related_obj


class SearchEditFormset(SearchFormView):
    """Search form filtering a formset of items to be updated."""
    model         = None
    formset_class = None
    form_class    = None

    def get_form_class(self):
        if self.request.method == "GET": return self.form_class
        else: return self.formset_class

    def get_queryset(self, form=None):
        return self.model.objects.filter(self.get_query(form))

    def get_query(self, form):
        """This method should always be overridden, applying search from the `form`."""
        return Q()

    def form_valid(self, form):
        formset = None
        if self.request.method == "GET":
            formset = self.formset_class(queryset=self.get_queryset(form))
        else:
            form.save()
            messages.success(self.request, "%s(s) were updated successfully" % self.model.__name__.capitalize())
            formset = form
            form = self.form_class(self.request.GET)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_invalid(self, form):
        formset = form
        form = self.form_class(self.request.GET)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_bound:
            if form.is_valid(): return self.form_valid(form)
            else: return self.form_invalid(form)
        return self.render_to_response(self.get_context_data(form=form))

########NEW FILE########
__FILENAME__ = list
from __future__ import unicode_literals

from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.translation import ugettext as _

from base import TemplateResponseMixin, ContextMixin, View


class MultipleObjectMixin(ContextMixin):
    """
    A mixin for views manipulating multiple objects.
    """
    allow_empty              = True
    list_queryset            = None
    list_model               = None
    paginate_by              = None
    list_context_object_name = None
    paginate_orphans         = 0
    paginator_class          = Paginator
    page_kwarg               = 'page'

    def get_list_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if self.list_queryset is not None:
            queryset = self.list_queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.list_model is not None:
            queryset = self.list_model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'list_queryset' or 'list_model'"
                                       % self.__class__.__name__)
        return queryset

    def paginate_queryset(self, queryset, page_size):
        """
        Paginate the queryset, if needed.
        """
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_("Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage as e:
            raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                                'page_number': page_number,
                                'message': str(e)
            })

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        """
        Return an instance of the paginator for this view.
        """
        return self.paginator_class(
            queryset, per_page, orphans=orphans,
            allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_paginate_orphans(self):
        """
        Returns the maximum number of orphans extend the last page by when
        paginating.
        """
        return self.paginate_orphans

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_list_context_object_name(self, object_list):
        """
        Get the name of the item to be used in the context.
        """
        if self.list_context_object_name:
            return self.list_context_object_name
        elif hasattr(object_list, 'model'):
            return '%s_list' % object_list.model._meta.object_name.lower()
        else:
            return None

    def get_list_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        if "object_list" not in kwargs:
            kwargs["object_list"] = self.get_queryset()

        queryset            = kwargs.pop('object_list')
        page_size           = self.get_paginate_by(queryset)
        context_object_name = self.get_list_context_object_name(queryset)
        page                = None

        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
            context = {
                'paginator': paginator,
                'page_obj': page,
                'is_paginated': is_paginated,
                'object_list': page.object_list
            }
        else:
            context = {
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
                'object_list': queryset
            }

        if context_object_name is not None:
            context[context_object_name] = context["object_list"]
        context.update(kwargs)
        return context


class BaseListView(MultipleObjectMixin, View):
    """
    A base view for displaying a list of objects.
    """
    def list_get(self, request, *args, **kwargs):
        self.object_list = self.get_list_queryset()
        allow_empty      = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if (self.get_paginate_by(self.object_list) is not None
                and hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
                        % {'class_name': self.__class__.__name__})
        return self.get_list_context_data(object_list=self.object_list)


class MultipleObjectTemplateResponseMixin(TemplateResponseMixin):
    """
    Mixin for responding with a template and list of objects.
    """
    template_name_suffix = '_list'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        try:
            names = super(MultipleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If the list is a queryset, we'll invent a template name based on the
        # app and model name. This name gets put at the end of the template
        # name list so that user-supplied names override the automatically-
        # generated ones.
        if hasattr(self.object_list, 'model'):
            opts = self.object_list.model._meta
            names.append("%s/%s%s.html" % (opts.app_label, opts.object_name.lower(), self.template_name_suffix))

        return names


class ListView(MultipleObjectTemplateResponseMixin, BaseListView):
    """
    Render some list of objects, set by `self.model` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """

########NEW FILE########
__FILENAME__ = list_custom
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.forms.models import modelformset_factory
from django.core.urlresolvers import reverse

from list import *
from edit_custom import *


class PaginatedSearch(ListView, SearchFormView):
    """ List Filter - filter list with a search form.

        as_view      : dispatch -> get or post
        get          : get_form OR get_queryset -> get_context_data -> render_to_response
        post         : get_form -> get_form_kwargs -> form_valid or form_invalid
        form_valid   : get_success_url
        form_invalid : get_context_data -> render_to_response

        as_view, dispatch      : base.View
        render_to_response     : TemplateResponseMixin

        get                    : BaseListView
        post                   : ProcessFormView
        get_form, form_invalid : FormMixin
        get_form_kwargs        : SearchFormViewMixin

        form_valid, get_success_url, get_queryset, get_context_data
    """
    object_list = None

    def get_list_queryset(self):
        return self.object_list or []

    def get_list_context_data(self, **kwargs):
        context = super(PaginatedSearch, self).get_list_context_data(**kwargs)
        get     = self.request.GET.copy()
        get.pop("page", None)
        extra = '&'+get.urlencode()
        return dict(context, extra_vars=extra, form=self.get_form())


class ListFilterView(PaginatedSearch):
    """Filter a list view through a search."""
    list_model   = None
    search_field = 'q'
    start_blank  = True     # start with full item listing or blank page

    def get_list_queryset(self):
        if self.object_list:
            return self.object_list
        else:
            return list() if self.start_blank else self.list_model.objects.all()

    def get_query(self, q):
        return Q()

    def form_valid(self, form):
        q                = form.cleaned_data[self.search_field].strip()
        filter           = self.list_model.objects.filter
        self.object_list = filter(self.get_query(q)) if q else None
        return dict(form=form)


class ListRelated(DetailView, ListView):
    """Listing of an object and related items."""
    related_name = None      # attribute name linking main object to related objects

    def get_list_queryset(self):
        obj = self.get_detail_object()
        return getattr(obj, self.related_name).all()


class DetailListCreateView(ListRelated, CreateView):
    """ DetailView of an object & listing of related objects and a form to create new related obj.

        fk_attr : field of object to be created that points back to detail_object, e.g.:
                    detail_model = Thread; fk_attr = "thread"; reply.thread = detail_object
    """
    success_url = '#'
    fk_attr     = None

    def modelform_valid(self, modelform):
        self.modelform_object = modelform.save(commit=False)
        setattr(self.modelform_object, self.fk_attr, self.get_detail_object())
        self.modelform_object.save()
        return HttpResponseRedirect(self.get_success_url())


class DetailListFormSetView(ListRelated, ModelFormSetView):
    """ List of items related to main item, viewed as a paginated formset.
        Note: `list_model` needs to have ordering specified for it to be able to paginate.
    """
    detail_model               = None
    list_model                 = None
    formset_model              = None
    related_name               = None
    detail_context_object_name = None
    formset_form_class         = None
    paginate_by                = None
    main_object                = None  # should be left as None in subclass
    extra                      = 0
    template_name              = None

    def get_formset_queryset(self):
        qset      = self.get_list_queryset()
        page_size = self.get_paginate_by(qset)
        if page_size : return self.paginate_queryset(qset, page_size)[2]
        else         : return qset


class PaginatedModelFormSetView(ListView, ModelFormSetView):
    detail_model               = None
    list_model                 = None
    formset_model              = None
    related_name               = None
    detail_context_object_name = None
    formset_form_class         = None
    paginate_by                = None
    main_object                = None  # should be left as None in subclass
    extra                      = 0
    template_name              = None

    def get_formset_queryset(self):
        # qset      = super(PaginatedModelFormSetView, self).get_formset_queryset()
        qset      = self.get_list_queryset()
        page_size = self.get_paginate_by(qset)
        if page_size : return self.paginate_queryset(qset, page_size)[2]
        else         : return qset

########NEW FILE########
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from dbe.portfolio.models import *

class GroupAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    list_display = ["title", "image_links"]

class ImageAdmin(admin.ModelAdmin):
    list_display = "__unicode__ title group created".split()
    list_filter  = ["group"]

admin.site.register(Group, GroupAdmin)
admin.site.register(Image, ImageAdmin)

########NEW FILE########
__FILENAME__ = fields
# encoding:utf-8
from django import forms as f
from django.forms import widgets
from dbe.shared.utils import *

########NEW FILE########
__FILENAME__ = forms
from django import forms as f
from dbe.portfolio.models import *
from dbe.shared.utils import *

class ImageForm(FormsetModelForm):
    class Meta:
        model   = Image
        exclude = "image width height hidden group thumbnail1 thumbnail2".split()
        attrs   = dict(cols=70)
        widgets = dict( description=f.Textarea(attrs=attrs) )

class AddImageForm(f.ModelForm):
    class Meta:
        model   = Image
        exclude = "width height hidden group thumbnail1 thumbnail2".split()
        attrs   = dict(cols=70, rows=2)
        widgets = dict( description=f.Textarea(attrs=attrs) )

########NEW FILE########
__FILENAME__ = models
import os
from PIL import Image as PImage
from settings import MEDIA_ROOT, MEDIA_URL
from os.path import join as pjoin, basename
from tempfile import NamedTemporaryFile

from django.db.models import *
from django.core.files import File

from dbe.shared.utils import *

link   = "<a href='%s'>%s</a>"
imgtag = "<img border='0' alt='' src='%s' />"


class Group(BaseModel):
    title       = CharField(max_length=60)
    description = TextField(blank=True, null=True)
    link        = URLField(blank=True, null=True)
    hidden      = BooleanField()

    def __unicode__(self):
        return self.title

    def get_absolute_url(self, show="thumbnails"):
        return reverse2("group", dpk=self.pk, show=show)

    def image_links(self):
        lst = [img.image.name for img in self.images.all()]
        lst = [link % ( MEDIA_URL+img, basename(img) ) for img in lst]
        return ", ".join(lst)
    image_links.allow_tags = True


class Image(BaseModel):
    title       = CharField(max_length=60, blank=True, null=True)
    description = TextField(blank=True, null=True)
    image       = ImageField(upload_to="images/")
    thumbnail1  = ImageField(upload_to="images/", blank=True, null=True)
    thumbnail2  = ImageField(upload_to="images/", blank=True, null=True)

    width       = IntegerField(blank=True, null=True)
    height      = IntegerField(blank=True, null=True)
    hidden      = BooleanField()
    group       = ForeignKey(Group, related_name="images", blank=True)
    created     = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]

    def __unicode__(self):
        return self.image.name

    def get_absolute_url(self):
        return reverse2("image", mfpk=self.pk)

    def save(self, *args, **kwargs):
        """Save image dimensions."""
        super(Image, self).save(*args, **kwargs)
        img = PImage.open(pjoin(MEDIA_ROOT, self.image.name))
        self.width, self.height = img.size
        self.save_thumbnail(img, 1, (128,128))
        self.save_thumbnail(img, 2, (64,64))
        super(Image, self).save(*args, **kwargs)

    def save_thumbnail(self, img, num, size):
        fn, ext = os.path.splitext(self.image.name)
        img.thumbnail(size, PImage.ANTIALIAS)
        thumb_fn = fn + "-thumb" + str(num) + ext
        tf = NamedTemporaryFile()
        img.save(tf.name, "JPEG")
        thumbnail = getattr(self, "thumbnail%s" % num)
        thumbnail.save(thumb_fn, File(open(tf.name)), save=False)
        tf.close()

    def size(self):
        return "%s x %s" % (self.width, self.height)

    def thumbnail1_url(self) : return MEDIA_URL + self.thumbnail1.name
    def thumbnail2_url(self) : return MEDIA_URL + self.thumbnail2.name
    def image_url(self)      : return MEDIA_URL + self.image.name

########NEW FILE########
__FILENAME__ = photo
from django import template
from django.conf import settings

from dbe.shared.utils import cjoin

register = template.Library()

def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID

def get(value, arg):
    return value[arg]

def list_related(value):
    if hasattr(value, "all"):
        return cjoin(str(i) for i in value.all())
    return value

def concat(value, arg):
    return value + arg


register.filter("getattribute", getattribute)
register.filter("get", get)
register.filter("concat", concat)
register.filter("list_related", list_related)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from dbe.portfolio.models import *
from dbe.portfolio.views import *

urlpatterns = patterns("dbe.portfolio.views",
   (r"^group/(?P<dpk>\d+)/(?P<show>\S+)/" , GroupView.as_view(), {}, "group"),
   (r"^group/(?P<dpk>\d+)/"               , GroupView.as_view(), {}, "group"),
   (r"^add-images/(?P<dpk>\d+)/"          , AddImages.as_view(), {}, "add_images"),
   (r"^slideshow/(?P<dpk>\d+)/"           , SlideshowView.as_view(), {}, "slideshow"),
   (r"^image/(?P<mfpk>\d+)/"              , ImageView.as_view(), {}, "image"),
   (r"^image/"                            , ImageView.as_view(), {}, "image"),
   (r""                                   , Main.as_view(), {}, "portfolio"),
)

########NEW FILE########
__FILENAME__ = views
from dbe.portfolio.models import *
from dbe.portfolio.forms import *
from settings import MEDIA_URL

from dbe.mcbv.detail import DetailView
from dbe.mcbv.list import ListView
from dbe.mcbv.list_custom import ListRelated, DetailListFormSetView
from dbe.mcbv.edit_custom import FormSetView, UpdateView

from dbe.shared.utils import *


class Main(ListView):
    list_model    = Group
    paginate_by   = 10
    template_name = "portfolio/list.html"

class SlideshowView(ListRelated):
    list_model    = Image
    detail_model  = Group
    related_name  = "images"
    template_name = "slideshow.html"


class GroupView(DetailListFormSetView):
    """List of images in an group, optionally with a formset to update image data."""
    detail_model       = Group
    formset_model      = Image
    formset_form_class = ImageForm
    related_name       = "images"
    paginate_by        = 25
    template_name      = "group.html"

    def add_context(self):
        return dict( show=self.kwargs.get("show", "thumbnails") )

    def process_form(self, form):
        if self.user.is_authenticated(): form.save()

    def get_success_url(self):
        return "%s?%s" % (self.detail_absolute_url(), self.request.GET.urlencode()) # keep page num


class AddImages(DetailView, FormSetView):
    """Add images to a group view."""
    detail_model       = Group
    formset_model      = Image
    formset_form_class = AddImageForm
    template_name      = "add_images.html"
    extra              = 10

    def process_form(self, form):
        form.instance.update( group=self.get_detail_object() )

    def get_success_url(self):
        return self.detail_absolute_url()


class ImageView(UpdateView):
    form_model      = Image
    modelform_class = ImageForm
    template_name   = "portfolio/image.html"

    def form_valid(self, form):
        if self.user.is_authenticated(): form.save()

    def edit(self):
        return self.user.is_authenticated() and self.request.GET.get("edit")


def portfolio_context(request):
    return dict(user=request.user, media_url=MEDIA_URL)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

from dbe.questionnaire.models import *

class SectionInline(admin.TabularInline):
    model = Section
    extra = 6

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 4


class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["name", "section_links"]
    inlines = [SectionInline]

class UserQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["user", "questionnaire"]

class QuestionAdmin(admin.ModelAdmin):
    list_display = "question choices answer_type section".split()

class AnswerAdmin(admin.ModelAdmin):
    list_display = "answer question user_questionnaire".split()
    list_filter = "user_questionnaire answer".split()


class SectionAdmin(admin.ModelAdmin):
    list_display = "name questionnaire order".split()
    inlines = [QuestionInline]

    def response_change(self, request, obj):
        """ Determines the HttpResponse for the change_view stage.

            copied from admin.options.ModelAdmin
        """
        opts = obj._meta

        # Handle proxy models automatically created by .only() or .defer()
        verbose_name = opts.verbose_name
        if obj._deferred:
            opts_ = opts.proxy_for_model._meta
            verbose_name = opts_.verbose_name

        pk_value = obj._get_pk_val()

        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': force_unicode(verbose_name), 'obj': force_unicode(obj)}
        if "_continue" in request.POST:
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if "_popup" in request.REQUEST:
                return HttpResponseRedirect(request.path + "?_popup=1")
            else:
                return HttpResponseRedirect(request.path)
        elif "_saveasnew" in request.POST:
            msg = _('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': force_unicode(verbose_name), 'obj': obj}
            self.message_user(request, msg)
            return HttpResponseRedirect("../%s/" % pk_value)
        elif "_addanother" in request.POST:
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(verbose_name)))
            return HttpResponseRedirect("../add/")
        else:
            self.message_user(request, msg)
            return HttpResponseRedirect(reverse("admin:questionnaire_questionnaire_changelist"))


admin.site.register(Questionnaire, QuestionnaireAdmin)
admin.site.register(UserQuestionnaire, UserQuestionnaireAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms as f
from dbe.questionnaire.models import *

null_choice = [("---", "---")]

class SectionForm(f.Form):
    def __init__(self, *args, **kwargs):
        """ Add a field for every question.
            Field may be CharField or ChoiceField; field name is question.order.
        """
        section = kwargs.pop("section")
        super(SectionForm, self).__init__(*args, **kwargs)

        for question in section.questions.all():
            choices = question.choices
            kw      = dict(help_text=question.question)

            if choices:
                fld           = f.ChoiceField
                choices       = [c.strip() for c in choices.split(',')]
                kw["choices"] = [(c,c) for c in choices]
            else:
                fld              = f.CharField
                kw["max_length"] = 200

            self.fields[str(question.order)] = fld(**kw)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Questionnaire'
        db.create_table('questionnaire_questionnaire', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60)),
        ))
        db.send_create_signal('questionnaire', ['Questionnaire'])

        # Adding model 'UserQuestionnaire'
        db.create_table('questionnaire_userquestionnaire', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='questionnaires', null=True, to=orm['auth.User'])),
            ('questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='user_questionnaires', null=True, to=orm['questionnaire.Questionnaire'])),
        ))
        db.send_create_signal('questionnaire', ['UserQuestionnaire'])

        # Adding model 'QuestionContainer'
        db.create_table('questionnaire_questioncontainer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60, null=True, blank=True)),
            ('questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='containers', null=True, to=orm['questionnaire.Questionnaire'])),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('questionnaire', ['QuestionContainer'])

        # Adding model 'Question'
        db.create_table('questionnaire_question', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('question', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('choices', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('answer_type', self.gf('django.db.models.fields.IntegerField')()),
            ('question_container', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='questions', null=True, to=orm['questionnaire.QuestionContainer'])),
        ))
        db.send_create_signal('questionnaire', ['Question'])

        # Adding model 'Answer'
        db.create_table('questionnaire_answer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='answers', null=True, to=orm['questionnaire.Question'])),
            ('user_questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='answers', null=True, to=orm['questionnaire.UserQuestionnaire'])),
        ))
        db.send_create_signal('questionnaire', ['Answer'])


    def backwards(self, orm):
        
        # Deleting model 'Questionnaire'
        db.delete_table('questionnaire_questionnaire')

        # Deleting model 'UserQuestionnaire'
        db.delete_table('questionnaire_userquestionnaire')

        # Deleting model 'QuestionContainer'
        db.delete_table('questionnaire_questioncontainer')

        # Deleting model 'Question'
        db.delete_table('questionnaire_question')

        # Deleting model 'Answer'
        db.delete_table('questionnaire_answer')


    models = {
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
        'questionnaire.answer': {
            'Meta': {'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.IntegerField', [], {}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'question_container': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.QuestionContainer']"})
        },
        'questionnaire.questioncontainer': {
            'Meta': {'object_name': 'QuestionContainer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'containers'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'object_name': 'UserQuestionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_question_answer_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.CharField')(max_length=6))


    def backwards(self, orm):
        
        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.IntegerField')())


    models = {
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
        'questionnaire.answer': {
            'Meta': {'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'question_container': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.QuestionContainer']"})
        },
        'questionnaire.questioncontainer': {
            'Meta': {'object_name': 'QuestionContainer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'containers'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'object_name': 'UserQuestionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_question_answer_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.CharField')(max_length=6, null=True))


    def backwards(self, orm):
        
        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.CharField')(default='str', max_length=6))


    models = {
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
        'questionnaire.answer': {
            'Meta': {'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'question_container': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.QuestionContainer']"})
        },
        'questionnaire.questioncontainer': {
            'Meta': {'object_name': 'QuestionContainer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'containers'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'object_name': 'UserQuestionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_userquestionnaire_created
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserQuestionnaire.created'
        db.add_column('questionnaire_userquestionnaire', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.date(2012, 3, 15), blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserQuestionnaire.created'
        db.delete_column('questionnaire_userquestionnaire', 'created')


    models = {
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
        'questionnaire.answer': {
            'Meta': {'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'question_container': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.QuestionContainer']"})
        },
        'questionnaire.questioncontainer': {
            'Meta': {'object_name': 'QuestionContainer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'containers'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'object_name': 'UserQuestionnaire'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_question_order
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Question.order'
        db.add_column('questionnaire_question', 'order', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Question.order'
        db.delete_column('questionnaire_question', 'order')


    models = {
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
        'questionnaire.answer': {
            'Meta': {'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'ordering': "['order']", 'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'question_container': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.QuestionContainer']"})
        },
        'questionnaire.questioncontainer': {
            'Meta': {'ordering': "['order']", 'object_name': 'QuestionContainer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'containers'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'object_name': 'UserQuestionnaire'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0006_auto__del_questioncontainer__add_section__add_unique_questionnaire_nam
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'QuestionContainer'
        db.delete_table('questionnaire_questioncontainer')

        # Adding model 'Section'
        db.create_table('questionnaire_section', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60, null=True, blank=True)),
            ('questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sections', null=True, to=orm['questionnaire.Questionnaire'])),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('questionnaire', ['Section'])

        # Adding unique constraint on 'Questionnaire', fields ['name']
        db.create_unique('questionnaire_questionnaire', ['name'])

        # Deleting field 'Question.question_container'
        db.delete_column('questionnaire_question', 'question_container_id')

        # Adding field 'Question.section'
        db.add_column('questionnaire_question', 'section', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='questions', null=True, to=orm['questionnaire.Section']), keep_default=False)

        # Adding unique constraint on 'Question', fields ['section', 'order']
        db.create_unique('questionnaire_question', ['section_id', 'order'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Question', fields ['section', 'order']
        db.delete_unique('questionnaire_question', ['section_id', 'order'])

        # Removing unique constraint on 'Questionnaire', fields ['name']
        db.delete_unique('questionnaire_questionnaire', ['name'])

        # Adding model 'QuestionContainer'
        db.create_table('questionnaire_questioncontainer', (
            ('order', self.gf('django.db.models.fields.IntegerField')()),
            ('questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(related_name='containers', null=True, to=orm['questionnaire.Questionnaire'], blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60, null=True, blank=True)),
        ))
        db.send_create_signal('questionnaire', ['QuestionContainer'])

        # Deleting model 'Section'
        db.delete_table('questionnaire_section')

        # Adding field 'Question.question_container'
        db.add_column('questionnaire_question', 'question_container', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', null=True, to=orm['questionnaire.QuestionContainer'], blank=True), keep_default=False)

        # Deleting field 'Question.section'
        db.delete_column('questionnaire_question', 'section_id')


    models = {
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
        'questionnaire.answer': {
            'Meta': {'ordering': "['question__section__order', 'question__order']", 'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'ordering': "['order']", 'unique_together': "(['section', 'order'],)", 'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.Section']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '60'})
        },
        'questionnaire.section': {
            'Meta': {'ordering': "['order']", 'object_name': 'Section'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sections'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'ordering': "['user', 'created']", 'object_name': 'UserQuestionnaire'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_question_answer_type__add_unique_section_questionnaire
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.CharField')(default='str', max_length=6))

        # Adding unique constraint on 'Section', fields ['questionnaire', 'order']
        db.create_unique('questionnaire_section', ['questionnaire_id', 'order'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Section', fields ['questionnaire', 'order']
        db.delete_unique('questionnaire_section', ['questionnaire_id', 'order'])

        # Changing field 'Question.answer_type'
        db.alter_column('questionnaire_question', 'answer_type', self.gf('django.db.models.fields.CharField')(max_length=6, null=True))


    models = {
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
        'questionnaire.answer': {
            'Meta': {'ordering': "['question__section__order', 'question__order']", 'object_name': 'Answer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.Question']"}),
            'user_questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'answers'", 'null': 'True', 'to': "orm['questionnaire.UserQuestionnaire']"})
        },
        'questionnaire.question': {
            'Meta': {'ordering': "['order']", 'unique_together': "[['section', 'order']]", 'object_name': 'Question'},
            'answer_type': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'choices': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questions'", 'null': 'True', 'to': "orm['questionnaire.Section']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '60'})
        },
        'questionnaire.section': {
            'Meta': {'ordering': "['order']", 'unique_together': "[['questionnaire', 'order']]", 'object_name': 'Section'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sections'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.userquestionnaire': {
            'Meta': {'ordering': "['user', 'created']", 'object_name': 'UserQuestionnaire'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_questionnaires'", 'null': 'True', 'to': "orm['questionnaire.Questionnaire']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'questionnaires'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['questionnaire']

########NEW FILE########
__FILENAME__ = models
from string import join
from django.db.models import *
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from dbe.shared.utils import *

link = "<a href='%s'>%s</a>"


class Questionnaire(BaseModel):
    name = CharField(max_length=60, unique=True)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self, section=1):
        return reverse2("questionnaire", self.pk, section)

    def section_links(self):
        section_url = "admin:questionnaire_section_change"
        lst         = [(c.pk, c.name) for c in self.sections.all()]
        lst         = [ (reverse2(section_url, pk), name) for pk, name in lst ]
        return ", ".join( [link % c for c in lst] )
    section_links.allow_tags = True


class UserQuestionnaire(BaseModel):
    user          = ForeignKey(User, related_name="questionnaires", blank=True, null=True)
    questionnaire = ForeignKey(Questionnaire, related_name="user_questionnaires", blank=True, null=True)
    created       = DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "%s - %s" % (self.user, self.questionnaire)

    class Meta:
        ordering = ["user", "created"]


class Section(BaseModel):
    """Container for a few questions, shown on a single page."""
    name          = CharField(max_length=60, blank=True, null=True)
    questionnaire = ForeignKey(Questionnaire, related_name="sections", blank=True, null=True)
    order         = IntegerField()

    class Meta:
        ordering        = ["order"]
        unique_together = [["questionnaire", "order"]]

    def __unicode__(self):
        return "[%s] (%s) %s" % (self.questionnaire, self.order, self.name or '')

    def title(self):
        return "(%s) %s" % (self.order, self.name or '')



class Question(BaseModel):
    question    = CharField(max_length=200)
    choices     = CharField(max_length=500, blank=True, null=True)
    answer_type = CharField(max_length=6, choices=(("str", "str"), ("int", "int")))
    section     = ForeignKey(Section, related_name="questions", blank=True, null=True)
    order       = IntegerField()

    class Meta:
        ordering        = ["order"]
        unique_together = [["section", "order"]]

    def __unicode__(self):
        return "%s: %s" % (self.section, self.question)


class Answer(BaseModel):
    answer             = CharField(max_length=200)
    question           = ForeignKey(Question, related_name="answers", blank=True, null=True)
    user_questionnaire = ForeignKey(UserQuestionnaire, related_name="answers", blank=True, null=True)

    def __unicode__(self):
        return "%s - %s" % (self.user_questionnaire, self.answer)

    class Meta:
        ordering = ["question__section__order", "question__order"]

########NEW FILE########
__FILENAME__ = todo
from django import template
from django.conf import settings

register = template.Library()

def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID

def get(value, arg):
    return value[arg]

def concat(value, arg):
    return value + arg


register.filter("getattribute", getattribute)
register.filter("get", get)
register.filter("concat", concat)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from dbe.questionnaire.views import *
from django.contrib.auth.decorators import login_required

urlpatterns = patterns("dbe.questionnaire.views",
    (r"^$", login_required(Questionnaires.as_view()), {}, "questionnaires"),

    (r"^questionnaire/(?P<dpk>\d+)/(?P<section>\d+)/$",
     login_required( ViewQuestionnaire.as_view() ), {}, "questionnaire"),

    (r"^questionnaire/(?P<dpk>\d+)/$",
     login_required( ViewQuestionnaire.as_view() ), {}, "questionnaire"),

    (r"^user-questionnaires/(?P<dpk>\d+)/$",
     login_required( UserQuests.as_view() ), {}, "user_questionnaires"),

    (r"^user-questionnaire/(?P<dpk>\d+)/$",
     login_required( UserQuest.as_view() ), {}, "user_questionnaire"),

    (r"^quest-stats/(?P<dpk>\d+)/$",
     login_required( QuestStats.as_view() ), {}, "quest_stats"),
)

urlpatterns += patterns("django.views.generic",
    (r"^done/$", "simple.direct_to_template", dict(template="questionnaire/done.html"), "done"),
)

########NEW FILE########
__FILENAME__ = views
from operator import itemgetter
from collections import OrderedDict

from dbe.shared.utils import *
from dbe.questionnaire.models import *
from dbe.questionnaire.forms import *

from dbe.mcbv.detail import DetailView
from dbe.mcbv.edit import FormView
from dbe.mcbv.list_custom import ListView, ListRelated


class Questionnaires(ListView):
    list_model    = Questionnaire
    template_name = "questionnaires.html"

class UserQuests(ListRelated):
    detail_model  = Questionnaire
    list_model    = UserQuestionnaire
    related_name  = "user_questionnaires"
    template_name = "user-quests.html"

class UserQuest(DetailView):
    detail_model  = UserQuestionnaire
    template_name = "user-quest.html"


class QuestStats(DetailView):
    detail_model  = Questionnaire
    template_name = "quest-stats.html"

    def stats(self):
        user_quests = UserQuestionnaire.obj.filter(questionnaire=self.detail_object)
        d           = DefaultOrderedDict
        #             quests    sections  questions answers:nums
        quests      = d( lambda:d( lambda:d( lambda:d(int) ) ) )

        for user_quest in user_quests:
            quest = user_quest.questionnaire.name

            # add each answer in user questionnaire to respective sections sub-dict, add to counter
            for answer in user_quest.answers.all():
                question = answer.question
                answer   = answer.answer
                q        = question.question
                section  = question.section.name

                quests[quest][section][q][answer] += 1

        # sort to have most frequent answers first
        for quest in quests.values():
            for section in quest.values():
                for name, question in section.items():
                    answers       = sorted(question.items(), key=itemgetter(1), reverse=True)
                    section[name] = OrderedDict(answers)

        return defdict_to_odict(quests)


class ViewQuestionnaire(ListRelated, FormView):
    detail_model  = Questionnaire
    list_model    = Section
    related_name  = "sections"
    form_class    = SectionForm
    template_name = "quest.html"

    def get_section(self):
        self.snum = int(self.kwargs.get("section", 1))
        return self.get_list_queryset()[self.snum-1]

    def get_form_kwargs(self):
        kwargs = super(ViewQuestionnaire, self).get_form_kwargs()
        return dict(kwargs, section=self.get_section())

    def form_valid(self, form):
        """Create user answer records using form data."""
        stotal  = self.get_list_queryset().count()
        quest   = self.get_detail_object()
        uquest  = UserQuestionnaire.obj.get_or_create(questionnaire=quest, user=self.user)[0]
        section = self.get_section()

        for order, value in form.cleaned_data.items():
            question = section.questions.get(order=int(order))
            answer   = Answer.obj.get_or_create(user_questionnaire=uquest, question=question)[0]
            answer.update(answer=value)

        # redirect to the next section or to 'done' page
        if self.snum >= stotal : return redir("done")
        else                   : return redir( quest.get_absolute_url(self.snum+1) )

########NEW FILE########
__FILENAME__ = utils
# Imports {{{
from collections import OrderedDict, Callable
from string import join

from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models import Model, Manager
from django import forms
# }}}

class UserForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(UserForm, self).__init__(*args, **kwargs)

class UserModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(UserModelForm, self).__init__(*args, **kwargs)

class FormsetModelForm(UserModelForm):
    def __iter__(self):
        """Workaround for a bug in modelformset factory."""
        for name in self.fields:
            if name!="id": yield self[name]

class ContainerFormMixin(object):
    """Wrap form data in a container."""
    def clean(self):
        return Container(**self.cleaned_data)


class BasicModel(Model):
    class Meta: abstract = True
    obj = objects = Manager()

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save()

BaseModel = BasicModel      # TODO: rename all views to BaseModel

class BaseError(Exception):
    def __init__(self, e): self.e = e
    def __str__(self): return self.e


class Container:
    def __init__(self, **kwds)  : self.__dict__.update(kwds)
    def __setitem__(self, k, v) : self.__dict__[k] = v
    def __delitem__(self, k)    : del self.__dict__[k]
    def __iter__(self)          : return iter(self.__dict__)
    def __getitem__(self, k)    : return self.__dict__[k]
    def __str__(self)           : return str(self.__dict__)
    def __repr__(self)          : return u"Container: <%s>" % repr(self.__dict__)
    def __unicode__(self)       : return unicode(self.__dict__)
    def __nonzero__(self)       : return len(self.__dict__)
    def pop(self, *args)        : return self.__dict__.pop(*args)
    def get(self, *args)        : return self.__dict__.get(*args)
    def update(self, arg)       : return self.__dict__.update(arg)
    def items(self)             : return self.__dict__.items()
    def keys(self)              : return self.__dict__.keys()
    def values(self)            : return self.__dict__.values()
    def dict(self)              : return self.__dict__
    def pp(self)                : pprint(self.__dict__)


class DefaultOrderedDict(OrderedDict):
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory, copy.deepcopy(self.items()))

    def __repr__(self):
        return 'DefaultOrderedDict(%s, %s)' % (self.default_factory, OrderedDict.__repr__(self))


def redir(to, *args, **kwargs):
    if not (to.startswith('/') or to.startswith("http://") or to.startswith("../") or to=='#'):
        to = reverse(to, args=args, kwargs=kwargs)
    return HttpResponseRedirect(to)

def reverse2(name, *args, **kwargs):
    return reverse(name, args=args, kwargs=kwargs)

def add_csrf(request, **kwargs):
    """Add CSRF to dictionary and wrap in a RequestContext (needed for context processor!)."""
    d = dict(user=request.user, **kwargs)
    d.update(csrf(request))
    return RequestContext(request, d)

def render(request, tpl, **kwargs):
    return render_to_response(tpl, add_csrf(request, **kwargs))

def make_paginator(request, items, per_page=50):
    """Make paginator."""
    try: page = int(request.GET.get("page", '1'))
    except ValueError: page = 1

    paginator = Paginator(items, per_page)
    try:
        items = paginator.page(page)
    except (InvalidPage, EmptyPage):
        items = paginator.page(paginator.num_pages)
    return items

def updated(dict1, dict2):
    return dict(dict1, **dict2)

def referer(request):
    return request.META["HTTP_REFERER"]

def defdict_to_dict(defdict, constructor=dict):
    """ Recursively convert default dicts to regular dicts.
        constructor: convert to a custom type of dict, e.g. OrderedDict
    """
    if isinstance(defdict, dict):
        new = constructor()
        for key, value in defdict.items():
            new[key] = defdict_to_dict(value, constructor)
        return new
    else:
        return defdict

def defdict_to_odict(defdict):
    from collections import OrderedDict
    return defdict_to_dict(defdict, OrderedDict)

def cjoin(lst):
    return join(lst, ", ")

def float_or_none(val):
    return float(val) if val not in ('', None) else None

def int_or_none(val):
    return int(val) if val not in ('', None) else None

def getitem(iterable, index, default=None):
    """Get item from an `iterable` at `index`, return default if index out of range."""
    try               : return iterable[index]
    except IndexError : return default

def first(iterable, default=None):
    try:
        return next(iter(iterable))
    except StopIteration:
        return default

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals

import logging
from functools import update_wrapper

from django import http
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from django.utils.decorators import classonlymethod
from django.utils import six


logger = logging.getLogger('django.request')


class ContextMixin(object):
    """
    A default context mixin that passes the keyword arguments received by
    get_context_data as the template context.
    """
    def add_context(self):
        """Convenience method; may be overridden to add context by returning a dictionary."""
        return {}

    def get_context_data(self, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self
        kwargs.update(self.add_context())
        return kwargs


class View(object):
    """
    Intentionally simple parent class for all views. Only implements
    dispatch-by-method and simple sanity checking.
    """

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace']

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classonlymethod
    def as_view(cls, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.user    = request.user
            self.args    = args
            self.kwargs  = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def initsetup(self):
        pass

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.

        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        self.initsetup()
        return handler(request, *args, **kwargs)

    def http_method_not_allowed(self, request, *args, **kwargs):
        logger.warning('Method Not Allowed (%s): %s', request.method, request.path,
            extra={
                'status_code': 405,
                'request': self.request
            }
        )
        return http.HttpResponseNotAllowed(self._allowed_methods())

    def options(self, request, *args, **kwargs):
        """
        Handles responding to requests for the OPTIONS HTTP verb.
        """
        response = http.HttpResponse()
        response['Allow'] = ', '.join(self._allowed_methods())
        response['Content-Length'] = '0'
        return response

    def _allowed_methods(self):
        return [m.upper() for m in self.http_method_names if hasattr(self, m)]

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class TemplateResponseMixin(object):
    """
    A mixin that can be used to render a template.
    """
    template_name = None
    response_class = TemplateResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response, using the `response_class` for this
        view, with a template rendered with the given context.

        If any keyword arguments are provided, they will be
        passed to the constructor of the response class.
        """
        return self.response_class(
            request = self.request,
            template = self.get_template_names(),
            context = context,
            **response_kwargs
        )

    def get_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        if self.template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'")
        else:
            return [self.template_name]

    def get(self, request, *args, **kwargs):
        from detail import DetailView
        from edit import FormView, FormSetView, ModelFormSetView, CreateView, UpdateView
        from list import ListView

        args    = [request] + list(args)
        context = dict()
        update  = context.update

        if isinstance(self, DetailView)                      : update( self.detail_get(*args, **kwargs) )
        if isinstance(self, FormView)                        : update( self.form_get(*args, **kwargs) )
        if isinstance(self, (FormSetView, ModelFormSetView)) : update( self.formset_get(*args, **kwargs) )
        if isinstance(self, CreateView)                      : update( self.create_get(*args, **kwargs) )
        if isinstance(self, UpdateView)                      : update( self.update_get(*args, **kwargs) )
        if isinstance(self, ListView)                        : update( self.list_get(*args, **kwargs) )

        update(self.get_context_data(**kwargs))
        return self.render_to_response(context)


class TemplateView(TemplateResponseMixin, ContextMixin, View):
    """
    A view that renders a template.  This view will also pass into the context
    any keyword arguments passed by the url conf.
    """
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class RedirectView(View):
    """
    A view that provides a redirect on any GET request.
    """
    permanent = True
    url = None
    query_string = False

    def get_redirect_url(self, **kwargs):
        """
        Return the URL redirect to. Keyword arguments from the
        URL pattern match generating the redirect request
        are provided as kwargs to this method.
        """
        if self.url:
            url = self.url % kwargs
            args = self.request.META.get('QUERY_STRING', '')
            if args and self.query_string:
                url = "%s?%s" % (url, args)
            return url
        else:
            return None

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url:
            if self.permanent:
                return http.HttpResponsePermanentRedirect(url)
            else:
                return http.HttpResponseRedirect(url)
        else:
            logger.warning('Gone: %s', self.request.path,
                        extra={
                            'status_code': 410,
                            'request': self.request
                        })
            return http.HttpResponseGone()

    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = dates
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.views.generic.base import View
from django.views.generic.detail import BaseDetailView, SingleObjectTemplateResponseMixin
from django.views.generic.list import MultipleObjectMixin, MultipleObjectTemplateResponseMixin

class YearMixin(object):
    """
    Mixin for views manipulating year-based data.
    """
    year_format = '%Y'
    year = None

    def get_year_format(self):
        """
        Get a year format string in strptime syntax to be used to parse the
        year from url variables.
        """
        return self.year_format

    def get_year(self):
        """
        Return the year for which this view should display data.
        """
        year = self.year
        if year is None:
            try:
                year = self.kwargs['year']
            except KeyError:
                try:
                    year = self.request.GET['year']
                except KeyError:
                    raise Http404(_("No year specified"))
        return year

    def get_next_year(self, date):
        """
        Get the next valid year.
        """
        return _get_next_prev(self, date, is_previous=False, period='year')

    def get_previous_year(self, date):
        """
        Get the previous valid year.
        """
        return _get_next_prev(self, date, is_previous=True, period='year')

    def _get_next_year(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date.replace(year=date.year + 1, month=1, day=1)

    def _get_current_year(self, date):
        """
        Return the start date of the current interval.
        """
        return date.replace(month=1, day=1)


class MonthMixin(object):
    """
    Mixin for views manipulating month-based data.
    """
    month_format = '%b'
    month = None

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

    def get_month(self):
        """
        Return the month for which this view should display data.
        """
        month = self.month
        if month is None:
            try:
                month = self.kwargs['month']
            except KeyError:
                try:
                    month = self.request.GET['month']
                except KeyError:
                    raise Http404(_("No month specified"))
        return month

    def get_next_month(self, date):
        """
        Get the next valid month.
        """
        return _get_next_prev(self, date, is_previous=False, period='month')

    def get_previous_month(self, date):
        """
        Get the previous valid month.
        """
        return _get_next_prev(self, date, is_previous=True, period='month')

    def _get_next_month(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        if date.month == 12:
            return date.replace(year=date.year + 1, month=1, day=1)
        else:
            return date.replace(month=date.month + 1, day=1)

    def _get_current_month(self, date):
        """
        Return the start date of the previous interval.
        """
        return date.replace(day=1)


class DayMixin(object):
    """
    Mixin for views manipulating day-based data.
    """
    day_format = '%d'
    day = None

    def get_day_format(self):
        """
        Get a day format string in strptime syntax to be used to parse the day
        from url variables.
        """
        return self.day_format

    def get_day(self):
        """
        Return the day for which this view should display data.
        """
        day = self.day
        if day is None:
            try:
                day = self.kwargs['day']
            except KeyError:
                try:
                    day = self.request.GET['day']
                except KeyError:
                    raise Http404(_("No day specified"))
        return day

    def get_next_day(self, date):
        """
        Get the next valid day.
        """
        return _get_next_prev(self, date, is_previous=False, period='day')

    def get_previous_day(self, date):
        """
        Get the previous valid day.
        """
        return _get_next_prev(self, date, is_previous=True, period='day')

    def _get_next_day(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date + datetime.timedelta(days=1)

    def _get_current_day(self, date):
        """
        Return the start date of the current interval.
        """
        return date


class WeekMixin(object):
    """
    Mixin for views manipulating week-based data.
    """
    week_format = '%U'
    week = None

    def get_week_format(self):
        """
        Get a week format string in strptime syntax to be used to parse the
        week from url variables.
        """
        return self.week_format

    def get_week(self):
        """
        Return the week for which this view should display data
        """
        week = self.week
        if week is None:
            try:
                week = self.kwargs['week']
            except KeyError:
                try:
                    week = self.request.GET['week']
                except KeyError:
                    raise Http404(_("No week specified"))
        return week

    def get_next_week(self, date):
        """
        Get the next valid week.
        """
        return _get_next_prev(self, date, is_previous=False, period='week')

    def get_previous_week(self, date):
        """
        Get the previous valid week.
        """
        return _get_next_prev(self, date, is_previous=True, period='week')

    def _get_next_week(self, date):
        """
        Return the start date of the next interval.

        The interval is defined by start date <= item date < next start date.
        """
        return date + datetime.timedelta(days=7 - self._get_weekday(date))

    def _get_current_week(self, date):
        """
        Return the start date of the current interval.
        """
        return date - datetime.timedelta(self._get_weekday(date))

    def _get_weekday(self, date):
        """
        Return the weekday for a given date.

        The first day according to the week format is 0 and the last day is 6.
        """
        week_format = self.get_week_format()
        if week_format == '%W':                 # week starts on Monday
            return date.weekday()
        elif week_format == '%U':               # week starts on Sunday
            return (date.weekday() + 1) % 7
        else:
            raise ValueError("unknown week format: %s" % week_format)


class DateMixin(object):
    """
    Mixin class for views manipulating date-based data.
    """
    date_field = None
    allow_future = False

    def get_date_field(self):
        """
        Get the name of the date field to be used to filter by.
        """
        if self.date_field is None:
            raise ImproperlyConfigured("%s.date_field is required." % self.__class__.__name__)
        return self.date_field

    def get_allow_future(self):
        """
        Returns `True` if the view should be allowed to display objects from
        the future.
        """
        return self.allow_future

    # Note: the following three methods only work in subclasses that also
    # inherit SingleObjectMixin or MultipleObjectMixin.

    @cached_property
    def uses_datetime_field(self):
        """
        Return `True` if the date field is a `DateTimeField` and `False`
        if it's a `DateField`.
        """
        model = self.get_queryset().model if self.model is None else self.model
        field = model._meta.get_field(self.get_date_field())
        return isinstance(field, models.DateTimeField)

    def _make_date_lookup_arg(self, value):
        """
        Convert a date into a datetime when the date field is a DateTimeField.

        When time zone support is enabled, `date` is assumed to be in the
        current time zone, so that displayed items are consistent with the URL.
        """
        if self.uses_datetime_field:
            value = datetime.datetime.combine(value, datetime.time.min)
            if settings.USE_TZ:
                value = timezone.make_aware(value, timezone.get_current_timezone())
        return value

    def _make_single_date_lookup(self, date):
        """
        Get the lookup kwargs for filtering on a single date.

        If the date field is a DateTimeField, we can't just filter on
        date_field=date because that doesn't take the time into account.
        """
        date_field = self.get_date_field()
        if self.uses_datetime_field:
            since = self._make_date_lookup_arg(date)
            until = self._make_date_lookup_arg(date + datetime.timedelta(days=1))
            return {
                '%s__gte' % date_field: since,
                '%s__lt' % date_field: until,
            }
        else:
            # Skip self._make_date_lookup_arg, it's a no-op in this branch.
            return {date_field: date}


class BaseDateListView(MultipleObjectMixin, DateMixin, View):
    """
    Abstract base class for date-based views displaying a list of objects.
    """
    allow_empty = False
    date_list_period = 'year'

    def get(self, request, *args, **kwargs):
        self.date_list, self.object_list, extra_context = self.get_dated_items()
        context = self.get_list_context_data(object_list=self.object_list,
                                             date_list=self.date_list)
        context.update(extra_context)
        return self.render_to_response(context)

    def get_dated_items(self):
        """
        Obtain the list of dates and items.
        """
        raise NotImplementedError('A DateView must provide an implementation of get_dated_items()')

    def get_dated_queryset(self, ordering=None, **lookup):
        """
        Get a queryset properly filtered according to `allow_future` and any
        extra lookup kwargs.
        """
        qs = self.get_queryset().filter(**lookup)
        date_field = self.get_date_field()
        allow_future = self.get_allow_future()
        allow_empty = self.get_allow_empty()
        paginate_by = self.get_paginate_by(qs)

        if ordering is not None:
            qs = qs.order_by(ordering)

        if not allow_future:
            now = timezone.now() if self.uses_datetime_field else timezone_today()
            qs = qs.filter(**{'%s__lte' % date_field: now})

        if not allow_empty:
            # When pagination is enabled, it's better to do a cheap query
            # than to load the unpaginated queryset in memory.
            is_empty = len(qs) == 0 if paginate_by is None else not qs.exists()
            if is_empty:
                raise Http404(_("No %(verbose_name_plural)s available") % {
                        'verbose_name_plural': force_text(qs.model._meta.verbose_name_plural)
                })

        return qs

    def get_date_list_period(self):
        """
        Get the aggregation period for the list of dates: 'year', 'month', or 'day'.
        """
        return self.date_list_period

    def get_date_list(self, queryset, date_type=None, ordering='ASC'):
        """
        Get a date list by calling `queryset.dates()`, checking along the way
        for empty lists that aren't allowed.
        """
        date_field = self.get_date_field()
        allow_empty = self.get_allow_empty()
        if date_type is None:
            date_type = self.get_date_list_period()

        date_list = queryset.dates(date_field, date_type, ordering)
        if date_list is not None and not date_list and not allow_empty:
            name = force_text(queryset.model._meta.verbose_name_plural)
            raise Http404(_("No %(verbose_name_plural)s available") %
                          {'verbose_name_plural': name})

        return date_list


class BaseArchiveIndexView(BaseDateListView):
    """
    Base class for archives of date-based items.

    Requires a response mixin.
    """
    context_object_name = 'latest'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        qs = self.get_dated_queryset(ordering='-%s' % self.get_date_field())
        date_list = self.get_date_list(qs, ordering='DESC')

        if not date_list:
            qs = qs.none()

        return (date_list, qs, {})


class ArchiveIndexView(MultipleObjectTemplateResponseMixin, BaseArchiveIndexView):
    """
    Top-level archive of date-based items.
    """
    template_name_suffix = '_archive'


class BaseYearArchiveView(YearMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    date_list_period = 'month'
    make_object_list = False

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format())

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_year(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(ordering='-%s' % date_field, **lookup_kwargs)
        date_list = self.get_date_list(qs)

        if not self.get_make_object_list():
            # We need this to be a queryset since parent classes introspect it
            # to find information about the model.
            qs = qs.none()

        return (date_list, qs, {
            'year': date,
            'next_year': self.get_next_year(date),
            'previous_year': self.get_previous_year(date),
        })

    def get_make_object_list(self):
        """
        Return `True` if this view should contain the full list of objects in
        the given year.
        """
        return self.make_object_list


class YearArchiveView(MultipleObjectTemplateResponseMixin, BaseYearArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_year'


class BaseMonthArchiveView(YearMixin, MonthMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    date_list_period = 'day'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format())

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_month(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)
        date_list = self.get_date_list(qs)

        return (date_list, qs, {
            'month': date,
            'next_month': self.get_next_month(date),
            'previous_month': self.get_previous_month(date),
        })


class MonthArchiveView(MultipleObjectTemplateResponseMixin, BaseMonthArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_month'


class BaseWeekArchiveView(YearMixin, WeekMixin, BaseDateListView):
    """
    List of objects published in a given week.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        week = self.get_week()

        date_field = self.get_date_field()
        week_format = self.get_week_format()
        week_start = {
            '%W': '1',
            '%U': '0',
        }[week_format]
        date = _date_from_string(year, self.get_year_format(),
                                 week_start, '%w',
                                 week, week_format)

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_week(date))
        lookup_kwargs = {
            '%s__gte' % date_field: since,
            '%s__lt' % date_field: until,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {
            'week': date,
            'next_week': self.get_next_week(date),
            'previous_week': self.get_previous_week(date),
        })


class WeekArchiveView(MultipleObjectTemplateResponseMixin, BaseWeekArchiveView):
    """
    List of objects published in a given week.
    """
    template_name_suffix = '_archive_week'


class BaseDayArchiveView(YearMixin, MonthMixin, DayMixin, BaseDateListView):
    """
    List of objects published on a given day.
    """
    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()

        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        return self._get_dated_items(date)

    def _get_dated_items(self, date):
        """
        Do the actual heavy lifting of getting the dated items; this accepts a
        date object so that TodayArchiveView can be trivial.
        """
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {
            'day': date,
            'previous_day': self.get_previous_day(date),
            'next_day': self.get_next_day(date),
            'previous_month': self.get_previous_month(date),
            'next_month': self.get_next_month(date)
        })


class DayArchiveView(MultipleObjectTemplateResponseMixin, BaseDayArchiveView):
    """
    List of objects published on a given day.
    """
    template_name_suffix = "_archive_day"


class BaseTodayArchiveView(BaseDayArchiveView):
    """
    List of objects published today.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        return self._get_dated_items(datetime.date.today())


class TodayArchiveView(MultipleObjectTemplateResponseMixin, BaseTodayArchiveView):
    """
    List of objects published today.
    """
    template_name_suffix = "_archive_day"


class BaseDateDetailView(YearMixin, MonthMixin, DayMixin, DateMixin, BaseDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    def get_detail_object(self, queryset=None):
        """
        Get the object this request displays.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        # Use a custom queryset if provided
        qs = queryset or self.get_detail_queryset()

        if not self.get_allow_future() and date > datetime.date.today():
            raise Http404(_("Future %(verbose_name_plural)s not available because %(class_name)s.allow_future is False.") % {
                'verbose_name_plural': qs.model._meta.verbose_name_plural,
                'class_name': self.__class__.__name__,
            })

        # Filter down a queryset from self.queryset using the date from the
        # URL. This'll get passed as the queryset to DetailView.get_object,
        # which'll handle the 404
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = qs.filter(**lookup_kwargs)

        return super(BaseDetailView, self).get_detail_object(queryset=qs)


class DateDetailView(SingleObjectTemplateResponseMixin, BaseDateDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    template_name_suffix = '_detail'


def _date_from_string(year, year_format, month='', month_format='', day='', day_format='', delim='__'):
    """
    Helper: get a datetime.date object given a format string and a year,
    month, and day (only year is mandatory). Raise a 404 for an invalid date.
    """
    format = delim.join((year_format, month_format, day_format))
    datestr = delim.join((year, month, day))
    try:
        return datetime.datetime.strptime(datestr, format).date()
    except ValueError:
        raise Http404(_("Invalid date string '%(datestr)s' given format '%(format)s'") % {
            'datestr': datestr,
            'format': format,
        })


def _get_next_prev(generic_view, date, is_previous, period):
    """
    Helper: Get the next or the previous valid date. The idea is to allow
    links on month/day views to never be 404s by never providing a date
    that'll be invalid for the given view.

    This is a bit complicated since it handles different intervals of time,
    hence the coupling to generic_view.

    However in essence the logic comes down to:

        * If allow_empty and allow_future are both true, this is easy: just
          return the naive result (just the next/previous day/week/month,
          reguardless of object existence.)

        * If allow_empty is true, allow_future is false, and the naive result
          isn't in the future, then return it; otherwise return None.

        * If allow_empty is false and allow_future is true, return the next
          date *that contains a valid object*, even if it's in the future. If
          there are no next objects, return None.

        * If allow_empty is false and allow_future is false, return the next
          date that contains a valid object. If that date is in the future, or
          if there are no next objects, return None.

    """
    date_field = generic_view.get_date_field()
    allow_empty = generic_view.get_allow_empty()
    allow_future = generic_view.get_allow_future()

    get_current = getattr(generic_view, '_get_current_%s' % period)
    get_next = getattr(generic_view, '_get_next_%s' % period)

    # Bounds of the current interval
    start, end = get_current(date), get_next(date)

    # If allow_empty is True, the naive result will be valid
    if allow_empty:
        if is_previous:
            result = get_current(start - datetime.timedelta(days=1))
        else:
            result = end

        if allow_future or result <= timezone_today():
            return result
        else:
            return None

    # Otherwise, we'll need to go to the database to look for an object
    # whose date_field is at least (greater than/less than) the given
    # naive result
    else:
        # Construct a lookup and an ordering depending on whether we're doing
        # a previous date or a next date lookup.
        if is_previous:
            lookup = {'%s__lt' % date_field: generic_view._make_date_lookup_arg(start)}
            ordering = '-%s' % date_field
        else:
            lookup = {'%s__gte' % date_field: generic_view._make_date_lookup_arg(end)}
            ordering = date_field

        # Filter out objects in the future if appropriate.
        if not allow_future:
            # Fortunately, to match the implementation of allow_future,
            # we need __lte, which doesn't conflict with __lt above.
            if generic_view.uses_datetime_field:
                now = timezone.now()
            else:
                now = timezone_today()
            lookup['%s__lte' % date_field] = now

        qs = generic_view.get_queryset().filter(**lookup).order_by(ordering)

        # Snag the first object from the queryset; if it doesn't exist that
        # means there's no next/previous link available.
        try:
            result = getattr(qs[0], date_field)
        except IndexError:
            return None

        # Convert datetimes to dates in the current time zone.
        if generic_view.uses_datetime_field:
            if settings.USE_TZ:
                result = timezone.localtime(result)
            result = result.date()

        # Return the first day of the period.
        return get_current(result)


def timezone_today():
    """
    Return the current date in the current time zone.
    """
    if settings.USE_TZ:
        return timezone.localtime(timezone.now()).date()
    else:
        return datetime.date.today()

########NEW FILE########
__FILENAME__ = detail
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.utils.translation import ugettext as _

from base import TemplateResponseMixin, ContextMixin, View


class SingleObjectMixin(ContextMixin):
    """
    Provides the ability to retrieve a single object for further manipulation.
    """
    detail_model               = None
    detail_context_object_name = None
    detail_queryset            = None
    detail_pk_url_kwarg        = 'dpk'
    slug_field                 = 'slug'
    slug_url_kwarg             = 'slug'

    def get_object(self, queryset=None, pk_url_kwarg=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(pk_url_kwarg, None)

        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_detail_object(self, queryset=None):
        return self.get_object( queryset or self.get_detail_queryset(), self.detail_pk_url_kwarg )

    def get_queryset(self, model):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if model:
            return model._default_manager.all()
        else:
            raise ImproperlyConfigured("%(cls)s is missing a queryset. Define "
                                       "%(cls)s.detail_model, %(cls)s.detail_queryset, or override "
                                       "%(cls)s.get_detail_queryset()." % {
                                            'cls': self.__class__.__name__
                                    })

    def get_detail_queryset(self):
        if self.detail_queryset:
            return self.detail_queryset._clone()
        else:
            return self.get_queryset(self.detail_model)

    def get_slug_field(self):
        """
        Get the name of a slug field to be used to look up by slug.
        """
        return self.slug_field

    def get_detail_context_object_name(self, obj):
        """
        Get the name to use for the object.
        """
        if self.detail_context_object_name:
            return self.detail_context_object_name
        elif isinstance(obj, models.Model):
            return obj._meta.object_name.lower()
        else:
            return None

    def get_detail_context_data(self, **kwargs):
        """
        Insert the single object into the context dict.
        """
        context = {}
        context_object_name = self.get_detail_context_object_name(self.detail_object)
        if context_object_name:
            context[context_object_name] = self.detail_object
        context.update(kwargs)
        return context

    def detail_absolute_url(self):
        return self.get_detail_object().get_absolute_url()


class BaseDetailView(SingleObjectMixin, View):
    """
    A base view for displaying a single object
    """
    def detail_get(self, request, *args, **kwargs):
        self.detail_object = self.get_detail_object()
        return self.get_detail_context_data(detail_object=self.detail_object)


class SingleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_field = None
    template_name_suffix = '_detail'

    def get_template_names(self):
        return self._get_template_names(self.detail_object, self.detail_model)

    def _get_template_names(self, object=None, model=None):
        """
        Return a list of template names to be used for the request. May not be
        called if render_to_response is overridden. Returns the following list:

        * the value of ``template_name`` on the view (if provided)
        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * ``<app_label>/<object_name><template_name_suffix>.html``
        """
        try:
            names = super(SingleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If self.template_name_field is set, grab the value of the field
        # of that name from the object; this is the most specific template
        # name, if given.
        if object and self.template_name_field:
            name = getattr(self.detail_object, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<model>_detail.html;
        # only use this if the object in question is a model.
        if isinstance(object, models.Model):
            names.append("%s/%s%s.html" % (
                object._meta.app_label,
                object._meta.object_name.lower(),
                self.template_name_suffix
            ))
        elif model is not None and issubclass(model, models.Model):
            names.append("%s/%s%s.html" % (
                model._meta.app_label,
                model._meta.object_name.lower(),
                self.template_name_suffix
            ))
        return names


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """

########NEW FILE########
__FILENAME__ = edit
from django.forms import models as model_forms
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.utils.encoding import force_text
from django.db import models
from django.contrib import messages

from django.utils.functional import curry
from django.forms.formsets import formset_factory, BaseFormSet, all_valid
from django.forms.models import modelformset_factory

from base import TemplateResponseMixin, ContextMixin, View
from detail import SingleObjectMixin, SingleObjectTemplateResponseMixin, BaseDetailView, DetailView
from list import MultipleObjectMixin, ListView


class FormMixin(ContextMixin):
    """
    A mixin that provides a way to show and handle a form in a request.
    """

    initial         = {}
    form_class      = None
    success_url     = None
    form_kwarg_user = False     # provide request user to form

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        return self.initial.copy()

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        return self.form_class

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        form_class = form_class or self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {'initial': self.get_initial()}
        if self.form_kwarg_user:
            kwargs['user'] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def form_valid(self, form):
        """
        If the form is valid, redirect to the supplied URL.
        """
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """
        If the form or modelform are invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.get_context_data(form=form)


class FormSetMixin(FormMixin):
    """A mixin that provides a way to show and handle a formset in a request."""
    formset_form_class = None
    formset_initial    = {}
    formset_class      = BaseFormSet
    extra              = 0
    can_delete         = False
    # ignore_get_args    = ("page", )     # TODO this may be better moved to the form class?

    formset_kwarg_user = False       # provide request user to form
    success_url        = None

    def get_formset_initial(self):
        return self.formset_initial.copy()

    def get_formset_class(self):
        return self.formset_class

    def get_formset_form_class(self):
        return self.formset_form_class

    def get_formset(self, form_class=None):
        form_class = form_class or self.formset_form_class
        kwargs     = dict()
        Formset    = formset_factory(form_class, extra=self.extra, can_delete=self.can_delete)

        if self.form_kwarg_user:
            kwargs["user"] = self.user

        Formset.form = staticmethod(curry(form_class, **kwargs))
        return Formset(**self.get_formset_kwargs())

    def get_formset_kwargs(self):
        kwargs = dict(initial=self.get_formset_initial())

        if self.formset_kwarg_user:
            kwargs["user"] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def formset_valid(self, formset):
        for form in formset:
            if form.has_changed():
                if form.cleaned_data.get("DELETE"):
                    self.process_delete(form)
                else:
                    self.process_form(form)
        return HttpResponseRedirect(self.get_success_url())

    def process_form(self, form):
        form.save()

    def process_delete(self, form):
        """Process checked 'delete' box."""
        pass

    def formset_invalid(self, formset):
        return self.get_context_data(formset=formset)


class ModelFormSetMixin(FormSetMixin):
    formset_model    = None
    formset_queryset = None

    def get_formset_queryset(self):
        if self.formset_queryset is not None:
            queryset = self.formset_queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.formset_model is not None:
            queryset = self.formset_model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'formset_queryset' or 'formset_model'"
                                        % self.__class__.__name__)
        return queryset

    def get_formset(self, form_class=None):
        form_class = form_class or self.formset_form_class
        kwargs     = dict()
        Formset    = modelformset_factory(self.formset_model, extra=self.extra, can_delete=self.can_delete)

        if self.form_kwarg_user:
            kwargs["user"] = self.user

        Formset.form = staticmethod(curry(form_class, **kwargs))
        return Formset(**self.get_formset_kwargs())

    def get_formset_kwargs(self):
        kwargs = {
                  'initial'  : self.get_formset_initial(),
                  'queryset' : self.get_formset_queryset(),
                  }

        if self.formset_kwarg_user:
            kwargs["user"] = self.request.user

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def process_delete(self, form):
        """Process checked 'delete' box."""
        form.instance.delete()


class ModelFormMixin(FormMixin, SingleObjectMixin):
    """
    A mixin that provides a way to show and handle a modelform in a request.
    """
    form_model                    = None
    modelform_class               = None
    modelform_queryset            = None
    modelform_context_object_name = None
    modelform_pk_url_kwarg        = 'mfpk'
    modelform_valid_msg           = None

    def get_modelform_class(self):
        """Returns the form class to use in this view."""
        if self.modelform_class:
            return self.modelform_class
        else:
            if self.form_model is not None:
                # If a model has been explicitly provided, use it
                model = self.form_model
            elif hasattr(self, 'modelform_object') and self.modelform_object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.modelform_object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_modelform_queryset().model
            return model_forms.modelform_factory(model)

    def get_modelform(self, form_class=None):
        form_class = form_class or self.get_modelform_class()
        return form_class(**self.get_modelform_kwargs())

    def get_modelform_kwargs(self):
        """Returns the keyword arguments for instantiating the form."""
        kwargs = super(ModelFormMixin, self).get_form_kwargs()
        kwargs.update({'instance': self.modelform_object})
        return kwargs

    def get_success_url(self):
        """Returns the supplied URL."""
        if self.success_url:
            url = self.success_url % self.modelform_object.__dict__
        else:
            try:
                url = self.modelform_object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the Model.")
        return url

    def modelform_valid(self, modelform):
        self.modelform_object = modelform.save()
        if self.modelform_valid_msg:
            messages.info(self.request, self.modelform_valid_msg)
        return HttpResponseRedirect(self.get_success_url())

    def modelform_invalid(self, modelform):
        return self.get_context_data(modelform=modelform)

    def get_modelform_context_data(self, **kwargs):
        """
        If an object has been supplied, inject it into the context with the
        supplied modelform_context_object_name name.
        """
        context = {}
        obj = self.modelform_object
        if obj:
            context['modelform_object'] = obj
            if self.modelform_context_object_name:
                context[self.modelform_context_object_name] = obj
            elif isinstance(obj, models.Model):
                context[obj._meta.object_name.lower()] = obj
        context.update(kwargs)
        return context

    def get_modelform_object(self, queryset=None):
        return self.get_object( queryset or self.get_modelform_queryset(), self.modelform_pk_url_kwarg )

    def get_modelform_queryset(self):
        if self.modelform_queryset:
            return self.modelform_queryset._clone()
        else:
            return self.get_queryset(self.form_model)


class ProcessFormView(View):
    """
    A mixin that renders a form on GET and processes it on POST.
    """

    def form_get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        return self.get_context_data( form=self.get_form() )

    def formset_get(self, request, *args, **kwargs):
        return self.get_context_data( formset=self.get_formset() )

    def modelform_get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        return self.get_modelform_context_data( modelform=self.get_modelform() )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = formset = modelform = None

        if isinstance(self, DetailView):
            self.detail_object = self.get_detail_object()

        if isinstance(self, ListView):
            self.object_list = self.get_list_queryset()

        if isinstance(self, FormView):
            form = self.get_form()

        if isinstance(self, (FormSetView, ModelFormSetView)):
            formset = self.get_formset()

        if isinstance(self, UpdateView):
            self.update_post(request, *args, **kwargs)
            modelform = self.get_modelform()

        if isinstance(self, CreateView):
            self.create_post(request, *args, **kwargs)
            modelform = self.get_modelform()

        if (not form or form and form.is_valid()) and \
           (not modelform or modelform and modelform.is_valid()) and \
           (not formset or formset and formset.is_valid()):

            if isinstance(self, FormView)                        : resp = self.form_valid(form)
            if isinstance(self, (FormSetView, ModelFormSetView)) : resp = self.formset_valid(formset)
            if isinstance(self, (UpdateView, CreateView))        : resp = self.modelform_valid(modelform)
            return resp

        else:
            context = self.get_context_data()
            update  = context.update
            if isinstance(self, FormView)                        : update(self.form_invalid(form))
            if isinstance(self, (FormSetView, ModelFormSetView)) : update(self.formset_invalid(formset))
            if isinstance(self, (UpdateView, CreateView))        : update(self.modelform_invalid(modelform))
            return self.render_to_response(context)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class BaseFormView(FormMixin, ProcessFormView):
    """ A base view for displaying a form """

class FormView(TemplateResponseMixin, BaseFormView):
    """ A view for displaying a form, and rendering a template response. """

class BaseFormSetView(FormSetMixin, ProcessFormView):
    """A base view for displaying a formset."""

class FormSetView(TemplateResponseMixin, BaseFormSetView):
    """A view for displaying a formset, and rendering a template response."""


class BaseModelFormSetView(ModelFormSetMixin, ProcessFormView):
    """A base view for displaying a modelformset."""

class ModelFormSetView(TemplateResponseMixin, BaseModelFormSetView):
    """A view for displaying a modelformset, and rendering a template response."""



class BaseCreateView(ModelFormMixin, ProcessFormView):
    """
    Base view for creating an new object instance.

    Using this base class requires subclassing to provide a response mixin.
    """
    def create_get(self, request, *args, **kwargs):
        self.modelform_object = None
        return self.modelform_get(request, *args, **kwargs)

    def create_post(self, request, *args, **kwargs):
        self.modelform_object = None


class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    """
    View for creating a new object instance,
    with a response rendered by template.
    """
    template_name_suffix = '_modelform'

    def get_template_names(self):
        return self._get_template_names(self.modelform_object, self.form_model)


class BaseUpdateView(ModelFormMixin, ProcessFormView):
    """
    Base view for updating an existing object.

    Using this base class requires subclassing to provide a response mixin.
    """
    def update_get(self, request, *args, **kwargs):
        self.modelform_object = self.get_modelform_object()
        return self.modelform_get(request, *args, **kwargs)

    def update_post(self, request, *args, **kwargs):
        self.modelform_object = self.get_modelform_object()


class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    """
    View for updating an object,
    with a response rendered by template.
    """
    template_name_suffix = '_modelform'

    def get_template_names(self):
        return self._get_template_names(self.modelform_object, self.form_model)


class CreateUpdateView(CreateView):
    """Update object if modelform_pk_url_kwarg is in kwargs, otherwise create it."""
    modelform_create_class = None

    def get_modelform_class(self):
        if self.modelform_pk_url_kwarg in self.kwargs:
            return self.modelform_class
        else:
            return self.modelform_create_class

    def create_get(self, request, *args, **kwargs):
        if self.modelform_pk_url_kwarg in self.kwargs:
            self.modelform_object = self.get_modelform_object()
            return self.modelform_get(request, *args, **kwargs)
        else:
            return super(CreateUpdateView, self).create_get(request, *args, **kwargs)

    def create_post(self, request, *args, **kwargs):
        if self.modelform_pk_url_kwarg in self.kwargs:
            self.modelform_object = self.get_modelform_object()
        else:
            super(CreateUpdateView, self).create_post(request, *args, **kwargs)


class DeletionMixin(object):
    """
    A mixin providing the ability to delete objects
    """
    success_url = None

    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.
        """
        self.modelform_object = self.get_modelform_object()
        self.modelform_object.delete()
        return HttpResponseRedirect(self.get_success_url())

    # Add support for browsers which only accept GET and POST for now.
    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def get_success_url(self):
        if self.success_url:
            return self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")


class BaseDeleteView(DeletionMixin, BaseDetailView):
    """
    Base view for deleting an object.

    Using this base class requires subclassing to provide a response mixin.
    """


class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    """
    View for deleting an object retrieved with `self.get_object()`,
    with a response rendered by template.
    """
    template_name_suffix = '_confirm_delete'

########NEW FILE########
__FILENAME__ = edit_custom
from copy import copy
from django.forms import formsets
from django.contrib import messages
from django.db.models import Q
from django.forms.formsets import formset_factory, BaseFormSet, all_valid

from detail import *
from edit import *


class SearchFormViewMixin(BaseFormView):
    ignore_get_keys = ("page", )    # TODO this should be ignored in search form?

    def get_form_kwargs(self):
        """Returns the keyword arguments for instantiating the form."""
        req    = self.request
        kwargs = dict(initial=self.get_initial())

        if req.method in ("POST", "PUT"):
            kwargs.update(dict(data=req.POST, files=req.FILES))
        elif req.GET:
            # do get form processing if there's get data that's not in ignore list
            get = dict((k,v) for k,v in req.GET.items() if k not in self.ignore_get_keys)
            if get:
                kwargs = dict(kwargs, initial=get, data=get)
        return kwargs

    def form_get(self, request):
        form    = self.get_form()
        context = self.get_context_data(form=form)

        if self.request.GET:
            if form.is_valid() : context.update(self.form_valid(form))
            else               : context.update(self.form_invalid(form))
        return context


class SearchFormView(FormView, SearchFormViewMixin):
    """FormView for search pages."""


class OwnObjMixin(SingleObjectMixin):
    """Access object, checking that it belongs to current user."""
    item_name   = None          # used in permissions error message
    owner_field = "creator"     # object's field to compare to current user to check permission

    def permission_error(self):
        name = self.item_name or self.object.__class__.__name__
        return HttpResponse("You don't have permissions to access this %s." % name)

    def validate(self, obj):
        if getattr(obj, self.owner_field) == self.request.user:
            return True

    def get_object(self, queryset=None):
        obj = super(OwnObjMixin, self).get_object(queryset)
        return obj if self.validate(obj) else None


class DeleteOwnObjView(OwnObjMixin, DeleteView):
    """Delete object, checking that it belongs to current user."""


class UpdateOwnObjView(OwnObjMixin, UpdateView):
    """Update object, checking that it belongs to current user."""


class UpdateRelatedView(DetailView, UpdateView):
    """Update object related to detail object; create if does not exist."""
    detail_model = None
    form_model   = None
    fk_attr      = None
    related_name = None

    def get_modelform_object(self, queryset=None):
        """ Get related object: detail_model.<related_name>
            If does not exist, create: form_model.<fk_attr>
        """
        obj    = self.get_detail_object()
        kwargs = {self.fk_attr: obj}
        try:
            related_obj = getattr(obj, self.related_name)
        except self.form_model.DoesNotExist:
            related_obj = self.form_model.obj.create(**kwargs)
            setattr(obj, self.related_name, related_obj)
        return related_obj


class SearchEditFormset(SearchFormView):
    """Search form filtering a formset of items to be updated."""
    model         = None
    formset_class = None
    form_class    = None

    def get_form_class(self):
        if self.request.method == "GET": return self.form_class
        else: return self.formset_class

    def get_queryset(self, form=None):
        return self.model.objects.filter(self.get_query(form))

    def get_query(self, form):
        """This method should always be overridden, applying search from the `form`."""
        return Q()

    def form_valid(self, form):
        formset = None
        if self.request.method == "GET":
            formset = self.formset_class(queryset=self.get_queryset(form))
        else:
            form.save()
            messages.success(self.request, "%s(s) were updated successfully" % self.model.__name__.capitalize())
            formset = form
            form = self.form_class(self.request.GET)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_invalid(self, form):
        formset = form
        form = self.form_class(self.request.GET)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_bound:
            if form.is_valid(): return self.form_valid(form)
            else: return self.form_invalid(form)
        return self.render_to_response(self.get_context_data(form=form))

########NEW FILE########
__FILENAME__ = list
from __future__ import unicode_literals

from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.translation import ugettext as _

from base import TemplateResponseMixin, ContextMixin, View


class MultipleObjectMixin(ContextMixin):
    """
    A mixin for views manipulating multiple objects.
    """
    allow_empty              = True
    list_queryset            = None
    list_model               = None
    paginate_by              = None
    list_context_object_name = None
    paginate_orphans         = 0
    paginator_class          = Paginator
    page_kwarg               = 'page'

    def get_list_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if self.list_queryset is not None:
            queryset = self.list_queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.list_model is not None:
            queryset = self.list_model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'list_queryset' or 'list_model'"
                                       % self.__class__.__name__)
        return queryset

    def paginate_queryset(self, queryset, page_size):
        """
        Paginate the queryset, if needed.
        """
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_("Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage as e:
            raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                                'page_number': page_number,
                                'message': str(e)
            })

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        """
        Return an instance of the paginator for this view.
        """
        return self.paginator_class(
            queryset, per_page, orphans=orphans,
            allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_paginate_orphans(self):
        """
        Returns the maximum number of orphans extend the last page by when
        paginating.
        """
        return self.paginate_orphans

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_list_context_object_name(self, object_list):
        """
        Get the name of the item to be used in the context.
        """
        if self.list_context_object_name:
            return self.list_context_object_name
        elif hasattr(object_list, 'model'):
            return '%s_list' % object_list.model._meta.object_name.lower()
        else:
            return None

    def get_list_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        if "object_list" not in kwargs:
            kwargs["object_list"] = self.get_queryset()

        queryset            = kwargs.pop('object_list')
        page_size           = self.get_paginate_by(queryset)
        context_object_name = self.get_list_context_object_name(queryset)
        page                = None

        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
            context = {
                'paginator': paginator,
                'page_obj': page,
                'is_paginated': is_paginated,
                'object_list': page.object_list
            }
        else:
            context = {
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
                'object_list': queryset
            }

        if context_object_name is not None:
            context[context_object_name] = context["object_list"]
        context.update(kwargs)
        return context


class BaseListView(MultipleObjectMixin, View):
    """
    A base view for displaying a list of objects.
    """
    def list_get(self, request, *args, **kwargs):
        self.object_list = self.get_list_queryset()
        allow_empty      = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if (self.get_paginate_by(self.object_list) is not None
                and hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
                        % {'class_name': self.__class__.__name__})
        return self.get_list_context_data(object_list=self.object_list)


class MultipleObjectTemplateResponseMixin(TemplateResponseMixin):
    """
    Mixin for responding with a template and list of objects.
    """
    template_name_suffix = '_list'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        try:
            names = super(MultipleObjectTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If the list is a queryset, we'll invent a template name based on the
        # app and model name. This name gets put at the end of the template
        # name list so that user-supplied names override the automatically-
        # generated ones.
        if hasattr(self.object_list, 'model'):
            opts = self.object_list.model._meta
            names.append("%s/%s%s.html" % (opts.app_label, opts.object_name.lower(), self.template_name_suffix))

        return names


class ListView(MultipleObjectTemplateResponseMixin, BaseListView):
    """
    Render some list of objects, set by `self.model` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """

########NEW FILE########
__FILENAME__ = list_custom
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.forms.models import modelformset_factory
from django.core.urlresolvers import reverse

from list import *
from edit_custom import *


class PaginatedSearch(ListView, SearchFormView):
    """ List Filter - filter list with a search form.

        as_view      : dispatch -> get or post
        get          : get_form OR get_queryset -> get_context_data -> render_to_response
        post         : get_form -> get_form_kwargs -> form_valid or form_invalid
        form_valid   : get_success_url
        form_invalid : get_context_data -> render_to_response

        as_view, dispatch      : base.View
        render_to_response     : TemplateResponseMixin

        get                    : BaseListView
        post                   : ProcessFormView
        get_form, form_invalid : FormMixin
        get_form_kwargs        : SearchFormViewMixin

        form_valid, get_success_url, get_queryset, get_context_data
    """
    object_list = None

    def get_list_queryset(self):
        return self.object_list or []

    def get_list_context_data(self, **kwargs):
        context = super(PaginatedSearch, self).get_list_context_data(**kwargs)
        get     = self.request.GET.copy()
        get.pop("page", None)
        extra = '&'+get.urlencode()
        return dict(context, extra_vars=extra, form=self.get_form())


class ListFilterView(PaginatedSearch):
    """Filter a list view through a search."""
    list_model   = None
    search_field = 'q'
    start_blank  = True     # start with full item listing or blank page

    def get_list_queryset(self):
        if self.object_list:
            return self.object_list
        else:
            return list() if self.start_blank else self.list_model.objects.all()

    def get_query(self, q):
        return Q()

    def form_valid(self, form):
        q                = form.cleaned_data[self.search_field].strip()
        filter           = self.list_model.objects.filter
        self.object_list = filter(self.get_query(q)) if q else None
        return dict(form=form)


class ListRelated(DetailView, ListView):
    """Listing of an object and related items."""
    related_name = None      # attribute name linking main object to related objects

    def get_list_queryset(self):
        obj = self.get_detail_object()
        return getattr(obj, self.related_name).all()


class DetailListCreateView(ListRelated, CreateView):
    """ DetailView of an object & listing of related objects and a form to create new related obj.

        fk_attr : field of object to be created that points back to detail_object, e.g.:
                    detail_model = Thread; fk_attr = "thread"; reply.thread = detail_object
    """
    success_url = '#'
    fk_attr     = None

    def modelform_valid(self, modelform):
        self.modelform_object = modelform.save(commit=False)
        setattr(self.modelform_object, self.fk_attr, self.get_detail_object())
        self.modelform_object.save()
        return HttpResponseRedirect(self.get_success_url())


class DetailListFormSetView(ListRelated, ModelFormSetView):
    """ List of items related to main item, viewed as a paginated formset.
        Note: `list_model` needs to have ordering specified for it to be able to paginate.
    """
    detail_model               = None
    list_model                 = None
    formset_model              = None
    related_name               = None
    detail_context_object_name = None
    formset_form_class         = None
    paginate_by                = None
    main_object                = None  # should be left as None in subclass
    extra                      = 0
    template_name              = None

    def get_formset_queryset(self):
        qset      = self.get_list_queryset()
        page_size = self.get_paginate_by(qset)
        if page_size : return self.paginate_queryset(qset, page_size)[2]
        else         : return qset


class PaginatedModelFormSetView(ListView, ModelFormSetView):
    detail_model               = None
    list_model                 = None
    formset_model              = None
    related_name               = None
    detail_context_object_name = None
    formset_form_class         = None
    paginate_by                = None
    main_object                = None  # should be left as None in subclass
    extra                      = 0
    template_name              = None

    def get_formset_queryset(self):
        # qset      = super(PaginatedModelFormSetView, self).get_formset_queryset()
        qset      = self.get_list_queryset()
        page_size = self.get_paginate_by(qset)
        if page_size : return self.paginate_queryset(qset, page_size)[2]
        else         : return qset

########NEW FILE########
