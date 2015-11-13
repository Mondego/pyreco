__FILENAME__ = admin
import re

import django
try:
    from django.conf.urls import patterns, url
    from django.views.generic import RedirectView
except ImportError:  # Django < 1.4
    from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.http import HttpResponsePermanentRedirect
from django.utils.html import escape
from django.utils.translation import ugettext as _
try:
    from django.utils.encoding import force_text
except ImportError:  # Django < 1.5
    from django.utils.encoding import force_unicode as force_text

from treemenus.models import Menu, MenuItem
from treemenus.utils import get_parent_choices, MenuItemChoiceField, move_item_or_clean_ranks


class MenuItemAdmin(admin.ModelAdmin):
    ''' This class is used as a proxy by MenuAdmin to manipulate menu items. It should never be registered. '''
    def __init__(self, model, admin_site, menu):
        super(MenuItemAdmin, self).__init__(model, admin_site)
        self._menu = menu

    def delete_view(self, request, object_id, extra_context=None):
        if request.method == 'POST':  # The user has already confirmed the deletion.
            # Delete and return to menu page
            super(MenuItemAdmin, self).delete_view(request, object_id, extra_context)
            return HttpResponseRedirect("../../../")
        else:
            # Show confirmation page
            return super(MenuItemAdmin, self).delete_view(request, object_id, extra_context)

    def save_model(self, request, obj, form, change):
        obj.menu = self._menu
        obj.save()

    def response_add(self, request, obj, post_url_continue=None):
        if django.VERSION < (1, 5):
            post_url_continue = '../%s/'
        else:
            pk_value = obj._get_pk_val()
            post_url_continue = '../%s/' % pk_value
        response = super(MenuItemAdmin, self).response_add(request, obj, post_url_continue)
        if "_continue" in request.POST:
            return response
        elif "_addanother" in request.POST:
            return HttpResponseRedirect(request.path)
        elif "_popup" in request.POST:
            return response
        else:
            return HttpResponseRedirect("../../")

    def response_change(self, request, obj):
        super(MenuItemAdmin, self).response_change(request, obj)
        if "_continue" in request.POST:
            return HttpResponseRedirect(request.path)
        elif "_addanother" in request.POST:
            return HttpResponseRedirect("../add/")
        elif "_saveasnew" in request.POST:
            return HttpResponseRedirect("../%s/" % obj._get_pk_val())
        else:
            return HttpResponseRedirect("../../")

    def get_form(self, request, obj=None, **kwargs):
        form = super(MenuItemAdmin, self).get_form(request, obj, **kwargs)
        choices = get_parent_choices(self._menu, obj)
        form.base_fields['parent'] = MenuItemChoiceField(choices=choices)
        return form


class MenuAdmin(admin.ModelAdmin):
    menu_item_admin_class = MenuItemAdmin

    def __call__(self, request, url):
        ''' DEPRECATED!! More recent versions of Django use the get_urls method instead.
            Overriden to route extra URLs.
        '''
        if url:
            if url.endswith('items/add'):
                return self.add_menu_item(request, unquote(url[:-10]))
            if url.endswith('items'):
                return HttpResponseRedirect('../')
            match = re.match('^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)$', url)
            if match:
                return self.edit_menu_item(request, match.group('menu_pk'), match.group('menu_item_pk'))
            match = re.match('^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/delete$', url)
            if match:
                return self.delete_menu_item(request, match.group('menu_pk'), match.group('menu_item_pk'))
            match = re.match('^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/history$', url)
            if match:
                return self.history_menu_item(request, match.group('menu_pk'), match.group('menu_item_pk'))
            match = re.match('^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/move_up$', url)
            if match:
                return self.move_up_item(request, match.group('menu_pk'), match.group('menu_item_pk'))
            match = re.match('^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/move_down$', url)
            if match:
                return self.move_down_item(request, match.group('menu_pk'), match.group('menu_item_pk'))
        return super(MenuAdmin, self).__call__(request, url)

    def get_urls(self):
        urls = super(MenuAdmin, self).get_urls()
        my_urls = patterns('',
                           (r'^(?P<menu_pk>[-\w]+)/items/add/$',
                            self.admin_site.admin_view(self.add_menu_item)),
                           (r'^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/$',
                            self.admin_site.admin_view(self.edit_menu_item)),
                           (r'^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/delete/$',
                            self.admin_site.admin_view(self.delete_menu_item)),
                           (r'^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/history/$',
                            self.admin_site.admin_view(self.history_menu_item)),
                           (r'^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/move_up/$',
                            self.admin_site.admin_view(self.move_up_item)),
                           (r'^(?P<menu_pk>[-\w]+)/items/(?P<menu_item_pk>[-\w]+)/move_down/$',
                            self.admin_site.admin_view(self.move_down_item)),
                           )

        if django.VERSION >= (1, 4):
            # Dummy named URLs to satisfy reversing the reversing requirements
            # of the menuitem add/change views. It shouldn't ever be used; it
            # just needs to exist so that it get resolved internally by the
            # django admin.
            
            my_urls += patterns('',
                                url(r'^item_changelist/$',
                                    RedirectView.as_view(url='/'),
                                    name='treemenus_menuitem_changelist'),
                                url(r'^item_add/$',
                                    RedirectView.as_view(url='/'),
                                    name='treemenus_menuitem_add'),
                                url(r'^item_history/(?P<pk>[-\w]+)/$',
                                    self.menu_item_redirect,
                                    {'action' : 'history'},
                                    name='treemenus_menuitem_history'),
                                url(r'^item_delete/(?P<pk>[-\w]+)/$',
                                    self.menu_item_redirect,
                                    {'action': 'delete'},
                                    name='treemenus_menuitem_delete'),
                                )
        return my_urls + urls

    def get_object_with_change_permissions(self, request, model, obj_pk):
        ''' Helper function that returns a menu/menuitem if it exists and if the user has the change permissions '''
        try:
            obj = model._default_manager.get(pk=obj_pk)
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        if obj is None:
            raise Http404('%s object with primary key %r does not exist.' % (model.__name__, escape(obj_pk)))
        return obj

    def menu_item_redirect(self, request, pk, action):
        menu_pk = MenuItem.objects.select_related('menu').get(id=pk).menu.id
        return HttpResponsePermanentRedirect(
                r'../../%d/items/%s/%s/' % (menu_pk, pk, action))

    def add_menu_item(self, request, menu_pk):
        ''' Custom view '''
        menu = self.get_object_with_change_permissions(request, Menu, menu_pk)
        menuitem_admin = self.menu_item_admin_class(MenuItem, self.admin_site, menu)
        return menuitem_admin.add_view(request, extra_context={'menu': menu})

    def edit_menu_item(self, request, menu_pk, menu_item_pk):
        ''' Custom view '''
        menu = self.get_object_with_change_permissions(request, Menu, menu_pk)
        menu_item_admin = self.menu_item_admin_class(MenuItem, self.admin_site, menu)
        return menu_item_admin.change_view(request, menu_item_pk, extra_context={'menu': menu})

    def delete_menu_item(self, request, menu_pk, menu_item_pk):
        ''' Custom view '''
        menu = self.get_object_with_change_permissions(request, Menu, menu_pk)
        menu_item_admin = self.menu_item_admin_class(MenuItem, self.admin_site, menu)
        return menu_item_admin.delete_view(request, menu_item_pk, extra_context={'menu': menu})

    def history_menu_item(self, request, menu_pk, menu_item_pk):
        ''' Custom view '''
        menu = self.get_object_with_change_permissions(request, Menu, menu_pk)
        menu_item_admin = self.menu_item_admin_class(MenuItem, self.admin_site, menu)
        return menu_item_admin.history_view(request, menu_item_pk, extra_context={'menu': menu})

    def move_down_item(self, request, menu_pk, menu_item_pk):
        self.get_object_with_change_permissions(request, Menu, menu_pk)
        menu_item = self.get_object_with_change_permissions(request, MenuItem, menu_item_pk)

        if menu_item.rank < menu_item.siblings().count():
            move_item_or_clean_ranks(menu_item, 1)
            msg = _('The menu item "%s" was moved successfully.') % force_text(menu_item)
        else:
            msg = _('The menu item "%s" is not allowed to move down.') % force_text(menu_item)

        if django.VERSION >= (1, 4):
            self.message_user(request, message=msg)
        else:
            request.user.message_set.create(message=msg)

        return HttpResponseRedirect('../../../')

    def move_up_item(self, request, menu_pk, menu_item_pk):
        self.get_object_with_change_permissions(request, Menu, menu_pk)
        menu_item = self.get_object_with_change_permissions(request, MenuItem, menu_item_pk)

        if menu_item.rank > 0:
            move_item_or_clean_ranks(menu_item, -1)
            msg = _('The menu item "%s" was moved successfully.') % force_text(menu_item)
        else:
            msg = _('The menu item "%s" is not allowed to move up.') % force_text(menu_item)

        if django.VERSION >= (1, 4):
            self.message_user(request, message=msg)
        else:
            request.user.message_set.create(message=msg)

        return HttpResponseRedirect('../../../')


admin.site.register(Menu, MenuAdmin)

########NEW FILE########
__FILENAME__ = config
APP_LABEL = 'treemenus'

########NEW FILE########
__FILENAME__ = models
from itertools import chain

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _


class MenuItem(models.Model):
    parent = models.ForeignKey('self', verbose_name=_('parent'), null=True, blank=True)
    caption = models.CharField(_('caption'), max_length=50)
    url = models.CharField(_('URL'), max_length=200, blank=True)
    named_url = models.CharField(_('named URL'), max_length=200, blank=True)
    level = models.IntegerField(_('level'), default=0, editable=False)
    rank = models.IntegerField(_('rank'), default=0, editable=False)
    menu = models.ForeignKey('Menu', related_name='contained_items', verbose_name=_('menu'), null=True, blank=True, editable=False)

    def __str__(self):
        return self.caption

    def __unicode__(self):
        return self.caption

    def save(self, force_insert=False, **kwargs):
        from treemenus.utils import clean_ranks

        # Calculate level
        old_level = self.level
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 0

        if self.pk:
            new_parent = self.parent
            old_parent = MenuItem.objects.get(pk=self.pk).parent
            if old_parent != new_parent:
                #If so, we need to recalculate the new ranks for the item and its siblings (both old and new ones).
                if new_parent:
                    clean_ranks(new_parent.children())  # Clean ranks for new siblings
                    self.rank = new_parent.children().count()
                super(MenuItem, self).save(force_insert, **kwargs)  # Save menu item in DB. It has now officially changed parent.
                if old_parent:
                    clean_ranks(old_parent.children())  # Clean ranks for old siblings
            else:
                super(MenuItem, self).save(force_insert, **kwargs)  # Save menu item in DB

        else:  # Saving the menu item for the first time (i.e creating the object)
            if not self.has_siblings():
                # No siblings - initial rank is 0.
                self.rank = 0
            else:
                # Has siblings - initial rank is highest sibling rank plus 1.
                siblings = self.siblings().order_by('-rank')
                self.rank = siblings[0].rank + 1
            super(MenuItem, self).save(force_insert, **kwargs)

        # If level has changed, force children to refresh their own level
        if old_level != self.level:
            for child in self.children():
                child.save()  # Just saving is enough, it'll refresh its level correctly.

    def delete(self, using=None):
        from treemenus.utils import clean_ranks
        old_parent = self.parent
        super(MenuItem, self).delete()
        if old_parent:
            clean_ranks(old_parent.children())

    def caption_with_spacer(self):
        spacer = ''
        for i in range(0, self.level):
            spacer += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        if self.level > 0:
            spacer += '|-&nbsp;'
        return '%s%s' % (spacer, self.caption)

    def get_flattened(self):
        flat_structure = [self]
        for child in self.children():
            flat_structure = chain(flat_structure, child.get_flattened())
        return flat_structure

    def siblings(self):
        if not self.parent:
            return MenuItem.objects.none()
        else:
            if not self.pk:  # If menu item not yet been saved in DB (i.e does not have a pk yet)
                return self.parent.children()
            else:
                return self.parent.children().exclude(pk=self.pk)

    def has_siblings(self):
        return self.siblings().count() > 0

    def children(self):
        _children = MenuItem.objects.filter(parent=self).order_by('rank',)
        for child in _children:
            child.parent = self  # Hack to avoid unnecessary DB queries further down the track.
        return _children

    def has_children(self):
        return self.children().count() > 0


class Menu(models.Model):
    name = models.CharField(_('name'), max_length=50)
    root_item = models.ForeignKey(MenuItem, related_name='is_root_item_of', verbose_name=_('root item'), null=True, blank=True, editable=False)

    def save(self, force_insert=False, **kwargs):
        if not self.root_item:
            root_item = MenuItem()
            root_item.caption = ugettext('root')
            if not self.pk:  # If creating a new object (i.e does not have a pk yet)
                super(Menu, self).save(force_insert, **kwargs)  # Save, so that it gets a pk
                force_insert = False
            root_item.menu = self
            root_item.save()  # Save, so that it gets a pk
            self.root_item = root_item
        super(Menu, self).save(force_insert, **kwargs)

    def delete(self, using=None):
        if self.root_item is not None:
            self.root_item.delete()
        super(Menu, self).delete()

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('menu')
        verbose_name_plural = _('menus')

########NEW FILE########
__FILENAME__ = tree_menu_tags
import sys

import django
from django import template
from django.template.defaulttags import url
from django.template import Node, TemplateSyntaxError


PY3 = sys.version_info[0] == 3
if PY3:
    from django.utils import six

from treemenus.models import Menu, MenuItem
from treemenus.config import APP_LABEL


register = template.Library()


@register.simple_tag
def get_treemenus_static_prefix():
    if django.VERSION >= (1, 3):
        from django.templatetags.static import PrefixNode
        return PrefixNode.handle_simple("STATIC_URL") + 'img/treemenus'
    else:
        from django.contrib.admin.templatetags.adminmedia import admin_media_prefix
        return admin_media_prefix() + 'img/admin/'


def show_menu(context, menu_name, menu_type=None):
    menu = Menu.objects.get(name=menu_name)
    context['menu'] = menu
    context['menu_name'] = menu_name
    if menu_type:
        context['menu_type'] = menu_type
    return context
register.inclusion_tag('%s/menu.html' % APP_LABEL, takes_context=True)(show_menu)


def show_menu_item(context, menu_item):
    if not isinstance(menu_item, MenuItem):
        error_message = 'Given argument must be a MenuItem object.'
        raise template.TemplateSyntaxError(error_message)

    context['menu_item'] = menu_item
    return context
register.inclusion_tag('%s/menu_item.html' % APP_LABEL, takes_context=True)(show_menu_item)


class ReverseNamedURLNode(Node):
    def __init__(self, named_url, parser):
        self.named_url = named_url
        self.parser = parser

    def render(self, context):
        from django.template import TOKEN_BLOCK, Token

        resolved_named_url = self.named_url.resolve(context)
        if django.VERSION >= (1, 3):
            contents = 'url "%s"' % resolved_named_url
        else:
            contents = 'url %s' % resolved_named_url

        urlNode = url(self.parser, Token(token_type=TOKEN_BLOCK, contents=contents))
        return urlNode.render(context)


def reverse_named_url(parser, token):
    bits = token.contents.split(' ', 2)
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes only one argument"
                                  " (named url)" % bits[0])
    named_url = parser.compile_filter(bits[1])

    return ReverseNamedURLNode(named_url, parser)
reverse_named_url = register.tag(reverse_named_url)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from .models import FakeMenuItemExtension

admin.site.register(FakeMenuItemExtension)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from treemenus.models import MenuItem


class FakeMenuItemExtension(models.Model):
    menu_item = models.OneToOneField(MenuItem, related_name="%(class)s_related")
    published = models.BooleanField(default=False)

########NEW FILE########
__FILENAME__ = settings
# For Django 1.1 and under
DATABASE_ENGINE = 'django.db.backends.sqlite3'

# For Django 1.2 and above
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'treemenus',
]

ROOT_URLCONF = 'treemenus.tests.urls'

SECRET_KEY = 'Shush... Tell no one.'

# For Django 1.3 and above
STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = test_treemenus
try:
    from imp import reload  # Python 3
except ImportError:
    pass
from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app
from django import template
from django.template.loaders import app_directories
from django.contrib.auth.models import User
import django
from django.core.urlresolvers import reverse

try:
    from django.utils.encoding import smart_bytes
except ImportError:  # Django < 1.5
    smart_bytes = str

from treemenus.models import Menu, MenuItem
from treemenus.utils import move_item, clean_ranks, move_item_or_clean_ranks


class TreemenusTestCase(TestCase):
    urls = 'treemenus.tests.urls'

    def setUp(self):
        # Install testapp
        self.old_INSTALLED_APPS = settings.INSTALLED_APPS
        settings.INSTALLED_APPS += ['treemenus.tests.fake_menu_extension']
        load_app('treemenus.tests.fake_menu_extension')
        call_command('syncdb', verbosity=0, interactive=False)

        # since django's r11862 templatags_modules and app_template_dirs are cached
        # the cache is not emptied between tests
        # clear out the cache of modules to load templatetags from so it gets refreshed
        template.templatetags_modules = []

        # clear out the cache of app_directories to load templates from so it gets refreshed
        app_directories.app_template_dirs = []
        # reload the module to refresh the cache
        reload(app_directories)
        # Log in as admin
        User.objects.create_superuser('super', 'super@test.com', 'secret')
        login = self.client.login(username='super', password='secret')
        self.assertEqual(login, True)

    def tearDown(self):
        # Restore settings
        settings.INSTALLED_APPS = self.old_INSTALLED_APPS

    def test_view_add_item(self):
        menu_data = {
            "name": "menu12387640",
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/add/', menu_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/')

        menu = Menu.objects.order_by('-pk')[0]

        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "blah",
            "url": "http://www.example.com"
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        # Make sure the 'menu' attribute has been set correctly
        menu_item = menu.root_item.children()[0]
        self.assertEqual(menu_item.menu, menu)

        # Save and continue editing
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "something0987456987546",
            "url": "http://www.example.com",
            "_continue": ''
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        new_menu_item = MenuItem.objects.order_by('-pk')[0]
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/%s/' % (menu.pk, new_menu_item.pk))

        # Save and add another
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "something",
            "url": "http://www.example.com",
            "_addanother": ''
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk)

    def test_view_history_item(self):
        menu_data = {
            "name": "menu4578756856",
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/add/', menu_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/')

        menu = Menu.objects.order_by('-pk')[0]

        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "blah",
            "url": "http://www.example.com"
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        menu_item = menu.root_item.children()[0]

        # Check if history is a valid page
        response = self.client.get('/test_treemenus_admin/treemenus/menu/%s/items/%s/history/' % (menu.pk, menu_item.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(smart_bytes('Change history') in response.content)

        if django.VERSION >= (1, 4):
            # Use reverse to get url as admin does when clicking on history button and check redirection
            response = self.client.get(reverse('admin:treemenus_menuitem_history', args=(menu_item.pk,)))
            self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/%s/history/' % (menu.pk, menu_item.pk),
                                 status_code=301)

    def test_view_delete_item(self):
        menu_data = {
            "name": "menu545468763498",
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/add/', menu_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/')

        menu = Menu.objects.order_by('-pk')[0]

        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "blah",
            "url": "http://www.example.com"
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        menu_item = menu.root_item.children()[0]

        # Delete item confirmation
        response = self.client.get('/test_treemenus_admin/treemenus/menu/%s/items/%s/delete/' % (menu.pk, menu_item.pk))
        self.assertEqual(response.request['PATH_INFO'], '/test_treemenus_admin/treemenus/menu/%s/items/%s/delete/' % (menu.pk, menu_item.pk))

        if django.VERSION >= (1, 4):
            # Use reverse to get url as admin does when clicking on delete button and check redirection
            response = self.client.get(reverse('admin:treemenus_menuitem_delete', args=(menu_item.pk,)))
            self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/%s/delete/' % (menu.pk, menu_item.pk),
                                 status_code=301)

        # Delete item for good
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/delete/' % (menu.pk, menu_item.pk), {'post': 'yes'})
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item.pk))

    def test_view_change_item(self):
        # Add the menu
        menu_data = {
            "name": "menu87623598762345",
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/add/', menu_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/')

        menu = Menu.objects.order_by('-pk')[0]

        # Add the item
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "blah",
            "url": "http://www.example.com"
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk, menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        menu_item = menu.root_item.children()[0]
        menu_item.menu = None  # Corrupt it!

        # Change the item
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "something else",
            "url": "http://www.example.com"
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/' % (menu.pk, menu_item.pk), menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        # Make sure the 'menu' attribute has been restored correctly
        menu_item = menu.root_item.children()[0]
        self.assertEqual(menu_item.menu, menu)

        # Save and continue editing
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "something else",
            "url": "http://www.example.com",
            "_continue": ''
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/' % (menu.pk, menu_item.pk), menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/%s/' % (menu.pk, menu_item.pk))

        # Save and add another
        menu_item_data = {
            "parent": menu.root_item.pk,
            "caption": "something else",
            "url": "http://www.example.com",
            "_addanother": ''
        }
        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/' % (menu.pk, menu_item.pk), menu_item_data)
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/items/add/' % menu.pk)

    def test_delete(self):
        menu = Menu(name='menu_delete')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu_item1)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu_item1)
        menu_item5 = MenuItem.objects.create(caption='menu_item5', parent=menu_item1)
        menu_item6 = MenuItem.objects.create(caption='menu_item6', parent=menu_item2)
        menu_item7 = MenuItem.objects.create(caption='menu_item7', parent=menu_item4)
        menu_item8 = MenuItem.objects.create(caption='menu_item8', parent=menu_item4)
        menu_item9 = MenuItem.objects.create(caption='menu_item9', parent=menu_item1)
        menu_item10 = MenuItem.objects.create(caption='menu_item10', parent=menu_item4)

        # menu
        #     ri
        #         mi1
        #             mi3
        #             mi4
        #                 mi7
        #                 mi8
        #                 mi10
        #             mi5
        #             mi9
        #         mi2
        #             mi6

        # Check initial ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 0)
        self.assertEqual(menu_item4.rank, 1)
        self.assertEqual(menu_item5.rank, 2)
        self.assertEqual(menu_item6.rank, 0)
        self.assertEqual(menu_item7.rank, 0)
        self.assertEqual(menu_item8.rank, 1)
        self.assertEqual(menu_item9.rank, 3)
        self.assertEqual(menu_item10.rank, 2)

        # Check initial levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 1)
        self.assertEqual(menu_item3.level, 2)
        self.assertEqual(menu_item4.level, 2)
        self.assertEqual(menu_item5.level, 2)
        self.assertEqual(menu_item6.level, 2)
        self.assertEqual(menu_item7.level, 3)
        self.assertEqual(menu_item8.level, 3)
        self.assertEqual(menu_item9.level, 2)
        self.assertEqual(menu_item10.level, 3)

        # Delete some items
        menu_item8.delete()
        menu_item3.delete()

        # menu
        #     ri
        #         mi1
        #             mi4
        #                 mi7
        #                 mi10
        #             mi5
        #             mi9
        #         mi2
        #             mi6

        # Refetch items from db
        menu_item1 = MenuItem.objects.get(pk=menu_item1.pk)
        menu_item2 = MenuItem.objects.get(pk=menu_item2.pk)
        menu_item4 = MenuItem.objects.get(pk=menu_item4.pk)
        menu_item5 = MenuItem.objects.get(pk=menu_item5.pk)
        menu_item6 = MenuItem.objects.get(pk=menu_item6.pk)
        menu_item7 = MenuItem.objects.get(pk=menu_item7.pk)
        menu_item9 = MenuItem.objects.get(pk=menu_item9.pk)
        menu_item10 = MenuItem.objects.get(pk=menu_item10.pk)

        # Check ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item4.rank, 0)
        self.assertEqual(menu_item5.rank, 1)
        self.assertEqual(menu_item6.rank, 0)
        self.assertEqual(menu_item7.rank, 0)
        self.assertEqual(menu_item9.rank, 2)
        self.assertEqual(menu_item10.rank, 1)

        # Check levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 1)
        self.assertEqual(menu_item4.level, 2)
        self.assertEqual(menu_item5.level, 2)
        self.assertEqual(menu_item6.level, 2)
        self.assertEqual(menu_item7.level, 3)
        self.assertEqual(menu_item9.level, 2)
        self.assertEqual(menu_item10.level, 3)

        # Delete some items
        menu_item4.delete()
        menu_item5.delete()

        # menu
        #     ri
        #         mi1
        #             mi9
        #         mi2
        #             mi6

        # Refetch items from db
        menu_item1 = MenuItem.objects.get(pk=menu_item1.pk)
        menu_item2 = MenuItem.objects.get(pk=menu_item2.pk)
        menu_item6 = MenuItem.objects.get(pk=menu_item6.pk)
        menu_item9 = MenuItem.objects.get(pk=menu_item9.pk)

        # Check ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item6.rank, 0)
        self.assertEqual(menu_item9.rank, 0)

        # Check levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 1)
        self.assertEqual(menu_item6.level, 2)
        self.assertEqual(menu_item9.level, 2)

        # Check that deleted items are in fact, gone.
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item3.pk))
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item4.pk))
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item5.pk))
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item7.pk))
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item8.pk))
        self.assertRaises(MenuItem.DoesNotExist, lambda: MenuItem.objects.get(pk=menu_item10.pk))

    def test_change_parents(self):
        menu = Menu(name='menu_change_parents')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu_item1)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu_item1)
        menu_item5 = MenuItem.objects.create(caption='menu_item5', parent=menu_item1)

        # menu
        #     ri
        #         mi1
        #             mi3
        #             mi4
        #             mi5
        #         mi2

        # Check initial ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 0)
        self.assertEqual(menu_item4.rank, 1)
        self.assertEqual(menu_item5.rank, 2)

        # Check initial levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 1)
        self.assertEqual(menu_item3.level, 2)
        self.assertEqual(menu_item4.level, 2)
        self.assertEqual(menu_item5.level, 2)

        # Change parent for some items
        menu_item4.parent = menu.root_item
        menu_item4.save()
        menu_item5.parent = menu_item2
        menu_item5.save()

        # menu
        #     ri
        #         mi1
        #             mi3
        #         mi2
        #             mi5
        #         mi4

        # Refetch items from db
        menu_item1 = MenuItem.objects.get(pk=menu_item1.pk)
        menu_item2 = MenuItem.objects.get(pk=menu_item2.pk)
        menu_item3 = MenuItem.objects.get(pk=menu_item3.pk)
        menu_item4 = MenuItem.objects.get(pk=menu_item4.pk)
        menu_item5 = MenuItem.objects.get(pk=menu_item5.pk)

        # Check ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 0)
        self.assertEqual(menu_item4.rank, 2)
        self.assertEqual(menu_item5.rank, 0)

        # Check levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 1)
        self.assertEqual(menu_item3.level, 2)
        self.assertEqual(menu_item4.level, 1)
        self.assertEqual(menu_item5.level, 2)

        # Change parent for some items
        menu_item2.parent = menu_item1
        menu_item2.save()
        menu_item5.parent = menu_item1
        menu_item5.save()
        menu_item3.parent = menu.root_item
        menu_item3.save()
        menu_item1.parent = menu_item4
        menu_item1.save()

        # menu
        #     ri
        #         mi4
        #             mi1
        #                 mi2
        #                 mi5
        #         mi3

        # Refetch items from db
        menu_item1 = MenuItem.objects.get(pk=menu_item1.pk)
        menu_item2 = MenuItem.objects.get(pk=menu_item2.pk)
        menu_item3 = MenuItem.objects.get(pk=menu_item3.pk)
        menu_item4 = MenuItem.objects.get(pk=menu_item4.pk)
        menu_item5 = MenuItem.objects.get(pk=menu_item5.pk)

        # Check ranks
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 0)
        self.assertEqual(menu_item3.rank, 1)
        self.assertEqual(menu_item4.rank, 0)
        self.assertEqual(menu_item5.rank, 1)

        # Check levels
        self.assertEqual(menu_item1.level, 2)
        self.assertEqual(menu_item2.level, 3)
        self.assertEqual(menu_item3.level, 1)
        self.assertEqual(menu_item4.level, 1)
        self.assertEqual(menu_item5.level, 3)

        # Change parent for some items
        menu_item2.parent = menu_item4
        menu_item2.save()
        menu_item4.parent = menu_item3
        menu_item4.save()
        menu_item1.parent = menu.root_item
        menu_item1.save()
        menu_item5.parent = menu_item4
        menu_item5.save()

        # menu
        #     ri
        #         mi3
        #             mi4
        #                 mi2
        #                 mi5
        #         mi1

        # Refetch items from db
        menu_item1 = MenuItem.objects.get(pk=menu_item1.pk)
        menu_item2 = MenuItem.objects.get(pk=menu_item2.pk)
        menu_item3 = MenuItem.objects.get(pk=menu_item3.pk)
        menu_item4 = MenuItem.objects.get(pk=menu_item4.pk)
        menu_item5 = MenuItem.objects.get(pk=menu_item5.pk)

        # Check ranks
        self.assertEqual(menu_item1.rank, 1)
        self.assertEqual(menu_item2.rank, 0)
        self.assertEqual(menu_item3.rank, 0)
        self.assertEqual(menu_item4.rank, 0)
        self.assertEqual(menu_item5.rank, 1)

        # Check levels
        self.assertEqual(menu_item1.level, 1)
        self.assertEqual(menu_item2.level, 3)
        self.assertEqual(menu_item3.level, 1)
        self.assertEqual(menu_item4.level, 2)
        self.assertEqual(menu_item5.level, 3)

    def test_move_up(self):
        menu = Menu(name='menu_move_up')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 2)
        self.assertEqual(menu_item4.rank, 3)

        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/move_up/' % (menu.pk, menu_item3.pk))
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        # Retrieve objects from db
        menu_item1 = MenuItem.objects.get(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.get(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.get(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.get(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 2)
        self.assertEqual(menu_item3.rank, 1)
        self.assertEqual(menu_item4.rank, 3)

        # Test forbidden move up
        self.assertRaises(MenuItem.DoesNotExist, lambda: move_item(menu_item1, -1))

    def test_move_down(self):
        menu = Menu(name='menu_move_down')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 2)
        self.assertEqual(menu_item4.rank, 3)

        response = self.client.post('/test_treemenus_admin/treemenus/menu/%s/items/%s/move_down/' % (menu.pk, menu_item3.pk))
        self.assertRedirects(response, '/test_treemenus_admin/treemenus/menu/%s/' % menu.pk)

        # Retrieve objects from db
        menu_item1 = MenuItem.objects.get(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.get(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.get(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.get(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 3)
        self.assertEqual(menu_item4.rank, 2)

        # Test forbidden move up
        self.assertRaises(MenuItem.DoesNotExist, lambda: move_item(menu_item3, 1))

    def test_clean_children_ranks(self):
        menu = Menu(name='menu_clean_children_ranks')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu.root_item)

        # Initial check
        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 2)
        self.assertEqual(menu_item4.rank, 3)

        # Mess up ranks
        menu_item1.rank = 99
        menu_item1.save()
        menu_item2.rank = -150
        menu_item2.save()
        menu_item3.rank = 3
        menu_item3.save()
        menu_item4.rank = 67
        menu_item4.save()

        clean_ranks(menu.root_item.children())

        # Retrieve objects from db
        menu_item1 = MenuItem.objects.get(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.get(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.get(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.get(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 3)
        self.assertEqual(menu_item2.rank, 0)
        self.assertEqual(menu_item3.rank, 1)
        self.assertEqual(menu_item4.rank, 2)

    def test_move_item_or_clean_ranks(self):
        menu = Menu(name='menu_move_item_or_clean_ranks')
        menu.save()
        menu_item1 = MenuItem.objects.create(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.create(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.create(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.create(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 1)
        self.assertEqual(menu_item3.rank, 2)
        self.assertEqual(menu_item4.rank, 3)

        # Corrupt ranks
        menu_item1.rank = 0
        menu_item1.save()
        menu_item2.rank = 0
        menu_item2.save()
        menu_item3.rank = 0
        menu_item3.save()
        menu_item4.rank = 0
        menu_item4.save()

        move_item_or_clean_ranks(menu_item3, -1)  # Move up

        # Retrieve objects from db
        menu_item1 = MenuItem.objects.get(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.get(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.get(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.get(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 0)
        self.assertEqual(menu_item2.rank, 2)
        self.assertEqual(menu_item3.rank, 1)
        self.assertEqual(menu_item4.rank, 3)

        # Corrupt ranks
        menu_item1.rank = 18
        menu_item1.save()
        menu_item2.rank = -1
        menu_item2.save()
        menu_item3.rank = 6
        menu_item3.save()
        menu_item4.rank = 99
        menu_item4.save()

        move_item_or_clean_ranks(menu_item1, 1)  # Try to move down

        # Retrieve objects from db
        menu_item1 = MenuItem.objects.get(caption='menu_item1', parent=menu.root_item)
        menu_item2 = MenuItem.objects.get(caption='menu_item2', parent=menu.root_item)
        menu_item3 = MenuItem.objects.get(caption='menu_item3', parent=menu.root_item)
        menu_item4 = MenuItem.objects.get(caption='menu_item4', parent=menu.root_item)

        self.assertEqual(menu_item1.rank, 3)
        self.assertEqual(menu_item2.rank, 0)
        self.assertEqual(menu_item3.rank, 1)
        self.assertEqual(menu_item4.rank, 2)

    def test_menu_create(self):
        # Regression test for issue #18
        # http://code.google.com/p/django-treemenus/issues/detail?id=18
        menu = Menu.objects.create(name="menu_created_with_force_insert_True")

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include
except ImportError:  # Django < 1.4
    from django.conf.urls.defaults import patterns, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
        (r'^test_treemenus_admin/', include(admin.site.urls)),
    )

handler500 = 'django.views.defaults.server_error'
########NEW FILE########
__FILENAME__ = utils
from django.utils.safestring import mark_safe
from django.forms import ChoiceField

from treemenus.models import MenuItem


class MenuItemChoiceField(ChoiceField):
    ''' Custom field to display the list of items in a tree manner '''
    def clean(self, value):
        return MenuItem.objects.get(pk=value)


def move_item(menu_item, vector):
    ''' Helper function to move and item up or down in the database '''
    old_rank = menu_item.rank
    swapping_sibling = MenuItem.objects.get(parent=menu_item.parent, rank=old_rank + vector)
    new_rank = swapping_sibling.rank
    swapping_sibling.rank = old_rank
    menu_item.rank = new_rank
    menu_item.save()
    swapping_sibling.save()


def move_item_or_clean_ranks(menu_item, vector):
    ''' Helper function to move and item up or down in the database.
        If the moving fails, we assume that the ranks were corrupted,
        so we clean them and try the moving again.
    '''
    try:
        move_item(menu_item, vector)
    except MenuItem.DoesNotExist:
        if menu_item.parent:
            clean_ranks(menu_item.parent.children())
            fresh_menu_item = MenuItem.objects.get(pk=menu_item.pk)
            move_item(fresh_menu_item, vector)


def get_parent_choices(menu, menu_item=None):
    """
    Returns flat list of tuples (possible_parent.pk, possible_parent.caption_with_spacer).
    If 'menu_item' is not given or None, returns every item of the menu. If given, intentionally omit it and its descendant in the list.
    """
    def get_flat_tuples(menu_item, excepted_item=None):
        if menu_item == excepted_item:
            return []
        else:
            choices = [(menu_item.pk, mark_safe(menu_item.caption_with_spacer()))]
            if menu_item.has_children():
                for child in menu_item.children():
                    choices += get_flat_tuples(child, excepted_item)
            return choices

    return get_flat_tuples(menu.root_item, menu_item)


def clean_ranks(menu_items):
    """
    Resets ranks from 0 to n, n being the number of items.
    """
    rank = 0
    for menu_item in menu_items:
        menu_item.rank = rank
        menu_item.save()
        rank += 1

########NEW FILE########
