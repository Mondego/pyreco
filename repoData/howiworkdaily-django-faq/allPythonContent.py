__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

try:
    import faq
except ImportError:
    sys.stderr.write("django-faq isn't installed; trying to use a source checkout in ../faq.")
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
#
# A minimal settings file that ought to work out of the box for just about
# anyone trying this project. It's deliberately missing most settings to keep
# everything simple.
#
# A real app would have a lot more settings. The only important bit as far as
# django-FAQ is concerned is to have `faq` in INSTALLED_APPS.
#

import os

PROJECT_DIR = os.path.dirname(__file__)
DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'faq.db'),
    }
}

SITE_ID = 1
SECRET_KEY = 'c#zi(mv^n+4te_sy$hpb*zdo7#f7ccmp9ro84yz9bmmfqj9y*c'
ROOT_URLCONF = 'urls'
TEMPLATE_DIRS = (
    [os.path.join(PROJECT_DIR, "templates")]
)
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',

    # Database migration helpers
    'south',

    'faq',
)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin; admin.autodiscover()
from django.conf import settings
from django.views.generic import TemplateView
import faq.views

urlpatterns = patterns('',
    # Just a simple example "home" page to show a bit of help/info.
    url(r'^$', TemplateView.as_view(template_name="home.html")),
    
    # This is the URLconf line you'd put in a real app to include the FAQ views.
    url(r'^faq/', include('faq.urls')),
    
    # Everybody wants an admin to wind a piece of string around.
    url(r'^admin/', include(admin.site.urls)),

    # Normally we'd do this if DEBUG only, but this is just an example app.
    url(regex  = r'^static/(?P<path>.*)$', 
        view   = 'django.views.static.serve',
        kwargs = {'document_root': settings.MEDIA_ROOT}
    ),
)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Question, Topic
            
class TopicAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}
    
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'sort_order', 'created_by', 'created_on',
                    'updated_by', 'updated_on', 'status']
    list_editable = ['sort_order', 'status']

    def save_model(self, request, obj, form, change): 
        '''
        Update created-by / modified-by fields.
        
        The date fields are upadated at the model layer, but that's not got
        access to the user.
        '''
        # If the object's new update the created_by field.
        if not change:
            obj.created_by = request.user
        
        # Either way update the updated_by field.
        obj.updated_by = request.user

        # Let the superclass do the final saving.
        return super(QuestionAdmin, self).save_model(request, obj, form, change)
        
admin.site.register(Question, QuestionAdmin)
admin.site.register(Topic, TopicAdmin)

########NEW FILE########
__FILENAME__ = forms
"""
Here we define a form for allowing site users to submit a potential FAQ that
they would like to see added.

From the user's perspective the question is not added automatically, but
actually it is, only it is added as inactive.
"""

from __future__ import absolute_import
import datetime
from django import forms
from .models import Question, Topic

class SubmitFAQForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['topic', 'text', 'answer']
########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models.query import QuerySet

class QuestionQuerySet(QuerySet):
    def active(self):
        """
        Return only "active" (i.e. published) questions.
        """
        return self.filter(status__exact=self.model.ACTIVE)

class QuestionManager(models.Manager):
    def get_query_set(self):
        return QuestionQuerySet(self.model)

    def active(self):
        return self.get_query_set().active()
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Topic'
        db.create_table(u'faq_topic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=150)),
            ('sort_order', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'faq', ['Topic'])

        # Adding model 'Question'
        db.create_table(u'faq_question', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('answer', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', to=orm['faq.Topic'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=100)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('protected', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sort_order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')()),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['auth.User'])),
            ('updated_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['auth.User'])),
        ))
        db.send_create_signal(u'faq', ['Question'])


    def backwards(self, orm):
        # Deleting model 'Topic'
        db.delete_table(u'faq_topic')

        # Deleting model 'Question'
        db.delete_table(u'faq_question')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'faq.question': {
            'Meta': {'ordering': "['sort_order', 'created_on']", 'object_name': 'Question'},
            'answer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100'}),
            'sort_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': u"orm['faq.Topic']"}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'faq.topic': {
            'Meta': {'ordering': "['sort_order', 'name']", 'object_name': 'Topic'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'sort_order': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['faq']
########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from managers import QuestionManager

User = get_user_model()

class Topic(models.Model):
    """
    Generic Topics for FAQ question grouping
    """
    name = models.CharField(_('name'), max_length=150)
    slug = models.SlugField(_('slug'), max_length=150)
    sort_order = models.IntegerField(_('sort order'), default=0,
        help_text=_('The order you would like the topic to be displayed.'))

    def get_absolute_url(self):
        return '/faq/' + self.slug

    class Meta:
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")
        ordering = ['sort_order', 'name']

    def __unicode__(self):
        return self.name

class Question(models.Model):
    HEADER = 2
    ACTIVE = 1
    INACTIVE = 0
    STATUS_CHOICES = (
        (ACTIVE,    _('Active')),
        (INACTIVE,  _('Inactive')),
        (HEADER,    _('Group Header')),
    )
    
    text = models.TextField(_('question'), help_text=_('The actual question itself.'))
    answer = models.TextField(_('answer'), blank=True, help_text=_('The answer text.'))
    topic = models.ForeignKey(Topic, verbose_name=_('topic'), related_name='questions')
    slug = models.SlugField(_('slug'), max_length=100)
    status = models.IntegerField(_('status'),
        choices=STATUS_CHOICES, default=INACTIVE, 
        help_text=_("Only questions with their status set to 'Active' will be "
                    "displayed. Questions marked as 'Group Header' are treated "
                    "as such by views and templates that are set up to use them."))
    
    protected = models.BooleanField(_('is protected'), default=False,
        help_text=_("Set true if this question is only visible by authenticated users."))
        
    sort_order = models.IntegerField(_('sort order'), default=0,
        help_text=_('The order you would like the question to be displayed.'))

    created_on = models.DateTimeField(_('created on'), default=datetime.datetime.now)
    updated_on = models.DateTimeField(_('updated on'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        null=True, related_name="+")
    updated_by = models.ForeignKey(User, verbose_name=_('updated by'),
        null=True, related_name="+")  
    
    objects = QuestionManager()
    
    class Meta:
        verbose_name = _("Frequent asked question")
        verbose_name_plural = _("Frequently asked questions")
        ordering = ['sort_order', 'created_on']

    def __unicode__(self):
        return self.text

    def save(self, *args, **kwargs):
        # Set the date updated.
        self.updated_on = datetime.datetime.now()
        
        # Create a unique slug, if needed.
        if not self.slug:
            suffix = 0
            potential = base = slugify(self.text[:90])
            while not self.slug:
                if suffix:
                    potential = "%s-%s" % (base, suffix)
                if not Question.objects.filter(slug=potential).exists():
                    self.slug = potential
                # We hit a conflicting slug; increment the suffix and try again.
                suffix += 1
        
        super(Question, self).save(*args, **kwargs)

    def is_header(self):
        return self.status == Question.HEADER

    def is_active(self):
        return self.status == Question.ACTIVE

########NEW FILE########
__FILENAME__ = faqtags
from __future__ import absolute_import

from django import template
from ..models import Question, Topic

register = template.Library()

class FaqListNode(template.Node):
    def __init__(self, num, varname, topic=None):
        self.num = template.Variable(num)
        self.topic = template.Variable(topic) if topic else None
        self.varname = varname

    def render(self, context):
        try:
            num = self.num.resolve(context)
            topic = self.topic.resolve(context) if self.topic else None
        except template.VariableDoesNotExist:
            return ''
        
        if isinstance(topic, Topic):
            qs = Question.objects.filter(topic=topic)
        elif topic is not None:
            qs = Question.objects.filter(topic__slug=topic)
        else:
            qs = Question.objects.all()
            
        context[self.varname] = qs.filter(status=Question.ACTIVE)[:num]
        return ''

@register.tag
def faqs_for_topic(parser, token):
    """
    Returns a list of 'count' faq's that belong to the given topic
    the supplied topic argument must be in the slug format 'topic-name'
    
    Example usage::
    
        {% faqs_for_topic 5 "my-slug" as faqs %}
    """

    args = token.split_contents()
    if len(args) != 5:
        raise template.TemplateSyntaxError("%s takes exactly four arguments" % args[0])
    if args[3] != 'as':
        raise template.TemplateSyntaxError("third argument to the %s tag must be 'as'" % args[0])

    return FaqListNode(num=args[1], topic=args[2], varname=args[4])


@register.tag
def faq_list(parser, token):
    """
    returns a generic list of 'count' faq's to display in a list 
    ordered by the faq sort order.

    Example usage::
    
        {% faq_list 15 as faqs %}
    """
    args = token.split_contents()
    if len(args) != 4:
        raise template.TemplateSyntaxError("%s takes exactly three arguments" % args[0])
    if args[2] != 'as':
        raise template.TemplateSyntaxError("second argument to the %s tag must be 'as'" % args[0])

    return FaqListNode(num=args[1], varname=args[3])

########NEW FILE########
__FILENAME__ = test_admin
"""
Some basic admin tests.

Rather than testing the frontend UI -- that's be a job for something like
Selenium -- this does a bunch of mocking and just tests the various admin
callbacks.
"""

from __future__ import absolute_import

import mock
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import unittest
from django.http import HttpRequest
from django import forms
from ..admin import QuestionAdmin
from ..models import Question

class FAQAdminTests(unittest.TestCase):
    
    def test_question_admin_save_model(self):
        user1 = mock.Mock(spec=User)
        user2 = mock.Mock(spec=User)
        req = mock.Mock(spec=HttpRequest)
        obj = mock.Mock(spec=Question)
        form = mock.Mock(spec=forms.Form)
        
        qa = QuestionAdmin(Question, admin.site)
        
        # Test saving a new model.
        req.user = user1
        qa.save_model(req, obj, form, change=False)
        obj.save.assert_called()
        self.assertEqual(obj.created_by, user1, "created_by wasn't set to request.user")
        self.assertEqual(obj.updated_by, user1, "updated_by wasn't set to request.user")
        
        # And saving an existing model.
        obj.save.reset_mock()
        req.user = user2
        qa.save_model(req, obj, form, change=True)
        obj.save.assert_called()
        self.assertEqual(obj.created_by, user1, "created_by shouldn't have been changed")
        self.assertEqual(obj.updated_by, user2, "updated_by wasn't set to request.user")
########NEW FILE########
__FILENAME__ = test_models
from __future__ import absolute_import

import datetime
import django.test
from ..models import Topic, Question

class FAQModelTests(django.test.TestCase):
    
    def test_model_save(self):
        t = Topic.objects.create(name='t', slug='t')
        q = Question.objects.create(
            text = "What is your quest?",
            answer = "I see the grail!",
            topic = t
        )
        self.assertEqual(q.created_on.date(), datetime.date.today())
        self.assertEqual(q.updated_on.date(), datetime.date.today())
        self.assertEqual(q.slug, "what-is-your-quest")
        
    def test_model_save_duplicate_slugs(self):
        t = Topic.objects.create(name='t', slug='t')
        q = Question.objects.create(
            text = "What is your quest?",
            answer = "I see the grail!",
            topic = t
        )
        q2 = Question.objects.create(
            text = "What is your quest?",
            answer = "I see the grail!",
            topic = t
        )
        self.assertEqual(q2.slug, 'what-is-your-quest-1')
########NEW FILE########
__FILENAME__ = test_templatetags
from __future__ import absolute_import

import django.test
from django import template
from django.utils import unittest
from ..templatetags import faqtags
from ..models import Topic

class FAQTagsSyntaxTests(unittest.TestCase):
    """
    Tests for the syntax/compliation functions.
    
    These are broken out here so that they don't have to be
    django.test.TestCases, which are slower.
    """
    
    def compile(self, tagfunc, token_contents):
        """
        Mock out a call to a template compliation function.
        
        Assumes the tag doesn't use the parser, so this won't work for block tags.
        """
        t = template.Token(template.TOKEN_BLOCK, token_contents)
        return tagfunc(None, t)
    
    def test_faqs_for_topic_compile(self):
        t = self.compile(faqtags.faqs_for_topic, "faqs_for_topic 15 'some-slug' as faqs")
        self.assertEqual(t.num.var, "15")
        self.assertEqual(t.topic.var, "'some-slug'")
        self.assertEqual(t.varname, "faqs")
        
    def test_faqs_for_topic_too_few_arguments(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faqs_for_topic, 
                          "faqs_for_topic 15 'some-slug' as")
        
    def test_faqs_for_topic_too_many_arguments(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faqs_for_topic, 
                          "faqs_for_topic 15 'some-slug' as varname foobar")
                          
    def test_faqs_for_topic_bad_as(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faqs_for_topic, 
                          "faqs_for_topic 15 'some-slug' blahblah varname")
    
    def test_faq_list_compile(self):
        t = self.compile(faqtags.faq_list, "faq_list 15 as faqs")
        self.assertEqual(t.num.var, "15")
        self.assertEqual(t.varname, "faqs")
        
    def test_faq_list_too_few_arguments(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faq_list, 
                          "faq_list 15")
        
    def test_faq_list_too_many_arguments(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faq_list, 
                          "faq_list 15 as varname foobar")
                          
    def test_faq_list_bad_as(self):
        self.assertRaises(template.TemplateSyntaxError,
                          self.compile, 
                          faqtags.faq_list, 
                          "faq_list 15 blahblah varname")

class FAQTagsNodeTests(django.test.TestCase):
    """
    Tests for the node classes themselves, and hence the rendering functions.
    """
    fixtures = ['faq_test_data.json']
    
    def test_faqs_for_topic_node(self):
        context = template.Context()
        node = faqtags.FaqListNode(num='5', topic='"silly-questions"', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assertQuerysetEqual(context['faqs'], 
            ['<Question: What is your favorite color?>',
             '<Question: What is your quest?>'])
             
    def test_faqs_for_topic_node_variable_arguments(self):
        """
        Test faqs_for_topic with a variable arguments.
        """
        context = template.Context({'topic': Topic.objects.get(pk=1),
                                    'number': 1})
        node = faqtags.FaqListNode(num='number', topic='topic', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assertQuerysetEqual(context['faqs'], ["<Question: What is your favorite color?>"])
    
    def test_faqs_for_topic_node_invalid_variables(self):
        context = template.Context()
        node = faqtags.FaqListNode(num='number', topic='topic', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assert_("faqs" not in context,
                     "faqs variable shouldn't have been added to the context.")
    
    def test_faq_list_node(self):
        context = template.Context()
        node = faqtags.FaqListNode(num='5', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assertQuerysetEqual(context['faqs'], 
            ['<Question: What is your favorite color?>',
             '<Question: What is your quest?>',
             '<Question: What is Django-FAQ?>'])
             
    def test_faq_list_node_variable_arguments(self):
        """
        Test faqs_for_topic with a variable arguments.
        """
        context = template.Context({'topic': Topic.objects.get(pk=1),
                                    'number': 1})
        node = faqtags.FaqListNode(num='number', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assertQuerysetEqual(context['faqs'], ["<Question: What is your favorite color?>"])
    
    def test_faq_list_node_invalid_variables(self):
        context = template.Context()
        node = faqtags.FaqListNode(num='number', varname="faqs")
        content = node.render(context)
        self.assertEqual(content, "")
        self.assert_("faqs" not in context,
                     "faqs variable shouldn't have been added to the context.")
    

########NEW FILE########
__FILENAME__ = test_views
from __future__ import absolute_import

import datetime
import django.test
import mock
import os
from django.conf import settings
from ..models import Topic, Question

class FAQViewTests(django.test.TestCase):
    urls = 'faq.urls'
    fixtures = ['faq_test_data.json']

    def setUp(self):
        # Make some test templates available.
        self._oldtd = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = [os.path.join(os.path.dirname(__file__), 'templates')]

    def tearDown(self):
        settings.TEMPLATE_DIRS = self._oldtd
    
    def test_submit_faq_get(self):
        response = self.client.get('/submit/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq/submit_question.html")

    @mock.patch('django.contrib.messages')
    def test_submit_faq_post(self, mock_messages):
        data = {
            'topic': '1',
            'text': 'What is your favorite color?',
            'answer': 'Blue. I mean red. I mean *AAAAHHHHH....*',
        }
        response = self.client.post('/submit/', data)
        mock_messages.sucess.assert_called()
        self.assertRedirects(response, "/submit/thanks/")
        self.assert_(
            Question.objects.filter(text=data['text']).exists(),
            "Expected question object wasn't created."
        )
        
    def test_submit_thanks(self):
        response = self.client.get('/submit/thanks/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq/submit_thanks.html")
    
    def test_faq_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq/topic_list.html")
        self.assertQuerysetEqual(
            response.context["topics"],
            ["<Topic: Silly questions>", "<Topic: Serious questions>"]
        )
        self.assertEqual(
            response.context['last_updated'],
            Question.objects.order_by('-updated_on')[0].updated_on
        )
        
    def test_topic_detail(self):
        response = self.client.get('/silly-questions/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq/topic_detail.html")
        self.assertEqual(
            response.context['topic'],
            Topic.objects.get(slug="silly-questions")
        )
        self.assertEqual(
            response.context['last_updated'],
            Topic.objects.get(slug='silly-questions').questions.order_by('-updated_on')[0].updated_on
        )
        self.assertQuerysetEqual(
            response.context["questions"],
            ["<Question: What is your favorite color?>", 
             "<Question: What is your quest?>"]
        )
    
    def test_question_detail(self):
        response = self.client.get('/silly-questions/your-quest/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq/question_detail.html")
        self.assertEqual(
            response.context["question"],
            Question.objects.get(slug="your-quest")
        )

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from django.conf.urls.defaults import *
from . import views as faq_views

urlpatterns = patterns('',
    url(regex = r'^$',
        view  = faq_views.TopicList.as_view(),
        name  = 'faq_topic_list',
    ),
    url(regex = r'^submit/$',
        view  = faq_views.SubmitFAQ.as_view(),
        name  = 'faq_submit',
    ),
    url(regex = r'^submit/thanks/$',
        view  = faq_views.SubmitFAQThanks.as_view(),
        name  = 'faq_submit_thanks',
    ),
    url(regex = r'^(?P<slug>[\w-]+)/$',
        view  = faq_views.TopicDetail.as_view(),
        name  = 'faq_topic_detail',
    ),
    url(regex = r'^(?P<topic_slug>[\w-]+)/(?P<slug>[\w-]+)/$',
        view  = faq_views.QuestionDetail.as_view(),
        name  = 'faq_question_detail',
    ),
)
########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import
from django.db.models import Max
from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from .models import Question, Topic
from .forms import SubmitFAQForm

class TopicList(ListView):
    model = Topic
    template = "faq/topic_list.html"
    allow_empty = True
    context_object_name = "topics"

    def get_context_data(self, **kwargs):
        data = super(TopicList, self).get_context_data(**kwargs)

        # This slightly magical queryset grabs the latest update date for
        # topic's questions, then the latest date for that whole group.
        # In other words, it's::
        #
        #   max(max(q.updated_on for q in topic.questions) for topic in topics)
        #
        # Except performed in the DB, so quite a bit more efficiant.
        #
        # We can't just do Question.objects.all().aggregate(max('updated_on'))
        # because that'd prevent a subclass from changing the view's queryset
        # (or even model -- this view'll even work with a different model
        # as long as that model has a many-to-one to something called "questions"
        # with an "updated_on" field). So this magic is the price we pay for
        # being generic.
        last_updated = (data['object_list']
                            .annotate(updated=Max('questions__updated_on'))
                            .aggregate(Max('updated')))

        data.update({'last_updated': last_updated['updated__max']})
        return data

class TopicDetail(DetailView):
    model = Topic
    template = "faq/topic_detail.html"
    context_object_name = "topic"

    def get_context_data(self, **kwargs):
        # Include a list of questions this user has access to. If the user is
        # logged in, this includes protected questions. Otherwise, not.
        qs = self.object.questions.active()
        if self.request.user.is_anonymous():
            qs = qs.exclude(protected=True)

        data = super(TopicDetail, self).get_context_data(**kwargs)
        data.update({
            'questions': qs,
            'last_updated': qs.aggregate(updated=Max('updated_on'))['updated'],
        })
        return data

class QuestionDetail(DetailView):
    queryset = Question.objects.active()
    template = "faq/question_detail.html"

    def get_queryset(self):
        topic = get_object_or_404(Topic, slug=self.kwargs['topic_slug'])

        # Careful here not to hardcode a base queryset. This lets
        # subclassing users re-use this view on a subset of questions, or
        # even on a new model.
        # FIXME: similar logic as above. This should push down into managers.
        qs = super(QuestionDetail, self).get_queryset().filter(topic=topic)
        if self.request.user.is_anonymous():
            qs = qs.exclude(protected=True)

        return qs

class SubmitFAQ(CreateView):
    model = Question
    form_class = SubmitFAQForm
    template_name = "faq/submit_question.html"
    success_view_name = "faq_submit_thanks"

    def get_form_kwargs(self):
        kwargs = super(SubmitFAQ, self).get_form_kwargs()
        kwargs['instance'] = Question()
        if self.request.user.is_authenticated():
            kwargs['instance'].created_by = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super(SubmitFAQ, self).form_valid(form)
        messages.success(self.request,
            _("Your question was submitted and will be reviewed by for inclusion in the FAQ."),
            fail_silently=True,
        )
        return response

    def get_success_url(self):
        # The superclass version raises ImproperlyConfigered if self.success_url
        # isn't set. Instead of that, we'll try to redirect to a named view.
        if self.success_url:
            return self.success_url
        else:
            return reverse(self.success_view_name)

class SubmitFAQThanks(TemplateView):
    template_name = "faq/submit_thanks.html"
########NEW FILE########
__FILENAME__ = _testrunner
"""
Test support harness to make setup.py test work.
"""

import sys

from django.conf import settings
settings.configure(
    DATABASES = {
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory;'}
    },
    INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'faq'],
    ROOT_URLCONF = 'faq.urls',
)

def runtests():
    import django.test.utils
    runner_class = django.test.utils.get_runner(settings)
    test_runner = runner_class(verbosity=1, interactive=True)
    failures = test_runner.run_tests(['faq'])
    sys.exit(failures)
########NEW FILE########
