__FILENAME__ = admin
from functools import update_wrapper

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.util import unquote, quote
from django.conf.urls import url

from . import util


class DjangoMpttAdmin(admin.ModelAdmin):
    tree_auto_open = 1
    tree_load_on_demand = 1
    trigger_save_after_move = False

    change_list_template = 'django_mptt_admin/grid_view.html'

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        if not self.has_change_permission(request, None):
            raise PermissionDenied()

        change_list = self.get_change_list_for_tree(request)

        context = dict(
            title=change_list.title,
            app_label=self.model._meta.app_label,
            model_name=util.get_model_name(self.model),
            cl=change_list,
            media=self.media,
            has_add_permission=self.has_add_permission(request),
            tree_auto_open=util.get_javascript_value(self.tree_auto_open),
            tree_json_url=self.get_admin_url('tree_json'),
            grid_url=self.get_admin_url('grid'),
        )

        # Django 1.7
        if hasattr(self.admin_site, 'each_context'):
            context.update(self.admin_site.each_context())

        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            'django_mptt_admin/change_list.html',
            context
        )

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = super(DjangoMpttAdmin, self).get_urls()

        def add_url(regex, url_name, view):
            # Prepend url to list so it has preference before 'change' url
            urlpatterns.insert(
                0,
                url(
                    regex,
                    wrap(view),
                    name='%s_%s_%s' % (
                        self.model._meta.app_label,
                        util.get_model_name(self.model),
                        url_name
                    )
                )
            )

        add_url(r'^(.+)/move/$', 'move', self.move_view)
        add_url(r'^tree_json/$', 'tree_json', self.tree_json_view)
        add_url(r'^grid/$', 'grid', self.grid_view)
        return urlpatterns

    @csrf_protect_m
    @util.django_atomic()
    def move_view(self, request, object_id):
        instance = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, instance):
            raise PermissionDenied()

        if request.method != 'POST':
            raise SuspiciousOperation()

        target_id = request.POST['target_id']
        position = request.POST['position']
        target_instance = self.get_object(request, target_id)

        if position == 'before':
            instance.move_to(target_instance, 'left')
        elif position == 'after':
            instance.move_to(target_instance, 'right')
        elif position == 'inside':
            instance.move_to(target_instance)
        else:
            raise Exception('Unknown position')

        if self.trigger_save_after_move:
            instance.save()

        return util.JsonResponse(
            dict(success=True)
        )

    def get_change_list_for_tree(self, request):
        kwargs = dict(
            request=request,
            model=self.model,
            list_display=(),
            list_display_links=(),
            list_filter=(),
            date_hierarchy=None,
            search_fields=(),
            list_select_related=(),
            list_per_page=100,
            list_editable=(),
            model_admin=self,
            list_max_show_all=200,
        )

        return ChangeList(**kwargs)

    def get_changelist(self, request, **kwargs):
        if util.get_short_django_version() >= (1, 5):
            return super(DjangoMpttAdmin, self).get_changelist(request, **kwargs)
        else:
            return FixedChangeList

    def get_admin_url(self, name, args=None):
        opts = self.model._meta
        url_name = 'admin:%s_%s_%s' % (opts.app_label, util.get_model_name(self.model), name)

        return reverse(
            url_name,
            args=args,
            current_app=self.admin_site.name
        )

    def get_tree_data(self, qs, max_level):
        pk_attname = self.model._meta.pk.attname

        def handle_create_node(instance, node_info):
            pk = quote(getattr(instance, pk_attname))

            node_info.update(
                url=self.get_admin_url('change', (quote(pk),)),
                move_url=self.get_admin_url('move', (quote(pk),))
            )

        return util.get_tree_from_queryset(qs, handle_create_node, max_level)

    def tree_json_view(self, request):
        node_id = request.GET.get('node')

        if node_id:
            node = self.model.objects.get(id=node_id)
            max_level = node.level + 1
        else:
            max_level = self.tree_load_on_demand

        qs = util.get_tree_queryset(
            model=self.model,
            node_id=node_id,
            selected_node_id=request.GET.get('selected_node'),
            max_level=max_level,
        )

        tree_data = self.get_tree_data(qs, max_level)
        return util.JsonResponse(tree_data)

    def grid_view(self, request):
        return super(DjangoMpttAdmin, self).changelist_view(
            request,
            dict(tree_url=self.get_admin_url('changelist'))
        )


class FixedChangeList(ChangeList):
    """
    Fix issue 1: the changelist must have a correct link to the edit page
    """
    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)

        return reverse(
            'admin:%s_%s_change' % (self.opts.app_label, self.opts.module_name),
            args=[quote(pk)],
            current_app=self.model_admin.admin_site.name
        )

########NEW FILE########
__FILENAME__ = util
import json

import six

import django
from django.http import HttpResponse
from django.db.models import Q
from django.db import transaction


def get_tree_from_queryset(queryset, on_create_node=None, max_level=None):
    """
    Return tree data that is suitable for jqTree.
    The queryset must be sorted by 'tree_id' and 'left' fields.
    """
    pk_attname = queryset.model._meta.pk.attname

    def serialize_id(pk):
        if isinstance(pk, six.integer_types + six.string_types):
            return pk
        else:
            # Nb. special case for uuid field
            return str(pk)

    # Result tree
    tree = []

    # Dict of all nodes; used for building the tree
    # - key is node id
    # - value is node info (label, id)
    node_dict = dict()

    # The lowest level of the tree; used for building the tree
    # - Initial value is None; set later
    # - For the whole tree this is 0, for a subtree this is higher
    min_level = None

    for instance in queryset:
        if min_level is None:
            min_level = instance.level

        pk = getattr(instance, pk_attname)
        node_info = dict(
            label=six.text_type(instance),
            id=serialize_id(pk)
        )
        if on_create_node:
            on_create_node(instance, node_info)

        if max_level is not None and not instance.is_leaf_node():
            # If there is a maximum level and this node has children, then initially set property 'load_on_demand' to true.
            node_info['load_on_demand'] = True

        if instance.level == min_level:
            # This is the lowest level. Skip finding a parent.
            # Add node to the tree
            tree.append(node_info)
        else:
            # NB: Use parent.id instead of parent_id for consistent values for uuid
            parent_id = instance.parent.id

            # Get parent from node dict
            parent_info = node_dict.get(parent_id)

            # Check for corner case: parent is deleted.
            if parent_info:
                if 'children' not in parent_info:
                    parent_info['children'] = []

                # Add node to the tree
                parent_info['children'].append(node_info)

                # If there is a maximum level, then reset property 'load_on_demand' for parent
                if max_level is not None:
                    parent_info['load_on_demand'] = False

        # Update node dict
        node_dict[pk] = node_info

    return tree


def get_tree_queryset(model, node_id=None, selected_node_id=None, max_level=None, include_root=True):
    if node_id:
        node = model.objects.get(id=node_id)
        max_level = node.level + 1
        qs = node.get_descendants().filter(level__lte=max_level)
    else:
        qs = model._default_manager.all()

        if isinstance(max_level, int):
            max_level_filter = Q(level__lte=max_level)

            selected_node = None
            if selected_node_id:
                selected_node_qs = model._default_manager.filter(pk=selected_node_id)

                if selected_node_qs.exists():
                    selected_node = selected_node_qs.get()

            if not (selected_node and selected_node.level > max_level):
                qs = qs.filter(max_level_filter)
            else:
                qs_parents = selected_node.get_ancestors(include_self=True)
                parents_filter = Q(parent__in=qs_parents)
                qs = qs.filter(max_level_filter | parents_filter)

        if not include_root:
            qs = qs.exclude(level=0)

    return qs.order_by('tree_id', 'lft')


def get_javascript_value(value):
    """
    Get javascript value for python value.

    >>> get_javascript_value(True)
    true
    >>> get_javascript_value(10)
    10
    """
    if isinstance(value, bool):
        if value:
            return 'true'
        else:
            return 'false'
    else:
        return json.dumps(value)


class JsonResponse(HttpResponse):
    def __init__(self, data, status=None):
        super(JsonResponse, self).__init__(
            json.dumps(data),
            'application/json',
            status
        )


def get_short_django_version():
    """
    Get first two numbers of Django version.
    E.g. (1, 5)
    """
    return django.VERSION[0:2]


def django_atomic():
    if get_short_django_version() >= (1, 6):
        return transaction.atomic
    else:
        return transaction.commit_on_success


def get_model_name(model):
    if get_short_django_version() >= (1, 6):
        return model._meta.model_name
    else:
        return model._meta.module_name

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from django_mptt_admin.admin import DjangoMpttAdmin

from .models import Country


class CountryAdmin(DjangoMpttAdmin):
    tree_auto_open = 0
    list_display = ('code', 'name')
    ordering = ('name',)


admin.site.register(Country, CountryAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from mptt.models import MPTTModel, TreeForeignKey


class Country(MPTTModel):
    class Meta:
        verbose_name_plural = 'countries'

    code = models.CharField(max_length=2, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.name or self.code or ''

    def __str__(self):
        return self.__unicode__()

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User

from django_webtest import WebTest

from .models import Country


class DjangoMpttAdminWebTests(WebTest):
    fixtures = ['initial_data.json']

    def setUp(self):
        super(DjangoMpttAdminWebTests, self).setUp()

        USERNAME = 'admin'
        PASSWORD = 'p'

        self.admin = User.objects.create_superuser(USERNAME, 'admin@admin.com', PASSWORD)
        self.login(USERNAME, PASSWORD)

    def test_tree_view(self):
        # - get countries admin page
        countries_page = self.app.get('/django_mptt_example/country/')
        tree_element = countries_page.pyquery('#tree')

        # check savestate key
        self.assertEqual(tree_element.attr('data-save_state'), 'django_mptt_example_country')

        # check url
        json_url = tree_element.attr('data-url')
        self.assertEqual(json_url, '/django_mptt_example/country/tree_json/')

    def test_load_json(self):
        base_url = '/django_mptt_example/country/tree_json/'

        # -- load json
        json_data = self.app.get(base_url).json

        self.assertEqual(len(json_data), 1)

        root = json_data[0]
        self.assertEqual(root['label'], 'root')
        self.assertEqual(len(root['children']), 7)

        africa_id = Country.objects.get(name='Africa').id

        africa = root['children'][0]
        self.assertEqual(
            africa,
            dict(
                label='Africa',
                id=africa_id,
                url='/django_mptt_example/country/%d/' % africa_id,
                move_url='/django_mptt_example/country/%d/move/' % africa_id,
                load_on_demand=True,
            )
        )

        # no children loaded beyond level 1
        self.assertFalse(hasattr(africa, 'children'))

        # -- load json with node 'Netherlands' selected
        netherlands_id = Country.objects.get(name='Netherlands').id

        json_data = self.app.get(
            '%s?selected_node=%d' % (base_url, netherlands_id)
        ).json

        root = json_data[0]

        africa = root['children'][0]
        self.assertEqual(africa['label'], 'Africa')
        self.assertFalse(hasattr(africa, 'children'))
        self.assertTrue(africa['load_on_demand'])

        europe = root['children'][3]
        self.assertEqual(europe['label'], 'Europe')

        self.assertEqual(len(europe['children']), 50)

        # -- load subtree
        json_data = self.app.get('%s?node=%d' % (base_url, africa_id)).json

        self.assertEqual(len(json_data), 58)
        self.assertEqual(json_data[0]['label'], 'Algeria')

        # -- issue 8; selected node does not exist
        self.app.get('%s?selected_node=9999999' % base_url)

    def test_grid_view(self):
        # - get grid page
        grid_page = self.app.get('/django_mptt_example/country/grid/')

        # get row with 'Africa'
        row_index = 0

        first_row = grid_page.pyquery('#result_list tbody tr').eq(row_index)

        # 'name' column
        self.assertEqual(first_row.find('td').eq(1).text(), 'Afghanistan')

        # 'code' column
        self.assertEqual(first_row.find('th').text(), 'AF')

        # link to edit page
        afghanistan_id = Country.objects.get(name='Afghanistan').id

        self.assertEqual(first_row.find('a').attr('href'), '/django_mptt_example/country/%d/' % afghanistan_id)

    def test_move_view(self):
        # setup
        bouvet_island = Country.objects.get(code='BV')
        oceania = Country.objects.get(name='Oceania')

        # - move Bouvet Island under Oceania
        countries_page = self.app.get('/django_mptt_example/country/')
        csrf_token = countries_page.form['csrfmiddlewaretoken'].value

        response = self.app.post(
            '/django_mptt_example/country/%d/move/' % bouvet_island.id,
            dict(
                csrfmiddlewaretoken=csrf_token,
                target_id=oceania.id,
                position='inside',
            )
        )
        self.assertEqual(response.json, dict(success=True))

    def login(self, username, password):
        login_page = self.app.get('/', auto_follow=True)
        form = login_page.form

        form['username'] = username
        form['password'] = password

        response = form.submit().follow()
        self.assertEqual(response.context['user'].username, 'admin')

########NEW FILE########
__FILENAME__ = settings
import os
import sys


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

sys.path.append(
    os.path.join(os.path.dirname(BASE_DIR))
)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = dict(
    default=dict(
        ENGINE='django.db.backends.sqlite3',
        NAME='example.db',
        USER='',
        PASSWORD='',
        HOST='',
        PORT='',
    )
)

INSTALLED_APPS = [
    # Project app
    'django_mptt_example',

    # Generic apps
    'mptt',
    'django_mptt_admin',

    # Django
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
]

STATIC_URL = '/static/'
ROOT_URLCONF = 'example_project.urls'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# django jenkins settings
try:
    import django_jenkins
    INSTALLED_APPS.append('django_jenkins')
except ImportError:
    pass

PROJECT_APPS = ['django_mptt_admin', 'django_mptt_example']

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
)

SECRET_KEY = 'secret'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
