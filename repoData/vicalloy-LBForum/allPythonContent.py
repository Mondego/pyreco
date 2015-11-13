__FILENAME__ = accountviews
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from forms import SignatureForm


def profile(request, user_id=None, template_name="lbforum/account/profile.html"):
    view_user = request.user
    if user_id:
        view_user = get_object_or_404(User, pk=user_id)
    view_only = view_user != request.user
    ext_ctx = {'view_user': view_user, 'view_only': view_only}
    return render(request, template_name, ext_ctx)


@login_required
def signature(request, form_class=SignatureForm, template_name="lbforum/account/signature.html"):
    profile = request.user.lbforum_profile
    if request.method == "POST":
        form = form_class(instance=profile, data=request.POST)
        form.save()
    else:
        form = form_class(instance=profile)
    ext_ctx = {'form': form}
    return render(request, template_name, ext_ctx)

########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from models import Category, Forum, TopicType, Topic
from models import Post, LBForumUserProfile

admin.site.register(Category)


def update_forum_state_info(modeladmin, request, queryset):
    for forum in queryset:
        forum.update_state_info()
update_forum_state_info.short_description = _("Update forum state info")


class ForumAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'num_topics', 'num_posts',)
    list_filter = ('category',)
    actions = [update_forum_state_info]

admin.site.register(Forum, ForumAdmin)


class TopicTypeAdmin(admin.ModelAdmin):
    list_display = ('forum', 'name', 'slug', 'description', )
    list_filter = ('forum',)

admin.site.register(TopicType, TopicTypeAdmin)


class PostInline(admin.TabularInline):
    model = Post


def update_topic_state_info(modeladmin, request, queryset):
    for topic in queryset:
        topic.update_state_info()
update_topic_state_info.short_description = _("Update topic state info")


def update_topic_attr_as_not(modeladmin, request, queryset, attr):
    for topic in queryset:
        if attr == 'sticky':
            topic.sticky = not topic.sticky
        elif attr == 'close':
            topic.closed = not topic.closed
        elif attr == 'hide':
            topic.hidden = not topic.hidden
        topic.save()


def sticky_unsticky_topic(modeladmin, request, queryset):
    update_topic_attr_as_not(modeladmin, request, queryset, 'sticky')
sticky_unsticky_topic.short_description = _("sticky/unsticky topics")


def close_unclose_topic(modeladmin, request, queryset):
    update_topic_attr_as_not(modeladmin, request, queryset, 'close')
close_unclose_topic.short_description = _("close/unclose topics")


def hide_unhide_topic(modeladmin, request, queryset):
    update_topic_attr_as_not(modeladmin, request, queryset, 'hide')
hide_unhide_topic.short_description = _("hide/unhide topics")


class TopicAdmin(admin.ModelAdmin):
    list_display = ('subject', 'forum', 'topic_type', 'posted_by', 'sticky', 'closed',
            'hidden', 'level', 'num_views', 'num_replies', 'created_on', 'updated_on', )
    list_filter = ('forum', 'sticky', 'closed', 'hidden', 'level')
    search_fields = ('subject', 'posted_by__username', )
    #inlines = (PostInline, )
    actions = [update_topic_state_info, sticky_unsticky_topic, close_unclose_topic, hide_unhide_topic]

admin.site.register(Topic, TopicAdmin)


class PostAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'topic', 'posted_by', 'poster_ip',
            'created_on', 'updated_on', )
    search_fields = ('topic__subject', 'posted_by__username', 'message', )

admin.site.register(Post, PostAdmin)


class LBForumUserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'userrank', 'last_activity', 'last_posttime', 'signature',)
    search_fields = ('user__username', 'userrank', )

admin.site.register(LBForumUserProfile, LBForumUserProfileAdmin)

########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from datetime import datetime

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import Topic, Post, TopicType
from models import LBForumUserProfile

FORUM_ORDER_BY_CHOICES = (
    ('-last_reply_on', _('Last Reply')),
    ('-created_on', _('Last Topic')),
)


class ForumForm(forms.Form):
    order_by = forms.ChoiceField(label=_('Order By'), choices=FORUM_ORDER_BY_CHOICES, required=False)


class PostForm(forms.ModelForm):
    topic_type = forms.ChoiceField(label=_('Topic Type'), required=False)
    subject = forms.CharField(label=_('Subject'), widget=forms.TextInput(attrs={'size': '80'}))
    message = forms.CharField(label=_('Message'), widget=forms.Textarea(attrs={'cols': '95', 'rows': '14'}))
    attachments = forms.Field(label=_('Attachments'), required=False, widget=forms.SelectMultiple())
    need_replay = forms.BooleanField(label=_('Need Reply'), required=False)
    need_reply_attachments = forms.BooleanField(label=_('Attachments Need Reply'), required=False)

    class Meta:
        model = Post
        fields = ('message',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.topic = kwargs.pop('topic', None)
        self.forum = kwargs.pop('forum', None)
        self.ip = kwargs.pop('ip', None)
        super(PostForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.forum = self.instance.topic.forum
        topic_types = self.forum.topictype_set.all()
        self.fields['topic_type'].choices = [(tp.id, tp.name) for tp in topic_types]
        self.fields['topic_type'].choices.insert(0, (('', '--------')))
        self.fields.keyOrder = ['topic_type', 'subject', 'message', 'attachments', 'need_replay',
                'need_reply_attachments']


class EditPostForm(PostForm):
    def __init__(self, *args, **kwargs):
        super(EditPostForm, self).__init__(*args, **kwargs)
        self.initial['subject'] = self.instance.topic.subject
        self.initial['need_replay'] = self.instance.topic.need_replay
        self.initial['need_reply_attachments'] = self.instance.topic.need_reply_attachments
        if self.instance.topic.topic_type:
            self.initial['topic_type'] = self.instance.topic.topic_type.id
        if not self.instance.topic_post:
            self.fields['subject'].required = False

    def save(self):
        post = self.instance
        post.message = self.cleaned_data['message']
        post.updated_on = datetime.now()
        post.edited_by = self.user.username
        attachments = self.cleaned_data['attachments']
        post.update_attachments(attachments)
        post.save()
        if post.topic_post:
            post.topic.subject = self.cleaned_data['subject']
            post.topic.need_replay = self.cleaned_data['need_replay']
            post.topic.need_reply_attachments = self.cleaned_data['need_reply_attachments']
            topic_type = self.cleaned_data['topic_type']
            if topic_type:
                topic_type = TopicType.objects.get(id=topic_type)
            else:
                topic_type = None
            post.topic.topic_type = topic_type
            post.topic.save()
        return post


class NewPostForm(PostForm):
    def __init__(self, *args, **kwargs):
        super(NewPostForm, self).__init__(*args, **kwargs)
        if self.topic:
            self.fields['subject'].required = False

    def save(self):
        topic_post = False
        if not self.topic:
            topic_type = self.cleaned_data['topic_type']
            if topic_type:
                topic_type = TopicType.objects.get(id=topic_type)
            else:
                topic_type = None
            topic = Topic(forum=self.forum,
                          posted_by=self.user,
                          subject=self.cleaned_data['subject'],
                          need_replay=self.cleaned_data['need_replay'],
                          need_reply_attachments=self.cleaned_data['need_reply_attachments'],
                          topic_type=topic_type,
                          )
            topic_post = True
            topic.save()
        else:
            topic = self.topic
        post = Post(topic=topic, posted_by=self.user, poster_ip=self.ip,
                    message=self.cleaned_data['message'], topic_post=topic_post)
        post.save()
        if topic_post:
            topic.post = post
            topic.save()
        attachments = self.cleaned_data['attachments']
        post.update_attachments(attachments)
        return post


class SignatureForm(forms.ModelForm):
    signature = forms.CharField(label=_('Message'), required=False,
            widget=forms.Textarea(attrs={'cols': '65', 'rows': '4'}))

    class Meta:
        model = LBForumUserProfile
        fields = ('signature',)

########NEW FILE########
__FILENAME__ = init_lbforum_user_profile
from django.core.management.base import BaseCommand

from lbforum.models import LBForumUserProfile
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Init LBForumUserProfile"
    
    def handle(self, **options):
        users = User.objects.all()
        for o in users:
            #LBForumUserProfile.objects.create(user=instance)
            try:
                o.lbforum_profile
            except LBForumUserProfile.DoesNotExist:
                LBForumUserProfile.objects.create(user=o)

########NEW FILE########
__FILENAME__ = lbforum_set_topic_post
from django.core.management.base import BaseCommand

from lbforum.models import Topic


class Command(BaseCommand):
    help = "update topic/post's base info."

    def handle(self, **options):
        topics = Topic.objects.all()
        for t in topics:
            post = t.posts.order_by('created_on').all()[0]
            t.post = post
            t.save()

########NEW FILE########
__FILENAME__ = update_posts
from django.core.management.base import BaseCommand

from lbforum.models import Post


class Command(BaseCommand):
    help = "update topic/post's base info."

    def handle(self, **options):
        posts = Post.objects.all()
        for o in posts:
            o.update_attachments_flag()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    depends_on = (
        ("attachments", "0001_initial"),
    )

    def forwards(self, orm):
        
        # Adding model 'Config'
        db.create_table('lbforum_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('lbforum', ['Config'])

        # Adding model 'Category'
        db.create_table('lbforum_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
            ('ordering', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('lbforum', ['Category'])

        # Adding model 'Forum'
        db.create_table('lbforum_forum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=110, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
            ('ordering', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lbforum.Category'])),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('num_topics', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('num_posts', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('last_post', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('lbforum', ['Forum'])

        # Adding model 'Topic'
        db.create_table('lbforum_topic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('forum', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lbforum.Forum'])),
            ('posted_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=999)),
            ('num_views', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('num_replies', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_reply_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_post', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('closed', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('sticky', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('lbforum', ['Topic'])

        # Adding model 'Post'
        db.create_table('lbforum_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lbforum.Topic'])),
            ('posted_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('poster_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
            ('topic_post', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('edited_by', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('lbforum', ['Post'])

        # Adding M2M table for field attachments on 'Post'
        db.create_table('lbforum_post_attachments', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('post', models.ForeignKey(orm['lbforum.post'], null=False)),
            ('attachment', models.ForeignKey(orm['attachments.attachment'], null=False))
        ))
        db.create_unique('lbforum_post_attachments', ['post_id', 'attachment_id'])

        # Adding model 'LBForumUserProfile'
        db.create_table('lbforum_lbforumuserprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='lbforum_profile', unique=True, to=orm['auth.User'])),
            ('last_activity', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('userrank', self.gf('django.db.models.fields.CharField')(default='Junior Member', max_length=30)),
            ('last_posttime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('signature', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
        ))
        db.send_create_signal('lbforum', ['LBForumUserProfile'])


    def backwards(self, orm):
        
        # Deleting model 'Config'
        db.delete_table('lbforum_config')

        # Deleting model 'Category'
        db.delete_table('lbforum_category')

        # Deleting model 'Forum'
        db.delete_table('lbforum_forum')

        # Deleting model 'Topic'
        db.delete_table('lbforum_topic')

        # Deleting model 'Post'
        db.delete_table('lbforum_post')

        # Removing M2M table for field attachments on 'Post'
        db.delete_table('lbforum_post_attachments')

        # Deleting model 'LBForumUserProfile'
        db.delete_table('lbforum_lbforumuserprofile')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lbforum.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_topic_has_imgs__add_field_topic_has_attachments__add_f
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Topic.has_imgs'
        db.add_column('lbforum_topic', 'has_imgs', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'Topic.has_attachments'
        db.add_column('lbforum_topic', 'has_attachments', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'Topic.level'
        db.add_column('lbforum_topic', 'level', self.gf('django.db.models.fields.SmallIntegerField')(default=30), keep_default=False)

        # Adding field 'Post.has_imgs'
        db.add_column('lbforum_post', 'has_imgs', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'Post.has_attachments'
        db.add_column('lbforum_post', 'has_attachments', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Topic.has_imgs'
        db.delete_column('lbforum_topic', 'has_imgs')

        # Deleting field 'Topic.has_attachments'
        db.delete_column('lbforum_topic', 'has_attachments')

        # Deleting field 'Topic.level'
        db.delete_column('lbforum_topic', 'level')

        # Deleting field 'Post.has_imgs'
        db.delete_column('lbforum_post', 'has_imgs')

        # Deleting field 'Post.has_attachments'
        db.delete_column('lbforum_post', 'has_attachments')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lbforum.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '10'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_topic_need_replay__add_field_post_format
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Topic.need_replay'
        db.add_column('lbforum_topic', 'need_replay', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'Post.format'
        db.add_column('lbforum_post', 'format', self.gf('django.db.models.fields.CharField')(default='bbcode', max_length=20), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Topic.need_replay'
        db.delete_column('lbforum_topic', 'need_replay')

        # Deleting field 'Post.format'
        db.delete_column('lbforum_post', 'format')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lbforum.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '20'}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '30'}),
            'need_replay': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_topic_need_reply_attachments
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Topic.need_reply_attachments'
        db.add_column('lbforum_topic', 'need_reply_attachments', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Topic.need_reply_attachments'
        db.delete_column('lbforum_topic', 'need_reply_attachments')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lbforum.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '20'}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '30'}),
            'need_replay': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'need_reply_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = 0005_auto__add_topictype__add_field_topic_topic_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TopicType'
        db.create_table('lbforum_topictype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('forum', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lbforum.Forum'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=100, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal('lbforum', ['TopicType'])

        # Adding field 'Topic.topic_type'
        db.add_column('lbforum_topic', 'topic_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lbforum.TopicType'], null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'TopicType'
        db.delete_table('lbforum_topictype')

        # Deleting field 'Topic.topic_type'
        db.delete_column('lbforum_topic', 'topic_type_id')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lbforum.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '20'}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '30'}),
            'need_replay': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'need_reply_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'topic_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.TopicType']", 'null': 'True', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topictype': {
            'Meta': {'object_name': 'TopicType'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100', 'db_index': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_topic_post
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Topic.post'
        db.add_column('lbforum_topic', 'post', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='topics_', null=True, to=orm['lbforum.Post']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Topic.post'
        db.delete_column('lbforum_topic', 'post_id')


    models = {
        'attachments.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_img': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'org_filename': ('django.db.models.fields.TextField', [], {}),
            'suffix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
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
        'lbforum.category': {
            'Meta': {'ordering': "('-ordering', 'created_on')", 'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'lbforum.forum': {
            'Meta': {'ordering': "('ordering', '-created_on')", 'object_name': 'Forum'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_topics': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.lbforumuserprofile': {
            'Meta': {'object_name': 'LBForumUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lbforum_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'lbforum.post': {
            'Meta': {'ordering': "('-created_on',)", 'object_name': 'Post'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['attachments.Attachment']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '20'}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'poster_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['lbforum.Topic']"}),
            'topic_post': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topic': {
            'Meta': {'ordering': "('-last_reply_on',)", 'object_name': 'Topic'},
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'has_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_imgs': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '30'}),
            'need_replay': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'need_reply_attachments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'num_views': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topics_'", 'null': 'True', 'to': "orm['lbforum.Post']"}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'topic_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.TopicType']", 'null': 'True', 'blank': 'True'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lbforum.topictype': {
            'Meta': {'object_name': 'TopicType'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lbforum.Forum']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100', 'db_index': 'True'})
        }
    }

    complete_apps = ['lbforum']

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from base64 import b64encode, b64decode
import pickle

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.db.models import Sum
from django.conf import settings

from attachments.models import Attachment
from onlineuser.models import Online


class Config(models.Model):
    key = models.CharField(max_length=255)  # PK
    value = models.CharField(max_length=255)


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(default='')
    ordering = models.PositiveIntegerField(default=1)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ('-ordering', 'created_on')

    def __unicode__(self):
        return self.name


class Forum(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110)
    description = models.TextField(default='')
    ordering = models.PositiveIntegerField(default=1)
    category = models.ForeignKey(Category)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    num_topics = models.IntegerField(default=0)
    num_posts = models.IntegerField(default=0)

    last_post = models.CharField(max_length=255, blank=True)  # pickle obj

    class Meta:
        verbose_name = _("Forum")
        verbose_name_plural = _("Forums")
        ordering = ('ordering', '-created_on')

    def _count_nums_topic(self):
        return self.topic_set.all().count()

    def _count_nums_post(self):
        num_posts = self.topic_set.all().aggregate(Sum('num_replies'))
        return num_posts['num_replies__sum'] or 0

    def get_last_post(self):
        if not self.last_post:
            return {}
        return pickle.loads(b64decode(self.last_post))

    @models.permalink
    def get_absolute_url(self):
        return ('lbforum_forum', (), {'forum_slug': self.slug})

    def __unicode__(self):
        return self.name

    def update_state_info(self, commit=True):
        self.num_topics = self._count_nums_topic()
        self.num_posts = self._count_nums_post()
        if self.num_topics:
            last_post = Post.objects.all().filter(topic__forum=self)
            last_post = last_post.order_by('-created_on')[0]
            self.last_post = gen_last_post_info(last_post)
        else:
            self.last_post = ''
        if commit:
            self.save()


class TopicType(models.Model):
    forum = models.ForeignKey(Forum, verbose_name=_('Forum'))
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, default='')

    def __unicode__(self):
        return self.name


class TopicManager(models.Manager):
    def get_query_set(self):
        return super(TopicManager, self).get_query_set().filter(hidden=False)

LEVEL_CHOICES = (
    (30, _('Default')),
    (60, _('Distillate')),
)


class Topic(models.Model):
    forum = models.ForeignKey(Forum, verbose_name=_('Forum'))
    topic_type = models.ForeignKey(TopicType, verbose_name=_('Topic Type'),
            blank=True, null=True)
    posted_by = models.ForeignKey(User)

    #TODO ADD TOPIC POST.
    post = models.ForeignKey('Post', verbose_name=_('Post'),
                             related_name='topics_', blank=True, null=True)
    subject = models.CharField(max_length=999)
    num_views = models.IntegerField(default=0)
    num_replies = models.PositiveSmallIntegerField(default=0)  # posts...
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    last_reply_on = models.DateTimeField(auto_now_add=True)
    last_post = models.CharField(max_length=255, blank=True)  # pickle obj

    has_imgs = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    need_replay = models.BooleanField(default=False)  # need_reply :-)
    need_reply_attachments = models.BooleanField(default=False)

    #Moderation features
    closed = models.BooleanField(default=False)
    sticky = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    level = models.SmallIntegerField(choices=LEVEL_CHOICES, default=30)

    objects = TopicManager()

    class Meta:
        ordering = ('-last_reply_on',)  # '-sticky'
        get_latest_by = ('created_on')
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")

    def __unicode__(self):
        return self.subject

    def count_nums_replies(self):
        return self.posts.all().count()

    @models.permalink
    def get_absolute_url(self):
        return ('lbforum_topic', (), {'topic_id': self.id})

    def get_last_post(self):
        if not self.last_post:
            return {}
        return pickle.loads(b64decode(self.last_post))

    def has_replied(self, user):
        if user.is_anonymous():
            return False
        return Post.objects.filter(posted_by=user, topic=self).count()

    def update_state_info(self, commit=True):
        self.num_replies = self.count_nums_replies()
        last_post = self.posts.order_by('-created_on')[0]
        self.last_post = gen_last_post_info(last_post)
        self.save()
        if commit:
            self.save()

FORMAT_CHOICES = (
    ('bbcode', _('BBCode')),
    ('html', _('Html')),
)


class Post(models.Model):
    topic = models.ForeignKey(Topic, verbose_name=_('Topic'), related_name='posts')
    posted_by = models.ForeignKey(User)
    poster_ip = models.IPAddressField()
    topic_post = models.BooleanField(default=False)

    format = models.CharField(max_length=20, default='bbcode')  # user name
    message = models.TextField()
    attachments = models.ManyToManyField(Attachment, blank=True)

    has_imgs = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    edited_by = models.CharField(max_length=255, blank=True)  # user name

    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        ordering = ('-created_on',)
        get_latest_by = ('created_on', )

    def __unicode__(self):
        return self.message[:80]

    def subject(self):
        if self.topic_post:
            return _('Topic: %s') % self.topic.subject
        return _('Re: %s') % self.topic.subject

    def file_attachments(self):
        return self.attachments.filter(is_img=False)

    def img_attachments(self):
        return self.attachments.filter(is_img=True)

    def update_attachments_flag(self):
        self.has_attachments = self.file_attachments().count() > 0
        self.has_imgs = self.img_attachments().count() > 0
        self.save()
        if self.topic_post:
            t = self.topic
            t.has_attachments = self.has_attachments
            t.has_imgs = self.has_imgs
            t.save()

    def update_attachments(self, attachment_ids):
        self.attachments.clear()
        for attachment_id in attachment_ids:
            try:
                attachment = Attachment.objects.get(pk=attachment_id)
            except:
                continue
            attachment.activated = True
            attachment.save()
            self.attachments.add(attachment)
        self.update_attachments_flag()

    @models.permalink
    def get_absolute_url(self):
        return ('lbforum_post', (), {'post_id': self.pk})

    def get_absolute_url_ext(self):
        topic = self.topic
        post_idx = topic.posts.filter(created_on__lte=self.created_on).count()
        page = (post_idx - 1) / settings.CTX_CONFIG['TOPIC_PAGE_SIZE'] + 1
        return '%s?page=%s#p%s' % (topic.get_absolute_url(), page, self.pk)


class LBForumUserProfile(models.Model):
    user = models.OneToOneField(User, related_name='lbforum_profile',
                                verbose_name=_('User'))
    last_activity = models.DateTimeField(auto_now_add=True)
    userrank = models.CharField(max_length=30, default="Junior Member")
    last_posttime = models.DateTimeField(auto_now_add=True)
    signature = models.CharField(max_length=1000, blank=True)

    def __unicode__(self):
        return self.user.username

    def get_total_posts(self):
        return self.user.post_set.count()

    def get_absolute_url(self):
        return self.user.get_absolute_url()


#### do smoe connect ###
def gen_last_post_info(post):
    last_post = {
        'posted_by': post.posted_by.username,
        'update': post.created_on
    }
    return b64encode(pickle.dumps(last_post, pickle.HIGHEST_PROTOCOL))


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        LBForumUserProfile.objects.create(user=instance)


def update_topic_on_post(sender, instance, created, **kwargs):
    if created:
        t = instance.topic
        t.last_post = gen_last_post_info(instance)
        t.last_reply_on = instance.created_on
        t.num_replies += 1
        t.save()
        p = instance.posted_by.lbforum_profile
        p.last_posttime = instance.created_on
        p.save()


def update_forum_on_post(sender, instance, created, **kwargs):
    if created:
        instance.topic.forum.last_post = gen_last_post_info(instance)
        instance.topic.forum.num_posts += 1
        instance.topic.forum.save()


def update_forum_on_topic(sender, instance, created, **kwargs):
    if created:
        instance.forum.num_topics += 1
        instance.forum.save()


def update_user_last_activity(sender, instance, created, **kwargs):
    if instance.user:
        p, created = LBForumUserProfile.objects.get_or_create(
            user=instance.user)

        p.last_activity = instance.updated_on
        p.save()

post_save.connect(create_user_profile, sender=User)
post_save.connect(update_topic_on_post, sender=Post)
post_save.connect(update_forum_on_post, sender=Post)
post_save.connect(update_forum_on_topic, sender=Topic)
post_save.connect(update_user_last_activity, sender=Online)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

STICKY_TOPIC_POST = getattr(settings, 'LBF_STICKY_TOPIC_POST', False)
LAST_TOPIC_NO_INDEX = getattr(settings, 'LBF_LAST_TOPIC_NO_INDEX', False)

########NEW FILE########
__FILENAME__ = bbcode
# -*- coding: UTF-8 -*-
import re

from django import template
from django.utils.translation import ugettext

from postmarkup import create, QuoteTag, TagBase, PostMarkup, strip_bbcode

from attachments.models import Attachment

from helper import clean_html

register = template.Library()

#bbcode
_RE_ATTACH = r"""\[attach\](\d*?)\[/attach\]"""
_RE_ATTACHIMG = r"""\[attachimg\](\d*?)\[/attachimg\]"""


class ReplyViewTag(TagBase):

    def render_open(self, parser, node_index):
        tag_data = parser.tag_data
        if not tag_data.get('has_replied', False):
            self.skip_contents(parser)
            contents = self.get_contents(parser)
            hide_attach = tag_data.get('hide_attachs', [])
            hide_attach.extend(re.findall(_RE_ATTACH, contents))
            hide_attach.extend(re.findall(_RE_ATTACHIMG, contents))
            tag_data['hide_attachs'] = hide_attach
            return '<p class="need-reply">%s</p>' % ugettext("to see the content, user must reply first.")
        return ""


class LBQuoteTag(QuoteTag):

    def render_open(self, parser, node_index):
        if self.params:
            return u'<div class="quotebox"><cite>%s:</cite><blockquote><p>' % (PostMarkup.standard_replace(self.params))
        else:
            return u'<div class="quotebox"><blockquote><p>'

    def render_close(self, parser, node_index):
        return u"</p></blockquote></div>"


class AttachTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):
        contents = self.get_contents(parser)
        self.skip_contents(parser)
        try:
            attach = Attachment.objects.get(pk=contents)
        except:
            return u'[attach]%s[/attach]' % contents
            pass
        return u'<a title="%s" href="%s">%s</a>' % (attach.description,
                attach.file.url, attach.org_filename)


class AttachImgTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):
        contents = self.get_contents(parser)
        self.skip_contents(parser)
        try:
            attach = Attachment.objects.get(pk=contents)
        except:
            return u'[attachimg]%s[/attachimg]' % contents
            pass
        return u'<img title="%s" src="%s"/>' % (attach.description,
                attach.file.url)


class HTMLTag(TagBase):

    def render_open(self, parser, node_index):
        contents = self.get_contents(parser)
        contents = strip_bbcode(contents)
        self.skip_contents(parser)
        return clean_html(contents)


_postmarkup = create(use_pygments=False, annotate_links=False)
_postmarkup.tag_factory.add_tag(LBQuoteTag, 'quote')
_postmarkup.tag_factory.add_tag(ReplyViewTag, 'replyview')
_postmarkup.tag_factory.add_tag(ReplyViewTag, 'hide')
_postmarkup.tag_factory.add_tag(AttachTag, 'attach')
_postmarkup.tag_factory.add_tag(AttachImgTag, 'attachimg')
_postmarkup.tag_factory.add_tag(HTMLTag, 'html')

########NEW FILE########
__FILENAME__ = helper
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from BeautifulSoup import BeautifulSoup, NavigableString
from django.conf import settings

acceptable_elements = [
    'a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
    'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
    'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em',
    'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
    'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol',
    'p', 'pre', 'q', 's', 'samp', 'small', 'span', 'strike',
    'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
    'thead', 'tr', 'tt', 'u', 'ul', 'var']

acceptable_attributes = [
    'abbr', 'accept', 'accept-charset', 'accesskey',
    'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
    'char', 'charoff', 'charset', 'checked', 'cite', 'clear', 'cols',
    'colspan', 'color', 'compact', 'coords', 'datetime', 'dir',
    'enctype', 'for', 'headers', 'height', 'href', 'hreflang', 'hspace',
    'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'method',
    'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt',
    'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'shape', 'size',
    'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
    'usemap', 'valign', 'value', 'vspace', 'width', 'style']

acceptable_elements.extend(getattr(settings, 'HTML_SAFE_TAGS', []))
acceptable_attributes.extend(getattr(settings, 'HTML_SAFE_ATTRS', []))
acceptable_elements = set(acceptable_elements) - set(getattr(settings, 'HTML_UNSAFE_TAGS', []))
acceptable_attributes = set(acceptable_attributes) - set(getattr(settings, 'HTML_UNSAFE_ATTRS', []))


def clean_html(fragment):
    soup = BeautifulSoup(fragment.strip())

    def cleanup(soup):
        for tag in soup:
            if not isinstance(tag, NavigableString):
                if tag.name not in acceptable_elements:
                    tag.extract()
                else:
                    for attr in tag._getAttrMap().keys():
                        if attr not in acceptable_attributes:
                            del tag[attr]
                    cleanup(tag)
    cleanup(soup)
    return unicode(soup)

########NEW FILE########
__FILENAME__ = lbforum_filters
# -*- coding: UTF-8 -*-
import datetime

from django import template
from django.template.defaultfilters import timesince as _timesince
from django.template.defaultfilters import date as _date
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.utils.tzinfo import LocalTimezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from bbcode import _postmarkup

register = template.Library()


@register.filter
def bbcode(s):
    if not s:
        return ""
    return _postmarkup(s,  # cosmetic_replace=False,
            auto_urls=getattr(settings, 'BBCODE_AUTO_URLS', True))


@register.filter
def form_all_error(form):
    errors = []
    global_error = form.errors.get('__all__', '')
    if global_error:
        global_error = global_error.as_text()
    for name, field in form.fields.items():
        e = form.errors.get(name, '')
        if e:
            errors.append((field.label, force_unicode(e), ))
    return mark_safe(u'<ul class="errorlist">%s %s</ul>' % (global_error,
        ''.join([u'<li>%s%s</li>' % (k, v) for k, v in errors])))


@register.filter
def topic_state(topic):
    c = []
    if topic.closed:
        c.append('closed')
    elif topic.sticky:
        c.append('sticky')
    else:
        c.append('normal')
    return ' '.join(c)


@register.filter
def post_style(forloop):
    styles = ''
    if forloop['first']:
        styles = 'firstpost topicpost'
    else:
        styles = 'replypost'
    if forloop['last']:
        styles += ' lastpost'
    return styles


@register.filter
def online(user):
    try:
        if user.online.online():
            return _('Online')
    except:
        pass
    return _('Offline')


@register.filter
def lbtimesince(d, now=None):
    # Convert datetime.date to datetime.datetime for comparison.
    if not d:
        return ''
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)
    if not now:
        if d.tzinfo:
            now = datetime.datetime.now(LocalTimezone(d))
        else:
            now = datetime.datetime.now()
    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since // (60 * 60 * 24) < 3:
        return _("%s ago") % _timesince(d)
    return _date(d, "Y-m-d H:i")

########NEW FILE########
__FILENAME__ = lbforum_tags
# -*- coding: UTF-8 -*-
from django import template
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from bbcode import _postmarkup

from djangohelper.decorators import basictag

register = template.Library()


@register.tag
@basictag(takes_context=True)
def bbcode(context, s, has_replied=False):
    if not s:
        return ""
    tag_data = {'has_replied': has_replied}
    html = _postmarkup(s,  # cosmetic_replace=False,
            tag_data=tag_data,
            auto_urls=getattr(settings, 'BBCODE_AUTO_URLS', True))
    context['hide_attachs'] = tag_data.get('hide_attachs', [])
    return html


@register.simple_tag
def forum_url(forum, topic_type, topic_type2):
    args = [forum.slug, topic_type, topic_type2]
    args = [e for e in args if e]
    return reverse('lbforum_forum', args=args)


@register.simple_tag
def show_attach(attach, post, has_replied, hide_attachs):
    if not has_replied and post.topic_post and \
            (post.topic.need_reply_attachments or hide_attachs.count(u"%s" % attach.pk)):
        return """<a href="#" onclick="alert('%s');return false;">%s</a>""" % \
                (_("reply to see the attachments"), attach.org_filename)
    else:
        return """<a href="%s">%s</a>""" % (attach.file.url, attach.org_filename)


@register.simple_tag
def page_item_idx(page_obj, forloop):
    return page_obj.start_index() + forloop['counter0']


@register.simple_tag
def page_range_info(page_obj):
    paginator = page_obj.paginator
    if paginator.num_pages == 1:
        return paginator.count
    return str(page_obj.start_index()) + ' ' + 'to' + ' ' + \
            str(page_obj.end_index()) + ' ' + 'of' + ' ' + str(page_obj.paginator.count)

DEFAULT_PAGINATION = getattr(settings, 'PAGINATION_DEFAULT_PAGINATION', 20)
DEFAULT_WINDOW = getattr(settings, 'PAGINATION_DEFAULT_WINDOW', 4)


@register.inclusion_tag('lbforum/post_paginate.html', takes_context=True)
def post_paginate(context, count, paginate_by=DEFAULT_PAGINATION, window=DEFAULT_WINDOW):
    if not isinstance(paginate_by, int):
        paginate_by = template.Variable(paginate_by)
    if not isinstance(window, int):
        window = template.Variable(paginate_by)
    page_count = count / paginate_by
    if count % paginate_by > 0:
        page_count += 1
    context['page_count'] = page_count
    pages = []
    if page_count == 1:
        pass
    elif window >= page_count:
        pages = [e + 1 for e in range(page_count)]
    else:
        pages = [e + 1 for e in range(window - 1)]
    context['pages'] = pages
    context['window'] = window
    return context

########NEW FILE########
__FILENAME__ = lbforum_widget_tags
from django.template import Library
from django.contrib.auth.models import User

from lbforum.models import Topic, Category, Post

register = Library()


@register.inclusion_tag('lbforum/tags/dummy.html')
def lbf_categories_and_forums(forum=None, template='lbforum/widgets/categories_and_forums.html'):
    return {'template': template,
            'forum': forum,
            'categories': Category.objects.all()}


@register.inclusion_tag('lbforum/tags/dummy.html')
def lbf_status(template='lbforum/widgets/lbf_status.html'):
    return {'template': template,
            'total_topics': Topic.objects.count(),
            'total_posts': Post.objects.count(),
            'total_users': User.objects.count(),
            'last_registered_user': User.objects.order_by('-date_joined')[0]}

########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF-8 -*-
from django.test import TestCase
from django.core.urlresolvers import reverse


class ViewsBaseCase(TestCase):
    fixtures = ['test_lbforum.json']


class ViewsSimpleTest(ViewsBaseCase):

    def test_index(self):
        resp = self.client.get(reverse('lbforum_index'))
        self.assertEqual(resp.status_code, 200)

    def test_recent(self):
        resp = self.client.get(reverse('lbforum_recent'))
        self.assertEqual(resp.status_code, 200)

    def test_forum(self):
        resp = self.client.get(reverse('lbforum_forum', args=("notexistforum", )))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('lbforum_forum', args=("forum", )))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('lbforum_forum', args=("forum", "topictype", )))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('lbforum_forum', args=("forum", "topictype", "good")))
        self.assertEqual(resp.status_code, 200)

    def test_topic(self):
        resp = self.client.get(reverse('lbforum_topic', args=(1, )))
        self.assertEqual(resp.status_code, 200)

    def test_lang_js(self):
        resp = self.client.get(reverse('lbforum_lang_js'))
        self.assertEqual(resp.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from lbforum import views, accountviews

forum_patterns = patterns(
    '',
    url(r'^(?P<forum_slug>[\w-]+)/$', views.forum, name='lbforum_forum'),
    url(r'^(?P<forum_slug>[\w-]+)/(?P<topic_type>[\w-]+)/$',
        views.forum, name='lbforum_forum'),
    url(r'^(?P<forum_slug>[\w-]+)/(?P<topic_type>[\w-]+)/(?P<topic_type2>[\w-]+)/$',
        views.forum, name='lbforum_forum'),
)

topic_patterns = patterns(
    '',
    url('^(?P<topic_id>\d+)/$', views.topic, name='lbforum_topic'),
    url('^(?P<topic_id>\d+)/delete/$', views.delete_topic,
        name='lbforum_delete_topic'),
    url('^(?P<topic_id>\d+)/update_topic_attr_as_not/(?P<attr>[\w-]+)/$',
        views.update_topic_attr_as_not,
        name='lbforum_update_topic_attr_as_not'),
    url('^new/(?P<forum_id>\d+)/$', views.new_post, name='lbforum_new_topic'),
)

post_patterns = patterns(
    '',
    url('^(?P<post_id>\d+)/$', views.post, name='lbforum_post'),
    url('^(?P<post_id>\d+)/edit/$', views.edit_post, name='lbforum_post_edit'),
    url('^(?P<post_id>\d+)/delete/$', views.delete_post,
        name='lbforum_post_delete'),
)

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='lbforum_index'),
    url(r'^recent/$', views.recent, name='lbforum_recent'),
    (r'^forum/', include(forum_patterns)),
    (r'^topic/', include(topic_patterns)),
    url('^reply/new/(?P<topic_id>\d+)/$', views.new_post,
        name='lbforum_new_replay'),
    (r'^post/', include(post_patterns)),
    url('^user/(?P<user_id>\d+)/topics/$', views.user_topics,
        name='lbforum_user_topics'),
    url('^user/(?P<user_id>\d+)/posts/$', views.user_posts,
        name='lbforum_user_posts'),
    url(r'^lang.js$', TemplateView.as_view(template_name='lbforum/lang.js'),
        name='lbforum_lang_js'),
    url('^markitup_preview/$', views.markitup_preview,
        name='markitup_preview'),
)

urlpatterns += patterns(
    '',
    url(r'^account/$', login_required(accountviews.profile),
        name='lbforum_account_index'),
    url(r'^account/signature/$', accountviews.signature,
        name='lbforum_signature'),
    url(r'^user/(?P<user_id>\d+)/$', login_required(accountviews.profile),
        name='lbforum_user_profile'),
)

urlpatterns += patterns(
    'simpleavatar.views',
    url('^account/avatar/change/$', 'change',
        {'template_name': 'lbforum/account/avatar/change.html'},
        name='lbforum_avatar_change'),
    (r'^accounts/avatar/', include('simpleavatar.urls')),
)

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
#from django.contrib import messages

from forms import EditPostForm, NewPostForm, ForumForm
from models import Topic, Forum, Post
import settings as lbf_settings


def index(request, template_name="lbforum/index.html"):
    ctx = {}
    if lbf_settings.LAST_TOPIC_NO_INDEX:
        ctx['topics'] = Topic.objects.all().order_by('-last_reply_on')[:20]
    return render(request, template_name, ctx)


def recent(request, template_name="lbforum/recent.html"):
    ctx = {}
    ctx['topics'] = Topic.objects.all().order_by('-last_reply_on')
    ctx['topics'] = ctx['topics'].select_related()

    return render(request, template_name, ctx)


def forum(request, forum_slug, topic_type='', topic_type2='',
        template_name="lbforum/forum.html"):
    forum = get_object_or_404(Forum, slug=forum_slug)
    topics = forum.topic_set.all()
    if topic_type and topic_type != 'good':
        topic_type2 = topic_type
        topic_type = ''
    if topic_type == 'good':
        topics = topics.filter(level__gt=30)
        #topic_type = _("Distillate District")
    if topic_type2:
        topics = topics.filter(topic_type__slug=topic_type2)
    order_by = request.GET.get('order_by', '-last_reply_on')
    topics = topics.order_by('-sticky', order_by).select_related()
    form = ForumForm(request.GET)
    ext_ctx = {'form': form, 'forum': forum, 'topics': topics,
            'topic_type': topic_type, 'topic_type2': topic_type2}
    return render(request, template_name, ext_ctx)


def topic(request, topic_id, template_name="lbforum/topic.html"):
    topic = get_object_or_404(Topic, id=topic_id)
    topic.num_views += 1
    topic.save()
    posts = topic.posts
    if lbf_settings.STICKY_TOPIC_POST:  # sticky topic post
        posts = posts.filter(topic_post=False)
    posts = posts.order_by('created_on').select_related()
    ext_ctx = {'topic': topic, 'posts': posts}
    ext_ctx['has_replied'] = topic.has_replied(request.user)
    return render(request, template_name, ext_ctx)


def post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return HttpResponseRedirect(post.get_absolute_url_ext())


@csrf_exempt
def markitup_preview(request, template_name="lbforum/markitup_preview.html"):
    return render(request, template_name, {'message': request.POST['data']})


@login_required
def new_post(request, forum_id=None, topic_id=None, form_class=NewPostForm,
        template_name='lbforum/post.html'):
    qpost = topic = forum = first_post = preview = None
    post_type = _('topic')
    topic_post = True
    if forum_id:
        forum = get_object_or_404(Forum, pk=forum_id)
    if topic_id:
        post_type = _('reply')
        topic_post = False
        topic = get_object_or_404(Topic, pk=topic_id)
        forum = topic.forum
        first_post = topic.posts.order_by('created_on').select_related()[0]
    if request.method == "POST":
        form = form_class(request.POST, user=request.user, forum=forum,
                topic=topic, ip=request.META['REMOTE_ADDR'])
        preview = request.POST.get('preview', '')
        if form.is_valid() and request.POST.get('submit', ''):
            post = form.save()
            if topic:
                return HttpResponseRedirect(post.get_absolute_url_ext())
            else:
                return HttpResponseRedirect(reverse("lbforum_forum",
                                                    args=[forum.slug]))
    else:
        initial = {}
        qid = request.GET.get('qid', '')
        if qid:
            qpost = get_object_or_404(Post, id=qid)
            initial['message'] = "[quote=%s]%s[/quote]"
            initial['message'] %= (qpost.posted_by.username, qpost.message)
        form = form_class(initial=initial, forum=forum)
    ext_ctx = {
        'forum': forum,
        'form': form,
        'topic': topic,
        'first_post': first_post,
        'post_type': post_type,
        'preview': preview
    }
    ext_ctx['unpublished_attachments'] = request.user.attachment_set.filter(activated=False)
    ext_ctx['is_new_post'] = True
    ext_ctx['topic_post'] = topic_post
    ext_ctx['session_key'] = request.session.session_key
    return render(request, template_name, ext_ctx)


@login_required
def edit_post(request, post_id, form_class=EditPostForm,
              template_name="lbforum/post.html"):
    preview = None
    post_type = _('reply')
    edit_post = get_object_or_404(Post, id=post_id)
    if not (request.user.is_staff or request.user == edit_post.posted_by):
        return HttpResponse(ugettext('no right'))
    if edit_post.topic_post:
        post_type = _('topic')
    if request.method == "POST":
        form = form_class(instance=edit_post, user=request.user,
                          data=request.POST)
        preview = request.POST.get('preview', '')
        if form.is_valid() and request.POST.get('submit', ''):
            edit_post = form.save()
            return HttpResponseRedirect('../')
    else:
        form = form_class(instance=edit_post)
    ext_ctx = {
        'form': form,
        'post': edit_post,
        'topic': edit_post.topic,
        'forum': edit_post.topic.forum,
        'post_type': post_type,
        'preview': preview
    }
    ext_ctx['unpublished_attachments'] = request.user.attachment_set.filter(activated=False)
    ext_ctx['topic_post'] = edit_post.topic_post
    ext_ctx['session_key'] = request.session.session_key
    return render(request, template_name, ext_ctx)


@login_required
def user_topics(request, user_id,
                template_name='lbforum/account/user_topics.html'):
    view_user = User.objects.get(pk=user_id)
    topics = view_user.topic_set.order_by('-created_on').select_related()
    context = {
        'topics': topics,
        'view_user': view_user
    }

    return render(request, template_name, context)



@login_required
def user_posts(request, user_id,
               template_name='lbforum/account/user_posts.html'):
    view_user = User.objects.get(pk=user_id)
    posts = view_user.post_set.order_by('-created_on').select_related()
    context = {
        'posts': posts,
        'view_user': view_user
    }
    return render(request, template_name, context)



@login_required
def delete_topic(request, topic_id):
    if not request.user.is_staff:
        #messages.error(_('no right'))
        return HttpResponse(ugettext('no right'))
    topic = get_object_or_404(Topic, id=topic_id)
    forum = topic.forum
    topic.delete()
    forum.update_state_info()
    return HttpResponseRedirect(reverse("lbforum_forum", args=[forum.slug]))


@login_required
def delete_post(request, post_id):
    if not request.user.is_staff:
        return HttpResponse(ugettext('no right'))
    post = get_object_or_404(Post, id=post_id)
    topic = post.topic
    post.delete()
    topic.update_state_info()
    topic.forum.update_state_info()
    #return HttpResponseRedirect(request.path)
    return HttpResponseRedirect(reverse("lbforum_topic", args=[topic.id]))


@login_required
def update_topic_attr_as_not(request, topic_id, attr):
    if not request.user.is_staff:
        return HttpResponse(ugettext('no right'))
    topic = get_object_or_404(Topic, id=topic_id)
    if attr == 'sticky':
        topic.sticky = not topic.sticky
    elif attr == 'close':
        topic.closed = not topic.closed
    elif attr == 'hide':
        topic.hidden = not topic.hidden
    elif attr == 'distillate':
        topic.level = 30 if topic.level >= 60 else 60
    topic.save()
    if topic.hidden:
        return HttpResponseRedirect(reverse("lbforum_forum",
                                            args=[topic.forum.slug]))
    else:
        return HttpResponseRedirect(reverse("lbforum_topic", args=[topic.id]))

#Feed...
#Add Post
#Add Topic

########NEW FILE########
