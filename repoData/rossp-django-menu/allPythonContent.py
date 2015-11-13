__FILENAME__ = admin
from django.contrib import admin
from menu.models import Menu, MenuItem

class MenuItemInline(admin.TabularInline):
    model = MenuItem

class MenuAdmin(admin.ModelAdmin):
    inlines = [MenuItemInline,]

admin.site.register(Menu, MenuAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Menu'
        db.create_table('menu_menu', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('base_url', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('menu', ['Menu'])

        # Adding model 'MenuItem'
        db.create_table('menu_menuitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('menu', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['menu.Menu'])),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
            ('link_url', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('login_required', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('menu', ['MenuItem'])


    def backwards(self, orm):
        
        # Deleting model 'Menu'
        db.delete_table('menu_menu')

        # Deleting model 'MenuItem'
        db.delete_table('menu_menuitem')


    models = {
        'menu.menu': {
            'Meta': {'object_name': 'Menu'},
            'base_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'menu.menuitem': {
            'Meta': {'object_name': 'MenuItem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'menu': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['menu.Menu']"}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['menu']


########NEW FILE########
__FILENAME__ = 0002_auto__add_field_menuitem_anonymous_only
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'MenuItem.anonymous_only'
        db.add_column('menu_menuitem', 'anonymous_only', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'MenuItem.anonymous_only'
        db.delete_column('menu_menuitem', 'anonymous_only')


    models = {
        'menu.menu': {
            'Meta': {'object_name': 'Menu'},
            'base_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'menu.menuitem': {
            'Meta': {'object_name': 'MenuItem'},
            'anonymous_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'menu': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['menu.Menu']"}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['menu']

########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _
from django.db import models


class Menu(models.Model):
    name = models.CharField(
        _(u'Name'),
        max_length=100
        )

    slug = models.SlugField(
        _(u'Slug')
        )

    base_url = models.CharField(
        _(u'Base URL'),
        max_length=100,
        blank=True,
        null=True
        )

    description = models.TextField(
        _(u'Description'),
        blank=True,
        null=True
        )

    class Meta:
        verbose_name = _(u'menu')
        verbose_name_plural = _(u'menus')

    def __unicode__(self):
        return u"%s" % self.name

    def save(self, *args, **kwargs):
        """
        Re-order all items from 10 upwards, at intervals of 10.
        This makes it easy to insert new items in the middle of
        existing items without having to manually shuffle
        them all around.
        """
        super(Menu, self).save(*args, **kwargs)

        current = 10
        for item in MenuItem.objects.filter(menu=self).order_by('order'):
            item.order = current
            item.save()
            current += 10


class MenuItem(models.Model):
    menu = models.ForeignKey(
        Menu,
        verbose_name=_(u'Name')
        )

    order = models.IntegerField(
        _(u'Order'),
        default=500
        )

    link_url = models.CharField(
        _(u'Link URL'),
        max_length=100,
        help_text=_(u'URL or URI to the content, eg /about/ or http://foo.com/')
        )

    title = models.CharField(
        _(u'Title'),
        max_length=100
        )

    login_required = models.BooleanField(
        _(u'Login required'),
        blank=True,
        help_text=_(u'Should this item only be shown to authenticated users?')
        )

    anonymous_only = models.BooleanField(
        _(u'Anonymous only'),
        blank=True,
        help_text=_(u'Should this item only be shown to non-logged-in users?')
        )

    class Meta:
        verbose_name = _(u'menu item')
        verbose_name_plural = _(u'menu items')

    def __unicode__(self):
        return u"%s %s. %s" % (self.menu.slug, self.order, self.title)

########NEW FILE########
__FILENAME__ = menubuilder
from menu.models import Menu, MenuItem
from django import template
from django.core.cache import cache

register = template.Library()

def build_menu(parser, token):
    """
    {% menu menu_name %}
    """
    try:
        tag_name, menu_name = token.split_contents()
    except:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]
    return MenuObject(menu_name)

class MenuObject(template.Node):
    def __init__(self, menu_name):
        self.menu_name = menu_name

    def render(self, context):
        current_path = context['request'].path
        user = context['request'].user
        context['menuitems'] = get_items(self.menu_name, current_path, user)
        return ''
  
def build_sub_menu(parser, token):
    """
    {% submenu %}
    """
    return SubMenuObject()

class SubMenuObject(template.Node):
    def __init__(self):
        pass

    def render(self, context):
        current_path = context['request'].path
        user = context['request'].user
        menu = False
        for m in Menu.objects.filter(base_url__isnull=False):
            if m.base_url and current_path.startswith(m.base_url):
                menu = m

        if menu:
            context['submenu_items'] = get_items(menu.slug, current_path, user)
            context['submenu'] = menu
        else:
            context['submenu_items'] = context['submenu'] = None
        return ''

def get_items(menu_name, current_path, user):
    """
    If possible, use a cached list of items to avoid continually re-querying 
    the database.
    The key contains the menu name, whether the user is authenticated, and the current path.
    Disable caching by setting MENU_CACHE_TIME to -1.
    """
    from django.conf import settings
    cache_time = getattr(settings, 'MENU_CACHE_TIME', 1800)
    debug = getattr(settings, 'DEBUG', False)

    if cache_time >= 0 and not debug:
        cache_key = 'django-menu-items/%s/%s/%s'  % (menu_name, current_path, user.is_authenticated())
        menuitems = cache.get(cache_key, [])
        if menuitems:
            return menuitems
    else:
        menuitems = []
        
    try:
        menu = Menu.objects.get(slug=menu_name)
    except Menu.DoesNotExist:
        return []

    for i in MenuItem.objects.filter(menu=menu).order_by('order'):
        current = ( i.link_url != '/' and current_path.startswith(i.link_url)) or ( i.link_url == '/' and current_path == '/' )
        if menu.base_url and i.link_url == menu.base_url and current_path != i.link_url:
            current = False
        show_anonymous = i.anonymous_only and user.is_anonymous()
        show_auth = i.login_required and user.is_authenticated()
        if (not (i.login_required or i.anonymous_only)) or (i.login_required and show_auth) or (i.anonymous_only and show_anonymous):
            menuitems.append({'url': i.link_url, 'title': i.title, 'current': current,})

    if cache_time >= 0 and not debug:
        cache.set(cache_key, menuitems, cache_time)
    return menuitems

register.tag('menu', build_menu)
register.tag('submenu', build_sub_menu)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
