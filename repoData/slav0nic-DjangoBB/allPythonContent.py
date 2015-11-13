__FILENAME__ = admin
# coding: utf-8

from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from djangobb_forum.models import Category, Forum, Topic, Post, Profile, Reputation, \
    Report, Ban, Attachment, Poll, PollChoice, PostTracking


class BaseModelAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        # disabled, because delete_selected ignoring delete model method
        actions = super(BaseModelAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class CategoryAdmin(BaseModelAdmin):
    list_display = ['name', 'position', 'forum_count']

class ForumAdmin(BaseModelAdmin):
    list_display = ['name', 'category', 'position', 'topic_count']
    raw_id_fields = ['moderators', 'last_post']

class TopicAdmin(BaseModelAdmin):
    def subscribers2(self, obj):
        return ", ".join([user.username for user in obj.subscribers.all()])
    subscribers2.short_description = _("subscribers")

    list_display = ['name', 'forum', 'created', 'head', 'post_count', 'subscribers2']
    search_fields = ['name']
    raw_id_fields = ['user', 'subscribers', 'last_post']

class PostAdmin(BaseModelAdmin):
    list_display = ['topic', 'user', 'created', 'updated', 'summary']
    search_fields = ['body']
    raw_id_fields = ['topic', 'user', 'updated_by']

class ProfileAdmin(BaseModelAdmin):
    list_display = ['user', 'status', 'time_zone', 'location', 'language']
    raw_id_fields = ['user']

class PostTrackingAdmin(BaseModelAdmin):
    list_display = ['user', 'last_read', 'topics']
    raw_id_fields = ['user']

class ReputationAdmin(BaseModelAdmin):
    list_display = ['from_user', 'to_user', 'post', 'sign', 'time', 'reason']
    raw_id_fields = ['from_user', 'to_user', 'post']

class ReportAdmin(BaseModelAdmin):
    list_display = ['reported_by', 'post', 'zapped', 'zapped_by', 'created', 'reason']
    raw_id_fields = ['reported_by', 'post']

class BanAdmin(BaseModelAdmin):
    list_display = ['user', 'ban_start', 'ban_end', 'reason']
    raw_id_fields = ['user']

class UserAdmin(auth_admin.UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
                        url(r'^(\d+)/password/$', self.admin_site.admin_view(self.user_change_password), name='user_change_password'),
                        ) + super(auth_admin.UserAdmin, self).get_urls()

class AttachmentAdmin(BaseModelAdmin):
    list_display = ['id', 'name', 'size', 'path', 'hash', ]
    search_fields = ['name']
    list_display_links = ('name',)
    list_filter = ("content_type",)


class PollChoiceInline(admin.TabularInline):
    model = PollChoice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "active",)
    list_display_links = ("question",)
    list_editable = ("active",)
    list_filter = ("active",)
    inlines = [PollChoiceInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(Category, CategoryAdmin)
admin.site.register(Forum, ForumAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(PostTracking, PostTrackingAdmin)
admin.site.register(Reputation, ReputationAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Ban, BanAdmin)
admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(Poll, PollAdmin)


########NEW FILE########
__FILENAME__ = context_processors
# coding: utf-8


from django.conf import settings

from djangobb_forum import settings as djangobb_settings


def forum_settings(request):
    return {
        'forum_settings': djangobb_settings,
        'DEBUG': settings.DEBUG,
    }

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.utils.feedgenerator import Atom1Feed
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.http import Http404

from djangobb_forum.models import Post, Topic, Forum, Category

class ForumFeed(Feed):
    feed_type = Atom1Feed

    def link(self):
        return reverse('djangobb:index')

    def item_guid(self, obj):
        return str(obj.id)

    def item_pubdate(self, obj):
        return obj.created

    def item_author_name(self, item):
        return item.user.username


class LastPosts(ForumFeed):
    title = _('Latest posts on forum')
    description = _('Latest posts on forum')
    title_template = 'djangobb_forum/feeds/posts_title.html'
    description_template = 'djangobb_forum/feeds/posts_description.html'

    def get_object(self, request):
        user_groups = request.user.groups.all()
        if request.user.is_anonymous():
            user_groups = []
        allow_forums = Forum.objects.filter(
                Q(category__groups__in=user_groups) | \
                Q(category__groups__isnull=True))
        return allow_forums

    def items(self, allow_forums):
        return Post.objects.filter(topic__forum__in=allow_forums).order_by('-created')[:15]


class LastTopics(ForumFeed):
    title = _('Latest topics on forum')
    description = _('Latest topics on forum')
    title_template = 'djangobb_forum/feeds/topics_title.html'
    description_template = 'djangobb_forum/feeds/topics_description.html'

    def get_object(self, request):
        user_groups = request.user.groups.all()
        if request.user.is_anonymous():
            user_groups = []
        allow_forums = Forum.objects.filter(
                Q(category__groups__in=user_groups) | \
                Q(category__groups__isnull=True))
        return allow_forums

    def items(self, allow_forums):
        return Topic.objects.filter(forum__in=allow_forums).order_by('-created')[:15]


class LastPostsOnTopic(ForumFeed):
    title_template = 'djangobb_forum/feeds/posts_title.html'
    description_template = 'djangobb_forum/feeds/posts_description.html'
    
    def get_object(self, request, topic_id):
        topic = Topic.objects.get(id=topic_id)
        if not topic.forum.category.has_access(request.user):
            raise Http404
        return topic

    def title(self, obj):
        return _('Latest posts on %s topic' % obj.name)

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return _('Latest posts on %s topic' % obj.name)

    def items(self, obj):
        return Post.objects.filter(topic__id=obj.id).order_by('-created')[:15]


class LastPostsOnForum(ForumFeed):
    title_template = 'djangobb_forum/feeds/posts_title.html'
    description_template = 'djangobb_forum/feeds/posts_description.html'

    def get_object(self, request, forum_id):
        forum = Forum.objects.get(id=forum_id)
        if not forum.category.has_access(request.user):
            raise Http404
        return forum

    def title(self, obj):
        return _('Latest posts on %s forum' % obj.name)

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return _('Latest posts on %s forum' % obj.name)

    def items(self, obj):
        return Post.objects.filter(topic__forum__id=obj.id).order_by('-created')[:15]


class LastPostsOnCategory(ForumFeed):
    title_template = 'djangobb_forum/feeds/posts_title.html'
    description_template = 'djangobb_forum/feeds/posts_description.html'
    
    def get_object(self, request, category_id):
        category = Category.objects.get(id=category_id)
        if not category.has_access(request.user):
            raise Http404
        return category

    def title(self, obj):
        return _('Latest posts on %s category' % obj.name)

    def description(self, obj):
        return _('Latest posts on %s category' % obj.name)

    def items(self, obj):
        return Post.objects.filter(topic__forum__category__id=obj.id).order_by('-created')[:15]

########NEW FILE########
__FILENAME__ = fields
"""
Details about AutoOneToOneField:
    http://softwaremaniacs.org/blog/2007/03/07/auto-one-to-one-field/
"""
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import random
from hashlib import sha1
import json

from django.db.models import OneToOneField
from django.db.models.fields.related import SingleRelatedObjectDescriptor
from django.db import models
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings


class AutoSingleRelatedObjectDescriptor(SingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        try:
            return super(AutoSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)
        except self.related.model.DoesNotExist:
            obj = self.related.model(**{self.related.field.name: instance})
            obj.save()
            return obj


class AutoOneToOneField(OneToOneField):
    """
    OneToOneField creates dependent object on first request from parent object
    if dependent oject has not created yet.
    """

    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), AutoSingleRelatedObjectDescriptor(related))
        #if not cls._meta.one_to_one_field:
        #    cls._meta.one_to_one_field = self


class ExtendedImageField(models.ImageField):
    """
    Extended ImageField that can resize image before saving it.
    """

    def __init__(self, *args, **kwargs):
        self.width = kwargs.pop('width', None)
        self.height = kwargs.pop('height', None)
        super(ExtendedImageField, self).__init__(*args, **kwargs)

    def save_form_data(self, instance, data):
        if data and self.width and self.height:
            content = self.resize_image(data.read(), width=self.width, height=self.height)
            salt = sha1(str(random.random())).hexdigest()[:5]
            fname =  sha1(salt + settings.SECRET_KEY).hexdigest() + '.png'
            data = SimpleUploadedFile(fname, content, content_type='image/png')
        super(ExtendedImageField, self).save_form_data(instance, data)

    def resize_image(self, rawdata, width, height):
        """
        Resize image to fit it into (width, height) box.
        """
        try:
            import Image
        except ImportError:
            from PIL import Image
        image = Image.open(StringIO(rawdata))
        oldw, oldh = image.size
        if oldw >= oldh:
            x = int(round((oldw - oldh) / 2.0))
            image = image.crop((x, 0, (x + oldh) - 1, oldh - 1))
        else:
            y = int(round((oldh - oldw) / 2.0))
            image = image.crop((0, y, oldw - 1, (y + oldw) - 1))
        image = image.resize((width, height), resample=Image.ANTIALIAS)


        string = StringIO()
        image.save(string, format='PNG')
        return string.getvalue()


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478
    """

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def get_prep_value(self, value):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return super(JSONField, self).get_prep_value(value)

########NEW FILE########
__FILENAME__ = forms
# coding: utf-8

import os.path
from datetime import datetime, timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.expressions import F
from django.utils.translation import ugettext_lazy as _

from djangobb_forum.models import Topic, Post, Profile, Reputation, Report, \
    Attachment, Poll, PollChoice
from djangobb_forum import settings as forum_settings
from djangobb_forum.util import convert_text_to_html, set_language


SORT_USER_BY_CHOICES = (
    ('username', _(u'Username')),
    ('registered', _(u'Registered')),
    ('num_posts', _(u'No. of posts')),
)

SORT_POST_BY_CHOICES = (
    ('0', _(u'Post time')),
    ('1', _(u'Author')),
    ('2', _(u'Subject')),
    ('3', _(u'Forum')),
)

SORT_DIR_CHOICES = (
    ('ASC', _(u'Ascending')),
    ('DESC', _(u'Descending')),
)

SHOW_AS_CHOICES = (
    ('topics', _(u'Topics')),
    ('posts', _(u'Posts')),
)

SEARCH_IN_CHOICES = (
    ('all', _(u'Message text and topic subject')),
    ('message', _(u'Message text only')),
    ('topic', _(u'Topic subject only')),
)


class AddPostForm(forms.ModelForm):
    FORM_NAME = "AddPostForm" # used in view and template submit button

    name = forms.CharField(label=_('Subject'), max_length=255,
                           widget=forms.TextInput(attrs={'size':'115'}))
    attachment = forms.FileField(label=_('Attachment'), required=False)
    subscribe = forms.BooleanField(label=_('Subscribe'), help_text=_("Subscribe this topic."), required=False)

    class Meta:
        model = Post
        fields = ['body']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.topic = kwargs.pop('topic', None)
        self.forum = kwargs.pop('forum', None)
        self.ip = kwargs.pop('ip', None)
        super(AddPostForm, self).__init__(*args, **kwargs)

        if self.topic:
            self.fields['name'].widget = forms.HiddenInput()
            self.fields['name'].required = False

        self.fields['body'].widget = forms.Textarea(attrs={'class':'markup', 'rows':'20', 'cols':'95'})

        if not forum_settings.ATTACHMENT_SUPPORT:
            self.fields['attachment'].widget = forms.HiddenInput()
            self.fields['attachment'].required = False

    def clean(self):
        '''
        checking is post subject and body contains not only space characters
        '''
        errmsg = _('Can\'t be empty nor contain only whitespace characters')
        cleaned_data = self.cleaned_data
        body = cleaned_data.get('body')
        subject = cleaned_data.get('name')
        if subject:
            if not subject.strip():
                self._errors['name'] = self.error_class([errmsg])
                del cleaned_data['name']
        if body:
            if not body.strip():
                self._errors['body'] = self.error_class([errmsg])
                del cleaned_data['body']
        return cleaned_data

    def clean_attachment(self):
        if self.cleaned_data['attachment']:
            memfile = self.cleaned_data['attachment']
            if memfile.size > forum_settings.ATTACHMENT_SIZE_LIMIT:
                raise forms.ValidationError(_('Attachment is too big'))
            return self.cleaned_data['attachment']

    def save(self):
        if self.forum:
            topic = Topic(forum=self.forum,
                          user=self.user,
                          name=self.cleaned_data['name'])
            topic.save()
        else:
            topic = self.topic

        if self.cleaned_data['subscribe']:
            # User would like to subscripe to this topic
            topic.subscribers.add(self.user)

        post = Post(topic=topic, user=self.user, user_ip=self.ip,
                    markup=self.user.forum_profile.markup,
                    body=self.cleaned_data['body'])

        post.save()
        if forum_settings.ATTACHMENT_SUPPORT:
            self.save_attachment(post, self.cleaned_data['attachment'])
        return post


    def save_attachment(self, post, memfile):
        if memfile:
            obj = Attachment(size=memfile.size, content_type=memfile.content_type,
                             name=memfile.name, post=post)
            dir = os.path.join(settings.MEDIA_ROOT, forum_settings.ATTACHMENT_UPLOAD_TO)
            fname = '%d.0' % post.id
            path = os.path.join(dir, fname)
            file(path, 'wb').write(memfile.read())
            obj.path = fname
            obj.save()


class EditPostForm(forms.ModelForm):
    name = forms.CharField(required=False, label=_('Subject'),
                           widget=forms.TextInput(attrs={'size':'115'}))

    class Meta:
        model = Post
        fields = ['body']

    def __init__(self, *args, **kwargs):
        self.topic = kwargs.pop('topic', None)
        super(EditPostForm, self).__init__(*args, **kwargs)
        self.fields['name'].initial = self.topic
        self.fields['body'].widget = forms.Textarea(attrs={'class':'markup'})

    def save(self, commit=True):
        post = super(EditPostForm, self).save(commit=False)
        post.updated = datetime.now()
        topic_name = self.cleaned_data['name']
        if topic_name:
            post.topic.name = topic_name
        if commit:
            post.topic.save()
            post.save()
        return post


class EssentialsProfileForm(forms.ModelForm):
    username = forms.CharField(label=_('Username'))
    email = forms.CharField(label=_('E-mail'))

    class Meta:
        model = Profile
        fields = ['auto_subscribe', 'time_zone', 'language']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        self.request = extra_args.pop('request', None)
        self.profile = kwargs['instance']
        super(EssentialsProfileForm, self).__init__(*args, **kwargs)
        self.fields['username'].initial = self.profile.user.username
        if not self.request.user.is_superuser:
            self.fields['username'].widget = forms.HiddenInput()
        self.fields['email'].initial = self.profile.user.email

    def save(self, commit=True):
        if self.cleaned_data:
            if self.request.user.is_superuser:
                self.profile.user.username = self.cleaned_data['username']
            self.profile.user.email = self.cleaned_data['email']
            self.profile.time_zone = self.cleaned_data['time_zone']
            self.profile.language = self.cleaned_data['language']
            self.profile.user.save()
            if commit:
                self.profile.save()
        set_language(self.request, self.profile.language)
        return self.profile


class PersonalProfileForm(forms.ModelForm):
    name = forms.CharField(label=_('Real name'), required=False)

    class Meta:
        model = Profile
        fields = ['status', 'location', 'site']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        self.profile = kwargs['instance']
        super(PersonalProfileForm, self).__init__(*args, **kwargs)
        self.fields['name'].initial = "%s %s" % (self.profile.user.first_name, self.profile.user.last_name)

    def save(self, commit=True):
        self.profile.status = self.cleaned_data['status']
        self.profile.location = self.cleaned_data['location']
        self.profile.site = self.cleaned_data['site']
        if self.cleaned_data['name']:
            cleaned_name = self.cleaned_data['name'].strip()
            if  ' ' in cleaned_name:
                self.profile.user.first_name, self.profile.user.last_name = cleaned_name.split(None, 1)
            else:
                self.profile.user.first_name = cleaned_name
                self.profile.user.last_name = ''
            self.profile.user.save()
            if commit:
                self.profile.save()
        return self.profile


class MessagingProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['jabber', 'icq', 'msn', 'aim', 'yahoo']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        super(MessagingProfileForm, self).__init__(*args, **kwargs)


class PersonalityProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['show_avatar', 'signature']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        self.profile = kwargs['instance']
        super(PersonalityProfileForm, self).__init__(*args, **kwargs)
        self.fields['signature'].widget = forms.Textarea(attrs={'class':'markup', 'rows':'10', 'cols':'75'})

    def save(self, commit=True):
        profile = super(PersonalityProfileForm, self).save(commit=False)
        profile.signature_html = convert_text_to_html(profile.signature, self.profile.markup)
        if commit:
            profile.save()
        return profile


class DisplayProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['theme', 'markup', 'show_smilies']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        super(DisplayProfileForm, self).__init__(*args, **kwargs)


class PrivacyProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['privacy_permission']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        super(PrivacyProfileForm, self).__init__(*args, **kwargs)
        self.fields['privacy_permission'].widget = forms.RadioSelect(
                                                    choices=self.fields['privacy_permission'].choices
                                                    )


class UploadAvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']

    def __init__(self, *args, **kwargs):
        extra_args = kwargs.pop('extra_args', {})
        super(UploadAvatarForm, self).__init__(*args, **kwargs)


class UserSearchForm(forms.Form):
    username = forms.CharField(required=False, label=_('Username'))
    #show_group = forms.ChoiceField(choices=SHOW_GROUP_CHOICES)
    sort_by = forms.ChoiceField(choices=SORT_USER_BY_CHOICES, label=_('Sort by'))
    sort_dir = forms.ChoiceField(choices=SORT_DIR_CHOICES, label=_('Sort order'))

    def filter(self, qs):
        if self.is_valid():
            username = self.cleaned_data['username']
            #show_group = self.cleaned_data['show_group']
            sort_by = self.cleaned_data['sort_by']
            sort_dir = self.cleaned_data['sort_dir']
            qs = qs.filter(username__contains=username, forum_profile__post_count__gte=forum_settings.POST_USER_SEARCH)
            if sort_by == 'username':
                if sort_dir == 'ASC':
                    return qs.order_by('username')
                elif sort_dir == 'DESC':
                    return qs.order_by('-username')
            elif sort_by == 'registered':
                if sort_dir == 'ASC':
                    return qs.order_by('date_joined')
                elif sort_dir == 'DESC':
                    return qs.order_by('-date_joined')
            elif sort_by == 'num_posts':
                if sort_dir == 'ASC':
                    return qs.order_by('forum_profile__post_count')
                elif sort_dir == 'DESC':
                    return qs.order_by('-forum_profile__post_count')
        else:
            return qs


class PostSearchForm(forms.Form):
    keywords = forms.CharField(required=False, label=_('Keyword search'),
                               widget=forms.TextInput(attrs={'size':'40', 'maxlength':'100'}))
    author = forms.CharField(required=False, label=_('Author search'),
                             widget=forms.TextInput(attrs={'size':'25', 'maxlength':'25'}))
    forum = forms.CharField(required=False, label=_('Forum'))
    search_in = forms.ChoiceField(choices=SEARCH_IN_CHOICES, label=_('Search in'))
    sort_by = forms.ChoiceField(choices=SORT_POST_BY_CHOICES, label=_('Sort by'))
    sort_dir = forms.ChoiceField(choices=SORT_DIR_CHOICES, initial='DESC', label=_('Sort order'))
    show_as = forms.ChoiceField(choices=SHOW_AS_CHOICES, label=_('Show results as'))



class ReputationForm(forms.ModelForm):

    class Meta:
        model = Reputation
        fields = ['reason', 'post', 'sign']

    def __init__(self, *args, **kwargs):
        self.from_user = kwargs.pop('from_user', None)
        self.to_user = kwargs.pop('to_user', None)
        self.post = kwargs.pop('post', None)
        self.sign = kwargs.pop('sign', None)
        super(ReputationForm, self).__init__(*args, **kwargs)
        self.fields['post'].widget = forms.HiddenInput()
        self.fields['sign'].widget = forms.HiddenInput()
        self.fields['reason'].widget = forms.Textarea(attrs={'class':'markup'})

    def clean_to_user(self):
        name = self.cleaned_data['to_user']
        try:
            user = User.objects.get(username=name)
        except User.DoesNotExist:
            raise forms.ValidationError(_('User with login %s does not exist') % name)
        else:
            return user

    def clean(self):
        try:
            Reputation.objects.get(from_user=self.from_user, post=self.cleaned_data['post'])
        except Reputation.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(_('You already voted for this post'))

        # check if this post really belong to `from_user`
        if not Post.objects.filter(pk=self.cleaned_data['post'].id, user=self.to_user).exists():
            raise forms.ValidationError(_('This post does\'t belong to this user'))

        return self.cleaned_data


    def save(self, commit=True):
        reputation = super(ReputationForm, self).save(commit=False)
        reputation.from_user = self.from_user
        reputation.to_user = self.to_user
        if commit:
            reputation.save()
        return reputation

class MailToForm(forms.Form):
    subject = forms.CharField(label=_('Subject'),
                              widget=forms.TextInput(attrs={'size':'75', 'maxlength':'70', 'class':'longinput'}))
    body = forms.CharField(required=False, label=_('Message'),
                               widget=forms.Textarea(attrs={'rows':'10', 'cols':'75'}))


class ReportForm(forms.ModelForm):

    class Meta:
        model = Report
        fields = ['reason', 'post']

    def __init__(self, *args, **kwargs):
        self.reported_by = kwargs.pop('reported_by', None)
        self.post = kwargs.pop('post', None)
        super(ReportForm, self).__init__(*args, **kwargs)
        self.fields['post'].widget = forms.HiddenInput()
        self.fields['post'].initial = self.post
        self.fields['reason'].widget = forms.Textarea(attrs={'rows':'10', 'cols':'75'})

    def save(self, commit=True):
        report = super(ReportForm, self).save(commit=False)
        report.created = datetime.now()
        report.reported_by = self.reported_by
        if commit:
            report.save()
        return report


class VotePollForm(forms.Form):
    """
    Dynamic form for the poll.
    """
    FORM_NAME = "VotePollForm" # used in view and template submit button

    choice = forms.MultipleChoiceField()
    def __init__(self, poll, *args, **kwargs):
        self.poll = poll
        super(VotePollForm, self).__init__(*args, **kwargs)

        choices = self.poll.choices.all().values_list("id", "choice")
        if self.poll.choice_count == 1:
            self.fields["choice"] = forms.ChoiceField(
                choices=choices, widget=forms.RadioSelect
            )
        else:
            self.fields["choice"] = forms.MultipleChoiceField(
                choices=choices, widget=forms.CheckboxSelectMultiple
            )

    def clean_choice(self):
        ids = self.cleaned_data["choice"]
        count = len(ids)
        if count > self.poll.choice_count:
            raise forms.ValidationError(
                _(u'You have selected too many choices! (Only %i allowed.)') % self.poll.choice_count
            )
        return ids


class PollForm(forms.ModelForm):
    answers = forms.CharField(min_length=2, widget=forms.Textarea,
        help_text=_("Write each answer on a new line.")
    )
    days = forms.IntegerField(required=False, min_value=1,
        help_text=_("Number of days for this poll to run. Leave empty for never ending poll.")
    )
    class Meta:
        model = Poll
        fields = ['question', 'choice_count']

    def create_poll(self):
        """
        return True if one field filled with data -> the user wants to create a poll
        """
        return any(self.data.get(key) for key in ('question', 'answers', 'days'))

    def clean_answers(self):
        # validate if there is more than whitespaces ;)
        raw_answers = self.cleaned_data["answers"]
        answers = [answer.strip() for answer in raw_answers.splitlines() if answer.strip()]
        if len(answers) == 0:
            raise forms.ValidationError(_(u"There is no valid answer!"))

        # validate length of all answers
        is_max_length = max([len(answer) for answer in answers])
        should_max_length = PollChoice._meta.get_field("choice").max_length
        if is_max_length > should_max_length:
            raise forms.ValidationError(_(u"One of this answers are too long!"))

        return answers

    def save(self, post):
        """
        Create poll and all answers in PollChoice model.
        """
        poll = super(PollForm, self).save(commit=False)
        poll.topic = post.topic
        days = self.cleaned_data["days"]
        if days:
            now = datetime.now()
            poll.deactivate_date = now + timedelta(days=days)
        poll.save()
        answers = self.cleaned_data["answers"]
        for answer in answers:
            PollChoice.objects.create(poll=poll, choice=answer)


########NEW FILE########
__FILENAME__ = djangobb_unban
from optparse import make_option
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from djangobb_forum.models import Ban


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='all', default=False, 
                    help=u'Unban all users'),
        make_option('--by-time', action='store_true', dest='by-time', default=False, 
                    help=u'Unban users by time'),
    )
    help = u'Unban users'

    def handle(self, *args, **options):
        if options['all']:
            bans = Ban.objects.all()
            user_ids = bans.values_list('user', flat=True)
            User.objects.filter(id__in=user_ids).update(is_active=True)
            bans.delete()
        elif options['by-time']:
            bans = Ban.objects.filter(ban_end__lte=datetime.now())
            user_ids = bans.values_list('user', flat=True)
            User.objects.filter(id__in=user_ids).update(is_active=True)
            bans.delete()
        else:
            raise CommandError('Invalid options')

########NEW FILE########
__FILENAME__ = middleware
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import translation
from django.conf import settings as global_settings

from djangobb_forum import settings as forum_settings

class LastLoginMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            cache.set('djangobb_user%d' % request.user.id, True, forum_settings.USER_ONLINE_TIMEOUT)

class ForumMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            profile = request.user.forum_profile
            language = translation.get_language_from_request(request)

            if not profile.language:
                profile.language = language
                profile.save()

            if profile.language and profile.language != language:
                request.session['django_language'] = profile.language
                translation.activate(profile.language)
                request.LANGUAGE_CODE = translation.get_language()

class UsersOnline(object):
    def process_request(self, request):
        now = datetime.now()
        delta = now - timedelta(seconds=forum_settings.USER_ONLINE_TIMEOUT)
        users_online = cache.get('djangobb_users_online', {})
        guests_online = cache.get('djangobb_guests_online', {})

        if request.user.is_authenticated():
            users_online[request.user.id] = now
        else:
            guest_sid = request.COOKIES.get(global_settings.SESSION_COOKIE_NAME, '')
            guests_online[guest_sid] = now

        for user_id in users_online.keys():
            if users_online[user_id] < delta:
                del users_online[user_id]

        for guest_id in guests_online.keys():
            if guests_online[guest_id] < delta:
                del guests_online[guest_id]

        cache.set('djangobb_users_online', users_online, 60*60*24)
        cache.set('djangobb_guests_online', guests_online, 60*60*24)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Category'
        db.create_table('djangobb_forum_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('position', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Category'])

        # Adding M2M table for field groups on 'Category'
        db.create_table('djangobb_forum_category_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm['djangobb_forum.category'], null=False)),
            ('group', models.ForeignKey(orm['auth.group'], null=False))
        ))
        db.create_unique('djangobb_forum_category_groups', ['category_id', 'group_id'])

        # Adding model 'Forum'
        db.create_table('djangobb_forum_forum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='forums', to=orm['djangobb_forum.Category'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('position', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('post_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('topic_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('last_post', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='last_forum_post', null=True, to=orm['djangobb_forum.Post'])),
        ))
        db.send_create_signal('djangobb_forum', ['Forum'])

        # Adding M2M table for field moderators on 'Forum'
        db.create_table('djangobb_forum_forum_moderators', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('forum', models.ForeignKey(orm['djangobb_forum.forum'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('djangobb_forum_forum_moderators', ['forum_id', 'user_id'])

        # Adding model 'Topic'
        db.create_table('djangobb_forum_topic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('forum', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics', to=orm['djangobb_forum.Forum'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('views', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('sticky', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('closed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('post_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('last_post', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='last_topic_post', null=True, to=orm['djangobb_forum.Post'])),
        ))
        db.send_create_signal('djangobb_forum', ['Topic'])

        # Adding M2M table for field subscribers on 'Topic'
        db.create_table('djangobb_forum_topic_subscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('topic', models.ForeignKey(orm['djangobb_forum.topic'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('djangobb_forum_topic_subscribers', ['topic_id', 'user_id'])

        # Adding model 'Post'
        db.create_table('djangobb_forum_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posts', to=orm['djangobb_forum.Topic'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posts', to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('updated_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('markup', self.gf('django.db.models.fields.CharField')(default='bbcode', max_length=15)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('body_html', self.gf('django.db.models.fields.TextField')()),
            ('user_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Post'])

        # Adding model 'Reputation'
        db.create_table('djangobb_forum_reputation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('from_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reputations_from', to=orm['auth.User'])),
            ('to_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reputations_to', to=orm['auth.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name='post', to=orm['djangobb_forum.Post'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('sign', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('reason', self.gf('django.db.models.fields.TextField')(max_length=1000)),
        ))
        db.send_create_signal('djangobb_forum', ['Reputation'])

        # Adding unique constraint on 'Reputation', fields ['from_user', 'post']
        db.create_unique('djangobb_forum_reputation', ['from_user_id', 'post_id'])

        # Adding model 'Profile'
        db.create_table('djangobb_forum_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('djangobb_forum.fields.AutoOneToOneField')(related_name='forum_profile', unique=True, to=orm['auth.User'])),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('site', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('jabber', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('icq', self.gf('django.db.models.fields.CharField')(max_length=12, blank=True)),
            ('msn', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('aim', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('yahoo', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('signature', self.gf('django.db.models.fields.TextField')(default='', max_length=1024, blank=True)),
            ('time_zone', self.gf('django.db.models.fields.FloatField')(default=3.0)),
            ('language', self.gf('django.db.models.fields.CharField')(default='', max_length=5)),
            ('avatar', self.gf('djangobb_forum.fields.ExtendedImageField')(default='', max_length=100, blank=True)),
            ('theme', self.gf('django.db.models.fields.CharField')(default='default', max_length=80)),
            ('show_avatar', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('show_signatures', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('privacy_permission', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('markup', self.gf('django.db.models.fields.CharField')(default='bbcode', max_length=15)),
            ('post_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Profile'])

        # Adding model 'PostTracking'
        db.create_table('djangobb_forum_posttracking', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('djangobb_forum.fields.AutoOneToOneField')(to=orm['auth.User'], unique=True)),
            ('topics', self.gf('djangobb_forum.fields.JSONField')(null=True)),
            ('last_read', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('djangobb_forum', ['PostTracking'])

        # Adding model 'Report'
        db.create_table('djangobb_forum_report', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('reported_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reported_by', to=orm['auth.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangobb_forum.Post'])),
            ('zapped', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('zapped_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='zapped_by', null=True, to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(blank=True)),
            ('reason', self.gf('django.db.models.fields.TextField')(default='', max_length='1000', blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Report'])

        # Adding model 'Ban'
        db.create_table('djangobb_forum_ban', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='ban_users', unique=True, to=orm['auth.User'])),
            ('ban_start', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('ban_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('reason', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('djangobb_forum', ['Ban'])

        # Adding model 'Attachment'
        db.create_table('djangobb_forum_attachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['djangobb_forum.Post'])),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('content_type', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('hash', self.gf('django.db.models.fields.CharField')(default='', max_length=40, db_index=True, blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Attachment'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Reputation', fields ['from_user', 'post']
        db.delete_unique('djangobb_forum_reputation', ['from_user_id', 'post_id'])

        # Deleting model 'Category'
        db.delete_table('djangobb_forum_category')

        # Removing M2M table for field groups on 'Category'
        db.delete_table('djangobb_forum_category_groups')

        # Deleting model 'Forum'
        db.delete_table('djangobb_forum_forum')

        # Removing M2M table for field moderators on 'Forum'
        db.delete_table('djangobb_forum_forum_moderators')

        # Deleting model 'Topic'
        db.delete_table('djangobb_forum_topic')

        # Removing M2M table for field subscribers on 'Topic'
        db.delete_table('djangobb_forum_topic_subscribers')

        # Deleting model 'Post'
        db.delete_table('djangobb_forum_post')

        # Deleting model 'Reputation'
        db.delete_table('djangobb_forum_reputation')

        # Deleting model 'Profile'
        db.delete_table('djangobb_forum_profile')

        # Deleting model 'PostTracking'
        db.delete_table('djangobb_forum_posttracking')

        # Deleting model 'Report'
        db.delete_table('djangobb_forum_report')

        # Deleting model 'Ban'
        db.delete_table('djangobb_forum_ban')

        # Deleting model 'Attachment'
        db.delete_table('djangobb_forum_attachment')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_profile_show_smilies
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Profile.show_smilies'
        db.add_column('djangobb_forum_profile', 'show_smilies', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Profile.show_smilies'
        db.delete_column('djangobb_forum_profile', 'show_smilies')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_profile_signature_html
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Profile.signature_html'
        db.add_column('djangobb_forum_profile', 'signature_html', self.gf('django.db.models.fields.TextField')(default='', max_length=1024, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Profile.signature_html'
        db.delete_column('djangobb_forum_profile', 'signature_html')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'signature_html': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_profile_auto_subscribe
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Profile.auto_subscribe'
        db.add_column('djangobb_forum_profile', 'auto_subscribe',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Profile.auto_subscribe'
        db.delete_column('djangobb_forum_profile', 'auto_subscribe')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'auto_subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'signature_html': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']
########NEW FILE########
__FILENAME__ = 0005_auto__add_pollchoice__add_poll
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PollChoice'
        db.create_table('djangobb_forum_pollchoice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='choices', to=orm['djangobb_forum.Poll'])),
            ('choice', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('votes', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('djangobb_forum', ['PollChoice'])

        # Adding model 'Poll'
        db.create_table('djangobb_forum_poll', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangobb_forum.Topic'])),
            ('question', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('choice_count', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('deactivate_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('djangobb_forum', ['Poll'])

        # Adding M2M table for field users on 'Poll'
        db.create_table('djangobb_forum_poll_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('poll', models.ForeignKey(orm['djangobb_forum.poll'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('djangobb_forum_poll_users', ['poll_id', 'user_id'])


    def backwards(self, orm):
        # Deleting model 'PollChoice'
        db.delete_table('djangobb_forum_pollchoice')

        # Deleting model 'Poll'
        db.delete_table('djangobb_forum_poll')

        # Removing M2M table for field users on 'Poll'
        db.delete_table('djangobb_forum_poll_users')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.poll': {
            'Meta': {'object_name': 'Poll'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'choice_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'deactivate_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Topic']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.pollchoice': {
            'Meta': {'object_name': 'PollChoice'},
            'choice': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'choices'", 'to': "orm['djangobb_forum.Poll']"}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'auto_subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'signature_html': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_forum_forum_logo
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Forum.forum_logo'
        db.add_column('djangobb_forum_forum', 'forum_logo',
                      self.gf('djangobb_forum.fields.ExtendedImageField')(default='', max_length=100, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Forum.forum_logo'
        db.delete_column('djangobb_forum_forum', 'forum_logo')


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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'forum_logo': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.poll': {
            'Meta': {'object_name': 'Poll'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'choice_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'deactivate_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Topic']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.pollchoice': {
            'Meta': {'object_name': 'PollChoice'},
            'choice': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'choices'", 'to': "orm['djangobb_forum.Poll']"}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'auto_subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'signature_html': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']
########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_post_user_ip
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Post.user_ip'
        db.alter_column('djangobb_forum_post', 'user_ip', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, null=True))

    def backwards(self, orm):

        # Changing field 'Post.user_ip'
        db.alter_column('djangobb_forum_post', 'user_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True))

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
        'djangobb_forum.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['djangobb_forum.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'djangobb_forum.ban': {
            'Meta': {'object_name': 'Ban'},
            'ban_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ban_start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ban_users'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.category': {
            'Meta': {'ordering': "['position']", 'object_name': 'Category'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'djangobb_forum.forum': {
            'Meta': {'ordering': "['position']", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'forums'", 'to': "orm['djangobb_forum.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'forum_logo': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_forum_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'topic_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'djangobb_forum.poll': {
            'Meta': {'object_name': 'Poll'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'choice_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'deactivate_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Topic']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.pollchoice': {
            'Meta': {'object_name': 'PollChoice'},
            'choice': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'choices'", 'to': "orm['djangobb_forum.Poll']"}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'djangobb_forum.post': {
            'Meta': {'ordering': "['created']", 'object_name': 'Post'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'body_html': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['djangobb_forum.Topic']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['auth.User']"}),
            'user_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'})
        },
        'djangobb_forum.posttracking': {
            'Meta': {'object_name': 'PostTracking'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'topics': ('djangobb_forum.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'djangobb_forum.profile': {
            'Meta': {'object_name': 'Profile'},
            'aim': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'auto_subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'avatar': ('djangobb_forum.fields.ExtendedImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'icq': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'markup': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '15'}),
            'msn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'privacy_permission': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'show_avatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_signatures': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_smilies': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signature': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'signature_html': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'site': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '80'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '3.0'}),
            'user': ('djangobb_forum.fields.AutoOneToOneField', [], {'related_name': "'forum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'yahoo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'djangobb_forum.report': {
            'Meta': {'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': "'1000'", 'blank': 'True'}),
            'reported_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reported_by'", 'to': "orm['auth.User']"}),
            'zapped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'zapped_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'zapped_by'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'djangobb_forum.reputation': {
            'Meta': {'unique_together': "(('from_user', 'post'),)", 'object_name': 'Reputation'},
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_from'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post'", 'to': "orm['djangobb_forum.Post']"}),
            'reason': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'sign': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reputations_to'", 'to': "orm['auth.User']"})
        },
        'djangobb_forum.topic': {
            'Meta': {'ordering': "['-updated']", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['djangobb_forum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'last_topic_post'", 'null': 'True', 'to': "orm['djangobb_forum.Post']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'post_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'views': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        }
    }

    complete_apps = ['djangobb_forum']
########NEW FILE########
__FILENAME__ = models
# coding: utf-8

from datetime import datetime
from hashlib import sha1
import os

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import aggregates
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from djangobb_forum.fields import AutoOneToOneField, ExtendedImageField, JSONField
from djangobb_forum.util import smiles, convert_text_to_html
from djangobb_forum import settings as forum_settings

if 'south' in settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ['^djangobb_forum\.fields\.AutoOneToOneField',
                                 '^djangobb_forum\.fields\.JSONField',
                                 '^djangobb_forum\.fields\.ExtendedImageField'])

TZ_CHOICES = [(float(x[0]), x[1]) for x in (
    (-12, '-12'), (-11, '-11'), (-10, '-10'), (-9.5, '-09.5'), (-9, '-09'),
    (-8.5, '-08.5'), (-8, '-08 PST'), (-7, '-07 MST'), (-6, '-06 CST'),
    (-5, '-05 EST'), (-4, '-04 AST'), (-3.5, '-03.5'), (-3, '-03 ADT'),
    (-2, '-02'), (-1, '-01'), (0, '00 GMT'), (1, '+01 CET'), (2, '+02'),
    (3, '+03'), (3.5, '+03.5'), (4, '+04'), (4.5, '+04.5'), (5, '+05'),
    (5.5, '+05.5'), (6, '+06'), (6.5, '+06.5'), (7, '+07'), (8, '+08'),
    (9, '+09'), (9.5, '+09.5'), (10, '+10'), (10.5, '+10.5'), (11, '+11'),
    (11.5, '+11.5'), (12, '+12'), (13, '+13'), (14, '+14'),
)]

SIGN_CHOICES = (
    (1, 'PLUS'),
    (-1, 'MINUS'),
)

PRIVACY_CHOICES = (
    (0, _(u'Display your e-mail address.')),
    (1, _(u'Hide your e-mail address but allow form e-mail.')),
    (2, _(u'Hide your e-mail address and disallow form e-mail.')),
)

MARKUP_CHOICES = [('bbcode', 'bbcode')]
try:
    import markdown
    MARKUP_CHOICES.append(("markdown", "markdown"))
except ImportError:
    pass

path = os.path.join(settings.STATIC_ROOT, 'djangobb_forum', 'themes')
if os.path.exists(path):
    # fix for collectstatic
    THEME_CHOICES = [(theme, theme) for theme in os.listdir(path)
                     if os.path.isdir(os.path.join(path, theme))]
else:
    THEME_CHOICES = []

class Category(models.Model):
    name = models.CharField(_('Name'), max_length=80)
    groups = models.ManyToManyField(Group, blank=True, null=True, verbose_name=_('Groups'), help_text=_('Only users from these groups can see this category'))
    position = models.IntegerField(_('Position'), blank=True, default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __unicode__(self):
        return self.name

    def forum_count(self):
        return self.forums.all().count()

    @property
    def topics(self):
        return Topic.objects.filter(forum__category__id=self.id).select_related()

    @property
    def posts(self):
        return Post.objects.filter(topic__forum__category__id=self.id).select_related()

    def has_access(self, user):
        if user.is_superuser:
            return True
        if self.groups.exists():
            if user.is_authenticated():
                if not self.groups.filter(user__pk=user.id).exists():
                    return False
            else:
                return False
        return True


class Forum(models.Model):
    category = models.ForeignKey(Category, related_name='forums', verbose_name=_('Category'))
    name = models.CharField(_('Name'), max_length=80)
    position = models.IntegerField(_('Position'), blank=True, default=0)
    description = models.TextField(_('Description'), blank=True, default='')
    moderators = models.ManyToManyField(User, blank=True, null=True, verbose_name=_('Moderators'))
    updated = models.DateTimeField(_('Updated'), auto_now=True)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)
    topic_count = models.IntegerField(_('Topic count'), blank=True, default=0)
    last_post = models.ForeignKey('Post', related_name='last_forum_post', blank=True, null=True)
    forum_logo = ExtendedImageField(_('Forum Logo'), blank=True, default='',
                                    upload_to=forum_settings.FORUM_LOGO_UPLOAD_TO,
                                    width=forum_settings.FORUM_LOGO_WIDTH,
                                    height=forum_settings.FORUM_LOGO_HEIGHT)

    class Meta:
        ordering = ['position']
        verbose_name = _('Forum')
        verbose_name_plural = _('Forums')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('djangobb:forum', [self.id])

    @property
    def posts(self):
        return Post.objects.filter(topic__forum__id=self.id).select_related()


class Topic(models.Model):
    forum = models.ForeignKey(Forum, related_name='topics', verbose_name=_('Forum'))
    name = models.CharField(_('Subject'), max_length=255)
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), null=True)
    user = models.ForeignKey(User, verbose_name=_('User'))
    views = models.IntegerField(_('Views count'), blank=True, default=0)
    sticky = models.BooleanField(_('Sticky'), blank=True, default=False)
    closed = models.BooleanField(_('Closed'), blank=True, default=False)
    subscribers = models.ManyToManyField(User, related_name='subscriptions', verbose_name=_('Subscribers'), blank=True)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)
    last_post = models.ForeignKey('Post', related_name='last_topic_post', blank=True, null=True)

    class Meta:
        ordering = ['-updated']
        get_latest_by = 'updated'
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')

    def __unicode__(self):
        return self.name

    def delete(self, *args, **kwargs):
        try:
            last_post = self.posts.latest()
            last_post.last_forum_post.clear()
        except Post.DoesNotExist:
            pass
        else:
            last_post.last_forum_post.clear()
        forum = self.forum
        super(Topic, self).delete(*args, **kwargs)
        try:
            forum.last_post = Topic.objects.filter(forum__id=forum.id).latest().last_post
        except Topic.DoesNotExist:
            forum.last_post = None
        forum.topic_count = Topic.objects.filter(forum__id=forum.id).count()
        forum.post_count = Post.objects.filter(topic__forum__id=forum.id).count()
        forum.save()

    @property
    def head(self):
        try:
            return self.posts.select_related().order_by('created')[0]
        except IndexError:
            return None

    @property
    def reply_count(self):
        return self.post_count - 1

    @models.permalink
    def get_absolute_url(self):
        return ('djangobb:topic', [self.id])

    def update_read(self, user):
        tracking = user.posttracking
        #if last_read > last_read - don't check topics
        if tracking.last_read and (tracking.last_read > self.last_post.created):
            return
        if isinstance(tracking.topics, dict):
            #clear topics if len > 5Kb and set last_read to current time
            if len(tracking.topics) > 5120:
                tracking.topics = None
                tracking.last_read = datetime.now()
                tracking.save()
            #update topics if exist new post or does't exist in dict
            if self.last_post_id > tracking.topics.get(str(self.id), 0):
                tracking.topics[str(self.id)] = self.last_post_id
                tracking.save()
        else:
            #initialize topic tracking dict
            tracking.topics = {self.id: self.last_post_id}
            tracking.save()


class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name='posts', verbose_name=_('Topic'))
    user = models.ForeignKey(User, related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, null=True)
    updated_by = models.ForeignKey(User, verbose_name=_('Updated by'), blank=True, null=True)
    markup = models.CharField(_('Markup'), max_length=15, default=forum_settings.DEFAULT_MARKUP, choices=MARKUP_CHOICES)
    body = models.TextField(_('Message'))
    body_html = models.TextField(_('HTML version'))
    user_ip = models.GenericIPAddressField(_('User IP'), blank=True, null=True)


    class Meta:
        ordering = ['created']
        get_latest_by = 'created'
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')

    def save(self, *args, **kwargs):
        self.body_html = convert_text_to_html(self.body, self.markup)
        if forum_settings.SMILES_SUPPORT and self.user.forum_profile.show_smilies:
            self.body_html = smiles(self.body_html)
        super(Post, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        self_id = self.id
        head_post_id = self.topic.posts.order_by('created')[0].id
        forum = self.topic.forum
        topic = self.topic
        profile = self.user.forum_profile
        self.last_topic_post.clear()
        self.last_forum_post.clear()
        super(Post, self).delete(*args, **kwargs)
        #if post was last in topic - remove topic
        if self_id == head_post_id:
            topic.delete()
        else:
            try:
                topic.last_post = Post.objects.filter(topic__id=topic.id).latest()
            except Post.DoesNotExist:
                topic.last_post = None
            topic.post_count = Post.objects.filter(topic__id=topic.id).count()
            topic.save()
        try:
            forum.last_post = Post.objects.filter(topic__forum__id=forum.id).latest()
        except Post.DoesNotExist:
            forum.last_post = None
        #TODO: for speedup - save/update only changed fields
        forum.post_count = Post.objects.filter(topic__forum__id=forum.id).count()
        forum.topic_count = Topic.objects.filter(forum__id=forum.id).count()
        forum.save()
        profile.post_count = Post.objects.filter(user__id=self.user_id).count()
        profile.save()

    @models.permalink
    def get_absolute_url(self):
        return ('djangobb:post', [self.id])

    def summary(self):
        LIMIT = 50
        tail = len(self.body) > LIMIT and '...' or ''
        return self.body[:LIMIT] + tail

    __unicode__ = summary


class Reputation(models.Model):
    from_user = models.ForeignKey(User, related_name='reputations_from', verbose_name=_('From'))
    to_user = models.ForeignKey(User, related_name='reputations_to', verbose_name=_('To'))
    post = models.ForeignKey(Post, related_name='post', verbose_name=_('Post'))
    time = models.DateTimeField(_('Time'), auto_now_add=True)
    sign = models.IntegerField(_('Sign'), choices=SIGN_CHOICES, default=0)
    reason = models.TextField(_('Reason'), max_length=1000)

    class Meta:
        verbose_name = _('Reputation')
        verbose_name_plural = _('Reputations')
        unique_together = (('from_user', 'post'),)

    def __unicode__(self):
        return u'T[%d], FU[%d], TU[%d]: %s' % (self.post.id, self.from_user.id, self.to_user.id, unicode(self.time))


class ProfileManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        qs = super(ProfileManager, self).get_query_set()
        if forum_settings.REPUTATION_SUPPORT:
            qs = qs.extra(select={
                'reply_total': 'SELECT SUM(sign) FROM djangobb_forum_reputation WHERE to_user_id = djangobb_forum_profile.user_id GROUP BY to_user_id',
                'reply_count_minus': "SELECT SUM(sign) FROM djangobb_forum_reputation WHERE to_user_id = djangobb_forum_profile.user_id AND sign = '-1' GROUP BY to_user_id",
                'reply_count_plus': "SELECT SUM(sign) FROM djangobb_forum_reputation WHERE to_user_id = djangobb_forum_profile.user_id AND sign = '1' GROUP BY to_user_id",
                })
        return qs

class Profile(models.Model):
    user = AutoOneToOneField(User, related_name='forum_profile', verbose_name=_('User'))
    status = models.CharField(_('Status'), max_length=30, blank=True)
    site = models.URLField(_('Site'), blank=True)
    jabber = models.CharField(_('Jabber'), max_length=80, blank=True)
    icq = models.CharField(_('ICQ'), max_length=12, blank=True)
    msn = models.CharField(_('MSN'), max_length=80, blank=True)
    aim = models.CharField(_('AIM'), max_length=80, blank=True)
    yahoo = models.CharField(_('Yahoo'), max_length=80, blank=True)
    location = models.CharField(_('Location'), max_length=30, blank=True)
    signature = models.TextField(_('Signature'), blank=True, default='', max_length=forum_settings.SIGNATURE_MAX_LENGTH)
    signature_html = models.TextField(_('Signature'), blank=True, default='', max_length=forum_settings.SIGNATURE_MAX_LENGTH)
    time_zone = models.FloatField(_('Time zone'), choices=TZ_CHOICES, default=float(forum_settings.DEFAULT_TIME_ZONE))
    language = models.CharField(_('Language'), max_length=5, default='', choices=settings.LANGUAGES)
    avatar = ExtendedImageField(_('Avatar'), blank=True, default='', upload_to=forum_settings.AVATARS_UPLOAD_TO, width=forum_settings.AVATAR_WIDTH, height=forum_settings.AVATAR_HEIGHT)
    theme = models.CharField(_('Theme'), choices=THEME_CHOICES, max_length=80, default='default')
    show_avatar = models.BooleanField(_('Show avatar'), blank=True, default=True)
    show_signatures = models.BooleanField(_('Show signatures'), blank=True, default=True)
    show_smilies = models.BooleanField(_('Show smilies'), blank=True, default=True)
    privacy_permission = models.IntegerField(_('Privacy permission'), choices=PRIVACY_CHOICES, default=1)
    auto_subscribe = models.BooleanField(_('Auto subscribe'), help_text=_("Auto subscribe all topics you have created or reply."), blank=True, default=False)
    markup = models.CharField(_('Default markup'), max_length=15, default=forum_settings.DEFAULT_MARKUP, choices=MARKUP_CHOICES)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)

    objects = ProfileManager()

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def last_post(self):
        posts = Post.objects.filter(user__id=self.user_id).order_by('-created')
        if posts:
            return posts[0].created
        else:
            return  None

class PostTracking(models.Model):
    """
    Model for tracking read/unread posts.
    In topics stored ids of topics and last_posts as dict.
    """

    user = AutoOneToOneField(User)
    topics = JSONField(null=True, blank=True)
    last_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Post tracking')
        verbose_name_plural = _('Post tracking')

    def __unicode__(self):
        return self.user.username


class Report(models.Model):
    reported_by = models.ForeignKey(User, related_name='reported_by', verbose_name=_('Reported by'))
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    zapped = models.BooleanField(_('Zapped'), blank=True, default=False)
    zapped_by = models.ForeignKey(User, related_name='zapped_by', blank=True, null=True, verbose_name=_('Zapped by'))
    created = models.DateTimeField(_('Created'), blank=True)
    reason = models.TextField(_('Reason'), blank=True, default='', max_length='1000')

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')

    def __unicode__(self):
        return u'%s %s' % (self.reported_by , self.zapped)

class Ban(models.Model):
    user = models.OneToOneField(User, verbose_name=_('Banned user'), related_name='ban_users')
    ban_start = models.DateTimeField(_('Ban start'), default=datetime.now)
    ban_end = models.DateTimeField(_('Ban end'), blank=True, null=True)
    reason = models.TextField(_('Reason'))

    class Meta:
        verbose_name = _('Ban')
        verbose_name_plural = _('Bans')

    def __unicode__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        self.user.is_active = False
        self.user.save()
        super(Ban, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.user.is_active = True
        self.user.save()
        super(Ban, self).delete(*args, **kwargs)


class Attachment(models.Model):
    post = models.ForeignKey(Post, verbose_name=_('Post'), related_name='attachments')
    size = models.IntegerField(_('Size'))
    content_type = models.CharField(_('Content type'), max_length=255)
    path = models.CharField(_('Path'), max_length=255)
    name = models.TextField(_('Name'))
    hash = models.CharField(_('Hash'), max_length=40, blank=True, default='', db_index=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Attachment, self).save(*args, **kwargs)
        if not self.hash:
            self.hash = sha1(str(self.id) + settings.SECRET_KEY).hexdigest()
        super(Attachment, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('djangobb:forum_attachment', [self.hash])

    def get_absolute_path(self):
        return os.path.join(settings.MEDIA_ROOT, forum_settings.ATTACHMENT_UPLOAD_TO,
                            self.path)


#------------------------------------------------------------------------------


class Poll(models.Model):
    topic = models.ForeignKey(Topic)
    question = models.CharField(max_length=200)
    choice_count = models.PositiveSmallIntegerField(default=1,
        help_text=_("How many choices are allowed simultaneously."),
    )
    active = models.BooleanField(default=True,
        help_text=_("Can users vote to this poll or just see the result?"),
    )
    deactivate_date = models.DateTimeField(null=True, blank=True,
        help_text=_("Point of time after this poll would be automatic deactivated"),
    )
    users = models.ManyToManyField(User, blank=True, null=True,
        help_text=_("Users who has voted this poll."),
    )
    def auto_deactivate(self):
        if self.active and self.deactivate_date:
            now = datetime.now()
            if now > self.deactivate_date:
                self.active = False
                self.save()

    def __unicode__(self):
        return self.question


class PollChoice(models.Model):
    poll = models.ForeignKey(Poll, related_name="choices")
    choice = models.CharField(max_length=200)
    votes = models.IntegerField(default=0, editable=False)

    def percent(self):
        if not self.votes:
            return 0.0
        result = PollChoice.objects.filter(poll=self.poll).aggregate(aggregates.Sum("votes"))
        votes_sum = result["votes__sum"]
        return float(self.votes) / votes_sum * 100

    def __unicode__(self):
        return self.choice


#------------------------------------------------------------------------------


from .signals import post_saved, topic_saved

post_save.connect(post_saved, sender=Post, dispatch_uid='djangobb_post_save')
post_save.connect(topic_saved, sender=Topic, dispatch_uid='djangobb_topic_save')

########NEW FILE########
__FILENAME__ = search_indexes
from haystack.indexes import *
from haystack import site

import djangobb_forum.models as models

class PostIndex(RealTimeSearchIndex):
    text = CharField(document=True, use_template=True)
    author = CharField(model_attr='user')
    created = DateTimeField(model_attr='created')
    topic = CharField(model_attr='topic')
    category = CharField(model_attr='topic__forum__category__name')
    forum = IntegerField(model_attr='topic__forum__pk')

site.register(models.Post, PostIndex)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from django.conf import settings

def get(key, default):
    return getattr(settings, key, default)

# FORUM Settings
FORUM_BASE_TITLE = get('DJANGOBB_FORUM_BASE_TITLE', 'Django Bulletin Board')
FORUM_META_DESCRIPTION = get('DJANGOBB_FORUM_META_DESCRIPTION', '')
FORUM_META_KEYWORDS = get('DJANGOBB_FORUM_META_KEYWORDS', '')
TOPIC_PAGE_SIZE = get('DJANGOBB_TOPIC_PAGE_SIZE', 10)
FORUM_PAGE_SIZE = get('DJANGOBB_FORUM_PAGE_SIZE', 20)
SEARCH_PAGE_SIZE = get('DJANGOBB_SEARCH_PAGE_SIZE', 20)
USERS_PAGE_SIZE = get('DJANGOBB_USERS_PAGE_SIZE', 20)
AVATARS_UPLOAD_TO = get('DJANGOBB_AVATARS_UPLOAD_TO', 'djangobb_forum/avatars')
AVATAR_WIDTH = get('DJANGOBB_AVATAR_WIDTH', 60)
AVATAR_HEIGHT = get('DJANGOBB_AVATAR_HEIGHT', 60)
FORUM_LOGO_UPLOAD_TO = get('DJANGOBB_FORUM_LOGO_UPLOAD_TO', 'djangobb_forum/forum_logo')
FORUM_LOGO_WIDTH = get('DJANGOBB_FORUM_LOGO_WIDTH', 16)
FORUM_LOGO_HEIGHT = get('DJANGOBB_FORUM_LOGO_HEIGHT', 16)
DEFAULT_TIME_ZONE = get('DJANGOBB_DEFAULT_TIME_ZONE', 3)
SIGNATURE_MAX_LENGTH = get('DJANGOBB_SIGNATURE_MAX_LENGTH', 1024)
SIGNATURE_MAX_LINES = get('DJANGOBB_SIGNATURE_MAX_LINES', 3)
HEADER = get('DJANGOBB_HEADER', 'DjangoBB')
TAGLINE = get('DJANGOBB_TAGLINE', 'Django based forum engine')
DEFAULT_MARKUP = get('DJANGOBB_DEFAULT_MARKUP', 'bbcode')
NOTICE = get('DJANGOBB_NOTICE', '')
USER_ONLINE_TIMEOUT = get('DJANGOBB_USER_ONLINE_TIMEOUT', 15 * 60)
EMAIL_DEBUG = get('DJANGOBB_FORUM_EMAIL_DEBUG', False)
POST_USER_SEARCH = get('DJANGOBB_POST_USER_SEARCH', 1)

# GRAVATAR Extension
GRAVATAR_SUPPORT = get('DJANGOBB_GRAVATAR_SUPPORT', True)
GRAVATAR_DEFAULT = get('DJANGOBB_GRAVATAR_DEFAULT', 'identicon')

# LOFI Extension
LOFI_SUPPORT = get('DJANGOBB_LOFI_SUPPORT', True)

# PM Extension
if 'django_messages' not in settings.INSTALLED_APPS:
    PM_SUPPORT = False
else:
    PM_SUPPORT = get('DJANGOBB_PM_SUPPORT', True)

# AUTHORITY Extension
AUTHORITY_SUPPORT = get('DJANGOBB_AUTHORITY_SUPPORT', True)
AUTHORITY_STEP_0 = get('DJANGOBB_AUTHORITY_STEP_0', 0)
AUTHORITY_STEP_1 = get('DJANGOBB_AUTHORITY_STEP_1', 10)
AUTHORITY_STEP_2 = get('DJANGOBB_AUTHORITY_STEP_2', 25)
AUTHORITY_STEP_3 = get('DJANGOBB_AUTHORITY_STEP_3', 50)
AUTHORITY_STEP_4 = get('DJANGOBB_AUTHORITY_STEP_4', 75)
AUTHORITY_STEP_5 = get('DJANGOBB_AUTHORITY_STEP_5', 100)
AUTHORITY_STEP_6 = get('DJANGOBB_AUTHORITY_STEP_6', 150)
AUTHORITY_STEP_7 = get('DJANGOBB_AUTHORITY_STEP_7', 200)
AUTHORITY_STEP_8 = get('DJANGOBB_AUTHORITY_STEP_8', 300)
AUTHORITY_STEP_9 = get('DJANGOBB_AUTHORITY_STEP_9', 500)
AUTHORITY_STEP_10 = get('DJANGOBB_AUTHORITY_STEP_10', 1000)

# REPUTATION Extension
REPUTATION_SUPPORT = get('DJANGOBB_REPUTATION_SUPPORT', True)

# ATTACHMENT Extension
ATTACHMENT_SUPPORT = get('DJANGOBB_ATTACHMENT_SUPPORT', True)
ATTACHMENT_UPLOAD_TO = get('DJANGOBB_ATTACHMENT_UPLOAD_TO', 'djangobb_forum/attachments')
ATTACHMENT_SIZE_LIMIT = get('DJANGOBB_ATTACHMENT_SIZE_LIMIT', 1024 * 1024)

# SMILE Extension
SMILES_SUPPORT = get('DJANGOBB_SMILES_SUPPORT', True)
EMOTION_SMILE = get('DJANGOBB_EMOTION_SMILE', '<img src="%sdjangobb_forum/img/smilies/smile.png" />' % settings.STATIC_URL)
EMOTION_NEUTRAL = get('DJANGOBB_EMOTION_NEUTRAL', '<img src="%sdjangobb_forum/img/smilies/neutral.png" />' % settings.STATIC_URL)
EMOTION_SAD = get('DJANGOBB_EMOTION_SAD', '<img src="%sdjangobb_forum/img/smilies/sad.png" />' % settings.STATIC_URL)
EMOTION_BIG_SMILE = get('DJANGOBB_EMOTION_BIG_SMILE', '<img src="%sdjangobb_forum/img/smilies/big_smile.png" />' % settings.STATIC_URL)
EMOTION_YIKES = get('DJANGOBB_EMOTION_YIKES', '<img src="%sdjangobb_forum/img/smilies/yikes.png" />' % settings.STATIC_URL)
EMOTION_WINK = get('DJANGOBB_EMOTION_WINK', '<img src="%sdjangobb_forum/img/smilies/wink.png" />' % settings.STATIC_URL)
EMOTION_HMM = get('DJANGOBB_EMOTION_HMM', '<img src="%sdjangobb_forum/img/smilies/hmm.png" />' % settings.STATIC_URL)
EMOTION_TONGUE = get('DJANGOBB_EMOTION_TONGUE', '<img src="%sdjangobb_forum/img/smilies/tongue.png" />' % settings.STATIC_URL)
EMOTION_LOL = get('DJANGOBB_EMOTION_LOL', '<img src="%sdjangobb_forum/img/smilies/lol.png" />' % settings.STATIC_URL)
EMOTION_MAD = get('DJANGOBB_EMOTION_MAD', '<img src="%sdjangobb_forum/img/smilies/mad.png" />' % settings.STATIC_URL)
EMOTION_ROLL = get('DJANGOBB_EMOTION_ROLL', '<img src="%sdjangobb_forum/img/smilies/roll.png" />' % settings.STATIC_URL)
EMOTION_COOL = get('DJANGOBB_EMOTION_COOL', '<img src="%sdjangobb_forum/img/smilies/cool.png" />' % settings.STATIC_URL)
SMILES = ((r'(:|=)\)', EMOTION_SMILE), #:), =)
          (r'(:|=)\|',  EMOTION_NEUTRAL), #:|, =| 
          (r'(:|=)\(', EMOTION_SAD), #:(, =(
          (r'(:|=)D', EMOTION_BIG_SMILE), #:D, =D
          (r':o', EMOTION_YIKES), # :o, :O
          (r';\)', EMOTION_WINK), # ;\ 
          (r':/', EMOTION_HMM), #:/
          (r':P', EMOTION_TONGUE), # :P
          (r':lol:', EMOTION_LOL),
          (r':mad:', EMOTION_MAD),
          (r':rolleyes:', EMOTION_ROLL),
          (r':cool:', EMOTION_COOL)
         )
SMILES = get('DJANGOBB_SMILES', SMILES)
########NEW FILE########
__FILENAME__ = signals
from datetime import datetime

from django.db.models.signals import post_save

from djangobb_forum.subscription import notify_topic_subscribers
from djangobb_forum.models import Topic, Post


def post_saved(instance, **kwargs):
    created = kwargs.get('created')
    post = instance
    topic = post.topic

    if created:
        topic.last_post = post
        topic.post_count = topic.posts.count()
        topic.updated = datetime.now()
        profile = post.user.forum_profile
        profile.post_count = post.user.posts.count()
        profile.save(force_update=True)
        notify_topic_subscribers(post)
    topic.save(force_update=True)


def topic_saved(instance, **kwargs):
    topic = instance
    forum = topic.forum
    forum.topic_count = forum.topics.count()
    forum.updated = topic.updated
    forum.post_count = forum.posts.count()
    forum.last_post_id = topic.last_post_id
    forum.save(force_update=True)

########NEW FILE########
__FILENAME__ = subscription
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.html import strip_tags

from djangobb_forum import settings as forum_settings
from djangobb_forum.util import absolute_url

if "mailer" in settings.INSTALLED_APPS:
    from mailer import send_mail
else:
    from django.core.mail import send_mail
    def send_mail(subject, text, from_email, rec_list, html=None):
        """
        Shortcut for sending email.
        """
    
        msg = EmailMultiAlternatives(subject, text, from_email, rec_list)
        if html:
            msg.attach_alternative(html, "text/html")
        if forum_settings.EMAIL_DEBUG:
            print '---begin---'
            print 'To:', rec_list
            print 'Subject:', subject
            print 'Body:', text
            print '---end---'
        else:
            msg.send(fail_silently=True)


# TODO: move to txt template
TOPIC_SUBSCRIPTION_TEXT_TEMPLATE = (u"""New reply from %(username)s to topic that you have subscribed on.
---
%(message)s
---
See topic: %(post_url)s
Unsubscribe %(unsubscribe_url)s""")


def notify_topic_subscribers(post):
    topic = post.topic
    post_body_text = strip_tags(post.body_html)
    if post != topic.head:
        for user in topic.subscribers.all():
            if user != post.user:
                subject = u'RE: %s' % topic.name
                to_email = user.email
                text_content = TOPIC_SUBSCRIPTION_TEXT_TEMPLATE % {
                        'username': post.user.username,
                        'message': post_body_text,
                        'post_url': absolute_url(post.get_absolute_url()),
                        'unsubscribe_url': absolute_url(reverse('djangobb:forum_delete_subscription', args=[post.topic.id])),
                    }
                #html_content = html_version(post)
                send_mail(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])

########NEW FILE########
__FILENAME__ = forum_extras
# -*- coding: utf-8
import urllib

from django import template
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode
from django.db import settings
from django.utils.html import escape
from django.utils.hashcompat import md5_constructor
from django.contrib.humanize.templatetags.humanize import naturalday

from pagination.templatetags.pagination_tags import paginate

from djangobb_forum.models import Report
from djangobb_forum import settings as forum_settings


register = template.Library()

# TODO:
# * rename all tags with forum_ prefix

@register.filter
def profile_link(user):
    data = u'<a href="%s">%s</a>' % (\
        reverse('djangobb:forum_profile', args=[user.username]), user.username)
    return mark_safe(data)


@register.tag
def forum_time(parser, token):
    try:
        tag, time = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('forum_time requires single argument')
    else:
        return ForumTimeNode(time)


class ForumTimeNode(template.Node):
    def __init__(self, time):
        self.time = template.Variable(time)

    def render(self, context):
        time = self.time.resolve(context)
        formated_time = u'%s %s' % (naturalday(time), time.strftime('%H:%M:%S'))
        formated_time = mark_safe(formated_time)
        return formated_time


# TODO: this old code requires refactoring
@register.inclusion_tag('djangobb_forum/pagination.html', takes_context=True)
def pagination(context, adjacent_pages=1):
    """
    Return the list of A tags with links to pages.
    """
    page_range = range(
        max(1, context['page'] - adjacent_pages),
        min(context['pages'], context['page'] + adjacent_pages) + 1)
    previous = None
    next = None

    if not 1 == context['page']:
        previous = context['page'] - 1

    if not 1 in page_range:
        page_range.insert(0, 1)
        if not 2 in page_range:
            page_range.insert(1, '.')

    if not context['pages'] == context['page']:
        next = context['page'] + 1

    if not context['pages'] in page_range:
        if not context['pages'] - 1 in page_range:
            page_range.append('.')
        page_range.append(context['pages'])
    get_params = '&'.join(['%s=%s' % (x[0], x[1]) for x in
        context['request'].GET.iteritems() if (x[0] != 'page' and x[0] != 'per_page')])
    if get_params:
        get_params = '?%s&' % get_params
    else:
        get_params = '?'

    return {
        'get_params': get_params,
        'previous': previous,
        'next': next,
        'page': context['page'],
        'pages': context['pages'],
        'page_range': page_range,
        'results_per_page': context['results_per_page'],
        'is_paginated': context['is_paginated'],
        }


@register.inclusion_tag('djangobb_forum/lofi/pagination.html', takes_context=True)
def lofi_pagination(context):
    return paginate(context)

@register.simple_tag
def link(object, anchor=u''):
    """
    Return A tag with link to object.
    """

    url = hasattr(object, 'get_absolute_url') and object.get_absolute_url() or None
    anchor = anchor or smart_unicode(object)
    return mark_safe('<a href="%s">%s</a>' % (url, escape(anchor)))


@register.simple_tag
def lofi_link(object, anchor=u''):
    """
    Return A tag with lofi_link to object.
    """

    url = hasattr(object, 'get_absolute_url') and object.get_absolute_url() or None
    anchor = anchor or smart_unicode(object)
    return mark_safe('<a href="%slofi/">%s</a>' % (url, escape(anchor)))


@register.filter
def has_unreads(topic, user):
    """
    Check if topic has messages which user didn't read.
    """
    if not user.is_authenticated() or\
        (user.posttracking.last_read is not None and\
         user.posttracking.last_read > topic.updated):
            return False
    else:
        if isinstance(user.posttracking.topics, dict):
            if topic.last_post_id > user.posttracking.topics.get(str(topic.id), 0):
                return True
            else:
                return False
        return True

@register.filter
def forum_unreads(forum, user):
    """
    Check if forum has topic which user didn't read.
    """
    if not user.is_authenticated():
        return False
    else:
        if isinstance(user.posttracking.topics, dict):
            topics = forum.topics.all().only('last_post')
            if user.posttracking.last_read:
                topics = topics.filter(updated__gte=user.posttracking.last_read)
            for topic in topics:
                if topic.last_post_id > user.posttracking.topics.get(str(topic.id), 0):
                    return True
        return False


@register.filter
def forum_moderated_by(topic, user):
    """
    Check if user is moderator of topic's forum.
    """

    return user.is_superuser or user in topic.forum.moderators.all()


@register.filter
def forum_editable_by(post, user):
    """
    Check if the post could be edited by the user.
    """

    if user.is_superuser:
        return True
    if post.user == user:
        return True
    if user in post.topic.forum.moderators.all():
        return True
    return False


@register.filter
def forum_posted_by(post, user):
    """
    Check if the post is writed by the user.
    """

    return post.user == user


@register.filter
def forum_equal_to(obj1, obj2):
    """
    Check if objects are equal.
    """

    return obj1 == obj2


@register.filter
def forum_authority(user):
    posts = user.forum_profile.post_count
    if posts >= forum_settings.AUTHORITY_STEP_10:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote10.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_9:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote9.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_8:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote8.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_7:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote7.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_6:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote6.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_5:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote5.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_4:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote4.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_3:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote3.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_2:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote2.gif" alt="" />' % (settings.STATIC_URL))
    elif posts >= forum_settings.AUTHORITY_STEP_1:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote1.gif" alt="" />' % (settings.STATIC_URL))
    else:
        return mark_safe('<img src="%sdjangobb_forum/img/authority/vote0.gif" alt="" />' % (settings.STATIC_URL))


@register.filter
def online(user):
    return cache.get('djangobb_user%d' % user.id)

@register.filter
def attachment_link(attach):
    from django.template.defaultfilters import filesizeformat
    if attach.content_type in ['image/png', 'image/gif', 'image/jpeg']:
        img = '<img src="%sdjangobb_forum/img/attachment/image.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['application/x-tar', 'application/zip']:
        img = '<img src="%sdjangobb_forum/img/attachment/compress.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['text/plain']:
        img = '<img src="%sdjangobb_forum/img/attachment/text.png" alt="attachment" />' % (settings.STATIC_URL)
    elif attach.content_type in ['application/msword']:
        img = '<img src="%sdjangobb_forum/img/attachment/doc.png" alt="attachment" />' % (settings.STATIC_URL)
    else:
        img = '<img src="%sdjangobb_forum/img/attachment/unknown.png" alt="attachment" />' % (settings.STATIC_URL)
    attachment = '%s <a href="%s">%s</a> (%s)' % (img, attach.get_absolute_url(), attach.name, filesizeformat(attach.size))
    return mark_safe(attachment)


@register.simple_tag
def new_reports():
    return Report.objects.filter(zapped=False).count()


@register.simple_tag(takes_context=True)
def gravatar(context, email):
    if forum_settings.GRAVATAR_SUPPORT:
        if 'request' in context:
            is_secure = context['request'].is_secure()
        else:
            is_secure = False
        size = max(forum_settings.AVATAR_WIDTH, forum_settings.AVATAR_HEIGHT)
        url = 'https://secure.gravatar.com/avatar/%s?' if is_secure \
            else 'http://www.gravatar.com/avatar/%s?'
        url = url % md5_constructor(email.lower()).hexdigest()
        url += urllib.urlencode({
            'size': size,
            'default': forum_settings.GRAVATAR_DEFAULT,
        })
        return url.replace('&', '&amp;')
    else:
        return ''

@register.simple_tag
def set_theme_style(user):
    theme_style = ''
    selected_theme = ''
    if user.is_authenticated():
        selected_theme = user.forum_profile.theme
        theme_style = '<link rel="stylesheet" type="text/css" href="%(static_url)sdjangobb_forum/themes/%(theme)s/style.css" />'
    else:
        theme_style = '<link rel="stylesheet" type="text/css" href="%(static_url)sdjangobb_forum/themes/default/style.css" />'

    return theme_style % dict(
        static_url=settings.STATIC_URL,
        theme=selected_theme
    )


########NEW FILE########
__FILENAME__ = search_sites
import haystack
haystack.autodiscover()

########NEW FILE########
__FILENAME__ = test_forum
# -*- coding: utf-8 -*-
from django.test import TestCase, Client
from django.contrib.auth.models import User

from djangobb_forum.models import Category, Forum, Topic, Post


class TestForum(TestCase):
    fixtures = ['test_forum.json']
    
    def setUp(self):
        self.category = Category.objects.get(pk=1)
        self.forum = Forum.objects.get(pk=1)
        self.topic = Topic.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)
        self.user = User.objects.get(pk=1)
        self.client = Client()
        self.ip = '127.0.0.1'
        
    def test_login(self):
        self.assertTrue(self.client.login(username='djangobb', password='djangobb'))
    
    def test_create_topic(self):
        topic = Topic.objects.create(forum=self.forum, user=self.user, name="Test Title")
        self.assert_(topic)
        post = Post.objects.create(
            topic=topic, user=self.user, user_ip=self.ip,
            markup='bbcode', body='Test Body'
        )
        self.assert_(post)
        
    def test_create_post(self):
        post = Post.objects.create(
            topic=self.topic, user=self.user, user_ip=self.ip,
            markup='bbcode', body='Test Body'
        )
        self.assert_(post)
        
    def test_edit_post(self):
        self.post.body = 'Test Edit Body'
        self.assertEqual(self.post.body, 'Test Edit Body')
########NEW FILE########
__FILENAME__ = test_profile
# -*- coding: utf-8 -*-
from django.test import TestCase

from djangobb_forum.models import Profile


class TestProfile(TestCase):
    fixtures = ['test_forum.json']
    
    def setUp(self):
        self.profile = Profile.objects.get(pk=1)
        self.signature = 'Test Signature'
        self.jabber = 'Test Jabber'
        self.icq = 'Test ICQ'
        self.msn = 'Test MSN'
        self.aim = 'Test AIM'
        self.yahoo = 'Test YAHOO'
        self.status = 'Test Status'
        self.location = 'Test Location'
        self.site = 'http://djangobb.org/'
        
    def test_personal_profile(self):
        self.profile.status = self.status
        self.assertEqual(self.profile.status, self.status)
        self.profile.location = self.location
        self.assertEqual(self.profile.location, self.location)
        self.profile.site = self.site
        self.assertEqual(self.profile.site, self.site)
        
    def test_messaging_profile(self):
        self.profile.jabber = self.jabber
        self.assertEqual(self.profile.jabber, self.jabber)
        self.profile.icq = self.icq
        self.assertEqual(self.profile.icq, self.icq)
        self.profile.msn = self.msn
        self.assertEqual(self.profile.msn, self.msn)
        self.profile.aim = self.aim
        self.assertEqual(self.profile.aim, self.aim)
        self.profile.yahoo = self.yahoo
        self.assertEqual(self.profile.yahoo, self.yahoo)
        
    def test_personality_profile(self):
        self.profile.show_avatar = False
        self.assertEqual(self.profile.show_avatar, False)
        self.profile.signature = self.signature
        self.assertEqual(self.profile.signature, self.signature)
        
    def test_display_profile(self):
        self.profile.show_smilies = False
        self.assertEqual(self.profile.show_smilies, False)
        
    def test_privacy_profile(self):
        self.profile.privacy_permission = 0 
        self.assertEqual(self.profile.privacy_permission, 0)
########NEW FILE########
__FILENAME__ = test_reputation
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.contrib.auth.models import User

from djangobb_forum.models import Post, Reputation


class TestReputation(TestCase):
    fixtures = ['test_forum.json']
    
    def setUp(self):
        self.from_user = User.objects.get(pk=1)
        self.to_user = User.objects.get(pk=2)
        self.post = Post.objects.get(pk=1)
        self.reason = 'Test Reason'
    
    def test_reputation_plus(self):
        reputation = Reputation.objects.create(
            from_user=self.from_user, to_user=self.to_user, post=self.post,
            sign=1, reason=self.reason
        )
        reputations = Reputation.objects.filter(to_user__id=self.to_user.id)
        total_reputation = 0
        for reputation in reputations:
            total_reputation += reputation.sign
        self.assertEqual(total_reputation, 1)

    def test_reputation_minus(self):
        reputation = Reputation.objects.create(
            from_user=self.from_user, to_user=self.to_user, post=self.post,
            sign=-1, reason=self.reason
        )
        reputations = Reputation.objects.filter(to_user__id=self.to_user.id)
        total_reputation = 0
        for reputation in reputations:
            total_reputation += reputation.sign
        self.assertEqual(total_reputation, -1)
########NEW FILE########
__FILENAME__ = test_templatetags
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.contrib.auth.models import User

from djangobb_forum.models import Post
from djangobb_forum.templatetags.forum_extras import profile_link, link, lofi_link


class TestLinkTags(TestCase):
    fixtures = ['test_forum.json']

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)

    def test_profile_link(self):
        plink = profile_link(self.user)
        self.assertEqual(plink, u"<a href=\"/forum/user/djangobb/\">djangobb</a>")
    
    def test_link(self):
        l = link(self.post)
        self.assertEqual(l, "<a href=\"/forum/post/1/\">Test Body</a>")

    def test_lofi_link(self):
        l = lofi_link(self.post)
        self.assertEqual(l, "<a href=\"/forum/post/1/lofi/\">Test Body</a>")

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
from django.test import TestCase, RequestFactory
from django.conf import settings

from djangobb_forum.models import Post
from djangobb_forum.util import urlize, smiles, convert_text_to_html, paginate


class TestParsers(TestCase):
    def setUp(self):
        self.data_url = "Lorem ipsum dolor sit amet, consectetur http://djangobb.org/ adipiscing elit."
        self.data_smiles = "Lorem ipsum dolor :| sit amet :) <a href=\"http://djangobb.org/\">http://djangobb.org/</a>"
        self.markdown = ""
        self.bbcode = "[b]Lorem[/b] [code]ipsum :)[/code] =)"

    def test_urlize(self):
        urlized_data = urlize(self.data_url)
        self.assertEqual(urlized_data, u"Lorem ipsum dolor sit amet, consectetur <a href=\"http://djangobb.org/\" rel=\"nofollow\">http://djangobb.org/</a> adipiscing elit.")

    def test_smiles(self):
        smiled_data = smiles(self.data_smiles)
        self.assertEqual(smiled_data, u"Lorem ipsum dolor <img src=\"{0}djangobb_forum/img/smilies/neutral.png\" /> sit amet <img src=\"{0}djangobb_forum/img/smilies/smile.png\" /> <a href=\"http://djangobb.org/\">http://djangobb.org/</a>".format(settings.STATIC_URL))

    def test_convert_text_to_html(self):
        bb_data = convert_text_to_html(self.bbcode, 'bbcode')
        self.assertEqual(bb_data, "<strong>Lorem</strong> <div class=\"code\"><pre>ipsum :)</pre></div>=)")

class TestPaginators(TestCase):
    fixtures = ['test_forum.json']

    def setUp(self):
        self.posts = Post.objects.all()[:5]
        self.factory = RequestFactory()

    def test_paginate(self):
        request = self.factory.get('/?page=2')
        pages, paginator, _ = paginate(self.posts, request, 3)
        self.assertEqual(pages, 2)

        request = self.factory.get('/?page=1')
        _, _, paged_list_name = paginate(self.posts, request, 3)
        self.assertEqual(paged_list_name.count(), 3)


class TestVersion(TestCase):
    def test_get_version(self):
        import djangobb_forum

        djangobb_forum.version_info = (0, 2, 1, 'f', 0)
        self.assertEqual(djangobb_forum.get_version(), '0.2.1')
        djangobb_forum.version_info = (2, 3, 1, 'a', 5)
        self.assertIn('2.3.1a5.dev', djangobb_forum.get_version())

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    (r'^forum/', include('djangobb_forum.urls', namespace='djangobb')),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from djangobb_forum import settings as forum_settings
from djangobb_forum import views as forum_views
from djangobb_forum.feeds import LastPosts, LastTopics, LastPostsOnForum, \
     LastPostsOnCategory, LastPostsOnTopic
from djangobb_forum.forms import EssentialsProfileForm, \
    PersonalProfileForm, MessagingProfileForm, PersonalityProfileForm, \
    DisplayProfileForm, PrivacyProfileForm, UploadAvatarForm


urlpatterns = patterns('',

    # Forum
    url('^$', forum_views.index, name='index'),
    url('^(?P<forum_id>\d+)/$', forum_views.show_forum, name='forum'),
    url('^moderate/(?P<forum_id>\d+)/$', forum_views.moderate, name='moderate'),
    url('^search/$', forum_views.search, name='search'),
    url('^misc/$', forum_views.misc, name='misc'),

    # User
    url('^user/(?P<username>.*)/upload_avatar/$', forum_views.upload_avatar, {
        'form_class': UploadAvatarForm,
        'template': 'djangobb_forum/upload_avatar.html'
        }, name='forum_profile_upload_avatar'),
    url('^user/(?P<username>.*)/privacy/$', forum_views.user, {
        'section': 'privacy',
        'form_class': PrivacyProfileForm,
        'template': 'djangobb_forum/profile/profile_privacy.html'
        }, name='forum_profile_privacy'),
    url('^user/(?P<username>.*)/display/$', forum_views.user, {
        'section': 'display',
        'form_class': DisplayProfileForm,
        'template': 'djangobb_forum/profile/profile_display.html'
        }, name='forum_profile_display'),
    url('^user/(?P<username>.*)/personality/$', forum_views.user, {
        'section': 'personality',
        'form_class': PersonalityProfileForm,
        'template': 'djangobb_forum/profile/profile_personality.html'
        }, name='forum_profile_personality'),
    url('^user/(?P<username>.*)/messaging/$', forum_views.user, {
        'section': 'messaging',
        'form_class': MessagingProfileForm,
        'template': 'djangobb_forum/profile/profile_messaging.html'
        }, name='forum_profile_messaging'),
    url('^user/(?P<username>.*)/personal/$', forum_views.user, {
        'section': 'personal',
        'form_class': PersonalProfileForm,
        'template': 'djangobb_forum/profile/profile_personal.html'
        }, name='forum_profile_personal'),
    url('^user/(?P<username>.*)/essentials/$', forum_views.user, name='forum_profile_essentials'),
    url('^user/(?P<username>.*)/$', forum_views.user, name='forum_profile'),
    url('^users/$', forum_views.users, name='forum_users'),

    # Topic
    url('^topic/(?P<topic_id>\d+)/$', forum_views.show_topic, name='topic'),
    url('^(?P<forum_id>\d+)/topic/add/$', forum_views.add_topic, name='add_topic'),
    url('^topic/(?P<topic_id>\d+)/delete_posts/$', forum_views.delete_posts, name='delete_posts'),
    url('^topic/move/$', forum_views.move_topic, name='move_topic'),
    url('^topic/(?P<topic_id>\d+)/stick_unstick/(?P<action>[s|u])/$', forum_views.stick_unstick_topic, name='stick_unstick_topic'),
    url('^topic/(?P<topic_id>\d+)/open_close/(?P<action>[c|o])/$', forum_views.open_close_topic, name='open_close_topic'),

    # Post
    url('^post/(?P<post_id>\d+)/$', forum_views.show_post, name='post'),
    url('^post/(?P<post_id>\d+)/edit/$', forum_views.edit_post, name='edit_post'),
    url('^post/(?P<post_id>\d+)/delete/$', forum_views.delete_post, name='delete_post'),
    # Post preview
    url(r'^preview/$', forum_views.post_preview, name='post_preview'),

    # Subscription
    url('^subscription/topic/(?P<topic_id>\d+)/delete/$', forum_views.delete_subscription, name='forum_delete_subscription'),
    url('^subscription/topic/(?P<topic_id>\d+)/add/$', forum_views.add_subscription, name='forum_add_subscription'),

    # Feeds
    url(r'^feeds/posts/$', LastPosts(), name='forum_posts_feed'),
    url(r'^feeds/topics/$', LastTopics(), name='forum_topics_feed'),
    url(r'^feeds/topic/(?P<topic_id>\d+)/$', LastPostsOnTopic(), name='forum_topic_feed'),
    url(r'^feeds/forum/(?P<forum_id>\d+)/$', LastPostsOnForum(), name='forum_forum_feed'),
    url(r'^feeds/category/(?P<category_id>\d+)/$', LastPostsOnCategory(), name='forum_category_feed'),
)

### EXTENSIONS ###

# LOFI Extension
if (forum_settings.LOFI_SUPPORT):
    urlpatterns += patterns('',
        url('^lofi/$', forum_views.index, {'full':False}, name='lofi_index'),
        url('^(?P<forum_id>\d+)/lofi/$', forum_views.show_forum, {'full':False}, name='lofi_forum'),
        url('^topic/(?P<topic_id>\d+)/lofi/$', forum_views.show_topic, {'full':False}, name='lofi_topic'),
    )

# REPUTATION Extension
if (forum_settings.REPUTATION_SUPPORT):
    urlpatterns += patterns('',
        url('^reputation/(?P<username>.*)/$', forum_views.reputation, name='reputation'),
    )

# ATTACHMENT Extension
if (forum_settings.ATTACHMENT_SUPPORT):
    urlpatterns += patterns('',
        url('^attachment/(?P<hash>\w+)/$', forum_views.show_attachment, name='forum_attachment'),
    )

########NEW FILE########
__FILENAME__ = util
# coding: utf-8

import re
from HTMLParser import HTMLParser, HTMLParseError
from postmarkup import render_bbcode
from json import JSONEncoder
try:
    import markdown
except ImportError:
    pass

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, Http404
from django.utils.functional import Promise
from django.utils.translation import check_for_language
from django.utils.encoding import force_unicode
from django.template.defaultfilters import urlize as django_urlize
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.contrib.sites.models import Site

from djangobb_forum import settings as forum_settings


#compile smiles regexp
_SMILES = [(re.compile(smile_re), path) for smile_re, path in forum_settings.SMILES]


def absolute_url(path):
    return 'http://%s%s' % (Site.objects.get_current().domain, path)


def paged(paged_list_name, per_page):
    """
    Parse page from GET data and pass it to view. Split the
    query set returned from view.
    """

    def decorator(func):
        def wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)
            if not isinstance(result, dict) or 'paged_qs' not in result:
                return result
            try:
                page = int(request.GET.get('page', 1))
            except ValueError:
                page = 1

            real_per_page = per_page

            #if per_page_var:
                #try:
                    #value = int(request.GET[per_page_var])
                #except (ValueError, KeyError):
                    #pass
                #else:
                    #if value > 0:
                        #real_per_page = value

            from django.core.paginator import Paginator
            paginator = Paginator(result['paged_qs'], real_per_page)
            try:
                page_obj = paginator.page(page)
            except (InvalidPage, EmptyPage):
                raise Http404
            result[paged_list_name] = page_obj.object_list
            result['is_paginated'] = page_obj.has_other_pages(),
            result['page_obj'] = page_obj,
            result['page'] = page
            result['page_range'] = paginator.page_range,
            result['pages'] = paginator.num_pages
            result['results_per_page'] = paginator.per_page,
            result['request'] = request
            return result
        return wrapper

    return decorator


class LazyJSONEncoder(JSONEncoder):
    """
    This fing need to save django from crashing.
    """

    def default(self, o):
        if isinstance(o, Promise):
            return force_unicode(o)
        else:
            return super(LazyJSONEncoder, self).default(o)


class JsonResponse(HttpResponse):
    """
    HttpResponse subclass that serialize data into JSON format.
    """

    def __init__(self, data, mimetype='application/json'):
        json_data = LazyJSONEncoder().encode(data)
        super(JsonResponse, self).__init__(
            content=json_data, mimetype=mimetype)


def build_form(Form, _request, GET=False, *args, **kwargs):
    """
    Shorcut for building the form instance of given form class
    """

    if not GET and 'POST' == _request.method:
        form = Form(_request.POST, _request.FILES, *args, **kwargs)
    elif GET and 'GET' == _request.method:
        form = Form(_request.GET, _request.FILES, *args, **kwargs)
    else:
        form = Form(*args, **kwargs)
    return form


class ExcludeTagsHTMLParser(HTMLParser):
        """
        Class for html parsing with excluding specified tags.
        """

        def __init__(self, func, tags=('a', 'pre', 'span')):
            HTMLParser.__init__(self)
            self.func = func
            self.is_ignored = False
            self.tags = tags
            self.html = []

        def handle_starttag(self, tag, attrs):
            self.html.append('<%s%s>' % (tag, self.__html_attrs(attrs)))
            if tag in self.tags:
                self.is_ignored = True

        def handle_data(self, data):
            if not self.is_ignored:
                data = self.func(data)
            self.html.append(data)

        def handle_startendtag(self, tag, attrs):
            self.html.append('<%s%s/>' % (tag, self.__html_attrs(attrs)))

        def handle_endtag(self, tag):
            self.is_ignored = False
            self.html.append('</%s>' % (tag))

        def handle_entityref(self, name):
            self.html.append('&%s;' % name)

        def handle_charref(self, name):
            self.html.append('&#%s;' % name)

        def unescape(self, s):
            #we don't need unescape data (without this possible XSS-attack)
            return s

        def __html_attrs(self, attrs):
            _attrs = ''
            if attrs:
                _attrs = ' %s' % (' '.join([('%s="%s"' % (k, v)) for k, v in attrs]))
            return _attrs

        def feed(self, data):
            HTMLParser.feed(self, data)
            self.html = ''.join(self.html)


def urlize(html):
    """
    Urlize plain text links in the HTML contents.

    Do not urlize content of A and CODE tags.
    """
    try:
        parser = ExcludeTagsHTMLParser(django_urlize)
        parser.feed(html)
        urlized_html = parser.html
        parser.close()
    except HTMLParseError:
        # HTMLParser from Python <2.7.3 is not robust
        # see: http://support.djangobb.org/topic/349/
        if settings.DEBUG:
            raise
        return html
    return urlized_html

def _smile_replacer(data):
    for smile, path in _SMILES:
        data = smile.sub(path, data)
    return data

def smiles(html):
    """
    Replace text smiles.
    """
    try:
        parser = ExcludeTagsHTMLParser(_smile_replacer)
        parser.feed(html)
        smiled_html = parser.html
        parser.close()
    except HTMLParseError:
        # HTMLParser from Python <2.7.3 is not robust
        # see: http://support.djangobb.org/topic/349/
        if settings.DEBUG:
            raise
        return html
    return smiled_html

def paginate(items, request, per_page, total_count=None):
    try:
        page_number = int(request.GET.get('page', 1))
    except ValueError:
        page_number = 1

    paginator = Paginator(items, per_page)
    pages = paginator.num_pages
    try:
        paged_list_name = paginator.page(page_number).object_list
    except (InvalidPage, EmptyPage):
        raise Http404
    return pages, paginator, paged_list_name

def set_language(request, language):
    """
    Change the language of session of authenticated user.
    """

    if check_for_language(language):
        request.session['django_language'] = language


def convert_text_to_html(text, markup):
    if markup == 'bbcode':
        text = render_bbcode(text)
    elif markup == 'markdown':
        text = markdown.markdown(text, safe_mode='escape')
    else:
        raise Exception('Invalid markup property: %s' % markup)
    return urlize(text)


########NEW FILE########
__FILENAME__ = views
# coding: utf-8

import math
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q, F
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from haystack.query import SearchQuerySet, SQ

from djangobb_forum import settings as forum_settings
from djangobb_forum.forms import AddPostForm, EditPostForm, UserSearchForm, \
    PostSearchForm, ReputationForm, MailToForm, EssentialsProfileForm, \
    VotePollForm, ReportForm, VotePollForm, PollForm
from djangobb_forum.models import Category, Forum, Topic, Post, Reputation, \
    Attachment, PostTracking
from djangobb_forum.templatetags import forum_extras
from djangobb_forum.templatetags.forum_extras import forum_moderated_by
from djangobb_forum.util import build_form, paginate, set_language, smiles, convert_text_to_html




def index(request, full=True):
    users_cached = cache.get('djangobb_users_online', {})
    users_online = users_cached and User.objects.filter(id__in=users_cached.keys()) or []
    guests_cached = cache.get('djangobb_guests_online', {})
    guest_count = len(guests_cached)
    users_count = len(users_online)

    _forums = Forum.objects.all()
    user = request.user
    if not user.is_superuser:
        user_groups = user.groups.all() or [] # need 'or []' for anonymous user otherwise: 'EmptyManager' object is not iterable
        _forums = _forums.filter(Q(category__groups__in=user_groups) | Q(category__groups__isnull=True))

    _forums = _forums.select_related('last_post__topic', 'last_post__user', 'category')

    cats = {}
    forums = {}
    for forum in _forums:
        cat = cats.setdefault(forum.category.id,
            {'id': forum.category.id, 'cat': forum.category, 'forums': []})
        cat['forums'].append(forum)
        forums[forum.id] = forum

    cmpdef = lambda a, b: cmp(a['cat'].position, b['cat'].position)
    cats = sorted(cats.values(), cmpdef)

    to_return = {'cats': cats,
                'posts': Post.objects.count(),
                'topics': Topic.objects.count(),
                'users': User.objects.count(),
                'users_online': users_online,
                'online_count': users_count,
                'guest_count': guest_count,
                'last_user': User.objects.latest('date_joined'),
                }
    if full:
        return render(request, 'djangobb_forum/index.html', to_return)
    else:
        return render(request, 'djangobb_forum/lofi/index.html', to_return)


@transaction.commit_on_success
def moderate(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    if request.user.is_superuser or request.user in forum.moderators.all():
        topic_ids = request.POST.getlist('topic_id')
        if 'move_topics' in request.POST:
            return render(request, 'djangobb_forum/move_topic.html', {
                'categories': Category.objects.all(),
                'topic_ids': topic_ids,
                'exclude_forum': forum,
            })
        elif 'delete_topics' in request.POST:
            for topic_id in topic_ids:
                topic = get_object_or_404(Topic, pk=topic_id)
                topic.delete()
            messages.success(request, _("Topics deleted"))
            return HttpResponseRedirect(reverse('djangobb:index'))
        elif 'open_topics' in request.POST:
            for topic_id in topic_ids:
                open_close_topic(request, topic_id, 'o')
            messages.success(request, _("Topics opened"))
            return HttpResponseRedirect(reverse('djangobb:index'))
        elif 'close_topics' in request.POST:
            for topic_id in topic_ids:
                open_close_topic(request, topic_id, 'c')
            messages.success(request, _("Topics closed"))
            return HttpResponseRedirect(reverse('djangobb:index'))

        return render(request, 'djangobb_forum/moderate.html', {'forum': forum,
                'topics': topics,
                #'sticky_topics': forum.topics.filter(sticky=True),
                'posts': forum.posts.count(),
                })
    else:
        raise Http404


def search(request):
    # TODO: used forms in every search type

    def _render_search_form(form=None):
        return render(request, 'djangobb_forum/search_form.html', {'categories': Category.objects.all(),
                'form': form,
                })

    if not 'action' in request.GET:
        return _render_search_form(form=PostSearchForm())

    if request.GET.get("show_as") == "posts":
        show_as_posts = True
        template_name = 'djangobb_forum/search_posts.html'
    else:
        show_as_posts = False
        template_name = 'djangobb_forum/search_topics.html'

    context = {}

    # Create 'user viewable' pre-filtered topics/posts querysets
    viewable_category = Category.objects.all()
    topics = Topic.objects.all().order_by("-last_post__created")
    posts = Post.objects.all().order_by('-created')
    user = request.user
    if not user.is_superuser:
        user_groups = user.groups.all() or [] # need 'or []' for anonymous user otherwise: 'EmptyManager' object is not iterable 
        viewable_category = viewable_category.filter(Q(groups__in=user_groups) | Q(groups__isnull=True))

        topics = Topic.objects.filter(forum__category__in=viewable_category)
        posts = Post.objects.filter(topic__forum__category__in=viewable_category)

    base_url = None
    _generic_context = True

    action = request.GET['action']
    if action == 'show_24h':
        date = datetime.now() - timedelta(days=1)
        if show_as_posts:
            context["posts"] = posts.filter(Q(created__gte=date) | Q(updated__gte=date))
        else:
            context["topics"] = topics.filter(Q(last_post__created__gte=date) | Q(last_post__updated__gte=date))
        _generic_context = False
    elif action == 'show_new':
        if not user.is_authenticated():
            raise Http404("Search 'show_new' not available for anonymous user.")
        try:
            last_read = PostTracking.objects.get(user=user).last_read
        except PostTracking.DoesNotExist:
            last_read = None

        if last_read:
            if show_as_posts:
                context["posts"] = posts.filter(Q(created__gte=last_read) | Q(updated__gte=last_read))
            else:
                context["topics"] = topics.filter(Q(last_post__created__gte=last_read) | Q(last_post__updated__gte=last_read))
            _generic_context = False
        else:
            #searching more than forum_settings.SEARCH_PAGE_SIZE in this way - not good idea :]
            topics_id = [topic.id for topic in topics[:forum_settings.SEARCH_PAGE_SIZE] if forum_extras.has_unreads(topic, user)]
            topics = Topic.objects.filter(id__in=topics_id) # to create QuerySet

    elif action == 'show_unanswered':
        topics = topics.filter(post_count=1)
    elif action == 'show_subscriptions':
        topics = topics.filter(subscribers__id=user.id)
    elif action == 'show_user':
        # Show all posts from user or topics started by user
        if not user.is_authenticated():
            raise Http404("Search 'show_user' not available for anonymous user.")

        user_id = request.GET.get("user_id", user.id)
        try:
            user_id = int(user_id)
        except ValueError:
            raise SuspiciousOperation()

        if user_id != user.id:
            try:
                search_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, _("Error: User unknown!"))
                return HttpResponseRedirect(request.path)
            messages.info(request, "Filter by user '%s'." % search_user.username)

        if show_as_posts:
            posts = posts.filter(user__id=user_id)
        else:
            # show as topic
            topics = topics.filter(posts__user__id=user_id).order_by("-last_post__created").distinct()

        base_url = "?action=show_user&user_id=%s&show_as=" % user_id
    elif action == 'search':
        form = PostSearchForm(request.GET)
        if not form.is_valid():
            return _render_search_form(form)

        keywords = form.cleaned_data['keywords']
        author = form.cleaned_data['author']
        forum = form.cleaned_data['forum']
        search_in = form.cleaned_data['search_in']
        sort_by = form.cleaned_data['sort_by']
        sort_dir = form.cleaned_data['sort_dir']

        query = SearchQuerySet().models(Post)

        if author:
            query = query.filter(author__username=author)

        if forum != u'0':
            query = query.filter(forum__id=forum)

        if keywords:
            if search_in == 'all':
                query = query.filter(SQ(topic=keywords) | SQ(text=keywords))
            elif search_in == 'message':
                query = query.filter(text=keywords)
            elif search_in == 'topic':
                query = query.filter(topic=keywords)

        order = {'0': 'created',
                 '1': 'author',
                 '2': 'topic',
                 '3': 'forum'}.get(sort_by, 'created')
        if sort_dir == 'DESC':
            order = '-' + order

        posts = query.order_by(order)

        if not show_as_posts:
            # TODO: We have here a problem to get a list of topics without double entries.
            # Maybe we must add a search index over topics?

            # Info: If whoosh backend used, setup HAYSTACK_ITERATOR_LOAD_PER_QUERY
            #    to a higher number to speed up
            post_pks = posts.values_list("pk", flat=True)
            context["topics"] = topics.filter(posts__in=post_pks).distinct()
        else:
            # FIXME: How to use the pre-filtered query from above?
            posts = posts.filter(topic__forum__category__in=viewable_category)
            context["posts"] = posts

        get_query_dict = request.GET.copy()
        get_query_dict.pop("show_as")
        base_url = "?%s&show_as=" % get_query_dict.urlencode()
        _generic_context = False

    if _generic_context:
        if show_as_posts:
            context["posts"] = posts.filter(topic__in=topics).order_by('-created')
        else:
            context["topics"] = topics

    if base_url is None:
        base_url = "?action=%s&show_as=" % action

    if show_as_posts:
        context["as_topic_url"] = base_url + "topics"
        post_count = context["posts"].count()
        messages.success(request, _("Found %i posts.") % post_count)
    else:
        context["as_post_url"] = base_url + "posts"
        topic_count = context["topics"].count()
        messages.success(request, _("Found %i topics.") % topic_count)

    return render(request, template_name, context)




@login_required
def misc(request):
    if 'action' in request.GET:
        action = request.GET['action']
        if action == 'markread':
            user = request.user
            PostTracking.objects.filter(user__id=user.id).update(last_read=datetime.now(), topics=None)
            messages.info(request, _("All topics marked as read."))
            return HttpResponseRedirect(reverse('djangobb:index'))

        elif action == 'report':
            if request.GET.get('post_id', ''):
                post_id = request.GET['post_id']
                post = get_object_or_404(Post, id=post_id)
                form = build_form(ReportForm, request, reported_by=request.user, post=post_id)
                if request.method == 'POST' and form.is_valid():
                    form.save()
                    messages.info(request, _("Post reported."))
                    return HttpResponseRedirect(post.get_absolute_url())
                return render(request, 'djangobb_forum/report.html', {'form':form})

    elif 'submit' in request.POST and 'mail_to' in request.GET:
        form = MailToForm(request.POST)
        if form.is_valid():
            user = get_object_or_404(User, username=request.GET['mail_to'])
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body'] + u'\n %s %s [%s]' % (Site.objects.get_current().domain,
                                                                  request.user.username,
                                                                  request.user.email)
            try:
                user.email_user(subject, body, request.user.email)
                messages.success(request, _("Email send."))
            except Exception:
                messages.error(request, _("Email could not be sent."))
            return HttpResponseRedirect(reverse('djangobb:index'))

    elif 'mail_to' in request.GET:
        mailto = get_object_or_404(User, username=request.GET['mail_to'])
        form = MailToForm()
        return render(request, 'djangobb_forum/mail_to.html', {'form':form,
                'mailto': mailto}
                )


def show_forum(request, forum_id, full=True):
    forum = get_object_or_404(Forum, pk=forum_id)
    if not forum.category.has_access(request.user):
        return HttpResponseForbidden()
    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    moderator = request.user.is_superuser or\
        request.user in forum.moderators.all()
    to_return = {'categories': Category.objects.all(),
                'forum': forum,
                'posts': forum.post_count,
                'topics': topics,
                'moderator': moderator,
                }
    if full:
        return render(request, 'djangobb_forum/forum.html', to_return)
    else:
        return render(request, 'djangobb_forum/lofi/forum.html', to_return)


@transaction.commit_on_success
def show_topic(request, topic_id, full=True):
    """
    * Display a topic
    * save a reply
    * save a poll vote
    
    TODO: Add reply in lofi mode
    """
    post_request = request.method == "POST"
    user_is_authenticated = request.user.is_authenticated()
    if post_request and not user_is_authenticated:
        # Info: only user that are logged in should get forms in the page.
        return HttpResponseForbidden()

    topic = get_object_or_404(Topic.objects.select_related(), pk=topic_id)
    if not topic.forum.category.has_access(request.user):
        return HttpResponseForbidden()
    Topic.objects.filter(pk=topic.id).update(views=F('views') + 1)

    last_post = topic.last_post

    if request.user.is_authenticated():
        topic.update_read(request.user)
    posts = topic.posts.all().select_related()

    moderator = request.user.is_superuser or request.user in topic.forum.moderators.all()
    if user_is_authenticated and request.user in topic.subscribers.all():
        subscribed = True
    else:
        subscribed = False

    # reply form
    reply_form = None
    form_url = None
    back_url = None
    if user_is_authenticated and not topic.closed:
        form_url = request.path + "#reply" # if form validation failed: browser should scroll down to reply form ;)
        back_url = request.path
        ip = request.META.get('REMOTE_ADDR', None)
        post_form_kwargs = {"topic":topic, "user":request.user, "ip":ip}
        if post_request and AddPostForm.FORM_NAME in request.POST:
            reply_form = AddPostForm(request.POST, request.FILES, **post_form_kwargs)
            if reply_form.is_valid():
                post = reply_form.save()
                messages.success(request, _("Your reply saved."))
                return HttpResponseRedirect(post.get_absolute_url())
        else:
            reply_form = AddPostForm(
                initial={
                    'markup': request.user.forum_profile.markup,
                    'subscribe': request.user.forum_profile.auto_subscribe,
                },
                **post_form_kwargs
            )

    # handle poll, if exists
    poll_form = None
    polls = topic.poll_set.all()
    if not polls:
        poll = None
    else:
        poll = polls[0]
        if user_is_authenticated: # Only logged in users can vote
            poll.auto_deactivate()
            has_voted = request.user in poll.users.all()
            if not post_request or not VotePollForm.FORM_NAME in request.POST:
                # It's not a POST request or: The reply form was send and not a poll vote
                if poll.active and not has_voted:
                    poll_form = VotePollForm(poll)
            else:
                if not poll.active:
                    messages.error(request, _("This poll is not active!"))
                    return HttpResponseRedirect(topic.get_absolute_url())
                elif has_voted:
                    messages.error(request, _("You have already vote to this poll in the past!"))
                    return HttpResponseRedirect(topic.get_absolute_url())

                poll_form = VotePollForm(poll, request.POST)
                if poll_form.is_valid():
                    ids = poll_form.cleaned_data["choice"]
                    queryset = poll.choices.filter(id__in=ids)
                    queryset.update(votes=F('votes') + 1)
                    poll.users.add(request.user) # save that this user has vote
                    messages.success(request, _("Your votes are saved."))
                    return HttpResponseRedirect(topic.get_absolute_url())

    highlight_word = request.GET.get('hl', '')
    if full:
        return render(request, 'djangobb_forum/topic.html', {'categories': Category.objects.all(),
                'topic': topic,
                'last_post': last_post,
                'form_url': form_url,
                'reply_form': reply_form,
                'back_url': back_url,
                'moderator': moderator,
                'subscribed': subscribed,
                'posts': posts,
                'highlight_word': highlight_word,
                'poll': poll,
                'poll_form': poll_form,
                })
    else:
        return render(request, 'djangobb_forum/lofi/topic.html', {'categories': Category.objects.all(),
                'topic': topic,
                'posts': posts,
                'poll': poll,
                'poll_form': poll_form,
                })


@login_required
@transaction.commit_on_success
def add_topic(request, forum_id):
    """
    create a new topic, with or without poll
    """
    forum = get_object_or_404(Forum, pk=forum_id)
    if not forum.category.has_access(request.user):
        return HttpResponseForbidden()

    ip = request.META.get('REMOTE_ADDR', None)
    post_form_kwargs = {"forum":forum, "user":request.user, "ip":ip, }

    if request.method == 'POST':
        form = AddPostForm(request.POST, request.FILES, **post_form_kwargs)
        if form.is_valid():
            all_valid = True
        else:
            all_valid = False

        poll_form = PollForm(request.POST)
        create_poll = poll_form.create_poll()
        if not create_poll:
            # All poll fields are empty: User didn't want to create a poll
            # Don't run validation and remove all form error messages
            poll_form = PollForm() # create clean form without form errors
        elif not poll_form.is_valid():
            all_valid = False

        if all_valid:
            post = form.save()
            if create_poll:
                poll_form.save(post)
                messages.success(request, _("Topic with poll saved."))
            else:
                messages.success(request, _("Topic saved."))
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = AddPostForm(
            initial={
                'markup': request.user.forum_profile.markup,
                'subscribe': request.user.forum_profile.auto_subscribe,
            },
            **post_form_kwargs
        )
        if forum_id: # Create a new topic
            poll_form = PollForm()

    context = {
        'forum': forum,
        'create_poll_form': poll_form,
        'form': form,
        'form_url': request.path,
        'back_url': forum.get_absolute_url(),
    }
    return render(request, 'djangobb_forum/add_topic.html', context)


@transaction.commit_on_success
def upload_avatar(request, username, template=None, form_class=None):
    user = get_object_or_404(User, username=username)
    if request.user.is_authenticated() and user == request.user or request.user.is_superuser:
        form = build_form(form_class, request, instance=user.forum_profile)
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, _("Your avatar uploaded."))
            return HttpResponseRedirect(reverse('djangobb:forum_profile', args=[user.username]))
        return render(request, template, {'form': form,
                'avatar_width': forum_settings.AVATAR_WIDTH,
                'avatar_height': forum_settings.AVATAR_HEIGHT,
               })
    else:
        topic_count = Topic.objects.filter(user__id=user.id).count()
        if user.forum_profile.post_count < forum_settings.POST_USER_SEARCH and not request.user.is_authenticated():
            messages.error(request, _("Please sign in."))
            return HttpResponseRedirect(reverse('user_signin') + '?next=%s' % request.path)
        return render(request, template, {'profile': user,
                'topic_count': topic_count,
               })


@transaction.commit_on_success
def user(request, username, section='essentials', action=None, template='djangobb_forum/profile/profile_essentials.html', form_class=EssentialsProfileForm):
    user = get_object_or_404(User, username=username)
    if request.user.is_authenticated() and user == request.user or request.user.is_superuser:
        profile_url = reverse('djangobb:forum_profile_%s' % section, args=[user.username])
        form = build_form(form_class, request, instance=user.forum_profile, extra_args={'request': request})
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, _("User profile saved."))
            return HttpResponseRedirect(profile_url)
        return render(request, template, {'active_menu': section,
                'profile': user,
                'form': form,
               })
    else:
        template = 'djangobb_forum/user.html'
        topic_count = Topic.objects.filter(user__id=user.id).count()
        if user.forum_profile.post_count < forum_settings.POST_USER_SEARCH and not request.user.is_authenticated():
            messages.error(request, _("Please sign in."))
            return HttpResponseRedirect(reverse('user_signin') + '?next=%s' % request.path)
        return render(request, template, {'profile': user,
                'topic_count': topic_count,
               })


@login_required
@transaction.commit_on_success
def reputation(request, username):
    user = get_object_or_404(User, username=username)
    form = build_form(ReputationForm, request, from_user=request.user, to_user=user)

    if 'action' in request.GET:
        if request.user == user:
            return HttpResponseForbidden(u'You can not change the reputation of yourself')

        if 'post_id' in request.GET:
            post_id = request.GET['post_id']
            form.fields['post'].initial = post_id
            if request.GET['action'] == 'plus':
                form.fields['sign'].initial = 1
            elif request.GET['action'] == 'minus':
                form.fields['sign'].initial = -1
            return render(request, 'djangobb_forum/reputation_form.html', {'form': form})
        else:
            raise Http404

    elif request.method == 'POST':
        if 'del_reputation' in request.POST and request.user.is_superuser:
            reputation_list = request.POST.getlist('reputation_id')
            for reputation_id in reputation_list:
                reputation = get_object_or_404(Reputation, pk=reputation_id)
                reputation.delete()
            messages.success(request, _("Reputation deleted."))
            return HttpResponseRedirect(reverse('djangobb:index'))
        elif form.is_valid():
            form.save()
            post_id = request.POST['post']
            post = get_object_or_404(Post, id=post_id)
            messages.success(request, _("Reputation saved."))
            return HttpResponseRedirect(post.get_absolute_url())
        else:
            return render(request, 'djangobb_forum/reputation_form.html', {'form': form})
    else:
        reputations = Reputation.objects.filter(to_user__id=user.id).order_by('-time').select_related()
        return render(request, 'djangobb_forum/reputation.html', {'reputations': reputations,
                'profile': user.forum_profile,
               })


def show_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    count = post.topic.posts.filter(created__lt=post.created).count() + 1
    page = math.ceil(count / float(forum_settings.TOPIC_PAGE_SIZE))
    url = '%s?page=%d#post-%d' % (reverse('djangobb:topic', args=[post.topic.id]), page, post.id)
    return HttpResponseRedirect(url)


@login_required
@transaction.commit_on_success
def edit_post(request, post_id):
    from djangobb_forum.templatetags.forum_extras import forum_editable_by

    post = get_object_or_404(Post, pk=post_id)
    topic = post.topic
    if not forum_editable_by(post, request.user):
        messages.error(request, _("No permissions to edit this post."))
        return HttpResponseRedirect(post.get_absolute_url())
    form = build_form(EditPostForm, request, topic=topic, instance=post)
    if form.is_valid():
        post = form.save(commit=False)
        post.updated_by = request.user
        post.save()
        messages.success(request, _("Post updated."))
        return HttpResponseRedirect(post.get_absolute_url())

    return render(request, 'djangobb_forum/edit_post.html', {'form': form,
            'post': post,
            })


@login_required
@transaction.commit_on_success
def delete_posts(request, topic_id):

    topic = Topic.objects.select_related().get(pk=topic_id)

    if forum_moderated_by(topic, request.user):
        deleted = False
        post_list = request.POST.getlist('post')
        for post_id in post_list:
            if not deleted:
                deleted = True
            delete_post(request, post_id)
        if deleted:
            messages.success(request, _("Post deleted."))
            return HttpResponseRedirect(topic.get_absolute_url())

    last_post = topic.posts.latest()

    if request.user.is_authenticated():
        topic.update_read(request.user)

    posts = topic.posts.all().select_related()

    initial = {}
    if request.user.is_authenticated():
        initial = {'markup': request.user.forum_profile.markup}
    form = AddPostForm(topic=topic, initial=initial)

    moderator = request.user.is_superuser or\
        request.user in topic.forum.moderators.all()
    if request.user.is_authenticated() and request.user in topic.subscribers.all():
        subscribed = True
    else:
        subscribed = False
    return render(request, 'djangobb_forum/delete_posts.html', {
            'topic': topic,
            'last_post': last_post,
            'form': form,
            'moderator': moderator,
            'subscribed': subscribed,
            'posts': posts,
            })


@login_required
@transaction.commit_on_success
def move_topic(request):
    if 'topic_id' in request.GET:
        #if move only 1 topic
        topic_ids = [request.GET['topic_id']]
    else:
        topic_ids = request.POST.getlist('topic_id')
    first_topic = topic_ids[0]
    topic = get_object_or_404(Topic, pk=first_topic)
    from_forum = topic.forum
    if 'to_forum' in request.POST:
        to_forum_id = int(request.POST['to_forum'])
        to_forum = get_object_or_404(Forum, pk=to_forum_id)
        for topic_id in topic_ids:
            topic = get_object_or_404(Topic, pk=topic_id)
            if topic.forum != to_forum:
                if forum_moderated_by(topic, request.user):
                    topic.forum = to_forum
                    topic.save()

        #TODO: not DRY
        try:
            last_post = Post.objects.filter(topic__forum__id=from_forum.id).latest()
        except Post.DoesNotExist:
            last_post = None
        from_forum.last_post = last_post
        from_forum.topic_count = from_forum.topics.count()
        from_forum.post_count = from_forum.posts.count()
        from_forum.save()
        messages.success(request, _("Topic moved."))
        return HttpResponseRedirect(to_forum.get_absolute_url())

    return render(request, 'djangobb_forum/move_topic.html', {'categories': Category.objects.all(),
            'topic_ids': topic_ids,
            'exclude_forum': from_forum,
            })


@login_required
@transaction.commit_on_success
def stick_unstick_topic(request, topic_id, action):
    topic = get_object_or_404(Topic, pk=topic_id)
    if forum_moderated_by(topic, request.user):
        if action == 's':
            topic.sticky = True
            messages.success(request, _("Topic marked as sticky."))
        elif action == 'u':
            messages.success(request, _("Sticky flag removed from topic."))
            topic.sticky = False
        topic.save()
    return HttpResponseRedirect(topic.get_absolute_url())


@login_required
@transaction.commit_on_success
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    last_post = post.topic.last_post
    topic = post.topic
    forum = post.topic.forum

    if not (request.user.is_superuser or\
        request.user in post.topic.forum.moderators.all() or \
        (post.user == request.user and post == last_post)):
        messages.success(request, _("You haven't the permission to delete this post."))
        return HttpResponseRedirect(post.get_absolute_url())

    post.delete()
    messages.success(request, _("Post deleted."))

    try:
        Topic.objects.get(pk=topic.id)
    except Topic.DoesNotExist:
        #removed latest post in topic
        return HttpResponseRedirect(forum.get_absolute_url())
    else:
        return HttpResponseRedirect(topic.get_absolute_url())


@login_required
@transaction.commit_on_success
def open_close_topic(request, topic_id, action):
    topic = get_object_or_404(Topic, pk=topic_id)
    if forum_moderated_by(topic, request.user):
        if action == 'c':
            topic.closed = True
            messages.success(request, _("Topic closed."))
        elif action == 'o':
            topic.closed = False
            messages.success(request, _("Topic opened."))
        topic.save()
    return HttpResponseRedirect(topic.get_absolute_url())


def users(request):
    users = User.objects.filter(forum_profile__post_count__gte=forum_settings.POST_USER_SEARCH).order_by('username')
    form = UserSearchForm(request.GET)
    users = form.filter(users)
    return render(request, 'djangobb_forum/users.html', {'users': users,
            'form': form,
            })


@login_required
@transaction.commit_on_success
def delete_subscription(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.remove(request.user)
    messages.info(request, _("Topic subscription removed."))
    if 'from_topic' in request.GET:
        return HttpResponseRedirect(reverse('djangobb:topic', args=[topic.id]))
    else:
        return HttpResponseRedirect(reverse('djangobb:forum_profile', args=[request.user.username]))


@login_required
@transaction.commit_on_success
def add_subscription(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.add(request.user)
    messages.success(request, _("Topic subscribed."))
    return HttpResponseRedirect(reverse('djangobb:topic', args=[topic.id]))


@login_required
def show_attachment(request, hash):
    attachment = get_object_or_404(Attachment, hash=hash)
    file_data = file(attachment.get_absolute_path(), 'rb').read()
    response = HttpResponse(file_data, mimetype=attachment.content_type)
    response['Content-Disposition'] = 'attachment; filename="%s"' % smart_str(attachment.name)
    return response


@login_required
@csrf_exempt
def post_preview(request):
    '''Preview for markitup'''
    markup = request.user.forum_profile.markup
    data = request.POST.get('data', '')

    data = convert_text_to_html(data, markup)
    if forum_settings.SMILES_SUPPORT:
        data = smiles(data)
    return render(request, 'djangobb_forum/post_preview.html', {'data': data})

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
import os
from os.path import dirname, abspath
from optparse import OptionParser

from django.conf import settings, global_settings

# For convenience configure settings if they are not pre-configured or if we
# haven't been provided settings to use by environment variable.
if not settings.configured and not os.environ.get('DJANGO_SETTINGS_MODULE'):
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.sitemaps',
            'django.contrib.humanize',

            'haystack',
            'pagination',

            'djangobb_forum',
        ),
        MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES + (
                'django.middleware.locale.LocaleMiddleware',
                'pagination.middleware.PaginationMiddleware',
                'django.middleware.transaction.TransactionMiddleware',
                'djangobb_forum.middleware.LastLoginMiddleware',
                'djangobb_forum.middleware.UsersOnline',
        ),
        TEMPLATE_CONTEXT_PROCESSORS=global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
            'djangobb_forum.context_processors.forum_settings',
        ),
        PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
        ROOT_URLCONF='djangobb_forum.tests.urls',
        DEBUG=False,
        SITE_ID=1,
        HAYSTACK_SITECONF='djangobb_forum.tests.search_sites',
        HAYSTACK_SEARCH_ENGINE='dummy',
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args, **kwargs):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['djangobb_forum']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    test_runner = DjangoTestSuiteRunner(verbosity=kwargs.get('verbosity', 1), interactive=kwargs.get('interactive', False), failfast=kwargs.get('failfast'))
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--failfast', action='store_true', default=False, dest='failfast')

    (options, args) = parser.parse_args()

    runtests(failfast=options.failfast, *args)

########NEW FILE########
