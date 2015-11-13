__FILENAME__ = admin
from django.contrib import admin

from models import Event, Topic
from models import Favorite, Vote
from models import Post

class Event_Admin(admin.ModelAdmin):
    list_display = ('name', 'begin_time')
    list_filter = ['begin_time']
    raw_id_fields = ('participants', 'appearances', 'last_modified_by')
    ordering = ['-id']

admin.site.register(Event, Event_Admin)

class Topic_Admin(admin.ModelAdmin):
    list_display = ('name', 'author', 'total_votes', 'in_event', 'accepted')
    list_filter = ['in_event', 'accepted']
    raw_id_fields = ('author', 'in_event', 'last_modified_by', )
    ordering = ['-id']
    
admin.site.register(Topic, Topic_Admin)

class Post_Admin(admin.ModelAdmin):
    list_display = ('title','post_name')
    date_hierarchy='created_at'
    raw_id_fields = ('created_by', )
    ordering = ['-id']

admin.site.register(Post,Post_Admin)

class Vote_Fav_Admin(admin.ModelAdmin):
    raw_id_fields = ('user', )

admin.site.register(Vote, Vote_Fav_Admin)
admin.site.register(Favorite, Vote_Fav_Admin)



########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings # import the settings file

def global_settings_injection(context):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {
        'ANALYTICS_ID': settings.ANALYTICS_ID,
        'COMMENT_SYSTEM': settings.COMMENT_SYSTEM,
        'SITE_URL': settings.SITE_URL,
        'DISQUS_BRANCH_ID': settings.DISQUS_BRANCH_ID,
    }


########NEW FILE########
__FILENAME__ = feeds
# -*- encoding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.syndication.views import Feed

from apps.core.models import Event, Topic, Post

import settings

class Events_Feed(Feed):

    title = "Beijing OpenParty 最新活动列表"
    link = settings.SITE_URL + "/event"
    author_link = link
    description = "发布 Beijing OpenParty 的最新活动信息"

    def root_attributes(self):
        attrs = super(Events_Feed, self).root_attributes()
        attrs['atom:links'] = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
        return attrs

    def items(self):
        return Event.objects.order_by('-begin_time')

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return settings.SITE_URL + item.get_absolute_url()

class Topics_Feed(Feed):

    title = "Beijing OpenParty 最新话题列表"
    link = settings.SITE_URL + "/topic"
    description = "发布 Beijing OpenParty 的最新活动中的话题信息"

    def items(self):
        return Topic.objects.all().order_by('-in_event__begin_time','-accepted', '-total_votes')

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return settings.SITE_URL + item.get_absolute_url()

class Posts_Feed(Feed):

    title = "Beijing OpenParty 最新新闻"
    link = settings.SITE_URL + "/post"
    description = "Beijing OpenParty 最新新闻"

    def items(self):
        return Post.objects.all().order_by("-created_at")

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.content

    def item_link(self, item):
        return settings.SITE_URL + item.get_absolute_url()


########NEW FILE########
__FILENAME__ = article_form
from apps.core.models import Topic
from django.forms import ModelForm, Textarea


class ArticleForm(ModelForm):
    class Meta:
        model   = Topic
        fields  = ('name', 'description', 'content', 'in_event')
        widgets = {
                    'description': Textarea(attrs={'cols': 60, 'rows': 5}),
                    'content': Textarea(attrs={'cols': 60, 'rows': 20,'class':'with_tinymce'})
        }

########NEW FILE########
__FILENAME__ = event_checkin_form
# -*- coding: utf-8 -*-
from django import forms
from django.core.validators import validate_email
from apps.member.models import Member


class EventCheckinForm(forms.Form):
    email = forms.EmailField(label=u'请填写您注册使用的Email', required=True, widget=forms.TextInput(attrs={'tabindex': '1'}))
    member = None
    
    def clean_email(self):
        email=self.cleaned_data.get('email','')
        validate_email(email)
        return email
    
    def clean(self):
        super(EventCheckinForm, self).clean()
        email = self.cleaned_data.get('email','')
        member = Member.objects.find_by_email(email)
        if member:
            self.member = member
        else:
            raise forms.ValidationError(u'您输入的邮件地址与密码不匹配或者帐号还不存在，请您重试')
        return self.cleaned_data

    def checkin(self, event):
        if self.is_valid():
            if self.member in event.appearances.all():
                raise forms.ValidationError(u'嘿，您已经签过到了，请下一位签到吧！')
            else:
                print self.member
                print self.member.id
                event.appearances.add(self.member)
            return True
        else:
            return False

########NEW FILE########
__FILENAME__ = crawl_google_doc_images
#!/usr/bin/env python
# encoding: utf-8
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from lxml import html
from lxml.cssselect import CSSSelector
from hashlib import md5
import urllib2
import traceback
import os

from apps.core.models import Post

class Command(BaseCommand):

    url_image_mapping_file = 'url_image_mapping_file.out'
    image_folder = 'post_images'
    m = md5()
    mapping = {}

    def handle(self, *args, **options):
        if len(args) == 0:
            self._usage()
            return
        
        if 'down' == args[0]:
            self.download()
        elif 'replace' == args[0]:
            self.replace()
        else:
            self._usage()
            
    def _usage(self):
        print 'Usage: ./manage.py crawl_google_doc_images [down|replace]'
    
    def replace(self):
        with open(self.url_image_mapping_file) as f:
            for line in f:
                line = line.strip()
                if not line.startswith('Failed'):
                    url, filename = line.split('->')
                    self.mapping[url.strip()] = filename.strip()

        posts = Post.objects.all()

        for post in posts:
            page_element = html.fromstring(post.content)
            image_selector = CSSSelector('img')
            images = image_selector(page_element)
            for image in images:
                url = image.attrib['src'].strip()
                if url in self.mapping:
                    image.attrib['src'] = "/post_images/%s" % self.mapping[url]
                    print 'replace %s with %s' % (url, self.mapping[url])
            post.content = html.tostring(page_element)
            post.save()

    def download(self):
        posts = Post.objects.all()
        image_urls = set()

        for post in posts:
            page_element = html.fromstring(post.content)
            image_selector = CSSSelector('img')
            images = image_selector(page_element)
            for image in images:
                image_urls.add(image.attrib['src'])

        with open(self.url_image_mapping_file, 'w') as f:
            for url in image_urls:
                if url.startswith('http'):
                    try:
                        filename = self.download_and_save(url)
                        self.mapping[url] = filename
                        f.write("%s -> %s" % (url, filename))
                        f.write('\n')
                    except:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print url, exc_type, exc_value, traceback.format_tb(exc_traceback)
                        f.write("Failed to download %s" % url.encode('utf-8'))
                        f.write('\n')

    def download_and_save(self, url, times=0):
        if times > 20:
            raise Exception('Failed to download after 19 reties')
        try:
            if url.startswith('https'):
                url = url.replace('https', 'http').encode('utf-8')
            req = urllib2.urlopen(url)
            mime = req.info().gettype()
            if mime == 'image/jpeg':
                ext = '.jpg'
            elif mime == 'image/gif':
                ext = '.gif'
            else:
                ext = ''
            self.m.update(url)
            filename = self.m.hexdigest() + ext
            self.save_image(filename, req.read())
            return filename
        except urllib2.HTTPError, urllib2.URLError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print url, exc_type, exc_value, traceback.format_tb(exc_traceback)
            return self.download_and_save(url, times + 1)
    
    def save_image(self, filename, content):
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)
        with open(os.path.join(self.image_folder, filename), 'w') as f:
            f.write(content)

########NEW FILE########
__FILENAME__ = sync_wordpress_posts
#!/usr/bin/env python
# encoding: utf-8
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
import MySQLdb
from collections import namedtuple

from apps.core.models import Post
from apps.member.models import Member


class Command(BaseCommand):
    row_structure = namedtuple('Row', 'id post_content post_title post_excerpt post_status post_name to_ping post_date post_modified guid post_author comment_count')

    def handle(self, *args, **options):
        print 'Start syncing'
        conn = MySQLdb.connect(host='localhost', user='root', db='openparty', use_unicode=True, charset='utf8')
        cursor = conn.cursor()
        sql = "SELECT id, post_content, post_title, post_excerpt, post_status, post_name, to_ping, post_date, post_modified, guid, post_author, comment_count FROM wp_posts WHERE post_type = 'post' AND post_status = 'publish'"
        cursor.execute(sql)
        rows = cursor.fetchall()
        cleverpig = self.find_cleverpig()
        synced = 0
        for row in rows:
            rs = self.row_structure._make(row)
            if self.should_sync(rs):
                post = Post(content=rs.post_content, content_type='html', title=rs.post_title, summary=rs.post_excerpt, status=10, post_name=rs.post_name, to_ping=rs.to_ping, created_at=rs.post_date, modified_at=rs.post_modified, guid=rs.guid, author='wp_%s' % rs.post_author, created_by=cleverpig, comment_count=rs.comment_count)
                post.save()
                print 'wp %s -> %s' % (rs.id, post.id)
                synced += 1

        print 'Synced %s wordpress posts' % synced
    
    def should_sync(self, rs):
        return not len(Post.objects.filter(guid=rs.guid)) # not duplicate
    
    def find_cleverpig(self):
        return Member.objects.get(id=6)


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Event'
        db.create_table('core_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, null=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, null=True, blank=True)),
            ('last_modified_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='event_last_modified', to=orm['member.Member'])),
            ('total_votes', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('total_favourites', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('begin_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=200)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('address', self.gf('django.db.models.fields.TextField')()),
            ('poster', self.gf('django.db.models.fields.CharField')(default='/media/upload/null-event-1.jpg', max_length=255, blank=True)),
        ))
        db.send_create_signal('core', ['Event'])

        # Adding M2M table for field participants on 'Event'
        db.create_table('core_event_participants', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('event', models.ForeignKey(orm['core.event'], null=False)),
            ('member', models.ForeignKey(orm['member.member'], null=False))
        ))
        db.create_unique('core_event_participants', ['event_id', 'member_id'])

        # Adding model 'Topic'
        db.create_table('core_topic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, null=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, null=True, blank=True)),
            ('last_modified_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topic_last_modified', to=orm['member.Member'])),
            ('total_votes', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('total_favourites', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topic_created', to=orm['member.Member'])),
            ('in_event', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='topic_shown_in', null=True, to=orm['core.Event'])),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=200)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('core', ['Topic'])

        # Adding model 'Vote'
        db.create_table('core_vote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('item_raw', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user_raw', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vote_created', to=orm['member.Member'])),
            ('rating', self.gf('django.db.models.fields.FloatField')(default=0)),
        ))
        db.send_create_signal('core', ['Vote'])

        # Adding model 'Favorite'
        db.create_table('core_favorite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('item_raw', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user_raw', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='favourites', to=orm['member.Member'])),
        ))
        db.send_create_signal('core', ['Favorite'])


    def backwards(self, orm):
        
        # Deleting model 'Event'
        db.delete_table('core_event')

        # Removing M2M table for field participants on 'Event'
        db.delete_table('core_event_participants')

        # Deleting model 'Topic'
        db.delete_table('core_topic')

        # Deleting model 'Vote'
        db.delete_table('core_vote')

        # Deleting model 'Favorite'
        db.delete_table('core_favorite')


    models = {
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
        'core.event': {
            'Meta': {'object_name': 'Event'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'begin_time': ('django.db.models.fields.DateTimeField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['member.Member']", 'symmetrical': 'False'}),
            'poster': ('django.db.models.fields.CharField', [], {'default': "'/media/upload/null-event-1.jpg'", 'max_length': '255', 'blank': 'True'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favourites'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'core.topic': {
            'Meta': {'object_name': 'Topic'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_created'", 'to': "orm['member.Member']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topic_shown_in'", 'null': 'True', 'to': "orm['core.Event']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.vote': {
            'Meta': {'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_created'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_topic_html__add_field_topic_content_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Topic.html'
        db.add_column('core_topic', 'html', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Adding field 'Topic.content_type'
        db.add_column('core_topic', 'content_type', self.gf('django.db.models.fields.CharField')(default='restructuredtext', max_length=30), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Topic.html'
        db.delete_column('core_topic', 'html')

        # Deleting field 'Topic.content_type'
        db.delete_column('core_topic', 'content_type')


    models = {
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
        'core.event': {
            'Meta': {'object_name': 'Event'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'begin_time': ('django.db.models.fields.DateTimeField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['member.Member']", 'symmetrical': 'False'}),
            'poster': ('django.db.models.fields.CharField', [], {'default': "'/media/upload/null-event-1.jpg'", 'max_length': '255', 'blank': 'True'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favourites'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'core.topic': {
            'Meta': {'object_name': 'Topic'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_created'", 'to': "orm['member.Member']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'restructuredtext'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topic_shown_in'", 'null': 'True', 'to': "orm['core.Event']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.vote': {
            'Meta': {'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_created'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0003_add_appearances_members_to_event
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding M2M table for field appearances on 'Event'
        db.create_table('core_event_appearances', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('event', models.ForeignKey(orm['core.event'], null=False)),
            ('member', models.ForeignKey(orm['member.member'], null=False))
        ))
        db.create_unique('core_event_appearances', ['event_id', 'member_id'])


    def backwards(self, orm):
        
        # Removing M2M table for field appearances on 'Event'
        db.delete_table('core_event_appearances')


    models = {
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
        'core.event': {
            'Meta': {'object_name': 'Event'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'appearances': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'arrived_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'begin_time': ('django.db.models.fields.DateTimeField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'joined_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'poster': ('django.db.models.fields.CharField', [], {'default': "'/media/upload/null-event-1.jpg'", 'max_length': '255', 'blank': 'True'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favourites'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'core.topic': {
            'Meta': {'object_name': 'Topic'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_created'", 'to': "orm['member.Member']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'restructuredtext'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topic_shown_in'", 'null': 'True', 'to': "orm['core.Event']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.vote': {
            'Meta': {'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_created'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0004_auto__add_post
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Post'
        db.create_table('core_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('content_type', self.gf('django.db.models.fields.CharField')(default='html', max_length=80)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('summary', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('post_name', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('to_ping', self.gf('django.db.models.fields.CharField')(max_length=512, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('guid', self.gf('django.db.models.fields.CharField')(max_length=512, blank=True)),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='post_created', to=orm['member.Member'])),
            ('comment_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('core', ['Post'])


    def backwards(self, orm):
        
        # Deleting model 'Post'
        db.delete_table('core_post')


    models = {
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
        'core.event': {
            'Meta': {'object_name': 'Event'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'appearances': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'arrived_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'begin_time': ('django.db.models.fields.DateTimeField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'joined_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'poster': ('django.db.models.fields.CharField', [], {'default': "'/media/upload/null-event-1.jpg'", 'max_length': '255', 'blank': 'True'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favourites'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'core.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'html'", 'max_length': '80'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post_created'", 'to': "orm['member.Member']"}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'post_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'to_ping': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        },
        'core.topic': {
            'Meta': {'object_name': 'Topic'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_created'", 'to': "orm['member.Member']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'html'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topic_shown_in'", 'null': 'True', 'to': "orm['core.Event']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.vote': {
            'Meta': {'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_created'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_post_created_at
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Post.created_at'
        db.alter_column('core_post', 'created_at', self.gf('django.db.models.fields.DateTimeField')())


    def backwards(self, orm):
        
        # Changing field 'Post.created_at'
        db.alter_column('core_post', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True))


    models = {
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
        'core.event': {
            'Meta': {'object_name': 'Event'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'appearances': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'arrived_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'begin_time': ('django.db.models.fields.DateTimeField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'joined_event'", 'symmetrical': 'False', 'to': "orm['member.Member']"}),
            'poster': ('django.db.models.fields.CharField', [], {'default': "'/media/upload/null-event-1.jpg'", 'max_length': '255', 'blank': 'True'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favourites'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'core.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'html'", 'max_length': '80'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'post_created'", 'to': "orm['member.Member']"}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'post_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'to_ping': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        },
        'core.topic': {
            'Meta': {'object_name': 'Topic'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_created'", 'to': "orm['member.Member']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.CharField', [], {'default': "'html'", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'topic_shown_in'", 'null': 'True', 'to': "orm['core.Event']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topic_last_modified'", 'to': "orm['member.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'total_favourites': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'total_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.vote': {
            'Meta': {'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_created'", 'to': "orm['member.Member']"}),
            'user_raw': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = event
# -*- coding: utf-8 -*-
from datetime import datetime

from django.db import models
from apps.member.models import Member
from django.core.urlresolvers import reverse

class EventManager(models.Manager):
    def next_event(self):
        '''定义next_event为获取当前未结束的活动或下次活动，减少逻辑复杂度'''
        latest_nonclosed_events = super(EventManager, self).get_query_set().filter(end_time__gte=datetime.now()).order_by("begin_time")
        if latest_nonclosed_events.count() >= 1:
            next_event = latest_nonclosed_events[0]
            next_event.css_class = 'hot'
            return next_event 
        else:
            return NullEvent()

    def upcoming_events(self):
        return super(EventManager, self).get_query_set().filter(begin_time__gte=datetime.now())

    def past_events(self):
        return super(EventManager, self).get_query_set().filter(end_time__lte=datetime.now())

class NullEventException(Exception):
    pass

class NullEvent(object):
    id = 0
    '''空的项目，保持接口的一致'''
    begin_time  = u'未定'
    end_time    = u'未定'
    description = u'本次活动正在计划中'
    content     = u'本次活动正在计划中'
    address     = u'东直门国华投资大厦11层'
    poster      = '/media/images/null.jpg'
    participants = set()
    
    css_class       = 'inactive'
    button_class    = 'disabled'
    
    def save():
        raise NullEventException()
    
    is_running  = False
    is_off      = False
    is_upcoming = True

class Event(models.Model):
    begin_time  = models.DateTimeField(u"开始时间", auto_now_add=False, auto_now=False, blank=False, null=False)
    end_time    = models.DateTimeField(u"结束时间", auto_now_add=False, auto_now=False, blank=False, null=False)
    description = models.TextField(u"简介", max_length=200, blank=False)
    content     = models.TextField(u"介绍", blank=False)
    address     = models.TextField(u"活动地点", blank=False)
    poster      = models.CharField(u"招贴画", default='/media/upload/null-event-1.jpg', blank=True, max_length=255)
    participants = models.ManyToManyField(Member, related_name='joined_%(class)s')
    appearances = models.ManyToManyField(Member, related_name='arrived_%(class)s')
    
    css_class       = ''
    button_class    = 'btn-primary'

    name = models.CharField("名称", max_length=255, blank=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=True, blank=True, null=True)
    last_modified = models.DateTimeField(auto_now_add=True, auto_now=True, blank=True, null=True)
    last_modified_by = models.ForeignKey(Member, related_name='%(class)s_last_modified')
    #aggrgated
    total_votes = models.PositiveIntegerField(default=0)
    total_favourites = models.PositiveIntegerField(default=0, editable=False)


    #englishname?
    #url_path = models.SlugField(_('url path'),max_length=250, db_index=True, blank=True)
    #Currently using ID in url

    @property
    def is_running(self):
        return datetime.now() > self.begin_time and datetime.now() < self.end_time

    @property
    def is_off(self):
        return datetime.now() > self.end_time

    @property
    def is_upcoming(self):
        return datetime.now() < self.begin_time

    def get_topics(self):
        return self.topic_shown_in.filter(accepted=True).all()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.begin_time)

    def get_absolute_url(self):
        return reverse("event", kwargs={"id":self.id})

    class Meta:
        app_label = 'core'

    objects = EventManager()

########NEW FILE########
__FILENAME__ = favorite
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from apps.member.models import Member

class Favorite(models.Model):
    ''' A Favourite action.''' 
    user = models.ForeignKey(Member, related_name='favourites',verbose_name=u"用户")

    content_type = models.ForeignKey(ContentType, limit_choices_to = {'model__in': ('topic', 'event', 'comment')})
    object_id = models.PositiveIntegerField()
    item = generic.GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField("创建日期",auto_now_add=True)
    # denorm
    item_raw = models.TextField('item raw',blank=True)
    user_raw = models.TextField('user raw',blank=True)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        return u'%s 收藏了 %s' % (self.user, self.item)

########NEW FILE########
__FILENAME__ = post
# -*- coding: utf-8 -*-
from django.db import models
from apps.member.models import Member
from django.db.models import signals
from django.core.urlresolvers import reverse

class PostStatus(object):
    DRAFT   = 0
    OPEN    = 10


class Post(models.Model):

    content = models.TextField(u'内容', blank=False) # post_content
    content_type = models.CharField(u'内容格式', blank=False, max_length=80, default='html')
    title = models.CharField(u'标题', blank=False, max_length=512) # post_title
    summary = models.TextField(u'摘要', blank=True) # post_excerpt
    status = models.IntegerField(blank=False, null=False, default=0) #post_status, 'open' -> 10
    post_name = models.CharField(u'短名称(引用url)', blank=True, max_length=256) # post_name
    to_ping = models.CharField(u'Ping文章', blank=True, max_length=512) # to_ping
    created_at = models.DateTimeField(u'创建时间', blank=False, null=False, auto_now_add=False) # post_date
    modified_at = models.DateTimeField(u'更新时间', blank=False, null=False, auto_now=True) # post_modified
    guid = models.CharField(u'Canonical网址', blank=True, max_length=512) # guid
    
    author = models.CharField(u'发表人', blank=False, max_length=256)
    created_by = models.ForeignKey(Member, related_name='post_created', verbose_name=u"创建人")
    comment_count = models.IntegerField(u'评论数量', blank=False, null=False, default=0) # comment_count
    
    post_status = PostStatus()
    
    def style_seed(self, range=4):
        return self.id % range

    def get_absolute_url(self):
        return reverse('view_post_by_name', args=[self.post_name])

    class Meta:
        app_label = 'core'



########NEW FILE########
__FILENAME__ = topic
# -*- coding: utf-8 -*-
from datetime import datetime

from django.db import models
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.template.loader import render_to_string
from django.contrib.markup.templatetags.markup import restructuredtext
from django.core.urlresolvers import reverse

from apps.member.models import Member
from apps.core.models import Event
from apps.core.models.vote import Vote

from lxml import html
from lxml.html.clean import Cleaner

class Topic(models.Model):

    author = models.ForeignKey(Member, related_name='topic_created', verbose_name=u"演讲者")
    in_event = models.ForeignKey(Event, related_name='topic_shown_in', blank=True, null=True, verbose_name=u"已安排在此活动中")
    description = models.TextField(u"简介", max_length=200, blank=False)
    content = models.TextField(u"内容", blank=True)
    html = models.TextField(u'HTML', blank=True, null=True)
    content_type = models.CharField(blank=False, default='html', max_length=30)
    accepted = models.BooleanField(default=False)  #该话题是否已经被管理员接受,True才能在活动正式的公布页面显示, 同时in_event才能显示

    name = models.CharField("名称", max_length=255, blank=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=True, blank=True, null=True)
    last_modified = models.DateTimeField(auto_now_add=True, auto_now=True, blank=True, null=True)
    last_modified_by = models.ForeignKey(Member, related_name='%(class)s_last_modified')
    #aggrgated
    total_votes = models.PositiveIntegerField(default=0)
    total_favourites = models.PositiveIntegerField(default=0, editable=False)

    html_cleaner = Cleaner(style=False, embedded=False, safe_attrs_only=False)

    def set_author(self, user):
        author = user.get_profile()
        self.last_modified_by = author # last_modified_by 总是author？
        self.author = author
        return self

    @property
    def poll_status(self):
        if self.in_event:
            if self.accepted:
                if self.in_event.is_upcoming:
                    return u'网络投票进行中'
                elif self.in_event.is_off:
                    return u'本话题所属活动已经结束'
            else:
                return u'活动等待管理员审核中，审核完毕后即可开始投票'
        else:
            return u'该话题尚未加入任何活动，无法开始投票'

        return u'我们也不知道怎么了'

    @property
    def rendered_content(self):
        if self.content_type == 'restructuredtext':
            '''暂时取消restructuredtext的处理'''
            #return restructuredtext(self.content)

            #创建lxml的html过滤器，保留object,embed,去除js,iframe
            return self.html_cleaner.clean_html(self.content) #使用过滤器,返回安全的html
        elif self.content_type == 'html':
            return self.html
        else:
            return restructuredtext(self.content)


    @property
    def is_shown(self):
        '''该话题所属活动是否正在进行或已经结束'''
        return self.in_event and (self.in_event.is_off or self.in_event.is_running)

    @property
    def is_arranged(self):
        '''该话题是否已经加入到活动，并且活动尚未开始'''
        return self.in_event and (self.in_event.is_upcoming == True)

    @property
    def content_text(self):
        try:
            content = self.content.decode('utf-8')
        except UnicodeEncodeError:
            content = self.content

        content_element = html.fromstring(content)

        return content_element.text_content()

    @property
    def summary(self):
        content = self.content_text

        if len(content) > 60:
            return '%s...' % content[:60]
        else:
            return content

    def style_seed(self, range=4):
        '''用来显示一些随机的样式'''
        return self.id % range

    def get_absolute_url(self):
        return reverse('topic', args = [self.id])

    def send_notification_mail(self, type):
        '''在话题提交及更新时发送提醒邮件'''

        type_dict = {'created':u'建立',
                     'updated':u'更新',
                    }
        subject = u"[Open Party] 话题%(type)s：%(name)s" % {'type':type_dict[type.lower()], 'name':self.name}

        ctx = { 'topic': self,
                'action': type_dict[type.lower()],
                'modification_date': str(datetime.now()),
                'site': settings.SITE_URL }

        message = render_to_string('core/topic_notification_email.txt', ctx)

        admin_user_set = User.objects.filter(is_staff = True) #给具有管理权限的用户发信
        #没有用mail_admins(),更灵活一些
        mail_queue = []
        for each_admin in admin_user_set:
            email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
            [each_admin.email], '',
            headers = {'Reply-To': each_admin.email})
            email.content_subtype = "plain"
            mail_queue.append(email)

        #使用单次SMTP连接批量发送邮件
        connection = mail.get_connection()   # Use default e-mail connection
        connection.send_messages(mail_queue)

        return True

    def __unicode__(self):
            return self.name

    votes = generic.GenericRelation('Vote')

    #TODO Add a custom manager for most web voted & unshown topics, to add to a upcoming event

    def save(self, *args, **kwargs):
        self.total_votes = self.votes.count()
        if not self.content or self.content.strip() == '':
          self.content = self.description
        super(Topic, self).save(*args, **kwargs)

    class Meta:
        app_label = 'core'

########NEW FILE########
__FILENAME__ = vote
# -*- coding: utf-8 -*-
from django.db import models

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from apps.member.models import Member

class Vote(models.Model):
    '''A Vote for Topic, Event or Comment'''
    user = models.ForeignKey(Member, related_name='vote_created',verbose_name=u"用户")
    rating = models.FloatField("评分",default=0)

    content_type = models.ForeignKey(ContentType, limit_choices_to = {'model__in': ('topic', 'event', 'comment')})
    object_id = models.PositiveIntegerField()
    item = generic.GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField("创建日期",auto_now_add=True)
    # denorm
    item_raw = models.TextField('item raw',blank=True)
    user_raw = models.TextField('user raw',blank=True)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        return u'%s 投票给 %s' % (self.user, self.item)

########NEW FILE########
__FILENAME__ = addcss
from django import template
register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
    return field.as_widget(attrs={"class":css})

########NEW FILE########
__FILENAME__ = event_test
#!/usr/bin/env python
# encoding: utf-8
from datetime import datetime, timedelta
from django.test import TestCase
from apps.core.models import Event
from apps.member import test_helper as member_test_helper

class EventTests(TestCase):

    def setUp(self):
        self.yesterday = datetime.now() - timedelta(days=1)
        self.the_day_before_yesterday = datetime.now() - timedelta(days=2)
        self.tomorrow = datetime.now() + timedelta(days=1)
        self.member = member_test_helper.create_user()

    def tearDown(self):
        pass
    
    def test_passed_event_is_not_upcoming_event(self):
        event = Event(begin_time=self.the_day_before_yesterday, end_time=self.yesterday, name='test', content='test')
        event.last_modified_by = self.member
        event.save()
        self.assertFalse(event.is_upcoming)
    
    def test_new_event_is_upcoming_event(self):
        event = Event(begin_time=self.tomorrow, end_time=self.tomorrow, name='test', content='test')
        event.last_modified_by = self.member
        event.save()
        self.assertTrue(event.is_upcoming)
    
    def test_event_is_off(self):
        event = Event(begin_time=self.tomorrow, end_time=self.tomorrow, name='test', content='test')
        event.last_modified_by = self.member
        event.save()
        self.assertFalse(event.is_off)
        event.end_time = self.yesterday
        event.save()
        self.assertTrue(event.is_off)
    
    def test_event_is_running(self):
        event = Event(begin_time=self.tomorrow, end_time=self.tomorrow, name='test', content='test')
        event.last_modified_by = self.member
        event.save()
        self.assertFalse(event.is_running)
        
        event.begin_time=self.yesterday
        event.end_time=self.yesterday
        event.save()
        self.assertFalse(event.is_running)
        
        event.begin_time=self.yesterday
        event.end_time= self.tomorrow
        event.save()
        self.assertTrue(event.is_running)

    def test_event_get_next_event(self):
        '''next_event获取最近一个尚未关闭的活动,用于报名及活动现场签到'''
        event = Event(begin_time=self.the_day_before_yesterday, end_time=self.tomorrow, name='test', content='test')
        event.last_modified_by = self.member
        event.save()
        self.failUnlessEqual(Event.objects.next_event(), event)

        event.end_time=self.yesterday #关闭该event
        event.save()
        #NullEvent的id为0
        self.assertEquals(Event.objects.next_event().id, 0)

        #上一个event关闭后，那么就该获取其后的event
        event_coming_willbe_next_event = Event(begin_time=self.tomorrow, end_time=self.tomorrow, name='test2', content='test2')
        event_coming_willbe_next_event.last_modified_by = self.member
        event_coming_willbe_next_event.save()
        self.assertEquals(Event.objects.next_event(), event_coming_willbe_next_event)

    def test_event_manager_upcoming_past_events(self):
        '''测试Manager里面的upcoming_events'''
        event = Event(begin_time=self.tomorrow, end_time=self.tomorrow, name='upcoming event', content='test')
        event.last_modified_by = self.member
        event.save()
        event_past = Event(begin_time=self.the_day_before_yesterday, end_time=self.yesterday, name='past event', content='test')
        event_past.last_modified_by = self.member
        event_past.save()

        self.failUnlessEqual(Event.objects.upcoming_events()[0], event)
        self.failUnlessEqual(Event.objects.past_events()[0], event_past)


########NEW FILE########
__FILENAME__ = feed_test
# -*- coding: utf-8 -*-
from django.test import TestCase
from apps.core.models import Topic
from apps.core.tests import test_helper
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from apps.member.models import Member
import apps.member.test_helper as helper


class FeedTest(TestCase):

    def test_topics_feed(self):
        '''测试话题的Feed能否正常输出'''

        response = self.client.post(reverse("feed_topics"))
        self.failUnlessEqual(response.status_code, 200)

    def test_events_feed(self):
        '''测试活动的Feed能否正常输出'''

        response = self.client.post(reverse("feed_events"))
        self.failUnlessEqual(response.status_code, 200)

    def test_posts_feed(self):
        '''测试新闻的Feed能否正常输出'''

        response = self.client.post(reverse("feed_posts"))
        self.failUnlessEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = status_check_test
# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.urlresolvers import reverse
from apps.member.models import Member
from apps.core.models import Event, Topic
from django.contrib.auth.models import User
from datetime import datetime

class StatusCheckTest(TestCase):
    def setUp(self):
        new_user = User.objects.create(username="tester", password="tester")
        new_user.save()
        self.client.login(username="tester", passsword="tester")
        new_member = Member.objects.create(user=new_user, nickname="tester")
        new_member.save()
        new_event = Event.objects.create(name="test event 01", description="xxx", content="xxx", begin_time = datetime.now(), end_time = datetime.now(), last_modified_by=new_member)
        new_event.save()
        new_topic = Topic.objects.create(name="test topic 01", description="xxx", content="xxx", author=new_member, last_modified_by=new_member)
        new_topic.save()

    def test_statuscheck_indexpage(self):
        response = self.client.get("/")
        #Check the response status
        self.failUnlessEqual(response.status_code, 200)
        #check template usage

    def test_statuscheck_eventlistpage(self):
        response = self.client.get(reverse('event_list'))
        self.failUnlessEqual(response.status_code, 200)

    def test_statuscheck_topiclist_page(self):
        response = self.client.get(reverse('topic_list'))
        self.failUnlessEqual(response.status_code, 200)

    def test_statuscheck_eventdetail_page(self):
        response = self.client.get("/event/1")
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.get("/event/19999")
        self.failUnlessEqual(response.status_code, 404)

    def test_statuscheck_topicdetail_page(self):
        response = self.client.get("/topic/1")
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.get("/topic/19999")
        self.failUnlessEqual(response.status_code, 404)

    def statuscheck_topicsubmit_page(self):
        response = self.client.get(reverse('submit_new_topic'))
        self.failUnlessEqual(response.status_code, 200)

    def statuscheck_eventjoin_page(self):
        response = self.client.get('/event/join')
        self.failUnlessEqual(response.status_code, 200)

    def test_statuscheck_topicvotedetail_page(self):
        response = self.client.get("/topic/1/votes")
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.get("/topic/19999/votes")
        self.failUnlessEqual(response.status_code, 404)



########NEW FILE########
__FILENAME__ = test_helper
#!/usr/bin/env python
# encoding: utf-8
from datetime import datetime, timedelta
from apps.core.models import Event
from apps.member import test_helper as member_test_helper

def yesterday():
    return datetime.now() - timedelta(days=1)

def the_day_before_yesterday():
    return datetime.now() - timedelta(days=2)

def tomorrow():
    return datetime.now() + timedelta(days=1)

def create_running_event(name='running event', content='running event'):
    event = Event(begin_time=yesterday(), end_time=tomorrow(), name=name, content=content)
    event.last_modified_by = member_test_helper.create_user()
    event.save()

    return event

def create_passed_event(name='passed event', content='passed event'):
    event = Event(begin_time=the_day_before_yesterday(), end_time=yesterday(), name=name, content=content)
    event.last_modified_by = member_test_helper.create_user()
    event.save()

    return event

def create_upcoming_event(name='upcoming event', content='upcoming event'):
    event = Event(begin_time=tomorrow(), end_time=tomorrow(), name=name, content=content)
    event.last_modified_by = member_test_helper.create_user()
    event.save()

    return event
    
########NEW FILE########
__FILENAME__ = topic_test
# -*- coding: utf-8 -*-
from django.test import TestCase
from apps.core.models import Topic
from apps.core.tests import test_helper
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from apps.member.models import Member
import apps.member.test_helper as helper

class TopicTest(TestCase):
    def test_topic_summary(self):
        content = '''软件需求遇到的最大问题是什么？基本上都是沟通和交流的相关问题需求从哪里来：客户（市场）、用户 我们需要确定的是：谁是用户？当前业务流程情况？业务目标是什么？ 项目需求确定中遇到的最大问题是什么？需求文档驱动的过程不堪重负 查看更多'''
        t = Topic(content=content)
        self.assertEquals(u'软件需求遇到的最大问题是什么？基本上都是沟通和交流的相关问题需求从哪里来：客户（市场）、用户 我们需要确定的是：谁是用户...', t.summary)

    # 看到註釋裡寫到去掉了restructuredtext的處理，所以去掉對應的注釋
    #def test_render_topic_content_restructuredtext(self):
    #    '''You have to install docutils for pass this test.'''
    #    content = '标题\n- point 1\n- point 2'
    #    t = Topic(content=content)
    #    self.assertEquals(u'<p>标题\n- point 1\n- point 2</p>\n', t.rendered_content)
    
    def test_render_topic_content_html(self):
        html = '<h2>标题</h2><p>内容</p>'
        t = Topic(html=html, content_type='html')
        self.assertEquals(html, t.rendered_content)
    
    def test_topic_poll_status_when_it_is_not_in_event(self):
        event = test_helper.create_passed_event()
        topic = Topic(name='test', content='test', description='', author=event.last_modified_by, accepted=True)
        topic.last_modified_by=event.last_modified_by
        topic.save()
        self.assertEquals(u'该话题尚未加入任何活动，无法开始投票', topic.poll_status)
        # it's not related to accepted
        topic.accepted = False
        topic.save()
        self.assertEquals(u'该话题尚未加入任何活动，无法开始投票', topic.poll_status)
    
    def test_topic_poll_status_when_it_is_not_accepted_by_admin(self):
        event = test_helper.create_passed_event()
        topic = Topic(name='test', content='test', description='', in_event=event, author=event.last_modified_by, accepted=False)
        topic.last_modified_by=event.last_modified_by
        topic.save()
        self.assertEquals(u'活动等待管理员审核中，审核完毕后即可开始投票', topic.poll_status)
    
    def test_topic_poll_status(self):
        event = test_helper.create_upcoming_event()
        topic = Topic(name='test', content='test', description='', in_event=event, author=event.last_modified_by, accepted=True)
        topic.last_modified_by=event.last_modified_by
        topic.save()
        self.assertEquals(u'网络投票进行中', topic.poll_status)

    def test_topic_poll_status_when_event_is_passed(self):
        event = test_helper.create_passed_event()
        topic = Topic(name='test', content='test', description='', in_event=event, author=event.last_modified_by, accepted=True)
        topic.last_modified_by=event.last_modified_by
        topic.save()
        self.assertEquals(u'本话题所属活动已经结束', topic.poll_status)

    def test_topic_model_refactor_last_modified_by_reverse_search(self):
        '''针对core中models合并后FK外键反向查找中%(class)s是否正常工作的测试(可删除)'''
        event = test_helper.create_upcoming_event()
        topic = Topic(name='test', content='test', description='', in_event=event, author=event.last_modified_by, accepted=True)
        topic.last_modified_by=event.last_modified_by
        topic.save()
        topic_should_be = event.last_modified_by.topic_last_modified.all()[0]
        self.failUnlessEqual(topic, topic_should_be)

    def test_submit_topic(self):
        '''用户登录后可以成功提交话题'''
        new_user = User.objects.create_user("tin", "tin@tin.com", "123")
        self.client.login(username='tin', password='123')
        Member.objects.create(user = new_user, nickname="Tin")
        event = test_helper.create_upcoming_event()
        response = self.client.post(reverse("submit_new_topic"), {'name':'Test Topic Submitted','title':'','description':'Test Topic Description','content':'content','in_event':event.id, 'captcha':''})
        check_topic = len(Topic.objects.filter(name="Test Topic Submitted"))
        self.assertEquals(1, check_topic)

    def test_captcha_on_submit(self):
        '''填写了不可见字段的话题被视为spam不可提交'''
        new_user = User.objects.create_user("tin", "tin@tin.com", "123")
        self.client.login(username='tin', password='123')
        Member.objects.create(user = new_user, nickname="Tin")
        event = test_helper.create_upcoming_event()
        response = self.client.post(reverse("submit_new_topic"), {"title":"iamaspamer",'name':'Test Topic Submitted','description':'Test Topic Description','content':'content','in_event':event.id, 'captcha':'should be empty if human'})
        self.assertEquals(response.status_code, 403)

    def test_edit_topic(self):
        '''用户登录后可以修改自己提交的话题'''

        new_user = User.objects.create_user("test", "test@test.com", "123")
        member_new_user = Member.objects.create(user = new_user, nickname="Test")
        self.client.login(username='test', password='123')

        event = test_helper.create_upcoming_event()
        
        test_user_topic = Topic.objects.create(author = member_new_user, in_event = event, \
                                               name = "Test", description = "test", content = "test")

        response = self.client.get(reverse("edit_topic",  kwargs = {"id": test_user_topic.id }))
        self.failUnlessEqual(response.status_code, 200)

        #如果用户不是此话题的作者，则无法编辑此话题

        non_relevant_user = User.objects.create_user("another_user", "another@test.com", "123")
        member_non_relevant_user = Member.objects.create(user = non_relevant_user, nickname="Another")

        test_non_user_topic = Topic.objects.create(author = member_non_relevant_user, in_event = event, \
                                                   name = "Another Topic", description = "test", content = "test")
        response = self.client.get(reverse("edit_topic", kwargs = {"id": test_non_user_topic.id }))
        self.failUnlessEqual(response.status_code, 302)



########NEW FILE########
__FILENAME__ = urls
from feeds import Events_Feed, Topics_Feed, Posts_Feed
from django.conf.urls.defaults import patterns, url

event_patterns = patterns('core.views',
    url(r'^$', 'event_list', name='event_list'),
    url(r'^join/?$', 'join_event'),
    url(r'^checkin$', 'checkin', name='event_checkin'),
    url(r'^(?P<id>\d+)$', 'event', name='event'),
)

topic_patterns = patterns('core.views',
    url(r'^$', 'topic_list', name='topic_list'),
    url(r'^(?P<id>\d+)$', 'topic', name='topic'),
    url(r'^new/?$', 'submit_topic', name='submit_new_topic'),
    url(r'^(?P<id>\d+)/edit/?$', 'edit_topic', name='edit_topic'),
    url(r'^(?P<id>\d+)/vote$', 'vote'),
    url(r'^(?P<id>\d+)/votes$', 'votes_for_topic', name='vote_for_topic'),
)

feed_patterns = patterns('core.views',
    url(r'^event/?$', Events_Feed(), name="feed_events"),
    url(r'^topic/?$', Topics_Feed(), name="feed_topics"),
    url(r'^post/?$', Posts_Feed(), name="feed_posts"),
)

post_patterns = patterns('core.views',
    url(r'^$', 'list_post', name='list_post'),
    url(r'^(?P<id>\d+)/?$', 'view_post', name='view_post'),
    url(r'^(?P<name>[^/]*)/?$', 'view_post_by_name', name='view_post_by_name'),
)

wordpress_redirect_patterns = patterns('core.views',
    url(r'^(?P<name>[^/]*)/?$', 'redirect_wordpress_post', name='redirect_wordpress_post'),
)

about_patterns = patterns('django.views.generic.simple',
        url(r'^/?$', 'direct_to_template', {'template': 'core/about.html', 'extra_context':{'tab':'about'}}, name="about"),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response, redirect, get_list_or_404
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django import forms

from apps.member.models import Member
from apps.member.forms import ProfileForm

from forms import ArticleForm, EventCheckinForm
from models import Event, Topic, Post
from models import Vote
from django.core.urlresolvers import reverse



def index(request):
    topic_list = Topic.objects.all().order_by('-in_event__begin_time','-accepted', '-total_votes')[:8]
    event_list = Event.objects.past_events().order_by('-begin_time')[:3]
    post_list = Post.objects.all().order_by('-created_at')[:15]
    next_event = Event.objects.next_event()

    ctx = {
        'event_list': event_list,
        'topic_list': topic_list,
        'post_list': post_list,
        'next_event': next_event,
        'tab': 'index',
    }
    return render_to_response('core/index.html', ctx, context_instance=RequestContext(request))

def event_list(request):
    event_list = Event.objects.all().order_by('-begin_time')
    topic_list = Topic.objects.all().order_by('-total_votes')

    ctx = {
        'event_list': event_list,
        'topic_list': topic_list,
        'tab': 'event',
    }
    return render_to_response('core/event_list.html', ctx, context_instance=RequestContext(request))

def topic_list(request):
    topic_list = Topic.objects.filter(accepted=True).order_by('-in_event__begin_time','-accepted', '-total_votes')
    paginator = Paginator(topic_list, 16)

    try:
        page_num = int(request.GET.get('page', '1'))
    except ValueError:
        page_num = 1

    try:
        page = paginator.page(page_num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    ctx = {
        'page': page,
        'topic_list': page.object_list,
        'tab': 'topic',
    }
    return render_to_response('core/topic_list.html', ctx, context_instance=RequestContext(request))

def join_event(request):
    if not request.user.is_authenticated():
        messages.info(request, u'对不起，您需要先登录才能报名参加活动，如果没有帐号可以选择<a href="/member/signup">注册</a>')
        return redirect(reverse('login'))

    next_event = Event.objects.next_event()

    if request.method == 'POST':
        form = ProfileForm(request.user, request.POST)
        member = form.save()
        if member:
            next_event.participants.add(member)
            messages.success(request, u'您已经成功报名参加《%s》活动，您是第%s名参加者' % (next_event.name, next_event.participants.count()))
            return redirect('/event/%s' % (next_event.id))
    else:
        try:
            this_user = request.user.get_profile()
        except:
            return redirect(reverse('signup'))

        if not next_event:
            raise Http404

        if this_user in next_event.participants.all():
            messages.success(request, u'感谢您的参与，您已经成功报名参加了 %s 活动 - 点击<a href="/event/%s">查看活动详情</a>' % (next_event.name, next_event.id))
            return redirect('/event/%s' % (next_event.id))
        else:
            form = ProfileForm(request.user)

    ctx = {
        'form': form,
        'next_event': next_event,
        'tab': 'event',
    }
    return render_to_response('core/join_evnet.html', ctx, context_instance=RequestContext(request))

def checkin(request):
    ctx = {'tab': 'event'}
    event = Event.objects.next_event()
    if request.method == 'GET':
        form = EventCheckinForm()
    else:
        form = EventCheckinForm(request.POST)
        try:
            if form.checkin(event):
                messages.success(request, u'您已经成功在现场签到了！')
        except forms.ValidationError, e:
            for error_message in e.messages:
                messages.error(request, error_message)
    ctx['form'] = form
    ctx['event'] = event
    return render_to_response('core/checkin.html', ctx, context_instance=RequestContext(request))

def event(request, id):
    this_event = get_object_or_404(Event, pk = id)
    topics_shown_in = this_event.topic_shown_in.filter(accepted=True)

    ctx = {
        'this_event': this_event,
        'topics_shown_in': topics_shown_in,
        'tab': 'event',
    }
    return render_to_response('core/event.html', ctx, context_instance=RequestContext(request))

def topic(request, id):
    this_topic = get_object_or_404(Topic, pk = id)

    is_voted = False
    try:
        vote_thistopic = this_topic.votes.get(user = request.user.get_profile())
        is_voted = True
    except:
        pass

    modified = False
    if this_topic.created != this_topic.last_modified:
        modified = True

    ctx = {
        'this_topic': this_topic,
        'is_voted': is_voted,
        'modified': modified,
        'tab': 'topic',
    }
    return render_to_response('core/topic.html', ctx, context_instance=RequestContext(request))

def votes_for_topic(request, id):
    this_topic = get_object_or_404(Topic, pk = id)
    votes_list = this_topic.votes.all().order_by('-id')
    tab = 'topic'
    ctx = {
        'this_topic': this_topic,
        'votes_list': votes_list,
        'tab': tab,
    }
    return render_to_response('core/votes_for_topic.html', ctx, context_instance=RequestContext(request))

@login_required
def vote(request, id):

    this_topic = Topic.objects.get(pk=id)

    is_voted = False
    try:
        vote_thistopic = this_topic.votes.get(user=request.user.get_profile())
        is_voted = True
    except:
        pass

    if is_voted == False:
        this_vote = Vote(user=request.user.get_profile())
        #this_topic.votes.add(user = request.user)
        topic_type = ContentType.objects.get_for_model(Topic)
        this_vote.content_type=topic_type
        this_vote.object_id=this_topic.id
        this_vote.save()


    #update vote count
    this_topic.save()

    return HttpResponseRedirect(reverse(topic, args=[this_topic.id]))

@login_required
def submit_topic(request):
    if request.method == 'GET':
        form = ArticleForm()
        form.fields['in_event'].queryset = Event.objects.upcoming_events()

        context = {
          'form': form,
          'tab': 'topic',
        }
        return render_to_response('core/submit_topic.html',
                                    context,
                                    context_instance=RequestContext(request))

    if request.method == 'POST' :
        form = ArticleForm(request.POST)
        context = {
            'form': form,
            'save_success': False,
        }

        if form.is_valid():
          topic = form.save(commit=False)
          if request.POST['captcha'] == '':
              topic = form.save(commit=False)
              topic.set_author(request.user)
              topic.save()
              topic.send_notification_mail('created')
              context['save_success'] = True
          else:
              return HttpResponseForbidden()

        return render_to_response('core/submit_topic.html',
                                    context,
                                    context_instance=RequestContext(request))


@login_required
def edit_topic(request, id):

    this_topic = get_object_or_404(Topic, pk = id)
    if this_topic.author.user != request.user:
        return HttpResponseRedirect(reverse('topic', args=[this_topic.id]))

    if request.method == 'GET':
        context = {
                    'form': ArticleForm(instance = this_topic),
                    'topic': this_topic,
                    'tab': 'topic',
                  }
        return render_to_response('core/edit_topic.html',
                                    context,
                                    context_instance=RequestContext(request))

    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=this_topic)
        topic = form.save(commit=False)
        topic.set_author(request.user)
        topic.save()
        topic.send_notification_mail('updated')

        context = {
            'form': form,
            'topic': topic,
            'edit_success': True,
            'tab': 'topic',
        }

        return render_to_response('core/edit_topic.html',
                                    context,
                                    context_instance=RequestContext(request))


def list_post(request):
    all_post = get_list_or_404(Post.objects.order_by('-created_at'), status=Post.post_status.OPEN)
    paginator = Paginator(all_post, 15)
    try:
        page_num = int(request.GET.get('page', '1'))
    except ValueError:
        page_num = 1

    try:
        page = paginator.page(page_num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    ctx = {
        'posts': page.object_list,
        'page': page,
        'tab': 'post',
    }
    return render_to_response('core/list_post.html',
                                ctx,
                                context_instance=RequestContext(request))


def view_post(request, id):
    post = get_object_or_404(Post, id=id)
    ctx = {
        'post': post,
        'tab': 'post',
    }
    return render_to_response('core/post.html',
                                ctx,
                                context_instance=RequestContext(request))

def view_post_by_name(request, name):
    post = get_object_or_404(Post, post_name=name)
    ctx = {
        'post': post,
        'object': post, #for pingback hook
        'tab': 'post',
    }
    return render_to_response('core/post.html',
                                ctx,
                                context_instance=RequestContext(request))

def redirect_wordpress_post(request, year, month, name):
    return HttpResponseRedirect(reverse('view_post_by_name', args=[name]))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from apps.member.models import Member

class Member_Admin(admin.ModelAdmin):
    raw_id_fields = ('user', )

admin.site.register(Member, Member_Admin)

########NEW FILE########
__FILENAME__ = change_password_form
# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from apps.member.models import Member


class ChangePasswordForm(forms.Form):
    oldpassword = forms.CharField(label=u'旧密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '1'}))
    password1 = forms.CharField(label=u'新密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '2'}))
    password2 = forms.CharField(label=u'重复密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '3'}))
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
    
    def clean_oldpassword(self):
        if not self.user.check_password(self.cleaned_data.get("oldpassword")):
            raise forms.ValidationError(u"您填写的旧密码不正确呀，要不您再试试（注意大小写）")
        return self.cleaned_data["oldpassword"]

    def clean_password1(self):
        password = self.cleaned_data['password1'].strip()
        if not password:
            raise forms.ValidationError(u'对不起，密码不能为空')
        return password

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(u'您所输入的两个密码不一致，请您重新输入')
        return self.cleaned_data

    def save(self):
        if not self.is_valid():
            return False
        password = self.cleaned_data['password1']
        self.user.set_password(password)
        self.user.save()
        return True

########NEW FILE########
__FILENAME__ = login_form
# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth import authenticate, login
from django.core.validators import validate_email


class LoginForm(forms.Form):
    email = forms.EmailField(label=u'email', required=True, widget=forms.TextInput(attrs={'tabindex': '1'}))
    password = forms.CharField(label=u'密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '2'}))
    remember = forms.BooleanField(label=u'记住登陆信息', help_text=u'如果选择记住登陆信息，会保留登陆信息2周', required = False, widget=forms.CheckboxInput(attrs={'tabindex': '3'}))
    
    user = None
    
    def clean_email(self):
        email=self.cleaned_data.get('email','')
        validate_email(email)
        return email
    
    def clean(self):
        super(LoginForm,self).clean()
        credential = { 'username': self.cleaned_data.get('email',''), 'password': self.cleaned_data.get('password','')}
        user = authenticate(**credential)
        if user:
            if user.is_active:
                self.user = user
            else:
                raise forms.ValidationError(u'您还没有通过邮件激活帐号，请您登陆邮箱打开链接激活')
        else:
            raise forms.ValidationError(u'您输入的邮件地址与密码不匹配或者帐号还不存在，请您重试或者注册帐号')
        return self.cleaned_data

    def login(self, request):
        if self.is_valid():
            login(request, self.user)
            if "remember" in self.cleaned_data and self.cleaned_data["remember"]:
                request.session.set_expiry(60 * 60 * 24 * 7 * 3)
            else:
                request.session.set_expiry(0)
            return True
        return False

########NEW FILE########
__FILENAME__ = profile_form
# -*- coding: utf-8 -*-
try:
    import json
except:
    from django.utils import simplejson as json

from django import forms
from apps.member.models import Member

class ProfileForm(forms.Form):
    realname = forms.CharField(label=u'真实姓名/Name', required=True, max_length=20, widget=forms.TextInput(attrs={'tabindex': '1'}))
    gender = forms.ChoiceField(label=u'性别/Gender', required=True, choices=((u'男', u'男'), (u'女', u'女'), (u'中性', u'中性')), widget=forms.Select(attrs={'tabindex': '2'}))
    career_years = forms.ChoiceField(label=u'工作年限/Career', required=True, choices=((u'1-3年', u'1-3年'), (u'3-5年', u'3-5年'), (u'5年以上', u'5年以上')), widget=forms.Select(attrs={'tabindex': '3'}))

    company = forms.CharField(label=u'公司/Company', required=False, max_length=40, widget=forms.TextInput(attrs={'tabindex': '4'}))
    position = forms.CharField(label=u'职位/Position', required=False, max_length=30, widget=forms.TextInput(attrs={'tabindex': '5'}))
    blog = forms.CharField(label=u'博客/Blog', required=False, max_length=255, widget=forms.TextInput(attrs={'tabindex': '6'}))
    phone = forms.CharField(label=u'手机/Phone', required=False, max_length=255, widget=forms.TextInput(attrs={'tabindex': '6'}))

    hobby = forms.CharField(label=u'兴趣/hobby', required=False, max_length=255, widget=forms.TextInput(attrs={'tabindex': '6'}))

    gtalk = forms.CharField(label=u'Gtalk', required=False, max_length=127, widget=forms.TextInput(attrs={'tabindex': '6'}))
    msn = forms.CharField(label=u'Msn', required=False, max_length=127, widget=forms.TextInput(attrs={'tabindex': '6'}))
    twitter = forms.CharField(label=u'twitter', required=False, max_length=127, widget=forms.TextInput(attrs={'tabindex': '6'}))
    foursquare = forms.CharField(label=u'foursquare', required=False, max_length=127, widget=forms.TextInput(attrs={'tabindex': '6'}))
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        self.member = user=self.user.get_profile()
        if (not args) and (not kwargs) and self.member and self.member.properties:
            properties = {}
            for key, value in json.loads(self.member.properties).items():
                properties[key.encode('utf-8')] = value.encode('utf-8')
            super(ProfileForm, self).__init__(properties)
        else:
            super(ProfileForm, self).__init__(*args, **kwargs)

    def clean(self):
        return self.cleaned_data
    
    def save(self):
        if not self.is_valid():
            return False

        if not self.member:
            return False
        
        properties = json.dumps(self.cleaned_data)
        self.member.properties = properties

        self.member.save()
        return self.member

########NEW FILE########
__FILENAME__ = request_reset_password_form
# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from django.core.validators import validate_email
from apps.member.models import Member


class RequestResetPasswordForm(forms.Form):
    email = forms.EmailField(label=u'email', required=True, widget=forms.TextInput(attrs={'tabindex': '1'}))
    
    user = None
    
    def clean_email(self):
        email=self.cleaned_data.get('email','')
        validate_email(email)
        return email
    
    def clean(self):
        super(RequestResetPasswordForm,self).clean()
        usermail = self.cleaned_data.get('email','')
        try:
            user = Member.objects.get(user__email=usermail).user
        except Member.DoesNotExist:
            raise forms.ValidationError(u'您输入的邮件地址与密码不匹配或者帐号还不存在，请您重试或者注册帐号')
        return self.cleaned_data

########NEW FILE########
__FILENAME__ = reset_password_form
# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from apps.member.models import Member


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(label=u'新密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '2'}))
    password2 = forms.CharField(label=u'重复密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '3'}))
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(ResetPasswordForm, self).__init__(*args, **kwargs)
    
    def clean_password1(self):
        password = self.cleaned_data['password1'].strip()
        if not password:
            raise forms.ValidationError(u'对不起，密码不能为空')
        return password

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(u'您所输入的两个密码不一致，请您重新输入')
        return self.cleaned_data

    def save(self):
        if not self.is_valid():
            return False
        password = self.cleaned_data['password1']
        self.user.set_password(password)
        self.user.save()
        return True

########NEW FILE########
__FILENAME__ = signup_form
# -*- coding: utf-8 -*-
import re
import random
from django import forms
from django.contrib.auth.models import User
from apps.member.models import Member

class SignupForm(forms.Form):
    email = forms.EmailField(label=u'email', required=True, widget=forms.TextInput(attrs={'tabindex': '1'}))
    nickname = forms.CharField(label=u'昵称', required=False, max_length=30, widget=forms.TextInput(attrs={'tabindex': '2'}))
    
    password1 = forms.CharField(label=u'密码', required=True, widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '3'}))
    password2 = forms.CharField(label=u'重复密码', widget=forms.PasswordInput(render_value=False, attrs={'tabindex': '4'}))
    
    def clean_nickname(self):
        nickname = self.cleaned_data['nickname'].strip()
        if nickname and (not re.compile(ur'^[\w|\u2E80-\u9FFF]+$').search(nickname)):
            raise forms.ValidationError(u'昵称“%s”名非法，昵称目前仅允许使用中英文字数字和下划线' % nickname)
        return nickname
    
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        try:
            # 每个Member对应一个User，但是允许后台User不对应Member
            User.objects.get(username__iexact=email) 
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(u'已经有用户使用“%s”注册了用户，请您确认邮件是否拼写错误' % email)
        return email
    
    def clean_password1(self):
        password = self.cleaned_data['password1'].strip()
        if not password:
            raise forms.ValidationError(u'对不起，密码不能为空')
        return password
    
    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(u'您所输入的两个密码不一致，请您重新输入')
        return self.cleaned_data
    
    def save(self):
        if not self.is_valid():
            return False
        email = self.cleaned_data['email']
        nickname = self.cleaned_data['nickname']
        password = self.cleaned_data['password1']
        
        
        member = Member.objects.create_with_inactive_user(email=email, password=password, nickname=nickname)
        return member

########NEW FILE########
__FILENAME__ = dump_event_participant
# -*- coding: utf-8 -*-
import sys
import csv
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.member.forms import ProfileForm
from apps.core.models import Event

class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args):
            event_id = int(args[0])
            event = Event.objects.get(pk=event_id)
        else:
            event = Event.objects.next_event()
        csv_file_name = '/tmp/openparty_%s_participants.csv' % event.id
        writer = csv.writer(open(csv_file_name , 'w'))
        header = ('id', 'username', 'nickname', 'realname', 'gender', 'career', 'company', 'position', 'blog', 'phone', 'hobby', 'gtalk', 'msn', 'twitter', 'foursquare')
        writer.writerow(header)
        for member in event.participants.all():
            profile = ProfileForm(user=member.user).data
            def prop(prop_name):
                try:
                    return unicode(profile.get(prop_name, ''), 'utf8').encode('utf8')
                except UnicodeDecodeError:
                    return ''

            row = (member.id, member.user.username.encode('utf8'), member.nickname.encode('utf8'), prop('realname'), prop('gender'), prop('career_years'), prop('company'), prop('position'), prop('blog'), prop('phone'), prop('hobby'), prop('gtalk'), prop('msn'), prop('twitter'), prop('foursquare'))
            writer.writerow(row)
        print 'out put csv file to %s' % csv_file_name

        
########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Member'
        db.create_table('member_member', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('nickname', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('properties', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('activation_key', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal('member', ['Member'])


    def backwards(self, orm):
        
        # Deleting model 'Member'
        db.delete_table('member_member')


    models = {
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
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['member']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_member_twitter_access_token_key__add_field_member_twit
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Member.twitter_access_token_key'
        db.add_column('member_member', 'twitter_access_token_key', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True), keep_default=False)

        # Adding field 'Member.twitter_access_token_secret'
        db.add_column('member_member', 'twitter_access_token_secret', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Member.twitter_access_token_key'
        db.delete_column('member_member', 'twitter_access_token_key')

        # Deleting field 'Member.twitter_access_token_secret'
        db.delete_column('member_member', 'twitter_access_token_secret')


    models = {
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
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'twitter_access_token_key': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'twitter_access_token_secret': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['member']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_member_twitter_enabled
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Member.twitter_enabled'
        db.add_column('member_member', 'twitter_enabled', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Member.twitter_enabled'
        db.delete_column('member_member', 'twitter_enabled')


    models = {
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
        'member.member': {
            'Meta': {'object_name': 'Member'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'properties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'twitter_access_token_key': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'twitter_access_token_secret': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'twitter_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['member']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import re, urllib, hashlib, random, datetime
from django.db import models
from django.conf import settings
from django.utils.hashcompat import sha_constructor
from django.template.loader import render_to_string
from django.db.transaction import commit_on_success
from django.contrib.auth.models import User
from django.core.cache import cache
import logging

import user

ACTIVATION_KEY_PATTERN = re.compile('^[a-f0-9]{40}$')

class MemberManager(models.Manager):
    @commit_on_success
    def create_with_inactive_user(self, email, password, nickname=''):
        def generate_activation_key(email):
            salt = sha_constructor(str(random.random())).hexdigest()[:8]
            activation_key = sha_constructor(salt+email).hexdigest()
            return activation_key

        user = User()
        user.username = email
        user.email = email
        user.set_password(password)
        user.is_active = True
        user.save()

        activation_key = generate_activation_key(email)
        member = self.model(user=user, nickname=nickname, activation_key=activation_key)
        member.save()
        member.send_activation_email()

        return member
    
    def find_by_activation_key(self, activation_key):
        if ACTIVATION_KEY_PATTERN.search(activation_key):
            try:
                member = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not member.is_activation_key_expired():
                user = member.user
                user.is_active = True
                user.save()
                member.activation_key = self.model.ACTIVATED
                member.save()
                return member
        return False
    
    def find_by_email(self, email):
        try:
            user = User.objects.get(username=email)
            if user:
                return self.get(user=user)
        except User.DoesNotExist:
            pass
        except Exception, e:
            logging.exception("find_by_email")
            pass
        return None


class Member(models.Model):
    ACTIVATED = "ALREADY_ACTIVATED"
    
    user = models.ForeignKey(User, unique=True, verbose_name=u"用户")
    nickname = models.CharField(verbose_name=u'用户名称', max_length=40)
    properties = models.TextField(verbose_name=u'属性', blank=True)
    activation_key = models.CharField(verbose_name=u'激活密钥 Activation Key', max_length=40)
    twitter_access_token_key = models.CharField(u'Twitter OAuth key', blank=True, null=True, max_length=80)
    twitter_access_token_secret = models.CharField(u'Twitter OAuth secret', blank=True, null=True, max_length=128)
    twitter_enabled = models.BooleanField(default=False)

    objects = MemberManager()
    
    def __unicode__(self):
        return self.user.username
    
    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        else:
            return self.user.username
    
    @property
    def avatar(self):
        default = settings.SITE_URL + '/media/images/default_gravatar.png'
        size = 40
        gravatar_url = "http://www.gravatar.com/avatar.php?"
        gravatar_url += urllib.urlencode({'gravatar_id':hashlib.md5(self.user.username).hexdigest(),
                                        'default':default, 'size':str(size)})
        return gravatar_url

    def send_activation_email(self):
        ctx = { 'activation_key': self.activation_key,
                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                'site': settings.SITE_URL }

        subject = "[Open Party] 帐号激活"
        message = render_to_string('member/activation_email.txt', ctx)

        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

    def _generate_pwd_reset_token(self):
        salt = sha_constructor(str(random.random())).hexdigest()[:8]
        token = sha_constructor(salt+self.user.username).hexdigest()
        cache.set('pwd_reset_token:%s' % self.user.id, token, 60*60*3)
        return token

    def is_pwd_reset_token_expired(self, given_token):
        return not (given_token and cache.get('pwd_reset_token:%s' % self.user.id, None) == given_token)

    def delete_pwd_reset_token(self):
        cache.delete('pwd_reset_token:%s' % self.user.id)

    def send_reset_password_email(self):
        ctx = { 'activation_key': self._generate_pwd_reset_token(),
                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                'user_id': self.id,
                'site': settings.SITE_URL }

        subject = "[Open Party] 密码重置"
        message = render_to_string('member/resetpwd_email.txt', ctx)

        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)


    
    def is_activation_key_expired(self):
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        already_joined_longer_than_expiration_days = (self.user.date_joined + expiration_date <= datetime.datetime.now())
        return self.activation_key == self.ACTIVATED or already_joined_longer_than_expiration_days

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.test import TestCase
from apps.member.models import Member
from apps.member.forms import SignupForm, LoginForm
import apps.member.test_helper as helper
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from apps.core.models import Event, Topic
from datetime import datetime

class MemberTest(TestCase):
    def test_save_member_though_form(self):
            form = SignupForm({ 'email': 'some@domain.com', 'password1': '1', 'password2': '1' })
            member = form.save()
            self.assertTrue(isinstance(member, Member))
            self.assertTrue(member.user.id)

    def test_save_member_though_form_with_nickname(self):
        form = SignupForm({ 'email': 'some@domain.com', 'nickname': u'田乐', 'password1': '1', 'password2': '1' })
        member = form.save()
        self.assertTrue(member.user.id)

    def test_save_member_should_show_error_when_password_not_matching(self):
        form = SignupForm({ 'email': 'some@domain.com', 'password1': '1', 'password2': '2' })
        self.assertFalse(form.save())
        self.assertEquals(1, len(form.errors))

    def test_save_member_should_show_error_when_email_is_not_valid(self):
        form = SignupForm({ 'email': 'domain.com', 'password1': '1', 'password2': '1' })
        self.assertFalse(form.save())
        self.assertEquals(1, len(form.errors))

    def test_save_member_should_show_error_when_usernick_valid(self):
        form = SignupForm({ 'email': 'domain.com', 'password1': '1', 'nickname': '123456', 'password2': '1' })
        self.assertFalse(form.save())
        self.assertEquals(1, len(form.errors))
        form = SignupForm({ 'email': 'some@domain.com', 'password1': '1', 'nickname': 'Bei Jing', 'password2': '1' })
        self.assertFalse(form.save())
        self.assertEquals(1, len(form.errors))

    def test_login(self):
        helper.create_user()
        response = self.client.post(reverse('login'), {'email': 'tin@domain.com', 'password': '123'})
        self.assertRedirects(response, '/')
    
    def test_login_should_failed_when_password_is_wrong(self):
        helper.create_user()
        response = self.client.post(reverse('login'), {'email': 'tin@domain.com', 'password': 'wrong-password'})
        self.assertFormError(response, 'form', '', u'您输入的邮件地址与密码不匹配或者帐号还不存在，请您重试或者注册帐号')
    
    # 暂时注释掉，因为邮件服务器总有问题，所以我们选择不需要邮件激活
    # def test_login_should_failed_before_activate(self):
    #         helper.create_user(activate=False)
    #         response = self.client.post(reverse('login'), {'email': 'tin@domain.com', 'password': '123'})
    #         self.assertFormError(response, 'form', '', u'您还没有通过邮件激活帐号，请您登陆邮箱打开链接激活')
    
    def test_avatar_of_member(self):
        import settings
        member = helper.create_user()
        user = member.user
        self.assertEquals('http://www.gravatar.com/avatar.php?default=http%3A%2F%2F' + settings.SITE_URL[len("http://"):] + '%2Fmedia%2Fimages%2Fdefault_gravatar.png&size=40&gravatar_id=ea746490cff50b7d53bf78a11c86815a', user.get_profile().avatar)

    def test_find_member_by_email(self):
        member = helper.create_user()
        user = member.user
        found = Member.objects.find_by_email(user.email)
        self.assertEquals(member, found)

    def test_find_member_by_none_existing_email(self):
        not_found = Member.objects.find_by_email('iamnotexisting@gmail.com')
        self.assertFalse(not_found)

class StatusTest(TestCase):
    def setUp(self):
        new_user = User.objects.create(username="tester", password="tester")
        new_user.save()
        self.client.login(username="tester", passsword="tester")
        new_member = Member.objects.create(user=new_user, nickname="tester")
        new_member.save()
        new_event = Event.objects.create(name="test event 01", description="xxx", content="xxx", begin_time = datetime.now(), end_time = datetime.now(), last_modified_by=new_member)
        new_event.save()
        new_topic = Topic.objects.create(name="test topic 01", description="xxx", content="xxx", author=new_member, last_modified_by=new_member)
        new_topic.save()

    def test_statuscheck_member_profile(self):
        response = self.client.get(reverse('member_profile', kwargs={"pk":1}))
        self.failUnlessEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = test_helper
from apps.member.forms import SignupForm

def create_user(email='tin@domain.com', password='123', nickname='tin', activate=True):
    signup_form = SignupForm({ 'email': email, 'password1': password, 'nickname': nickname, 'password2': password })
    member = signup_form.save()
    if activate:
        member.user.is_active = True
        member.user.save()
    return member
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from apps.member.views import MemberProfileView
from apps.member.views import MemberRequestResetPasswordView, MemberRequestResetPasswordDone

urlpatterns = patterns('member.views',
    url(r'^signup$', 'signup', name='signup'),
    url(r'^login$', 'login', name='login'),
    url(r'^logout$', 'logout', name='logout'),
    url(r'^change_password$', 'change_password', name='change_password'),
    url(r'^update_profile$', 'update_profile', name='update_profile'),
    url(r'^activate/(?P<activation_key>\w+)/$', 'activate', name='activate_account'),
    url(r'^(?P<pk>\d+)/$', MemberProfileView.as_view(), name='member_profile'),
    url(r'^request_reset_password$', MemberRequestResetPasswordView.as_view(), name='member_request_reset_pwd'),
    url(r'^request_reset_password_done$', MemberRequestResetPasswordDone.as_view(), name='member_request_reset_pwd_done'),
    url('^reset_password/(?P<user_id>\d+)/(?P<pwd_reset_token>\w+)/$', 'reset_password', name='reset_password'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView
from django.http import Http404  

from apps.member.forms import LoginForm, SignupForm, ChangePasswordForm, ProfileForm, RequestResetPasswordForm, ResetPasswordForm
from apps.member.models import Member
from django.core.urlresolvers import reverse

def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.login(request):
            next = request.GET.get("next", "")
            if next:
                return redirect(next)
            return redirect('/')
    else:
        form = LoginForm()

    ctx = { 'form': form,  }
    return render_to_response('member/login.html', ctx, context_instance=RequestContext(request))

def logout(request):
    auth_logout(request)
    return HttpResponseRedirect('/')

def signup(request):
    if request.method == 'POST' and request.POST['captcha'] == '':
        form = SignupForm(request.POST)
        if form.save():
            ctx = { 'email': form.cleaned_data['email'], }
            return render_to_response('member/verification_sent.html', ctx,
                context_instance=RequestContext(request))
    else:
        form = SignupForm()

    ctx = { 'form': form,  }
    return render_to_response('member/signup.html', ctx, context_instance=RequestContext(request))

def activate(request, activation_key):
    activating_member = Member.objects.find_by_activation_key(activation_key)
    if activating_member:
        messages.success(request, u'您的帐号已经成功激活，请尝试登录吧')
    else:
        messages.error(request, u'对不起，您所的激活号码已经过期或者根本就不存在？')
    return redirect(reverse('login'))

@login_required
def change_password(request):
    if request.method == 'POST' and request.user.is_authenticated():
        form = ChangePasswordForm(request.user, request.POST)
        if form.save():
            messages.success(request, u'您的密码已经修改')
            return redirect('/')
    else:
        form = ChangePasswordForm(request)
    ctx = { 'form': form,  }
    return render_to_response('member/change_password.html', ctx,
        context_instance=RequestContext(request))

class MemberRequestResetPasswordView(FormView):
    form_class = RequestResetPasswordForm
    template_name = 'member/request_reset_password.html'

    def form_valid(self, form):
        this_member = Member.objects.get(user__email=form.cleaned_data['email'])
        this_member.send_reset_password_email()
        return super(MemberRequestResetPasswordView, self).form_valid(form)

    def get_success_url(self):
        return reverse('member_request_reset_pwd_done')

class MemberRequestResetPasswordDone(TemplateView):
    template_name = 'member/request_reset_password_done.html'

def reset_password(request, user_id, pwd_reset_token):
    try:
        this_member = Member.objects.get(id=user_id)
    except Member.DoesNotExist:
        raise Http404
    token = pwd_reset_token
    if request.method == 'POST' and not this_member.is_pwd_reset_token_expired(token):
        form = ResetPasswordForm(this_member.user, request.POST)
        if form.save():
            messages.success(request, u'您的密码已经修改')
            this_member.delete_pwd_reset_token()
            return redirect('/')
    elif not this_member.is_pwd_reset_token_expired(token):
        form = ResetPasswordForm(request)
        ctx = { 'form': form,  }
    else:
        ctx = { 'status': 'failed' }
    return render_to_response('member/reset_password.html', ctx, context_instance=RequestContext(request))

@login_required
def update_profile(request):
    if request.method == 'POST' and request.user.is_authenticated():
        form = ProfileForm(request.user, request.POST)
        if form.save():
            messages.success(request, u'您的个人信息已经修改')
            return redirect('/')
    else:
        form = ProfileForm(request.user)
    ctx = { 'form': form,  }
    return render_to_response('member/update_profile.html', ctx,
        context_instance=RequestContext(request))


class MemberProfileView(DetailView):

    context_object_name = "member"
    model = Member

    def get_queryset(self, **kwargs):
        queryset = super(MemberProfileView, self).get_queryset(**kwargs)
        return queryset.select_related()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from models import Tweet

class Tweet_Admin(admin.ModelAdmin):
    list_display = ('tweet_user_name', 'text', 'created_at', 'source')
    list_filter = ['source']

admin.site.register(Tweet, Tweet_Admin)

########NEW FILE########
__FILENAME__ = sync_tweets
#!/usr/bin/env python
# encoding: utf-8
import sys
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.twitter.models import Tweet


class Command(BaseCommand):

    def handle(self, *args, **options):
        print 'Start syncing'
        if len(args) == 1:
            if args[0] == 'all':
                sync_all = True
                query = '#openparty'
            else:
                sync_all = False
                query = args[0]
        elif len(args) == 2:
            if args[0] == 'all':
                sync_all = True
                query = args[1]
            else:
                print 'Paramerters was wrong'
                sys.exit()
        else:
            sync_all = False
            query = '#openparty'
        
        if sync_all:
            count = Tweet.objects.sync_all(query=query)
        else:
            count = Tweet.objects.sync(query=query)
        
        print 'Synced %s tweets' % count


########NEW FILE########
__FILENAME__ = sync_weibo
#!/usr/bin/env python
# encoding: utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.twitter.models import Tweet


class Command(BaseCommand):

    def handle(self, *args, **options):
        print 'Start syncing'
        if len(args) == 1:
            if args[0] == 'all':
                sync_all = True
                query = '#openparty'
            else:
                sync_all = False
                query = args[0]
        elif len(args) == 2:
            if args[0] == 'all':
                sync_all = True
                query = args[1]
            else:
                print 'Paramerters was wrong'
                sys.exit()
        else:
            sync_all = False
            query = '#openparty'
        
        count = Tweet.objects.sync_weibo(query=query)
        print 'Synced %s tweets' % count


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Tweet'
        db.create_table('twitter_tweet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('tweet_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True)),
            ('profile_image', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=512, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True)),
            ('geo', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('tweet_user_id', self.gf('django.db.models.fields.BigIntegerField')(blank=True)),
            ('tweet_user_name', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('craeted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('dump', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('query', self.gf('django.db.models.fields.CharField')(max_length=127, null=True, blank=True)),
        ))
        db.send_create_signal('twitter', ['Tweet'])


    def backwards(self, orm):
        
        # Deleting model 'Tweet'
        db.delete_table('twitter_tweet')


    models = {
        'twitter.tweet': {
            'Meta': {'object_name': 'Tweet'},
            'craeted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'dump': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'geo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'profile_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.CharField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'tweet_user_id': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'tweet_user_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_tweet_race__add_field_tweet_uri__chg_field_tweet_text
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models, connection, transaction


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Tweet.race'
        db.add_column('twitter_tweet', 'race', self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True), keep_default=False)

        # Adding field 'Tweet.uri'
        db.add_column('twitter_tweet', 'uri', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True), keep_default=False)

        # Changing field 'Tweet.text'
        db.alter_column('twitter_tweet', 'text', self.gf('django.db.models.fields.TextField')(max_length=512, blank=True))
        db.execute("update twitter_tweet set race = 'twitter' where race is null")

    def backwards(self, orm):
        
        # Deleting field 'Tweet.race'
        db.delete_column('twitter_tweet', 'race')

        # Deleting field 'Tweet.uri'
        db.delete_column('twitter_tweet', 'uri')

        # Changing field 'Tweet.text'
        db.alter_column('twitter_tweet', 'text', self.gf('django.db.models.fields.CharField')(max_length=512, blank=True))


    models = {
        'twitter.tweet': {
            'Meta': {'object_name': 'Tweet'},
            'craeted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'dump': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'geo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'profile_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.CharField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'race': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'max_length': '512', 'blank': 'True'}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'tweet_user_id': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'tweet_user_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_tweet_craeted_at__add_field_tweet_created_at
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Tweet.craeted_at'
        db.delete_column('twitter_tweet', 'craeted_at')

        # Adding field 'Tweet.created_at'
        db.add_column('twitter_tweet', 'created_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Tweet.craeted_at'
        db.add_column('twitter_tweet', 'craeted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)

        # Deleting field 'Tweet.created_at'
        db.delete_column('twitter_tweet', 'created_at')


    models = {
        'twitter.tweet': {
            'Meta': {'object_name': 'Tweet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'dump': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'geo': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'profile_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.CharField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'race': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'max_length': '512', 'blank': 'True'}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'tweet_user_id': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'tweet_user_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
try:
    import json
except:
    from django.utils import simplejson as json

import tweepy

import time
from lxml import html
from datetime import datetime, timedelta
from django.db import models
import urllib, urllib2
from cookielib import CookieJar

class TweetManager(models.Manager):

    def search(self, query='#openparty', limit=5, since=None, page=1):
        tweets = tweepy.api.search(q=query, rpp=limit, since_id=since, page=page)
        return [self.model.create_from_tweepy_tweet(tweet=tweet) for tweet in tweets]
    
    def sync(self, query='#openparty', since=None):
        if since:
            max_tweet_id = since # for test only
        else:
            max_tweet_id = self.filter(query=query).aggregate(models.Max('tweet_id'))['tweet_id__max']
        print 'Syncing new tweets of %s (newer than %s)' % (query, max_tweet_id)
        new_tweets = self.search(query=query, limit=100, since=max_tweet_id, page=1)
        if len(new_tweets):
            for tweet in new_tweets:
                tweet.query = query
                tweet.save()
            return len(new_tweets)
        else:
            return 0
    
    def sync_all(self, query='#openparty'):
        page = 1
        count = 0
        print 'Syncing all of %s' % query
        while True:
            tweets = tweepy.api.search(q=query, rpp=50, page=page)
            page += 1
            if len(tweets) == 0:
                break
            for tweet in tweets:
                t = self.model.create_from_tweepy_tweet(tweet=tweet)
                t.query = query
                t.save()
                count += 1
            print 'synced %s tweets' % count
            time.sleep(5)
        return count
    
    def sync_weibo(self, query='#openparty'):
        weibo_query = urllib.quote(urllib.quote(query))
        username = 'iamtin%40gmail.com'
        password = '111111'

        def add_headers(req):
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7')
            req.add_header('Referer', 'http://t.sina.com.cn/')
            return req

        post_data = 'client=ssologin.js(v1.3.9)&encoding=utf-8&' +\
                    'entry=miniblog&from=&gateway=1&password=' + password +\
                    '&returntype=META&savestate=7&service=miniblog&' +\
                     'url=http%3A%2F%2Ft.sina.com.cn%2Fajaxlogin.php%3Fframelogin%3D1%26c' +\
                     'allback%3Dparent.sinaSSOController.feedBackUrlCallBack&' +\
                     'username=' + username + '&useticket=0'

        post_url = 'http://login.sina.com.cn/sso/login.php'
        
        cookie = CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        urllib2.install_opener(opener)

        # login
        req = urllib2.Request(url=post_url, data=post_data)
        req = add_headers(req)
        response = urllib2.urlopen(req)
        
        # do the real search
        search_req = urllib2.Request(url='http://t.sina.com.cn/k/%2523openparty')
        req = add_headers(search_req)
        response = urllib2.urlopen(search_req)
        htm = response.read()
        page = html.fromstring(htm)
        tweets_list = page.cssselect('#feed_list li')
        tweets = []
        for tweet_element in tweets_list:
            tweet = self.model.create_from_weibo_html_fragment(tweet_element)
            if not tweet.is_duplicated():
                tweet.save()
                tweets.append(tweet)
        return len(tweets)

# Create your models here.
class Tweet(models.Model):
    """(A model represent the tweets of twitter.com)"""
    tweet_id = models.BigIntegerField(blank=False, null=False, unique=True)
    profile_image = models.CharField(blank=True, null=True, max_length=255)
    text = models.TextField(blank=True, null=False, max_length=512)
    language = models.CharField(blank=True, null=True, max_length=16)
    geo = models.CharField(blank=True, null=True, max_length=80)
    tweet_user_id = models.BigIntegerField(blank=True, null=False)
    tweet_user_name = models.CharField(blank=True, null=True, max_length=128)
    created_at = models.DateTimeField(blank=True, null=True)
    source = models.CharField(blank=True, null=True, max_length=80)
    dump = models.TextField(blank=True, null=False)
    query = models.CharField(blank=True, null=True, max_length=127)
    race = models.CharField(blank=True, null=True, max_length=16)
    uri = models.CharField(blank=True, null=True, max_length=512)
    
    objects = TweetManager()
    
    class Meta:
        ordering = []
        verbose_name, verbose_name_plural = "Tweet", "Tweets"

    def __unicode__(self):
        return u"Tweet"
    
    def is_duplicated(self):
        try:
            self.__class__.objects.get(tweet_id=self.tweet_id)
            return True
        except self.DoesNotExist:
            return False
    
    @property
    def profile_url(self):
        if self.race == 'weibo':
            return 'http://t.sina.com.cn/%s' % self.tweet_user_id
        else:
            return 'http://twitter.com/#!/%s' % self.tweet_user_name
    
    @classmethod
    def create_from_tweepy_tweet(cls, tweet):
        my_tweet = cls()
        my_tweet.race = 'twitter'
        my_tweet.tweet_id = tweet.id
        my_tweet.profile_image = tweet.profile_image_url
        my_tweet.text = tweet.text
        my_tweet.language = tweet.iso_language_code
        my_tweet.geo = tweet.geo
        my_tweet.tweet_user_id = tweet.from_user_id
        my_tweet.tweet_user_name = tweet.from_user
        my_tweet.created_at = tweet.created_at
        my_tweet.source = tweet.source
        d = tweet.__dict__.copy()
        d.pop('created_at')
        my_tweet.dump = json.dumps(d)
        return my_tweet
    
    @classmethod
    def create_from_weibo_html_fragment(cls, ele):
        t = cls()
        t.dump = html.tostring(ele)
        t.race = 'weibo'
        # tweet_id
        smss = ele.cssselect('.MIB_feed_c .sms')
        if len(smss) == 1:
            t.tweet_id = int(smss[0].get('mid'))
        # profile_image, user_id, user_name
        images = ele.cssselect('.head_pic img')
        if len(images) == 1:
            user_image = images[0]
            t.profile_image = user_image.get('src')
            t.tweet_user_id = int(user_image.get('uid'))
            t.tweet_user_name = user_image.get('title')
        # created_at
        created_ats = ele.cssselect('.feed_att cite strong')
        if len(created_ats) == 1:
            created_at = created_ats[0]
            time_str = created_at.text_content()
            if time_str.find(u'分钟前') != -1:
                minutes = time_str[:time_str.find(u'分钟前')]
                t.created_at = datetime.now() - timedelta(seconds=60*int(minutes))
            elif time_str.find(u'月') != -1:
                this_year = datetime.today().year
                time_str = u'%s年%s' % (this_year, time_str)
                t.created_at = datetime.strptime(time_str.encode('utf-8'), '%Y年%m月%d日 %H:%M')
            else:
                t.created_at = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        # uri
        uris = ele.cssselect(".feed_att a[href^='http://t.sina.com.cn']")
        if len(uris) == 1:
            t.uri = uris[0].get('href')
        # source
        attr = ele.cssselect('.feed_att .lf')
        if len(attr) == 1:
            attr_text = attr[0].text_content()
            idx = attr_text.find(u'来自')
            if idx != -1:
                t.source = attr_text[idx+2:].strip()
        # text
        contents = ele.cssselect('.MIB_feed_c')
        if len(contents) == 1:
            t.text = html.tostring(contents[0])
        return t

    @models.permalink
    def get_absolute_url(self):
        return ('Tweet', [self.id])

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.db import models
from django.core.urlresolvers import reverse
from apps.twitter.models import Tweet
from apps.twitter.test_weibo import WeiboTest

class StatusTest(TestCase):
    def test_tweetspage(self):
        '''测试tweets页面能否正常显示'''
        response = self.client.get(reverse("tweets"))
        self.failUnlessEqual(response.status_code, 200)

class TweetTest(TestCase):
    def test_search(self):
        tweets = Tweet.objects.search(query='#openparty', limit=1)
        t = tweets[0]
        self.assertTrue(t.text)
    
    def test_sync(self):
        tweets = Tweet.objects.search(query='#openparty', limit=2)
        new = tweets[0]
        old = tweets[1]
        self.assertTrue(new.tweet_id > old.tweet_id)
        old.save()
        self.assertEquals(1, Tweet.objects.count())
        new_tweets = Tweet.objects.sync(query='#openparty', since=old.tweet_id)
        self.assertTrue(new_tweets)
        self.assertTrue(Tweet.objects.count() > 1)

__test__ = {}

########NEW FILE########
__FILENAME__ = test_weibo
#!/usr/bin/env python
# encoding: utf-8
from django.test import TestCase
from django.db import models
from django.core.urlresolvers import reverse
from apps.twitter.models import Tweet
from lxml import html
from datetime import datetime, timedelta


weibo_sms_html_frag = u'''
<li id="mid_211101110530573" class="MIB_linedot2">
  <div class="head_pic"><a href="http://t.sina.com.cn/lanyueniao"><img src="http://tp3.sinaimg.cn/1661931502/50/1287680537/1" imgtype="head" uid="1661931502" title="蓝月鸟"></a>
</div>
  <div class="MIB_feed_c">
    <p type="3" mid="211101110530573" class="sms"><a title="蓝月鸟" href="http://t.sina.com.cn/lanyueniao">蓝月鸟</a>：我们是海盗！</p>
    <div class="MIB_assign">
  <div class="MIB_asarrow_l"></div>
  <div class="MIB_assign_t"></div>
  <div class="MIB_assign_c MIB_txtbl"> 
    <p type="2" mid="211101110530573" class="source">
      <a href="http://t.sina.com.cn/1646023983">@cleverpig</a>：继续邀请一位航海家到<a href="http://t.sina.com.cn/k/openparty">#openparty#</a>分享话题，半年前已经邀请过但不巧没有成行，继续努力！祈求上帝保佑～
    <span class="source_att MIB_linkbl"><a href="http://t.sina.com.cn/1646023983/24EN12cPh"><strong lang="CL1005">原文转发</strong><strong type="rttCount" rid="211101110525963">(2)</strong></a><span class="MIB_line_l">|</span><a href="http://t.sina.com.cn/1646023983/24EN12cPh"><strong lang="CC0603">原文评论</strong><strong type="commtCount" rid="211101110525963">(5)</strong></a></span></p>
    <div id="prev_211101110530573" class="feed_preview">
            <div class="clear"></div>
    </div>
    <div style="display:none;" id="disp_211101110530573" class="blogPicOri"> </div>
     </div>
  <div class="MIB_assign_b"></div>
</div>
        <div class="feed_att">
      <div class="lf MIB_txtbl"><cite><a href="http://t.sina.com.cn/1661931502/24EN12e1D"><strong>11月10日 11:19</strong></a></cite>
<strong lang="CL1006">来自</strong><cite><a target="_blank" href="https://chrome.google.com/extensions/detail/aicelmgbddfgmpieedjiggifabdpcnln?hl=zh-cn">FaWave</a></cite></div>
      <div class="rt"><a onclick="App.ModForward('211101110530573','%E7%BB%A7%E7%BB%AD%E9%82%80%E8%AF%B7%E4%B8%80%E4%BD%8D%E8%88%AA%E6%B5%B7%E5%AE%B6%E5%88%B0%3Ca%20href%3D%22http%3A%2F%2Ft.sina.com.cn%2Fk%2Fopenparty%22%3E%23openparty%23%3C%2Fa%3E%E5%88%86%E4%BA%AB%E8%AF%9D%E9%A2%98%EF%BC%8C%E5%8D%8A%E5%B9%B4%E5%89%8D%E5%B7%B2%E7%BB%8F%E9%82%80%E8%AF%B7%E8%BF%87%E4%BD%86%E4%B8%8D%E5%B7%A7%E6%B2%A1%E6%9C%89%E6%88%90%E8%A1%8C%EF%BC%8C%E7%BB%A7%E7%BB%AD%E5%8A%AA%E5%8A%9B%EF%BC%81%E7%A5%88%E6%B1%82%E4%B8%8A%E5%B8%9D%E4%BF%9D%E4%BD%91%EF%BD%9E',0,this,'num_211101110530573','蓝月鸟','%E6%88%91%E4%BB%AC%E6%98%AF%E6%B5%B7%E7%9B%97%EF%BC%81','')" initblogername="cleverpig" initbloger="1646023983" lastforwardername="蓝月鸟" lastforwarder="1661931502" href="javascript:void(0);"><strong lang="CD0023">转发</strong><strong type="rttCount" rid="211101110530573" id="num_211101110530573"></strong></a>
<span class="navBorder">|</span>
<a onclick="App.addfavorite_miniblog('211101110530573');" href="javascript:void(0);"><strong lang="CL1003">收藏</strong></a>
<span class="navBorder">|</span>
<a onclick="scope.loadCommentByRid(1661931502, 'miniblog2', '新浪微博', '211101110530573', '%E6%88%91%E4%BB%AC%E6%98%AF%E6%B5%B7%E7%9B%97%EF%BC%81', '', '', 1, 0, 1);" href="javascript:void(0);" id="_comment_count_miniblog2_211101110530573"><strong lang="CL1004">评论</strong><strong type="commtCount" rid="211101110530573"></strong></a>
</div>
    </div>
    <div id="_comment_list_miniblog2_211101110530573"></div>
  </div>
</li>
'''

class WeiboTest(TestCase):
    # def test_login_to_weibo(self):
    #         post_data = 'client=ssologin.js(v1.3.9)&encoding=utf-8&' +\
    #             'entry=miniblog&from=&gateway=1&password=' + self.password +\
    #             '&returntype=META&savestate=7&service=miniblog&' +\
    #              'url=http%3A%2F%2Ft.sina.com.cn%2Fajaxlogin.php%3Fframelogin%3D1%26c' +\
    #              'allback%3Dparent.sinaSSOController.feedBackUrlCallBack&' +\
    #              'username=' + self.username + '&useticket=0'
    # 
    #         post_url = 'http://login.sina.com.cn/sso/login.php'
    #         
    #         cookie = CookieJar()
    #         opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    #         urllib2.install_opener(opener)
    # 
    #         req = urllib2.Request(url=post_url, data=post_data)
    #         req = self._add_headers(req)
    #         response = urllib2.urlopen(req)
    #         # print dir(response)
    #         
    #         search_req = urllib2.Request(url='http://t.sina.com.cn/k/%2523openparty')
    #         req = self._add_headers(search_req)
    #         response = urllib2.urlopen(search_req)
    #         print response.info()
    #         print response.headers
    #         print response.read()
    #     
    #     def _add_headers(self, req):
    #         req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7')
    #         req.add_header('Referer', 'http://t.sina.com.cn/')
    #         return req
    
    def test_tweet_should_have_id_when_create_it_from_weibo_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals(211101110530573L, t.tweet_id)
    
    def test_tweet_should_have_profile_image_when_create_it_from_weibo_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals('http://tp3.sinaimg.cn/1661931502/50/1287680537/1', t.profile_image)
    
    def test_tweet_should_have_user_id_when_create_it_from_weibo_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals(u'蓝月鸟', t.tweet_user_name)
        self.assertEquals(1661931502L, t.tweet_user_id)
    
    def test_tweet_should_have_created_at_time_when_create_it_from_weibo_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        created_at = datetime(2010, 11, 10, 11, 19)
        self.assertEquals(created_at.strftime('%Y%m%d %H%M%S'), t.created_at.strftime('%Y%m%d %H%M%S'))

        m = weibo_sms_html_frag.replace(u'11月10日 11:19', '2009-8-29 16:55')
        ele = html.fromstring(m)
        t = Tweet.create_from_weibo_html_fragment(ele)
        created_at = datetime(2009, 8, 29, 16, 55)
        self.assertEquals(created_at.strftime('%Y%m%d %H%M%S'), t.created_at.strftime('%Y%m%d %H%M%S'))
        
        m = weibo_sms_html_frag.replace(u'11月10日 11:19', u'18分钟前')
        ele = html.fromstring(m)
        t = Tweet.create_from_weibo_html_fragment(ele)
        created_at = datetime.now() - timedelta(seconds=60*18)
        self.assertEquals(created_at.strftime('%Y%m%d %H%M%S'), t.created_at.strftime('%Y%m%d %H%M%S'))
    
    def test_tweet_should_have_source_when_create_it_from_weibo_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals('FaWave', t.source)
    
    def test_tweet_should_have_dump_which_is_the_original_html_fragment(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals(html.tostring(ele), t.dump)
    
    def test_weibo_tweet_should_be_weibo_race(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals('weibo', t.race)
    
    def test_weibo_tweet_should_have_uri(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        self.assertEquals('http://t.sina.com.cn/1661931502/24EN12e1D', t.uri)
    
    def test_weibo_tweet_should_use_original_content_as_text(self):
        ele = html.fromstring(weibo_sms_html_frag)
        t = Tweet.create_from_weibo_html_fragment(ele)
        ele = html.fromstring(t.text)
        self.assertEquals('MIB_feed_c', ele.get('class'))

__test__ = {}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('twitter.views',
    url(r'^$', 'index', name='tweets'),
    url(r'^/request_oauth$', 'request_oauth', name='request_oauth'),
    url(r'^/oauth_callback$', 'oauth_callback', name='oauth_callback'),
    url(r'^/update$', 'update', name='update_tweet'),
    url(r'^/delete$', 'delete', name='delete_tweet'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
# Create your views here.
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.contrib import messages
import tweepy
from settings import TWITTER_OPENPARTY_KEY, TWITTER_OPENPARTY_SECRET

import hashlib

from apps.twitter.models import Tweet
from apps.member.models import Member


def index(request):
    twitter_enabled = False
    if hasattr(request, 'user'):
        
        admin_mail_sha1_hash = ('c4a1f1d86ccd8981e9ea8cb3027c848d362bacd4', #cnborn
                           '72056e7da242b31ca6638fd208560620062212a9', #tin
                           'f26995abecc6e1edf01e1b9a5e3dc6c0317a49ea', #makestory
                           '0ed17b80ebae26e1b28d9caef21c5425d49f78cb', #conglin
                           '6356945b9581d8049c73ea6e94760c8b2c6303cb', #cleverpig
                           )

        if hashlib.sha1(request.user.username.lower()).hexdigest() in admin_mail_sha1_hash:
            twitter_enabled = True
    tweets = Tweet.objects.order_by('-created_at', '-tweet_id')
    paginator = Paginator(tweets, 50)

    try:
        page_num = int(request.GET.get('page', '1'))
    except ValueError:
        page_num = 1
    
    try:
        page = paginator.page(page_num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    ctx = {
        'page': page,
        'tweets': page.object_list,
        'tab': 'tweet',
        'twitter_enabled': twitter_enabled
    }
    return render_to_response('twitter/index.html', ctx, context_instance=RequestContext(request))

@login_required
def request_oauth(request):
    member = request.user.get_profile()
    auth = tweepy.OAuthHandler(TWITTER_OPENPARTY_KEY, TWITTER_OPENPARTY_SECRET)
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError:
        render_to_response('500.html', {'error_message': u'无法从twitter.com获取redirect url'}, context_instance=RequestContext(request))

    member.twitter_access_token_key = auth.request_token.key
    member.twitter_access_token_secret = auth.request_token.secret
    if member.twitter_enabled:
        member.twitter_enabled = False
    member.save()
    return redirect(redirect_url, permanent=False)

@login_required
def oauth_callback(request):
    member = request.user.get_profile()
    auth = tweepy.OAuthHandler(TWITTER_OPENPARTY_KEY, TWITTER_OPENPARTY_SECRET)
    try:
        auth.set_request_token(member.twitter_access_token_key, member.twitter_access_token_secret)
        auth.get_access_token()
        member.twitter_access_token_key = auth.access_token.key
        member.twitter_access_token_secret = auth.access_token.secret
        member.twitter_enabled = True
        member.save()
        messages.info(request, u'恭喜，您已经成功通过了Twitter的OAuth认证！以后您就可以在这里发推了。')
    except tweepy.TweepError:
        messages.error(request, u'对不起，认证的过程中发生了错误')

    return redirect(reverse('tweets'))

@login_required
def update(request):
    member = request.user.get_profile()
    status = request.POST.get('status')
    if member.twitter_enabled:
        auth = tweepy.OAuthHandler(TWITTER_OPENPARTY_KEY, TWITTER_OPENPARTY_SECRET)
        auth.set_access_token(member.twitter_access_token_key, member.twitter_access_token_secret)
        api = tweepy.API(auth)
        api.update_status(status)
        messages.info(request, u'Sent!')
    else:
        messages.error(request, u'对不起您还没有通过Twitter的OAuth认证')
    return redirect(reverse('tweets'))


@login_required
def delete(request):
    member = request.user.get_profile()
    tweet_id = request.POST.get('tweet_id')
    if member.twitter_enabled:
        tweet = Tweet.objects.get(tweet_id=tweet_id)
        tweet.delete()
        messages.info(request, u'Deleted')
    else:
        messages.error(request, u'对不起您还没有管理员身份')
    return redirect(reverse('tweets'))

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *
# Default release is 'current'
env.name = 'openparty'
env.release = 'current'
env.python_version = '2.7.2'


@task
def production():
    """Production server settings"""
    env.settings = 'production'
    env.user = 'openparty'
    env.path = '/home/%(user)s/sites/openparty-app' % env
    env.hosts = ['zztin.com']


@task
def setup():
    """
    Setup a fresh virtualenv and install everything we need so it's ready to deploy to
    """
    with activate_virtualenv():
        run('mkdir -p %(path)s; cd %(path)s; mkdir releases; mkdir shared;' % env)
        clone_repo()
        checkout_latest()
        install_requirements()


@task
def deploy():
    """Deploy the latest version of the site to the server and restart nginx"""
    with activate_virtualenv():
        checkout_latest()
        install_requirements()
        symlink_current_release()
        migrate()
        restart_server()


def clone_repo():
    """Do initial clone of the git repo"""
    run('cd %(path)s; git clone https://github.com/openparty/openparty.git repository' % env)


def checkout_latest():
    """Pull the latest code into the git repo and copy to a timestamped release directory"""
    import time
    env.release = time.strftime('%Y%m%d%H%M%S')
    run("cd %(path)s/repository; git pull origin master" % env)
    run('cp -R %(path)s/repository %(path)s/releases/%(release)s; rm -rf %(path)s/releases/%(release)s/.git*' % env)


def install_requirements():
    """Install the required packages using pip"""
    """Pip need copy file into system folder, so we need a sudo"""
    run('cd %(path)s; pip install -r ./releases/%(release)s/requirements.txt' % env)


def symlink_current_release():
    """Symlink our current release, uploads and settings file"""
    with settings(warn_only=True):
        run('cd %(path)s; rm releases/previous; mv releases/current releases/previous;' % env)
    run('cd %(path)s; ln -s %(release)s releases/current' % env)
    """ production settings"""
    run('cd %(path)s/releases/current/; cp %(path)s/conf/local_settings.py local_settings.py' % env)
    run('cd %(path)s/releases/current/; cp %(path)s/conf/site-restart site-restart' % env)
    with settings(warn_only=True):
        run('cd %(path)s/releases/current/media; ln -s %(path)s/shared/post_images post_images' % env)
        run('cd %(path)s/releases/current/media; rm -rf upload; ln -s %(path)s/shared/upload upload' % env)
        run('cd %(path)s/releases/current/media; ln -s /usr/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin .' %
            env)
        # run('rm %(path)s/shared/static' % env)
        # run('cd %(path)s/releases/current/static/; ln -s %(path)s/releases/%(release)s/static %(path)s/shared/static ' %env)


def migrate():
    """Run our migrations"""
    run('cd %(path)s/releases/current; python manage.py syncdb --noinput --migrate' % env)
    run('cd %(path)s/releases/current; python manage.py migrate --noinput core' % env)


def rollback():
    """
    Limited rollback capability. Simple loads the previously current
    version of the code. Rolling back again will swap between the two.
    """
    run('cd %(path)s; mv releases/current releases/_previous;' % env)
    run('cd %(path)s; mv releases/previous releases/current;' % env)
    run('cd %(path)s; mv releases/_previous releases/previous;' % env)
    restart_server()


@task
def restart_server():
    """Restart the web server"""
    run('cd %(path)s/releases/current; %(path)s/releases/current/site-restart' % env)
    sudo('/etc/init.d/nginx restart')


def activate_virtualenv():
    return prefix('PATH=/home/%(user)s/.pythonbrew/bin:$PATH source /home/%(user)s/.pythonbrew/etc/bashrc '\
        '&& pythonbrew use %(python_version)s && pythonbrew venv use %(name)s-%(settings)s' % env)


@task
def setup_pythonbrew():
    with prefix('PATH=/home/%(user)s/.pythonbrew/bin:$PATH source /home/%(user)s/.pythonbrew/etc/bashrc' % env):
        run('pythonbrew install %(python_version)s' % env)
        run('pythonbrew switch %(python_version)s' % env)
        run('pythonbrew symlink')
        run('pythonbrew venv init')


@task
def create_venv():
    with prefix('PATH=/home/%(user)s/.pythonbrew/bin:$PATH source /home/%(user)s/.pythonbrew/etc/bashrc && pythonbrew use %(python_version)s' % env):
        run('pythonbrew venv create %(name)s-%(settings)s' % env)
        run('pythonbrew venv use %(name)s-%(settings)s' % env)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
from os.path import join
from django.core.management import execute_manager

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

sys.path.insert(1, join(settings.PROJECT_ROOT, "apps"))
sys.path.insert(1, join(settings.PROJECT_ROOT, "vendor"))

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for openparty project.
import os.path
PROJECT_ROOT = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'openparty',                      # Or path to database file if using sqlite3.
        'USER': 'root',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
}

DATABASE_OPTIONS = {
   "init_command": "SET storage_engine=MYISAM",
}

#EMAIL_BACKEND = 'custom_email_backend.unix_sendmail_backend.EmailBackend'
EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
# EMAIL_USE_TLS = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'zh-cn'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ')x_^bgbj$v_r-5=rn&01pm-5*%szlnc+8^3kh4$^$#z-gn5yo#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    # "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",
    "apps.core.context_processors.global_settings_injection",
)

MIDDLEWARE_CLASSES = (
    'raven.contrib.django.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

LOGIN_URL = '/member/login'

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
    '/usr/local/lib/python2.6/dist-packages/debug_toolbar/templates',
)


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.comments',
    'django.contrib.markup',
    #TODO: take the unittest framework back
    'south',
    'django_xmlrpc',
    'apps.core',
    'apps.member',
    'apps.twitter',
    'debug_toolbar',
    'raven.contrib.django.raven_compat',
)

# One-week activation window; you may, of course, use a different value.
ACCOUNT_ACTIVATION_DAYS = 7
SITE_URL = 'http://www.beijing-open-party.org'

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
INTERNAL_IPS = ('127.0.0.1')

ANALYTICS_ID = 'UA-329713-8'
COMMENT_SYSTEM = 'disqus'#'homebrew'
DISQUS_BRANCH_ID = 'beijing'

TWITTER_OPENPARTY_KEY = "REPLACE_IT_WITH_REAL_VALUE_IN_LOCAL_SETTINGS"
TWITTER_OPENPARTY_SECRET = "REPLACE_IT_WITH_REAL_VALUE_IN_LOCAL_SETTINGS"

AUTH_PROFILE_MODULE = "member.Member"

INTERNAL_IPS = ('114.254.99.95',)

# Sentry is server debuging tool

RAVEN_CONFIG = {
    'dsn': '',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url, handler404
from settings import MEDIA_ROOT
from django.contrib import admin

from apps.core.urls import event_patterns, topic_patterns, feed_patterns, post_patterns, about_patterns, wordpress_redirect_patterns


admin.autodiscover()
urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^member/', include('member.urls')),
    (r'^event/', include(event_patterns)),
    (r'^topic/', include(topic_patterns)),
    (r'^feed/', include(feed_patterns)),
    (r'^post/', include(post_patterns)),
    (r'^tweets', include('twitter.urls')),
    (r'^about/', include(about_patterns)),
    (r'^(?P<year>\d{4})/(?P<month>\d{1,2})/', include(wordpress_redirect_patterns)),
)

urlpatterns += patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': MEDIA_ROOT}),
    (r'^comments/', include('django.contrib.comments.urls')),
)

urlpatterns += patterns('apps.core.views',
    url(r'^index$', 'index', name='index'),
    url(r'^/?$', 'index'),
)

def handler500(request):
    """
    An error handler which exposes the request object to the error template.
    """
    from django.template import Context, loader
    from django.http import HttpResponseServerError
    from raven.contrib.django.models import sentry_exception_handler

    import logging
    import sys

    sentry_exception_handler(request=request)
    context = { 'request': request }

    t = loader.get_template('500.html') # You need to create a 500.html template.
    return HttpResponseServerError(t.render(Context(context)))

########NEW FILE########
__FILENAME__ = unix_sendmail_backend
# -*- coding: utf-8 -*-
"""sendmail email backend class."""

import threading

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from subprocess import Popen,PIPE

class EmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super(EmailBackend, self).__init__(fail_silently=fail_silently)
        self._lock = threading.RLock()

    def open(self):
        return True

    def close(self):
        pass

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return
        self._lock.acquire()
        try:
            num_sent = 0
            for message in email_messages:
                sent = self._send(message)
                if sent:
                    num_sent += 1
        finally:
            self._lock.release()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        try:
            try:
                ps = Popen(["/usr/sbin/sendmail"]+list(email_message.recipients()), stdin=PIPE)
            except OSError:
                ps = Popen(["sendmail"]+list(email_message.recipients()), stdin=PIPE)
            except OSError:
                if not self.fail_silently:
                    raise

            ps.stdin.write(email_message.message().as_string())
            ps.stdin.flush()
            ps.stdin.close()
            return not ps.wait()
        except:
            if not self.fail_silently:
                raise
            return False
        return True

########NEW FILE########
__FILENAME__ = actions
"""
Actions - things like 'a model was removed' or 'a field was changed'.
Each one has a class, which can take the action description and insert code
blocks into the forwards() and backwards() methods, in the right place.
"""

import sys
import datetime

from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT
from django.db.models.fields import FieldDoesNotExist, NOT_PROVIDED

from south import modelsinspector
from south.creator.freezer import remove_useless_attributes, model_key

class Action(object):
    """
    Generic base Action class. Contains utility methods for inserting into
    the forwards() and backwards() method lists.
    """
    
    def forwards_code(self):
        raise NotImplementedError
    
    def backwards_code(self):
        raise NotImplementedError
    
    def add_forwards(self, forwards):
        forwards.append(self.forwards_code())
    
    def add_backwards(self, backwards):
        backwards.append(self.backwards_code())
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        raise NotImplementedError
    
    @classmethod
    def triples_to_defs(cls, fields):
        # Turn the (class, args, kwargs) format into a string
        for field, triple in fields.items():
            fields[field] = cls.triple_to_def(triple)
        return fields
    
    @classmethod
    def triple_to_def(cls, triple):
        "Turns a single triple into a definition."
        return "self.gf(%r)(%s)" % (
            triple[0], # Field full path
            ", ".join(triple[1] + ["%s=%s" % (kwd, val) for kwd, val in triple[2].items()]), # args and kwds
        )
    
    
class AddModel(Action):
    """
    Addition of a model. Takes the Model subclass that is being created.
    """
    
    FORWARDS_TEMPLATE = '''
        # Adding model '%(model_name)s'
        db.create_table(%(table_name)r, (
            %(field_defs)s
        ))
        db.send_create_signal(%(app_label)r, [%(model_name)r])'''
    
    BACKWARDS_TEMPLATE = '''
        # Deleting model '%(model_name)s'
        db.delete_table(%(table_name)r)'''

    def __init__(self, model, model_def):
        self.model = model
        self.model_def = model_def
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Added model %s.%s" % (
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )

    def forwards_code(self):
        "Produces the code snippet that gets put into forwards()"
        field_defs = ",\n            ".join([
            "(%r, %s)" % (name, defn) for name, defn
            in self.triples_to_defs(self.model_def).items()
        ]) + ","
        
        return self.FORWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "app_label": self.model._meta.app_label,
            "field_defs": field_defs,
        }

    def backwards_code(self):
        "Produces the code snippet that gets put into backwards()"
        return self.BACKWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
        }
    
    
class DeleteModel(AddModel):
    """
    Deletion of a model. Takes the Model subclass that is being created.
    """
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " - Deleted model %s.%s" % (
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )

    def forwards_code(self):
        return AddModel.backwards_code(self)

    def backwards_code(self):
        return AddModel.forwards_code(self)
    
    
class AddField(Action):
    """
    Adds a field to a model. Takes a Model class and the field name.
    """
    
    FORWARDS_TEMPLATE = '''
        # Adding field '%(model_name)s.%(field_name)s'
        db.add_column(%(table_name)r, %(field_name)r, %(field_def)s, keep_default=False)'''
    
    BACKWARDS_TEMPLATE = '''
        # Deleting field '%(model_name)s.%(field_name)s'
        db.delete_column(%(table_name)r, %(field_column)r)'''
    
    def __init__(self, model, field, field_def):
        self.model = model
        self.field = field
        self.field_def = field_def
        
        # See if they've made a NOT NULL column but also have no default (far too common)
        is_null = self.field.null
        default = (self.field.default is not None) and (self.field.default is not NOT_PROVIDED)
        
        if not is_null and not default:
            # Oh dear. Ask them what to do.
            print " ? The field '%s.%s' does not have a default specified, yet is NOT NULL." % (
                self.model._meta.object_name,
                self.field.name,
            )
            print " ? Since you are adding or removing this field, you MUST specify a default"
            print " ? value to use for existing rows. Would you like to:"
            print " ?  1. Quit now, and add a default to the field in models.py"
            print " ?  2. Specify a one-off value to use for existing columns now"
            while True: 
                choice = raw_input(" ? Please select a choice: ")
                if choice == "1":
                    sys.exit(1)
                elif choice == "2":
                    break
                else:
                    print " ! Invalid choice."
            # OK, they want to pick their own one-time default. Who are we to refuse?
            print " ? Please enter Python code for your one-off default value."
            print " ? The datetime module is available, so you can do e.g. datetime.date.today()"
            while True:
                code = raw_input(" >>> ")
                if not code:
                    print " ! Please enter some code, or 'exit' (with no quotes) to exit."
                elif code == "exit":
                    sys.exit(1)
                else:
                    try:
                        result = eval(code, {}, {"datetime": datetime})
                    except (SyntaxError, NameError), e:
                        print " ! Invalid input: %s" % e
                    else:
                        break
            # Right, add the default in.
            self.field_def[2]['default'] = repr(result)
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Added field %s on %s.%s" % (
            self.field.name,
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        
        return self.FORWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "field_name": self.field.name,
            "field_column": self.field.column,
            "field_def": self.triple_to_def(self.field_def),
        }

    def backwards_code(self):
        return self.BACKWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "field_name": self.field.name,
            "field_column": self.field.column,
        }
    
    
class DeleteField(AddField):
    """
    Removes a field from a model. Takes a Model class and the field name.
    """
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " - Deleted field %s on %s.%s" % (
            self.field.name,
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        return AddField.backwards_code(self)

    def backwards_code(self):
        return AddField.forwards_code(self)



class ChangeField(Action):
    """
    Changes a field's type/options on a model.
    """
    
    FORWARDS_TEMPLATE = BACKWARDS_TEMPLATE = '''
        # Changing field '%(model_name)s.%(field_name)s'
        db.alter_column(%(table_name)r, %(field_column)r, %(field_def)s)'''
    
    RENAME_TEMPLATE = '''
        # Renaming column for '%(model_name)s.%(field_name)s' to match new field type.
        db.rename_column(%(table_name)r, %(old_column)r, %(new_column)r)'''
    
    def __init__(self, model, old_field, new_field, old_def, new_def):
        self.model = model
        self.old_field = old_field
        self.new_field = new_field
        self.old_def = old_def
        self.new_def = new_def
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " ~ Changed field %s on %s.%s" % (
            self.new_field.name,
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def _code(self, old_field, new_field, new_def):
        
        output = ""
        
        if self.old_field.column != self.new_field.column:
            output += self.RENAME_TEMPLATE % {
                "model_name": self.model._meta.object_name,
                "table_name": self.model._meta.db_table,
                "field_name": new_field.name,
                "old_column": old_field.column,
                "new_column": new_field.column,
            }
        
        output += self.FORWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "field_name": new_field.name,
            "field_column": new_field.column,
            "field_def": self.triple_to_def(new_def),
        }
        
        return output

    def forwards_code(self):
        return self._code(self.old_field, self.new_field, self.new_def)

    def backwards_code(self):
        return self._code(self.new_field, self.old_field, self.old_def)


class AddUnique(Action):
    """
    Adds a unique constraint to a model. Takes a Model class and the field names.
    """
    
    FORWARDS_TEMPLATE = '''
        # Adding unique constraint on '%(model_name)s', fields %(field_names)s
        db.create_unique(%(table_name)r, %(fields)r)'''
    
    BACKWARDS_TEMPLATE = '''
        # Removing unique constraint on '%(model_name)s', fields %(field_names)s
        db.delete_unique(%(table_name)r, %(fields)r)'''
    
    def __init__(self, model, fields):
        self.model = model
        self.fields = fields
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Added unique constraint for %s on %s.%s" % (
            [x.name for x in self.fields],
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        
        return self.FORWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "fields":  [field.column for field in self.fields],
            "field_names":  [field.name for field in self.fields],
        }

    def backwards_code(self):
        return self.BACKWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "table_name": self.model._meta.db_table,
            "fields": [field.column for field in self.fields],
            "field_names":  [field.name for field in self.fields],
        }


class DeleteUnique(AddUnique):
    """
    Removes a unique constraint from a model. Takes a Model class and the field names.
    """
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " - Deleted unique constraint for %s on %s.%s" % (
            [x.name for x in self.fields],
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        return AddUnique.backwards_code(self)

    def backwards_code(self):
        return AddUnique.forwards_code(self)


class AddIndex(AddUnique):
    """
    Adds an index to a model field[s]. Takes a Model class and the field names.
    """
    
    FORWARDS_TEMPLATE = '''
        # Adding index on '%(model_name)s', fields %(field_names)s
        db.create_index(%(table_name)r, %(fields)r)'''
    
    BACKWARDS_TEMPLATE = '''
        # Removing index on '%(model_name)s', fields %(field_names)s
        db.delete_index(%(table_name)r, %(fields)r)'''
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Added index for %s on %s.%s" % (
            [x.name for x in self.fields],
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )


class DeleteIndex(AddIndex):
    """
    Deletes an index off a model field[s]. Takes a Model class and the field names.
    """
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Deleted index for %s on %s.%s" % (
            [x.name for x in self.fields],
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        return AddIndex.backwards_code(self)

    def backwards_code(self):
        return AddIndex.forwards_code(self)


class AddM2M(Action):
    """
    Adds a unique constraint to a model. Takes a Model class and the field names.
    """
    
    FORWARDS_TEMPLATE = '''
        # Adding M2M table for field %(field_name)s on '%(model_name)s'
        db.create_table(%(table_name)r, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            (%(left_field)r, models.ForeignKey(orm[%(left_model_key)r], null=False)),
            (%(right_field)r, models.ForeignKey(orm[%(right_model_key)r], null=False))
        ))
        db.create_unique(%(table_name)r, [%(left_column)r, %(right_column)r])'''
    
    BACKWARDS_TEMPLATE = '''
        # Removing M2M table for field %(field_name)s on '%(model_name)s'
        db.delete_table('%(table_name)s')'''
    
    def __init__(self, model, field):
        self.model = model
        self.field = field
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " + Added M2M table for %s on %s.%s" % (
            self.field.name,
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        
        return self.FORWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "field_name": self.field.name,
            "table_name": self.field.m2m_db_table(),
            "left_field": self.field.m2m_column_name()[:-3], # Remove the _id part
            "left_column": self.field.m2m_column_name(),
            "left_model_key": model_key(self.model),
            "right_field": self.field.m2m_reverse_name()[:-3], # Remove the _id part
            "right_column": self.field.m2m_reverse_name(),
            "right_model_key": model_key(self.field.rel.to),
        }

    def backwards_code(self):
        
        return self.BACKWARDS_TEMPLATE % {
            "model_name": self.model._meta.object_name,
            "field_name": self.field.name,
            "table_name": self.field.m2m_db_table(),
        }


class DeleteM2M(AddM2M):
    """
    Adds a unique constraint to a model. Takes a Model class and the field names.
    """
    
    def console_line(self):
        "Returns the string to print on the console, e.g. ' + Added field foo'"
        return " - Deleted M2M table for %s on %s.%s" % (
            self.field.name,
            self.model._meta.app_label, 
            self.model._meta.object_name,
        )
    
    def forwards_code(self):
        return AddM2M.backwards_code(self)

    def backwards_code(self):
        return AddM2M.forwards_code(self)
    
########NEW FILE########
__FILENAME__ = changes
"""
Contains things to detect changes - either using options passed in on the
commandline, or by using autodetection, etc.
"""

from django.db import models
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.datastructures import SortedDict

from south.creator.freezer import remove_useless_attributes, freeze_apps, model_key
from south.utils import auto_through

class BaseChanges(object):
    """
    Base changes class.
    """
    def suggest_name(self):
        return ''
    
    def split_model_def(self, model, model_def):
        """
        Given a model and its model def (a dict of field: triple), returns three
        items: the real fields dict, the Meta dict, and the M2M fields dict.
        """
        real_fields = SortedDict()
        meta = SortedDict()
        m2m_fields = SortedDict()
        for name, triple in model_def.items():
            if name == "Meta":
                meta = triple
            elif isinstance(model._meta.get_field_by_name(name)[0], models.ManyToManyField):
                m2m_fields[name] = triple
            else:
                real_fields[name] = triple
        return real_fields, meta, m2m_fields
    
    def current_model_from_key(self, key):
        app_label, model_name = key.split(".")
        return models.get_model(app_label, model_name)
    
    def current_field_from_key(self, key, fieldname):
        app_label, model_name = key.split(".")
        # Special, for the magical field from order_with_respect_to
        if fieldname == "_order":
            field = models.IntegerField()
            field.name = "_order"
            field.attname = "_order"
            field.column = "_order"
            field.default = 0
            return field
        # Otherwise, normal.
        return models.get_model(app_label, model_name)._meta.get_field_by_name(fieldname)[0]


class AutoChanges(BaseChanges):
    """
    Detects changes by 'diffing' two sets of frozen model definitions.
    """
    
    # Field types we don't generate add/remove field changes for.
    IGNORED_FIELD_TYPES = [
        GenericRelation,
    ]
    
    def __init__(self, migrations, old_defs, old_orm, new_defs):
        self.migrations = migrations
        self.old_defs = old_defs
        self.old_orm = old_orm
        self.new_defs = new_defs
    
    def suggest_name(self):
        parts = ["auto"]
        for change_name, params in self.get_changes():
            if change_name == "AddModel":
                parts.append("add_%s" % params['model']._meta.object_name.lower())
            elif change_name == "DeleteModel":
                parts.append("del_%s" % params['model']._meta.object_name.lower())
            elif change_name == "AddField":
                parts.append("add_field_%s_%s" % (
                    params['model']._meta.object_name.lower(),
                    params['field'].name,
                ))
            elif change_name == "DeleteField":
                parts.append("del_field_%s_%s" % (
                    params['model']._meta.object_name.lower(),
                    params['field'].name,
                ))
            elif change_name == "ChangeField":
                parts.append("chg_field_%s_%s" % (
                    params['model']._meta.object_name.lower(),
                    params['new_field'].name,
                ))
            elif change_name == "AddUnique":
                parts.append("add_unique_%s_%s" % (
                    params['model']._meta.object_name.lower(),
                    "_".join([x.name for x in params['fields']]),
                ))
            elif change_name == "DeleteUnique":
                parts.append("del_unique_%s_%s" % (
                    params['model']._meta.object_name.lower(),
                    "_".join([x.name for x in params['fields']]),
                ))
        return ("__".join(parts))[:70]
    
    def get_changes(self):
        """
        Returns the difference between the old and new sets of models as a 5-tuple:
        added_models, deleted_models, added_fields, deleted_fields, changed_fields
        """
        
        deleted_models = set()
        
        # See if anything's vanished
        for key in self.old_defs:
            if key not in self.new_defs:
                # We shouldn't delete it if it was managed=False
                if self.old_defs[key].get("Meta", {}).get("managed", "True") != "False":
                    old_fields, old_meta, old_m2ms = self.split_model_def(self.old_orm[key], self.old_defs[key])
                    # Alright, delete it.
                    yield ("DeleteModel", {
                        "model": self.old_orm[key], 
                        "model_def": old_fields,
                    })
                    # Also make sure we delete any M2Ms it had.
                    for fieldname in old_m2ms:
                        # Only delete its stuff if it wasn't a through=.
                        field = self.old_orm[key + ":" + fieldname]
                        if auto_through(field):
                            yield ("DeleteM2M", {"model": self.old_orm[key], "field": field})
                # We always add it in here so we ignore it later
                deleted_models.add(key)
        
        # Or appeared
        for key in self.new_defs:
            if key not in self.old_defs:
                # We shouldn't add it if it's managed=False
                if self.new_defs[key].get("Meta", {}).get("managed", "True") != "False":
                    new_fields, new_meta, new_m2ms = self.split_model_def(self.current_model_from_key(key), self.new_defs[key])
                    yield ("AddModel", {
                        "model": self.current_model_from_key(key), 
                        "model_def": new_fields,
                    })
                    # Also make sure we add any M2Ms it has.
                    for fieldname in new_m2ms:
                        # Only create its stuff if it wasn't a through=.
                        field = self.current_field_from_key(key, fieldname)
                        if auto_through(field):
                            yield ("AddM2M", {"model": self.current_model_from_key(key), "field": field})
        
        # Now, for every model that's stayed the same, check its fields.
        for key in self.old_defs:
            if key not in deleted_models:
                
                still_there = set()
                
                old_fields, old_meta, old_m2ms = self.split_model_def(self.old_orm[key], self.old_defs[key])
                new_fields, new_meta, new_m2ms = self.split_model_def(self.current_model_from_key(key), self.new_defs[key])
                
                # Find fields that have vanished.
                for fieldname in old_fields:
                    if fieldname not in new_fields:
                        # Don't do it for any fields we're ignoring
                        field = self.old_orm[key + ":" + fieldname]
                        field_allowed = True
                        for field_type in self.IGNORED_FIELD_TYPES:
                            if isinstance(field, field_type):
                                field_allowed = False
                        if field_allowed:
                            # Looks alright.
                            yield ("DeleteField", {
                                "model": self.old_orm[key],
                                "field": field,
                                "field_def": old_fields[fieldname],
                            })
                
                # And ones that have appeared
                for fieldname in new_fields:
                    if fieldname not in old_fields:
                        # Don't do it for any fields we're ignoring
                        field = self.current_field_from_key(key, fieldname)
                        field_allowed = True
                        for field_type in self.IGNORED_FIELD_TYPES:
                            if isinstance(field, field_type):
                                field_allowed = False
                        if field_allowed:
                            # Looks alright.
                            yield ("AddField", {
                                "model": self.current_model_from_key(key),
                                "field": field,
                                "field_def": new_fields[fieldname],
                            })
                
                # Find M2Ms that have vanished
                for fieldname in old_m2ms:
                    if fieldname not in new_m2ms:
                        # Only delete its stuff if it wasn't a through=.
                        field = self.old_orm[key + ":" + fieldname]
                        if auto_through(field):
                            yield ("DeleteM2M", {"model": self.old_orm[key], "field": field})
                
                # Find M2Ms that have appeared
                for fieldname in new_m2ms:
                    if fieldname not in old_m2ms:
                        # Only create its stuff if it wasn't a through=.
                        field = self.current_field_from_key(key, fieldname)
                        if auto_through(field):
                            yield ("AddM2M", {"model": self.current_model_from_key(key), "field": field})
                
                # For the ones that exist in both models, see if they were changed
                for fieldname in set(old_fields).intersection(set(new_fields)):
                    # Non-index changes
                    if self.different_attributes(
                     remove_useless_attributes(old_fields[fieldname], True, True),
                     remove_useless_attributes(new_fields[fieldname], True, True)):
                        yield ("ChangeField", {
                            "model": self.current_model_from_key(key),
                            "old_field": self.old_orm[key + ":" + fieldname],
                            "new_field": self.current_field_from_key(key, fieldname),
                            "old_def": old_fields[fieldname],
                            "new_def": new_fields[fieldname],
                        })
                    # Index changes
                    old_field = self.old_orm[key + ":" + fieldname]
                    new_field = self.current_field_from_key(key, fieldname)
                    if not old_field.db_index and new_field.db_index:
                        # They've added an index.
                        yield ("AddIndex", {
                            "model": self.current_model_from_key(key),
                            "fields": [new_field],
                        })
                    if old_field.db_index and not new_field.db_index:
                        # They've removed an index.
                        yield ("DeleteIndex", {
                            "model": self.old_orm[key],
                            "fields": [old_field],
                        })
                    # See if their uniques have changed
                    if old_field.unique != new_field.unique:
                        # Make sure we look at the one explicitly given to see what happened
                        if new_field.unique:
                            yield ("AddUnique", {
                                "model": self.current_model_from_key(key),
                                "fields": [new_field],
                            })
                        else:
                            yield ("DeleteUnique", {
                                "model": self.old_orm[key],
                                "fields": [old_field],
                            })
                
                # See if there's any M2Ms that have changed.
                for fieldname in set(old_m2ms).intersection(set(new_m2ms)):
                    old_field = self.old_orm[key + ":" + fieldname]
                    new_field = self.current_field_from_key(key, fieldname)
                    # Have they _added_ a through= ?
                    if auto_through(old_field) and not auto_through(new_field):
                        yield ("DeleteM2M", {"model": self.old_orm[key], "field": old_field})
                    # Have they _removed_ a through= ?
                    if not auto_through(old_field) and auto_through(new_field):
                        yield ("AddM2M", {"model": self.current_model_from_key(key), "field": new_field})
                
                ## See if the unique_togethers have changed
                # First, normalise them into lists of sets.
                old_unique_together = eval(old_meta.get("unique_together", "[]"))
                new_unique_together = eval(new_meta.get("unique_together", "[]"))
                if old_unique_together and isinstance(old_unique_together[0], basestring):
                    old_unique_together = [old_unique_together]
                if new_unique_together and isinstance(new_unique_together[0], basestring):
                    new_unique_together = [new_unique_together]
                old_unique_together = map(set, old_unique_together)
                new_unique_together = map(set, new_unique_together)
                # See if any appeared or disappeared
                for item in old_unique_together:
                    if item not in new_unique_together:
                        yield ("DeleteUnique", {
                            "model": self.old_orm[key],
                            "fields": [self.old_orm[key + ":" + x] for x in item],
                        })
                for item in new_unique_together:
                    if item not in old_unique_together:
                        yield ("AddUnique", {
                            "model": self.current_model_from_key(key),
                            "fields": [self.current_field_from_key(key, x) for x in item],
                        })

    @classmethod
    def is_triple(cls, triple):
        "Returns whether the argument is a triple."
        return isinstance(triple, (list, tuple)) and len(triple) == 3 and \
            isinstance(triple[0], (str, unicode)) and \
            isinstance(triple[1], (list, tuple)) and \
            isinstance(triple[2], dict)

    @classmethod
    def different_attributes(cls, old, new):
        """
        Backwards-compat comparison that ignores orm. on the RHS and not the left
        and which knows django.db.models.fields.CharField = models.CharField.
        Has a whole load of tests in tests/autodetection.py.
        """
        
        # If they're not triples, just do normal comparison
        if not cls.is_triple(old) or not cls.is_triple(new):
            return old != new
        
        # Expand them out into parts
        old_field, old_pos, old_kwd = old
        new_field, new_pos, new_kwd = new
        
        # Copy the positional and keyword arguments so we can compare them and pop off things
        old_pos, new_pos = old_pos[:], new_pos[:]
        old_kwd = dict(old_kwd.items())
        new_kwd = dict(new_kwd.items())
        
        # Remove comparison of the existence of 'unique', that's done elsewhere.
        # TODO: Make this work for custom fields where unique= means something else?
        if "unique" in old_kwd:
            del old_kwd['unique']
        if "unique" in new_kwd:
            del new_kwd['unique']
        
        # If the first bit is different, check it's not by dj.db.models...
        if old_field != new_field:
            if old_field.startswith("models.") and (new_field.startswith("django.db.models") \
             or new_field.startswith("django.contrib.gis")):
                if old_field.split(".")[-1] != new_field.split(".")[-1]:
                    return True
                else:
                    # Remove those fields from the final comparison
                    old_field = new_field = ""
        
        # If there's a positional argument in the first, and a 'to' in the second,
        # see if they're actually comparable.
        if (old_pos and "to" in new_kwd) and ("orm" in new_kwd['to'] and "orm" not in old_pos[0]):
            # Do special comparison to fix #153
            try:
                if old_pos[0] != new_kwd['to'].split("'")[1].split(".")[1]:
                    return True
            except IndexError:
                pass # Fall back to next comparison
            # Remove those attrs from the final comparison
            old_pos = old_pos[1:]
            del new_kwd['to']
        
        return old_field != new_field or old_pos != new_pos or old_kwd != new_kwd


class ManualChanges(BaseChanges):
    """
    Detects changes by reading the command line.
    """
    
    def __init__(self, migrations, added_models, added_fields, added_indexes):
        self.migrations = migrations
        self.added_models = added_models
        self.added_fields = added_fields
        self.added_indexes = added_indexes
    
    def suggest_name(self):
        bits = []
        for model_name in self.added_models:
            bits.append('add_model_%s' % model_name)
        for field_name in self.added_fields:
            bits.append('add_field_%s' % field_name)
        for index_name in self.added_indexes:
            bits.append('add_index_%s' % index_name)
        return '_'.join(bits)
    
    def get_changes(self):
        # Get the model defs so we can use them for the yield later
        model_defs = freeze_apps([self.migrations.app_label()])
        # Make the model changes
        for model_name in self.added_models:
            model = models.get_model(self.migrations.app_label(), model_name)
            real_fields, meta, m2m_fields = self.split_model_def(model, model_defs[model_key(model)])
            yield ("AddModel", {
                "model": model,
                "model_def": real_fields,
            })
        # And the field changes
        for field_desc in self.added_fields:
            try:
                model_name, field_name = field_desc.split(".")
            except (TypeError, ValueError):
                print "%r is not a valid field description." % field_desc
            model = models.get_model(self.migrations.app_label(), model_name)
            real_fields, meta, m2m_fields = self.split_model_def(model, model_defs[model_key(model)])
            yield ("AddField", {
                "model": model,
                "field": model._meta.get_field_by_name(field_name)[0],
                "field_def": real_fields[field_name],
            })
        # And the indexes
        for field_desc in self.added_indexes:
            try:
                model_name, field_name = field_desc.split(".")
            except (TypeError, ValueError):
                print "%r is not a valid field description." % field_desc
            model = models.get_model(self.migrations.app_label(), model_name)
            yield ("AddIndex", {
                "model": model,
                "fields": [model._meta.get_field_by_name(field_name)[0]],
            })
    
    
class InitialChanges(BaseChanges):
    """
    Creates all models; handles --initial.
    """
    def suggest_name(self):
        return 'initial'
    
    def __init__(self, migrations):
        self.migrations = migrations
    
    def get_changes(self):
        # Get the frozen models for this app
        model_defs = freeze_apps([self.migrations.app_label()])
        
        for model in models.get_models(models.get_app(self.migrations.app_label())):
            
            # Don't do anything for unmanaged, abstract or proxy models
            if model._meta.abstract or getattr(model._meta, "proxy", False) or not getattr(model._meta, "managed", True):
                continue
            
            real_fields, meta, m2m_fields = self.split_model_def(model, model_defs[model_key(model)])
            
            # Firstly, add the main table and fields
            yield ("AddModel", {
                "model": model,
                "model_def": real_fields,
            })
            
            # Then, add any uniqueness that's around
            if meta:
                unique_together = eval(meta.get("unique_together", "[]"))
                if unique_together:
                    # If it's only a single tuple, make it into the longer one
                    if isinstance(unique_together[0], basestring):
                        unique_together = [unique_together]
                    # For each combination, make an action for it
                    for fields in unique_together:
                        yield ("AddUnique", {
                            "model": model,
                            "fields": [model._meta.get_field_by_name(x)[0] for x in fields],
                        })
            
            # Finally, see if there's some M2M action
            for name, triple in m2m_fields.items():
                field = model._meta.get_field_by_name(name)[0]
                # But only if it's not through=foo (#120)
                if field.rel.through:
                    try:
                        # Django 1.1 and below
                        through_model = field.rel.through_model
                    except AttributeError:
                        # Django 1.2
                        through_model = field.rel.through
                if (not field.rel.through) or getattr(through_model._meta, "auto_created", False):
                    yield ("AddM2M", {
                        "model": model,
                        "field": field,
                    })
########NEW FILE########
__FILENAME__ = freezer
"""
Handles freezing of models into FakeORMs.
"""

import sys

from django.db import models
from django.contrib.contenttypes.generic import GenericRelation

from south.orm import FakeORM
from south.utils import auto_model
from south import modelsinspector

def freeze_apps(apps):
    """
    Takes a list of app labels, and returns a string of their frozen form.
    """
    if isinstance(apps, basestring):
        apps = [apps]
    frozen_models = set()
    # For each app, add in all its models
    for app in apps:
        for model in models.get_models(models.get_app(app)):
            # Only add if it's not abstract or proxy
            if not model._meta.abstract and not getattr(model._meta, "proxy", False):
                frozen_models.add(model)
    # Now, add all the dependencies
    for model in list(frozen_models):
        frozen_models.update(model_dependencies(model))
    # Serialise!
    model_defs = {}
    for model in frozen_models:
        model_defs[model_key(model)] = prep_for_freeze(model)
    # Check for any custom fields that failed to freeze.
    missing_fields = False
    for key, fields in model_defs.items():
        for field_name, value in fields.items():
            if value is None:
                missing_fields = True
                print " ! Cannot freeze field '%s.%s'" % (key, field_name)
    if missing_fields:
        print ""
        print " ! South cannot introspect some fields; this is probably because they are custom"
        print " ! fields. If they worked in 0.6 or below, this is because we have removed the"
        print " ! models parser (it often broke things)."
        print " ! To fix this, read http://south.aeracode.org/wiki/MyFieldsDontWork"
        sys.exit(1)
    
    return model_defs
    
def freeze_apps_to_string(apps):
    return pprint_frozen_models(freeze_apps(apps))
    
### 

def model_key(model):
    "For a given model, return 'appname.modelname'."
    return "%s.%s" % (model._meta.app_label, model._meta.object_name.lower())

def prep_for_freeze(model):
    """
    Takes a model and returns the ready-to-serialise dict (all you need
    to do is just pretty-print it).
    """
    fields = modelsinspector.get_model_fields(model, m2m=True)
    # Remove useless attributes (like 'choices')
    for name, field in fields.items():
        fields[name] = remove_useless_attributes(field)
    # See if there's a Meta
    fields['Meta'] = remove_useless_meta(modelsinspector.get_model_meta(model))
    # Add in our own special items to track the object name and managed
    fields['Meta']['object_name'] = model._meta.object_name # Special: not eval'able.
    if not getattr(model._meta, "managed", True):
        fields['Meta']['managed'] = repr(model._meta.managed)
    return fields

### Dependency resolvers

def model_dependencies(model, checked_models=None):
    """
    Returns a set of models this one depends on to be defined; things like
    OneToOneFields as ID, ForeignKeys everywhere, etc.
    """
    depends = set()
    checked_models = checked_models or set()
    # Get deps for each field
    for field in model._meta.fields + model._meta.many_to_many:
        depends.update(field_dependencies(field))
    # Add in any non-abstract bases
    for base in model.__bases__:
        if issubclass(base, models.Model) and (base is not models.Model) and not base._meta.abstract:
            depends.add(base)
    # Now recurse
    new_to_check = depends - checked_models
    while new_to_check:
        checked_model = new_to_check.pop()
        if checked_model == model or checked_model in checked_models:
            continue
        checked_models.add(checked_model)
        deps = model_dependencies(checked_model, checked_models)
        # Loop through dependencies...
        for dep in deps:
            # If the new dep is not already checked, add to the queue
            if (dep not in depends) and (dep not in new_to_check) and (dep not in checked_models):
                new_to_check.add(dep)
            depends.add(dep)
    return depends

def field_dependencies(field, checked_models=None):
    checked_models = checked_models or set()
    depends = set()
    if isinstance(field, (models.OneToOneField, models.ForeignKey, models.ManyToManyField, GenericRelation)):
        if field.rel.to in checked_models:
            return depends
        checked_models.add(field.rel.to)
        depends.add(field.rel.to)
        depends.update(field_dependencies(field.rel.to._meta.pk, checked_models))
        # Also include M2M throughs
        if isinstance(field, models.ManyToManyField):
            if field.rel.through:
                if hasattr(field.rel, "through_model"): # 1.1 and below
                    depends.add(field.rel.through_model)
                else:
                    # Make sure it's not an automatic one
                    if not auto_model(field.rel.through):
                        depends.add(field.rel.through) # 1.2 and up
    return depends

### Prettyprinters

def pprint_frozen_models(models):
    return "{\n        %s\n    }" % ",\n        ".join([
        "%r: %s" % (name, pprint_fields(fields))
        for name, fields in sorted(models.items())
    ])

def pprint_fields(fields):
    return "{\n            %s\n        }" % ",\n            ".join([
        "%r: %r" % (name, defn)
        for name, defn in sorted(fields.items())
    ])

### Output sanitisers

USELESS_KEYWORDS = ["choices", "help_text", "upload_to", "verbose_name", "storage"]
USELESS_DB_KEYWORDS = ["related_name", "default"] # Important for ORM, not for DB.
INDEX_KEYWORDS = ["db_index"]

def remove_useless_attributes(field, db=False, indexes=False):
    "Removes useless (for database) attributes from the field's defn."
    # Work out what to remove, and remove it.
    keywords = USELESS_KEYWORDS[:]
    if db:
        keywords += USELESS_DB_KEYWORDS[:]
    if indexes:
        keywords += INDEX_KEYWORDS[:]
    if field:
        for name in keywords:
            if name in field[2]:
                del field[2][name]
    return field

USELESS_META = ["verbose_name", "verbose_name_plural"]
def remove_useless_meta(meta):
    "Removes useless (for database) attributes from the table's meta."
    if meta:
        for name in USELESS_META:
            if name in meta:
                del meta[name]
    return meta
########NEW FILE########
__FILENAME__ = generic

import datetime
import string
import random
import re
import sys

from django.core.management.color import no_style
from django.db import transaction, models
from django.db.backends.util import truncate_name
from django.db.models.fields import NOT_PROVIDED
from django.dispatch import dispatcher
from django.conf import settings
from django.utils.datastructures import SortedDict

from south.logger import get_logger

def alias(attrname):
    """
    Returns a function which calls 'attrname' - for function aliasing.
    We can't just use foo = bar, as this breaks subclassing.
    """
    def func(self, *args, **kwds):
        return getattr(self, attrname)(*args, **kwds)
    return func


class DatabaseOperations(object):

    """
    Generic SQL implementation of the DatabaseOperations.
    Some of this code comes from Django Evolution.
    """

    # We assume the generic DB can handle DDL transactions. MySQL wil change this.
    has_ddl_transactions = True

    alter_string_set_type = 'ALTER COLUMN %(column)s TYPE %(type)s'
    alter_string_set_null = 'ALTER COLUMN %(column)s DROP NOT NULL'
    alter_string_drop_null = 'ALTER COLUMN %(column)s SET NOT NULL'
    has_check_constraints = True
    delete_check_sql = 'ALTER TABLE %(table)s DROP CONSTRAINT %(constraint)s'
    allows_combined_alters = True
    add_column_string = 'ALTER TABLE %s ADD COLUMN %s;'
    delete_unique_sql = "ALTER TABLE %s DROP CONSTRAINT %s"
    delete_foreign_key_sql = 'ALTER TABLE %(table)s DROP CONSTRAINT %(constraint)s'
    supports_foreign_keys = True
    max_index_name_length = 63
    drop_index_string = 'DROP INDEX %(index_name)s'
    delete_column_string = 'ALTER TABLE %s DROP COLUMN %s CASCADE;'
    create_primary_key_string = "ALTER TABLE %(table)s ADD CONSTRAINT %(constraint)s PRIMARY KEY (%(columns)s)"
    delete_primary_key_sql = "ALTER TABLE %(table)s DROP CONSTRAINT %(constraint)s"
    backend_name = None

    def __init__(self, db_alias):
        self.debug = False
        self.deferred_sql = []
        self.dry_run = False
        self.pending_transactions = 0
        self.pending_create_signals = []
        self.db_alias = db_alias
        self.connection_init()
    
    def _is_multidb(self):
        try: 
            from django.db import connections
        except ImportError:
            return False
        else:
            return True

    def _get_connection(self): 
        """ 
        Returns a django connection for a given DB Alias 
        """
        if self._is_multidb():
            from django.db import connections 
            return connections[self.db_alias] 
        else:
            from django.db import connection 
            return connection 

    def _get_setting(self, setting_name):
        """
        Allows code to get a setting (like, for example, STORAGE_ENGINE)
        """
        setting_name = setting_name.upper()
        connection = self._get_connection() 
        if self._is_multidb():
            # Django 1.2 and above
            return connection.settings_dict[setting_name] 
        else:
            # Django 1.1 and below
            return getattr(settings, "DATABASE_%s" % setting_name)

    def _has_setting(self, setting_name):
        """
        Existence-checking version of _get_setting.
        """
        try:
            self._get_setting(setting_name)
        except (KeyError, AttributeError):
            return False
        else:
            return True

    def connection_init(self):
        """
        Run before any SQL to let database-specific config be sent as a command,
        e.g. which storage engine (MySQL) or transaction serialisability level.
        """
        pass
    
    def quote_name(self, name):
        """
        Uses the database backend to quote the given table/column name.
        """
        return self._get_connection().ops.quote_name(name)

    def execute(self, sql, params=[]):
        """
        Executes the given SQL statement, with optional parameters.
        If the instance's debug attribute is True, prints out what it executes.
        """
        cursor = self._get_connection().cursor()
        if self.debug:
            print "   = %s" % sql, params

        get_logger().debug('south execute "%s" with params "%s"' % (sql, params))

        if self.dry_run:
            return []

        cursor.execute(sql, params)
        try:
            return cursor.fetchall()
        except:
            return []


    def execute_many(self, sql, regex=r"(?mx) ([^';]* (?:'[^']*'[^';]*)*)", comment_regex=r"(?mx) (?:^\s*$)|(?:--.*$)"):
        """
        Takes a SQL file and executes it as many separate statements.
        (Some backends, such as Postgres, don't work otherwise.)
        """
        # Be warned: This function is full of dark magic. Make sure you really
        # know regexes before trying to edit it.
        # First, strip comments
        sql = "\n".join([x.strip().replace("%", "%%") for x in re.split(comment_regex, sql) if x.strip()])
        # Now execute each statement
        for st in re.split(regex, sql)[1:][::2]:
            self.execute(st)


    def add_deferred_sql(self, sql):
        """
        Add a SQL statement to the deferred list, that won't be executed until
        this instance's execute_deferred_sql method is run.
        """
        self.deferred_sql.append(sql)


    def execute_deferred_sql(self):
        """
        Executes all deferred SQL, resetting the deferred_sql list
        """
        for sql in self.deferred_sql:
            self.execute(sql)

        self.deferred_sql = []


    def clear_deferred_sql(self):
        """
        Resets the deferred_sql list to empty.
        """
        self.deferred_sql = []


    def clear_run_data(self, pending_creates = None):
        """
        Resets variables to how they should be before a run. Used for dry runs.
        If you want, pass in an old panding_creates to reset to.
        """
        self.clear_deferred_sql()
        self.pending_create_signals = pending_creates or []


    def get_pending_creates(self):
        return self.pending_create_signals


    def create_table(self, table_name, fields):
        """
        Creates the table 'table_name'. 'fields' is a tuple of fields,
        each repsented by a 2-part tuple of field name and a
        django.db.models.fields.Field object
        """

        if len(table_name) > 63:
            print "   ! WARNING: You have a table name longer than 63 characters; this will not fully work on PostgreSQL or MySQL."

        columns = [
            self.column_sql(table_name, field_name, field)
            for field_name, field in fields
        ]

        self.execute('CREATE TABLE %s (%s);' % (
            self.quote_name(table_name),
            ', '.join([col for col in columns if col]),
        ))

    add_table = alias('create_table') # Alias for consistency's sake


    def rename_table(self, old_table_name, table_name):
        """
        Renames the table 'old_table_name' to 'table_name'.
        """
        if old_table_name == table_name:
            # Short-circuit out.
            return
        params = (self.quote_name(old_table_name), self.quote_name(table_name))
        self.execute('ALTER TABLE %s RENAME TO %s;' % params)


    def delete_table(self, table_name, cascade=True):
        """
        Deletes the table 'table_name'.
        """
        params = (self.quote_name(table_name), )
        if cascade:
            self.execute('DROP TABLE %s CASCADE;' % params)
        else:
            self.execute('DROP TABLE %s;' % params)

    drop_table = alias('delete_table')


    def clear_table(self, table_name):
        """
        Deletes all rows from 'table_name'.
        """
        params = (self.quote_name(table_name), )
        self.execute('DELETE FROM %s;' % params)



    def add_column(self, table_name, name, field, keep_default=True):
        """
        Adds the column 'name' to the table 'table_name'.
        Uses the 'field' paramater, a django.db.models.fields.Field instance,
        to generate the necessary sql

        @param table_name: The name of the table to add the column to
        @param name: The name of the column to add
        @param field: The field to use
        """
        sql = self.column_sql(table_name, name, field)
        if sql:
            params = (
                self.quote_name(table_name),
                sql,
            )
            sql = self.add_column_string % params
            self.execute(sql)

            # Now, drop the default if we need to
            if not keep_default and field.default is not None:
                field.default = NOT_PROVIDED
                self.alter_column(table_name, name, field, explicit_name=False, ignore_constraints=True)


    def _db_type_for_alter_column(self, field):
        """
        Returns a field's type suitable for ALTER COLUMN.
        By default it just returns field.db_type().
        To be overriden by backend specific subclasses
        @param field: The field to generate type for
        """
        try:
            return field.db_type(connection=self._get_connection())
        except TypeError:
            return field.db_type()
        
    def _alter_set_defaults(self, field, name, params, sqls): 
        "Subcommand of alter_column that sets default values (overrideable)"
        # Next, set any default
        if not field.null and field.has_default():
            default = field.get_default()
            sqls.append(('ALTER COLUMN %s SET DEFAULT %%s ' % (self.quote_name(name),), [default]))
        else:
            sqls.append(('ALTER COLUMN %s DROP DEFAULT' % (self.quote_name(name),), []))

    def alter_column(self, table_name, name, field, explicit_name=True, ignore_constraints=False):
        """
        Alters the given column name so it will match the given field.
        Note that conversion between the two by the database must be possible.
        Will not automatically add _id by default; to have this behavour, pass
        explicit_name=False.

        @param table_name: The name of the table to add the column to
        @param name: The name of the column to alter
        @param field: The new field definition to use
        """

        # hook for the field to do any resolution prior to it's attributes being queried
        if hasattr(field, 'south_init'):
            field.south_init()

        # Add _id or whatever if we need to
        field.set_attributes_from_name(name)
        if not explicit_name:
            name = field.column
        else:
            field.column = name

        if not ignore_constraints:
            # Drop all check constraints. TODO: Add the right ones back.
            if self.has_check_constraints:
                check_constraints = self._constraints_affecting_columns(table_name, [name], "CHECK")
                for constraint in check_constraints:
                    self.execute(self.delete_check_sql % {
                        'table': self.quote_name(table_name),
                        'constraint': self.quote_name(constraint),
                    })
        
            # Drop all foreign key constraints
            try:
                self.delete_foreign_key(table_name, name)
            except ValueError:
                # There weren't any
                pass

        # First, change the type
        params = {
            "column": self.quote_name(name),
            "type": self._db_type_for_alter_column(field)            
        }

        # SQLs is a list of (SQL, values) pairs.
        sqls = [(self.alter_string_set_type % params, [])]

        # Next, nullity
        if field.null:
            sqls.append((self.alter_string_set_null % params, []))
        else:
            sqls.append((self.alter_string_drop_null % params, []))

        # Next, set any default
        self._alter_set_defaults(field, name, params, sqls)

        # Finally, actually change the column
        if self.allows_combined_alters:
            sqls, values = zip(*sqls)
            self.execute(
                "ALTER TABLE %s %s;" % (self.quote_name(table_name), ", ".join(sqls)),
                flatten(values),
            )
        else:
            # Databases like e.g. MySQL don't like more than one alter at once.
            for sql, values in sqls:
                self.execute("ALTER TABLE %s %s;" % (self.quote_name(table_name), sql), values)
        
        if not ignore_constraints:
            # Add back FK constraints if needed
            if field.rel and self.supports_foreign_keys:
                self.execute(
                    self.foreign_key_sql(
                        table_name,
                        field.column,
                        field.rel.to._meta.db_table,
                        field.rel.to._meta.get_field(field.rel.field_name).column
                    )
                )


    def _constraints_affecting_columns(self, table_name, columns, type="UNIQUE"):
        """
        Gets the names of the constraints affecting the given columns.
        If columns is None, returns all constraints of the type on the table.
        """

        if self.dry_run:
            raise ValueError("Cannot get constraints for columns during a dry run.")

        if columns is not None:
            columns = set(columns)

        if type == "CHECK":
            ifsc_table = "constraint_column_usage"
        else:
            ifsc_table = "key_column_usage"

        # First, load all constraint->col mappings for this table.
        rows = self.execute("""
            SELECT kc.constraint_name, kc.column_name
            FROM information_schema.%s AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %%s AND
                kc.table_name = %%s AND
                c.constraint_type = %%s
        """ % ifsc_table, ['public', table_name, type])
        
        # Load into a dict
        mapping = {}
        for constraint, column in rows:
            mapping.setdefault(constraint, set())
            mapping[constraint].add(column)
        
        # Find ones affecting these columns
        for constraint, itscols in mapping.items():
            # If columns is None we definitely want this field! (see docstring)
            if itscols == columns or columns is None:
                yield constraint

    def create_unique(self, table_name, columns):
        """
        Creates a UNIQUE constraint on the columns on the given table.
        """

        if not isinstance(columns, (list, tuple)):
            columns = [columns]

        name = self.create_index_name(table_name, columns, suffix="_uniq")

        cols = ", ".join(map(self.quote_name, columns))
        self.execute("ALTER TABLE %s ADD CONSTRAINT %s UNIQUE (%s)" % (
            self.quote_name(table_name), 
            self.quote_name(name), 
            cols,
        ))
        return name

    def delete_unique(self, table_name, columns):
        """
        Deletes a UNIQUE constraint on precisely the columns on the given table.
        """

        if not isinstance(columns, (list, tuple)):
            columns = [columns]

        # Dry runs mean we can't do anything.
        if self.dry_run:
            return

        constraints = list(self._constraints_affecting_columns(table_name, columns))
        if not constraints:
            raise ValueError("Cannot find a UNIQUE constraint on table %s, columns %r" % (table_name, columns))
        for constraint in constraints:
            self.execute(self.delete_unique_sql % (
                self.quote_name(table_name), 
                self.quote_name(constraint),
            ))


    def column_sql(self, table_name, field_name, field, tablespace='', with_name=True, field_prepared=False):
        """
        Creates the SQL snippet for a column. Used by add_column and add_table.
        """

        # If the field hasn't already been told its attribute name, do so.
        if not field_prepared:
            field.set_attributes_from_name(field_name)

        # hook for the field to do any resolution prior to it's attributes being queried
        if hasattr(field, 'south_init'):
            field.south_init()

        # Possible hook to fiddle with the fields (e.g. defaults & TEXT on MySQL)
        field = self._field_sanity(field)

        try:
            sql = field.db_type(connection=self._get_connection())
        except TypeError:
            sql = field.db_type()
        
        if sql:
            
            # Some callers, like the sqlite stuff, just want the extended type.
            if with_name:
                field_output = [self.quote_name(field.column), sql]
            else:
                field_output = [sql]
            
            field_output.append('%sNULL' % (not field.null and 'NOT ' or ''))
            if field.primary_key:
                field_output.append('PRIMARY KEY')
            elif field.unique:
                # Just use UNIQUE (no indexes any more, we have delete_unique)
                field_output.append('UNIQUE')

            tablespace = field.db_tablespace or tablespace
            if tablespace and self._get_connection().features.supports_tablespaces and field.unique:
                # We must specify the index tablespace inline, because we
                # won't be generating a CREATE INDEX statement for this field.
                field_output.append(self._get_connection().ops.tablespace_sql(tablespace, inline=True))
            
            sql = ' '.join(field_output)
            sqlparams = ()
            # if the field is "NOT NULL" and a default value is provided, create the column with it
            # this allows the addition of a NOT NULL field to a table with existing rows
            if not field.null and not getattr(field, '_suppress_default', False) and field.has_default():
                default = field.get_default()
                # If the default is actually None, don't add a default term
                if default is not None:
                    # If the default is a callable, then call it!
                    if callable(default):
                        default = default()
                    # Now do some very cheap quoting. TODO: Redesign return values to avoid this.
                    if isinstance(default, basestring):
                        default = "'%s'" % default.replace("'", "''")
                    elif isinstance(default, (datetime.date, datetime.time, datetime.datetime)):
                        default = "'%s'" % default
                    # Escape any % signs in the output (bug #317)
                    if isinstance(default, basestring):
                        default = default.replace("%", "%%")
                    # Add it in
                    sql += " DEFAULT %s"
                    sqlparams = (default)
            elif (not field.null and field.blank) or ((field.get_default() == '') and (not getattr(field, '_suppress_default', False))):
                if field.empty_strings_allowed and self._get_connection().features.interprets_empty_strings_as_nulls:
                    sql += " DEFAULT ''"
                # Error here would be nice, but doesn't seem to play fair.
                #else:
                #    raise ValueError("Attempting to add a non null column that isn't character based without an explicit default value.")

            if field.rel and self.supports_foreign_keys:
                self.add_deferred_sql(
                    self.foreign_key_sql(
                        table_name,
                        field.column,
                        field.rel.to._meta.db_table,
                        field.rel.to._meta.get_field(field.rel.field_name).column
                    )
                )

        # Things like the contrib.gis module fields have this in 1.1 and below
        if hasattr(field, 'post_create_sql'):
            for stmt in field.post_create_sql(no_style(), table_name):
                self.add_deferred_sql(stmt)
        
        # In 1.2 and above, you have to ask the DatabaseCreation stuff for it.
        # This also creates normal indexes in 1.1.
        if hasattr(self._get_connection().creation, "sql_indexes_for_field"):
            # Make a fake model to pass in, with only db_table
            model = self.mock_model("FakeModelForGISCreation", table_name)
            for stmt in self._get_connection().creation.sql_indexes_for_field(model, field, no_style()):
                self.add_deferred_sql(stmt)
        
        if sql:
            return sql % sqlparams
        else:
            return None


    def _field_sanity(self, field):
        """
        Placeholder for DBMS-specific field alterations (some combos aren't valid,
        e.g. DEFAULT and TEXT on MySQL)
        """
        return field


    def foreign_key_sql(self, from_table_name, from_column_name, to_table_name, to_column_name):
        """
        Generates a full SQL statement to add a foreign key constraint
        """
        constraint_name = '%s_refs_%s_%x' % (from_column_name, to_column_name, abs(hash((from_table_name, to_table_name))))
        return 'ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s (%s)%s;' % (
            self.quote_name(from_table_name),
            self.quote_name(truncate_name(constraint_name, self._get_connection().ops.max_name_length())),
            self.quote_name(from_column_name),
            self.quote_name(to_table_name),
            self.quote_name(to_column_name),
            self._get_connection().ops.deferrable_sql() # Django knows this
        )
    

    def delete_foreign_key(self, table_name, column):
        "Drop a foreign key constraint"
        if self.dry_run:
            return # We can't look at the DB to get the constraints
        constraints = list(self._constraints_affecting_columns(table_name, [column], "FOREIGN KEY"))
        if not constraints:
            raise ValueError("Cannot find a FOREIGN KEY constraint on table %s, column %s" % (table_name, column))
        for constraint_name in constraints:
            self.execute(self.delete_foreign_key_sql % {
                "table": self.quote_name(table_name),
                "constraint": self.quote_name(constraint_name),
            })

    drop_foreign_key = alias('delete_foreign_key')


    def create_index_name(self, table_name, column_names, suffix=""):
        """
        Generate a unique name for the index
        """
        index_unique_name = ''

        if len(column_names) > 1:
            index_unique_name = '_%x' % abs(hash((table_name, ','.join(column_names))))

        # If the index name is too long, truncate it
        index_name = ('%s_%s%s%s' % (table_name, column_names[0], index_unique_name, suffix))
        if len(index_name) > self.max_index_name_length:
            part = ('_%s%s%s' % (column_names[0], index_unique_name, suffix))
            index_name = '%s%s' % (table_name[:(self.max_index_name_length-len(part))], part)

        return index_name


    def create_index_sql(self, table_name, column_names, unique=False, db_tablespace=''):
        """
        Generates a create index statement on 'table_name' for a list of 'column_names'
        """
        if not column_names:
            print "No column names supplied on which to create an index"
            return ''

        connection = self._get_connection()
        if db_tablespace and self._get_connection().features.supports_tablespaces:
            tablespace_sql = ' ' + self._get_connection().ops.tablespace_sql(db_tablespace)
        else:
            tablespace_sql = ''

        index_name = self.create_index_name(table_name, column_names)
        return 'CREATE %sINDEX %s ON %s (%s)%s;' % (
            unique and 'UNIQUE ' or '',
            self.quote_name(index_name),
            self.quote_name(table_name),
            ','.join([self.quote_name(field) for field in column_names]),
            tablespace_sql
        )

    def create_index(self, table_name, column_names, unique=False, db_tablespace=''):
        """ Executes a create index statement """
        sql = self.create_index_sql(table_name, column_names, unique, db_tablespace)
        self.execute(sql)


    def delete_index(self, table_name, column_names, db_tablespace=''):
        """
        Deletes an index created with create_index.
        This is possible using only columns due to the deterministic
        index naming function which relies on column names.
        """
        if isinstance(column_names, (str, unicode)):
            column_names = [column_names]
        name = self.create_index_name(table_name, column_names)
        sql = self.drop_index_string % {
            "index_name": self.quote_name(name),
            "table_name": self.quote_name(table_name),
        }
        self.execute(sql)

    drop_index = alias('delete_index')


    def delete_column(self, table_name, name):
        """
        Deletes the column 'column_name' from the table 'table_name'.
        """
        params = (self.quote_name(table_name), self.quote_name(name))
        self.execute(self.delete_column_string % params, [])

    drop_column = alias('delete_column')


    def rename_column(self, table_name, old, new):
        """
        Renames the column 'old' from the table 'table_name' to 'new'.
        """
        raise NotImplementedError("rename_column has no generic SQL syntax")


    def delete_primary_key(self, table_name):
        """
        Drops the old primary key.
        """
        # Dry runs mean we can't do anything.
        if self.dry_run:
            return
        
        constraints = list(self._constraints_affecting_columns(table_name, None, type="PRIMARY KEY"))
        if not constraints:
            raise ValueError("Cannot find a PRIMARY KEY constraint on table %s" % (table_name,))
        
        for constraint in constraints:
            self.execute(self.delete_primary_key_sql % {
                "table": self.quote_name(table_name),
                "constraint": self.quote_name(constraint),
            })
    
    drop_primary_key = alias('delete_primary_key')


    def create_primary_key(self, table_name, columns):
        """
        Creates a new primary key on the specified columns.
        """
        if not isinstance(columns, (list, tuple)):
            columns = [columns]
        self.execute(self.create_primary_key_string % {
            "table": self.quote_name(table_name),
            "constraint": self.quote_name(table_name+"_pkey"),
            "columns": ", ".join(map(self.quote_name, columns)),
        })


    def start_transaction(self):
        """
        Makes sure the following commands are inside a transaction.
        Must be followed by a (commit|rollback)_transaction call.
        """
        if self.dry_run:
            self.pending_transactions += 1
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)


    def commit_transaction(self):
        """
        Commits the current transaction.
        Must be preceded by a start_transaction call.
        """
        if self.dry_run:
            return
        transaction.commit()
        transaction.leave_transaction_management()


    def rollback_transaction(self):
        """
        Rolls back the current transaction.
        Must be preceded by a start_transaction call.
        """
        if self.dry_run:
            self.pending_transactions -= 1
        transaction.rollback()
        transaction.leave_transaction_management()

    def rollback_transactions_dry_run(self):
        """
        Rolls back all pending_transactions during this dry run.
        """
        if not self.dry_run:
            return
        while self.pending_transactions > 0:
            self.rollback_transaction()
        if transaction.is_dirty():
            # Force an exception, if we're still in a dirty transaction.
            # This means we are missing a COMMIT/ROLLBACK.
            transaction.leave_transaction_management()


    def send_create_signal(self, app_label, model_names):
        self.pending_create_signals.append((app_label, model_names))


    def send_pending_create_signals(self, verbosity=0, interactive=False):
        # Group app_labels together
        signals = SortedDict()
        for (app_label, model_names) in self.pending_create_signals:
            try:
                signals[app_label].extend(model_names)
            except KeyError:
                signals[app_label] = list(model_names)
        # Send only one signal per app.
        for (app_label, model_names) in signals.iteritems():
            self.really_send_create_signal(app_label, list(set(model_names)),
                                           verbosity=verbosity,
                                           interactive=interactive)
        self.pending_create_signals = []


    def really_send_create_signal(self, app_label, model_names,
                                  verbosity=0, interactive=False):
        """
        Sends a post_syncdb signal for the model specified.

        If the model is not found (perhaps it's been deleted?),
        no signal is sent.

        TODO: The behavior of django.contrib.* apps seems flawed in that
        they don't respect created_models.  Rather, they blindly execute
        over all models within the app sending the signal.  This is a
        patch we should push Django to make  For now, this should work.
        """
        
        if self.debug:
            print " - Sending post_syncdb signal for %s: %s" % (app_label, model_names)
        
        app = models.get_app(app_label)
        if not app:
            return

        created_models = []
        for model_name in model_names:
            model = models.get_model(app_label, model_name)
            if model:
                created_models.append(model)

        if created_models:

            if hasattr(dispatcher, "send"):
                # Older djangos
                dispatcher.send(signal=models.signals.post_syncdb, sender=app,
                                app=app, created_models=created_models,
                                verbosity=verbosity, interactive=interactive)
            else:
                if self._is_multidb():
                    # Django 1.2+
                    models.signals.post_syncdb.send(
                        sender=app,
                        app=app,
                        created_models=created_models,
                        verbosity=verbosity,
                        interactive=interactive,
                        db=self.db_alias,
                    )
                else:
                    # Django 1.1 - 1.0
                    models.signals.post_syncdb.send(
                        sender=app,
                        app=app,
                        created_models=created_models,
                        verbosity=verbosity,
                        interactive=interactive,
                    )


    def mock_model(self, model_name, db_table, db_tablespace='', 
                   pk_field_name='id', pk_field_type=models.AutoField,
                   pk_field_args=[], pk_field_kwargs={}):
        """
        Generates a MockModel class that provides enough information
        to be used by a foreign key/many-to-many relationship.

        Migrations should prefer to use these rather than actual models
        as models could get deleted over time, but these can remain in
        migration files forever.

        Depreciated.
        """
        class MockOptions(object):
            def __init__(self):
                self.db_table = db_table
                self.db_tablespace = db_tablespace or settings.DEFAULT_TABLESPACE
                self.object_name = model_name
                self.module_name = model_name.lower()

                if pk_field_type == models.AutoField:
                    pk_field_kwargs['primary_key'] = True

                self.pk = pk_field_type(*pk_field_args, **pk_field_kwargs)
                self.pk.set_attributes_from_name(pk_field_name)
                self.abstract = False

            def get_field_by_name(self, field_name):
                # we only care about the pk field
                return (self.pk, self.model, True, False)

            def get_field(self, name):
                # we only care about the pk field
                return self.pk

        class MockModel(object):
            _meta = None

        # We need to return an actual class object here, not an instance
        MockModel._meta = MockOptions()
        MockModel._meta.model = MockModel
        return MockModel


# Single-level flattening of lists
def flatten(ls):
    nl = []
    for l in ls:
        nl += l
    return nl

########NEW FILE########
__FILENAME__ = mysql

from django.db import connection
from django.conf import settings
from south.db import generic

class DatabaseOperations(generic.DatabaseOperations):

    """
    MySQL implementation of database operations.
    
    MySQL is an 'interesting' database; it has no DDL transaction support,
    among other things. This can confuse people when they ask how they can
    roll back - hence the dry runs, etc., found in the migration code.
    Alex agrees, and Alex is always right.
    [19:06] <Alex_Gaynor> Also, I want to restate once again that MySQL is a special database
    
    (Still, if you want a key-value store with relational tendancies, go MySQL!)
    """
    
    backend_name = "mysql"
    alter_string_set_type = ''
    alter_string_set_null = 'MODIFY %(column)s %(type)s NULL;'
    alter_string_drop_null = 'MODIFY %(column)s %(type)s NOT NULL;'
    drop_index_string = 'DROP INDEX %(index_name)s ON %(table_name)s'
    delete_primary_key_sql = "ALTER TABLE %(table)s DROP PRIMARY KEY"
    delete_foreign_key_sql = "ALTER TABLE %(table)s DROP FOREIGN KEY %(constraint)s"
    allows_combined_alters = False
    has_ddl_transactions = False
    has_check_constraints = False
    delete_unique_sql = "ALTER TABLE %s DROP INDEX %s"
    
    
    def connection_init(self):
        """
        Run before any SQL to let database-specific config be sent as a command,
        e.g. which storage engine (MySQL) or transaction serialisability level.
        """
        cursor = self._get_connection().cursor()
        if self._has_setting('STORAGE_ENGINE') and self._get_setting('STORAGE_ENGINE'):
            cursor.execute("SET storage_engine=%s;" % self._get_setting('STORAGE_ENGINE'))
        # Turn off foreign key checks, and turn them back on at the end
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        self.deferred_sql.append("SET FOREIGN_KEY_CHECKS=1;")

    
    def rename_column(self, table_name, old, new):
        if old == new or self.dry_run:
            return []
        
        rows = [x for x in self.execute('DESCRIBE %s' % (self.quote_name(table_name),)) if x[0] == old]
        
        if not rows:
            raise ValueError("No column '%s' in '%s'." % (old, table_name))
        
        params = (
            self.quote_name(table_name),
            self.quote_name(old),
            self.quote_name(new),
            rows[0][1],
            rows[0][2] == "YES" and "NULL" or "NOT NULL",
            rows[0][4] and "DEFAULT " or "",
            rows[0][4] and "%s" or "",
            rows[0][5] or "",
        )
        
        sql = 'ALTER TABLE %s CHANGE COLUMN %s %s %s %s %s %s %s;' % params
        
        if rows[0][4]:
            self.execute(sql, (rows[0][4],))
        else:
            self.execute(sql)
    
    
    def delete_column(self, table_name, name):
        db_name = self._get_setting('NAME')
        
        # See if there is a foreign key on this column
        cursor = self._get_connection().cursor()
        get_fkeyname_query = "SELECT tc.constraint_name FROM \
                              information_schema.table_constraints tc, \
                              information_schema.key_column_usage kcu \
                              WHERE tc.table_name=kcu.table_name \
                              AND tc.table_schema=kcu.table_schema \
                              AND tc.constraint_name=kcu.constraint_name \
                              AND tc.constraint_type='FOREIGN KEY' \
                              AND tc.table_schema='%s' \
                              AND tc.table_name='%s' \
                              AND kcu.column_name='%s'"

        result = cursor.execute(get_fkeyname_query % (db_name, table_name, name))
        
        # If a foreign key exists, we need to delete it first
        if result > 0:
            assert result == 1 # We should only have one result, otherwise there's Issues
            fkey_name = cursor.fetchone()[0]
            drop_query = "ALTER TABLE %s DROP FOREIGN KEY %s"
            cursor.execute(drop_query % (self.quote_name(table_name), self.quote_name(fkey_name)))

        super(DatabaseOperations, self).delete_column(table_name, name)

    
    def rename_table(self, old_table_name, table_name):
        """
        Renames the table 'old_table_name' to 'table_name'.
        """
        if old_table_name == table_name:
            # No Operation
            return
        params = (self.quote_name(old_table_name), self.quote_name(table_name))
        self.execute('RENAME TABLE %s TO %s;' % params)
    
    
    def _constraints_affecting_columns(self, table_name, columns, type="UNIQUE"):
        """
        Gets the names of the constraints affecting the given columns.
        If columns is None, returns all constraints of the type on the table.
        """
        
        if self.dry_run:
            raise ValueError("Cannot get constraints for columns during a dry run.")
        
        if columns is not None:
            columns = set(columns)
        
        db_name = self._get_setting('NAME')
        
        # First, load all constraint->col mappings for this table.
        rows = self.execute("""
            SELECT kc.constraint_name, kc.column_name
            FROM information_schema.key_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %s AND
                kc.table_catalog IS NULL AND
                kc.table_name = %s AND
                c.constraint_type = %s
        """, [db_name, table_name, type])
        
        # Load into a dict
        mapping = {}
        for constraint, column in rows:
            mapping.setdefault(constraint, set())
            mapping[constraint].add(column)
        
        # Find ones affecting these columns
        for constraint, itscols in mapping.items():
            if itscols == columns or columns is None:
                yield constraint
    
    
    def _field_sanity(self, field):
        """
        This particular override stops us sending DEFAULTs for BLOB/TEXT columns.
        """
        if self._db_type_for_alter_column(field).upper() in ["BLOB", "TEXT", "LONGTEXT"]:
            field._suppress_default = True
        return field
    
    
    def _alter_set_defaults(self, field, name, params, sqls):
        """
        MySQL does not support defaults on text or blob columns.
        """
        type = params['type']
        if not (type.endswith('text') or type.endswith('blob')):
            super(DatabaseOperations, self)._alter_set_defaults(field, name, params, sqls)

########NEW FILE########
__FILENAME__ = oracle
import os.path
import re
import cx_Oracle

from django.db import connection, models
from django.db.backends.util import truncate_name
from django.core.management.color import no_style
from django.db.backends.oracle.base import get_sequence_name
from django.db.models.fields import NOT_PROVIDED
from south.db import generic

print " ! WARNING: South's Oracle support is still alpha."
print " !          Be wary of posible bugs."

class DatabaseOperations(generic.DatabaseOperations):    
    """
    Oracle implementation of database operations.    
    """
    backend_name = 'oracle'

    alter_string_set_type =     'ALTER TABLE %(table_name)s MODIFY "%(column)s" %(type)s %(nullity)s;'
    alter_string_set_default =  'ALTER TABLE %(table_name)s MODIFY "%(column)s" DEFAULT %(default)s;'
    add_column_string =         'ALTER TABLE %s ADD %s;'
    delete_column_string =      'ALTER TABLE %s DROP COLUMN %s;'

    allows_combined_alters = False
    
    constraits_dict = {
        'PRIMARY KEY': 'P',
        'UNIQUE': 'U',
        'CHECK': 'C',
        'REFERENCES': 'R'
    }
    table_names_cache = set()

    def adj_column_sql(self, col):
        col = re.sub('(?P<constr>CHECK \(.*\))(?P<any>.*)(?P<default>DEFAULT [0|1])', 
                     lambda mo: '%s %s%s'%(mo.group('default'), mo.group('constr'), mo.group('any')), col) #syntax fix for boolean field only
        col = re.sub('(?P<not_null>NOT NULL) (?P<default>DEFAULT.+)',
                     lambda mo: '%s %s'%(mo.group('default'), mo.group('not_null')), col) #fix order  of DEFAULT and NOT NULL
        return col

    def check_m2m(self, table_name):
        m2m_table_name = table_name
        existing_tables = []

        if not self.table_names_cache:
            self.check_meta(table_name)
            self.table_names_cache = set(connection.introspection.table_names())
        tn = table_name.rsplit('_', 1)

        while len(tn) == 2:
            tn2qn = self.quote_name(tn[0], upper = False, check_m2m = False) 
            if tn2qn in self.table_names_cache:
                m2m_table_name = table_name.replace(tn[0], tn2qn)
                break
            else:
                if not existing_tables:
                    existing_tables = connection.introspection.table_names()
                if tn2qn in existing_tables:
                    m2m_table_name = table_name.replace(tn[0], tn2qn)
                    break
            tn = tn[0].rsplit('_', 1)

        self.table_names_cache.add(m2m_table_name)
        return m2m_table_name

    def check_meta(self, table_name):
        return table_name in [ m._meta.db_table for m in models.get_models() ] #caching provided by Django

    def quote_name(self, name, upper=True, column = False, check_m2m = True):
        if not column:
            if check_m2m:
                name = self.check_m2m(name)
            if self.check_meta(name): #replication of Django flow for models where Meta.db_table is set by user
                name = name.upper()
        tn = truncate_name(name, connection.ops.max_name_length())

        return upper and tn.upper() or tn.lower()

    def create_table(self, table_name, fields): 
        qn = self.quote_name(table_name, upper = False)
        qn_upper = qn.upper()
        columns = []
        autoinc_sql = ''

        for field_name, field in fields:
            col = self.column_sql(qn_upper, field_name, field)
            if not col:
                continue
            col = self.adj_column_sql(col)

            columns.append(col)
            if isinstance(field, models.AutoField):
                autoinc_sql = connection.ops.autoinc_sql(self.check_meta(table_name) and table_name or qn, field_name)

        sql = 'CREATE TABLE %s (%s);' % (qn_upper, ', '.join([col for col in columns]))
        self.execute(sql)
        if autoinc_sql:
            self.execute(autoinc_sql[0])
            self.execute(autoinc_sql[1])

    def delete_table(self, table_name, cascade=True):
        qn = self.quote_name(table_name, upper = False)

        if cascade:
            self.execute('DROP TABLE %s CASCADE CONSTRAINTS PURGE;' % qn.upper())
        else:
            self.execute('DROP TABLE %s;' % qn.upper())
        self.execute('DROP SEQUENCE %s;'%get_sequence_name(qn))

    def alter_column(self, table_name, name, field, explicit_name=True):
        qn = self.quote_name(table_name)

        # hook for the field to do any resolution prior to it's attributes being queried
        if hasattr(field, 'south_init'):
            field.south_init()
        field = self._field_sanity(field)

        # Add _id or whatever if we need to
        field.set_attributes_from_name(name)
        if not explicit_name:
            name = field.column
        qn_col = self.quote_name(name, column = True)

        # First, change the type
        params = {
            'table_name':qn,
            'column': qn_col,
            'type': self._db_type_for_alter_column(field),
            'nullity': 'NOT NULL',
            'default': 'NULL'
        }
        if field.null:
            params['nullity'] = ''
        sqls = [self.alter_string_set_type % params]

        if not field.null and field.has_default():
            params['default'] = field.get_default()

        sqls.append(self.alter_string_set_default % params)

        #UNIQUE constraint
        unique_constraint = list(self._constraints_affecting_columns(qn, [qn_col]))

        if field.unique and not unique_constraint:
            self.create_unique(qn, [qn_col])
        elif not field.unique and unique_constraint:
            self.delete_unique(qn, [qn_col])

        #CHECK constraint is not handled

        for sql in sqls:
            try:
                self.execute(sql)
            except cx_Oracle.DatabaseError, exc:
                if str(exc).find('ORA-01442') == -1:
                    raise

    def add_column(self, table_name, name, field, keep_default=True):
        qn = self.quote_name(table_name, upper = False)
        sql = self.column_sql(qn, name, field)
        sql = self.adj_column_sql(sql)

        if sql:
            params = (
                qn.upper(),
                sql
            )
            sql = self.add_column_string % params
            self.execute(sql)

            # Now, drop the default if we need to
            if not keep_default and field.default is not None:
                field.default = NOT_PROVIDED
                self.alter_column(table_name, name, field, explicit_name=False)

    def delete_column(self, table_name, name):
        return super(DatabaseOperations, self).delete_column(self.quote_name(table_name), name)

    def _field_sanity(self, field):
        """
        This particular override stops us sending DEFAULTs for BooleanField.
        """
        if isinstance(field, models.BooleanField) and field.has_default():
            field.default = int(field.to_python(field.get_default()))
        return field

    def _constraints_affecting_columns(self, table_name, columns, type='UNIQUE'):
        """
        Gets the names of the constraints affecting the given columns.
        """
        qn = self.quote_name

        if self.dry_run:
            raise ValueError("Cannot get constraints for columns during a dry run.")
        columns = set(columns)
        rows = self.execute("""
            SELECT user_cons_columns.constraint_name, user_cons_columns.column_name
            FROM user_constraints
            JOIN user_cons_columns ON
                 user_constraints.table_name = user_cons_columns.table_name AND 
                 user_constraints.constraint_name = user_cons_columns.constraint_name
            WHERE user_constraints.table_name = '%s' AND
                  user_constraints.constraint_type = '%s'
        """ % (qn(table_name), self.constraits_dict[type]))
        # Load into a dict
        mapping = {}
        for constraint, column in rows:
            mapping.setdefault(constraint, set())
            mapping[constraint].add(column)
        # Find ones affecting these columns
        for constraint, itscols in mapping.items():
            if itscols == columns:
                yield constraint
########NEW FILE########
__FILENAME__ = postgresql_psycopg2

from django.db import connection, models
from south.db import generic

class DatabaseOperations(generic.DatabaseOperations):

    """
    PsycoPG2 implementation of database operations.
    """
    
    backend_name = "postgres"

    def rename_column(self, table_name, old, new):
        if old == new:
            # Short-circuit out
            return []
        self.execute('ALTER TABLE %s RENAME COLUMN %s TO %s;' % (
            self.quote_name(table_name),
            self.quote_name(old),
            self.quote_name(new),
        ))
    
    def rename_table(self, old_table_name, table_name):
        "will rename the table and an associated ID sequence and primary key index"
        # First, rename the table
        generic.DatabaseOperations.rename_table(self, old_table_name, table_name)
        # Then, try renaming the ID sequence
        # (if you're using other AutoFields... your problem, unfortunately)
        self.commit_transaction()
        self.start_transaction()
        try:
            generic.DatabaseOperations.rename_table(self, old_table_name+"_id_seq", table_name+"_id_seq")
        except:
            if self.debug:
                print "   ~ No such sequence (ignoring error)"
            self.rollback_transaction()
        else:
            self.commit_transaction()
        self.start_transaction()

        # Rename primary key index, will not rename other indices on
        # the table that are used by django (e.g. foreign keys). Until
        # figure out how, you need to do this yourself.
        try:
            generic.DatabaseOperations.rename_table(self, old_table_name+"_pkey", table_name+ "_pkey")
        except:
            if self.debug:
                print "   ~ No such primary key (ignoring error)"
            self.rollback_transaction()
        else:
            self.commit_transaction()
        self.start_transaction()


    def rename_index(self, old_index_name, index_name):
        "Rename an index individually"
        generic.DatabaseOperations.rename_table(self, old_index_name, index_name)

    def _db_type_for_alter_column(self, field):
        """
        Returns a field's type suitable for ALTER COLUMN.
        Strips CHECKs from PositiveSmallIntegerField) and PositiveIntegerField
        @param field: The field to generate type for
        """
        super_result = super(DatabaseOperations, self)._db_type_for_alter_column(field)
        if isinstance(field, models.PositiveSmallIntegerField) or isinstance(field, models.PositiveIntegerField):
            return super_result.split(" ")[0]
        return super_result

########NEW FILE########
__FILENAME__ = sqlite3
import inspect
import re

from django.db.models import ForeignKey

from south.db import generic
from django.core.management.commands import inspectdb
    
class DatabaseOperations(generic.DatabaseOperations):

    """
    SQLite3 implementation of database operations.
    """
    
    backend_name = "sqlite3"

    # SQLite ignores several constraints. I wish I could.
    supports_foreign_keys = False
    has_check_constraints = False

    def add_column(self, table_name, name, field, *args, **kwds):
        """
        Adds a column.
        """
        # If it's not nullable, and has no default, raise an error (SQLite is picky)
        if (not field.null and 
            (not field.has_default() or field.get_default() is None) and
            not field.empty_strings_allowed):
            raise ValueError("You cannot add a null=False column without a default value.")
        # We add columns by remaking the table; even though SQLite supports 
        # adding columns, it doesn't support adding PRIMARY KEY or UNIQUE cols.
        self._remake_table(table_name, added={
            field.column: self._column_sql_for_create(table_name, name, field, False),
        })
    
    def _remake_table(self, table_name, added={}, renames={}, deleted=[], altered={}):
        """
        Given a table and three sets of changes (renames, deletes, alters),
        recreates it with the modified schema.
        """
        # Dry runs get skipped completely
        if self.dry_run:
            return
        # Temporary table's name
        temp_name = "_south_new_" + table_name
        # Work out the (possibly new) definitions of each column
        definitions = {}
        cursor = self._get_connection().cursor()
        # Get the index descriptions
        indexes = self._get_connection().introspection.get_indexes(cursor, table_name)
        # Work out new column defs.
        for column_info in self._get_connection().introspection.get_table_description(cursor, table_name):
            name = column_info[0]
            if name in deleted:
                continue
            # Get the type, ignoring PRIMARY KEY (we need to be consistent)
            type = column_info[1].replace("PRIMARY KEY", "")
            # Add on unique or primary key if needed.
            if indexes[name]['unique']:
                type += " UNIQUE"
            if indexes[name]['primary_key']:
                type += " PRIMARY KEY"
            # Deal with a rename
            if name in renames:
                name = renames[name]
            # Add to the defs
            definitions[name] = type
        # Add on altered columns
        definitions.update(altered)
        # Add on the new columns
        definitions.update(added)
        # Alright, Make the table
        self.execute("CREATE TABLE %s (%s)" % (
            self.quote_name(temp_name),
            ", ".join(["%s %s" % (self.quote_name(cname), ctype) for cname, ctype in definitions.items()]),
        ))
        # Copy over the data
        self._copy_data(table_name, temp_name, renames)
        # Delete the old table, move our new one over it
        self.delete_table(table_name)
        self.rename_table(temp_name, table_name)
    
    def _copy_data(self, src, dst, field_renames={}):
        "Used to copy data into a new table"
        # Make a list of all the fields to select
        cursor = self._get_connection().cursor()
        src_fields = [column_info[0] for column_info in self._get_connection().introspection.get_table_description(cursor, src)]
        dst_fields = [column_info[0] for column_info in self._get_connection().introspection.get_table_description(cursor, dst)]
        src_fields_new = []
        dst_fields_new = []
        for field in src_fields:
            if field in field_renames:
                dst_fields_new.append(self.quote_name(field_renames[field]))
            elif field in dst_fields:
                dst_fields_new.append(self.quote_name(field))
            else:
                continue
            src_fields_new.append(self.quote_name(field))
        # Copy over the data
        self.execute("INSERT INTO %s (%s) SELECT %s FROM %s;" % (
            self.quote_name(dst),
            ', '.join(dst_fields_new),
            ', '.join(src_fields_new),
            self.quote_name(src),
        ))
    
    def _column_sql_for_create(self, table_name, name, field, explicit_name=True):
        "Given a field and its name, returns the full type for the CREATE TABLE."
        field.set_attributes_from_name(name)
        if not explicit_name:
            name = field.db_column
        else:
            field.column = name
        sql = self.column_sql(table_name, name, field, with_name=False, field_prepared=True)
        #if field.primary_key:
        #    sql += " PRIMARY KEY"
        #if field.unique:
        #    sql += " UNIQUE"
        return sql
    
    def alter_column(self, table_name, name, field, explicit_name=True):
        """
        Changes a column's SQL definition
        """
        # Remake the table correctly
        self._remake_table(table_name, altered={
            name: self._column_sql_for_create(table_name, name, field, explicit_name),
        })

    def delete_column(self, table_name, column_name):
        """
        Deletes a column.
        """
        self._remake_table(table_name, deleted=[column_name])
    
    def rename_column(self, table_name, old, new):
        """
        Renames a column from one name to another.
        """
        self._remake_table(table_name, renames={old: new})
    
    # Nor unique creation
    def create_unique(self, table_name, columns):
        """
        Not supported under SQLite.
        """
        print "   ! WARNING: SQLite does not support adding unique constraints. Ignored."
    
    # Nor unique deletion
    def delete_unique(self, table_name, columns):
        """
        Not supported under SQLite.
        """
        print "   ! WARNING: SQLite does not support removing unique constraints. Ignored."

    # Not implemented this yet.
    def delete_primary_key(self, table_name):
        raise NotImplementedError()
    
    # No cascades on deletes
    def delete_table(self, table_name, cascade=True):
        generic.DatabaseOperations.delete_table(self, table_name, False)

########NEW FILE########
__FILENAME__ = pyodbc
from django.db import connection
from django.db.models.fields import *
from south.db import generic

class DatabaseOperations(generic.DatabaseOperations):
    """
    django-pyodbc (sql_server.pyodbc) implementation of database operations.
    """
    
    backend_name = "pyodbc"
    
    add_column_string = 'ALTER TABLE %s ADD %s;'
    alter_string_set_type = 'ALTER COLUMN %(column)s %(type)s'
    alter_string_drop_null = 'ALTER COLUMN %(column)s %(type)s NOT NULL'
    allows_combined_alters = False

    drop_index_string = 'DROP INDEX %(index_name)s ON %(table_name)s'
    drop_constraint_string = 'ALTER TABLE %(table_name)s DROP CONSTRAINT %(constraint_name)s'
    delete_column_string = 'ALTER TABLE %s DROP COLUMN %s'


    def delete_column(self, table_name, name):
        q_table_name, q_name = (self.quote_name(table_name), self.quote_name(name))

        # Zap the indexes
        for ind in self._find_indexes_for_column(table_name,name):
            params = {'table_name':q_table_name, 'index_name': ind}
            sql = self.drop_index_string % params
            self.execute(sql, [])

        # Zap the constraints
        for const in self._find_constraints_for_column(table_name,name):
            params = {'table_name':q_table_name, 'constraint_name': const}
            sql = self.drop_constraint_string % params
            self.execute(sql, [])

        # Finally zap the column itself
        self.execute(self.delete_column_string % (q_table_name, q_name), [])

    def _find_indexes_for_column(self, table_name, name):
        "Find the indexes that apply to a column, needed when deleting"
        q_table_name, q_name = (self.quote_name(table_name), self.quote_name(name))

        sql = """
        SELECT si.name, si.id, sik.colid, sc.name
        FROM dbo.sysindexes SI WITH (NOLOCK)
        INNER JOIN dbo.sysindexkeys SIK WITH (NOLOCK)
            ON  SIK.id = Si.id
            AND SIK.indid = SI.indid
        INNER JOIN dbo.syscolumns SC WITH (NOLOCK)
            ON  SI.id = SC.id
            AND SIK.colid = SC.colid
        WHERE SI.indid !=0
            AND Si.id = OBJECT_ID('%s')
            AND SC.name = '%s'
        """
        idx = self.execute(sql % (table_name, name), [])
        return [i[0] for i in idx]

    def _find_constraints_for_column(self, table_name, name):
        "Find the constraints that apply to a column, needed when deleting"
        q_table_name, q_name = (self.quote_name(table_name), self.quote_name(name))

        sql = """
        SELECT  
            Cons.xtype, 
            Cons.id, 
            Cons.[name]
        FROM dbo.sysobjects AS Cons WITH(NOLOCK)
        INNER JOIN (
            SELECT [id], colid, name
            FROM dbo.syscolumns WITH(NOLOCK)
            WHERE id = OBJECT_ID('%s')
            AND name = '%s'
        ) AS Cols
            ON  Cons.parent_obj = Cols.id
        WHERE Cons.parent_obj = OBJECT_ID('%s')
        AND (
            (OBJECTPROPERTY(Cons.[id],'IsConstraint') = 1
                 AND Cons.info = Cols.colid)
             OR (OBJECTPROPERTY(Cons.[id],'IsForeignKey') = 1
                 AND LEFT(Cons.name,%d) = '%s')
        )
        """
        cons = self.execute(sql % (table_name, name, table_name, len(name), name), [])
        return [c[2] for c in cons]


    def drop_column_default_sql(self, table_name, name, q_name):
        "MSSQL specific drop default, which is a pain"

        sql = """
        SELECT object_name(cdefault)
        FROM syscolumns
        WHERE id = object_id('%s')
        AND name = '%s'
        """
        cons = self.execute(sql % (table_name, name), [])
        if cons and cons[0] and cons[0][0]:
            return "DROP CONSTRAINT %s" % cons[0][0]
        return None

    def _fix_field_definition(self, field):
        if isinstance(field, BooleanField):
            if field.default == True:
                field.default = 1
            if field.default == False:
                field.default = 0

    def add_column(self, table_name, name, field, keep_default=True):
        self._fix_field_definition(field)
        generic.DatabaseOperations.add_column(self, table_name, name, field, keep_default)

    def create_table(self, table_name, fields):
        # Tweak stuff as needed
        for name,f in fields:
            self._fix_field_definition(f)

        # Run
        generic.DatabaseOperations.create_table(self, table_name, fields)

    def rename_column(self, table_name, old, new):
        """
        Renames the column of 'table_name' from 'old' to 'new'.
        WARNING - This isn't transactional on MSSQL!
        """
        if old == new:
            # No Operation
            return
        # Examples on the MS site show the table name not being quoted...
        params = (table_name, self.quote_name(old), self.quote_name(new))
        self.execute("EXEC sp_rename '%s.%s', %s, 'COLUMN'" % params)

    def rename_table(self, old_table_name, table_name):
        """
        Renames the table 'old_table_name' to 'table_name'.
        WARNING - This isn't transactional on MSSQL!
        """
        if old_table_name == table_name:
            # No Operation
            return
        params = (self.quote_name(old_table_name), self.quote_name(table_name))
        self.execute('EXEC sp_rename %s, %s' % params)

########NEW FILE########
__FILENAME__ = exceptions
from traceback import format_exception

class SouthError(RuntimeError):
    pass


class BrokenMigration(SouthError):
    def __init__(self, migration, exc_info):
        self.migration = migration
        self.exc_info = exc_info
        if self.exc_info:
            self.traceback = ''.join(format_exception(*self.exc_info))

    def __str__(self):
        return ("While loading migration '%(migration)s':\n"
                '%(traceback)s' % self.__dict__)


class UnknownMigration(BrokenMigration):
    def __str__(self):
        return ("Migration '%(migration)s' probably doesn't exist.\n"
                '%(traceback)s' % self.__dict__)


class InvalidMigrationModule(SouthError):
    def __init__(self, application, module):
        self.application = application
        self.module = module
    
    def __str__(self):
        return ('The migration module specified for %(application)s, %(module)r, is invalid; the parent module does not exist.' % self.__dict__)


class NoMigrations(SouthError):
    def __init__(self, application):
        self.application = application

    def __str__(self):
        return "Application '%(application)s' has no migrations." % self.__dict__


class MultiplePrefixMatches(SouthError):
    def __init__(self, prefix, matches):
        self.prefix = prefix
        self.matches = matches

    def __str__(self):
        self.matches_list = "\n    ".join([unicode(m) for m in self.matches])
        return ("Prefix '%(prefix)s' matches more than one migration:\n"
                "    %(matches_list)s") % self.__dict__


class GhostMigrations(SouthError):
    def __init__(self, ghosts):
        self.ghosts = ghosts

    def __str__(self):
        self.ghosts_list = "\n    ".join([unicode(m) for m in self.ghosts])
        return ("\n\n ! These migrations are in the database but not on disk:\n"
                "    %(ghosts_list)s\n"
                " ! I'm not trusting myself; either fix this yourself by fiddling\n"
                " ! with the south_migrationhistory table, or pass --delete-ghost-migrations\n"
                " ! to South to have it delete ALL of these records (this may not be good).") % self.__dict__


class CircularDependency(SouthError):
    def __init__(self, trace):
        self.trace = trace

    def __str__(self):
        trace = " -> ".join([unicode(s) for s in self.trace])
        return ("Found circular dependency:\n"
                "    %s") % trace


class InconsistentMigrationHistory(SouthError):
    def __init__(self, problems):
        self.problems = problems

    def __str__(self):
        return ('Inconsistent migration history\n'
                'The following options are available:\n'
                '    --merge: will just attempt the migration ignoring any potential dependency conflicts.')


class DependsOnHigherMigration(SouthError):
    def __init__(self, migration, depends_on):
        self.migration = migration
        self.depends_on = depends_on

    def __str__(self):
        return "Lower migration '%(migration)s' depends on a higher migration '%(depends_on)s' in the same app." % self.__dict__


class DependsOnUnknownMigration(SouthError):
    def __init__(self, migration, depends_on):
        self.migration = migration
        self.depends_on = depends_on

    def __str__(self):
        print "Migration '%(migration)s' depends on unknown migration '%(depends_on)s'." % self.__dict__


class DependsOnUnmigratedApplication(SouthError):
    def __init__(self, migration, application):
        self.migration = migration
        self.application = application

    def __str__(self):
        return "Migration '%(migration)s' depends on unmigrated application '%(application)s'." % self.__dict__


class FailedDryRun(SouthError):
    def __init__(self, migration, exc_info):
        self.migration = migration
        self.name = migration.name()
        self.exc_info = exc_info
        self.traceback = ''.join(format_exception(*self.exc_info))

    def __str__(self):
        return (" ! Error found during dry run of '%(name)s'! Aborting.\n"
                "%(traceback)s") % self.__dict__


class ORMBaseNotIncluded(SouthError):
    """Raised when a frozen model has something in _ormbases which isn't frozen."""
    pass


class UnfreezeMeLater(Exception):
    """An exception, which tells the ORM unfreezer to postpone this model."""
    pass


class ImpossibleORMUnfreeze(SouthError):
    """Raised if the ORM can't manage to unfreeze all the models in a linear fashion."""
    pass

########NEW FILE########
__FILENAME__ = django_1_0
"""
Hacks for the Django 1.0/1.0.2 releases.
"""

from django.conf import settings
from django.db import models
from django.db.models.loading import AppCache, cache
from django.utils.datastructures import SortedDict

class Hacks:
    
    def set_installed_apps(self, apps):
        """
        Sets Django's INSTALLED_APPS setting to be effectively the list passed in.
        """
        
        # Make sure it's a list.
        apps = list(apps)
        
        # Make sure it contains strings
        if apps:
            assert isinstance(apps[0], basestring), "The argument to set_installed_apps must be a list of strings."
        
        # Monkeypatch in!
        settings.INSTALLED_APPS, settings.OLD_INSTALLED_APPS = (
            apps,
            settings.INSTALLED_APPS,
        )
        self._redo_app_cache()
    
    
    def reset_installed_apps(self):
        """
        Undoes the effect of set_installed_apps.
        """
        settings.INSTALLED_APPS = settings.OLD_INSTALLED_APPS
        self._redo_app_cache()
    
    
    def _redo_app_cache(self):
        """
        Used to repopulate AppCache after fiddling with INSTALLED_APPS.
        """
        a = AppCache()
        a.loaded = False
        a.handled = {}
        a.postponed = []
        a.app_store = SortedDict()
        a.app_models = SortedDict()
        a.app_errors = {}
        a._populate()
    
    
    def clear_app_cache(self):
        """
        Clears the contents of AppCache to a blank state, so new models
        from the ORM can be added.
        """
        self.old_app_models, cache.app_models = cache.app_models, {}
    
    
    def unclear_app_cache(self):
        """
        Reversed the effects of clear_app_cache.
        """
        cache.app_models = self.old_app_models
        cache._get_models_cache = {}
    
    
    def repopulate_app_cache(self):
        """
        Rebuilds AppCache with the real model definitions.
        """
        cache._populate()
    
########NEW FILE########
__FILENAME__ = annoying_autoonetoone
from south.modelsinspector import add_introspection_rules

try:
    from annoying.fields import AutoOneToOneField
except ImportError:
    pass
else:
    #django-annoying's AutoOneToOneField is essentially a OneToOneField.
    add_introspection_rules([], ["^annoying\.fields\.AutoOneToOneField"])

########NEW FILE########
__FILENAME__ = django_objectpermissions
"""
South introspection rules for django-objectpermissions
"""

from south.modelsinspector import add_ignored_fields

try:
    from objectpermissions.models import UserPermissionRelation, GroupPermissionRelation
except ImportError:
    pass
else:
    add_ignored_fields(["^objectpermissions\.models\.UserPermissionRelation",
                        "^objectpermissions\.models\.GroupPermissionRelation"])


########NEW FILE########
__FILENAME__ = django_tagging
from south.modelsinspector import add_introspection_rules
from django.conf import settings

if "tagging" in settings.INSTALLED_APPS:
    try:
        from tagging.fields import TagField
    except ImportError:
        pass
    else:
        rules = [
            (
                (TagField, ),
                [],
                {
                    "blank": ["blank", {"default": True}],
                    "max_length": ["max_length", {"default": 255}],
                },
            ),
        ]
    
        add_introspection_rules(rules, ["^tagging\.fields",])

########NEW FILE########
__FILENAME__ = django_taggit
"""
South introspection rules for django-taggit
"""

from south.modelsinspector import add_ignored_fields

try:
    from taggit.managers import TaggableManager
except ImportError:
    pass
else:
    add_ignored_fields(["^taggit\.managers"])

########NEW FILE########
__FILENAME__ = geodjango
"""
GeoDjango introspection rules
"""

import django
from django.conf import settings

from south.modelsinspector import add_introspection_rules

has_gis = "django.contrib.gis" in settings.INSTALLED_APPS

if has_gis:
    # Alright,import the field
    from django.contrib.gis.db.models.fields import GeometryField
    
    # Make some introspection rules
    if django.VERSION[0] == 1 and django.VERSION[1] >= 1:
        # Django 1.1's gis module renamed these.
        rules = [
            (
                (GeometryField, ),
                [],
                {
                    "srid": ["srid", {"default": 4326}],
                    "spatial_index": ["spatial_index", {"default": True}],
                    "dim": ["dim", {"default": 2}],
                },
            ),
        ]
    else:
        rules = [
            (
                (GeometryField, ),
                [],
                {
                    "srid": ["_srid", {"default": 4326}],
                    "spatial_index": ["_index", {"default": True}],
                    "dim": ["_dim", {"default": 2}],
                },
            ),
        ]
    
    # Install them
    add_introspection_rules(rules, ["^django\.contrib\.gis"])
########NEW FILE########
__FILENAME__ = logger
import sys
import logging
from django.conf import settings

# Create a dummy handler to use for now.
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

_logger = logging.getLogger("south")
_logger.addHandler(NullHandler())
_logger.setLevel(logging.DEBUG)

def get_logger():
    "Attach a file handler to the logger if there isn't one already."
    debug_on = getattr(settings, "SOUTH_LOGGING_ON", False)
    logging_file = getattr(settings, "SOUTH_LOGGING_FILE", False)
    
    if debug_on:
        if logging_file:
            if len(_logger.handlers) < 2:
                _logger.addHandler(logging.FileHandler(logging_file))
                _logger.setLevel(logging.DEBUG)
        else:
            raise IOError, "SOUTH_LOGGING_ON is True. You also need a SOUTH_LOGGING_FILE setting."
    
    return _logger

def close_logger():
    "Closes the logger handler for the file, so we can remove the file after a test."
    for handler in _logger.handlers:
        _logger.removeHandler(handler)
        if isinstance(handler, logging.FileHandler):
            handler.close()
########NEW FILE########
__FILENAME__ = convert_to_south
"""
Quick conversion command module.
"""

from optparse import make_option
import sys

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.conf import settings
from django.db import models
from django.core import management
from django.core.exceptions import ImproperlyConfigured

from south.migration import Migrations
from south.hacks import hacks
from south.exceptions import NoMigrations

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list
    if '--verbosity' not in [opt.get_opt_string() for opt in BaseCommand.option_list]:
        option_list += (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        )

    help = "Quickly converts the named application to use South if it is currently using syncdb."

    def handle(self, app=None, *args, **options):
        
        # Make sure we have an app
        if not app:
            print "Please specify an app to convert."
            return
        
        # See if the app exists
        app = app.split(".")[-1]
        try:
            app_module = models.get_app(app)
        except ImproperlyConfigured:
            print "There is no enabled application matching '%s'." % app
            return
        
        # Try to get its list of models
        model_list = models.get_models(app_module)
        if not model_list:
            print "This application has no models; this command is for applications that already have models syncdb'd."
            print "Make some models, and then use ./manage.py startmigration %s --initial instead." % app
            return
        
        # Ask South if it thinks it's already got migrations
        try:
            Migrations(app)
        except NoMigrations:
            pass
        else:
            print "This application is already managed by South."
            return
        
        # Finally! It seems we've got a candidate, so do the two-command trick
        verbosity = int(options.get('verbosity', 0))
        management.call_command("schemamigration", app, initial=True, verbosity=verbosity)
        
        # Now, we need to re-clean and sanitise appcache
        hacks.clear_app_cache()
        hacks.repopulate_app_cache()
        
        # And also clear our cached Migration classes
        Migrations._clear_cache()
        
        # Now, migrate
        management.call_command("migrate", app, "0001", fake=True, verbosity=verbosity)
        
        print 
        print "App '%s' converted. Note that South assumed the application's models matched the database" % app
        print "(i.e. you haven't changed it since last syncdb); if you have, you should delete the %s/migrations" % app
        print "directory, revert models.py so it matches the database, and try again."

########NEW FILE########
__FILENAME__ = datamigration
"""
Data migration creation command
"""

import sys
import os
import re
from optparse import make_option

try:
    set
except NameError:
    from sets import Set as set

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import models
from django.conf import settings

from south.migration import Migrations
from south.exceptions import NoMigrations
from south.creator import freezer

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--freeze', action='append', dest='freeze_list', type='string',
            help='Freeze the specified app(s). Provide an app name with each; use the option multiple times for multiple apps'),
        make_option('--stdout', action='store_true', dest='stdout', default=False,
            help='Print the migration to stdout instead of writing it to a file.'),
    )
    help = "Creates a new template data migration for the given app"
    usage_str = "Usage: ./manage.py datamigration appname migrationname [--stdout] [--freeze appname]"
    
    def handle(self, app=None, name="", freeze_list=None, stdout=False, verbosity=1, **options):
        
        # Any supposed lists that are None become empty lists
        freeze_list = freeze_list or []

        # --stdout means name = -
        if stdout:
            name = "-"
	
        # Only allow valid names
        if re.search('[^_\w]', name) and name != "-":
            self.error("Migration names should contain only alphanumeric characters and underscores.")
        
        # if not name, there's an error
        if not name:
            self.error("You must provide a name for this migration\n" + self.usage_str)
        
        if not app:
            self.error("You must provide an app to create a migration for.\n" + self.usage_str)
        
        # Get the Migrations for this app (creating the migrations dir if needed)
        migrations = Migrations(app, force_creation=True, verbose_creation=verbosity > 0)
        
        # See what filename is next in line. We assume they use numbers.
        new_filename = migrations.next_filename(name)
        
        # Work out which apps to freeze
        apps_to_freeze = self.calc_frozen_apps(migrations, freeze_list)
        
        # So, what's in this file, then?
        file_contents = MIGRATION_TEMPLATE % {
            "frozen_models":  freezer.freeze_apps_to_string(apps_to_freeze),
            "complete_apps": apps_to_freeze and "complete_apps = [%s]" % (", ".join(map(repr, apps_to_freeze))) or ""
        }
        
        # - is a special name which means 'print to stdout'
        if name == "-":
            print file_contents
        # Write the migration file if the name isn't -
        else:
            fp = open(os.path.join(migrations.migrations_dir(), new_filename), "w")
            fp.write(file_contents)
            fp.close()
            print >>sys.stderr, "Created %s." % new_filename
    
    def calc_frozen_apps(self, migrations, freeze_list):
        """
        Works out, from the current app, settings, and the command line options,
        which apps should be frozen.
        """
        apps_to_freeze = []
        for to_freeze in freeze_list:
            if "." in to_freeze:
                self.error("You cannot freeze %r; you must provide an app label, like 'auth' or 'books'." % to_freeze)
            # Make sure it's a real app
            if not models.get_app(to_freeze):
                self.error("You cannot freeze %r; it's not an installed app." % to_freeze)
            # OK, it's fine
            apps_to_freeze.append(to_freeze)
        if getattr(settings, 'SOUTH_AUTO_FREEZE_APP', True):
            apps_to_freeze.append(migrations.app_label())
        return apps_to_freeze
    
    def error(self, message, code=1):
        """
        Prints the error, and exits with the given code.
        """
        print >>sys.stderr, message
        sys.exit(code)


MIGRATION_TEMPLATE = """# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."


    def backwards(self, orm):
        "Write your backwards methods here."


    models = %(frozen_models)s

    %(complete_apps)s
"""

########NEW FILE########
__FILENAME__ = graphmigrations
"""
Outputs a graphviz dot file of the dependencies.
"""

from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from south.migration import Migrations, all_migrations

class Command(BaseCommand):

    help = "Outputs a GraphViz dot file of all migration dependencies to stdout."
    
    def handle(self, **options):
        
        # Resolve dependencies
        Migrations.calculate_dependencies()
        
        print "digraph G {"
        
        # Print each app in a cluster
        #for migrations in all_migrations():
        #    print "  subgraph %s {" % migrations.app_label()
        #    # Nodes inside here are linked
        #    print (" -> ".join(['"%s.%s"' % (migration.app_label(), migration.name()) for migration in migrations])) + ";"
        #    print "  }"
    
        # For every migration, print its links.
        for migrations in all_migrations():
            for migration in migrations:
                for other in migration.dependencies:
                    print '"%s.%s" -> "%s.%s"' % (
                        other.app_label(), other.name(),
                        migration.app_label(), migration.name(),
                    )
            
        print "}";
########NEW FILE########
__FILENAME__ = migrate
"""
Migrate management command.
"""

import sys
from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.conf import settings
from django.db import models

from south import migration
from south.migration import Migration, Migrations
from south.migration.utils import get_app_label
from south.exceptions import NoMigrations
from south.db import DEFAULT_DB_ALIAS

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='all_apps', default=False,
            help='Run the specified migration for all apps.'),
        make_option('--list', action='store_true', dest='show_list', default=False,
            help='List migrations noting those that have been applied'),
        make_option('--skip', action='store_true', dest='skip', default=False,
            help='Will skip over out-of-order missing migrations'),
        make_option('--merge', action='store_true', dest='merge', default=False,
            help='Will run out-of-order missing migrations as they are - no rollbacks.'),
        make_option('--no-initial-data', action='store_true', dest='no_initial_data', default=False,
            help='Skips loading initial data if specified.'),
        make_option('--fake', action='store_true', dest='fake', default=False,
            help="Pretends to do the migrations, but doesn't actually execute them."),
        make_option('--db-dry-run', action='store_true', dest='db_dry_run', default=False,
            help="Doesn't execute the SQL generated by the db methods, and doesn't store a record that the migration(s) occurred. Useful to test migrations before applying them."),
        make_option('--delete-ghost-migrations', action='store_true', dest='delete_ghosts', default=False,
            help="Tells South to delete any 'ghost' migrations (ones in the database but not on disk)."),
        make_option('--ignore-ghost-migrations', action='store_true', dest='ignore_ghosts', default=False,
            help="Tells South to ignore any 'ghost' migrations (ones in the database but not on disk) and continue to apply new migrations."),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to synchronize. '
                'Defaults to the "default" database.'),
    )
    if '--verbosity' not in [opt.get_opt_string() for opt in BaseCommand.option_list]:
        option_list += (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        )
    help = "Runs migrations for all apps."
    args = "[appname] [migrationname|zero] [--all] [--list] [--skip] [--merge] [--no-initial-data] [--fake] [--db-dry-run] [--database=dbalias]"

    def handle(self, app=None, target=None, skip=False, merge=False, backwards=False, fake=False, db_dry_run=False, show_list=False, database=DEFAULT_DB_ALIAS, delete_ghosts=False, ignore_ghosts=False, **options):

        # Work out what the resolve mode is
        resolve_mode = merge and "merge" or (skip and "skip" or None)
        
        # NOTE: THIS IS DUPLICATED FROM django.core.management.commands.syncdb
        # This code imports any module named 'management' in INSTALLED_APPS.
        # The 'management' module is the preferred way of listening to post_syncdb
        # signals, and since we're sending those out with create_table migrations,
        # we need apps to behave correctly.
        for app_name in settings.INSTALLED_APPS:
            try:
                __import__(app_name + '.management', {}, {}, [''])
            except ImportError, exc:
                msg = exc.args[0]
                if not msg.startswith('No module named') or 'management' not in msg:
                    raise
        # END DJANGO DUPE CODE
        
        # if all_apps flag is set, shift app over to target
        if options.get('all_apps', False):
            target = app
            app = None

        # Migrate each app
        if app:
            try:
                apps = [Migrations(app)]
            except NoMigrations:
                print "The app '%s' does not appear to use migrations." % app
                print "./manage.py migrate " + self.args
                return
        else:
            apps = list(migration.all_migrations())
        
        # Do we need to show the list of migrations?
        if show_list and apps:
            list_migrations(apps, database)
        
        if not show_list:
            
            for app in apps:
                result = migration.migrate_app(
                    app,
                    #resolve_mode = resolve_mode,
                    target_name = target,
                    fake = fake,
                    db_dry_run = db_dry_run,
                    verbosity = int(options.get('verbosity', 0)),
                    interactive = options.get('interactive', True),
                    load_initial_data = not options.get('no_initial_data', False),
                    merge = merge,
                    skip = skip,
                    database = database,
                    delete_ghosts = delete_ghosts,
                    ignore_ghosts = ignore_ghosts,
                )
                if result is False:
                    sys.exit(1) # Migration failed, so the command fails.


def list_migrations(apps, database = DEFAULT_DB_ALIAS):
    """
    Prints a list of all available migrations, and which ones are currently applied.
    Accepts a list of Migrations instances.
    """
    from south.models import MigrationHistory
    applied_migrations = MigrationHistory.objects.filter(app_name__in=[app.app_label() for app in apps])
    if database != DEFAULT_DB_ALIAS:
        applied_migrations = applied_migrations.using(database)
    applied_migrations = ['%s.%s' % (mi.app_name,mi.migration) for mi in applied_migrations]

    print
    for app in apps:
        print " " + app.app_label()
        # Get the migrations object
        for migration in app:
            if migration.app_label() + "." + migration.name() in applied_migrations:
                print format_migration_list_item(migration.name())
            else:
                print format_migration_list_item(migration.name(), applied=False)
        print


def format_migration_list_item(name, applied=True):
    if applied:
        return '  (*) %s' % name
    return '  ( ) %s' % name

########NEW FILE########
__FILENAME__ = schemamigration
"""
Startmigration command, version 2.
"""

import sys
import os
import re
import string
import random
import inspect
import parser
from optparse import make_option

try:
    set
except NameError:
    from sets import Set as set

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import models
from django.conf import settings

from south.migration import Migrations
from south.exceptions import NoMigrations
from south.creator import changes, actions, freezer
from south.management.commands.datamigration import Command as DataCommand

class Command(DataCommand):
    option_list = DataCommand.option_list + (
        make_option('--add-model', action='append', dest='added_model_list', type='string',
            help='Generate a Create Table migration for the specified model.  Add multiple models to this migration with subsequent --model parameters.'),
        make_option('--add-field', action='append', dest='added_field_list', type='string',
            help='Generate an Add Column migration for the specified modelname.fieldname - you can use this multiple times to add more than one column.'),
        make_option('--add-index', action='append', dest='added_index_list', type='string',
            help='Generate an Add Index migration for the specified modelname.fieldname - you can use this multiple times to add more than one column.'),
        make_option('--initial', action='store_true', dest='initial', default=False,
            help='Generate the initial schema for the app.'),
        make_option('--auto', action='store_true', dest='auto', default=False,
            help='Attempt to automatically detect differences from the last migration.'),
        make_option('--empty', action='store_true', dest='empty', default=False,
            help='Make a blank migration.'),
    )
    help = "Creates a new template schema migration for the given app"
    usage_str = "Usage: ./manage.py schemamigration appname migrationname [--empty] [--initial] [--auto] [--add-model ModelName] [--add-field ModelName.field_name] [--stdout]"
    
    def handle(self, app=None, name="", added_model_list=None, added_field_list=None, freeze_list=None, initial=False, auto=False, stdout=False, added_index_list=None, verbosity=1, empty=False, **options):
        
        # Any supposed lists that are None become empty lists
        added_model_list = added_model_list or []
        added_field_list = added_field_list or []
        added_index_list = added_index_list or []
        freeze_list = freeze_list or []

        # --stdout means name = -
        if stdout:
            name = "-"
	
        # Only allow valid names
        if re.search('[^_\w]', name) and name != "-":
            self.error("Migration names should contain only alphanumeric characters and underscores.")
        
        # Make sure options are compatable
        if initial and (added_model_list or added_field_list or auto):
            self.error("You cannot use --initial and other options together\n" + self.usage_str)
        
        if auto and (added_model_list or added_field_list or initial):
            self.error("You cannot use --auto and other options together\n" + self.usage_str)
        
        if not app:
            self.error("You must provide an app to create a migration for.\n" + self.usage_str)
        
        # Get the Migrations for this app (creating the migrations dir if needed)
        migrations = Migrations(app, force_creation=True, verbose_creation=verbosity > 0)
        
        # What actions do we need to do?
        if auto:
            # Get the old migration
            try:
                last_migration = migrations[-1]
            except IndexError:
                self.error("You cannot use --auto on an app with no migrations. Try --initial.")
            # Make sure it has stored models
            if migrations.app_label() not in getattr(last_migration.migration_class(), "complete_apps", []):
                self.error("You cannot use automatic detection, since the previous migration does not have this whole app frozen.\nEither make migrations using '--freeze %s' or set 'SOUTH_AUTO_FREEZE_APP = True' in your settings.py." % migrations.app_label())
            # Alright, construct two model dicts to run the differ on.
            old_defs = dict(
                (k, v) for k, v in last_migration.migration_class().models.items()
                if k.split(".")[0] == migrations.app_label()
            )
            new_defs = dict(
                (k, v) for k, v in freezer.freeze_apps([migrations.app_label()]).items()
                if k.split(".")[0] == migrations.app_label()
            )
            change_source = changes.AutoChanges(
                migrations = migrations,
                old_defs = old_defs,
                old_orm = last_migration.orm(),
                new_defs = new_defs,
            )
        
        elif initial:
            # Do an initial migration
            change_source = changes.InitialChanges(migrations)
        
        else:
            # Read the commands manually off of the arguments
            if (added_model_list or added_field_list or added_index_list):
                change_source = changes.ManualChanges(
                    migrations,
                    added_model_list,
                    added_field_list,
                    added_index_list,
                )
            elif empty:
                change_source = None
            else:
                print >>sys.stderr, "You have not passed any of --initial, --auto, --empty, --add-model, --add-field or --add-index."
                sys.exit(1)
        
        # if not name, there's an error
        if not name:
            if change_source:
                name = change_source.suggest_name()
            if not name:
                self.error("You must provide a name for this migration\n" + self.usage_str)
        
        # See what filename is next in line. We assume they use numbers.
        new_filename = migrations.next_filename(name)
        
        # Get the actions, and then insert them into the actions lists
        forwards_actions = []
        backwards_actions = []
        if change_source:
            for action_name, params in change_source.get_changes():
                # Run the correct Action class
                try:
                    action_class = getattr(actions, action_name)
                except AttributeError:
                    raise ValueError("Invalid action name from source: %s" % action_name)
                else:
                    action = action_class(**params)
                    action.add_forwards(forwards_actions)
                    action.add_backwards(backwards_actions)
                    print >>sys.stderr, action.console_line()
        
        # Nowt happen? That's not good for --auto.
        if auto and not forwards_actions:
            self.error("Nothing seems to have changed.")
        
        # Work out which apps to freeze
        apps_to_freeze = self.calc_frozen_apps(migrations, freeze_list)
        
        # So, what's in this file, then?
        file_contents = MIGRATION_TEMPLATE % {
            "forwards": "\n".join(forwards_actions or ["pass"]), 
            "backwards": "\n".join(backwards_actions or ["pass"]), 
            "frozen_models":  freezer.freeze_apps_to_string(apps_to_freeze),
            "complete_apps": apps_to_freeze and "complete_apps = [%s]" % (", ".join(map(repr, apps_to_freeze))) or ""
        }
        
        # - is a special name which means 'print to stdout'
        if name == "-":
            print file_contents
        # Write the migration file if the name isn't -
        else:
            fp = open(os.path.join(migrations.migrations_dir(), new_filename), "w")
            fp.write(file_contents)
            fp.close()
            if empty:
                print >>sys.stderr, "Created %s. You must now edit this migration and add the code for each direction." % new_filename
            else:
                print >>sys.stderr, "Created %s. You can now apply this migration with: ./manage.py migrate %s" % (new_filename, app)


MIGRATION_TEMPLATE = """# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        %(forwards)s


    def backwards(self, orm):
        %(backwards)s


    models = %(frozen_models)s

    %(complete_apps)s
"""

########NEW FILE########
__FILENAME__ = startmigration
"""
Now-obsolete startmigration command.
"""

from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.color import no_style

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--model', action='append', dest='added_model_list', type='string',
            help='Generate a Create Table migration for the specified model.  Add multiple models to this migration with subsequent --model parameters.'),
        make_option('--add-field', action='append', dest='added_field_list', type='string',
            help='Generate an Add Column migration for the specified modelname.fieldname - you can use this multiple times to add more than one column.'),
        make_option('--add-index', action='append', dest='added_index_list', type='string',
            help='Generate an Add Index migration for the specified modelname.fieldname - you can use this multiple times to add more than one column.'),
        make_option('--initial', action='store_true', dest='initial', default=False,
            help='Generate the initial schema for the app.'),
        make_option('--auto', action='store_true', dest='auto', default=False,
            help='Attempt to automatically detect differences from the last migration.'),
        make_option('--freeze', action='append', dest='freeze_list', type='string',
            help='Freeze the specified model(s). Pass in either an app name (to freeze the whole app) or a single model, as appname.modelname.'),
        make_option('--stdout', action='store_true', dest='stdout', default=False,
            help='Print the migration to stdout instead of writing it to a file.'),
    )
    help = "Depereciated command"
    
    def handle(self, app=None, name="", added_model_list=None, added_field_list=None, initial=False, freeze_list=None, auto=False, stdout=False, added_index_list=None, **options):
        
        print "The 'startmigration' command is now deprecated; please use the new 'schemamigration' and 'datamigration' commands."
########NEW FILE########
__FILENAME__ = syncdb
"""
Overridden syncdb command
"""

import sys
from optparse import make_option

from django.core.management.base import NoArgsCommand, BaseCommand 
from django.core.management.color import no_style
from django.utils.datastructures import SortedDict
from django.core.management.commands import syncdb
from django.conf import settings
from django.db import models
from django.db.models.loading import cache
from django.core import management

from south.db import dbs
from south import migration
from south.exceptions import NoMigrations

def get_app_label(app):
    return '.'.join( app.__name__.split('.')[0:-1] )

class Command(NoArgsCommand):
    option_list = syncdb.Command.option_list + ( 
        make_option('--migrate', action='store_true', dest='migrate', default=False,
            help='Tells South to also perform migrations after the sync. Default for during testing, and other internal calls.'),
        make_option('--all', action='store_true', dest='migrate_all', default=False,
            help='Makes syncdb work on all apps, even migrated ones. Be careful!'),
    )
    if '--verbosity' not in [opt.get_opt_string() for opt in syncdb.Command.option_list]:
        option_list += (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        )
    help = "Create the database tables for all apps in INSTALLED_APPS whose tables haven't already been created, except those which use migrations."

    def handle_noargs(self, migrate_all=False, **options):
        # Work out what uses migrations and so doesn't need syncing
        apps_needing_sync = []
        apps_migrated = []
        for app in models.get_apps():
            app_label = get_app_label(app)
            if migrate_all:
                apps_needing_sync.append(app_label)
            else:
                try:
                    migrations = migration.Migrations(app_label)
                except NoMigrations:
                    # It needs syncing
                    apps_needing_sync.append(app_label)
                else:
                    # This is a migrated app, leave it
                    apps_migrated.append(app_label)
        verbosity = int(options.get('verbosity', 0))
        
        # Run syncdb on only the ones needed
        if verbosity:
            print "Syncing..."
        
        old_installed, settings.INSTALLED_APPS = settings.INSTALLED_APPS, apps_needing_sync
        old_app_store, cache.app_store = cache.app_store, SortedDict([
            (k, v) for (k, v) in cache.app_store.items()
            if get_app_label(k) in apps_needing_sync
        ])
        
        # This will allow the setting of the MySQL storage engine, for example.
        for db in dbs.values(): 
            db.connection_init() 
        
        # OK, run the actual syncdb
        syncdb.Command().execute(**options)
        
        settings.INSTALLED_APPS = old_installed
        cache.app_store = old_app_store
        
        # Migrate if needed
        if options.get('migrate', True):
            if verbosity:
                print "Migrating..."
            management.call_command('migrate', **options)
        
        # Be obvious about what we did
        if verbosity:
            print "\nSynced:\n > %s" % "\n > ".join(apps_needing_sync)
        
        if options.get('migrate', True):
            if verbosity:
                print "\nMigrated:\n - %s" % "\n - ".join(apps_migrated)
        else:
            if verbosity:
                print "\nNot synced (use migrations):\n - %s" % "\n - ".join(apps_migrated)
                print "(use ./manage.py migrate to migrate these)"

########NEW FILE########
__FILENAME__ = test
from django.core.management.commands import test

from south.management.commands import patch_for_test_db_setup

class Command(test.Command):
    def handle(self, *args, **kwargs):
        patch_for_test_db_setup()
        super(Command, self).handle(*args, **kwargs)

########NEW FILE########
__FILENAME__ = testserver
from django.core.management.commands import testserver

from south.management.commands import patch_for_test_db_setup

class Command(testserver.Command):
    def handle(self, *args, **kwargs):
        patch_for_test_db_setup()
        super(Command, self).handle(*args, **kwargs)

########NEW FILE########
__FILENAME__ = base
from collections import deque
import datetime
import os
import re
import sys

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.conf import settings

from south import exceptions
from south.migration.utils import depends, dfs, flatten, get_app_label
from south.orm import FakeORM
from south.utils import memoize, ask_for_it_by_name
from south.migration.utils import app_label_to_app_module


def all_migrations(applications=None):
    """
    Returns all Migrations for all `applications` that are migrated.
    """
    if applications is None:
        applications = models.get_apps()
    for model_module in applications:
        # The app they've passed is the models module - go up one level
        app_path = ".".join(model_module.__name__.split(".")[:-1])
        app = ask_for_it_by_name(app_path)
        try:
            yield Migrations(app)
        except exceptions.NoMigrations:
            pass


def application_to_app_label(application):
    "Works out the app label from either the app label, the app name, or the module"
    if isinstance(application, basestring):
        app_label = application.split('.')[-1]
    else:
        app_label = application.__name__.split('.')[-1]
    return app_label


class MigrationsMetaclass(type):
    
    """
    Metaclass which ensures there is only one instance of a Migrations for
    any given app.
    """
    
    def __init__(self, name, bases, dict):
        super(MigrationsMetaclass, self).__init__(name, bases, dict)
        self.instances = {}
    
    def __call__(self, application, **kwds):
        
        app_label = application_to_app_label(application)
        
        # If we don't already have an instance, make one
        if app_label not in self.instances:
            self.instances[app_label] = super(MigrationsMetaclass, self).__call__(app_label_to_app_module(app_label), **kwds)
        
        return self.instances[app_label]

    def _clear_cache(self):
        "Clears the cache of Migration objects."
        self.instances = {}


class Migrations(list):
    """
    Holds a list of Migration objects for a particular app.
    """
    
    __metaclass__ = MigrationsMetaclass
    
    if getattr(settings, "SOUTH_USE_PYC", False):
        MIGRATION_FILENAME = re.compile(r'(?!__init__)' # Don't match __init__.py
                                        r'[0-9a-zA-Z_]*' # Don't match dotfiles, or names with dots/invalid chars in them
                                        r'(\.pyc?)?$')     # Match .py or .pyc files, or module dirs
    else:
        MIGRATION_FILENAME = re.compile(r'(?!__init__)' # Don't match __init__.py
                                        r'[0-9a-zA-Z_]*' # Don't match dotfiles, or names with dots/invalid chars in them
                                        r'(\.py)?$')       # Match only .py files, or module dirs

    def __init__(self, application, force_creation=False, verbose_creation=True):
        "Constructor. Takes the module of the app, NOT its models (like get_app returns)"
        self._cache = {}
        self.set_application(application, force_creation, verbose_creation)
    
    def create_migrations_directory(self, verbose=True):
        "Given an application, ensures that the migrations directory is ready."
        migrations_dir = self.migrations_dir()
        # Make the directory if it's not already there
        if not os.path.isdir(migrations_dir):
            if verbose:
                print "Creating migrations directory at '%s'..." % migrations_dir
            os.mkdir(migrations_dir)
        # Same for __init__.py
        init_path = os.path.join(migrations_dir, "__init__.py")
        if not os.path.isfile(init_path):
            # Touch the init py file
            if verbose:
                print "Creating __init__.py in '%s'..." % migrations_dir
            open(init_path, "w").close()
    
    def migrations_dir(self):
        """
        Returns the full path of the migrations directory.
        If it doesn't exist yet, returns where it would exist, based on the
        app's migrations module (defaults to app.migrations)
        """
        module_path = self.migrations_module()
        try:
            module = __import__(module_path, {}, {}, [''])
        except ImportError:
            # There's no migrations module made yet; guess!
            try:
                parent = __import__(".".join(module_path.split(".")[:-1]), {}, {}, [''])
            except ImportError:
                # The parent doesn't even exist, that's an issue.
                raise exceptions.InvalidMigrationModule(
                    application = self.application.__name__,
                    module = module_path,
                )
            else:
                # Good guess.
                return os.path.join(os.path.dirname(parent.__file__), module_path.split(".")[-1])
        else:
            # Get directory directly
            return os.path.dirname(module.__file__)
    
    def migrations_module(self):
        "Returns the module name of the migrations module for this"
        app_label = application_to_app_label(self.application)
        if hasattr(settings, "SOUTH_MIGRATION_MODULES"):
            if app_label in settings.SOUTH_MIGRATION_MODULES:
                # There's an override.
                return settings.SOUTH_MIGRATION_MODULES[app_label]
        return self._application.__name__ + '.migrations'

    def get_application(self):
        return self._application

    def set_application(self, application, force_creation=False, verbose_creation=True):
        """
        Called when the application for this Migrations is set.
        Imports the migrations module object, and throws a paddy if it can't.
        """
        self._application = application
        if not hasattr(application, 'migrations'):
            try:
                module = __import__(self.migrations_module(), {}, {}, [''])
                self._migrations = application.migrations = module
            except ImportError:
                if force_creation:
                    self.create_migrations_directory(verbose_creation)
                    module = __import__(self.migrations_module(), {}, {}, [''])
                    self._migrations = application.migrations = module
                else:
                    raise exceptions.NoMigrations(application)
        self._load_migrations_module(application.migrations)

    application = property(get_application, set_application)

    def _load_migrations_module(self, module):
        self._migrations = module
        filenames = []
        dirname = self.migrations_dir()
        for f in os.listdir(dirname):
            if self.MIGRATION_FILENAME.match(os.path.basename(f)):
                full_path = os.path.join(dirname, f)
                # If it's a .pyc file, only append if the .py isn't already around
                if f.endswith(".pyc") and (os.path.isfile(full_path[:-1])):
                    continue
                # If it's a module directory, only append if it contains __init__.py[c].
                if os.path.isdir(full_path):
                    if not (os.path.isfile(os.path.join(full_path, "__init__.py")) or \
                      (getattr(settings, "SOUTH_USE_PYC", False) and \
                      os.path.isfile(os.path.join(full_path, "__init__.pyc")))):
                        continue
                filenames.append(f)
        filenames.sort()
        self.extend(self.migration(f) for f in filenames)

    def migration(self, filename):
        name = Migration.strip_filename(filename)
        if name not in self._cache:
            self._cache[name] = Migration(self, name)
        return self._cache[name]

    def __getitem__(self, value):
        if isinstance(value, basestring):
            return self.migration(value)
        return super(Migrations, self).__getitem__(value)

    def _guess_migration(self, prefix):
        prefix = Migration.strip_filename(prefix)
        matches = [m for m in self if m.name().startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise exceptions.MultiplePrefixMatches(prefix, matches)
        else:
            raise exceptions.UnknownMigration(prefix, None)

    def guess_migration(self, target_name):
        if target_name == 'zero' or not self:
            return
        elif target_name is None:
            return self[-1]
        else:
            return self._guess_migration(prefix=target_name)
    
    def app_label(self):
        return self._application.__name__.split('.')[-1]

    def full_name(self):
        return self._migrations.__name__

    @classmethod
    def calculate_dependencies(cls, force=False):
        "Goes through all the migrations, and works out the dependencies."
        if getattr(cls, "_dependencies_done", False) and not force:
            return
        for migrations in all_migrations():
            for migration in migrations:
                migration.calculate_dependencies()
        cls._dependencies_done = True
    
    @staticmethod
    def invalidate_all_modules():
        "Goes through all the migrations, and invalidates all cached modules."
        for migrations in all_migrations():
            for migration in migrations:
                migration.invalidate_module()
    
    def next_filename(self, name):
        "Returns the fully-formatted filename of what a new migration 'name' would be"
        highest_number = 0
        for migration in self:
            try:
                number = int(migration.name().split("_")[0])
                highest_number = max(highest_number, number)
            except ValueError:
                pass
        # Work out the new filename
        return "%04i_%s.py" % (
            highest_number + 1,
            name,
        )


class Migration(object):
    
    """
    Class which represents a particular migration file on-disk.
    """
    
    def __init__(self, migrations, filename):
        """
        Returns the migration class implied by 'filename'.
        """
        self.migrations = migrations
        self.filename = filename
        self.dependencies = set()
        self.dependents = set()

    def __str__(self):
        return self.app_label() + ':' + self.name()

    def __repr__(self):
        return u'<Migration: %s>' % unicode(self)

    def app_label(self):
        return self.migrations.app_label()

    @staticmethod
    def strip_filename(filename):
        return os.path.splitext(os.path.basename(filename))[0]

    def name(self):
        return self.strip_filename(os.path.basename(self.filename))

    def full_name(self):
        return self.migrations.full_name() + '.' + self.name()

    def migration(self):
        "Tries to load the actual migration module"
        full_name = self.full_name()
        try:
            migration = sys.modules[full_name]
        except KeyError:
            try:
                migration = __import__(full_name, {}, {}, ['Migration'])
            except ImportError, e:
                raise exceptions.UnknownMigration(self, sys.exc_info())
            except Exception, e:
                raise exceptions.BrokenMigration(self, sys.exc_info())
        # Override some imports
        migration._ = lambda x: x  # Fake i18n
        migration.datetime = datetime
        return migration
    migration = memoize(migration)

    def migration_class(self):
        "Returns the Migration class from the module"
        return self.migration().Migration

    def migration_instance(self):
        "Instantiates the migration_class"
        return self.migration_class()()
    migration_instance = memoize(migration_instance)

    def previous(self):
        "Returns the migration that comes before this one in the sequence."
        index = self.migrations.index(self) - 1
        if index < 0:
            return None
        return self.migrations[index]
    previous = memoize(previous)

    def next(self):
        "Returns the migration that comes after this one in the sequence."
        index = self.migrations.index(self) + 1
        if index >= len(self.migrations):
            return None
        return self.migrations[index]
    next = memoize(next)
    
    def _get_dependency_objects(self, attrname):
        """
        Given the name of an attribute (depends_on or needed_by), either yields
        a list of migration objects representing it, or errors out.
        """
        for app, name in getattr(self.migration_class(), attrname, []):
            try:
                migrations = Migrations(app)
            except ImproperlyConfigured:
                raise exceptions.DependsOnUnmigratedApplication(self, app)
            migration = migrations.migration(name)
            try:
                migration.migration()
            except exceptions.UnknownMigration:
                raise exceptions.DependsOnUnknownMigration(self, migration)
            if migration.is_before(self) == False:
                raise exceptions.DependsOnHigherMigration(self, migration)
            yield migration
    
    def calculate_dependencies(self):
        """
        Loads dependency info for this migration, and stores it in itself
        and any other relevant migrations.
        """
        # Normal deps first
        for migration in self._get_dependency_objects("depends_on"):
            self.dependencies.add(migration)
            migration.dependents.add(self)
        # And reverse deps
        for migration in self._get_dependency_objects("needed_by"):
            self.dependents.add(migration)
            migration.dependencies.add(self)
        # And implicit ordering deps
        previous = self.previous()
        if previous:
            self.dependencies.add(previous)
            previous.dependents.add(self)
    
    def invalidate_module(self):
        """
        Removes the cached version of this migration's module import, so we
        have to re-import it. Used when south.db.db changes.
        """
        reload(self.migration())
        self.migration._invalidate()

    def forwards(self):
        return self.migration_instance().forwards

    def backwards(self):
        return self.migration_instance().backwards

    def forwards_plan(self):
        """
        Returns a list of Migration objects to be applied, in order.

        This list includes `self`, which will be applied last.
        """
        return depends(self, lambda x: x.dependencies)

    def _backwards_plan(self):
        return depends(self, lambda x: x.dependents)

    def backwards_plan(self):
        """
        Returns a list of Migration objects to be unapplied, in order.

        This list includes `self`, which will be unapplied last.
        """
        return list(self._backwards_plan())

    def is_before(self, other):
        if self.migrations == other.migrations:
            if self.filename < other.filename:
                return True
            return False

    def is_after(self, other):
        if self.migrations == other.migrations:
            if self.filename > other.filename:
                return True
            return False

    def prev_orm(self):
        previous = self.previous()
        if previous is None:
            # First migration? The 'previous ORM' is empty.
            return FakeORM(None, self.app_label())
        return previous.orm()
    prev_orm = memoize(prev_orm)

    def orm(self):
        return FakeORM(self.migration_class(), self.app_label())
    orm = memoize(orm)

    def no_dry_run(self):
        migration_class = self.migration_class()
        try:
            return migration_class.no_dry_run
        except AttributeError:
            return False

########NEW FILE########
__FILENAME__ = migrators
from copy import copy
from cStringIO import StringIO
import datetime
import inspect
import sys
import traceback

from django.core.management import call_command
from django.core.management.commands import loaddata
from django.db import models

import south.db
from south import exceptions
from south.db import DEFAULT_DB_ALIAS
from south.models import MigrationHistory
from south.signals import ran_migration


class Migrator(object):
    def __init__(self, verbosity=0, interactive=False):
        self.verbosity = int(verbosity)
        self.interactive = bool(interactive)

    @staticmethod
    def title(target):
        raise NotImplementedError()

    def print_title(self, target):
        if self.verbosity:
            print self.title(target)
        
    @staticmethod
    def status(target):
        raise NotImplementedError()

    def print_status(self, migration):
        status = self.status(migration)
        if self.verbosity and status:
            print status

    @staticmethod
    def orm(migration):
        raise NotImplementedError()

    def backwards(self, migration):
        return self._wrap_direction(migration.backwards(), migration.prev_orm())

    def direction(self, migration):
        raise NotImplementedError()

    @staticmethod
    def _wrap_direction(direction, orm):
        args = inspect.getargspec(direction)
        if len(args[0]) == 1:
            # Old migration, no ORM should be passed in
            return direction
        return (lambda: direction(orm))

    @staticmethod
    def record(migration, database):
        raise NotImplementedError()

    def run_migration_error(self, migration, extra_info=''):
        return (
            ' ! Error found during real run of migration! Aborting.\n'
            '\n'
            ' ! Since you have a database that does not support running\n'
            ' ! schema-altering statements in transactions, we have had \n'
            ' ! to leave it in an interim state between migrations.\n'
            '%s\n'
            ' ! The South developers regret this has happened, and would\n'
            ' ! like to gently persuade you to consider a slightly\n'
            ' ! easier-to-deal-with DBMS.\n'
            ' ! NOTE: The error which caused the migration to fail is further up.'
        ) % extra_info

    def run_migration(self, migration):
        migration_function = self.direction(migration)
        south.db.db.start_transaction()
        try:
            migration_function()
            south.db.db.execute_deferred_sql()
        except:
            south.db.db.rollback_transaction()
            if not south.db.db.has_ddl_transactions:
                print self.run_migration_error(migration)
            raise
        else:
            south.db.db.commit_transaction()

    def run(self, migration):
        # Get the correct ORM.
        south.db.db.current_orm = self.orm(migration)
        # If the database doesn't support running DDL inside a transaction
        # *cough*MySQL*cough* then do a dry run first.
        if not south.db.db.has_ddl_transactions:
            dry_run = DryRunMigrator(migrator=self, ignore_fail=False)
            dry_run.run_migration(migration)
        return self.run_migration(migration)

    def done_migrate(self, migration, database):
        south.db.db.start_transaction()
        try:
            # Record us as having done this
            self.record(migration, database)
        except:
            south.db.db.rollback_transaction()
            raise
        else:
            south.db.db.commit_transaction()

    def send_ran_migration(self, migration):
        ran_migration.send(None,
                           app=migration.app_label(),
                           migration=migration,
                           method=self.__class__.__name__.lower())

    def migrate(self, migration, database):
        """
        Runs the specified migration forwards/backwards, in order.
        """
        app = migration.migrations._migrations
        migration_name = migration.name()
        self.print_status(migration)
        result = self.run(migration)
        self.done_migrate(migration, database)
        self.send_ran_migration(migration)
        return result

    def migrate_many(self, target, migrations, database):
        raise NotImplementedError()


class MigratorWrapper(object):
    def __init__(self, migrator, *args, **kwargs):
        self._migrator = copy(migrator)
        attributes = dict([(k, getattr(self, k))
                           for k in self.__class__.__dict__.iterkeys()
                           if not k.startswith('__')])
        self._migrator.__dict__.update(attributes)

    def __getattr__(self, name):
        return getattr(self._migrator, name)


class DryRunMigrator(MigratorWrapper):
    def __init__(self, ignore_fail=True, *args, **kwargs):
        super(DryRunMigrator, self).__init__(*args, **kwargs)
        self._ignore_fail = ignore_fail

    def _run_migration(self, migration):
        if migration.no_dry_run() and self.verbosity:
            print " - Migration '%s' is marked for no-dry-run." % migration
            return
        south.db.db.dry_run = True
        if self._ignore_fail:
            south.db.db.debug, old_debug = False, south.db.db.debug
        pending_creates = south.db.db.get_pending_creates()
        south.db.db.start_transaction()
        migration_function = self.direction(migration)
        try:
            try:
                migration_function()
                south.db.db.execute_deferred_sql()
            except:
                raise exceptions.FailedDryRun(migration, sys.exc_info())
        finally:
            south.db.db.rollback_transactions_dry_run()
            if self._ignore_fail:
                south.db.db.debug = old_debug
            south.db.db.clear_run_data(pending_creates)
            south.db.db.dry_run = False

    def run_migration(self, migration):
        try:
            self._run_migration(migration)
        except exceptions.FailedDryRun:
            if self._ignore_fail:
                return False
            raise

    def done_migrate(self, *args, **kwargs):
        pass

    def send_ran_migration(self, *args, **kwargs):
        pass


class FakeMigrator(MigratorWrapper):
    def run(self, migration):
        if self.verbosity:
            print '   (faked)'

    def send_ran_migration(self, *args, **kwargs):
        pass


class LoadInitialDataMigrator(MigratorWrapper):
    
    def load_initial_data(self, target):
        if target is None or target != target.migrations[-1]:
            return
        # Load initial data, if we ended up at target
        if self.verbosity:
            print " - Loading initial data for %s." % target.app_label()
        # Override Django's get_apps call temporarily to only load from the
        # current app
        old_get_apps = models.get_apps
        new_get_apps = lambda: [models.get_app(target.app_label())]
        models.get_apps = new_get_apps
        loaddata.get_apps = new_get_apps
        try:
            call_command('loaddata', 'initial_data', verbosity=self.verbosity)
        finally:
            models.get_apps = old_get_apps
            loaddata.get_apps = old_get_apps

    def migrate_many(self, target, migrations, database):
        migrator = self._migrator
        result = migrator.__class__.migrate_many(migrator, target, migrations, database)
        if result:
            self.load_initial_data(target)
        return True


class Forwards(Migrator):
    """
    Runs the specified migration forwards, in order.
    """
    torun = 'forwards'

    @staticmethod
    def title(target):
        if target is not None:
            return " - Migrating forwards to %s." % target.name()
        else:
            assert False, "You cannot migrate forwards to zero."

    @staticmethod
    def status(migration):
        return ' > %s' % migration

    @staticmethod
    def orm(migration):
        return migration.orm()

    def forwards(self, migration):
        return self._wrap_direction(migration.forwards(), migration.orm())

    direction = forwards

    @staticmethod
    def record(migration, database):
        # Record us as having done this
        record = MigrationHistory.for_migration(migration, database)
        record.applied = datetime.datetime.utcnow()
        if database != DEFAULT_DB_ALIAS:
            record.save(using=database)
        else:
            # Django 1.1 and below always go down this branch.
            record.save()

    def format_backwards(self, migration):
        if migration.no_dry_run():
            return "   (migration cannot be dry-run; cannot discover commands)"
        old_debug, old_dry_run = south.db.db.debug, south.db.db.dry_run
        south.db.db.debug = south.db.db.dry_run = True
        stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            try:
                self.backwards(migration)()
                return sys.stdout.getvalue()
            except:
                raise
        finally:
            south.db.db.debug, south.db.db.dry_run = old_debug, old_dry_run
            sys.stdout = stdout

    def run_migration_error(self, migration, extra_info=''):
        extra_info = ('\n'
                      '! You *might* be able to recover with:'
                      '%s'
                      '%s' %
                      (self.format_backwards(migration), extra_info))
        return super(Forwards, self).run_migration_error(migration, extra_info)

    def migrate_many(self, target, migrations, database):
        try:
            for migration in migrations:
                result = self.migrate(migration, database)
                if result is False: # The migrations errored, but nicely.
                    return False
        finally:
            # Call any pending post_syncdb signals
            south.db.db.send_pending_create_signals(verbosity=self.verbosity,
                                                    interactive=self.interactive)
        return True


class Backwards(Migrator):
    """
    Runs the specified migration backwards, in order.
    """
    torun = 'backwards'

    @staticmethod
    def title(target):
        if target is None:
            return " - Migrating backwards to zero state."
        else:
            return " - Migrating backwards to just after %s." % target.name()

    @staticmethod
    def status(migration):
        return ' < %s' % migration

    @staticmethod
    def orm(migration):
        return migration.prev_orm()

    direction = Migrator.backwards

    @staticmethod
    def record(migration, database):
        # Record us as having not done this
        record = MigrationHistory.for_migration(migration, database)
        if record.id is not None:
            if database != DEFAULT_DB_ALIAS:
                record.delete(using=database)
            else:
                # Django 1.1 always goes down here
                record.delete()

    def migrate_many(self, target, migrations, database):
        for migration in migrations:
            self.migrate(migration, database)
        return True




########NEW FILE########
__FILENAME__ = utils
import sys
from collections import deque

from django.utils.datastructures import SortedDict
from django.db import models

from south import exceptions


class SortedSet(SortedDict):
    def __init__(self, data=tuple()):
        self.extend(data)

    def __str__(self):
        return "SortedSet(%s)" % list(self)

    def add(self, value):
        self[value] = True

    def remove(self, value):
        del self[value]

    def extend(self, iterable):
        [self.add(k) for k in iterable]


def get_app_label(app):
    """
    Returns the _internal_ app label for the given app module.
    i.e. for <module django.contrib.auth.models> will return 'auth'
    """
    return app.__name__.split('.')[-2]


def app_label_to_app_module(app_label):
    """
    Given the app label, returns the module of the app itself (unlike models.get_app,
    which returns the models module)
    """
    # Get the models module
    app = models.get_app(app_label)
    module_name = ".".join(app.__name__.split(".")[:-1])
    try:
        module = sys.modules[module_name]
    except KeyError:
        __import__(module_name, {}, {}, [''])
        module = sys.modules[module_name]
    return module


def flatten(*stack):
    stack = deque(stack)
    while stack:
        try:
            x = stack[0].next()
        except AttributeError:
            stack[0] = iter(stack[0])
            x = stack[0].next()
        except StopIteration:
            stack.popleft()
            continue
        if hasattr(x, '__iter__'):
            stack.appendleft(x)
        else:
            yield x
    

def _dfs(start, get_children):
    # Prepend ourselves to the result
    yield start
    children = sorted(get_children(start), key=lambda x: str(x))
    if children:
        # We need to apply all the migrations this one depends on
        yield (_dfs(n, get_children) for n in children)

def dfs(start, get_children):
    return flatten(_dfs(start, get_children))

def detect_cycles(iterable):
    result = []
    i = iter(iterable)
    try:
        # Point to the tortoise
        tortoise = 0
        result.append(i.next())
        # Point to the hare
        hare = 1
        result.append(i.next())
        # Start looking for cycles
        power = 1
        while True:
            # Use Richard P. Brent's algorithm to find an element that
            # repeats.
            while result[tortoise] != result[hare]:
                if power == (hare - tortoise):
                    tortoise = hare
                    power *= 2
                hare += 1
                result.append(i.next())
            # Brent assumes the sequence is stateless, but since we're
            # dealing with a DFS tree, we need to make sure that all
            # the items between `tortoise` and `hare` are identical.
            cycle = True
            for j in xrange(0, hare - tortoise + 1):
                tortoise += 1
                hare += 1
                result.append(i.next())
                if result[tortoise] != result[hare]:
                    # False alarm: no cycle here.
                    cycle = False
                    power = 1
                    tortoise = hare
                    hare += 1
                    result.append(i.next())
                    break
            # Both loops are done, so we must have a cycle
            if cycle:
                raise exceptions.CircularDependency(result[tortoise:hare+1])
    except StopIteration:
        # Return when `iterable` is exhausted. Obviously, there are no cycles.
        return result

def depends(start, get_children):
    result = SortedSet(reversed(detect_cycles(dfs(start, get_children))))
    return list(result)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from south.db import DEFAULT_DB_ALIAS

class MigrationHistory(models.Model):
    app_name = models.CharField(max_length=255)
    migration = models.CharField(max_length=255)
    applied = models.DateTimeField(blank=True)

    @classmethod
    def for_migration(cls, migration, database):
        try:
            # Switch on multi-db-ness
            if database != DEFAULT_DB_ALIAS:
                # Django 1.2
                objects = cls.objects.using(database)
            else:
                # Django <= 1.1
                objects = cls.objects
            return objects.get(
                app_name=migration.app_label(),
                migration=migration.name(),
            )
        except cls.DoesNotExist:
            return cls(
                app_name=migration.app_label(),
                migration=migration.name(),
            )

    def get_migrations(self):
        from south.migration.base import Migrations
        return Migrations(self.app_name)

    def get_migration(self):
        return self.get_migrations().migration(self.migration)
    
    def __unicode__(self):
        return "<%s: %s>" % (self.app_name, self.migration)

########NEW FILE########
__FILENAME__ = modelsinspector
"""
Like the old south.modelsparser, but using introspection where possible
rather than direct inspection of models.py.
"""

import datetime
import re
import decimal

from south.utils import get_attribute, auto_through

from django.db import models
from django.db.models.base import ModelBase, Model
from django.db.models.fields import NOT_PROVIDED
from django.conf import settings
from django.utils.functional import Promise
from django.contrib.contenttypes import generic
from django.utils.datastructures import SortedDict

NOISY = False

# Gives information about how to introspect certain fields.
# This is a list of triples; the first item is a list of fields it applies to,
# (note that isinstance is used, so superclasses are perfectly valid here)
# the second is a list of positional argument descriptors, and the third
# is a list of keyword argument descriptors.
# Descriptors are of the form:
#  [attrname, options]
# Where attrname is the attribute on the field to get the value from, and options
# is an optional dict.
#
# The introspector uses the combination of all matching entries, in order.
introspection_details = [
    (
        (models.Field, ),
        [],
        {
            "null": ["null", {"default": False}],
            "blank": ["blank", {"default": False, "ignore_if":"primary_key"}],
            "primary_key": ["primary_key", {"default": False}],
            "max_length": ["max_length", {"default": None}],
            "unique": ["_unique", {"default": False}],
            "db_index": ["db_index", {"default": False}],
            "default": ["default", {"default": NOT_PROVIDED, "ignore_dynamics": True}],
            "db_column": ["db_column", {"default": None}],
            "db_tablespace": ["db_tablespace", {"default": settings.DEFAULT_INDEX_TABLESPACE}],
        },
    ),
    (
        (models.ForeignKey, models.OneToOneField),
        [],
        {
            "to": ["rel.to", {}],
            "to_field": ["rel.field_name", {"default_attr": "rel.to._meta.pk.name"}],
            "related_name": ["rel.related_name", {"default": None}],
            "db_index": ["db_index", {"default": True}],
        },
    ),
    (
        (models.ManyToManyField,),
        [],
        {
            "to": ["rel.to", {}],
            "symmetrical": ["rel.symmetrical", {"default": True}],
            "related_name": ["rel.related_name", {"default": None}],
            "db_table": ["db_table", {"default": None}],
            # TODO: Kind of ugly to add this one-time-only option
            "through": ["rel.through", {"ignore_if_auto_through": True}],
        },
    ),
    (
        (models.DateField, models.TimeField),
        [],
        {
            "auto_now": ["auto_now", {"default": False}],
            "auto_now_add": ["auto_now_add", {"default": False}],
        },
    ),
    (
        (models.DecimalField, ),
        [],
        {
            "max_digits": ["max_digits", {"default": None}],
            "decimal_places": ["decimal_places", {"default": None}],
        },
    ),
    (
        (models.BooleanField, ),
        [],
        {
            "default": ["default", {"default": NOT_PROVIDED, "converter": bool}],
        },
    ),
    (
        (models.FilePathField, ),
        [],
        {
            "path": ["path", {"default": ''}],
            "match": ["match", {"default": None}],
            "recursive": ["recursive", {"default": False}],
        },
    ),
    (
        (generic.GenericRelation, ),
        [],
        {
            "to": ["rel.to", {}],
            "symmetrical": ["rel.symmetrical", {"default": True}],
            "object_id_field": ["object_id_field_name", {"default": "object_id"}],
            "content_type_field": ["content_type_field_name", {"default": "content_type"}],
            "blank": ["blank", {"default": True}],
        },
    ),
]

# Regexes of allowed field full paths
allowed_fields = [
    "^django\.db",
    "^django\.contrib\.contenttypes\.generic",
    "^django\.contrib\.localflavor",
]

# Regexes of ignored fields (custom fields which look like fields, but have no column behind them)
ignored_fields = [
    "^django\.contrib\.contenttypes\.generic\.GenericRelation",
    "^django\.contrib\.contenttypes\.generic\.GenericForeignKey",
]

# Similar, but for Meta, so just the inner level (kwds).
meta_details = {
    "db_table": ["db_table", {"default_attr_concat": ["%s_%s", "app_label", "module_name"]}],
    "db_tablespace": ["db_tablespace", {"default": settings.DEFAULT_TABLESPACE}],
    "unique_together": ["unique_together", {"default": []}],
}

# 2.4 compatability
any = lambda x: reduce(lambda y, z: y or z, x, False)


def add_introspection_rules(rules=[], patterns=[]):
    "Allows you to add some introspection rules at runtime, e.g. for 3rd party apps."
    assert isinstance(rules, (list, tuple))
    assert isinstance(patterns, (list, tuple))
    allowed_fields.extend(patterns)
    introspection_details.extend(rules)

def add_ignored_fields(patterns):
    "Allows you to add some ignore field patterns."
    assert isinstance(patterns, (list, tuple))
    ignored_fields.extend(patterns)
    
def can_ignore(field):
    """
    Returns True if we know for certain that we can ignore this field, False
    otherwise.
    """
    full_name = "%s.%s" % (field.__class__.__module__, field.__class__.__name__)
    for regex in ignored_fields:
        if re.match(regex, full_name):
            return True
    return False

def can_introspect(field):
    """
    Returns True if we are allowed to introspect this field, False otherwise.
    ('allowed' means 'in core'. Custom fields can declare they are introspectable
    by the default South rules by adding the attribute _south_introspects = True.)
    """
    # Check for special attribute
    if hasattr(field, "_south_introspects") and field._south_introspects:
        return True
    # Check it's an introspectable field
    full_name = "%s.%s" % (field.__class__.__module__, field.__class__.__name__)
    for regex in allowed_fields:
        if re.match(regex, full_name):
            return True
    return False


def matching_details(field):
    """
    Returns the union of all matching entries in introspection_details for the field.
    """
    our_args = []
    our_kwargs = {}
    for classes, args, kwargs in introspection_details:
        if any([isinstance(field, x) for x in classes]):
            our_args.extend(args)
            our_kwargs.update(kwargs)
    return our_args, our_kwargs


class IsDefault(Exception):
    """
    Exception for when a field contains its default value.
    """


def get_value(field, descriptor):
    """
    Gets an attribute value from a Field instance and formats it.
    """
    attrname, options = descriptor
    # If the options say it's not a attribute name but a real value, use that.
    if options.get('is_value', False):
        value = attrname
    else:
        value = get_attribute(field, attrname)
    # Lazy-eval functions get eval'd.
    if isinstance(value, Promise):
        value = unicode(value)
    # If the value is the same as the default, omit it for clarity
    if "default" in options and value == options['default']:
        raise IsDefault
    # If there's an ignore_if, use it
    if "ignore_if" in options:
        if get_attribute(field, options['ignore_if']):
            raise IsDefault
    # If there's an ignore_if_auto_through which is True, use it
    if options.get("ignore_if_auto_through", False):
        if auto_through(field):
            raise IsDefault
    # Some default values need to be gotten from an attribute too.
    if "default_attr" in options:
        default_value = get_attribute(field, options['default_attr'])
        if value == default_value:
            raise IsDefault
    # Some are made from a formatting string and several attrs (e.g. db_table)
    if "default_attr_concat" in options:
        format, attrs = options['default_attr_concat'][0], options['default_attr_concat'][1:]
        default_value = format % tuple(map(lambda x: get_attribute(field, x), attrs))
        if value == default_value:
            raise IsDefault
    # Callables get called.
    if callable(value) and not isinstance(value, ModelBase):
        # Datetime.datetime.now is special, as we can access it from the eval
        # context (and because it changes all the time; people will file bugs otherwise).
        if value == datetime.datetime.now:
            return "datetime.datetime.now"
        if value == datetime.datetime.utcnow:
            return "datetime.datetime.utcnow"
        if value == datetime.date.today:
            return "datetime.date.today"
        # All other callables get called.
        value = value()
    # Models get their own special repr()
    if isinstance(value, ModelBase):
        # If it's a proxy model, follow it back to its non-proxy parent
        if getattr(value._meta, "proxy", False):
            value = value._meta.proxy_for_model
        return "orm['%s.%s']" % (value._meta.app_label, value._meta.object_name)
    # As do model instances
    if isinstance(value, Model):
        if options.get("ignore_dynamics", False):
            raise IsDefault
        return "orm['%s.%s'].objects.get(pk=%r)" % (value.__class__._meta.app_label, value.__class__._meta.object_name, value.pk)
    # Make sure Decimal is converted down into a string
    if isinstance(value, decimal.Decimal):
        value = str(value)
    # Now, apply the converter func if there is one
    if "converter" in options:
        value = options['converter'](value)
    # Return the final value
    return repr(value)


def introspector(field):
    """
    Given a field, introspects its definition triple.
    """
    arg_defs, kwarg_defs = matching_details(field)
    args = []
    kwargs = {}
    # For each argument, use the descriptor to get the real value.
    for defn in arg_defs:
        try:
            args.append(get_value(field, defn))
        except IsDefault:
            pass
    for kwd, defn in kwarg_defs.items():
        try:
            kwargs[kwd] = get_value(field, defn)
        except IsDefault:
            pass
    return args, kwargs


def get_model_fields(model, m2m=False):
    """
    Given a model class, returns a dict of {field_name: field_triple} defs.
    """
    
    field_defs = SortedDict()
    inherited_fields = {}
    
    # Go through all bases (that are themselves models, but not Model)
    for base in model.__bases__:
        if base != models.Model and issubclass(base, models.Model):
            if not base._meta.abstract:
                # Looks like we need their fields, Ma.
                inherited_fields.update(get_model_fields(base))
    
    # Now, go through all the fields and try to get their definition
    source = model._meta.local_fields[:]
    if m2m:
        source += model._meta.local_many_to_many
    
    for field in source:
        # Can we ignore it completely?
        if can_ignore(field):
            continue
        # Does it define a south_field_triple method?
        if hasattr(field, "south_field_triple"):
            if NOISY:
                print " ( Nativing field: %s" % field.name
            field_defs[field.name] = field.south_field_triple()
        # Can we introspect it?
        elif can_introspect(field):
            # Get the full field class path.
            field_class = field.__class__.__module__ + "." + field.__class__.__name__
            # Run this field through the introspector
            args, kwargs = introspector(field)
            # That's our definition!
            field_defs[field.name] = (field_class, args, kwargs)
        # Shucks, no definition!
        else:
            if NOISY:
                print " ( Nodefing field: %s" % field.name
            field_defs[field.name] = None
    
    # If they've used the horrific hack that is order_with_respect_to, deal with
    # it.
    if model._meta.order_with_respect_to:
        field_defs['_order'] = ("django.db.models.fields.IntegerField", [], {"default": "0"})
    
    return field_defs


def get_model_meta(model):
    """
    Given a model class, will return the dict representing the Meta class.
    """
    
    # Get the introspected attributes
    meta_def = {}
    for kwd, defn in meta_details.items():
        try:
            meta_def[kwd] = get_value(model._meta, defn)
        except IsDefault:
            pass
    
    # Also, add on any non-abstract model base classes.
    # This is called _ormbases as the _bases variable was previously used
    # for a list of full class paths to bases, so we can't conflict.
    for base in model.__bases__:
        if base != models.Model and issubclass(base, models.Model):
            if not base._meta.abstract:
                # OK, that matches our terms.
                if "_ormbases" not in meta_def:
                    meta_def['_ormbases'] = []
                meta_def['_ormbases'].append("%s.%s" % (
                    base._meta.app_label,
                    base._meta.object_name,
                ))
    
    return meta_def


# Now, load the built-in South introspection plugins
import south.introspection_plugins

########NEW FILE########
__FILENAME__ = orm
"""
South's fake ORM; lets you not have to write SQL inside migrations.
Roughly emulates the real Django ORM, to a point.
"""

import inspect
import datetime

from django.db import models
from django.db.models.loading import cache
from django.core.exceptions import ImproperlyConfigured

from south.db import db
from south.utils import ask_for_it_by_name
from south.hacks import hacks
from south.exceptions import UnfreezeMeLater, ORMBaseNotIncluded, ImpossibleORMUnfreeze


class ModelsLocals(object):
    
    """
    Custom dictionary-like class to be locals();
    falls back to lowercase search for items that don't exist
    (because we store model names as lowercase).
    """
    
    def __init__(self, data):
        self.data = data
    
    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            return self.data[key.lower()]


# Stores already-created ORMs.
_orm_cache = {}

def FakeORM(*args):
    """
    Creates a Fake Django ORM.
    This is actually a memoised constructor; the real class is _FakeORM.
    """
    if not args in _orm_cache:
        _orm_cache[args] = _FakeORM(*args)  
    return _orm_cache[args]


class LazyFakeORM(object):
    """
    In addition to memoising the ORM call, this function lazily generates them
    for a Migration class. Assign the result of this to (for example)
    .orm, and as soon as .orm is accessed the ORM will be created.
    """
    
    def __init__(self, *args):
        self._args = args
        self.orm = None
    
    def __get__(self, obj, type=None):
        if not self.orm:
            self.orm = FakeORM(*self._args)
        return self.orm


class _FakeORM(object):
    
    """
    Simulates the Django ORM at some point in time,
    using a frozen definition on the Migration class.
    """
    
    def __init__(self, cls, app):
        self.default_app = app
        self.cls = cls
        # Try loading the models off the migration class; default to no models.
        self.models = {}
        try:
            self.models_source = cls.models
        except AttributeError:
            return
        
        # Start a 'new' AppCache
        hacks.clear_app_cache()
        
        # Now, make each model's data into a FakeModel
        # We first make entries for each model that are just its name
        # This allows us to have circular model dependency loops
        model_names = []
        for name, data in self.models_source.items():
            # Make sure there's some kind of Meta
            if "Meta" not in data:
                data['Meta'] = {}
            try:
                app_label, model_name = name.split(".", 1)
            except ValueError:
                app_label = self.default_app
                model_name = name
            
            # If there's an object_name in the Meta, use it and remove it
            if "object_name" in data['Meta']:
                model_name = data['Meta']['object_name']
                del data['Meta']['object_name']
            
            name = "%s.%s" % (app_label, model_name)
            self.models[name.lower()] = name
            model_names.append((name.lower(), app_label, model_name, data))
        
        # Loop until model_names is entry, or hasn't shrunk in size since
        # last iteration.
        # The make_model method can ask to postpone a model; it's then pushed
        # to the back of the queue. Because this is currently only used for
        # inheritance, it should thus theoretically always decrease by one.
        last_size = None
        while model_names:
            # First, make sure we've shrunk.
            if len(model_names) == last_size:
                raise ImpossibleORMUnfreeze()
            last_size = len(model_names)
            # Make one run through
            postponed_model_names = []
            for name, app_label, model_name, data in model_names:
                try:
                    self.models[name] = self.make_model(app_label, model_name, data)
                except UnfreezeMeLater:
                    postponed_model_names.append((name, app_label, model_name, data))
            # Reset
            model_names = postponed_model_names
        
        # And perform the second run to iron out any circular/backwards depends.
        self.retry_failed_fields()
        
        # Force evaluation of relations on the models now
        for model in self.models.values():
            model._meta.get_all_field_names()
        
        # Reset AppCache
        hacks.unclear_app_cache()
    
    
    def __iter__(self):
        return iter(self.models.values())

    
    def __getattr__(self, key):
        fullname = (self.default_app+"."+key).lower()
        try:
            return self.models[fullname]
        except KeyError:
            raise AttributeError("The model '%s' from the app '%s' is not available in this migration. (Did you use orm.ModelName, not orm['app.ModelName']?)" % (key, self.default_app))
    
    
    def __getitem__(self, key):
        # Detect if they asked for a field on a model or not.
        if ":" in key:
            key, fname = key.split(":")
        else:
            fname = None
        # Now, try getting the model
        key = key.lower()
        try:
            model = self.models[key]
        except KeyError:
            try:
                app, model = key.split(".", 1)
            except ValueError:
                raise KeyError("The model '%s' is not in appname.modelname format." % key)
            else:
                raise KeyError("The model '%s' from the app '%s' is not available in this migration." % (model, app))
        # If they asked for a field, get it.
        if fname:
            return model._meta.get_field_by_name(fname)[0]
        else:
            return model
    
    
    def eval_in_context(self, code, app, extra_imports={}):
        "Evaluates the given code in the context of the migration file."
        
        # Drag in the migration module's locals (hopefully including models.py)
        fake_locals = dict(inspect.getmodule(self.cls).__dict__)
        
        # Remove all models from that (i.e. from modern models.py), to stop pollution
        for key, value in fake_locals.items():
            if isinstance(value, type) and issubclass(value, models.Model) and hasattr(value, "_meta"):
                del fake_locals[key]
        
        # We add our models into the locals for the eval
        fake_locals.update(dict([
            (name.split(".")[-1], model)
            for name, model in self.models.items()
        ]))
        
        # Make sure the ones for this app override.
        fake_locals.update(dict([
            (name.split(".")[-1], model)
            for name, model in self.models.items()
            if name.split(".")[0] == app
        ]))
        
        # Ourselves as orm, to allow non-fail cross-app referencing
        fake_locals['orm'] = self
        
        # And a fake _ function
        fake_locals['_'] = lambda x: x
        
        # Datetime; there should be no datetime direct accesses
        fake_locals['datetime'] = datetime
        
        # Now, go through the requested imports and import them.
        for name, value in extra_imports.items():
            # First, try getting it out of locals.
            parts = value.split(".")
            try:
                obj = fake_locals[parts[0]]
                for part in parts[1:]:
                    obj = getattr(obj, part)
            except (KeyError, AttributeError):
                pass
            else:
                fake_locals[name] = obj
                continue
            # OK, try to import it directly
            try:
                fake_locals[name] = ask_for_it_by_name(value)
            except ImportError:
                if name == "SouthFieldClass":
                    raise ValueError("Cannot import the required field '%s'" % value)
                else:
                    print "WARNING: Cannot import '%s'" % value
        
        # Use ModelsLocals to make lookups work right for CapitalisedModels
        fake_locals = ModelsLocals(fake_locals)
        
        return eval(code, globals(), fake_locals)
    
    
    def make_meta(self, app, model, data, stub=False):
        "Makes a Meta class out of a dict of eval-able arguments."
        results = {'app_label': app}
        for key, code in data.items():
            # Some things we never want to use.
            if key in ["_bases", "_ormbases"]:
                continue
            # Some things we don't want with stubs.
            if stub and key in ["order_with_respect_to"]:
                continue
            # OK, add it.
            try:
                results[key] = self.eval_in_context(code, app)
            except (NameError, AttributeError), e:
                raise ValueError("Cannot successfully create meta field '%s' for model '%s.%s': %s." % (
                    key, app, model, e
                ))
        return type("Meta", tuple(), results) 
    
    
    def make_model(self, app, name, data):
        "Makes a Model class out of the given app name, model name and pickled data."
        
        # Extract any bases out of Meta
        if "_ormbases" in data['Meta']:
            # Make sure everything we depend on is done already; otherwise, wait.
            for key in data['Meta']['_ormbases']:
                key = key.lower()
                if key not in self.models:
                    raise ORMBaseNotIncluded("Cannot find ORM base %s" % key)
                elif isinstance(self.models[key], basestring):
                    # Then the other model hasn't been unfrozen yet.
                    # We postpone ourselves; the situation will eventually resolve.
                    raise UnfreezeMeLater()
            bases = [self.models[key.lower()] for key in data['Meta']['_ormbases']]
        # Perhaps the old style?
        elif "_bases" in data['Meta']:
            bases = map(ask_for_it_by_name, data['Meta']['_bases'])
        # Ah, bog standard, then.
        else:
            bases = [models.Model]
        
        # Turn the Meta dict into a basic class
        meta = self.make_meta(app, name, data['Meta'], data.get("_stub", False))
        
        failed_fields = {}
        fields = {}
        stub = False
        
        # Now, make some fields!
        for fname, params in data.items():
            # If it's the stub marker, ignore it.
            if fname == "_stub":
                stub = bool(params)
                continue
            elif fname == "Meta":
                continue
            elif not params:
                raise ValueError("Field '%s' on model '%s.%s' has no definition." % (fname, app, name))
            elif isinstance(params, (str, unicode)):
                # It's a premade definition string! Let's hope it works...
                code = params
                extra_imports = {}
            else:
                # If there's only one parameter (backwards compat), make it 3.
                if len(params) == 1:
                    params = (params[0], [], {})
                # There should be 3 parameters. Code is a tuple of (code, what-to-import)
                if len(params) == 3:
                    code = "SouthFieldClass(%s)" % ", ".join(
                        params[1] +
                        ["%s=%s" % (n, v) for n, v in params[2].items()]
                    )
                    extra_imports = {"SouthFieldClass": params[0]}
                else:
                    raise ValueError("Field '%s' on model '%s.%s' has a weird definition length (should be 1 or 3 items)." % (fname, app, name))
            
            try:
                # Execute it in a probably-correct context.
                field = self.eval_in_context(code, app, extra_imports)
            except (NameError, AttributeError, AssertionError, KeyError):
                # It might rely on other models being around. Add it to the
                # model for the second pass.
                failed_fields[fname] = (code, extra_imports)
            else:
                fields[fname] = field
        
        # Find the app in the Django core, and get its module
        more_kwds = {}
        try:
            app_module = models.get_app(app)
            more_kwds['__module__'] = app_module.__name__
        except ImproperlyConfigured:
            # The app this belonged to has vanished, but thankfully we can still
            # make a mock model, so ignore the error.
            more_kwds['__module__'] = '_south_mock'
        
        more_kwds['Meta'] = meta
        
        # Make our model
        fields.update(more_kwds)
        
        model = type(
            str(name),
            tuple(bases),
            fields,
        )
        
        # If this is a stub model, change Objects to a whiny class
        if stub:
            model.objects = WhinyManager()
            # Also, make sure they can't instantiate it
            model.__init__ = whiny_method
        else:
            model.objects = NoDryRunManager(model.objects)
        
        if failed_fields:
            model._failed_fields = failed_fields
        
        return model
    
    def retry_failed_fields(self):
        "Tries to re-evaluate the _failed_fields for each model."
        for modelkey, model in self.models.items():
            app, modelname = modelkey.split(".", 1)
            if hasattr(model, "_failed_fields"):
                for fname, (code, extra_imports) in model._failed_fields.items():
                    try:
                        field = self.eval_in_context(code, app, extra_imports)
                    except (NameError, AttributeError, AssertionError, KeyError), e:
                        # It's failed again. Complain.
                        raise ValueError("Cannot successfully create field '%s' for model '%s': %s." % (
                            fname, modelname, e
                        ))
                    else:
                        # Startup that field.
                        model.add_to_class(fname, field)


class WhinyManager(object):
    "A fake manager that whines whenever you try to touch it. For stub models."
    
    def __getattr__(self, key):
        raise AttributeError("You cannot use items from a stub model.")


class NoDryRunManager(object):
    """
    A manager that always proxies through to the real manager,
    unless a dry run is in progress.
    """
    
    def __init__(self, real):
        self.real = real
    
    def __getattr__(self, name):
        if db.dry_run:
            raise AttributeError("You are in a dry run, and cannot access the ORM.\nWrap ORM sections in 'if not db.dry_run:', or if the whole migration is only a data migration, set no_dry_run = True on the Migration class.")
        return getattr(self.real, name)


def whiny_method(*a, **kw):
    raise ValueError("You cannot instantiate a stub model.")

########NEW FILE########
__FILENAME__ = signals
"""
South-specific signals
"""

from django.dispatch import Signal
from django.conf import settings

# Sent at the start of the migration of an app
pre_migrate = Signal(providing_args=["app"])

# Sent after each successful migration of an app
post_migrate = Signal(providing_args=["app"])

# Sent after each run of a particular migration in a direction
ran_migration = Signal(providing_args=["app","migration","method"])

# Compatibility code for django.contrib.auth
if 'django.contrib.auth' in settings.INSTALLED_APPS:
    def create_permissions_compat(app, **kwargs):
        from django.db.models import get_app
        from django.contrib.auth.management import create_permissions
        create_permissions(get_app(app), (), 0)
    post_migrate.connect(create_permissions_compat)

########NEW FILE########
__FILENAME__ = autodetection
import unittest

from south.creator.changes import AutoChanges

class TestComparison(unittest.TestCase):
    
    """
    Tests the comparison methods of startmigration.
    """
    
    def test_no_change(self):
        "Test with a completely unchanged definition."
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['southdemo.Lizard']"}),
                ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['southdemo.Lizard']"}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.related.ForeignKey', ['ohhai', 'there'], {'to': "somewhere", "from": "there"}),
                ('django.db.models.fields.related.ForeignKey', ['ohhai', 'there'], {"from": "there", 'to': "somewhere"}),
            ),
            False,
        )
    
    
    def test_pos_change(self):
        "Test with a changed positional argument."
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['hi'], {'to': "foo"}),
                ('django.db.models.fields.CharField', [], {'to': "foo"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', [], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['bye'], {'to': "foo"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['pi'], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['pi'], {'to': "foo"}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['pisdadad'], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['pi'], {'to': "foo"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['hi'], {}),
                ('django.db.models.fields.CharField', [], {}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', [], {}),
                ('django.db.models.fields.CharField', ['bye'], {}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['pi'], {}),
                ('django.db.models.fields.CharField', ['pi'], {}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['pi'], {}),
                ('django.db.models.fields.CharField', ['45fdfdf'], {}),
            ),
            True,
        )
    
    
    def test_kwd_change(self):
        "Test a changed keyword argument"
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['pi'], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['pi'], {'to': "blue"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', [], {'to': "foo"}),
                ('django.db.models.fields.CharField', [], {'to': "blue"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['b'], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['b'], {'to': "blue"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', [], {'to': "foo"}),
                ('django.db.models.fields.CharField', [], {}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['a'], {'to': "foo"}),
                ('django.db.models.fields.CharField', ['a'], {}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', [], {}),
                ('django.db.models.fields.CharField', [], {'to': "foo"}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('django.db.models.fields.CharField', ['a'], {}),
                ('django.db.models.fields.CharField', ['a'], {'to': "foo"}),
            ),
            True,
        )
        
    
    
    def test_backcompat_nochange(self):
        "Test that the backwards-compatable comparison is working"
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', [], {}),
                ('django.db.models.fields.CharField', [], {}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['ack'], {}),
                ('django.db.models.fields.CharField', ['ack'], {}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', [], {'to':'b'}),
                ('django.db.models.fields.CharField', [], {'to':'b'}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {'to':'you'}),
                ('django.db.models.fields.CharField', ['hah'], {'to':'you'}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {'to':'you'}),
                ('django.db.models.fields.CharField', ['hah'], {'to':'heh'}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {}),
                ('django.db.models.fields.CharField', [], {'to':"orm['appname.hah']"}),
            ),
            False,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {}),
                ('django.db.models.fields.CharField', [], {'to':'hah'}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {}),
                ('django.db.models.fields.CharField', [], {'to':'rrr'}),
            ),
            True,
        )
        
        self.assertEqual(
            AutoChanges.different_attributes(
                ('models.CharField', ['hah'], {}),
                ('django.db.models.fields.IntField', [], {'to':'hah'}),
            ),
            True,
        )
########NEW FILE########
__FILENAME__ = 0001_depends_on_unmigrated
from south.db import db
from django.db import models

class Migration:

    depends_on = [('unknown', '0001_initial')]
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0002_depends_on_unknown
from south.db import db
from django.db import models

class Migration:

    depends_on = [('fakeapp', '9999_unknown')]
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0003_depends_on_higher
from south.db import db
from django.db import models

class Migration:

    depends_on = [('brokenapp', '0004_higher')]
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0004_higher
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-

from django.db import models
from django.contrib.auth.models import User as UserAlias

def default_func():
    return "yays"

# An empty case.
class Other1(models.Model): pass

# Nastiness.
class HorribleModel(models.Model):
    "A model to test the edge cases of model parsing"
    
    ZERO, ONE = range(2)
    
    # First, some nice fields
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    
    # A ForeignKey, to a model above, and then below
    o1 = models.ForeignKey(Other1)
    o2 = models.ForeignKey('Other2')
    
    # Now to something outside
    user = models.ForeignKey(UserAlias, related_name="horribles")
    
    # Unicode!
    code = models.CharField(max_length=25, default="↑↑↓↓←→←→BA")
    
    # Odd defaults!
    class_attr = models.IntegerField(default=ZERO)
    func = models.CharField(max_length=25, default=default_func)
    
    # Time to get nasty. Define a non-field choices, and use it
    choices = [('hello', '1'), ('world', '2')]
    choiced = models.CharField(max_length=20, choices=choices)
    
    class Meta:
        db_table = "my_fave"
        verbose_name = "Dr. Strangelove," + \
                     """or how I learned to stop worrying
and love the bomb"""
    
    # Now spread over multiple lines
    multiline = \
              models.TextField(
        )
    
# Special case.
class Other2(models.Model):
    # Try loading a field without a newline after it (inspect hates this)
    close_but_no_cigar = models.PositiveIntegerField(primary_key=True)
########NEW FILE########
__FILENAME__ = 0001_first
from south.db import db
from django.db import models

class Migration:
    
    depends_on = [('circular_b', '0001_first')]
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = 0001_first
from south.db import db
from django.db import models

class Migration:
    
    depends_on = [('circular_a', '0001_first')]
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = db
import unittest

from south.db import db
from django.db import connection, models

# Create a list of error classes from the various database libraries
errors = []
try:
    from psycopg2 import ProgrammingError
    errors.append(ProgrammingError)
except ImportError:
    pass
errors = tuple(errors)

class TestOperations(unittest.TestCase):

    """
    Tests if the various DB abstraction calls work.
    Can only test a limited amount due to DB differences.
    """

    def setUp(self):
        db.debug = False
        db.clear_deferred_sql()
        db.start_transaction()
    
    def tearDown(self):
        db.rollback_transaction()

    def test_create(self):
        """
        Test creation of tables.
        """
        cursor = connection.cursor()
        # It needs to take at least 2 args
        self.assertRaises(TypeError, db.create_table)
        self.assertRaises(TypeError, db.create_table, "test1")
        # Empty tables (i.e. no columns) are not fine, so make at least 1
        db.create_table("test1", [('email_confirmed', models.BooleanField(default=False))])
        # And should exist
        cursor.execute("SELECT * FROM test1")
        # Make sure we can't do the same query on an empty table
        try:
            cursor.execute("SELECT * FROM nottheretest1")
            self.fail("Non-existent table could be selected!")
        except:
            pass
    
    def test_delete(self):
        """
        Test deletion of tables.
        """
        db.create_table("test_deltable", [('email_confirmed', models.BooleanField(default=False))])
        db.delete_table("test_deltable")
        # Make sure it went
        try:
            cursor.execute("SELECT * FROM test1")
            self.fail("Just-deleted table could be selected!")
        except:
            pass
    
    def test_nonexistent_delete(self):
        """
        Test deletion of nonexistent tables.
        """
        try:
            db.delete_table("test_nonexistdeltable")
            self.fail("Non-existent table could be deleted!")
        except:
            pass
    
    def test_foreign_keys(self):
        """
        Tests foreign key creation, especially uppercase (see #61)
        """
        Test = db.mock_model(model_name='Test', db_table='test5a',
                             db_tablespace='', pk_field_name='ID',
                             pk_field_type=models.AutoField, pk_field_args=[])
        db.create_table("test5a", [('ID', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True))])
        db.create_table("test5b", [
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('UNIQUE', models.ForeignKey(Test)),
        ])
        db.execute_deferred_sql()
    
    def test_rename(self):
        """
        Test column renaming
        """
        cursor = connection.cursor()
        db.create_table("test_rn", [('spam', models.BooleanField(default=False))])
        # Make sure we can select the column
        cursor.execute("SELECT spam FROM test_rn")
        # Rename it
        db.rename_column("test_rn", "spam", "eggs")
        cursor.execute("SELECT eggs FROM test_rn")
        db.commit_transaction()
        db.start_transaction()
        try:
            cursor.execute("SELECT spam FROM test_rn")
            self.fail("Just-renamed column could be selected!")
        except:
            pass
        db.rollback_transaction()
        db.delete_table("test_rn")
        db.start_transaction()
    
    def test_dry_rename(self):
        """
        Test column renaming while --dry-run is turned on (should do nothing)
        See ticket #65
        """
        cursor = connection.cursor()
        db.create_table("test_drn", [('spam', models.BooleanField(default=False))])
        # Make sure we can select the column
        cursor.execute("SELECT spam FROM test_drn")
        # Rename it
        db.dry_run = True
        db.rename_column("test_drn", "spam", "eggs")
        db.dry_run = False
        cursor.execute("SELECT spam FROM test_drn")
        db.commit_transaction()
        db.start_transaction()
        try:
            cursor.execute("SELECT eggs FROM test_drn")
            self.fail("Dry-renamed new column could be selected!")
        except:
            pass
        db.rollback_transaction()
        db.delete_table("test_drn")
        db.start_transaction()
    
    def test_table_rename(self):
        """
        Test column renaming
        """
        cursor = connection.cursor()
        db.create_table("testtr", [('spam', models.BooleanField(default=False))])
        # Make sure we can select the column
        cursor.execute("SELECT spam FROM testtr")
        # Rename it
        db.rename_table("testtr", "testtr2")
        cursor.execute("SELECT spam FROM testtr2")
        db.commit_transaction()
        db.start_transaction()
        try:
            cursor.execute("SELECT spam FROM testtr")
            self.fail("Just-renamed column could be selected!")
        except:
            pass
        db.rollback_transaction()
        db.delete_table("testtr2")
        db.start_transaction()
    
    def test_percents_in_defaults(self):
        """
        Test that % in a default gets escaped to %%.
        """
        cursor = connection.cursor()
        try:
            db.create_table("testpind", [('cf', models.CharField(max_length=255, default="It should be 2%!"))])
        except IndexError:
            self.fail("% was not properly escaped in column SQL.")
        db.delete_table("testpind")
    
    def test_index(self):
        """
        Test the index operations
        """
        db.create_table("test3", [
            ('SELECT', models.BooleanField(default=False)),
            ('eggs', models.IntegerField(unique=True)),
        ])
        db.execute_deferred_sql()
        # Add an index on that column
        db.create_index("test3", ["SELECT"])
        # Add another index on two columns
        db.create_index("test3", ["SELECT", "eggs"])
        # Delete them both
        db.delete_index("test3", ["SELECT"])
        db.delete_index("test3", ["SELECT", "eggs"])
        # Delete the unique index/constraint
        if db.backend_name != "sqlite3":
            db.delete_unique("test3", ["eggs"])
        db.delete_table("test3")
    
    def test_primary_key(self):
        """
        Test the primary key operations
        """
        
        # SQLite backend doesn't support this yet.
        if db.backend_name == "sqlite3":
            return
        
        db.create_table("test_pk", [
            ('id', models.IntegerField(primary_key=True)),
            ('new_pkey', models.IntegerField()),
            ('eggs', models.IntegerField(unique=True)),
        ])
        db.execute_deferred_sql()
        # Remove the default primary key, and make eggs it
        db.delete_primary_key("test_pk")
        db.create_primary_key("test_pk", "new_pkey")
        # Try inserting a now-valid row pair
        db.execute("INSERT INTO test_pk (id, new_pkey, eggs) VALUES (1, 2, 3)")
        db.execute("INSERT INTO test_pk (id, new_pkey, eggs) VALUES (1, 3, 4)")
        db.delete_table("test_pk")
    
    def test_primary_key_implicit(self):
        """
        Tests changing primary key implicitly.
        """
        
        # This is ONLY important for SQLite. It's not a feature we support, but
        # not implementing it means SQLite fails (due to the table-copying weirdness).
        if db.backend_name != "sqlite3":
            return
        
        db.create_table("test_pki", [
            ('id', models.IntegerField(primary_key=True)),
            ('new_pkey', models.IntegerField()),
            ('eggs', models.IntegerField(unique=True)),
        ])
        db.execute_deferred_sql()
        # Remove the default primary key, and make eggs it
        db.alter_column("test_pki", "id", models.IntegerField())
        db.alter_column("test_pki", "new_pkey", models.IntegerField(primary_key=True))
        # Try inserting a now-valid row pair
        db.execute("INSERT INTO test_pki (id, new_pkey, eggs) VALUES (1, 2, 3)")
        db.execute("INSERT INTO test_pki (id, new_pkey, eggs) VALUES (1, 3, 4)")
        db.delete_table("test_pki")
        
    
    def test_add_columns(self):
        """
        Test adding columns
        """
        db.create_table("test_addc", [
            ('spam', models.BooleanField(default=False)),
            ('eggs', models.IntegerField()),
        ])
        # Add a column
        db.add_column("test_addc", "add1", models.IntegerField(default=3), keep_default=False)
        # Add a FK with keep_default=False (#69)
        User = db.mock_model(model_name='User', db_table='auth_user', db_tablespace='', pk_field_name='id', pk_field_type=models.AutoField, pk_field_args=[], pk_field_kwargs={})
        # insert some data so we can test the default value of the added fkey
        db.execute("INSERT INTO test_addc (eggs, add1) VALUES (1, 2)")
        db.add_column("test_addc", "user", models.ForeignKey(User, null=True), keep_default=False)
        # try selecting from the user_id column to make sure it was actually created
        val = db.execute("SELECT user_id FROM test_addc")[0][0]
        self.assertEquals(val, None)
        db.delete_column("test_addc", "add1")
        db.delete_table("test_addc")
    
    def test_alter_columns(self):
        """
        Test altering columns
        """
        db.create_table("test_alterc", [
            ('spam', models.BooleanField(default=False)),
            ('eggs', models.IntegerField()),
        ])
        # Change eggs to be a FloatField
        db.alter_column("test_alterc", "eggs", models.FloatField())
        db.delete_table("test_alterc")
    
    def test_mysql_defaults(self):
        """
        Test MySQL default handling for BLOB and TEXT.
        """
        db.create_table("test_altermyd", [
            ('spam', models.BooleanField(default=False)),
            ('eggs', models.TextField()),
        ])
        # Change eggs to be a FloatField
        db.alter_column("test_altermyd", "eggs", models.TextField(null=True))
        db.delete_table("test_altermyd")
    
    def test_alter_column_postgres_multiword(self):
        """
        Tests altering columns with multiple words in Postgres types (issue #125)
        e.g. 'datetime with time zone', look at django/db/backends/postgresql/creation.py
        """
        db.create_table("test_multiword", [
            ('col_datetime', models.DateTimeField(null=True)),
            ('col_integer', models.PositiveIntegerField(null=True)),
            ('col_smallint', models.PositiveSmallIntegerField(null=True)),
            ('col_float', models.FloatField(null=True)),
        ])
        
        # test if 'double precision' is preserved
        db.alter_column('test_multiword', 'col_float', models.FloatField('float', null=True))

        # test if 'CHECK ("%(column)s" >= 0)' is stripped
        db.alter_column('test_multiword', 'col_integer', models.PositiveIntegerField(null=True))
        db.alter_column('test_multiword', 'col_smallint', models.PositiveSmallIntegerField(null=True))

        # test if 'with timezone' is preserved
        if db.backend_name == "postgres":
            db.execute("INSERT INTO test_multiword (col_datetime) VALUES ('2009-04-24 14:20:55+02')")
            db.alter_column('test_multiword', 'col_datetime', models.DateTimeField(auto_now=True))
            assert db.execute("SELECT col_datetime = '2009-04-24 14:20:55+02' FROM test_multiword")[0][0]

        db.delete_table("test_multiword")
    
    def test_alter_constraints(self):
        """
        Tests that going from a PostiveIntegerField to an IntegerField drops
        the constraint on the database.
        """
        # Only applies to databases that support CHECK constraints
        if not db.has_check_constraints:
            return
        # Make the test table
        db.create_table("test_alterc", [
            ('num', models.PositiveIntegerField()),
        ])
        # Add in some test values
        db.execute("INSERT INTO test_alterc (num) VALUES (1)")
        db.execute("INSERT INTO test_alterc (num) VALUES (2)")
        # Ensure that adding a negative number is bad
        db.commit_transaction()
        db.start_transaction()
        try:
            db.execute("INSERT INTO test_alterc (num) VALUES (-3)")
        except:
            db.rollback_transaction()
        else:
            self.fail("Could insert a negative integer into a PositiveIntegerField.")
        # Alter it to a normal IntegerField
        db.alter_column("test_alterc", "num", models.IntegerField())
        # It should now work
        db.execute("INSERT INTO test_alterc (num) VALUES (-3)")
        db.delete_table("test_alterc")
        # We need to match up for tearDown
        db.start_transaction()
    
    def test_unique(self):
        """
        Tests creating/deleting unique constraints.
        """
        
        # SQLite backend doesn't support this yet.
        if db.backend_name == "sqlite3":
            return
        
        db.create_table("test_unique2", [
            ('id', models.AutoField(primary_key=True)),
        ])
        db.create_table("test_unique", [
            ('spam', models.BooleanField(default=False)),
            ('eggs', models.IntegerField()),
            ('ham', models.ForeignKey(db.mock_model('Unique2', 'test_unique2'))),
        ])
        # Add a constraint
        db.create_unique("test_unique", ["spam"])
        # Shouldn't do anything during dry-run
        db.dry_run = True
        db.delete_unique("test_unique", ["spam"])
        db.dry_run = False
        db.delete_unique("test_unique", ["spam"])
        db.create_unique("test_unique", ["spam"])
        db.commit_transaction()
        db.start_transaction()
        
        # Test it works
        db.execute("INSERT INTO test_unique2 (id) VALUES (1)")
        db.execute("INSERT INTO test_unique2 (id) VALUES (2)")
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 0, 1)")
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (false, 1, 2)")
        try:
            db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 2, 1)")
        except:
            db.rollback_transaction()
        else:
            self.fail("Could insert non-unique item.")
        
        # Drop that, add one only on eggs
        db.delete_unique("test_unique", ["spam"])
        db.execute("DELETE FROM test_unique")
        db.create_unique("test_unique", ["eggs"])
        db.start_transaction()
        
        # Test similarly
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 0, 1)")
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (false, 1, 2)")
        try:
            db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 1, 1)")
        except:
            db.rollback_transaction()
        else:
            self.fail("Could insert non-unique item.")
        
        # Drop those, test combined constraints
        db.delete_unique("test_unique", ["eggs"])
        db.execute("DELETE FROM test_unique")
        db.create_unique("test_unique", ["spam", "eggs", "ham_id"])
        db.start_transaction()
        # Test similarly
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 0, 1)")
        db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (false, 1, 1)")
        try:
            db.execute("INSERT INTO test_unique (spam, eggs, ham_id) VALUES (true, 0, 1)")
        except:
            db.rollback_transaction()
        else:
            self.fail("Could insert non-unique pair.")
        db.delete_unique("test_unique", ["spam", "eggs", "ham_id"])
        db.start_transaction()
    
    def test_capitalised_constraints(self):
        """
        Under PostgreSQL at least, capitalised constrains must be quoted.
        """
        db.create_table("test_capconst", [
            ('SOMECOL', models.PositiveIntegerField(primary_key=True)),
        ])
        # Alter it so it's not got the check constraint
        db.alter_column("test_capconst", "SOMECOL", models.IntegerField())
    
    def test_text_default(self):
        """
        MySQL cannot have blank defaults on TEXT columns.
        """
        db.create_table("test_textdef", [
            ('textcol', models.TextField(blank=True)),
        ])
    
    def test_add_unique_fk(self):
        """
        Test adding a ForeignKey with unique=True or a OneToOneField
        """
        db.create_table("test_add_unique_fk", [
            ('spam', models.BooleanField(default=False))
        ])
        
        db.add_column("test_add_unique_fk", "mock1", models.ForeignKey(db.mock_model('Mock', 'mock'), null=True, unique=True))
        db.add_column("test_add_unique_fk", "mock2", models.OneToOneField(db.mock_model('Mock', 'mock'), null=True))
        
        db.delete_table("test_add_unique_fk")

########NEW FILE########
__FILENAME__ = 0001_a
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0002_a
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0003_a
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0004_a
from south.db import db
from django.db import models

class Migration:

    depends_on = [('deps_b', '0003_b')]

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0005_a
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = 0001_b
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0002_b
from south.db import db
from django.db import models

class Migration:

    depends_on = [('deps_a', '0002_a')]

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0003_b
from south.db import db
from django.db import models

class Migration:

    depends_on = [('deps_a', '0003_a')]

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0004_b
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0005_b
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = 0001_c
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0002_c
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0003_c
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0004_c
from south.db import db
from django.db import models

class Migration:

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0005_c
from south.db import db
from django.db import models

class Migration:

    depends_on = [('deps_a', '0002_a')]

    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = 0001_spam
from south.db import db
from django.db import models

class Migration:
    
    def forwards(self):
        # Model 'Spam'
        db.create_table("southtest_spam", (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('weight', models.FloatField()),
            ('expires', models.DateTimeField()),
            ('name', models.CharField(max_length=255))
        ))
    
    def backwards(self):
        db.delete_table("southtest_spam")


########NEW FILE########
__FILENAME__ = 0002_eggs
from south.db import db
from django.db import models

class Migration:
    
    def forwards(self):
        
        Spam = db.mock_model(model_name='Spam', db_table='southtest_spam', db_tablespace='', pk_field_name='id', pk_field_type=models.AutoField)
        
        db.create_table("southtest_eggs", (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('size', models.FloatField()),
            ('quantity', models.IntegerField()),
            ('spam', models.ForeignKey(Spam)),
        ))
    
    def backwards(self):
        
        db.delete_table("southtest_eggs")


########NEW FILE########
__FILENAME__ = 0003_alter_spam
from south.db import db
from django.db import models

class Migration:
    
    def forwards(self):
        
        db.alter_column("southtest_spam", 'name', models.CharField(max_length=255, null=True))
    
    def backwards(self):
        
        db.alter_column("southtest_spam", 'name', models.CharField(max_length=255))

    models = {
        "fakeapp.bug135": {
            'date':  ('models.DateTimeField', [], {'default': 'datetime.datetime(2009, 5, 6, 15, 33, 15, 780013)'}),
        }
    }

########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-

from django.db import models
from django.contrib.auth.models import User as UserAlias

def default_func():
    return "yays"

# An empty case.
class Other1(models.Model): pass

# Nastiness.
class HorribleModel(models.Model):
    "A model to test the edge cases of model parsing"
    
    ZERO, ONE = range(2)
    
    # First, some nice fields
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    
    # A ForeignKey, to a model above, and then below
    o1 = models.ForeignKey(Other1)
    o2 = models.ForeignKey('Other2')
    
    # Now to something outside
    user = models.ForeignKey(UserAlias, related_name="horribles")
    
    # Unicode!
    code = models.CharField(max_length=25, default="↑↑↓↓←→←→BA")
    
    # Odd defaults!
    class_attr = models.IntegerField(default=ZERO)
    func = models.CharField(max_length=25, default=default_func)
    
    # Time to get nasty. Define a non-field choices, and use it
    choices = [('hello', '1'), ('world', '2')]
    choiced = models.CharField(max_length=20, choices=choices)
    
    class Meta:
        db_table = "my_fave"
        verbose_name = "Dr. Strangelove," + \
                     """or how I learned to stop worrying
and love the bomb"""
    
    # Now spread over multiple lines
    multiline = \
              models.TextField(
        )
    
# Special case.
class Other2(models.Model):
    # Try loading a field without a newline after it (inspect hates this)
    close_but_no_cigar = models.PositiveIntegerField(primary_key=True)
########NEW FILE########
__FILENAME__ = inspector
import unittest

from south.tests import Monkeypatcher
from south.modelsinspector import *
from fakeapp.models import HorribleModel

class TestModelInspector(Monkeypatcher):

    """
    Tests if the various parts of the modelinspector work.
    """
    
    def test_get_value(self):
        
        # Let's start nicely.
        name = HorribleModel._meta.get_field_by_name("name")[0]
        slug = HorribleModel._meta.get_field_by_name("slug")[0]
        user = HorribleModel._meta.get_field_by_name("user")[0]
        
        # Simple int retrieval
        self.assertEqual(
            get_value(name, ["max_length", {}]),
            "255",
        )
        
        # Bool retrieval
        self.assertEqual(
            get_value(slug, ["unique", {}]),
            "True",
        )
        
        # String retrieval
        self.assertEqual(
            get_value(user, ["rel.related_name", {}]),
            "'horribles'",
        )
        
        # Default triggering
        self.assertEqual(
            get_value(slug, ["unique", {"default": False}]),
            "True",
        )
        self.assertRaises(
            IsDefault,
            get_value,
            slug,
            ["unique", {"default": True}],
        )
    
########NEW FILE########
__FILENAME__ = logger
import os
import unittest
import tempfile

from django.conf import settings
from django.db import connection, models

from south.db import db
from south.logger import close_logger

class TestLogger(unittest.TestCase):

    """
    Tests if the logging is working reasonably. Some tests ignored if you don't
    have write permission to the disk.
    """
    
    def setUp(self):
        db.debug = False
        self.test_path = tempfile.mkstemp(suffix=".south.log")[1]
    
    def test_db_execute_logging_nofile(self):
        "Does logging degrade nicely if SOUTH_DEBUG_ON not set?"
        settings.SOUTH_LOGGING_ON = False     # this needs to be set to False
                                              # to avoid issues where other tests
                                              # set this to True. settings is shared
                                              # between these tests.
        db.create_table("test9", [('email_confirmed', models.BooleanField(default=False))])
        
    def test_db_execute_logging_validfile(self):
        "Does logging work when passing in a valid file?"
        settings.SOUTH_LOGGING_ON = True
        settings.SOUTH_LOGGING_FILE = self.test_path
        # Check to see if we can make the logfile
        try:
            fh = open(self.test_path, "w")
        except IOError:
            # Permission was denied, ignore the test.
            return
        else:
            fh.close()
        # Do an action which logs
        db.create_table("test10", [('email_confirmed', models.BooleanField(default=False))])
        # Close the logged file
        close_logger()
        try:
            os.remove(self.test_path)
        except:
            # It's a tempfile, it's not vital we remove it.
            pass

    def test_db_execute_logging_missingfilename(self):
        "Does logging raise an error if there is a missing filename?"
        settings.SOUTH_LOGGING_ON = True
        settings.SOUTH_LOGGING_FILE = None
        self.assertRaises(
            IOError,
            db.create_table,
            "test11",
            [('email_confirmed', models.BooleanField(default=False))],
        )
        
        
########NEW FILE########
__FILENAME__ = logic
import unittest

from collections import deque
import datetime
import sys
import os
import StringIO

from south import exceptions
from south.migration import migrate_app
from south.migration.base import all_migrations, Migration, Migrations
from south.migration.utils import depends, dfs, flatten, get_app_label
from south.models import MigrationHistory
from south.tests import Monkeypatcher
from south.db import db



class TestBrokenMigration(Monkeypatcher):
    installed_apps = ["fakeapp", "otherfakeapp", "brokenapp"]

    def test_broken_dependencies(self):
        self.assertRaises(
            exceptions.DependsOnUnmigratedApplication,
            Migrations.calculate_dependencies,
            force=True,
        )
        #depends_on_unknown = self.brokenapp['0002_depends_on_unknown']
        #self.assertRaises(exceptions.DependsOnUnknownMigration,
        #                  depends_on_unknown.dependencies)
        #depends_on_higher = self.brokenapp['0003_depends_on_higher']
        #self.assertRaises(exceptions.DependsOnHigherMigration,
        #                  depends_on_higher.dependencies)


class TestMigration(Monkeypatcher):
    installed_apps = ["fakeapp", "otherfakeapp"]

    def setUp(self):
        super(TestMigration, self).setUp()
        self.fakeapp = Migrations('fakeapp')
        self.otherfakeapp = Migrations('otherfakeapp')
        Migrations.calculate_dependencies(force=True)

    def test_str(self):
        migrations = [str(m) for m in self.fakeapp]
        self.assertEqual(['fakeapp:0001_spam',
                          'fakeapp:0002_eggs',
                          'fakeapp:0003_alter_spam'],
                         migrations)
    
    def test_repr(self):
        migrations = [repr(m) for m in self.fakeapp]
        self.assertEqual(['<Migration: fakeapp:0001_spam>',
                          '<Migration: fakeapp:0002_eggs>',
                          '<Migration: fakeapp:0003_alter_spam>'],
                         migrations)

    def test_app_label(self):
        self.assertEqual(['fakeapp', 'fakeapp', 'fakeapp'],
                         [m.app_label() for m in self.fakeapp])
                         
    def test_name(self):
        self.assertEqual(['0001_spam', '0002_eggs', '0003_alter_spam'],
                         [m.name() for m in self.fakeapp])

    def test_full_name(self):
        self.assertEqual(['fakeapp.migrations.0001_spam',
                          'fakeapp.migrations.0002_eggs',
                          'fakeapp.migrations.0003_alter_spam'],
                         [m.full_name() for m in self.fakeapp])
    
    def test_migration(self):
        # Can't use vanilla import, modules beginning with numbers aren't in grammar
        M1 = __import__("fakeapp.migrations.0001_spam", {}, {}, ['Migration']).Migration
        M2 = __import__("fakeapp.migrations.0002_eggs", {}, {}, ['Migration']).Migration
        M3 = __import__("fakeapp.migrations.0003_alter_spam", {}, {}, ['Migration']).Migration
        self.assertEqual([M1, M2, M3],
                         [m.migration().Migration for m in self.fakeapp])
        self.assertRaises(exceptions.UnknownMigration,
                          self.fakeapp['9999_unknown'].migration)

    def test_previous(self):
        self.assertEqual([None,
                          self.fakeapp['0001_spam'],
                          self.fakeapp['0002_eggs']],
                         [m.previous() for m in self.fakeapp])

    def test_dependencies(self):
        "Test that the dependency detection works."
        self.assertEqual([
                set([]),
                set([self.fakeapp['0001_spam']]),
                set([self.fakeapp['0002_eggs']])
            ],
            [m.dependencies for m in self.fakeapp],
        )
        self.assertEqual([
                set([self.fakeapp['0001_spam']]),
                set([self.otherfakeapp['0001_first']]),
                set([
                    self.otherfakeapp['0002_second'],
                    self.fakeapp['0003_alter_spam'],
                ])
            ],
            [m.dependencies for m in self.otherfakeapp],
        )

    def test_forwards_plan(self):
        self.assertEqual([
                [self.fakeapp['0001_spam']],
                [
                    self.fakeapp['0001_spam'],
                    self.fakeapp['0002_eggs']
                ],
                [
                    self.fakeapp['0001_spam'],
                    self.fakeapp['0002_eggs'],
                    self.fakeapp['0003_alter_spam'],
                ]
            ],
            [m.forwards_plan() for m in self.fakeapp],
        )
        self.assertEqual([
                [
                    self.fakeapp['0001_spam'],
                    self.otherfakeapp['0001_first']
                ],
                [
                    self.fakeapp['0001_spam'],
                    self.otherfakeapp['0001_first'],
                    self.otherfakeapp['0002_second']
                ],
                [
                    self.fakeapp['0001_spam'],
                    self.otherfakeapp['0001_first'],
                    self.otherfakeapp['0002_second'],
                    self.fakeapp['0002_eggs'],
                    self.fakeapp['0003_alter_spam'],
                    self.otherfakeapp['0003_third'],
                ]
            ],
            [m.forwards_plan() for m in self.otherfakeapp],
        )

    def test_is_before(self):
        F1 = self.fakeapp['0001_spam']
        F2 = self.fakeapp['0002_eggs']
        F3 = self.fakeapp['0003_alter_spam']
        O1 = self.otherfakeapp['0001_first']
        O2 = self.otherfakeapp['0002_second']
        O3 = self.otherfakeapp['0003_third']
        self.assertTrue(F1.is_before(F2))
        self.assertTrue(F1.is_before(F3))
        self.assertTrue(F2.is_before(F3))
        self.assertEqual(O3.is_before(O1), False)
        self.assertEqual(O3.is_before(O2), False)
        self.assertEqual(O2.is_before(O2), False)
        self.assertEqual(O2.is_before(O1), False)
        self.assertEqual(F2.is_before(O1), None)
        self.assertEqual(F2.is_before(O2), None)
        self.assertEqual(F2.is_before(O3), None)


class TestMigrationDependencies(Monkeypatcher):
    installed_apps = ['deps_a', 'deps_b', 'deps_c']

    def setUp(self):
        super(TestMigrationDependencies, self).setUp()
        self.deps_a = Migrations('deps_a')
        self.deps_b = Migrations('deps_b')
        self.deps_c = Migrations('deps_c')
        Migrations.calculate_dependencies(force=True)

    def test_dependencies(self):
        self.assertEqual(
            [
                set([]),
                set([self.deps_a['0001_a']]),
                set([self.deps_a['0002_a']]),
                set([
                    self.deps_a['0003_a'],
                    self.deps_b['0003_b'],
                ]),
                set([self.deps_a['0004_a']]),
            ],
            [m.dependencies for m in self.deps_a],
        )
        self.assertEqual(
            [
                set([]),
                set([
                    self.deps_b['0001_b'],
                    self.deps_a['0002_a']
                ]),
                set([
                    self.deps_b['0002_b'],
                    self.deps_a['0003_a']
                ]),
                set([self.deps_b['0003_b']]),
                set([self.deps_b['0004_b']]),
            ],
            [m.dependencies for m in self.deps_b],
        )
        self.assertEqual(
            [
                set([]),
                set([self.deps_c['0001_c']]),
                set([self.deps_c['0002_c']]),
                set([self.deps_c['0003_c']]),
                set([
                    self.deps_c['0004_c'],
                    self.deps_a['0002_a']
                ]),
            ],
            [m.dependencies for m in self.deps_c],
        )

    def test_dependents(self):
        self.assertEqual([set([self.deps_a['0002_a']]),
                          set([self.deps_c['0005_c'],
                                 self.deps_b['0002_b'],
                                 self.deps_a['0003_a']]),
                          set([self.deps_b['0003_b'],
                                 self.deps_a['0004_a']]),
                          set([self.deps_a['0005_a']]),
                          set([])],
                         [m.dependents for m in self.deps_a])
        self.assertEqual([set([self.deps_b['0002_b']]),
                          set([self.deps_b['0003_b']]),
                          set([self.deps_b['0004_b'],
                                 self.deps_a['0004_a']]),
                          set([self.deps_b['0005_b']]),
                          set([])],
                         [m.dependents for m in self.deps_b])
        self.assertEqual([set([self.deps_c['0002_c']]),
                          set([self.deps_c['0003_c']]),
                          set([self.deps_c['0004_c']]),
                          set([self.deps_c['0005_c']]),
                          set([])],
                         [m.dependents for m in self.deps_c])

    def test_forwards_plan(self):
        self.assertEqual([[self.deps_a['0001_a']],
                          [self.deps_a['0001_a'],
                           self.deps_a['0002_a']],
                          [self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_a['0003_a']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b'],
                           self.deps_a['0003_a'],
                           self.deps_b['0003_b'],
                           self.deps_a['0004_a']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b'],
                           self.deps_a['0003_a'],
                           self.deps_b['0003_b'],
                           self.deps_a['0004_a'],
                           self.deps_a['0005_a']]],
                         [m.forwards_plan() for m in self.deps_a])
        self.assertEqual([[self.deps_b['0001_b']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b'],
                           self.deps_a['0003_a'],
                           self.deps_b['0003_b']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b'],
                           self.deps_a['0003_a'],
                           self.deps_b['0003_b'],
                           self.deps_b['0004_b']],
                          [self.deps_b['0001_b'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_b['0002_b'],
                           self.deps_a['0003_a'],
                           self.deps_b['0003_b'],
                           self.deps_b['0004_b'],
                           self.deps_b['0005_b']]],
                         [m.forwards_plan() for m in self.deps_b])
        self.assertEqual([[self.deps_c['0001_c']],
                          [self.deps_c['0001_c'],
                           self.deps_c['0002_c']],
                          [self.deps_c['0001_c'],
                           self.deps_c['0002_c'],
                           self.deps_c['0003_c']],
                          [self.deps_c['0001_c'],
                           self.deps_c['0002_c'],
                           self.deps_c['0003_c'],
                           self.deps_c['0004_c']],
                          [self.deps_c['0001_c'],
                           self.deps_c['0002_c'],
                           self.deps_c['0003_c'],
                           self.deps_c['0004_c'],
                           self.deps_a['0001_a'],
                           self.deps_a['0002_a'],
                           self.deps_c['0005_c']]],
                         [m.forwards_plan() for m in self.deps_c])

    def test_backwards_plan(self):
        self.assertEqual([
            [
                self.deps_c['0005_c'],
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
                self.deps_b['0002_b'],
                self.deps_a['0003_a'],
                self.deps_a['0002_a'],
                self.deps_a['0001_a'],
            ],
            [
                self.deps_c['0005_c'],
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
                self.deps_b['0002_b'],
                self.deps_a['0003_a'],
                self.deps_a['0002_a'],
            ],
            [
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
                self.deps_a['0003_a'],
            ],
            [
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
            ],
            [
                self.deps_a['0005_a'],
            ]
        ], [m.backwards_plan() for m in self.deps_a])
        self.assertEqual([
            [
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
                self.deps_b['0002_b'],
                self.deps_b['0001_b'],
            ],
            [
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
                self.deps_b['0002_b'],
            ],
            [
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
                self.deps_a['0005_a'],
                self.deps_a['0004_a'],
                self.deps_b['0003_b'],
            ],
            [
                self.deps_b['0005_b'],
                self.deps_b['0004_b'],
            ],
            [
                self.deps_b['0005_b'],
            ],
        ], [m.backwards_plan() for m in self.deps_b])
        self.assertEqual([
            [
                self.deps_c['0005_c'],
                self.deps_c['0004_c'],
                self.deps_c['0003_c'],
                self.deps_c['0002_c'],
                self.deps_c['0001_c'],
            ],
            [
                self.deps_c['0005_c'],
                self.deps_c['0004_c'],
                self.deps_c['0003_c'],
                self.deps_c['0002_c'],
            ],
            [
                self.deps_c['0005_c'],
                self.deps_c['0004_c'],
                self.deps_c['0003_c'],
            ],
            [
                self.deps_c['0005_c'],
                self.deps_c['0004_c'],
            ],
            [self.deps_c['0005_c']]
        ],  [m.backwards_plan() for m in self.deps_c])


class TestCircularDependencies(Monkeypatcher):
    installed_apps = ["circular_a", "circular_b"]

    def test_plans(self):
        Migrations.calculate_dependencies(force=True)
        circular_a = Migrations('circular_a')
        circular_b = Migrations('circular_b')
        self.assertRaises(
            exceptions.CircularDependency,
            circular_a[-1].forwards_plan,
        )
        self.assertRaises(
            exceptions.CircularDependency,
            circular_b[-1].forwards_plan,
        )
        self.assertRaises(
            exceptions.CircularDependency,
            circular_a[-1].backwards_plan,
        )
        self.assertRaises(
            exceptions.CircularDependency,
            circular_b[-1].backwards_plan,
        )


class TestMigrations(Monkeypatcher):
    installed_apps = ["fakeapp", "otherfakeapp"]

    def test_all(self):
        
        M1 = Migrations(__import__("fakeapp", {}, {}, ['']))
        M2 = Migrations(__import__("otherfakeapp", {}, {}, ['']))
        
        self.assertEqual(
            [M1, M2],
            list(all_migrations()),
        )

    def test(self):
        
        M1 = Migrations(__import__("fakeapp", {}, {}, ['']))
        
        self.assertEqual(M1, Migrations("fakeapp"))
        self.assertEqual(M1, Migrations(self.create_fake_app("fakeapp")))

    def test_application(self):
        fakeapp = Migrations("fakeapp")
        application = __import__("fakeapp", {}, {}, [''])
        self.assertEqual(application, fakeapp.application)

    def test_migration(self):
        # Can't use vanilla import, modules beginning with numbers aren't in grammar
        M1 = __import__("fakeapp.migrations.0001_spam", {}, {}, ['Migration']).Migration
        M2 = __import__("fakeapp.migrations.0002_eggs", {}, {}, ['Migration']).Migration
        migration = Migrations('fakeapp')
        self.assertEqual(M1, migration['0001_spam'].migration().Migration)
        self.assertEqual(M2, migration['0002_eggs'].migration().Migration)
        self.assertRaises(exceptions.UnknownMigration,
                          migration['0001_jam'].migration)

    def test_guess_migration(self):
        # Can't use vanilla import, modules beginning with numbers aren't in grammar
        M1 = __import__("fakeapp.migrations.0001_spam", {}, {}, ['Migration']).Migration
        M2 = __import__("fakeapp.migrations.0002_eggs", {}, {}, ['Migration']).Migration
        migration = Migrations('fakeapp')
        self.assertEqual(M1, migration.guess_migration("0001_spam").migration().Migration)
        self.assertEqual(M1, migration.guess_migration("0001_spa").migration().Migration)
        self.assertEqual(M1, migration.guess_migration("0001_sp").migration().Migration)
        self.assertEqual(M1, migration.guess_migration("0001_s").migration().Migration)
        self.assertEqual(M1, migration.guess_migration("0001_").migration().Migration)
        self.assertEqual(M1, migration.guess_migration("0001").migration().Migration)
        self.assertRaises(exceptions.UnknownMigration,
                          migration.guess_migration, "0001-spam")
        self.assertRaises(exceptions.MultiplePrefixMatches,
                          migration.guess_migration, "000")
        self.assertRaises(exceptions.MultiplePrefixMatches,
                          migration.guess_migration, "")
        self.assertRaises(exceptions.UnknownMigration,
                          migration.guess_migration, "0001_spams")
        self.assertRaises(exceptions.UnknownMigration,
                          migration.guess_migration, "0001_jam")

    def test_app_label(self):
        names = ['fakeapp', 'otherfakeapp']
        self.assertEqual(names,
                         [Migrations(n).app_label() for n in names])
    
    def test_full_name(self):
        names = ['fakeapp', 'otherfakeapp']
        self.assertEqual([n + '.migrations' for n in names],
                         [Migrations(n).full_name() for n in names])


class TestMigrationLogic(Monkeypatcher):

    """
    Tests if the various logic functions in migration actually work.
    """
    
    installed_apps = ["fakeapp", "otherfakeapp"]

    def assertListEqual(self, list1, list2):
        list1 = list(list1)
        list2 = list(list2)
        list1.sort()
        list2.sort()
        return self.assertEqual(list1, list2)

    def test_find_ghost_migrations(self):
        pass
    
    def test_apply_migrations(self):
        MigrationHistory.objects.all().delete()
        migrations = Migrations("fakeapp")
        
        # We should start with no migrations
        self.assertEqual(list(MigrationHistory.objects.all()), [])
        
        # Apply them normally
        migrate_app(migrations, target_name=None, fake=False,
                    load_initial_data=True)
        
        # We should finish with all migrations
        self.assertListEqual(
            ((u"fakeapp", u"0001_spam"),
             (u"fakeapp", u"0002_eggs"),
             (u"fakeapp", u"0003_alter_spam"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # Now roll them backwards
        migrate_app(migrations, target_name="zero", fake=False)
        
        # Finish with none
        self.assertEqual(list(MigrationHistory.objects.all()), [])
    
    
    def test_migration_merge_forwards(self):
        MigrationHistory.objects.all().delete()
        migrations = Migrations("fakeapp")
        
        # We should start with no migrations
        self.assertEqual(list(MigrationHistory.objects.all()), [])
        
        # Insert one in the wrong order
        MigrationHistory.objects.create(app_name = "fakeapp",
                                        migration = "0002_eggs",
                                        applied = datetime.datetime.now())
        
        # Did it go in?
        self.assertListEqual(
            ((u"fakeapp", u"0002_eggs"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # Apply them normally
        self.assertRaises(exceptions.InconsistentMigrationHistory,
                          migrate_app,
                          migrations, target_name=None, fake=False)
        self.assertRaises(exceptions.InconsistentMigrationHistory,
                          migrate_app,
                          migrations, target_name='zero', fake=False)
        try:
            migrate_app(migrations, target_name=None, fake=False)
        except exceptions.InconsistentMigrationHistory, e:
            self.assertEqual(
                [
                    (
                        migrations['0002_eggs'],
                        migrations['0001_spam'],
                    )
                ],
                e.problems,
            )
        try:
            migrate_app(migrations, target_name="zero", fake=False)
        except exceptions.InconsistentMigrationHistory, e:
            self.assertEqual(
                [
                    (
                        migrations['0002_eggs'],
                        migrations['0001_spam'],
                    )
                ],
                e.problems,
            )
        
        # Nothing should have changed (no merge mode!)
        self.assertListEqual(
            ((u"fakeapp", u"0002_eggs"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # Apply with merge
        migrate_app(migrations, target_name=None, merge=True, fake=False)
        
        # We should finish with all migrations
        self.assertListEqual(
            ((u"fakeapp", u"0001_spam"),
             (u"fakeapp", u"0002_eggs"),
             (u"fakeapp", u"0003_alter_spam"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # Now roll them backwards
        migrate_app(migrations, target_name="0002", fake=False)
        migrate_app(migrations, target_name="0001", fake=True)
        migrate_app(migrations, target_name="zero", fake=False)
        
        # Finish with none
        self.assertEqual(list(MigrationHistory.objects.all()), [])
    
    def test_alter_column_null(self):
        
        def null_ok():
            from django.db import connection, transaction
            # the DBAPI introspection module fails on postgres NULLs.
            cursor = connection.cursor()
        
            # SQLite has weird now()
            if db.backend_name == "sqlite3":
                now_func = "DATETIME('NOW')"
            else:
                now_func = "NOW()"
            
            try:
                cursor.execute("INSERT INTO southtest_spam (id, weight, expires, name) VALUES (100, 10.1, %s, NULL);" % now_func)
            except:
                transaction.rollback()
                return False
            else:
                cursor.execute("DELETE FROM southtest_spam")
                transaction.commit()
                return True

        MigrationHistory.objects.all().delete()
        migrations = Migrations("fakeapp")
        
        # by default name is NOT NULL
        migrate_app(migrations, target_name="0002", fake=False)
        self.failIf(null_ok())
        self.assertListEqual(
            ((u"fakeapp", u"0001_spam"),
             (u"fakeapp", u"0002_eggs"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # after 0003, it should be NULL
        migrate_app(migrations, target_name="0003", fake=False)
        self.assert_(null_ok())
        self.assertListEqual(
            ((u"fakeapp", u"0001_spam"),
             (u"fakeapp", u"0002_eggs"),
             (u"fakeapp", u"0003_alter_spam"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )

        # make sure it is NOT NULL again
        migrate_app(migrations, target_name="0002", fake=False)
        self.failIf(null_ok(), 'name not null after migration')
        self.assertListEqual(
            ((u"fakeapp", u"0001_spam"),
             (u"fakeapp", u"0002_eggs"),),
            MigrationHistory.objects.values_list("app_name", "migration"),
        )
        
        # finish with no migrations, otherwise other tests fail...
        migrate_app(migrations, target_name="zero", fake=False)
        self.assertEqual(list(MigrationHistory.objects.all()), [])
    
    def test_dependencies(self):
        
        fakeapp = Migrations("fakeapp")
        otherfakeapp = Migrations("otherfakeapp")
        
        # Test a simple path
        self.assertEqual([fakeapp['0001_spam'],
                          fakeapp['0002_eggs'],
                          fakeapp['0003_alter_spam']],
                         fakeapp['0003_alter_spam'].forwards_plan())
        
        # And a complex one.
        self.assertEqual(
            [
                fakeapp['0001_spam'],
                otherfakeapp['0001_first'],
                otherfakeapp['0002_second'],
                fakeapp['0002_eggs'],
                fakeapp['0003_alter_spam'],
                otherfakeapp['0003_third']
            ],
            otherfakeapp['0003_third'].forwards_plan(),
        )


class TestMigrationUtils(Monkeypatcher):
    installed_apps = ["fakeapp", "otherfakeapp"]

    def test_get_app_label(self):
        self.assertEqual(
            "southtest",
            get_app_label(self.create_fake_app("southtest.models")),
        )
        self.assertEqual(
            "baz",
            get_app_label(self.create_fake_app("foo.bar.baz.models")),
        )

class TestUtils(unittest.TestCase):

    def test_flatten(self):
        self.assertEqual([], list(flatten(iter([]))))
        self.assertEqual([], list(flatten(iter([iter([]), ]))))
        self.assertEqual([1], list(flatten(iter([1]))))
        self.assertEqual([1, 2], list(flatten(iter([1, 2]))))
        self.assertEqual([1, 2], list(flatten(iter([iter([1]), 2]))))
        self.assertEqual([1, 2], list(flatten(iter([iter([1, 2])]))))
        self.assertEqual([1, 2, 3], list(flatten(iter([iter([1, 2]), 3]))))
        self.assertEqual([1, 2, 3],
                         list(flatten(iter([iter([1]), iter([2]), 3]))))
        self.assertEqual([1, 2, 3],
                         list(flatten([[1], [2], 3])))

    def test_depends(self):
        graph = {'A1': []}
        self.assertEqual(['A1'],
                         depends('A1', lambda n: graph[n]))
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2']}
        self.assertEqual(['A1', 'A2', 'A3'],
                         depends('A3', lambda n: graph[n]))
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'A1']}
        self.assertEqual(['A1', 'A2', 'A3'],
                         depends('A3', lambda n: graph[n]))
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'A1', 'B1'],
                 'B1': []}
        self.assertEqual(
            ['B1', 'A1', 'A2', 'A3'],
            depends('A3', lambda n: graph[n]),
        )
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'A1', 'B2'],
                 'B1': [],
                 'B2': ['B1']}
        self.assertEqual(
            ['B1', 'B2', 'A1', 'A2', 'A3'],
            depends('A3', lambda n: graph[n]),
        )
        graph = {'A1': [],
                 'A2': ['A1', 'B1'],
                 'A3': ['A2'],
                 'B1': ['A1']}
        self.assertEqual(['A1', 'B1', 'A2', 'A3'],
                         depends('A3', lambda n: graph[n]))
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'A1', 'B2'],
                 'B1': [],
                 'B2': ['B1', 'C1'],
                 'C1': ['B1']}
        self.assertEqual(
            ['B1', 'C1', 'B2', 'A1', 'A2', 'A3'],
            depends('A3', lambda n: graph[n]),
        )
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'B2', 'A1', 'C1'],
                 'B1': ['A1'],
                 'B2': ['B1', 'C2', 'A1'],
                 'C1': ['B1'],
                 'C2': ['C1', 'A1'],
                 'C3': ['C2']}
        self.assertEqual(
            ['A1', 'B1', 'C1', 'C2', 'B2', 'A2', 'A3'],
            depends('A3', lambda n: graph[n]),
        )

    def assertCircularDependency(self, trace, target, graph):
        "Custom assertion that checks a circular dependency is detected correctly."
        self.assertRaises(
            exceptions.CircularDependency,
            depends,
            target,
            lambda n: graph[n],
        )
        try:
            depends(target, lambda n: graph[n])
        except exceptions.CircularDependency, e:
            self.assertEqual(trace, e.trace)

    def test_depends_cycle(self):
        graph = {'A1': ['A1']}
        self.assertCircularDependency(
            ['A1', 'A1'],
            'A1',
            graph,
        )
        graph = {'A1': [],
                 'A2': ['A1', 'A2'],
                 'A3': ['A2']}
        self.assertCircularDependency(
            ['A1', 'A2', 'A1'],
            'A3',
            graph,
        )
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'A3'],
                 'A4': ['A3']}
        self.assertCircularDependency(
            ['A3', 'A2', 'A1', 'A3'],
            'A4',
            graph,
        )
        graph = {'A1': ['B1'],
                 'B1': ['A1']}
        self.assertCircularDependency(
            ['A1', 'B1', 'A1'],
            'A1',
            graph,
        )
        graph = {'A1': [],
                 'A2': ['A1', 'B2'],
                 'A3': ['A2'],
                 'B1': [],
                 'B2': ['B1', 'A2'],
                 'B3': ['B2']}
        self.assertCircularDependency(
            ['A2', 'A1', 'B2', 'A2'],
            'A3',
            graph,
        )
        graph = {'A1': [],
                 'A2': ['A1', 'B3'],
                 'A3': ['A2'],
                 'B1': [],
                 'B2': ['B1', 'A2'],
                 'B3': ['B2']}
        self.assertCircularDependency(
            ['B2', 'A2', 'A1', 'B3', 'B2'],
            'A3',
            graph,
        )
        graph = {'A1': [],
                 'A2': ['A1'],
                 'A3': ['A2', 'B2'],
                 'A4': ['A3'],
                 'B1': ['A3'],
                 'B2': ['B1']}
        self.assertCircularDependency(
            ['A1', 'B2', 'B1', 'A3', 'A2', 'A1'],
            'A4',
            graph,
        )


########NEW FILE########
__FILENAME__ = 0001_first
from south.db import db
from django.db import models

class Migration:
    
    depends_on = (
        ("fakeapp", "0001_spam"),
    )
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0002_second
from south.db import db
from django.db import models

class Migration:
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass


########NEW FILE########
__FILENAME__ = 0003_third
from south.db import db
from django.db import models

class Migration:
    
    depends_on = (
        ("fakeapp", "0003_alter_spam"),
    )
    
    def forwards(self):
        pass
    
    def backwards(self):
        pass

########NEW FILE########
__FILENAME__ = models
# This file left intentionally blank.
########NEW FILE########
__FILENAME__ = utils
"""
Generally helpful utility functions.
"""


def _ask_for_it_by_name(name):
    "Returns an object referenced by absolute path."
    bits = name.split(".")

    ## what if there is no absolute reference?
    if len(bits)>1:
        modulename = ".".join(bits[:-1])
    else:
        modulename=bits[0]
        
    module = __import__(modulename, {}, {}, bits[-1])
    
    if len(bits) == 1:
        return module
    else:
        return getattr(module, bits[-1])


def ask_for_it_by_name(name): 
    "Returns an object referenced by absolute path. (Memoised outer wrapper)"
    if name not in ask_for_it_by_name.cache: 
        ask_for_it_by_name.cache[name] = _ask_for_it_by_name(name) 
    return ask_for_it_by_name.cache[name] 
ask_for_it_by_name.cache = {} 


def get_attribute(item, attribute):
    """
    Like getattr, but recursive (i.e. you can ask for 'foo.bar.yay'.)
    """
    value = item
    for part in attribute.split("."):
        value = getattr(value, part)
    return value

def auto_through(field):
    "Returns if the M2M class passed in has an autogenerated through table or not."
    return (
        # Django 1.0/1.1
        (not field.rel.through)
        or
        # Django 1.2+
        getattr(getattr(field.rel.through, "_meta", None), "auto_created", False)
    )

def auto_model(model):
    "Returns if the given model was automatically generated."
    return getattr(model._meta, "auto_created", False)

def memoize(function):
    "Standard memoization decorator."
    name = function.__name__
    _name = '_' + name
    
    def method(self):
        if not hasattr(self, _name):
            value = function(self)
            setattr(self, _name, value)
        return getattr(self, _name)
    
    def invalidate():
        if hasattr(method, _name):
            delattr(method, _name)
        
    method.__name__ = function.__name__
    method.__doc__ = function.__doc__
    method._invalidate = invalidate
    return method

########NEW FILE########
__FILENAME__ = v2
"""
API versioning file; we can tell what kind of migrations things are
by what class they inherit from (if none, it's a v1).
"""

from south.utils import ask_for_it_by_name

class BaseMigration(object):
    
    def gf(self, field_name):
        "Gets a field by absolute reference."
        return ask_for_it_by_name(field_name)

class SchemaMigration(BaseMigration):
    pass

class DataMigration(BaseMigration):
    # Data migrations shouldn't be dry-run
    no_dry_run = True

########NEW FILE########
