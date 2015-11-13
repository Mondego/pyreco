__FILENAME__ = dashboard
"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'scripts.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """
    
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        
        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('AppList: Applications'),
            collapsible=True,
            column=1,
            css_classes=('collapse closed',),
            exclude=('django.contrib.*',),
        ))
        
        # append an app list module for "Administration"
        self.children.append(modules.ModelList(
            _('ModelList: Administration'),
            column=1,
            collapsible=False,
            models=('django.contrib.*',),
        ))
        
        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Media Management'),
            column=2,
            children=[
                {
                    'title': _('FileBrowser'),
                    'url': '/admin/filebrowser/browse/',
                    'external': False,
                },
            ]
        ))
        
        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=5,
            collapsible=False,
            column=3,
        ))



########NEW FILE########
__FILENAME__ = admin
# -*- coding: UTF-8 -*-
from django.db import models
from django.contrib import admin

from .models import Post, Category
from .widgets import EpicEditorWidget

class PostAdmin(admin.ModelAdmin):
    list_display        = ('title', 'slug', 'author', 'status', 'created_at', 'publish', )
    search_fields       = ('title', 'body', )
    #raw_id_fields       = ('author',)
    #list_filter         = ('category',)
    formfield_overrides = {
        models.TextField: {'widget': EpicEditorWidget},
    }

class CategoryAdmin(admin.ModelAdmin):
    list_display        = ('title', 'slug', )
    search_fields       = ('title', 'slug', )

admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.conf import settings
from django.core.urlresolvers import reverse

from .models import Post

class LatestDPressPostFeed(Feed):
    title = getattr(settings, 'DPRESS_TITLE', '')
    description = getattr(settings, 'DPRESS_DESCN', '')
    description_template = 'dpress/feeds/description.html'

    def items(self):
        return Post.objects.filter(status=2).order_by("-publish")[:10]

    def item_pubdate(self, item):
        return item.publish

    def link(self):
        return reverse('dpress_index')

########NEW FILE########
__FILENAME__ = helper
# -*- coding: UTF-8 -*-
import datetime
import time

from django.template import Context, Template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

import markdown

def tl_markdown(md, no_p=False):
    ret = markdown.markdown(force_unicode(md), 
        ['fenced_code', 'codehilite'], safe_mode=False) #'nl2br', 
    return mark_safe(ret)

def archive_month_filter(year, month, queryset, date_field):
    try:
        tt = time.strptime("%s-%s" % (year, month), '%s-%s' % ('%Y', '%m'))
        date = datetime.date(*tt[:3])
    except ValueError:
        raise Http404

    first_day = date.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1)
    lookup_kwargs = {
        '%s__gte' % date_field: first_day,
        '%s__lt' % date_field: last_day,
    }
    return queryset.filter(**lookup_kwargs), {'archive_month': date}

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Post'
        db.create_table('dpress_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(related_name='added_posts', to=orm['auth.User'])),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('publish', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('dpress', ['Post'])


    def backwards(self, orm):
        # Deleting model 'Post'
        db.delete_table('dpress_post')


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
        'dpress.post': {
            'Meta': {'ordering': "('-publish',)", 'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'added_posts'", 'to': "orm['auth.User']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'publish': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['dpress']
########NEW FILE########
__FILENAME__ = 0002_auto__add_category__add_field_post_category
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table('dpress_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('dpress', ['Category'])

        # Adding field 'Post.category'
        db.add_column('dpress_post', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='posts', null=True, blank=True, to=orm['dpress.Category']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table('dpress_category')

        # Deleting field 'Post.category'
        db.delete_column('dpress_post', 'category_id')


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
        'dpress.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'dpress.post': {
            'Meta': {'ordering': "('-publish',)", 'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'added_posts'", 'to': "orm['auth.User']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'posts'", 'null': 'True', 'blank': 'True', 'to': "orm['dpress.Category']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'publish': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['dpress']
########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-
from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from taggit.managers import TaggableManager

class Category(models.Model):
    title           = models.CharField(_('title'), max_length=200)
    slug            = models.SlugField(_('slug'))

    class Meta:
        verbose_name        = _('category')
        verbose_name_plural = _('categorys')
        ordering            = ('title',)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return ('dpress_category', None, {
            'category': self.slug
    })
    get_absolute_url = models.permalink(get_absolute_url)

class Post(models.Model):
    """Post model."""
    STATUS_CHOICES = (
        (1, _('Draft')),
        (2, _('Public')),
    )
    title           = models.CharField(_('title'), max_length=200)
    slug            = models.SlugField(_('slug'))
    author          = models.ForeignKey(User, related_name="added_posts")
    body            = models.TextField(_('body'))
    status          = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=1)
    publish         = models.DateTimeField(_('publish'), default=datetime.now)
    created_at      = models.DateTimeField(_('created at'), default=datetime.now)
    updated_at      = models.DateTimeField(_('updated at'), auto_now=True)
    category        = models.ForeignKey(Category, related_name="posts", \
                        blank=True, null=True, default=None, on_delete=models.SET_NULL)
    tags            = TaggableManager(blank=True)
    
    class Meta:
        verbose_name        = _('post')
        verbose_name_plural = _('posts')
        ordering            = ('-publish',)
        get_latest_by       = 'publish'

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return ('dpress_post', None, {
            'year': self.publish.year,
            'month': "%02d" % self.publish.month,
            'slug': self.slug
    })
    get_absolute_url = models.permalink(get_absolute_url)

########NEW FILE########
__FILENAME__ = dpress_tags
import re

from django.template import Library
from django.utils.safestring import mark_safe

from dpress.helper import tl_markdown
from dpress.models import Post
from dpress.models import Category

register = Library()

@register.filter
def md(_md):
    return tl_markdown(_md)

@register.inclusion_tag("dpress/tags/dummy.html")
def last_post(template='dpress/widgets/lastposts.html'):
    lastposts = Post.objects.filter(status=2).select_related(depth=1).order_by("-publish")
    return {
            "template": template,
            'lastposts': lastposts[:5]
    }

@register.inclusion_tag("dpress/tags/dummy.html")
def month_links(template="dpress/widgets/monthlinks.html"):
    return {
            "template": template,
            'dates': Post.objects.filter(status=2).dates('publish', 'month')[:12],
            }

@register.inclusion_tag("dpress/tags/dummy.html")
def categorys(template="dpress/widgets/categorys.html"):
    return {
            "template": template,
            'categorys': Category.objects.order_by("title"),
            }

########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF-8 -*-
from django.test import TestCase
from django.core.urlresolvers import reverse

class ViewsBaseCase(TestCase):

    fixtures = ['test_dpress_users.json', 
            'test_dpress_posts.json']

class ViewsSimpleTest(ViewsBaseCase):

    def test_index(self):
        resp = self.client.get(reverse('dpress_index'))
        self.assertEqual(resp.status_code, 200)

    def test_archive(self):
        resp = self.client.get(reverse('dpress_month_archive', args=("2012", "8", )))
        self.assertEqual(resp.status_code, 200)

    def test_category(self):
        resp = self.client.get(reverse('dpress_category', args=("default", )))
        self.assertEqual(resp.status_code, 200)

    def test_tag(self):
        resp = self.client.get(reverse('dpress_tag', args=("testtag", )))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('dpress_tag', args=("notag", )))
        self.assertEqual(resp.status_code, 404)

    def test_post(self):
        resp = self.client.get(reverse('dpress_post', args=("2012", "08", "dpress")))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('dpress_post', args=("2012", "08", "noslug")))
        self.assertEqual(resp.status_code, 404)

    def test_feed(self):
        resp = self.client.get(reverse('dpress_feeds'))
        self.assertEqual(resp.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from . import views
from .feeds import LatestDPressPostFeed

feeds = {
    'latest': LatestDPressPostFeed,
}

urlpatterns = patterns('',
    url(r'^$', views.index, name='dpress_index'),
    url(r'^a/(?P<year>\d{4})/(?P<month>\d{1,2})/$', views.index, name='dpress_month_archive'),
    url(r'^c/(?P<category>[-\w]+)/$', views.index, name='dpress_category'),
    url(r'^tags/(?P<tag>[-\w]+)/$', views.index, name='dpress_tag'),
    url(r'^post/(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[-\w]+)/$', 
        views.post, name='dpress_post'),
    url(r'^latest/feed/$', LatestDPressPostFeed(), name="dpress_feeds"),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: UTF-8 -*-
from django.shortcuts import render, get_object_or_404

from taggit.models import Tag

from .models import Post
from .helper import archive_month_filter

def index(request, username=None, tag=None, year=None, month=None,
        category=None, template_name="dpress/index.html"):
    posts = Post.objects.filter(status=2)
    ctx = {}
    if tag:
        ctx['tag'] = get_object_or_404(Tag, name=tag)
        posts = posts.filter(tags__name__in=[tag])
    if year and month:
        posts, t_context = archive_month_filter(year, month, posts, 'publish')
        ctx.update(t_context)

    if category:
        posts = posts.filter(category__slug=category)
        
    if username:
        posts = posts.filter(author__username=username)
    posts = posts.order_by("-publish")
    ctx['posts'] = posts
    return render(request, template_name, ctx)

def post(request, year, month, slug,
         template_name="dpress/post.html"):
    post = get_object_or_404(Post, slug=slug, publish__year=int(year), 
            publish__month=int(month), status=2)
    ctx = {}
    ctx['post'] = post
    return render(request, template_name, ctx)

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.conf import settings
from django.contrib.admin import widgets as admin_widgets
from django.core.urlresolvers import reverse
from django.forms.widgets import flatatt
try:
    from django.utils.encoding import smart_unicode
except ImportError:
    from django.forms.util import smart_unicode
from django.utils.html import escape
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, ugettext as _

class EpicEditorWidget(forms.Textarea):

    def __init__(self, *args, **kwargs):
        super(EpicEditorWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        cfg = {"container": "epic_body_id", "autoSave": False, 'clientSideStorage': False}
        cfg['basePath'] = getattr(settings, 'EPIC_BASEPATH', '/static/dpress/epiceditor')
        cfg_f = {'name': 'body'}
        cfg_f['defaultContent'] = value.replace('\r', '') if value else ""
        cfg['file'] = cfg_f
        cfg_json = simplejson.dumps(cfg)
        hide_field = super(EpicEditorWidget, self).render(name, value, attrs)
        html = u"""
        <div id="epic_body_id" style="height: 300px"></div>
        <div style="display: none">%s</div>
        <script type="text/javascript">
        (function($){
            var bdEditor = new EpicEditor(%s).load(); 
            $('#post_form').submit(function(){
                $('#id_body').val(bdEditor.exportFile());
                });
        }(grp.jQuery));
        </script>
        """ % (hide_field, simplejson.dumps(cfg), )
        return mark_safe(html)

    def _media(self):
        epic_js = getattr(settings, 'EPIC_JS', 'dpress/epiceditor/js/epiceditor.min.js')
        #epic_js = 'dpress/epiceditor/js/epiceditor.js'
        return forms.Media(js=[epic_js])
    media = property(_media)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = saestorage
# -*- coding: utf-8 -*-
import os, time, random 
from django.core.files.base import File
from django.core.files.storage import Storage
from django.conf import settings 
from django.core.files import File
import sae.storage
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class SaeStorage(Storage):
     
    def __init__(self, location="base"
            #accesskey=settings.ACCESS_KEY, 
            #secretkey=settings.SECRET_KEY, 
            #prefix=settings.APP_NAME
            #media_root=settings.MEDIA_ROOT,
            #media_url=settings.MEDIA_URL,
            ): 
        #self.accesskey = accesskey
        #self.secretkey = secretkey
        #self.prefix = prefix
        #self.media_root = media_root
        #self.media_url = media_url

        #self.client = sae.storage.Client(accesskey, secretkey, prefix)
        self.prefix = location
        self.client = sae.storage.Client()

    def _put_file(self, name, content):
        ob = sae.storage.Object(content)
        self.client.put(self.prefix, name, ob)

    def _read(self, name):
        memory_file = StringIO()
        try:
            o = self.client.get(self.prefix, name)
            memory_file.write(o.data)
        except sae.storage.ObjectNotExistsError, e:
            pass
        return memory_file

    def _open(self, name, mode="rb"):
        return SaeStorageFile(name, self, mode=mode)

    def _save(self, name, content): 
        content.open()
        if hasattr(content, 'chunks'):
            content_str = ''.join(chunk for chunk in content.chunks())
        else:
            content_str = content.read()
        #for fake tempfile
        if not content_str and hasattr(content, "file"):
            try:
                content_str = content.file.getvalue()
            except:
                pass
        self._put_file(name, content_str)
        content.close()
        return name

    def delete(self, name):
        self.client.delete(self.prefix, name)

    def exists(self, name):
        try:
            o = self.client.stat(self.prefix, name)
        #except sae.storage.ObjectNotExistsError, e:
        except:
            return False
        return True

    def listdir(self, domain):
        #sae no folder
        files = self.client.list(self.prefix)
        return ((), tuple(f['name'] for f in files))
        
    def size(self, name):
        try:
            stat = self.client.stat(self.prefix, name)
        except sae.storage.ObjectNotExistsError, e:
            return 0
        return stat.length

    def url(self, name):
        return self.client.url(self.prefix, name)
        
    def isdir(self, name):
        return False if name else True

    def isfile(self, name):
        return self.exists(name) if name else False
        
    def modified_time(self, name):
        from datetime import datetime
        return datetime.now()
        
class SaeStorageFile(File):
    """docstring for SaeStorageFile"""
    def __init__(self, name, storage, mode):
        self._name = name
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self._is_read = False

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        if not self._is_read:
            self.file = self._storage._read(self._name)
            self.file = StringIO(self.file.getvalue())
            self._is_read = True
        if num_bytes:
            return self.file.read(num_bytes)
        else:
            return self.file.read()
            
    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True
        self._is_read = True

    def close(self):
        if self._is_dirty:
            self._storage._put_file(self._name, self.file.getvalue())
        self.file.close()

########NEW FILE########
__FILENAME__ = base
# Django settings for simple_todo_site project.
import os
HERE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.join(HERE, '../')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(HERE, 'db.sqlite'),                      # Or path to database file if using sqlite3.
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
#TIME_ZONE = 'America/Chicago'
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
#LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'zh-cn'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(HERE, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(HERE, 'collectedstatic')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
#ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
        os.path.join(HERE, 'static/'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '@lco-u^-xeugx-(c^5w-#-u-eqzc+9@m5@-^!mz@p6ygg$gh7a'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.eggs.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages"
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(HERE, 'templates_plus'),
    os.path.join(HERE, 'templates'),
)

INSTALLED_APPS = (
    'grappelli.dashboard',
    'grappelli',
    'filebrowser',
        
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs', 
    'django.contrib.syndication',
    'django.contrib.flatpages',

    'dj_scaffold',
    'djangohelper',
    'south',
    'compressor',
    'taggit',
    'taggit_templatetags',
    'pagination',

    'dpress',
)
try:
    import gunicorn
    INSTALLED_APPS += ('gunicorn',)
except:
    pass

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio'),
    ('text/less', 'lessc {infile} {outfile}'),
    ('text/x-sass', 'sass {infile} {outfile}'),
    ('text/x-scss', 'sass --scss {infile} {outfile}'),
)

GRAPPELLI_INDEX_DASHBOARD = 'dashboard.CustomIndexDashboard'
PAGINATION_DEFAULT_PAGINATION = 6

DPRESS_TITLE = 'D_TITLE'
DPRESS_SUBTITLE = 'DPRESS_SUBTITLE'
DPRESS_DESCN = ''
DISQUS_SHORTNAME = ''
EPIC_JS = 'dpress/epiceditor/js/epiceditor.min.js'
EPIC_BASEPATH = STATIC_URL + 'dpress/epiceditor'
GOOGLE_ANALYTICS_CODE = ''

########NEW FILE########
__FILENAME__ = dev
from base import *

DEBUG = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#devserver
#MIDDLEWARE_CLASSES += ('devserver.middleware.DevServerMiddleware',)
#INSTALLED_APPS = ('devserver',) + INSTALLED_APPS#devserver must in first

#debug_toolbar
INSTALLED_APPS += ('debug_toolbar',)
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
INTERNAL_IPS = ('127.0.0.2',)

########NEW FILE########
__FILENAME__ = production
from base import *

DEBUG = False
########NEW FILE########
__FILENAME__ = theme_moment
# -*- coding: UTF-8 -*-
from base import *

PAGINATION_DEFAULT_PAGINATION = 20

TEMPLATE_DIRS += (
    os.path.join(HERE, 'themes/moment/templates'),
)

STATICFILES_DIRS += (
    os.path.join(HERE, 'themes/moment/static'),
)

DPRESS_SHOW_CATEGORYS_NAV = True#show categorys in nav

#DPRESS_NAV = [{"name": u"@github", "link": "https://github.com/vicalloy/"},]
DPRESS_NAV = []
DPRESS_ELSEWHERE = []

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.conf import settings

from filebrowser.sites import site

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/filebrowser/', include(site.urls)),
    (r'^grappelli/', include('grappelli.urls')),

    url(r'^', include('dpress.urls')),

    # Examples:
    #url('^$', 'demoapp.views.index', name='idx'),
    #url(r'^demo/', include('demoapp.urls')),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
