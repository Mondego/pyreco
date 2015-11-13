__FILENAME__ = admin
from django.contrib import admin
from models import Chunk

class ChunkAdmin(admin.ModelAdmin):
  list_display = ('key','description',)
  search_fields = ('key', 'content')

admin.site.register(Chunk, ChunkAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Chunk'
        db.create_table('chunks_chunk', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('chunks', ['Chunk'])


    def backwards(self, orm):
        
        # Deleting model 'Chunk'
        db.delete_table('chunks_chunk')


    models = {
        'chunks.chunk': {
            'Meta': {'object_name': 'Chunk'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['chunks']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_chunk_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Chunk.description'
        db.add_column('chunks_chunk', 'description', self.gf('django.db.models.fields.CharField')(default='', max_length=64, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Chunk.description'
        db.delete_column('chunks_chunk', 'description')


    models = {
        'chunks.chunk': {
            'Meta': {'object_name': 'Chunk'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['chunks']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

class Chunk(models.Model):
    """
    A Chunk is a piece of content associated
    with a unique key that can be inserted into
    any template with the use of a special template
    tag
    """
    key = models.CharField(_(u'Key'), help_text=_(u"A unique name for this chunk of content"), blank=False, max_length=255, unique=True)
    content = models.TextField(_(u'Content'), blank=True)
    description = models.CharField(_(u'Description'), blank=True, max_length=64, help_text=_(u"Short Description"))

    class Meta:
        verbose_name = _(u'chunk')
        verbose_name_plural = _(u'chunks')

    def __unicode__(self):
        return u"%s" % (self.key,)

########NEW FILE########
__FILENAME__ = chunks
from django import template
from django.db import models
from django.core.cache import cache

register = template.Library()

Chunk = models.get_model('chunks', 'chunk')
CACHE_PREFIX = "chunk_"

def do_chunk(parser, token):
    # split_contents() knows not to split quoted strings.
    tokens = token.split_contents()
    if len(tokens) < 2 or len(tokens) > 3:
        raise template.TemplateSyntaxError, "%r tag should have either 2 or 3 arguments" % (tokens[0],)
    if len(tokens) == 2:
        tag_name, key = tokens
        cache_time = 0
    if len(tokens) == 3:
        tag_name, key, cache_time = tokens
    key = ensure_quoted_string(key, "%r tag's argument should be in quotes" % tag_name)
    return ChunkNode(key, cache_time)

class ChunkNode(template.Node):
    def __init__(self, key, cache_time=0):
       self.key = key
       self.cache_time = cache_time

    def render(self, context):
        try:
            cache_key = CACHE_PREFIX + self.key
            c = cache.get(cache_key)
            if c is None:
                c = Chunk.objects.get(key=self.key)
                cache.set(cache_key, c, int(self.cache_time))
            content = c.content
        except Chunk.DoesNotExist:
            content = ''
        return content


def do_get_chunk(parser, token):
    tokens = token.split_contents()
    if len(tokens) != 4 or tokens[2] != 'as':
        raise template.TemplateSyntaxError, 'Invalid syntax. Usage: {%% %s "key" as varname %%}' % tokens[0]
    tagname, key, varname = tokens[0], tokens[1], tokens[3]
    key = ensure_quoted_string(key, "Key argument to %r must be in quotes" % tagname)
    return GetChunkNode(key, varname)

class GetChunkNode(template.Node):
    def __init__(self, key, varname):
        self.key = key
        self.varname = varname

    def render(self, context):
        try:
            chunk = Chunk.objects.get(key=self.key)
        except Chunk.DoesNotExist:
            chunk = None
        context[self.varname] = chunk
        return ''


def ensure_quoted_string(string, error_message):
    '''
    Check to see if the key is properly double/single quoted and
    returns the string without quotes
    '''
    if not (string[0] == string[-1] and string[0] in ('"', "'")):
        raise template.TemplateSyntaxError, error_message
    return string[1:-1]


register.tag('chunk', do_chunk)
register.tag('get_chunk', do_get_chunk)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.template import Context, Template, TemplateSyntaxError
from django.core.cache import cache

from chunks.models import Chunk

class BaseTestCase(TestCase):

    def setUp(self):
        self.home_page_left = Chunk.objects.create(
            key='home_page_left',
            content='This is the content for left box')
        cache.delete('cache_home_page_left')


    def render_template(self, content_string, context={}):
        template = Template(content_string)
        return template.render(Context(context))


class ChuckTemplateTagTestCase(BaseTestCase):

    def test_should_render_content_from_key(self):
        result = self.render_template('{% load chunks %}'
                                      '<div>{% chunk "home_page_left" %}</div>')

        self.assertEquals('<div>This is the content for left box</div>', result)


    def test_should_render_empty_string_if_key_not_found(self):
        result = self.render_template('{% load chunks %}'
                                      '<div>{% chunk "key_not_found" %}</div>')

        self.assertEquals('<div></div>', result)


    def test_should_cache_rendered_content(self):
        cache_key = 'chunk_home_page_left'
        self.assertFalse(cache.get(cache_key), "key %r should NOT be cached" % cache_key)

        self.render_template("{% load chunks %}"
                             "<div>{% chunk 'home_page_left' 10 %}</div>")
        cached_result = cache.get(cache_key)

        self.assertTrue(cached_result, "key %r should be cached" % cache_key)
        self.assertEquals('This is the content for left box', cached_result.content)


    def test_should_fail_if_wrong_number_of_arguments(self):
        with self.assertRaisesRegexp(TemplateSyntaxError, "'chunk' tag should have either 2 or 3 arguments"):
            self.render_template('{% load chunks %}'
                                 '{% chunk %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, "'chunk' tag should have either 2 or 3 arguments"):
            self.render_template('{% load chunks %}'
                                 '{% chunk "home_page_left" 10 "invalid" %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, "'chunk' tag should have either 2 or 3 arguments"):
            self.render_template('{% load chunks %}'
                                 '{% chunk "home_page_left" 10 too much invalid arguments %}')


    def test_should_fail_if_key_not_quoted(self):
        with self.assertRaisesRegexp(TemplateSyntaxError, "'chunk' tag's argument should be in quotes"):
            self.render_template('{% load chunks %}'
                                 '{% chunk home_page_left %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, "'chunk' tag's argument should be in quotes"):
            self.render_template('{% load chunks %}'
                                 '{% chunk "home_page_left\' %}')


class GetChuckTemplateTagTestCase(BaseTestCase):

    def test_should_get_chunk_object_given_key(self):
        result = self.render_template('{% load chunks %}'
                                      '{% get_chunk "home_page_left" as chunk_obj %}'
                                      '<p>{{ chunk_obj.content }}</p>')

        self.assertEquals('<p>This is the content for left box</p>', result)

    def test_should_assign_varname_to_None_if_chunk_not_found(self):
        result = self.render_template('{% load chunks %}'
                                      '{% get_chunk "chunk_not_found" as chunk_obj %}'
                                      '{{ chunk_obj }}')

        self.assertEquals('None', result)

    def test_should_fail_if_wrong_number_of_arguments(self):
        with self.assertRaisesRegexp(TemplateSyntaxError, 'Invalid syntax. Usage: {% get_chunk "key" as varname %}'):
            self.render_template('{% load chunks %}'
                                 '{% get_chunk %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, 'Invalid syntax. Usage: {% get_chunk "key" as varname %}'):
            self.render_template('{% load chunks %}'
                                 '{% get_chunk "home_page_left" %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, 'Invalid syntax. Usage: {% get_chunk "key" as varname %}'):
            self.render_template('{% load chunks %}'
                                 '{% get_chunk "home_page_left" as %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, 'Invalid syntax. Usage: {% get_chunk "key" as varname %}'):
            self.render_template('{% load chunks %}'
                                 '{% get_chunk "home_page_left" notas chunk_obj %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, 'Invalid syntax. Usage: {% get_chunk "key" as varname %}'):
            self.render_template('{% load chunks %}'
                                 '{% get_chunk "home_page_left" as chunk_obj invalid %}')

    def test_should_fail_if_key_not_quoted(self):
        with self.assertRaisesRegexp(TemplateSyntaxError, "Key argument to u'get_chunk' must be in quotes"):
            result = self.render_template('{% load chunks %}'
                                          '{% get_chunk home_page_left as chunk_obj %}')

        with self.assertRaisesRegexp(TemplateSyntaxError, "Key argument to u'get_chunk' must be in quotes"):
            result = self.render_template('{% load chunks %}'
                                          '{% get_chunk "home_page_left\' as chunk_obj %}')

########NEW FILE########
__FILENAME__ = runtests
import os.path
import sys

from django.conf import settings

settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(os.path.dirname(__file__), 'testdb.sqlite'),
            }
        },
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        },
    INSTALLED_APPS = ('chunks',)
)

from django.test.utils import get_runner

test_runner = get_runner(settings)()
failures = test_runner.run_tests(['chunks'])

sys.exit(failures)

########NEW FILE########
