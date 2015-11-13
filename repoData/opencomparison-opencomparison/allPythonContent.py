__FILENAME__ = api
"""The ``Api`` definition module"""
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from tastypie.api import Api as TastyPieApi
from tastypie.serializers import Serializer
from tastypie.utils.mime import build_content_type


class Api(TastyPieApi):
    """A sub-class of ``TastyPieApi`` -
    the actual Api class
    """

    def top_level(self, request, api_name=None):
        """
        A view that returns a serialized list of all resources registered
        to the ``Api``. Useful for the resource discovery.
        """
        serializer = Serializer()
        available_resources = {}

        if api_name is None:
            api_name = self.api_name

        for name in sorted(self._registry.keys()):
            available_resources[name] = reverse("api_dispatch_list", kwargs={
                'api_name': api_name,
                'resource_name': name,
            })

        desired_format = "application/json"
        serialized = serializer.serialize(available_resources, desired_format)
        return HttpResponse(content=serialized, content_type=build_content_type(desired_format))

########NEW FILE########
__FILENAME__ = models
# boilerplate

########NEW FILE########
__FILENAME__ = resources
"""``Api`` resource definition module.

All of the resource classes in this module are registered with
the :class:`~apiv1.api.Api` in the main :mod:`urls.py <urls>`.
"""
from django.conf.urls import url
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from tastypie import fields
from tastypie.bundle import Bundle
from tastypie.exceptions import NotFound
from tastypie.resources import ModelResource, ALL_WITH_RELATIONS

from grid.models import Grid
from homepage.models import Dpotw, Gotw
from package.models import Package, Category


# TODO - exclude ID, and other fields not yet used

class BaseResource(ModelResource):
    """Base resource class - a subclass of tastypie's ``ModelResource``"""

    def determine_format(self, *args, **kwargs):
        """defines all resources as returning json data"""

        return "application/json"


class EnhancedModelResource(BaseResource):
    def obj_get(self, **kwargs):
        """
        A ORM-specific implementation of ``obj_get``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        lookup_field = getattr(self._meta, 'lookup_field', 'pk')
        try:
            return self._meta.queryset.get(**{lookup_field: kwargs['pk']})
        except ValueError:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")

    def get_resource_value(self, obj):
        lookup_field = getattr(self._meta, 'lookup_field', 'pk')
        lookups = lookup_field.split('__')
        for lookup in lookups:
            obj = getattr(obj, lookup)
        return obj

    def get_resource_uri(self, bundle_or_obj):
        """
        Handles generating a resource URI for a single resource.

        Uses the model's ``pk`` in order to create the URI.
        """
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = self.get_resource_value(bundle_or_obj.obj)
        else:
            kwargs['pk'] = self.get_resource_value(bundle_or_obj)

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return reverse("api_dispatch_detail", kwargs=kwargs)


class PackageResourceBase(EnhancedModelResource):

    class Meta:
        queryset = Package.objects.all()
        resource_name = 'package'
        allowed_methods = ['get']
        include_absolute_url = True
        lookup_field = 'slug'


class GridResource(EnhancedModelResource):
    """Provides information about the grid.
    Pulls data from the :class:`~grid.models.Grid` model.
    """

    packages = fields.ToManyField(PackageResourceBase, "packages")

    class Meta:
        queryset = Grid.objects.all()
        resource_name = 'grid'
        allowed_methods = ['get']
        include_absolute_url = True
        lookup_field = 'slug'
        excludes = ["id"]

    def override_urls(self):
        return [
            url(
                r"^%s/(?P<grid_name>[-\w]+)/packages/$" % GridResource._meta.resource_name,
                self.get_packages,
                name='api_grid_packages',
            ),
        ]

    def get_packages(self, request, **kwargs):
        """
        Returns a serialized list of resources based on the identifiers
        from the URL.

        Pulls the data from the model :class:`~package.models.Package`.

        Calls ``obj_get`` to fetch only the objects requested. This method
        only responds to HTTP GET.

        Should return a ``HttpResponse`` (200 OK).
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        qs = Package.objects.filter(grid__slug=kwargs['grid_name'])
        pkg = PackageResource()
        object_list = [pkg.full_dehydrate(obj) for obj in qs]

        self.log_throttled_access(request)
        return self.create_response(request, object_list)


class DpotwResource(ModelResource):
    """Package of the week resource.
    Pulls data from :class:`~homepage.models.Dpotw`.
    """

    class Meta:
        queryset = Dpotw.objects.all()
        resource_name = 'package-of-the-week'
        allowed_methods = ['get']
        include_absolute_url = True
        lookup_field = 'package__slug'
        excludes = ["id"]


class GotwResource(EnhancedModelResource):
    """Grid of the week resource.
    The data comes from :class:`~homepage.models.GotwResource`
    """

    class Meta:
        queryset = Gotw.objects.all()
        resource_name = 'grid-of-the-week'
        allowed_methods = ['get']
        include_absolute_url = True
        lookup_field = 'grid__slug'
        excludes = ["id"]


class CategoryResource(EnhancedModelResource):
    """Category resource.
    The data is from :class:`~package.models.Category`.
    """

    class Meta:
        queryset = Category.objects.all()
        resource_name = 'category'
        allowed_methods = ['get']
        lookup_field = 'slug'
        excludes = ["id"]


class UserResource(EnhancedModelResource):
    """User resource.
    The data is from the :class:`contrib.auth.models.User`.
    Exposes ``last_login``, ``username`` and ``date_joined``.
    """

    class Meta:
        queryset = User.objects.all().order_by("-id")
        resource_name = 'user'
        allowed_methods = ['get']
        lookup_field = 'username'
        fields = ["resource_uri", "last_login", "username", "date_joined"]


class PackageResource(PackageResourceBase):
    """Package resource.
    Pulls data from :class:`~package.models.Package` and provides
    additional related data:

    * :attr:`category`
    * :attr:`grids`
    * :attr:`created_by`
    * :attr:`last_modified_by`
    * :attr:`pypi_vesion`
    """

    category = fields.ForeignKey(CategoryResource, "category")
    grids = fields.ToManyField(GridResource, "grid_set")
    created_by = fields.ForeignKey(UserResource, "created_by", null=True)
    last_modified_by = fields.ForeignKey(UserResource, "created_by", null=True)
    pypi_version = fields.CharField('pypi_version')
    commits_over_52 = fields.CharField('commits_over_52')
    usage_count = fields.CharField('get_usage_count')

    class Meta:
        queryset = Package.objects.all()
        resource_name = 'package'
        allowed_methods = ['get']
        include_absolute_url = True
        lookup_field = 'slug'
        filtering = {
            "category": ALL_WITH_RELATIONS
        }

########NEW FILE########
__FILENAME__ = data
from grid.models import Grid
from django.contrib.auth.models import Group, User, Permission
from package.models import Category, PackageExample, Package
from grid.models import Element, Feature, GridPackage
from core.tests import datautil


def load():
    category, created = Category.objects.get_or_create(
        pk=1,
        slug=u'apps',
        title=u'App',
        description=u'Small components used to build projects.',
    )

    package1, created = Package.objects.get_or_create(
        pk=1,
        category=category,
        repo_watchers=0,
        title=u'Testability',
        pypi_url='',
        participants=u'malcomt,jacobian',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-la-facebook',
        repo_forks=0,
        slug=u'testability',
        repo_description=u'Increase your testing ability with this steroid free supplement.',
    )
    package2, created = Package.objects.get_or_create(
        pk=2,
        category=category,
        repo_watchers=0,
        title=u'Supertester',
        pypi_url='',
        participants=u'thetestman',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-uni-form',
        
        repo_forks=0,
        slug=u'supertester',
        repo_description=u'Test everything under the sun with one command!',
    )
    package3, created = Package.objects.get_or_create(
        pk=3,
        category=category,
        repo_watchers=0,
        title=u'Serious Testing',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/opencomparison/opencomparison',
        
        repo_forks=0,
        slug=u'serious-testing',
        repo_description=u'Make testing as painless as waxing your legs.',
    )
    package4, created = Package.objects.get_or_create(
        pk=4,
        category=category,
        repo_watchers=0,
        title=u'Another Test',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/djangopackages/djangopackages',
        
        repo_forks=0,
        slug=u'another-test',
        repo_description=u'Yet another test package, with no grid affiliation.',
    )

    grid1, created = Grid.objects.get_or_create(
        pk=1,
        description=u'A grid for testing.',
        title=u'Testing',
        is_locked=False,
        slug=u'testing',
    )
    grid2, created = Grid.objects.get_or_create(
        pk=2,
        description=u'Another grid for testing.',
        title=u'Another Testing',
        is_locked=False,
        slug=u'another-testing',
    )

    gridpackage1, created = GridPackage.objects.get_or_create(
        pk=1,
        package=package1,
        grid=grid1,
    )
    gridpackage2, created = GridPackage.objects.get_or_create(
        pk=2,
        package=package1,
        grid=grid1,
    )
    gridpackage3, created = GridPackage.objects.get_or_create(
        pk=3,
        package=package3,
        grid=grid1,
    )
    gridpackage4, created = GridPackage.objects.get_or_create(
        pk=4,
        package=package3,
        grid=grid2,
    )
    gridpackage5, created = GridPackage.objects.get_or_create(
        pk=5,
        package=package2,
        grid=grid1,
    )

    feature1, created = Feature.objects.get_or_create(
        pk=1,
        title=u'Has tests?',
        grid=grid1,
        description=u'Does this package come with tests?',
    )
    feature2, created = Feature.objects.get_or_create(
        pk=2,
        title=u'Coolness?',
        grid=grid1,
        description=u'Is this package cool?',
    )

    element, created = Element.objects.get_or_create(
        pk=1,
        text=u'Yes',
        feature=feature1,
        grid_package=gridpackage1,
    )

    group1, created = Group.objects.get_or_create(
        pk=1,
        name=u'Moderators',
        #permissions=[[u'delete_gridpackage', u'grid', u'gridpackage'], [u'delete_feature', u'grid', u'feature']],
    )
    group1.permissions.clear()
    group1.permissions = [
        Permission.objects.get(codename='delete_gridpackage'),
        Permission.objects.get(codename='delete_feature')
        ]

    user1, created = User.objects.get_or_create(
        pk=1,
        username=u'user',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$644c9$347f3dd85fb609a5745ebe33d0791929bf08f22e',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2, created = User.objects.get_or_create(
        pk=2,
        username=u'cleaner',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        #groups=[group1],
        password=u'sha1$e6fe2$78b744e21cddb39117997709218f4c6db4e91894',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2.groups = [group1]

    user3, created = User.objects.get_or_create(
        pk=3,
        username=u'staff',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$8894d$c4814980edd6778f0ab1632c4270673c0fd40efe',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user4, created = User.objects.get_or_create(
        pk=4,
        username=u'admin',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$52c7f$59b4f64ffca593e6abd23f90fd1f95cf71c367a4',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )

    packageexample, created = PackageExample.objects.get_or_create(
        pk=1,
        package=package1,
        url=u'http://www.example.com/',
        active=True,
        title=u'www.example.com',
    )

    datautil.reset_sequences(Grid, Group, User, Permission, Category, PackageExample,
                             Package, Element, Feature, GridPackage)

########NEW FILE########
__FILENAME__ = test_grid
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from grid.models import Grid, GridPackage
from package.models import Package, Category
import json


class GridV1Tests(TestCase):
    def setUp(self):
        """
        Set up initial data, done through Python because fixtures break way too
        quickly with migrations and are terribly hard to maintain.
        """
        app = Category.objects.create(
            title='App',
            slug='app',
        )
        self.grid = Grid.objects.create(
            title='A Grid',
            slug='grid',
        )
        self.pkg1 = Package.objects.create(
            title='Package1',
            slug='package1',
            category=app,
            repo_url='https://github.com/pydanny/django-uni-form'
        )
        self.pkg2 = Package.objects.create(
            title='Package2',
            slug='package2',
            category=app,
            repo_url='https://github.com/opencomparison/opencomparison'
        )
        GridPackage.objects.create(package=self.pkg1, grid=self.grid)
        GridPackage.objects.create(package=self.pkg2, grid=self.grid)
        user = User.objects.create_user('user', 'user@opencomparison.com', 'user')
        self.pkg1.usage.add(user)

    def test_01_grid_packages_usage(self):
        urlkwargs = {'api_name': 'v1', 'grid_name': self.grid.slug}
        url = reverse('api_grid_packages', kwargs=urlkwargs)
        response = self.client.get(url)
        # check that the request was successful
        self.assertEqual(response.status_code, 200)
        raw_json = response.content
        package_list = json.loads(raw_json)
        # turn the flat package list into a dictionary with the package slug as
        # key for easier assertion of data integrity
        package_dict = dict([(pkg['slug'], pkg) for pkg in package_list])
        pkg1_usage_count = int(package_dict[self.pkg1.slug]['usage_count'])
        pkg2_usage_count = int(package_dict[self.pkg2.slug]['usage_count'])
        self.assertEqual(pkg1_usage_count, self.pkg1.usage.count())
        self.assertEqual(pkg2_usage_count, self.pkg2.usage.count())

########NEW FILE########
__FILENAME__ = test_package
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from grid.models import Grid, GridPackage
from package.models import Package, Category
import json
from requests.compat import urlencode




class PackageV1Tests(TestCase):
    def setUp(self):
        """
        Set up initial data, done through Python because fixtures break way too
        quickly with migrations and are terribly hard to maintain.
        """
        self.app = Category.objects.create(
            title='App',
            slug='app',
        )
        self.framework = Category.objects.create(
            title='Framework',
            slug='framework',
        )
        self.grid = Grid.objects.create(
            title='A Grid',
            slug='grid',
        )
        self.pkg1 = Package.objects.create(
            title='Package1',
            slug='package1',
            category=self.app,
            repo_url='https://github.com/pydanny/django-uni-form'
        )
        self.pkg2 = Package.objects.create(
            title='Package2',
            slug='package2',
            category=self.app,
            repo_url='https://github.com/cartwheelweb/opencomparison'  
        )
        self.pkg3 = Package.objects.create(
            title='Package3',
            slug='package3',
            category=self.framework,
            repo_url='https://github.com/divio/django-cms'
        )
        GridPackage.objects.create(package=self.pkg1, grid=self.grid)
        GridPackage.objects.create(package=self.pkg2, grid=self.grid)
        user = User.objects.create_user('user', 'user@opencomparison.com', 'user')
        self.pkg1.usage.add(user)

    def test_01_packages_usage(self):
        urlkwargs_pkg1 = {
            'api_name': 'v1',
            'resource_name': 'package',
            'pk': self.pkg1.slug,
        }
        url_pkg1 = reverse('api_dispatch_detail', kwargs=urlkwargs_pkg1)
        response_pkg1 = self.client.get(url_pkg1)
        # check that the request was successful
        self.assertEqual(response_pkg1.status_code, 200)
        # check that we have a usage_count equal to the one in the DB
        raw_json_pkg1 = response_pkg1.content
        pkg_1 = json.loads(raw_json_pkg1)
        usage_count_pkg1 = int(pkg_1['usage_count'])
        self.assertEqual(usage_count_pkg1, self.pkg1.usage.count())
        # do the same with pkg2
        urlkwargs_pkg2 = {
            'api_name': 'v1',
            'resource_name': 'package',
            'pk': self.pkg2.slug,
        }
        url_pkg2 = reverse('api_dispatch_detail', kwargs=urlkwargs_pkg2)
        response_pkg2 = self.client.get(url_pkg2)
        # check that the request was successful
        self.assertEqual(response_pkg2.status_code, 200)
        # check that we have a usage_count equal to the one in the DB
        raw_json_pkg2 = response_pkg2.content
        pkg_2 = json.loads(raw_json_pkg2)
        usage_count_pkg2 = int(pkg_2['usage_count'])
        self.assertEqual(usage_count_pkg2, self.pkg2.usage.count())

    def test_02_category_packages(self):
        urlkwargs_pkg_list = {
            'api_name': 'v1',
            'resource_name': 'package',
        }
        querystring_filter_app = {
            'category__slug': self.app.slug
        }
        url_app_pkg = "%s?%s" % (reverse('api_dispatch_list',
            kwargs=urlkwargs_pkg_list), urlencode(querystring_filter_app))
        response_app_pkg = self.client.get(url_app_pkg)
        # check that the request was successful
        self.assertEqual(response_app_pkg.status_code, 200)
        # check that we have correct number of packages in filter
        raw_json_app_pkg = response_app_pkg.content
        app_pkg = json.loads(raw_json_app_pkg)
        app_pkg_count = int(app_pkg['meta']['total_count'])
        self.assertEqual(app_pkg_count, self.app.package_set.count())
        # Check that we have filter applied correclty
        app_package_slug_list = self.app.package_set.values_list('slug', flat=True)
        self.assertIn(self.pkg1.slug, app_package_slug_list)
        self.assertIn(self.pkg2.slug, app_package_slug_list)

########NEW FILE########
__FILENAME__ = test_resources
from django.test import TestCase
from django.core.urlresolvers import reverse
from apiv1.tests import data


class ResourcesV1Tests(TestCase):
    base_kwargs = {'api_name': 'v1'}

    def setUp(self):
        data.load()

    def test_01_category(self):
        kwargs = {'resource_name': 'category'}
        kwargs.update(self.base_kwargs)
        # check 200's
        list_url = reverse('api_dispatch_list', kwargs=kwargs)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        kwargs['pk'] = 'apps'
        cat_url = reverse('api_dispatch_detail', kwargs=kwargs)
        self.assertTrue(cat_url in response.content)
        response = self.client.get(cat_url)
        self.assertEqual(response.status_code, 200)

        query_filter = "?category__slug=apps"
        cat_filter_url = "%s%s" % (list_url, query_filter)
        response = self.client.get(cat_url)
        self.assertEqual(response.status_code, 200)

    def test_02_grid(self):
        kwargs = {'resource_name': 'grid'}
        kwargs.update(self.base_kwargs)
        # check 200's
        list_url = reverse('api_dispatch_list', kwargs=kwargs)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        kwargs['pk'] = 'testing'
        grid_url = reverse('api_dispatch_detail', kwargs=kwargs)
        self.assertTrue(grid_url in response.content)
        response = self.client.get(grid_url)
        self.assertEqual(response.status_code, 200)

    def test_03_package(self):
        kwargs = {'resource_name': 'package'}
        kwargs.update(self.base_kwargs)
        # check 200's
        list_url = reverse('api_dispatch_list', kwargs=kwargs)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        kwargs['pk'] = 'testability'
        package_url = reverse('api_dispatch_detail', kwargs=kwargs)
        self.assertTrue(package_url in response.content)
        response = self.client.get(package_url)
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = resources
from django.core.urlresolvers import reverse


def base_resource(obj):
    return {
        "absolute_url": obj.get_absolute_url(),
        "created": obj.created,
        "modified": obj.modified,
        "slug": obj.slug,
        "title": obj.title,
    }


def category_resource(cat):
    data = base_resource(cat)
    data.update(
        {
            "description": cat.description,
            "resource_uri": reverse("apiv3:category_detail", kwargs={"slug": cat.slug}),
            "show_pypi": cat.show_pypi,
            "title_plural": cat.title_plural
        }
    )
    return data


def grid_resource(grid):
    data = base_resource(grid)
    data.update(
        {
            "description": grid.description,
            "is_locked": grid.is_locked,
            "resource_uri": reverse("apiv3:grid_detail", kwargs={"slug": grid.slug}),
            "header": grid.header,
            "packages": [
                reverse("apiv3:package_detail", kwargs={'slug':x.slug}) for x in grid.packages.all()
            ]
        }
    )
    return data


def package_resource(package):
    data = base_resource(package)

    if package.created_by is None:
        created_by = None
    else:
        created_by = reverse("apiv3:user_detail", kwargs={"github_account": package.created_by.get_profile().github_account})

    try:
        last_modified_by = package.last_modified_by.get_profile().github_account
    except AttributeError:
        last_modified_by = None

    data.update(
        {
            "category": reverse("apiv3:category_detail", kwargs={"slug": package.category.slug}),
            "commit_list": package.commit_list,
            "commits_over_52": package.commits_over_52(),
            "created_by": created_by,
            "documentation_url": package.documentation_url,
            "grids": [
                reverse("apiv3:grid_detail", kwargs={"slug": x.slug}) for x in package.grids()
            ],
            "last_fetched": package.last_fetched,
            "last_modified_by": last_modified_by,
            "participants": package.participants,
            "pypi_url": package.pypi_url,
            "pypi_version": package.pypi_version(),
            "repo_description": package.repo_description,
            "repo_forks": package.repo_forks,
            "repo_url": package.repo_url,
            "repo_watchers": package.repo_watchers,
            "resource_uri": reverse("apiv3:package_detail", kwargs={"slug": package.slug}),
            "usage_count": package.get_usage_count()
        }
    )
    return data


def user_resource(profile, list_packages=False):
    user = profile.user
    data = {
        "absolute_url": profile.get_absolute_url(),
        "resource_uri": reverse("apiv3:user_detail", kwargs={"github_account": profile.github_account}),
        "created": profile.created,
        "modified": profile.modified,
        "github_account": profile.github_account,
        "username": user.username,
        "date_joined": user.date_joined,
        "last_login": user.last_login,
        "bitbucket_url": profile.bitbucket_url,
        "google_code_url": profile.google_code_url
    }
    if list_packages:
        data['packages'] = [
            reverse("apiv3:package_detail", kwargs={"slug": x.slug}) for x in profile.my_packages()
        ]
    return data

########NEW FILE########
__FILENAME__ = data
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from grid.models import Grid, GridPackage
from package.models import Package, Category
from profiles.models import Profile


class BaseData(TestCase):
    def setUp(self):
        """
        Set up initial data, done through Python because fixtures break way too
        quickly with migrations and are terribly hard to maintain.
        """
        self.now = timezone.now()
        self.app = Category.objects.create(
            title='App',
            slug='app',
        )
        self.framework = Category.objects.create(
            title='Framework',
            slug='framework',
        )
        self.grid = Grid.objects.create(
            title='A Grid',
            slug='grid',
        )
        self.pkg1 = Package.objects.create(
            title='Package1',
            slug='package1',
            category=self.app,
            repo_url='https://github.com/pydanny/django-uni-form',
            last_fetched=self.now
        )
        self.pkg2 = Package.objects.create(
            title='Package2',
            slug='package2',
            category=self.app,
            repo_url='https://github.com/cartwheelweb/opencomparison'
        )
        GridPackage.objects.create(package=self.pkg1, grid=self.grid)
        GridPackage.objects.create(package=self.pkg2, grid=self.grid)
        self.user = User.objects.create_user('user', 'user@opencomparison.com', 'user')
        self.profile = Profile.objects.create(
            user=self.user,
            github_account="user"
        )
        
        self.pkg1.usage.add(self.user)
        
        self.pkg3 = Package.objects.create(
            title='Package3',
            slug='package3',
            category=self.framework,
            repo_url='https://github.com/divio/django-cms',
            created_by=self.user
        )
########NEW FILE########
__FILENAME__ = test_package
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from grid.models import Grid, GridPackage
from package.models import Package, Category
import json
from requests.compat import urlencode




class PackageV1Tests(TestCase):
    def setUp(self):
        """
        Set up initial data, done through Python because fixtures break way too
        quickly with migrations and are terribly hard to maintain.
        """
        self.app = Category.objects.create(
            title='App',
            slug='app',
        )
        self.framework = Category.objects.create(
            title='Framework',
            slug='framework',
        )
        self.grid = Grid.objects.create(
            title='A Grid',
            slug='grid',
        )
        self.pkg1 = Package.objects.create(
            title='Package1',
            slug='package1',
            category=self.app,
            repo_url='https://github.com/pydanny/django-uni-form'
        )
        self.pkg2 = Package.objects.create(
            title='Package2',
            slug='package2',
            category=self.app,
            repo_url='https://github.com/cartwheelweb/opencomparison'  
        )
        self.pkg3 = Package.objects.create(
            title='Package3',
            slug='package3',
            category=self.framework,
            repo_url='https://github.com/divio/django-cms'
        )
        GridPackage.objects.create(package=self.pkg1, grid=self.grid)
        GridPackage.objects.create(package=self.pkg2, grid=self.grid)
        user = User.objects.create_user('user', 'user@opencomparison.com', 'user')
        self.pkg1.usage.add(user)

    def test_01_packages_usage(self):
        urlkwargs_pkg1 = {
            'api_name': 'v1',
            'resource_name': 'package',
            'pk': self.pkg1.slug,
        }
        url_pkg1 = reverse('api_dispatch_detail', kwargs=urlkwargs_pkg1)
        response_pkg1 = self.client.get(url_pkg1)
        # check that the request was successful
        self.assertEqual(response_pkg1.status_code, 200)
        # check that we have a usage_count equal to the one in the DB
        raw_json_pkg1 = response_pkg1.content
        pkg_1 = json.loads(raw_json_pkg1)
        usage_count_pkg1 = int(pkg_1['usage_count'])
        self.assertEqual(usage_count_pkg1, self.pkg1.usage.count())
        # do the same with pkg2
        urlkwargs_pkg2 = {
            'api_name': 'v1',
            'resource_name': 'package',
            'pk': self.pkg2.slug,
        }
        url_pkg2 = reverse('api_dispatch_detail', kwargs=urlkwargs_pkg2)
        response_pkg2 = self.client.get(url_pkg2)
        # check that the request was successful
        self.assertEqual(response_pkg2.status_code, 200)
        # check that we have a usage_count equal to the one in the DB
        raw_json_pkg2 = response_pkg2.content
        pkg_2 = json.loads(raw_json_pkg2)
        usage_count_pkg2 = int(pkg_2['usage_count'])
        self.assertEqual(usage_count_pkg2, self.pkg2.usage.count())

    def test_02_category_packages(self):
        urlkwargs_pkg_list = {
            'api_name': 'v1',
            'resource_name': 'package',
        }
        querystring_filter_app = {
            'category__slug': self.app.slug
        }
        url_app_pkg = "%s?%s" % (reverse('api_dispatch_list',
            kwargs=urlkwargs_pkg_list), urlencode(querystring_filter_app))
        response_app_pkg = self.client.get(url_app_pkg)
        # check that the request was successful
        self.assertEqual(response_app_pkg.status_code, 200)
        # check that we have correct number of packages in filter
        raw_json_app_pkg = response_app_pkg.content
        app_pkg = json.loads(raw_json_app_pkg)
        app_pkg_count = int(app_pkg['meta']['total_count'])
        self.assertEqual(app_pkg_count, self.app.package_set.count())
        # Check that we have filter applied correclty
        app_package_slug_list = self.app.package_set.values_list('slug', flat=True)
        self.assertIn(self.pkg1.slug, app_package_slug_list)
        self.assertIn(self.pkg2.slug, app_package_slug_list)

########NEW FILE########
__FILENAME__ = test_resources
from django.core.urlresolvers import reverse

from apiv3 import resources
from apiv3.tests.data import BaseData


class ResourceTests(BaseData):

    def test_package_resource(self):
        r = resources.package_resource(self.pkg1)
        self.assertEqual(r['last_fetched'], self.now)
        self.assertEqual(r['repo_watchers'], 0)
        self.assertEqual(r['documentation_url'], '')
        self.assertEqual(r['created_by'], None)

    def test_package_resource_created_by(self):
        r = resources.package_resource(self.pkg3)
        self.assertEqual(r['created_by'], reverse("apiv3:user_detail", kwargs={"github_account": "user"}))

    def test_category_resource(self):
        r = resources.category_resource(self.app)
        self.assertEqual(r['description'], "")
        self.assertEqual(r['title'], "App")
        self.assertEqual(r['slug'], "app")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns("",
    url(
        regex=r"^grids/$",
        view=views.grid_list,
        name="grid_list",
    ),
    url(
        regex=r"^grids/(?P<slug>[-\w]+)/$",
        view=views.grid_detail,
        name="grid_detail",
    ),
    url(
        regex=r"^packages/$",
        view=views.package_list,
        name="package_list",
    ),
    url(
        regex=r"^packages/(?P<slug>[-\w]+)/$",
        view=views.package_detail,
        name="package_detail",
    ),
    url(
        regex=r"^categories/$",
        view=views.category_list,
        name="category_list"
    ),
    url(
        regex=r"^categories/(?P<slug>[-\w]+)/$",
        view=views.category_detail,
        name="category_detail"
    ),
    url(
        regex=r"^users/(?P<github_account>[-\w]+)/$",
        view=views.user_detail,
        name="user_detail"
    ),
    url(
        regex=r"^users/$",
        view=views.user_list,
        name="user_list"
    )
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404

from jsonview.decorators import json_view

from .resources import (
        grid_resource, package_resource, category_resource, user_resource
    )
from grid.models import Grid
from package.models import Package, Category
from profiles.models import Profile


def GET_int(request, value_name, default):
    try:
        value = int(request.GET.get(value_name, default))
    except ValueError:
        value = default
    return value


def calc_next(request, limit, offset, count):
    # calculate next
    if count > limit + offset:
        next = "{}?limit={}&offset={}".format(
            request.path,
            limit,
            offset + limit
        )
    else:
        next = None
    return next


def calc_previous(request, limit, offset, count):

    # calculate previous
    if offset <= 0:
        previous = None
    else:
        previous = "{}?limit={}&offset={}".format(
            request.path,
            limit,
            max(offset - limit, 0)
        )
    return previous


@json_view
def grid_detail(request, slug):
    grid = get_object_or_404(Grid, slug=slug)
    return grid_resource(grid)


@json_view
def grid_list(request):
    count = Grid.objects.count()
    limit = GET_int(request, "limit", 20)
    offset = GET_int(request, "offset", 0)

    # Return the Data structure
    return {
        "meta": {
            "limit": limit,
            "next": calc_next(request, limit, offset, count),
            "offset": offset,
            "previous": calc_previous(request, limit, offset, count),
            "total_count": count
        },
        "objects": [grid_resource(x) for x in Grid.objects.all()[offset:offset + limit]]
    }


@json_view
def package_detail(request, slug):
    package = get_object_or_404(Package, slug=slug)
    return package_resource(package)


@json_view
def package_list(request):
    category = request.GET.get("category", None)
    try:
        category = Category.objects.get(slug=category)
        count = Package.objects.filter(category=category).count()
    except Category.DoesNotExist:
        category = None
        count = Package.objects.count()

    limit = GET_int(request, "limit", 20)
    offset = GET_int(request, "offset", 0)

    # build the Data structure
    data = {
        "meta": {
            "limit": limit,
            "next": calc_next(request, limit, offset, count),
            "offset": offset,
            "previous": calc_previous(request, limit, offset, count),
            "total_count": count
        },
        "category": None
    }

    if category:
        data['objects'] = [
            package_resource(x) for x in Package.objects.filter(category=category)[offset:offset + limit]
        ]
    else:
        data['objects'] = [package_resource(x) for x in Package.objects.all()[offset:offset + limit]]

    return data


@json_view
def category_list(request):
    count = Profile.objects.count()
    limit = GET_int(request, "limit", 20)
    offset = GET_int(request, "offset", 0)

    # Return the Data structure
    return {
        "meta": {
            "limit": limit,
            "next": calc_next(request, limit, offset, count),
            "offset": offset,
            "previous": calc_previous(request, limit, offset, count),
            "total_count": count
        },
        "objects": [category_resource(x) for x in Category.objects.all()[offset:offset + limit]]
    }


@json_view
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    return category_resource(category)


@json_view
def user_list(request):
    count = Profile.objects.count()
    limit = GET_int(request, "limit", 20)
    offset = GET_int(request, "offset", 0)
    list_packages = request.GET.get("list_packages", False)

    # Return the Data structure
    return {
        "meta": {
            "limit": limit,
            "next": calc_next(request, limit, offset, count),
            "offset": offset,
            "previous": calc_previous(request, limit, offset, count),
            "total_count": count
        },
        "objects": [user_resource(x, list_packages) for x in Profile.objects.all()[offset:offset + limit]]
    }


@json_view
def user_detail(request, github_account):
    profile = get_object_or_404(Profile, github_account=github_account)
    list_packages = request.GET.get("list_packages", False)
    return user_resource(profile, list_packages)

########NEW FILE########
__FILENAME__ = apiv2
from django.conf.urls import patterns, url

from package import apiv2 as package_api
from grid import views as grid_views
from searchv2 import views as search_views

urlpatterns = patterns("",
    # {% url "apiv2:category" %}
    url(
        regex=r"categories/$",
        view=package_api.CategoryListAPIView.as_view(),
        name="categories"
    ),
    # {% url "apiv2:packages" %}
    url(
        regex=r"packages/$",
        view=package_api.PackageListAPIView.as_view(),
        name="packages"
    ),
    # {% url "apiv2:packages" slug %}
    url(
        regex=r"packages/(?P<slug>[-\w]+)/$",
        view=package_api.PackageDetailAPIView.as_view(),
        name="packages"
    ),
    # {% url "apiv2:grids" %}
    url(
        regex=r"grids/$",
        view=grid_views.GridListAPIView.as_view(),
        name="grids"
    ),
    # {% url "apiv2:grids" slug %}
    url(
        regex=r"grids/(?P<slug>[-\w]+)/$",
        view=grid_views.GridDetailAPIView.as_view(),
        name="grids"
    ),
    # {% url "apiv2:search" %}
    url(
        regex=r"search/$",
        view=search_views.SearchListAPIView.as_view(),
        name="search"
    ),
    # {% url "apiv2:search" slug %}
    url(
        regex=r"search/(?P<slug>[-\w]+)/$",
        view=search_views.SearchDetailAPIView.as_view(),
        name="search"
    ),
    # {% url "apiv2:python3" slug %}
    url(
        regex=r"python3/$",
        view=package_api.Python3ListAPIView.as_view(),
        name="python3"
    ),
)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Max

from searchv2.models import SearchV2

def core_values(request):
    """
    A nice pun. But this is how we stick handy data everywhere.
    """

    data = {
        'SITE_TITLE': getattr(settings, "SITE_TITLE", "Django Packages"),
        'FRAMEWORK_TITLE': getattr(settings, "FRAMEWORK_TITLE", "Django"),
        'MAX_WEIGHT': SearchV2.objects.all().aggregate(Max('weight'))['weight__max']
        }
    return data


def current_path(request):
    """Adds the path of the current page to template context, but only
    if it's not the path to the logout page. This allows us to redirect
    user's back to the page they were viewing before they logged in,
    while making sure we never redirect them back to the logout page!

    """
    context = {}
    if request.path.strip() != reverse('logout'):
        context['current_path'] = request.path
    return context

########NEW FILE########
__FILENAME__ = decorators
""" This code was authored by Raymond Hettiger. """

import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter

class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0

def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10
    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                  # mapping of args to results
        queue = collections.deque() # order that keys have been used
        refcount = Counter()        # times each key is in the queue
        sentinel = object()         # marker for looping around the queue
        kwd_mark = object()         # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1


            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function
########NEW FILE########
__FILENAME__ = fields
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField


class CreationDateTimeField(CreationDateTimeField):

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.DateTimeField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)


class ModificationDateTimeField(ModificationDateTimeField):

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.DateTimeField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)

########NEW FILE########
__FILENAME__ = big_email_send
import time
from sys import stdout

from django.conf import settings
from django.core.management.base import CommandError, NoArgsCommand
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

from django.contrib.auth.models import User
from django.core.mail import send_mail

class Command(NoArgsCommand):
    
    help = "Send out email to everyone"
    
    def handle(self, *args, **options): 
        print >> stdout, "Commencing big email send"

        #users = User.objects.filter(is_active=True).exclude(email__contains="qq.com").exclude(email__contains="tom.com")
        users = User.objects.filter(username__in=("pydanny","audreyr"))

        for index, user in enumerate(users):
            if not user.email.strip():
                continue
            send_mail(
                subject=settings.BIG_EMAIL_SEND_SUBJECT,
                message=settings.BIG_EMAIL_SEND,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email,],
            )            
            print "Sent to", index, user.email
            time.sleep(1)

########NEW FILE########
__FILENAME__ = load_dev_data
from sys import stdout

from django.conf import settings
from django.core.management.base import CommandError, NoArgsCommand
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule


class Command(NoArgsCommand):
    
    help = "Import development data for local dev"
    
    def handle(self, *args, **options): 
        print >> stdout, "Commencing dev data import"

        for app in settings.INSTALLED_APPS:
            mod = import_module(app)
            # Attempt to import the app's test.data module.
            try:
                mod_data = import_module('%s.tests.data' % app)
                mod_data.load()
            except:
                # Decide whether to bubble up this error. If the app just
                # doesn't have an test.data module, we can ignore the error
                # attempting to import it, otherwise we want it to bubble up.
                if module_has_submodule(mod, 'test.data'):
                    raise


########NEW FILE########
__FILENAME__ = middleware
from django.views.debug import technical_500_response
import sys


class UserBasedExceptionMiddleware(object):
    def process_exception(self, request, exception):
        if request.user.is_superuser:
            return technical_500_response(request, *sys.exc_info())

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.fields import CreationDateTimeField, ModificationDateTimeField


class BaseModel(models.Model):
    """ Base abstract base class to give creation and modified times """
    created = CreationDateTimeField(_('created'))
    modified = ModificationDateTimeField(_('modified'))

    class Meta:
        abstract = True

    def cache_namer(self, method):
        return "{}:{}".format(
            method.__name__,
            self.pk
        )

    def model_cache_name(self):
        return "{}:{}".format(
            self.__class__.__name__,
            self.pk
        )

########NEW FILE########
__FILENAME__ = opencomparison_tags
# -*- coding: utf-8 -*-
from django import template

register = template.Library()


"""
jQuery templates use constructs like:

    {{if condition}} print something{{/if}}

This, of course, completely screws up Django templates,
because Django thinks {{ and }} mean something.

Wrap {% verbatim %} and {% endverbatim %} around those
blocks of jQuery templates and this will try its best
to output the contents with no changes.
"""

register = template.Library()


class VerbatimNode(template.Node):

    def __init__(self, text):
        self.text = text

    def render(self, context):
        return self.text


@register.tag
def verbatim(parser, token):
    text = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endverbatim':
            break
        if token.token_type == template.TOKEN_VAR:
            text.append('{{')
        elif token.token_type == template.TOKEN_BLOCK:
            text.append('{%')
        text.append(token.contents)
        if token.token_type == template.TOKEN_VAR:
            text.append('}}')
        elif token.token_type == template.TOKEN_BLOCK:
            text.append('%}')
    return VerbatimNode(''.join(text))

########NEW FILE########
__FILENAME__ = data
from django.contrib.auth.models import User

from package.models import Category, Package

STOCK_PASSWORD = "stock_password"


def make():

    create_users()

    category, created = Category.objects.get_or_create(
        title="App",
        slug="apps",
        description="Small components used to build projects."
    )
    category.save()

    package, created = Package.objects.get_or_create(
        category = category,
        participants = "malcomt,jacobian",
        repo_description = "Increase your testing ability with this steroid free supplement.",
        repo_url = "https://github.com/pydanny/django-la-facebook",
        slug = "testability",
        title="Testability"
    )
    package.save()
    package, created = Package.objects.get_or_create(
        category = category,
        participants = "thetestman",
        repo_description = "Test everything under the sun with one command!",
        repo_url = "https://github.com/pydanny/django-uni-form",
        slug = "supertester",
        title="Supertester"
    )
    package.save()
    package, created = Package.objects.get_or_create(
        category = category,
        participants = "pydanny",
        repo_description = "Make testing as painless as frozen yogurt.",
        repo_url = "https://github.com/opencomparison/opencomparison",
        slug = "serious-testing",
        title="Serious Testing"
    )
    package.save()    
    package, created = Package.objects.get_or_create(
        category = category,
        participants = "pydanny",
        repo_description = "Yet another test package, with no grid affiliation.",
        repo_url = "https://github.com/djangopackages/djangopackages",
        slug = "another-test",
        title="Another Test"
    )
    package.save()


def create_users():

    user = User.objects.create_user(
        username="user",
        password=STOCK_PASSWORD,
        email="user@example.com"
    )
    user.is_active = True
    user.save()

    user = User.objects.create_user(
        username="cleaner",
        password="cleaner",
        email="cleaner@example.com"
    )
    user.is_active = True
    user.save()

    user = User.objects.create_user(
        username="staff",
        password="staff",
        email="staff@example.com"
    )
    user.is_active = True
    user.is_staff = True
    user.save()

    user = User.objects.create_user(
        username="admin",
        password="admin",
        email="admin@example.com"
    )
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
########NEW FILE########
__FILENAME__ = datautil
from django.db import connections, DEFAULT_DB_ALIAS, transaction
from django.core.management.color import no_style


def reset_sequences(*models):
    """
    After loading data the sequences must be reset in the database if
    the primary keys are manually specified. This is handled
    automatically by django for fixtures.

    Much of this is modeled after django.core.management.commands.loaddata.
    """
    connection = connections[DEFAULT_DB_ALIAS]
    cursor = connection.cursor()
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), models)
    if sequence_sql:
        for line in sequence_sql:
            cursor.execute(line)
    transaction.commit_unless_managed()
    cursor.close()

########NEW FILE########
__FILENAME__ = test_fields
from django.test import TestCase

from core.fields import CreationDateTimeField, ModificationDateTimeField


class TestFields(TestCase):

    def test_create_override(self):
        field = CreationDateTimeField()
        triple = field.south_field_triple()

        self.assertEquals(triple[0], 'django.db.models.fields.DateTimeField')
        self.assertEquals(triple[1], list())
        self.assertEquals(triple[2], {'default': 'datetime.datetime.now', 'blank': 'True'})

    def test_modify_override(self):
        field = ModificationDateTimeField()
        triple = field.south_field_triple()

        self.assertEquals(triple[0], 'django.db.models.fields.DateTimeField')
        self.assertEquals(triple[1], list())
        self.assertEquals(triple[2], {'default': 'datetime.datetime.now', 'blank': 'True'})

########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase

from core import utils


class SlugifyOC(TestCase):

    def test_oc_slugify(self):

        lst = (
            ('test.this.value', 'test-this-value'),
            ('Plone.OpenComparison', 'plone-opencomparison'),
            ('Run from here', 'run-from-here'),
            ('Jump_the shark', 'jump_the-shark'),
            )

        for l in lst:
            self.assertEquals(utils.oc_slugify(l[0]), l[1])


class GetPypiUrl(TestCase):

    def test_get_pypi_url_success(self):

        lst = (
            ('django', 'http://pypi.python.org/pypi/django'),
            ('Django Uni Form', 'http://pypi.python.org/pypi/django-uni-form'),
        )
        for l in lst:
            self.assertEquals(utils.get_pypi_url(l[0].lower()), l[1].lower())

    def test_get_pypi_url_fail(self):

        lst = (
            'ColdFusion is not here',
            'php is not here'
        )
        for l in lst:
            self.assertEquals(utils.get_pypi_url(l), None)

########NEW FILE########
__FILENAME__ = context_managers
# -*- coding: utf-8 -*-
from django.conf import settings


class NULL:
    pass


class SettingsOverride(object):
    """
    Overrides Django settings within a context and resets them to their inital
    values on exit.

    Example::

        with SettingsOverride(DEBUG=True):
            # do something
    """

    def __init__(self, **overrides):
        self.overrides = overrides

    def __enter__(self):
        self.old = {}
        for key, value in self.overrides.items():
            self.old[key] = getattr(settings, key, NULL)
            setattr(settings, key, value)

    def __exit__(self, type, value, traceback):
        for key, value in self.old.items():
            if value is not NULL:
                setattr(settings, key, value)
            else:
                delattr(settings, key)  # do not pollute the context!

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.core.cache import cache
from django.template.defaultfilters import slugify

import re
import requests


def cache_fetcher(cachekey_func, identifier_model):
    key = cachekey_func(identifier_model)
    return (key, cache.get(key))


def oc_slugify(value):
    value = value.replace('.', '-')
    return slugify(value)


def get_pypi_url(title):
    title = title.strip()
    for value in [oc_slugify(title.lower()), oc_slugify(title), title, title.lower(), title.title(), ]:
        value = 'http://pypi.python.org/pypi/' + value
        r = requests.get(value)
        if r.status_code == 200:
            return value
    return None


STATUS_CHOICES = (
    (0, "Unknown"),
    (1, "Development Status :: 1 - Planning"),
    (2, "Development Status :: 2 - Pre-Alpha"),
    (3, "Development Status :: 3 - Alpha"),
    (4, "Development Status :: 4 - Beta"),
    (5, "Development Status :: 5 - Production/Stable"),
    (6, "Development Status :: 6 - Mature"),
    (7, "Development Status :: 7 - Inactive")
)


def status_choices_switch(status):
    for key, value in STATUS_CHOICES:
        if status == value:
            return key


def get_repo_from_url(url):
    """
        Needs to account for:

            1. GitHub Design
            2. Ability to assign special CNAME for BitBucket repos
            3. et al
    """

    # Handle github repos
    if url.startswith("https://github.com/"):
        m = re.match(settings.URL_REGEX_GITHUB, url)
        if m:
            return m.group()

    return None



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Python Packages documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 14 13:56:50 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# todo: see if VIRTUAL_ENV variable is in the paths
# and if it is not, add to os.path - this is necessary when sphinx is
# installed only in the sitewide packages directory

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../'))

from settings import base
from django.core.management import setup_environ
setup_environ(base)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest',
              'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Packages'
copyright = u'2010-2012, Audrey Roy, Daniel Greenfeld and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'opencomparisondoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'DjangoPackages.tex', u'Django Packages Documentation',
   u'Audrey Roy, Daniel Greenfeld and contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'DjangoPackages', u'Django Packages Documentation',
     [u'Audrey Roy, Daniel Greenfeld and contributors'], 1)
]

########NEW FILE########
__FILENAME__ = feeds
"""Contains classes for the feeds"""

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from package.models import Package


class RssLatestPackagesFeed(Feed):
    """RSS Feed for the packages"""
    title = "Latest {0} packages added".format(settings.FRAMEWORK_TITLE)
    link = "/packages/latest/"
    description = "The last 15 packages added"

    def items(self):
        """Returns 15 most recently created repositories"""
        return Package.objects.all().order_by("-created")[:15]

    def item_title(self, item):
        """Get title of the repository"""
        return item.title

    def item_description(self, item):
        """Get description of the repository"""
        return item.repo_description

    def item_pubdate(self, item):
        """Get publication date"""
        return item.created


class AtomLatestPackagesFeed(RssLatestPackagesFeed):
    """Atom feed for the packages"""
    feed_type = Atom1Feed
    subtitle = RssLatestPackagesFeed.description

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = data
from grid.models import Grid
from django.contrib.auth.models import Group, User, Permission
from package.models import Category, PackageExample, Package
from grid.models import Element, Feature, GridPackage
from core.tests import datautil


def load():
    category, created = Category.objects.get_or_create(
        pk=1,
        slug=u'apps',
        title=u'App',
        description=u'Small components used to build projects.',
    )

    package1, created = Package.objects.get_or_create(
        pk=1,
        category=category,
        repo_watchers=0,
        title=u'Testability',
        pypi_url='',
        participants=u'malcomt,jacobian',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-la-facebook',
        
        repo_forks=0,
        slug=u'testability',
        repo_description=u'Increase your testing ability with this steroid free supplement.',
    )
    package2, created = Package.objects.get_or_create(
        pk=2,
        category=category,
        repo_watchers=0,
        title=u'Supertester',
        pypi_url='',
        participants=u'thetestman',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-uni-form',
        
        repo_forks=0,
        slug=u'supertester',
        repo_description=u'Test everything under the sun with one command!',
    )
    package3, created = Package.objects.get_or_create(
        pk=3,
        category=category,
        repo_watchers=0,
        title=u'Serious Testing',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/opencomparison/opencomparison',
        
        repo_forks=0,
        slug=u'serious-testing',
        repo_description=u'Make testing as painless as waxing your legs.',
    )
    package4, created = Package.objects.get_or_create(
        pk=4,
        category=category,
        repo_watchers=0,
        title=u'Another Test',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/djangopackages/djangopackages',
        
        repo_forks=0,
        slug=u'another-test',
        repo_description=u'Yet another test package, with no grid affiliation.',
    )

    grid1, created = Grid.objects.get_or_create(
        pk=1,
        description=u'A grid for testing.',
        title=u'Testing',
        is_locked=False,
        slug=u'testing',
    )
    grid2, created = Grid.objects.get_or_create(
        pk=2,
        description=u'Another grid for testing.',
        title=u'Another Testing',
        is_locked=False,
        slug=u'another-testing',
    )

    gridpackage1, created = GridPackage.objects.get_or_create(
        pk=1,
        package=package1,
        grid=grid1,
    )
    gridpackage2, created = GridPackage.objects.get_or_create(
        pk=2,
        package=package1,
        grid=grid1,
    )
    gridpackage3, created = GridPackage.objects.get_or_create(
        pk=3,
        package=package3,
        grid=grid1,
    )
    gridpackage4, created = GridPackage.objects.get_or_create(
        pk=4,
        package=package3,
        grid=grid2,
    )
    gridpackage5, created = GridPackage.objects.get_or_create(
        pk=5,
        package=package2,
        grid=grid1,
    )

    feature1, created = Feature.objects.get_or_create(
        pk=1,
        title=u'Has tests?',
        grid=grid1,
        description=u'Does this package come with tests?',
    )
    feature2, created = Feature.objects.get_or_create(
        pk=2,
        title=u'Coolness?',
        grid=grid1,
        description=u'Is this package cool?',
    )

    element, created = Element.objects.get_or_create(
        pk=1,
        text=u'Yes',
        feature=feature1,
        grid_package=gridpackage1,
    )

    group1, created = Group.objects.get_or_create(
        pk=1,
        name=u'Moderators',
        #permissions=[[u'delete_gridpackage', u'grid', u'gridpackage'], [u'delete_feature', u'grid', u'feature']],
    )
    group1.permissions.clear()
    group1.permissions = [
        Permission.objects.get(codename='delete_gridpackage'),
        Permission.objects.get(codename='delete_feature')
        ]

    user1, created = User.objects.get_or_create(
        pk=1,
        username=u'user',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$644c9$347f3dd85fb609a5745ebe33d0791929bf08f22e',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2, created = User.objects.get_or_create(
        pk=2,
        username=u'cleaner',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        #groups=[group1],
        password=u'sha1$e6fe2$78b744e21cddb39117997709218f4c6db4e91894',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2.groups = [group1]

    user3, created = User.objects.get_or_create(
        pk=3,
        username=u'staff',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$8894d$c4814980edd6778f0ab1632c4270673c0fd40efe',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user4, created = User.objects.get_or_create(
        pk=4,
        username=u'admin',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$52c7f$59b4f64ffca593e6abd23f90fd1f95cf71c367a4',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )

    packageexample, created = PackageExample.objects.get_or_create(
        pk=1,
        package=package1,
        url=u'http://www.example.com/',
        active=True,
        title=u'www.example.com',
    )

    datautil.reset_sequences(Grid, Group, User, Permission, Category, PackageExample,
                             Package, Element, Feature, GridPackage)


########NEW FILE########
__FILENAME__ = test_latest
from django.test import TestCase
from django.core.urlresolvers import reverse
from package.models import Package

import feedparser

from feeds.tests import data


class LatestFeedsTest(TestCase):
    def setUp(self):
        data.load()

    def test_latest_feeds(self):

        packages = Package.objects.all().order_by('-created')[:15]

        for feed_type in ('rss', 'atom'):
            url = reverse('feeds_latest_packages_%s' % feed_type)
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)

            feed = feedparser.parse(response.content)

            expect_titles = [p.title for p in packages]
            actual_titles = [e['title'] for e in feed.entries]

            for expected_title, actual_title in zip(expect_titles, actual_titles):
                self.assertEqual(expected_title, actual_title)

            expect_summaries = [p.repo_description for p in packages]
            actual_summaries = [e['summary'] for e in feed.entries]

            for expected_summary, actual_summary in zip(expect_summaries, actual_summaries):
                self.assertEqual(expected_summary, actual_summary)

########NEW FILE########
__FILENAME__ = urls
"""url patterns for the feeds"""

from django.conf.urls import patterns, url

from feeds import *

urlpatterns = patterns("",
    url(r'^packages/latest/rss/$', RssLatestPackagesFeed(), name="feeds_latest_packages_rss"),
    url(r'^packages/latest/atom/$', AtomLatestPackagesFeed(), name="feeds_latest_packages_atom"),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from reversion.admin import VersionAdmin

from grid.models import Element, Feature, Grid, GridPackage


class GridPackageInline(admin.TabularInline):
    model = GridPackage


class GridAdmin(VersionAdmin):
    list_display_links = ('title',)
    list_display = ('title', 'header',)
    list_editable = ('header',)
    inlines = [
        GridPackageInline,
    ]

admin.site.register(Element, VersionAdmin)
admin.site.register(Feature, VersionAdmin)
admin.site.register(Grid, GridAdmin)
admin.site.register(GridPackage, VersionAdmin)

########NEW FILE########
__FILENAME__ = cachekeys
def grid_grid_packages(grid):
    return "grid:grid_packages:%s" % grid.id

########NEW FILE########
__FILENAME__ = context_processors
from itertools import izip, chain, repeat

from grid.models import Grid


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return izip(*[chain(iterable, repeat(padvalue, n-1))]*n)


def grid_headers(request):
    grid_headers = list(Grid.objects.filter(header=True))
    grid_headers = grouper(7, grid_headers)
    return {'grid_headers': grid_headers}

########NEW FILE########
__FILENAME__ = forms
"""Forms for the :mod:`grid` app
"""

from django.forms import ModelForm

from grid.models import  Element, Feature, Grid, GridPackage


class GridForm(ModelForm):
    """collects data for the new grid - a
    django ``ModelForm`` for :class:`grid.models.Grid`
    """

    def clean_slug(self):
        """returns lower-cased slug"""
        return self.cleaned_data['slug'].lower()

    class Meta:
        model = Grid
        fields = ['title', 'slug', 'description']


class ElementForm(ModelForm):
    """collects data for a new grid element -
    a ``ModelForm`` for :class:`grid.models.Element`
    """

    class Meta:
        model = Element
        fields = ['text', ]


class FeatureForm(ModelForm):
    """collects data for the feature -
    a ``ModelForm`` for :class:`grid.models.Feature`
    """

    class Meta:
        model = Feature
        fields = ['title', 'description', ]


class GridPackageForm(ModelForm):
    """collects data for a new package -
    a ``ModelForm`` for :class:`grid.models.GridPackage`
    """

    class Meta:
        model = GridPackage
        fields = ['package']

########NEW FILE########
__FILENAME__ = fix_grid_element
from collections import defaultdict

from django.core.management.base import BaseCommand
from grid.models import Element


class Command(BaseCommand):
    help = 'fix Grid.Element table'

    def handle(self, *args, **kwargs):
        print 'fixing Grid.Element table...'

        rows = Element.objects.all().values('grid_package_id', 'feature_id', 'id')

        dedup = defaultdict(list)

        for row in rows:
            dedup[(row['grid_package_id'], row['feature_id'])].append(row['id'])
        print 'found {0} duplicate rows...'.format(len(rows) - len(dedup))

        for (feature, package), ids in dedup.iteritems():
            inlist = sorted(ids)[1:]
            if inlist:
                print 'deleting package {0}, feature {1} (id {2})'.format(package, feature, ','.join(map(str, inlist)))
                Element.objects.filter(id__in=inlist).delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    depends_on = (
            ("package", "0016_auto__del_field_package_pypi_home_page"),
        )    

    def forwards(self, orm):
        
        # Adding model 'Grid'
        db.create_table('grid_grid', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('is_locked', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('grid', ['Grid'])

        # Adding model 'GridPackage'
        db.create_table('grid_gridpackage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('grid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Grid'])),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'])),
        ))
        db.send_create_signal('grid', ['GridPackage'])

        # Adding model 'Feature'
        db.create_table('grid_feature', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('grid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Grid'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('grid', ['Feature'])

        # Adding model 'Element'
        db.create_table('grid_element', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('grid_package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.GridPackage'])),
            ('feature', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Feature'])),
            ('text', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('grid', ['Element'])


    def backwards(self, orm):
        
        # Deleting model 'Grid'
        db.delete_table('grid_grid')

        # Deleting model 'GridPackage'
        db.delete_table('grid_gridpackage')

        # Deleting model 'Feature'
        db.delete_table('grid_feature')

        # Deleting model 'Element'
        db.delete_table('grid_element')


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
        'grid.element': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Element'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'feature': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Feature']"}),
            'grid_package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.GridPackage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'grid.feature': {
            'Meta': {'object_name': 'Feature'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['grid']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_grid_header
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    depends_on = (
            ("package", "0016_auto__del_field_package_pypi_home_page"),
        )    
    

    def forwards(self, orm):
        
        # Adding field 'Grid.header'
        db.add_column('grid_grid', 'header', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Grid.header'
        db.delete_column('grid_grid', 'header')


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
        'grid.element': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Element'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'feature': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Feature']"}),
            'grid_package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.GridPackage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'grid.feature': {
            'Meta': {'object_name': 'Feature'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['grid']

########NEW FILE########
__FILENAME__ = models
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.models import BaseModel
from grid.utils import make_template_fragment_key
from package.models import Package


class Grid(BaseModel):
    """Grid object, inherits form :class:`package.models.BaseModel`. Attributes:

    * :attr:`~grid.models.Grid.title` - grid title
    * :attr:`~grid.models.Grid.slug` - grid slug for SEO
    * :attr:`~grid.models.Grid.description` - description of the grid
      with line breaks and urlized links
    * :attr:`~grid.models.Grid.is_locked` - boolean field accessible
      to moderators
    * :attr:`~grid.models.Grid.packages` - many-to-many relation
      with :class:~`grid.models.GridPackage` objects
    """

    title = models.CharField(_('Title'), max_length=100)
    slug = models.SlugField(_('Slug'), help_text="Slugs will be lowercased", unique=True)
    description = models.TextField(_('Description'), blank=True, help_text="Lines are broken and urls are urlized")
    is_locked = models.BooleanField(_('Is Locked'), default=False, help_text="Moderators can lock grid access")
    packages = models.ManyToManyField(Package, through="GridPackage")
    header = models.BooleanField(_("Header tab?"), default=False, help_text="If checked then displayed on homepage header")

    def elements(self):
        elements = []
        for feature in self.feature_set.all():
            for element in feature.element_set.all():
                elements.append(element)
        return elements

    def __unicode__(self):
        return self.title

    @property
    def grid_packages(self):
        """ Gets all the packages and orders them for views and other things
         """
        gp = self.gridpackage_set.select_related('gridpackage', 'package__repo', 'package__category')
        grid_packages = gp.annotate(usage_count=models.Count('package__usage')).order_by('-usage_count', 'package')
        return grid_packages

        """
        key, grid_packages = cache_fetcher(cachekeys.grid_grid_packages, self)
        if grid_packages is not None:
            return grid_packages
        gp = self.gridpackage_set.select_related('gridpackage', 'package__repo', 'package__category')
        grid_packages = gp.annotate(usage_count=models.Count('package__usage')).order_by('-usage_count', 'package')
        cache.set(key, grid_packages, settings.CACHE_TIMEOUT)
        return grid_packages
        """

    def save(self, *args, **kwargs):
        self.grid_packages  # fire the cache
        self.clear_detail_template_cache()  # Delete the template fragment cache
        super(Grid, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ("grid", [self.slug])

    def clear_detail_template_cache(self):
        key = make_template_fragment_key("detail_template_cache", [self.pk, ])
        cache.delete(key)

    class Meta:
        ordering = ['title']


class GridPackage(BaseModel):
    """Grid package.
    This model describes packages listed on one side of the grids
    and
    explicitly defines the many-to-many relationship between grids
    and the packages
    (i.e - allows any given package to be assigned to several grids at once).

    Attributes:

    * :attr:`grid` - the :class:`~grid.models.Grid` to which the package is assigned
    * :attr:`package` - the :class:`~grid.models.Package`
    """

    grid = models.ForeignKey(Grid)
    package = models.ForeignKey(Package)

    class Meta:
        verbose_name = 'Grid Package'
        verbose_name_plural = 'Grid Packages'

    def save(self, *args, **kwargs):
        self.grid.grid_packages  # fire the cache
        self.grid.clear_detail_template_cache()
        super(GridPackage, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s : %s' % (self.grid.slug, self.package.slug)


class Feature(BaseModel):
    """ These are the features measured against a grid.
    ``Feature`` has the following attributes:

    * :attr:`grid` - the grid to which the feature is assigned
    * :attr:`title` - name of the feature (100 chars is max)
    * :attr:`description` - plain-text description
    """

    grid = models.ForeignKey(Grid)
    title = models.CharField(_('Title'), max_length=100)
    description = models.TextField(_('Description'), blank=True)

    def save(self, *args, **kwargs):
        self.grid.grid_packages  # fire the cache
        self.grid.clear_detail_template_cache()
        super(Feature, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s : %s' % (self.grid.slug, self.title)

help_text = """
Linebreaks are turned into 'br' tags<br />
Urls are turned into links<br />
You can use just 'check', 'yes', 'good' to place a checkmark icon.<br />
You can use 'bad', 'negative', 'evil', 'sucks', 'no' to place a negative icon.<br />
Plus just '+' or '-' signs can be used but cap at 3 multiples to protect layout<br/>

"""


class Element(BaseModel):
    """ The individual cells on the grid.
    The ``Element`` grid attributes are:

    * :attr:`grid_package` - foreign key to :class:`~grid.models.GridPackage`
    * :attr:`feature` - foreign key to :class:`~grid.models.Feature`
    * :attr:`text` - the actual contents of the grid cell
    """

    grid_package = models.ForeignKey(GridPackage)
    feature = models.ForeignKey(Feature)
    text = models.TextField(_('text'), blank=True, help_text=help_text)

    class Meta:

        ordering = ["-id"]

    def save(self, *args, **kwargs):
        self.feature.save()  # fire grid_packages cache
        super(Element, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s : %s : %s' % (self.grid_package.grid.slug, self.grid_package.package.slug, self.feature.title)

########NEW FILE########
__FILENAME__ = grid_tags
"""template tags and filters
for the :mod:`grid` app"""

from django import template
from django.conf import settings
from django.template.defaultfilters import escape, truncatewords
from django.template.loader import render_to_string


import re

register = template.Library()

static_url = settings.STATIC_URL

plus_two_re = re.compile(r'^(\+2|\+{2})$')
minus_two_re = re.compile(r'^(\-2|\-{2})$')

plus_three_re = re.compile(r'^(\+[3-9]{1,}|\+{3,}|\+[1-9][0-9]+)$')
minus_three_re = re.compile(r'^(\-[3-9]{1,}|\-{3,}|\-[1-9][0-9]+)$')

YES_KEYWORDS = ('check', 'yes', 'good', '+1', '+')
NO_KEYWORDS = ('bad', 'negative', 'evil', 'sucks', 'no', '-1', '-')
YES_IMG = '<span class="glyphicon glyphicon-ok"></span>'
NO_IMG = '<span class="glyphicon glyphicon-remove"></span>'


@register.filter
def style_element(text):
    low_text = text.strip().lower()
    if low_text in YES_KEYWORDS:
        return YES_IMG
    if low_text in NO_KEYWORDS:
        return NO_IMG

    if plus_two_re.search(low_text):
        return YES_IMG * 2

    if minus_two_re.search(low_text):
        return NO_IMG * 2

    if plus_three_re.search(low_text):
        return YES_IMG * 3

    if minus_three_re.search(low_text):
        return NO_IMG * 3

    text = escape(text)

    found = False
    for positive in YES_KEYWORDS:
        if text.startswith(positive):
            text = '%s&nbsp;%s' % (YES_IMG, text[len(positive):])
            found = True
            break
    if not found:
        for negative in NO_KEYWORDS:
            if text.startswith(negative):
                text = '%s&nbsp;%s' % (NO_IMG, text[len(negative):])
                break

    return text


@register.filter
def hash(h, key):
    """Function leaves considerable overhead in the grid_detail views.
    each element of the list results in two calls to this hash function.
    Code there, and possible here, should be refactored.
    """
    return h.get(key, {})


@register.filter
def style_attribute(attribute_name, package):
    mappings = {
            'title': style_title,
            'repo_description': style_repo_description,
            'commits_over_52': style_commits,
    }

    as_var = template.Variable('package.' + attribute_name)
    try:
        value = as_var.resolve({'package': package})
    except template.VariableDoesNotExist:
        value = ''

    if attribute_name in mappings.keys():
        return  mappings[attribute_name](value)

    return style_default(value)


@register.filter
def style_title(value):
    value = value[:20]
    return render_to_string('grid/snippets/_title.html', {'value': value})


def style_commits(value):
    return render_to_string('grid/snippets/_commits.html', {'value': value})


@register.filter
def style_description(value):
    return style_default(value[:20])


@register.filter
def style_default(value):
    return value


@register.filter
def style_repo_description(var):
    truncated_desc = truncatewords(var, 20)
    return truncated_desc

########NEW FILE########
__FILENAME__ = data
from django.contrib.auth.models import Group, User, Permission

from core.tests import datautil
from grid.models import Grid
from grid.models import Element, Feature, GridPackage
from package.models import Category, PackageExample, Package
from profiles.models import Profile


def load():
    category, created = Category.objects.get_or_create(
        pk=1,
        slug=u'apps',
        title=u'App',
        description=u'Small components used to build projects.',
    )

    package1, created = Package.objects.get_or_create(
        pk=1,
        category=category,
        repo_watchers=0,
        title=u'Testability',
        pypi_url='',
        participants=u'malcomt,jacobian',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-la-facebook',
        
        repo_forks=0,
        slug=u'testability',
        repo_description=u'Increase your testing ability with this steroid free supplement.',
    )
    package2, created = Package.objects.get_or_create(
        pk=2,
        category=category,
        repo_watchers=0,
        title=u'Supertester',
        pypi_url='',
        participants=u'thetestman',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-uni-form',
        
        repo_forks=0,
        slug=u'supertester',
        repo_description=u'Test everything under the sun with one command!',
    )
    package3, created = Package.objects.get_or_create(
        pk=3,
        category=category,
        repo_watchers=0,
        title=u'Serious Testing',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/opencomparison/opencomparison',
        
        repo_forks=0,
        slug=u'serious-testing',
        repo_description=u'Make testing as painless as waxing your legs.',
    )
    package4, created = Package.objects.get_or_create(
        pk=4,
        category=category,
        repo_watchers=0,
        title=u'Another Test',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/djangopackages/djangopackages',
        
        repo_forks=0,
        slug=u'another-test',
        repo_description=u'Yet another test package, with no grid affiliation.',
    )

    grid1, created = Grid.objects.get_or_create(
        pk=1,
        description=u'A grid for testing.',
        title=u'Testing',
        is_locked=False,
        slug=u'testing',
    )
    grid2, created = Grid.objects.get_or_create(
        pk=2,
        description=u'Another grid for testing.',
        title=u'Another Testing',
        is_locked=False,
        slug=u'another-testing',
    )

    gridpackage1, created = GridPackage.objects.get_or_create(
        pk=1,
        package=package1,
        grid=grid1,
    )
    gridpackage2, created = GridPackage.objects.get_or_create(
        pk=2,
        package=package1,
        grid=grid1,
    )
    gridpackage3, created = GridPackage.objects.get_or_create(
        pk=3,
        package=package3,
        grid=grid1,
    )
    gridpackage4, created = GridPackage.objects.get_or_create(
        pk=4,
        package=package3,
        grid=grid2,
    )
    gridpackage5, created = GridPackage.objects.get_or_create(
        pk=5,
        package=package2,
        grid=grid1,
    )

    feature1, created = Feature.objects.get_or_create(
        pk=1,
        title=u'Has tests?',
        grid=grid1,
        description=u'Does this package come with tests?',
    )
    feature2, created = Feature.objects.get_or_create(
        pk=2,
        title=u'Coolness?',
        grid=grid1,
        description=u'Is this package cool?',
    )

    element, created = Element.objects.get_or_create(
        pk=1,
        text=u'Yes',
        feature=feature1,
        grid_package=gridpackage1,
    )

    group1, created = Group.objects.get_or_create(
        pk=1,
        name=u'Moderators',
        #permissions=[[u'delete_gridpackage', u'grid', u'gridpackage'], [u'delete_feature', u'grid', u'feature']],
    )
    group1.permissions.clear()
    group1.permissions = [
        Permission.objects.get(codename='delete_gridpackage'),
        Permission.objects.get(codename='delete_feature')
        ]

    user1, created = User.objects.get_or_create(
        pk=1,
        username=u'user',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$644c9$347f3dd85fb609a5745ebe33d0791929bf08f22e',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2, created = User.objects.get_or_create(
        pk=2,
        username=u'cleaner',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        #groups=[group1],
        password=u'sha1$e6fe2$78b744e21cddb39117997709218f4c6db4e91894',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2.groups = [group1]

    user3, created = User.objects.get_or_create(
        pk=3,
        username=u'staff',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$8894d$c4814980edd6778f0ab1632c4270673c0fd40efe',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user4, created = User.objects.get_or_create(
        pk=4,
        username=u'admin',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$52c7f$59b4f64ffca593e6abd23f90fd1f95cf71c367a4',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )

    packageexample, created = PackageExample.objects.get_or_create(
        pk=1,
        package=package1,
        url=u'http://www.example.com/',
        active=True,
        title=u'www.example.com',
    )
    for user in User.objects.all():
        profile = Profile.objects.create(user=user)

    datautil.reset_sequences(Grid, Group, User, Permission, Category, PackageExample,
                             Package, Element, Feature, GridPackage)


########NEW FILE########
__FILENAME__ = test_templatetags
from django.test import TestCase

from grid.templatetags.grid_tags import style_element, YES_IMG, NO_IMG, \
    YES_KEYWORDS, NO_KEYWORDS


class GridTest(TestCase):
    def test_01_style_element_filter(self):
        tests = [
            ('+', 1, 0, ''),
            ('++', 2, 0, ''),
            ('+++', 3, 0, ''),
            ('+1', 1, 0, ''),
            ('+2', 2, 0, ''),
            ('+3', 3, 0, ''),
            ('+4', 3, 0, ''),
            ('+42', 3, 0, ''),
            ('-', 0, 1, ''),
            ('--', 0, 2, ''),
            ('---', 0, 3, ''),
            ('-1', 0, 1, ''),
            ('-2', 0, 2, ''),
            ('-3', 0, 3, ''),
            ('-4', 0, 3, ''),
            ('-42', 0, 3, ''),
        ]
        for positive in YES_KEYWORDS:
            tests.append((positive, 1, 0, ''))
            tests.append(('%stest' % positive, 1, 0, 'test'))
        for negative in NO_KEYWORDS:
            tests.append((negative, 0, 1, ''))
            tests.append(('%stest' % negative, 0, 1, 'test'))
        for text, yes, no, endswith in tests:
            output = style_element(text)
            got_yes = output.count(YES_IMG)
            self.assertEqual(
                got_yes,
                yes,
                "%s resulted in %s yes-gifs instead of %s." % (text, got_yes, yes)
            )
            got_no = output.count(NO_IMG)
            self.assertEqual(
                got_no,
                no,
                "%s resulted in %s no-gifs instead of %s." % (text, got_no, no)
            )
            self.assertTrue(
                output.endswith(endswith),
                "Expected %s to end with %s, got %s instead." % (text, endswith, output)
            )

########NEW FILE########
__FILENAME__ = test_views
from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission

from grid.models import Grid, Element, Feature, GridPackage
from package.models import Package

from grid.tests import data


class FunctionalGridTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = False

    def test_grid_list_view(self):
        url = reverse('grids')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/grids.html')

    def test_grid_detail_view(self):
        url = reverse('grid', kwargs={'slug': 'testing'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/grid_detail.html')


    def test_add_grid_view(self):
        url = reverse('add_grid')
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/update_grid.html')

        # Test form post
        count = Grid.objects.count()
        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'slug': 'test-title',
            'description': 'Just a test description'
        }, follow=True)
        self.assertEqual(Grid.objects.count(), count + 1)
        self.assertContains(response, 'TEST TITLE')

    def test_edit_grid_view(self):
        url = reverse('edit_grid', kwargs={'slug': 'testing'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/update_grid.html')

        # Test form post
        count = Grid.objects.count()
        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'slug': 'testing',
            'description': 'Just a test description'
        }, follow=True)
        self.assertEqual(Grid.objects.count(), count)
        self.assertContains(response, 'TEST TITLE')

    def test_add_feature_view(self):
        url = reverse('add_feature', kwargs={'grid_slug': 'testing'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/update_feature.html')

        # Test form post
        count = Feature.objects.count()
        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'description': 'Just a test description'
        }, follow=True)
        self.assertEqual(Feature.objects.count(), count + 1)
        self.assertContains(response, 'TEST TITLE')

    def test_edit_feature_view(self):
        url = reverse('edit_feature', kwargs={'id': '1'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/update_feature.html')

        # Test form post
        count = Feature.objects.count()
        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'description': 'Just a test description'
        }, follow=True)
        self.assertEqual(Feature.objects.count(), count)
        self.assertContains(response, 'TEST TITLE')

    def test_delete_feature_view(self):
        count = Feature.objects.count()

        # Since this user doesn't have the appropriate permissions, none of the
        # features should be deleted (thus the count should be the same).
        self.assertTrue(self.client.login(username='user', password='user'))
        url = reverse('delete_feature', kwargs={'id': '1'})
        self.client.get(url)
        self.assertEqual(count, Feature.objects.count())

        # Once we log in with the appropriate user, the request should delete
        # the given feature, reducing the count by one.
        self.assertTrue(self.client.login(username='cleaner', password='cleaner'))
        self.client.get(url)
        self.assertEqual(Feature.objects.count(), count - 1)

    def test_edit_element_view(self):
        url = reverse('edit_element', kwargs={'feature_id': '1', 'package_id': '1'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/edit_element.html')

        # Test form post
        count = Element.objects.count()
        response = self.client.post(url, {
            'text': 'Some random text',
        }, follow=True)
        self.assertEqual(Element.objects.count(), count)
        self.assertContains(response, 'Some random text')

        # Confirm 404 if grid IDs differ
        url = reverse('edit_element', kwargs={'feature_id': '1', 'package_id': '4'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_add_grid_package_view(self):
        url = reverse('add_grid_package', kwargs={'grid_slug': 'testing'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/add_grid_package.html')

        # Test form post for existing grid package
        response = self.client.post(url, {
            'package': 2,
        })
        self.assertContains(response,
                            '&#39;Supertester&#39; is already in this grid.')
        # Test form post for new grid package
        count = GridPackage.objects.count()
        response = self.client.post(url, {
            'package': 4,
        }, follow=True)
        self.assertEqual(GridPackage.objects.count(), count + 1)
        self.assertContains(response, 'Another Test')

    def test_add_new_grid_package_view(self):
        url = reverse('add_new_grid_package', kwargs={'grid_slug': 'testing'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/package_form.html')

        # Test form post
        count = Package.objects.count()
        response = self.client.post(url, {
            'repo_url': 'http://www.example.com',
            'title': 'Test package',
            'slug': 'test-package',
            'pypi_url': 'http://pypi.python.org/pypi/mogo/0.1.1',
            'category': 1
        }, follow=True)
        self.assertEqual(Package.objects.count(), count + 1)
        self.assertContains(response, 'Test package')

    def test_ajax_grid_list_view(self):
        url = reverse('ajax_grid_list') + '?q=Testing&package_id=4'
        response = self.client.get(url)
        self.assertContains(response, 'Testing')

    def test_delete_gridpackage_view(self):
        count = GridPackage.objects.count()

        # Since this user doesn't have the appropriate permissions, none of the
        # features should be deleted (thus the count should be the same).
        self.assertTrue(self.client.login(username='user', password='user'))
        url = reverse('delete_grid_package', kwargs={'id': '1'})
        self.client.get(url)
        self.assertEqual(count, GridPackage.objects.count())

        # Once we log in with the appropriate user, the request should delete
        # the given feature, reducing the count by one.
        self.assertTrue(self.client.login(username='cleaner', password='cleaner'))
        self.client.get(url)
        self.assertEqual(count - 1, GridPackage.objects.count())


class RegressionGridTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = False

    def test_edit_element_view_for_nonexistent_elements(self):
        """Make sure that attempts to edit nonexistent elements succeed.

        """
        # Delete the element for the sepcified feature and package.
        element, created = Element.objects.get_or_create(feature=1, grid_package=1)
        element.delete()

        # Log in the test user and attempt to edit the element.
        self.assertTrue(self.client.login(username='user', password='user'))

        url = reverse('edit_element', kwargs={'feature_id': '1', 'package_id': '1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grid/edit_element.html')


class GridPermissionTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = True
        self.test_add_url = reverse('add_grid')
        self.test_edit_url = reverse('edit_grid', kwargs={'slug': 'testing'})
        self.login = self.client.login(username='user', password='user')
        self.user = User.objects.get(username='user')

    def test_add_grid_permission_fail(self):
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 403)

    def test_add_grid_permission_success(self):
        add_grid_perm = Permission.objects.get(codename='add_grid',
            content_type__app_label='grid')
        self.user.user_permissions.add(add_grid_perm)
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 200)

    def test_edit_grid_permission_fail(self):
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 403)

    def test_edit_grid_permission_success(self):
        edit_grid_perm = Permission.objects.get(codename='change_grid',
                content_type__app_label='grid')
        self.user.user_permissions.add(edit_grid_perm)
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 200)


class GridPackagePermissionTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = True
        self.test_add_url = reverse('add_grid_package',
                                    kwargs={'grid_slug': 'testing'})
        self.test_add_new_url = reverse('add_new_grid_package',
                                        kwargs={'grid_slug': 'testing'})
        self.test_delete_url = reverse('delete_grid_package',
                                       kwargs={'id': '1'})
        self.login = self.client.login(username='user', password='user')
        self.user = User.objects.get(username='user')

    def test_login(self):
        self.assertTrue(self.login)

    def test_add_grid_package_permission_fail(self):
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 403)

    def test_add_grid_package_permission_success(self):
        add_grid_perm = Permission.objects.get(codename='add_gridpackage',
                content_type__app_label='grid')
        self.user.user_permissions.add(add_grid_perm)
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 200)

    def test_add_new_grid_package_permission_fail(self):
        response = self.client.get(self.test_add_new_url)
        self.assertEqual(response.status_code, 403)

    def test_add_new_grid_package_permission_success(self):
        add_new_grid_perm = Permission.objects.get(codename='add_gridpackage',
                content_type__app_label='grid')
        self.user.user_permissions.add(add_new_grid_perm)
        response = self.client.get(self.test_add_new_url)
        self.assertEqual(response.status_code, 200)

    def test_delete_grid_package_permission_fail(self):
        response = self.client.get(self.test_delete_url)
        self.assertEqual(response.status_code, 302)

    def test_delete_grid_package_permission_success(self):
        delete_grid_perm = Permission.objects.get(codename='delete_gridpackage',
                content_type__app_label='grid')
        self.user.user_permissions.add(delete_grid_perm)
        response = self.client.get(self.test_delete_url)
        self.assertEqual(response.status_code, 302)


class GridFeaturePermissionTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = True
        self.test_add_url = reverse('add_feature',
                                    kwargs={'grid_slug': 'testing'})
        self.test_edit_url = reverse('edit_feature', kwargs={'id': '1'})
        self.test_delete_url = reverse('delete_feature',  kwargs={'id': '1'})
        self.login = self.client.login(username='user', password='user')
        self.user = User.objects.get(username='user')

    def test_add_feature_permission_fail(self):
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 403)

    def test_add_feature_permission_success(self):
        add_feature = Permission.objects.get(codename='add_feature',
                content_type__app_label='grid')
        self.user.user_permissions.add(add_feature)
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 200)

    def test_edit_feature_permission_fail(self):
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 403)

    def test_edit_feature_permission_success(self):
        edit_feature = Permission.objects.get(codename='change_feature',
                content_type__app_label='grid')
        self.user.user_permissions.add(edit_feature)
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 200)

    def test_delete_feature_permission_fail(self):
        response = self.client.get(self.test_delete_url)
        self.assertEqual(response.status_code, 302)

    def test_delete_feature_permission_success(self):
        delete_feature = Permission.objects.get(codename='delete_feature',
                content_type__app_label='grid')
        self.user.user_permissions.add(delete_feature)
        response = self.client.get(self.test_delete_url)
        self.assertEqual(response.status_code, 302)


class GridElementPermissionTest(TestCase):
    def setUp(self):
        data.load()
        settings.RESTRICT_GRID_EDITORS = True
        self.test_edit_url = reverse('edit_element',
                                     kwargs={'feature_id': '1',
                                             'package_id': '1'})
        self.login = self.client.login(username='user', password='user')
        self.user = User.objects.get(username='user')

    def test_edit_element_permission_fail(self):
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 403)

    def test_edit_element_permission_success(self):
        edit_element = Permission.objects.get(codename='change_element',
                content_type__app_label='grid')
        self.user.user_permissions.add(edit_element)
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 200)


########NEW FILE########
__FILENAME__ = urls
"""grid url patterns"""
from django.conf.urls import patterns, url

from grid import views

from grid.views import (
        add_feature,
        add_grid,
        add_grid_package,
        add_new_grid_package,
        ajax_grid_list,
        delete_feature,
        delete_grid_package,
        edit_element,
        edit_grid,
        edit_feature,
        grid_detail,
        grids
    )

urlpatterns = patterns("",

    url(
        regex='^add/$',
        view=add_grid,
        name='add_grid',
    ),

    url(
        regex='^(?P<slug>[-\w]+)/edit/$',
        view=edit_grid,
        name='edit_grid',
    ),

    url(
        regex='^element/(?P<feature_id>\d+)/(?P<package_id>\d+)/$',
        view=edit_element,
        name='edit_element',
    ),

    url(
        regex='^feature/add/(?P<grid_slug>[a-z0-9\-\_]+)/$',
        view=add_feature,
        name='add_feature',
    ),

    url(
        regex='^feature/(?P<id>\d+)/$',
        view=edit_feature,
        name='edit_feature',
    ),

    url(
        regex='^feature/(?P<id>\d+)/delete/$',
        view=delete_feature,
        name='delete_feature',
    ),

    url(
        regex='^package/(?P<id>\d+)/delete/$',
        view=delete_grid_package,
        name='delete_grid_package',
    ),

    url(
        regex='^(?P<grid_slug>[a-z0-9\-\_]+)/package/add/$',
        view=add_grid_package,
        name='add_grid_package',
    ),

    url(
        regex='^(?P<grid_slug>[a-z0-9\-\_]+)/package/add/new$',
        view=add_new_grid_package,
        name='add_new_grid_package',
    ),

    url(
        regex='^ajax_grid_list/$',
        view=ajax_grid_list,
        name='ajax_grid_list',
    ),


    url(
        regex='^$',
        view=grids,
        name='grids',
    ),

    url(
        regex='^g/(?P<slug>[-\w]+)/$',
        view=grid_detail,
        name='grid',
    ),

    url(
        regex='^g/(?P<slug>[-\w]+)/landscape/$',
        view=views.grid_detail_landscape,
        name='grid_landscape',
    ),
)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import hashlib
from django.utils.http import urlquote

TEMPLATE_FRAGMENT_KEY_TEMPLATE = 'template.cache.%s.%s'


def make_template_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join([urlquote(var) for var in vary_on])
    args = hashlib.md5(key)
    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())

########NEW FILE########
__FILENAME__ = views
"""views for the :mod:`grid` app"""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from rest_framework.generics import ListAPIView, RetrieveAPIView

from grid.forms import ElementForm, FeatureForm, GridForm, GridPackageForm
from grid.models import Element, Feature, Grid, GridPackage
from package.models import Package
from package.forms import PackageForm
from package.views import repo_data_for_js


def build_element_map(elements):
    # Horrifying two-level dict due to needing to use hash() function later
    element_map = {}
    for element in elements:
        element_map.setdefault(element.feature_id, {})
        element_map[element.feature_id][element.grid_package_id] = element
    return element_map


def grids(request, template_name="grid/grids.html"):
    """lists grids

    Template context:

    * ``grids`` - all grid objects
    """
    # annotations providing bad counts
    grids = Grid.objects.filter()
    grids = grids.prefetch_related("feature_set")
    grids = grids.annotate(gridpackage_count=Count('gridpackage'))
    return render(request, template_name, {'grids': grids, })


def grid_detail_landscape(request, slug, template_name="grid/grid_detail2.html"):
    """displays a grid in detail

    Template context:

    * ``grid`` - the grid object
    * ``elements`` - elements of the grid
    * ``features`` - feature set used in the grid
    * ``grid_packages`` - packages involved in the current grid
    """
    grid = get_object_or_404(Grid, slug=slug)
    features = grid.feature_set.all()

    grid_packages = grid.grid_packages.order_by("package__commit_list")

    elements = Element.objects.all() \
                .filter(feature__in=features,
                        grid_package__in=grid_packages)

    element_map = build_element_map(elements)

    # These attributes are how we determine what is displayed in the grid
    default_attributes = [('repo_description', 'Description'),
                ('category', 'Category'),
                ('pypi_downloads', 'Downloads'),
                ('last_updated', 'Last Updated'),
                ('pypi_version', 'Version'),
                ('repo', 'Repo'),
                ('commits_over_52', 'Commits'),
                ('repo_watchers', 'Repo watchers'),
                ('repo_forks', 'Forks'),
                ('participant_list', 'Participants'),
                ('license_latest', 'License')
            ]

    return render(request, template_name, {
            'grid': grid,
            'features': features,
            'grid_packages': grid_packages,
            'attributes': default_attributes,
            'elements': element_map,
        })


@login_required
def add_grid(request, template_name="grid/update_grid.html"):
    """Creates a new grid, requires user to be logged in.
    Works for both GET and POST request methods

    Template context:

    * ``form`` - an instance of :class:`~app.grid.forms.GridForm`
    """

    if not request.user.get_profile().can_add_grid:
        return HttpResponseForbidden("permission denied")

    new_grid = Grid()
    form = GridForm(request.POST or None, instance=new_grid)

    if form.is_valid():
        new_grid = form.save()
        return HttpResponseRedirect(reverse('grid', kwargs={'slug': new_grid.slug}))

    return render(request, template_name, {'form': form})


@login_required
def edit_grid(request, slug, template_name="grid/update_grid.html"):
    """View to modify the grid, handles GET and POST requests.
    This view requires user to be logged in.

    Template context:

    * ``form`` - instance of :class:`grid.forms.GridForm`
    """

    if not request.user.get_profile().can_edit_grid:
        return HttpResponseForbidden("permission denied")

    grid = get_object_or_404(Grid, slug=slug)
    form = GridForm(request.POST or None, instance=grid)

    if form.is_valid():
        grid = form.save()
        message = "Grid has been edited"
        messages.add_message(request, messages.INFO, message)
        return HttpResponseRedirect(reverse('grid', kwargs={'slug': grid.slug}))
    return render(request, template_name, {'form': form,  'grid': grid})


@login_required
def add_feature(request, grid_slug, template_name="grid/update_feature.html"):
    """Adds a feature to the grid, accepts GET and POST requests.

    Requires user to be logged in

    Template context:

    * ``form`` - instance of :class:`grid.forms.FeatureForm` form
    * ``grid`` - instance of :class:`grid.models.Grid` model
    """

    if not request.user.get_profile().can_add_grid_feature:
        return HttpResponseForbidden("permission denied")

    grid = get_object_or_404(Grid, slug=grid_slug)
    feature = Feature()
    form = FeatureForm(request.POST or None, instance=feature)

    if form.is_valid():
        feature = Feature(
                    grid=grid,
                    title=request.POST['title'],
                    description=request.POST['description']
                )
        feature.save()
        return HttpResponseRedirect(reverse('grid', kwargs={'slug': feature.grid.slug}))

    return render(request, template_name, {'form': form, 'grid': grid})


@login_required
def edit_feature(request, id, template_name="grid/update_feature.html"):
    """edits feature on a grid - this view has the same
    semantics as :func:`grid.views.add_feature`.

    Requires the user to be logged in.
    """

    if not request.user.get_profile().can_edit_grid_feature:
        return HttpResponseForbidden("permission denied")

    feature = get_object_or_404(Feature, id=id)
    form = FeatureForm(request.POST or None, instance=feature)

    if form.is_valid():
        feature = form.save()
        return HttpResponseRedirect(reverse('grid', kwargs={'slug': feature.grid.slug}))

    return render(request, template_name, {'form': form, 'grid': feature.grid})


@permission_required('grid.delete_feature')
def delete_feature(request, id, template_name="grid/edit_feature.html"):
    # do not need to check permission via profile because
    # we default to being strict about deleting
    """deletes a feature from the grid, ``id`` is id of the
    :class:`grid.models.Feature` model that is to be deleted

    Requires permission `grid.delete_feature`.

    Redirects to the parent :func:`grid.views.grid_detail`
    """

    feature = get_object_or_404(Feature, id=id)
    Element.objects.filter(feature=feature).delete()
    feature.delete()

    return HttpResponseRedirect(reverse('grid', kwargs={'slug': feature.grid.slug}))


@permission_required('grid.delete_gridpackage')
def delete_grid_package(request, id, template_name="grid/edit_feature.html"):
    """Deletes package from the grid, ``id`` is the id of the
    :class:`grid.models.GridPackage` instance

    Requires permission ``grid.delete_gridpackage``.

    Redirects to :func:`grid.views.grid_detail`.
    """

    # do not need to check permission via profile because
    # we default to being strict about deleting
    package = get_object_or_404(GridPackage, id=id)
    Element.objects.filter(grid_package=package).delete()
    package.delete()

    return HttpResponseRedirect(reverse('grid', kwargs={'slug': package.grid.slug}))


@login_required
def edit_element(request, feature_id, package_id, template_name="grid/edit_element.html"):

    if not request.user.get_profile().can_edit_grid_element:
        return HttpResponseForbidden("permission denied")

    feature = get_object_or_404(Feature, pk=feature_id)
    grid_package = get_object_or_404(GridPackage, pk=package_id)

    # Sanity check to make sure both the feature and grid_package are related to
    # the same grid!
    if feature.grid_id != grid_package.grid_id:
        raise Http404

    element, created = Element.objects.get_or_create(
                                    grid_package=grid_package,
                                    feature=feature
                                    )

    form = ElementForm(request.POST or None, instance=element)

    if form.is_valid():
        element = form.save()
        return HttpResponseRedirect(reverse('grid', kwargs={'slug': feature.grid.slug}))

    return render(request, template_name, {
        'form': form,
        'feature': feature,
        'package': grid_package.package,
        'grid': feature.grid
        })


@login_required
def add_grid_package(request, grid_slug, template_name="grid/add_grid_package.html"):
    """Add an existing package to this grid."""

    if not request.user.get_profile().can_add_grid_package:
        return HttpResponseForbidden("permission denied")

    grid = get_object_or_404(Grid, slug=grid_slug)
    grid_package = GridPackage()
    form = GridPackageForm(request.POST or None, instance=grid_package)

    if form.is_valid():
        package = get_object_or_404(Package, id=request.POST['package'])
        try:
            GridPackage.objects.get(grid=grid, package=package)
            message = "Sorry, but '%s' is already in this grid." % package.title
            messages.add_message(request, messages.ERROR, message)
        except GridPackage.DoesNotExist:
            grid_package = GridPackage(
                        grid=grid,
                        package=package
                    )
            grid_package.save()
            redirect = request.POST.get('redirect', '')
            if redirect:
                return HttpResponseRedirect(redirect)

            return HttpResponseRedirect(reverse('grid', kwargs={'slug': grid.slug}))

    return render(request, template_name, {
        'form': form,
        'grid': grid
        })


@login_required
def add_new_grid_package(request, grid_slug, template_name="package/package_form.html"):
    """Add a package to a grid that isn't yet represented on the site."""

    if not request.user.get_profile().can_add_grid_package:
        return HttpResponseForbidden("permission denied")

    grid = get_object_or_404(Grid, slug=grid_slug)

    new_package = Package()
    form = PackageForm(request.POST or None, instance=new_package)

    if form.is_valid():
        new_package = form.save()
        GridPackage.objects.create(
            grid=grid,
            package=new_package
        )
        return HttpResponseRedirect(reverse("grid", kwargs={"slug": grid_slug}))

    return render(request, template_name, {"form": form, "repo_data": repo_data_for_js(), "action": "add"})


def ajax_grid_list(request, template_name="grid/ajax_grid_list.html"):
    q = request.GET.get('q', '')
    grids = []
    if q:
        grids = Grid.objects.filter(title__istartswith=q)
        package_id = request.GET.get('package_id', '')
        if package_id:
            grids = grids.exclude(gridpackage__package__id=package_id)
    return render(request, template_name, {'grids': grids})


def grid_detail(request, slug, template_name="grid/grid_detail.html"):
    """displays a grid in detail

    Template context:

    * ``grid`` - the grid object
    * ``elements`` - elements of the grid
    * ``features`` - feature set used in the grid
    * ``grid_packages`` - packages involved in the current grid
    """
    grid = get_object_or_404(Grid, slug=slug)
    features = grid.feature_set.select_related()

    grid_packages = grid.grid_packages.order_by("-package__repo_watchers")

    elements = Element.objects.filter(feature__in=features,
                        grid_package__in=grid_packages)

    element_map = build_element_map(elements)

    # These attributes are how we determine what is displayed in the grid
    default_attributes = [('repo_description', 'Description'),
                ('category', 'Category'),
                ('pypi_downloads', 'Downloads'),
                ('last_updated', 'Last Updated'),
                ('pypi_version', 'Version'),
                ('repo', 'Repo'),
                ('commits_over_52', 'Commits'),
                ('repo_watchers', 'Repo watchers'),
                ('repo_forks', 'Forks'),
                ('participant_list', 'Participants'),
                ('license_latest', 'License')
            ]

    return render(request, template_name, {
            'grid': grid,
            'features': features,
            'grid_packages': grid_packages,
            'attributes': default_attributes,
            'elements': element_map,
        })


class GridListAPIView(ListAPIView):
    model = Grid
    paginate_by = 20


class GridDetailAPIView(RetrieveAPIView):
    model = Grid

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from homepage.models import Dpotw, Gotw, PSA

admin.site.register(Dpotw)
admin.site.register(Gotw)
admin.site.register(PSA)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    depends_on = (
            ("package", "0001_initial"),
            ("grid", "0001_initial"),            
        )    

    def forwards(self, orm):
        
        # Adding model 'Dpotw'
        db.create_table('homepage_dpotw', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('homepage', ['Dpotw'])

        # Adding model 'Gotw'
        db.create_table('homepage_gotw', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('grid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Grid'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('homepage', ['Gotw'])

        # Adding model 'Tab'
        db.create_table('homepage_tab', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('grid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Grid'])),
            ('order', self.gf('django.db.models.fields.IntegerField')(default='0')),
        ))
        db.send_create_signal('homepage', ['Tab'])


    def backwards(self, orm):
        
        # Deleting model 'Dpotw'
        db.delete_table('homepage_dpotw')

        # Deleting model 'Gotw'
        db.delete_table('homepage_gotw')

        # Deleting model 'Tab'
        db.delete_table('homepage_tab')


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
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'homepage.dpotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Dpotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.gotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Gotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.tab': {
            'Meta': {'ordering': "['order', 'grid']", 'object_name': 'Tab'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': "'0'"})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['homepage']

########NEW FILE########
__FILENAME__ = 0002_auto__del_tab
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    depends_on = (
            ("package", "0001_initial"),
            ("grid", "0001_initial"),            
        )    

    def forwards(self, orm):
        
        # Deleting model 'Tab'
        db.delete_table('homepage_tab')


    def backwards(self, orm):
        
        # Adding model 'Tab'
        db.create_table('homepage_tab', (
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('grid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grid.Grid'])),
            ('order', self.gf('django.db.models.fields.IntegerField')(default='0')),
        ))
        db.send_create_signal('homepage', ['Tab'])


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
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'homepage.dpotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Dpotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.gotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Gotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['homepage']

########NEW FILE########
__FILENAME__ = 0003_auto__add_psa
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PSA'
        db.create_table('homepage_psa', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('body_text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('homepage', ['PSA'])


    def backwards(self, orm):
        
        # Deleting model 'PSA'
        db.delete_table('homepage_psa')


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
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'homepage.dpotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Dpotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.gotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Gotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.psa': {
            'Meta': {'object_name': 'PSA'},
            'body_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['homepage']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_psa_created__add_field_psa_modified
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'PSA.created'
        db.add_column('homepage_psa', 'created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True), keep_default=False)

        # Adding field 'PSA.modified'
        db.add_column('homepage_psa', 'modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'PSA.created'
        db.delete_column('homepage_psa', 'created')

        # Deleting field 'PSA.modified'
        db.delete_column('homepage_psa', 'modified')


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
        'grid.grid': {
            'Meta': {'ordering': "['title']", 'object_name': 'Grid'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['package.Package']", 'through': "orm['grid.GridPackage']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'grid.gridpackage': {
            'Meta': {'object_name': 'GridPackage'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'homepage.dpotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Dpotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.gotw': {
            'Meta': {'ordering': "('-start_date', '-end_date')", 'object_name': 'Gotw'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'grid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grid.Grid']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'homepage.psa': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'PSA'},
            'body_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'})
        },
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['homepage']

########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from grid.models import Grid
from package.models import BaseModel, Package


class RotatorManager(models.Manager):

    def get_current(self):
        now = datetime.datetime.now()
        return self.get_query_set().filter(start_date__lte=now, end_date__gte=now)


class Dpotw(BaseModel):

    package = models.ForeignKey(Package)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))

    objects = RotatorManager()

    class Meta:
        ordering = ('-start_date', '-end_date',)
        get_latest_by = 'created'

        verbose_name = "Django Package of the Week"
        verbose_name_plural = "Django Packages of the Week"

    def __unicode__(self):
        return '%s : %s - %s' % (self.package.title, self.start_date, self.end_date)

    @models.permalink
    def get_absolute_url(self):
        return ("package", [self.package.slug])


class Gotw(BaseModel):

    grid = models.ForeignKey(Grid)

    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))

    objects = RotatorManager()

    class Meta:
        ordering = ('-start_date', '-end_date',)
        get_latest_by = 'created'

        verbose_name = "Grid of the Week"
        verbose_name_plural = "Grids of the Week"

    def __unicode__(self):
        return '%s : %s - %s' % (self.grid.title, self.start_date, self.end_date)

    @models.permalink
    def get_absolute_url(self):
        return ("grid", [self.grid.slug])


class PSA(BaseModel):
    """ Public Service Announcement on the homepage """

    body_text = models.TextField(_("PSA Body Text"), blank=True, null=True)

    class Meta:
        ordering = ('-created',)
        get_latest_by = 'created'

        verbose_name = "Public Service Announcement"
        verbose_name_plural = "Public Service Announcements"

    def __unicode__(self):
        return "{0} : {1}".format(self.created, self.body_text)

########NEW FILE########
__FILENAME__ = data
from grid.models import Grid
from django.contrib.auth.models import Group, User, Permission
from package.models import Category, PackageExample, Package
from grid.models import Element, Feature, GridPackage
from core.tests import datautil


def load():
    category, created = Category.objects.get_or_create(
        pk=1,
        slug=u'apps',
        title=u'App',
        description=u'Small components used to build projects.',
    )

    package1, created = Package.objects.get_or_create(
        pk=1,
        category=category,
        repo_watchers=0,
        title=u'Testability',
        pypi_url='',
        participants=u'malcomt,jacobian',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-la-facebook',
        
        repo_forks=0,
        slug=u'testability',
        repo_description=u'Increase your testing ability with this steroid free supplement.',
    )
    package2, created = Package.objects.get_or_create(
        pk=2,
        category=category,
        repo_watchers=0,
        title=u'Supertester',
        pypi_url='',
        participants=u'thetestman',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-uni-form',
        
        repo_forks=0,
        slug=u'supertester',
        repo_description=u'Test everything under the sun with one command!',
    )
    package3, created = Package.objects.get_or_create(
        pk=3,
        category=category,
        repo_watchers=0,
        title=u'Serious Testing',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/opencomparison/opencomparison',
        
        repo_forks=0,
        slug=u'serious-testing',
        repo_description=u'Make testing as painless as frozen yogurt.',
    )
    package4, created = Package.objects.get_or_create(
        pk=4,
        category=category,
        repo_watchers=0,
        title=u'Another Test',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/djangopackages/djangopackages',
        
        repo_forks=0,
        slug=u'another-test',
        repo_description=u'Yet another test package, with no grid affiliation.',
    )

    grid1, created = Grid.objects.get_or_create(
        pk=1,
        description=u'A grid for testing.',
        title=u'Testing',
        is_locked=False,
        slug=u'testing',
    )
    grid2, created = Grid.objects.get_or_create(
        pk=2,
        description=u'Another grid for testing.',
        title=u'Another Testing',
        is_locked=False,
        slug=u'another-testing',
    )

    gridpackage1, created = GridPackage.objects.get_or_create(
        pk=1,
        package=package1,
        grid=grid1,
    )
    gridpackage2, created = GridPackage.objects.get_or_create(
        pk=2,
        package=package1,
        grid=grid1,
    )
    gridpackage3, created = GridPackage.objects.get_or_create(
        pk=3,
        package=package3,
        grid=grid1,
    )
    gridpackage4, created = GridPackage.objects.get_or_create(
        pk=4,
        package=package3,
        grid=grid2,
    )
    gridpackage5, created = GridPackage.objects.get_or_create(
        pk=5,
        package=package2,
        grid=grid1,
    )

    feature1, created = Feature.objects.get_or_create(
        pk=1,
        title=u'Has tests?',
        grid=grid1,
        description=u'Does this package come with tests?',
    )
    feature2, created = Feature.objects.get_or_create(
        pk=2,
        title=u'Coolness?',
        grid=grid1,
        description=u'Is this package cool?',
    )

    element, created = Element.objects.get_or_create(
        pk=1,
        text=u'Yes',
        feature=feature1,
        grid_package=gridpackage1,
    )

    group1, created = Group.objects.get_or_create(
        pk=1,
        name=u'Moderators',
        #permissions=[[u'delete_gridpackage', u'grid', u'gridpackage'], [u'delete_feature', u'grid', u'feature']],
    )
    group1.permissions.clear()
    group1.permissions = [
        Permission.objects.get(codename='delete_gridpackage'),
        Permission.objects.get(codename='delete_feature')
        ]

    user1, created = User.objects.get_or_create(
        pk=1,
        username=u'user',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$644c9$347f3dd85fb609a5745ebe33d0791929bf08f22e',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2, created = User.objects.get_or_create(
        pk=2,
        username=u'cleaner',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        #groups=[group1],
        password=u'sha1$e6fe2$78b744e21cddb39117997709218f4c6db4e91894',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2.groups = [group1]

    user3, created = User.objects.get_or_create(
        pk=3,
        username=u'staff',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$8894d$c4814980edd6778f0ab1632c4270673c0fd40efe',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user4, created = User.objects.get_or_create(
        pk=4,
        username=u'admin',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$52c7f$59b4f64ffca593e6abd23f90fd1f95cf71c367a4',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )

    packageexample, created = PackageExample.objects.get_or_create(
        pk=1,
        package=package1,
        url=u'http://www.example.com/',
        active=True,
        title=u'www.example.com',
    )

    datautil.reset_sequences(Grid, Group, User, Permission, Category, PackageExample,
                             Package, Element, Feature, GridPackage)


########NEW FILE########
__FILENAME__ = test_views
from datetime import datetime, timedelta

from django.core.urlresolvers import reverse
from django.test import TestCase

from grid.models import Grid
from homepage.models import Dpotw, Gotw
from package.models import Package, Category

from homepage.tests import data


class FunctionalHomepageTest(TestCase):
    def setUp(self):
        data.load()

    def test_homepage_view(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage.html')

        for p in Package.objects.all():
            self.assertContains(response, p.title)
            self.assertContains(response, p.repo_description)

        self.assertEquals(response.context['package_count'], Package.objects.count())

    def test_categories_on_homepage(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage.html')

        for c in Category.objects.all():
            self.assertContains(response, c.title_plural)
            self.assertContains(response, c.description)

    def test_items_of_the_week(self):
        url = reverse('home')
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        p = Package.objects.all()[0]
        g = Grid.objects.all()[0]

        d_live = Dpotw.objects.create(package=p, start_date=yesterday, end_date=tomorrow)

        g_live = Gotw.objects.create(grid=g, start_date=yesterday, end_date=tomorrow)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage.html')
        self.assertContains(response, d_live.package.title)
        self.assertContains(response, g_live.grid.title)


class FunctionalHomepageTestWithoutPackages(TestCase):
    def setUp(self):
        data.load()

    def test_homepage_view(self):
        Package.objects.all().delete()
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage.html')


class TestErrorPages(TestCase):

    def test_404_test(self):
        r = self.client.get("/404")
        self.assertEquals(r.status_code, 404)

    def test_500_test(self):
        r = self.client.get("/500")
        self.assertEquals(r.status_code, 500)

########NEW FILE########
__FILENAME__ = views
from random import sample

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render

import feedparser

from core.decorators import lru_cache
from grid.models import Grid
from homepage.models import Dpotw, Gotw, PSA
from package.models import Category, Package, Version


@lru_cache()
def get_feed():
    feed = 'http://opencomparison.blogspot.com/feeds/posts/default'
    return feedparser.parse(feed)


def homepage(request, template_name="homepage.html"):

    categories = []
    for category in Category.objects.annotate(package_count=Count("package")):
        element = {
            "title": category.title,
            "description": category.description,
            "count": category.package_count,
            "slug": category.slug,
            "title_plural": category.title_plural,
            "show_pypi": category.show_pypi,
        }
        categories.append(element)

    # get up to 5 random packages
    package_count = Package.objects.count()
    random_packages = []
    if package_count > 1:
        package_ids = set([])

        # Get 5 random keys
        package_ids = sample(
            range(1, package_count + 1),  # generate a list from 1 to package_count +1
            min(package_count, 5)  # Get a sample of the smaller of 5 or the package count
        )

        # Get the random packages
        random_packages = Package.objects.filter(pk__in=package_ids)[:5]

    try:
        potw = Dpotw.objects.latest().package
    except Dpotw.DoesNotExist:
        potw = None
    except Package.DoesNotExist:
        potw = None

    try:
        gotw = Gotw.objects.latest().grid
    except Gotw.DoesNotExist:
        gotw = None
    except Grid.DoesNotExist:
        gotw = None

    # Public Service Announcement on homepage
    try:
        psa_body = PSA.objects.latest().body_text
    except PSA.DoesNotExist:
        psa_body = '<p>There are currently no announcements.  To request a PSA, tweet at <a href="http://twitter.com/open_comparison">@Open_Comparison</a>.</p>'

    # Latest Django Packages blog post on homepage

    feed_result = get_feed()
    if len(feed_result.entries):
        blogpost_title = feed_result.entries[0].title
        blogpost_body = feed_result.entries[0].summary
    else:
        blogpost_title = ''
        blogpost_body = ''

    return render(request,
        template_name, {
            "latest_packages": Package.objects.all().order_by('-created')[:5],
            "random_packages": random_packages,
            "potw": potw,
            "gotw": gotw,
            "psa_body": psa_body,
            "blogpost_title": blogpost_title,
            "blogpost_body": blogpost_body,
            "categories": categories,
            "package_count": package_count,
            "py3_compat": Package.objects.filter(version__supports_python3=True).select_related().distinct().count(),
            "latest_python3": Version.objects.filter(supports_python3=True).select_related("package").distinct().order_by("-created")[0:5]
        }
    )


def error_500_view(request):
    with open("templates/500.html") as f:
        text = f.read()
    response = HttpResponse(text)
    response.status_code = 500
    return response


def error_404_view(request):
    response = render(request, "404.html")
    response.status_code = 404
    return response


def py3_compat(request, template_name="py3_compat.html"):
    packages = Package.objects.filter(version__supports_python3=True)
    packages = packages.distinct()
    packages = packages.annotate(usage_count=Count("usage"))
    packages.order_by("-repo_watchers", "title")
    return render(request, template_name, {
        "packages": packages
        }
    )


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.base")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from reversion.admin import VersionAdmin

from package.models import Category, Package, PackageExample, Commit, Version


class PackageExampleInline(admin.TabularInline):
    model = PackageExample


class PackageAdmin(VersionAdmin):

    save_on_top = True
    search_fields = ("title",)
    list_filter = ("category",)
    list_display = ("title", "created", )
    date_hierarchy = "created"
    inlines = [
        PackageExampleInline,
    ]
    fieldsets = (
        (None, {
            "fields": ("title", "slug", "category", "pypi_url", "repo_url", "usage", "created_by", "last_modified_by",)
        }),
        ("Pulled data", {
            "classes": ("collapse",),
            "fields": ("repo_description", "repo_watchers", "repo_forks", "commit_list", "pypi_downloads", "participants")
        }),
    )


class CommitAdmin(admin.ModelAdmin):
    list_filter = ("package",)


class VersionLocalAdmin(admin.ModelAdmin):
    search_fields = ("package__title",)


class PackageExampleAdmin(admin.ModelAdmin):

    list_display = ("title", )
    search_fields = ("title",)


admin.site.register(Category, VersionAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Commit, CommitAdmin)
admin.site.register(Version, VersionLocalAdmin)
admin.site.register(PackageExample, PackageExampleAdmin)

########NEW FILE########
__FILENAME__ = apiv2
from django.db.models import Count

from rest_framework.generics import ListAPIView, RetrieveAPIView

from package.models import Category, Package
from package.serializers import PackageSerializer


class PackageListAPIView(ListAPIView):
    model = Package
    paginate_by = 20


class PackageDetailAPIView(RetrieveAPIView):
    model = Package


class CategoryListAPIView(ListAPIView):
    model = Category
    paginate_by = 200


class Python3ListAPIView(ListAPIView):
    model = Package
    serializer_class = PackageSerializer
    paginate_by = 200

    def get_queryset(self):
        packages = Package.objects.filter(version__supports_python3=True)
        packages = packages.distinct()
        packages = packages.annotate(usage_count=Count("usage"))
        packages.order_by("-repo_watchers", "title")
        return packages



########NEW FILE########
__FILENAME__ = context_processors
from django.core.cache import cache


def used_packages_list(request):
    context = {}
    if request.user.is_authenticated():
        cache_key = "sitewide_used_packages_list_%s" % request.user.pk
        used_packages_list = cache.get(cache_key)
        if used_packages_list is None:
            used_packages_list = request.user.package_set.values_list("pk", flat=True)
            cache.set(cache_key, used_packages_list, 60 * 60 * 24)
        context['used_packages_list'] = used_packages_list
    if 'used_packages_list' not in context:
        context['used_packages_list'] = []
    return context

########NEW FILE########
__FILENAME__ = forms
from floppyforms import ModelForm, TextInput

from package.models import Category, Package, PackageExample


def package_help_text():
    help_text = ""
    for category in Category.objects.all():
        help_text += """<li><strong>{title_plural}</strong> {description}</li>""".format(
                        title_plural=category.title_plural,
                        description=category.description
                        )
    help_text = "<ul>{0}</ul>".format(help_text)
    return help_text


class PackageForm(ModelForm):

    def __init__(self, *args, **kwargs):
            super(PackageForm, self).__init__(*args, **kwargs)
            self.fields['category'].help_text = package_help_text()
            self.fields['repo_url'].required = True
            self.fields['repo_url'].widget = TextInput(attrs={
                'placeholder': 'ex: https://github.com/django/django'
            })

    def clean_slug(self):
        return self.cleaned_data['slug'].lower()

    class Meta:
        model = Package
        fields = ['repo_url', 'title', 'slug', 'pypi_url', 'category', ]


class PackageExampleForm(ModelForm):

    class Meta:
        model = PackageExample
        fields = ['title', 'url']


class PackageExampleModeratorForm(ModelForm):

    class Meta:
        model = PackageExample
        fields = ['title', 'url', 'active']


class DocumentationForm(ModelForm):

    class Meta:
        model = Package
        fields = ["documentation_url", ]

########NEW FILE########
__FILENAME__ = commit_fixer
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

import requests
from github3 import login

from package.models import Package, Commit

github = login(settings.GITHUB_USERNAME, settings.GITHUB_PASSWORD)


class Command(BaseCommand):
    args = '<package_slug package_slug ...>'
    help = 'Fixes the commits for a package'

    def handle(self, *args, **options):
        for slug in args:
            try:
                package = Package.objects.get(slug=slug)
            except Package.DoesNotExist:
                raise CommandError('Package "%s" does not exist' % slug)

            while github.ratelimit_remaining < 10:
                self.stdout.write("Sleeping...")
                sleep(1)

            repo_name = package.repo_name()
            if repo_name.endswith("/"):
                repo_name = repo_name[:-1]
            try:
                username, repo_name = package.repo_name().split('/')
            except ValueError:
                self.stdout.write('Bad GitHub link on "%s"' % package)
                continue

            self.stdout.write('Getting old GitHub commits for "%s"\n' % package)
            next_url = 'https://api.github.com/repos/{}/{}/commits?per_page=100'.format(
                username, repo_name
            )
            while next_url:
                self.stdout.write(next_url + "\n")
                response = requests.get(url=next_url,
                    auth=(settings.GITHUB_USERNAME, settings.GITHUB_PASSWORD)
                )
                if response.status_code == 200:
                    if 'next' in response.links:
                            next_url = response.links['next']['url'] + "&per_page=100"
                    else:
                        next_url = ''

                    commit = None
                    for commit in [x['commit'] for x in response.json()]:
                        try:
                            commit, created = Commit.objects.get_or_create(
                                package=package,
                                commit_date=commit['committer']['date']
                            )
                        except Commit.MultipleObjectsReturned:
                            pass

                    if commit is not None:
                        new_commit = Commit.objects.get(pk=commit.pk)
                        if new_commit.commit_date < timezone.now() - timezone.timedelta(days=365):
                            self.stdout.write("Last commit recorded at {}\n".format(commit.commit_date))
                            break
                else:
                    self.stdout.write("Status code is {}".format(response.status_code))
                    break

                package.last_fetched = timezone.now()
            package.save()
            self.stdout.write('Successfully fixed commits on "%s"' % package.slug)

########NEW FILE########
__FILENAME__ = package_updater
import logging
import logging.config
from time import sleep

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.core.mail import send_mail

from github3 import login as github_login

from package.models import Package

logger = logging.getLogger(__name__)


class PackageUpdaterException(Exception):
    def __init__(self, error, title):
        log_message = "For {title}, {error_type}: {error}".format(
            title=title,
            error_type=type(error),
            error=error
        )
        logging.critical(log_message)
        logging.exception(error)


class Command(NoArgsCommand):

    help = "Updates all the packages in the system. Commands belongs to django-packages.package"

    def handle(self, *args, **options):

        github = github_login(settings.GITHUB_USERNAME, settings.GITHUB_PASSWORD)

        for index, package in enumerate(Package.objects.iterator()):

            # Simple attempt to deal with Github rate limiting
            while True:
                if github.ratelimit_remaining() < 50:
                    sleep(120)
                break

            try:
                try:
                    package.fetch_metadata(fetch_metadata=False)
                    package.fetch_commits()
                except Exception as e:
                    raise PackageUpdaterException(e, package.title)
            except PackageUpdaterException:
                pass  # We've already caught the error so let's move on now

            sleep(5)

        message = "TODO - load logfile here"  # TODO
        send_mail(
            subject="Package Updating complete",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[x[1] for x in settings.ADMINS]
        )

########NEW FILE########
__FILENAME__ = pypi_updater
import logging
import logging.config

from django.core.management.base import NoArgsCommand


from package.models import Package

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):

    help = "Updates all the packages in the system by checking against their PyPI data."

    def handle(self, *args, **options):

        count = 0
        count_updated = 0
        for package in Package.objects.filter().iterator():

            updated = package.fetch_pypi_data()
            if updated:
                count_updated += 1
                package.save()
            print package.slug, updated
            count += 1
            # msg = "{}. {}. {}".format(count, count_updated, package)
            # logger.info(msg)


########NEW FILE########
__FILENAME__ = repo_updater
import logging
import logging.config

from django.core.management.base import NoArgsCommand
from django.utils import timezone

from package.models import Package

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):

    help = "Updates all the packages in the system focusing on repo data"

    def handle(self, *args, **options):

        yesterday = timezone.now() - timezone.timedelta(1)
        for package in Package.objects.filter().iterator():
            # keep this here because for now we only have one last_fetched field.
            package.repo.fetch_metadata(package, fetch_pypi=False)
            if package.last_fetched <= yesterday:
                continue
            package.repo.fetch_commits(package)
            # if package.repo.title == "Github":
            #     msg = "{}. {}. {}".format(count, package.repo.github.ratelimit_remaining, package)
            # else:
            #     msg = "{}. {}".format(count, package)
            # logger.info(msg)

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
        db.create_table('package_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='50')),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('package', ['Category'])

        # Adding model 'Repo'
        db.create_table('package_repo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('is_supported', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='50')),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('package', ['Repo'])

        # Adding model 'Package'
        db.create_table('package_package', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='100')),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Category'])),
            ('repo', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Repo'], null=True)),
            ('repo_description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('repo_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('repo_watchers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('repo_forks', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('repo_commits', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('pypi_url', self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True)),
            ('pypi_version', self.gf('django.db.models.fields.CharField')(max_length='20', blank=True)),
            ('pypi_downloads', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('participants', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('package', ['Package'])

        # Adding M2M table for field related_packages on 'Package'
        db.create_table('package_package_related_packages', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_package', models.ForeignKey(orm['package.package'], null=False)),
            ('to_package', models.ForeignKey(orm['package.package'], null=False))
        ))
        db.create_unique('package_package_related_packages', ['from_package_id', 'to_package_id'])

        # Adding model 'PackageExample'
        db.create_table('package_packageexample', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='100')),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('package', ['PackageExample'])

        # Adding model 'Commit'
        db.create_table('package_commit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'])),
            ('commit_date', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('package', ['Commit'])


    def backwards(self, orm):
        
        # Deleting model 'Category'
        db.delete_table('package_category')

        # Deleting model 'Repo'
        db.delete_table('package_repo')

        # Deleting model 'Package'
        db.delete_table('package_package')

        # Removing M2M table for field related_packages on 'Package'
        db.delete_table('package_package_related_packages')

        # Deleting model 'PackageExample'
        db.delete_table('package_packageexample')

        # Deleting model 'Commit'
        db.delete_table('package_commit')


    models = {
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_category_title_plural__add_field_repo_is_other__add_fi
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.title_plural'
        db.add_column('package_category', 'title_plural', self.gf('django.db.models.fields.CharField')(default='', max_length='50', blank=True), keep_default=False)

        # Adding field 'Repo.is_other'
        db.add_column('package_repo', 'is_other', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'Repo.user_regex'
        db.add_column('package_repo', 'user_regex', self.gf('django.db.models.fields.CharField')(default='', max_length='100', blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.title_plural'
        db.delete_column('package_category', 'title_plural')

        # Deleting field 'Repo.is_other'
        db.delete_column('package_repo', 'is_other')

        # Deleting field 'Repo.user_regex'
        db.delete_column('package_repo', 'user_regex')


    models = {
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_repo_repo_regex__add_field_repo_handler
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Repo.repo_regex'
        db.add_column('package_repo', 'repo_regex', self.gf('django.db.models.fields.CharField')(default='', max_length='100', blank=True), keep_default=False)

        # Adding field 'Repo.handler'
        db.add_column('package_repo', 'handler', self.gf('django.db.models.fields.CharField')(default='', max_length='200'), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Repo.repo_regex'
        db.delete_column('package_repo', 'repo_regex')

        # Deleting field 'Repo.handler'
        db.delete_column('package_repo', 'handler')


    models = {
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_repo_slug_regex
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Repo.slug_regex'
        db.add_column('package_repo', 'slug_regex', self.gf('django.db.models.fields.CharField')(default='', max_length='100', blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Repo.slug_regex'
        db.delete_column('package_repo', 'slug_regex')


    models = {
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0005_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding M2M table for field usage on 'Package'
        db.create_table('package_package_usage', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('package', models.ForeignKey(orm['package.package'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('package_package_usage', ['package_id', 'user_id'])


    def backwards(self, orm):
        
        # Removing M2M table for field usage on 'Package'
        db.delete_table('package_package_usage')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0006_auto__add_version
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Version'
        db.create_table('package_version', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'])),
            ('number', self.gf('django.db.models.fields.CharField')(max_length='100')),
            ('downloads', self.gf('django.db.models.fields.IntegerField')()),
            ('license', self.gf('django.db.models.fields.CharField')(max_length='100')),
        ))
        db.send_create_signal('package', ['Version'])


    def backwards(self, orm):
        
        # Deleting model 'Version'
        db.delete_table('package_version')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_version_package
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Version.package'
        db.alter_column('package_version', 'package_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package'], null=True))


    def backwards(self, orm):
        
        # Changing field 'Version.package'
        db.alter_column('package_version', 'package_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Package']))


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_version_hidden
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Version.hidden'
        db.add_column('package_version', 'hidden', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Version.hidden'
        db.delete_column('package_version', 'hidden')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_package_created_by__add_field_package_last_modified_by
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Package.created_by'
        db.add_column('package_package', 'created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='creator', null=True, to=orm['auth.User']), keep_default=False)

        # Adding field 'Package.last_modified_by'
        db.add_column('package_package', 'last_modified_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='modifier', null=True, to=orm['auth.User']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Package.created_by'
        db.delete_column('package_package', 'created_by_id')

        # Deleting field 'Package.last_modified_by'
        db.delete_column('package_package', 'last_modified_by_id')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_category_show_pypi
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.show_pypi'
        db.add_column('package_category', 'show_pypi', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.show_pypi'
        db.delete_column('package_category', 'show_pypi')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'pypi_version': ('django.db.models.fields.CharField', [], {'max_length': "'20'", 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0011_auto__del_field_package_pypi_version
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Package.pypi_version'
        db.delete_column('package_package', 'pypi_version')


    def backwards(self, orm):
        
        # Adding field 'Package.pypi_version'
        db.add_column('package_package', 'pypi_version', self.gf('django.db.models.fields.CharField')(default='', max_length='20', blank=True), keep_default=False)


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0012_auto__add_unique_package_repo_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Package', fields ['repo_url']
        db.create_unique('package_package', ['repo_url'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Package', fields ['repo_url']
        db.delete_unique('package_package', ['repo_url'])


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0013_auto__add_field_repo_user_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Repo.user_url'
        db.add_column('package_repo', 'user_url', self.gf('django.db.models.fields.CharField')(default='', max_length='100', blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Repo.user_url'
        db.delete_column('package_repo', 'user_url')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'user_url': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-number']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0014_auto__add_field_package_pypi_home_page
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Package.pypi_home_page'
        db.add_column('package_package', 'pypi_home_page', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Package.pypi_home_page'
        db.delete_column('package_package', 'pypi_home_page')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Repo']", 'null': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.repo': {
            'Meta': {'ordering': "['-is_supported', 'title']", 'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'default': "'package.handlers.unsupported'", 'max_length': "'200'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_other': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_supported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'repo_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'slug_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user_regex': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'}),
            'user_url': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'blank': 'True'})
        },
        'package.version': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0015_auto__del_repo__del_field_package_repo
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Repo'
        db.delete_table('package_repo')

        # Deleting field 'Package.repo'
        db.delete_column('package_package', 'repo_id')


    def backwards(self, orm):
        
        # Adding model 'Repo'
        db.create_table('package_repo', (
            ('slug_regex', self.gf('django.db.models.fields.CharField')(max_length='100', blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user_url', self.gf('django.db.models.fields.CharField')(max_length='100', blank=True)),
            ('handler', self.gf('django.db.models.fields.CharField')(default='package.handlers.unsupported', max_length='200')),
            ('repo_regex', self.gf('django.db.models.fields.CharField')(max_length='100', blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='50')),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('is_supported', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user_regex', self.gf('django.db.models.fields.CharField')(max_length='100', blank=True)),
            ('is_other', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('package', ['Repo'])

        # Adding field 'Package.repo'
        db.add_column('package_package', 'repo', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['package.Repo'], null=True), keep_default=False)


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_home_page': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'related_packages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_packages_rel_+'", 'blank': 'True', 'to': "orm['package.Package']"}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0016_auto__del_field_package_pypi_home_page
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Package.pypi_home_page'
        db.delete_column('package_package', 'pypi_home_page')

        # Removing M2M table for field related_packages on 'Package'
        db.delete_table('package_package_related_packages')


    def backwards(self, orm):
        
        # Adding field 'Package.pypi_home_page'
        db.add_column('package_package', 'pypi_home_page', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True), keep_default=False)

        # Adding M2M table for field related_packages on 'Package'
        db.create_table('package_package_related_packages', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_package', models.ForeignKey(orm['package.package'], null=False)),
            ('to_package', models.ForeignKey(orm['package.package'], null=False))
        ))
        db.create_unique('package_package_related_packages', ['from_package_id', 'to_package_id'])


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0017_auto__add_field_version_upload_time
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Version.upload_time'
        db.add_column('package_version', 'upload_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Version.upload_time'
        db.delete_column('package_version', 'upload_time')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0018_auto__add_field_commit_commit_hash
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Commit.commit_hash'
        db.add_column('package_commit', 'commit_hash', self.gf('django.db.models.fields.CharField')(default='', max_length=150, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Commit.commit_hash'
        db.delete_column('package_commit', 'commit_hash')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']

########NEW FILE########
__FILENAME__ = 0019_auto__add_field_package_commit_list__chg_field_package_created_by__chg
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.commit_list'
        db.add_column('package_package', 'commit_list',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


        # Changing field 'Package.created_by'
        db.alter_column('package_package', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, on_delete=models.SET_NULL, to=orm['auth.User']))

        # Changing field 'Package.last_modified_by'
        db.alter_column('package_package', 'last_modified_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, on_delete=models.SET_NULL, to=orm['auth.User']))

    def backwards(self, orm):
        # Deleting field 'Package.commit_list'
        db.delete_column('package_package', 'commit_list')


        # Changing field 'Package.created_by'
        db.alter_column('package_package', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

        # Changing field 'Package.last_modified_by'
        db.alter_column('package_package', 'last_modified_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = 0020_auto__add_field_version_development_status
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Version.development_status'
        db.add_column('package_version', 'development_status',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Version.development_status'
        db.delete_column('package_version', 'development_status')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'development_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = 0021_auto__add_field_version_supports_python3
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Version.supports_python3'
        db.add_column('package_version', 'supports_python3',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Version.supports_python3'
        db.delete_column('package_version', 'supports_python3')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_commits': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'development_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'supports_python3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = 0022_auto__del_field_package_repo_commits
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Package.repo_commits'
        db.delete_column('package_package', 'repo_commits')


    def backwards(self, orm):
        # Adding field 'Package.repo_commits'
        db.add_column('package_package', 'repo_commits',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'development_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'supports_python3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = 0023_auto__add_field_package_last_fetched
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.last_fetched'
        db.add_column('package_package', 'last_fetched',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Package.last_fetched'
        db.delete_column('package_package', 'last_fetched')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_fetched': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'development_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'supports_python3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = 0024_auto__add_field_package_documentation_url
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.documentation_url'
        db.add_column('package_package', 'documentation_url',
                      self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Package.documentation_url'
        db.delete_column('package_package', 'documentation_url')


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
        'package.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'show_pypi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'title_plural': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'})
        },
        'package.commit': {
            'Meta': {'ordering': "['-commit_date']", 'object_name': 'Commit'},
            'commit_date': ('django.db.models.fields.DateTimeField', [], {}),
            'commit_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"})
        },
        'package.package': {
            'Meta': {'ordering': "['title']", 'object_name': 'Package'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Category']"}),
            'commit_list': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'documentation_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_fetched': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'last_modified_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modifier'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pypi_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'repo_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'package.packageexample': {
            'Meta': {'ordering': "['title']", 'object_name': 'PackageExample'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'package.version': {
            'Meta': {'ordering': "['-upload_time']", 'object_name': 'Version'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'development_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': "'100'", 'blank': "''"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['package.Package']", 'null': 'True', 'blank': 'True'}),
            'supports_python3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['package']
########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta
import json
import re

from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from distutils.version import LooseVersion as versioner
import requests

from core.utils import STATUS_CHOICES, status_choices_switch
from core.models import BaseModel
from package.repos import get_repo_for_repo_url
from package.signals import signal_fetch_latest_metadata
from package.utils import get_version, get_pypi_version, normalize_license

repo_url_help_text = settings.PACKAGINATOR_HELP_TEXT['REPO_URL']
pypi_url_help_text = settings.PACKAGINATOR_HELP_TEXT['PYPI_URL']


class NoPyPiVersionFound(Exception):
    pass


class Category(BaseModel):

    title = models.CharField(_("Title"), max_length="50")
    slug = models.SlugField(_("slug"))
    description = models.TextField(_("description"), blank=True)
    title_plural = models.CharField(_("Title Plural"), max_length="50", blank=True)
    show_pypi = models.BooleanField(_("Show pypi stats & version"), default=True)

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Categories'

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ("category", [self.slug])


class Package(BaseModel):

    title = models.CharField(_("Title"), max_length="100")
    slug = models.SlugField(_("Slug"), help_text="Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens. Values will be converted to lowercase.", unique=True)
    category = models.ForeignKey(Category, verbose_name="Installation")
    repo_description = models.TextField(_("Repo Description"), blank=True)
    repo_url = models.URLField(_("repo URL"), help_text=repo_url_help_text, blank=True, unique=True, verify_exists=True)
    repo_watchers = models.IntegerField(_("repo watchers"), default=0)
    repo_forks = models.IntegerField(_("repo forks"), default=0)
    pypi_url = models.URLField(_("PyPI slug"), help_text=pypi_url_help_text, blank=True, default='', verify_exists=True)
    pypi_downloads = models.IntegerField(_("Pypi downloads"), default=0)
    participants = models.TextField(_("Participants"),
                        help_text="List of collaborats/participants on the project", blank=True)
    usage = models.ManyToManyField(User, blank=True)
    created_by = models.ForeignKey(User, blank=True, null=True, related_name="creator", on_delete=models.SET_NULL)
    last_modified_by = models.ForeignKey(User, blank=True, null=True, related_name="modifier", on_delete=models.SET_NULL)
    last_fetched = models.DateTimeField(blank=True, null=True, default=timezone.now)
    documentation_url = models.URLField(_("Documentation URL"), blank=True, null=True, default="")

    commit_list = models.TextField(_("Commit List"), blank=True)

    @property
    def pypi_name(self):
        """ return the pypi name of a package"""

        if not self.pypi_url.strip():
            return ""

        name = self.pypi_url.replace("http://pypi.python.org/pypi/", "")
        if "/" in name:
            return name[:name.index("/")]
        return name

    def last_updated(self):
        cache_name = self.cache_namer(self.last_updated)
        last_commit = cache.get(cache_name)
        if last_commit is not None:
            return last_commit
        try:
            last_commit = self.commit_set.latest('commit_date').commit_date
            if last_commit:
                cache.set(cache_name, last_commit)
                return last_commit
        except ObjectDoesNotExist:
            last_commit = None

        return last_commit

    @property
    def repo(self):
        return get_repo_for_repo_url(self.repo_url)

    @property
    def active_examples(self):
        return self.packageexample_set.filter(active=True)

    @property
    def license_latest(self):
        try:
            return self.version_set.latest().license
        except Version.DoesNotExist:
            return "UNKNOWN"

    def grids(self):

        return (x.grid for x in self.gridpackage_set.all())

    def repo_name(self):
        return re.sub(self.repo.url_regex, '', self.repo_url)

    def repo_info(self):
        return dict(
            username=self.repo_name().split('/')[0],
            repo_name=self.repo_name().split('/')[1],
        )

    def participant_list(self):

        return self.participants.split(',')

    def get_usage_count(self):
        return self.usage.count()

    def commits_over_52(self):
        cache_name = self.cache_namer(self.commits_over_52)
        value = cache.get(cache_name)
        if value is not None:
            return value
        now = datetime.now()
        commits = self.commit_set.filter(
            commit_date__gt=now - timedelta(weeks=52),
        ).values_list('commit_date', flat=True)

        weeks = [0] * 52
        for cdate in commits:
            age_weeks = (now - cdate).days // 7
            if age_weeks < 52:
                weeks[age_weeks] += 1

        value = ','.join(map(str, reversed(weeks)))
        cache.set(cache_name, value)
        return value

    def fetch_pypi_data(self, *args, **kwargs):
        # Get the releases from pypi
        if self.pypi_url.strip() and self.pypi_url != "http://pypi.python.org/pypi/":

            total_downloads = 0
            url = "https://pypi.python.org/pypi/{0}/json".format(self.pypi_name)
            response = requests.get(url)
            if settings.DEBUG:
                if response.status_code not in (200, 404):
                    print("BOOM!")
                    print(self, response.status_code)
            if response.status_code == 404:
                if settings.DEBUG:
                    print("BOOM!")
                    print(self, response.status_code)
                return False
            release = json.loads(response.content)
            info = release['info']

            version, created = Version.objects.get_or_create(
                package=self,
                number=info['version']
            )

            # add to versions
            license = info['license']
            if not info['license'] or not license.strip()  or 'UNKNOWN' == license.upper():
                for classifier in info['classifiers']:
                    if classifier.strip().startswith('License'):
                        # Do it this way to cover people not quite following the spec
                        # at http://docs.python.org/distutils/setupscript.html#additional-meta-data
                        license = classifier.strip().replace('License ::', '')
                        license = license.replace('OSI Approved :: ', '')
                        break

            if license and len(license) > 100:
                license = "Other (see http://pypi.python.org/pypi/%s)" % self.pypi_name

            version.license = license

            #version stuff
            try:
                url_data = release['urls'][0]
                version.downloads = url_data['downloads']
                version.upload_time = url_data['upload_time']
            except IndexError:
                # Not a real release so we just guess the upload_time.
                version.upload_time = version.created

            version.hidden = info['_pypi_hidden']
            for classifier in info['classifiers']:
                if classifier.startswith('Development Status'):
                    version.development_status = status_choices_switch(classifier)
                    break
            for classifier in info['classifiers']:
                if classifier.startswith('Programming Language :: Python :: 3'):
                    version.supports_python3 = True
                    break
            version.save()

            self.pypi_downloads = total_downloads
            # Calculate total downloads

            return True
        return False

    def fetch_metadata(self, fetch_pypi=True, fetch_repo=True):

        if fetch_pypi:
            self.fetch_pypi_data()
        if fetch_repo:
            self.repo.fetch_metadata(self)
        signal_fetch_latest_metadata.send(sender=self)
        self.save()

    def grid_clear_detail_template_cache(self):
        for grid in self.grids():
            grid.clear_detail_template_cache()

    def save(self, *args, **kwargs):
        if not self.repo_description:
            self.repo_description = ""
        self.grid_clear_detail_template_cache()
        super(Package, self).save(*args, **kwargs)

    def fetch_commits(self):
        self.repo.fetch_commits(self)

    def pypi_version(self):
        cache_name = self.cache_namer(self.pypi_version)
        version = cache.get(cache_name)
        if version is not None:
            return version
        version = get_pypi_version(self)
        cache.set(cache_name, version)
        return version

    def last_released(self):
        cache_name = self.cache_namer(self.last_released)
        version = cache.get(cache_name)
        if version is not None:
            return version
        version = get_version(self)
        cache.set(cache_name, version)
        return version

    @property
    def development_status(self):
        """ Gets data needed in API v2 calls """
        return self.last_released().pretty_status


    @property
    def pypi_ancient(self):
        release = self.last_released()
        if release:
            return release.upload_time < datetime.now() - timedelta(365)
        return None

    @property
    def no_development(self):
        commit_date = self.last_updated()
        if commit_date is not None:
            return commit_date < datetime.now() - timedelta(365)
        return None

    class Meta:
        ordering = ['title']
        get_latest_by = 'id'

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ("package", [self.slug])


class PackageExample(BaseModel):

    package = models.ForeignKey(Package)
    title = models.CharField(_("Title"), max_length="100")
    url = models.URLField(_("URL"))
    active = models.BooleanField(_("Active"), default=True, help_text="Moderators have to approve links before they are provided")

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return self.title
        
    @property
    def pretty_url(self):
        if self.url.startswith("http"):
            return self.url
        return "http://" + self.url


class Commit(BaseModel):

    package = models.ForeignKey(Package)
    commit_date = models.DateTimeField(_("Commit Date"))
    commit_hash = models.CharField(_("Commit Hash"), help_text="Example: Git sha or SVN commit id", max_length=150, blank=True, default="")

    class Meta:
        ordering = ['-commit_date']
        get_latest_by = 'commit_date'

    def __unicode__(self):
        return "Commit for '%s' on %s" % (self.package.title, unicode(self.commit_date))

    def save(self, *args, **kwargs):
        # reset the last_updated and commits_over_52 caches on the package
        package = self.package
        cache.delete(package.cache_namer(self.package.last_updated))
        cache.delete(package.cache_namer(package.commits_over_52))
        self.package.last_updated()
        super(Commit, self).save(*args, **kwargs)


class VersionManager(models.Manager):
    def by_version(self, *args, **kwargs):
        qs = self.get_query_set().filter(*args, **kwargs)
        return sorted(qs, key=lambda v: versioner(v.number))

    def by_version_not_hidden(self, *args, **kwargs):
        qs = self.get_query_set().filter(*args, **kwargs)
        qs = qs.filter(hidden=False)
        qs = sorted(qs, key=lambda v: versioner(v.number))
        qs.reverse()
        return qs


class Version(BaseModel):

    package = models.ForeignKey(Package, blank=True, null=True)
    number = models.CharField(_("Version"), max_length="100", default="", blank="")
    downloads = models.IntegerField(_("downloads"), default=0)
    license = models.CharField(_("license"), max_length="100")
    hidden = models.BooleanField(_("hidden"), default=False)
    upload_time = models.DateTimeField(_("upload_time"), help_text=_("When this was uploaded to PyPI"), blank=True, null=True)
    development_status = models.IntegerField(_("Development Status"), choices=STATUS_CHOICES, default=0)
    supports_python3 = models.BooleanField(_("Supports Python 3"), default=False)

    objects = VersionManager()

    class Meta:
        get_latest_by = 'upload_time'
        ordering = ['-upload_time']

    @property
    def pretty_license(self):
        return self.license.replace("License", "").replace("license", "")

    @property
    def pretty_status(self):
        return self.get_development_status_display().split(" ")[-1]

    def save(self, *args, **kwargs):
        self.license = normalize_license(self.license)

        # reset the latest_version cache on the package
        cache_name = self.package.cache_namer(self.package.last_released)
        cache.delete(cache_name)
        get_version(self.package)

        # reset the pypi_version cache on the package
        cache_name = self.package.cache_namer(self.package.pypi_version)
        cache.delete(cache_name)
        get_pypi_version(self.package)

        super(Version, self).save(*args, **kwargs)

    def __unicode__(self):
        return "%s: %s" % (self.package.title, self.number)

########NEW FILE########
__FILENAME__ = base_handler
""" 
Base class for objects that interact with third-party code repository services.
"""

import json

import requests


class BaseHandler(object):

    def __str__(self):
        return self.title

    @property
    def title(self):
        """ title for display in drop downs:

                return: string
                example: 'Github'
        """
        return NotImplemented

    @property
    def url(self):
        """ base value for url API interation:

                return: URL string
                example: 'https://github.com'
        """
        return NotImplemented

    def fetch_metadata(self, package):
        """ Accepts a package.models.Package instance:

                return: package.models.Package instance

            Must set the following fields:

                package.repo_watchers (int)
                package.repo_forks (int)
                package.repo_description (text )
                package.participants = (comma-seperated value)

        """
        return NotImplemented

    def fetch_commits(self, package):
        """ Accepts a package.models.Package instance:
        """
        return NotImplemented

    @property
    def is_other(self):
        """ DON'T CHANGE THIS PROPERTY! This should only be overridden by
        the unsupported handler.

                return: False
        """
        return False

    @property
    def user_url(self):
        """ identifies the user URL:

                example:
        """
        return ''

    @property
    def repo_regex(self):
        """ Used by the JavaScript forms """
        return NotImplemented

    @property
    def slug_regex(self):
        """ Used by the JavaScript forms """
        return NotImplemented

    def packages_for_profile(self, profile):
        """ Return a list of all packages contributed to by a profile. """
        repo_url = profile.url_for_repo(self)
        if repo_url:
            from package.models import Package
            regex = r'^{0},|,{0},|{0}$'.format(repo_url)
            return list(Package.objects.filter(participants__regex=regex, repo_url__regex=self.repo_regex))
        else:
            return []

    def serialize(self):
        return {
            "title": self.title,
            "url": self.url,
            "repo_regex": self.repo_regex,
        }

    def get_json(self, target):
        """
        Helpful utility method to do a quick GET for JSON data.
        """
        r = requests.get(target)
        if r.status_code != 200:
            r.raise_for_status()
        return json.loads(r.content)


########NEW FILE########
__FILENAME__ = bitbucket
from datetime import datetime, timedelta
import re
from warnings import warn


from .base_handler import BaseHandler

import requests

API_TARGET = "https://api.bitbucket.org/1.0/repositories"

descendants_re = re.compile(r"Forks/Queues \((?P<descendants>\d+)\)", re.IGNORECASE)


class BitbucketHandler(BaseHandler):
    title = 'Bitbucket'
    url_regex = 'https://bitbucket.org/'
    url = 'https://bitbucket.org'
    repo_regex = r'https://bitbucket.org/[\w\-\_]+/([\w\-\_]+)/{0,1}'
    slug_regex = r'https://bitbucket.org/[\w\-\_]+/([\w\-\_]+)/{0,1}'

    def _get_bitbucket_commits(self, package):
        repo_name = package.repo_name()
        if repo_name.endswith("/"):
            repo_name = repo_name[0:-1]
        target = "%s/%s/changesets/?limit=50" % (API_TARGET, repo_name)
        try:
            data = self.get_json(target)
        except requests.exceptions.HTTPError:
            return []
        if data is None:
            return []  # todo: log this?

        return data.get("changesets", [])

    def fetch_commits(self, package):
        from package.models import Commit  # Import placed here to avoid circular dependencies
        for commit in self._get_bitbucket_commits(package):
            timestamp = commit["timestamp"].split("+")
            if len(timestamp) > 1:
                timestamp = timestamp[0]
            else:
                timestamp = commit["timestamp"]
            commit, created = Commit.objects.get_or_create(package=package, commit_date=timestamp)

        #  ugly way to get 52 weeks of commits
        # TODO - make this better
        now = datetime.now()
        commits = package.commit_set.filter(
            commit_date__gt=now - timedelta(weeks=52),
        ).values_list('commit_date', flat=True)

        weeks = [0] * 52
        for cdate in commits:
            age_weeks = (now - cdate).days // 7
            if age_weeks < 52:
                weeks[age_weeks] += 1

        package.commit_list = ','.join(map(str, reversed(weeks)))
        package.save()

    def fetch_metadata(self, package):
        # prep the target name
        repo_name = package.repo_name()
        target = API_TARGET + "/" + repo_name
        if not target.endswith("/"):
            target += "/"

        try:
            data = self.get_json(target)
        except requests.exceptions.HTTPError:
            return package

        if data is None:
            # TODO - log this better
            message = "%s had a JSONDecodeError during bitbucket.repo.pull" % (package.title)
            warn(message)
            return package

        # description
        package.repo_description = data.get("description", "")

        # get the forks of a repo
        url = "{0}forks/".format(target)
        try:
            data = self.get_json(url)
        except requests.exceptions.HTTPError:
            return package
        package.repo_forks = len(data['forks'])

        # get the followers of a repo
        url = "{0}followers/".format(target)
        try:
            data = self.get_json(url)
        except requests.exceptions.HTTPError:
            return package
        package.repo_watchers = data['count']

        # Getting participants
        try:
            package.participants = package.repo_url.split("/")[3]  # the only way known to fetch this from bitbucket!!!
        except IndexError:
            package.participants = ""

        return package

repo_handler = BitbucketHandler()

########NEW FILE########
__FILENAME__ = github
from time import sleep

from django.conf import settings
from django.utils import timezone

from github3 import GitHub, login
import requests

from base_handler import BaseHandler
from package.utils import uniquer


class GitHubHandler(BaseHandler):
    title = "Github"
    url_regex = '(http|https|git)://github.com/'
    url = 'https://github.com'
    repo_regex = r'(?:http|https|git)://github.com/[^/]*/([^/]*)/{0,1}'
    slug_regex = repo_regex

    def __init__(self):
        if settings.GITHUB_USERNAME:
            self.github = login(settings.GITHUB_USERNAME, settings.GITHUB_PASSWORD)
        else:
            self.github = GitHub()

    def manage_ratelimit(self):
        while self.github.ratelimit_remaining < 10:
            sleep(1)

    def fetch_metadata(self, package):
        self.manage_ratelimit()

        repo_name = package.repo_name()
        if repo_name.endswith("/"):
            repo_name = repo_name[:-1]
        try:
            username, repo_name = package.repo_name().split('/')
        except ValueError:
            return package
        repo = self.github.repository(username, repo_name)
        if repo is None:
            return package

        package.repo_watchers = repo.watchers
        package.repo_forks = repo.forks
        package.repo_description = repo.description

        contributors = [x.login for x in repo.iter_contributors()]
        if contributors:
            package.participants = ','.join(uniquer(contributors))

        return package

    def fetch_commits(self, package):

        self.manage_ratelimit()
        repo_name = package.repo_name()
        if repo_name.endswith("/"):
            repo_name = repo_name[:-1]
        try:
            username, repo_name = package.repo_name().split('/')
        except ValueError:
            # TODO error #248
            return package

        if settings.GITHUB_USERNAME:
            r = requests.get(
                url='https://api.github.com/repos/{}/{}/commits?per_page=100'.format(username, repo_name),
                auth=(settings.GITHUB_USERNAME, settings.GITHUB_PASSWORD)
            )
        else:
            r = requests.get(
                url='https://api.github.com/repos/{}/{}/commits?per_page=100'.format(username, repo_name)
            )
        if r.status_code == 200:
            from package.models import Commit  # Added here to avoid circular imports
            for commit in [x['commit'] for x in r.json()]:
                try:
                    commit, created = Commit.objects.get_or_create(
                        package=package,
                        commit_date=commit['committer']['date']
                    )
                except Commit.MultipleObjectsReturned:
                    pass

        package.save()
        return package

repo_handler = GitHubHandler()

########NEW FILE########
__FILENAME__ = unsupported
from .base_handler import BaseHandler


class UnsupportedHandler(BaseHandler):
    title = 'Other'
    is_other = True
    url_regex = ''
    url = ''

    def fetch_metadata(self, package):
        package.repo_watchers = 0
        package.repo_forks = 0
        package.repo_description = ''
        package.participants = ''

    def fetch_commits(self, package):
        package.commit_set.all().delete()


repo_handler = UnsupportedHandler()

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import serializers

from .models import Package


class PackageSerializer(serializers.ModelSerializer):
    pypi_version = serializers.CharField(max_length=50)
    usage_count = serializers.IntegerField()
    commits_over_52 = serializers.CharField(max_length=255)
    development_status = serializers.CharField(max_length=255)

    def transform_pypi_version(self, obj, value):
        return obj.pypi_version

    def transform_usage_count(self, obj, value):
        return obj.usage_count

    def transform_commits_over_52(self, obj, value):
        return obj.commits_over_52()

    def transform_development_status(self, obj, value):
        return obj.development_status

    class Meta:
        model = Package
        fields = (
                    "id",
                    "slug",
                    "title",
                    "repo_description",
                    "repo_watchers",
                    "repo_forks",
                    "pypi_version",
                    "usage_count",
                    "commits_over_52",
                    "development_status"
                )

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

signal_fetch_latest_metadata = django.dispatch.Signal()

########NEW FILE########
__FILENAME__ = package_tags
from django import template


from package.context_processors import used_packages_list

register = template.Library()


class ParticipantURLNode(template.Node):

    def __init__(self, repo, participant):
        self.repo = template.Variable(repo)
        self.participant = template.Variable(participant)

    def render(self, context):
        repo = self.repo.resolve(context)
        participant = self.participant.resolve(context)
        if repo.user_url:
            user_url = repo.user_url % participant
        else:
            user_url = '%s/%s' % (repo.url, participant)
        return user_url


@register.tag
def participant_url(parser, token):
    try:
        tag_name, repo, participant = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly two arguments" % token.contents.split()[0]
    return ParticipantURLNode(repo, participant)


@register.filter
def commits_over_52(package):
    return package.commits_over_52()


@register.inclusion_tag('package/templatetags/_usage_button.html', takes_context=True)
def usage_button(context):
    response = used_packages_list(context['request'])
    response['STATIC_URL'] = context['STATIC_URL']
    response['package'] = context['package']
    if context['package'].pk in response['used_packages_list']:
        response['usage_action'] = "remove"
        response['image'] = "usage_triangle_filled"
    else:
        response['usage_action'] = "add"
        response['image'] = "usage_triangle_hollow"
    return response

########NEW FILE########
__FILENAME__ = data
from django.contrib.auth.models import User

from core.tests import datautil
from package.models import Category, Package, Version
from profiles.models import Profile


def load():
    category, created = Category.objects.get_or_create(
        pk=2,
        description=u'Large efforts that combine many python modules or apps. Examples include Django, Pinax, and Satchmo. Most CMS falls into this category.',
        show_pypi=True,
        title_plural=u'Frameworks',
        title=u'Framework',
        slug=u'frameworks',
    )

    package, created = Package.objects.get_or_create(
        pk=6,
        category=category,
        title=u'Django CMS',
        created_by=None,
        repo_watchers=967,
        pypi_url=u'http://pypi.python.org/pypi/django-cms',
        pypi_downloads=26257,
        last_modified_by=None,
        repo_url=u'https://github.com/divio/django-cms',
        participants=u'chrisglass,digi604,erobit,fivethreeo,ojii,stefanfoulis,pcicman,DrMeers,brightwhitefox,FlashJunior,philomat,jezdez,havan,acdha,m000,hedberg,piquadrat,spookylukey,izimobil,ulope,emiquelito,aaloy,lasarux,yohanboniface,aparo,jsma,johbo,ionelmc,quattromic,almost,specialunderwear,mitar,yml,pajusmar,diofeher,marcor,cortextual,hysia,dstufft,ssteinerx,oversize,jalaziz,tercerojista,eallik,f4nt,kaapa,mbrochh,srj55,dz,mathijs-dumon,sealibora,cyberj,adsworth,tokibito,DaNmarner,IanLewis,indexofire,bneijt,tehfink,PPvG,seyhunak,pigletto,fcurella,gleb-chipiga,beshrkayali,kinea,lucasvo,jordanjambazov,tonnzor,centralniak,arthur-debert,bzed,jasondavies,nimnull,limpbrains,pvanderlinden,sleytr,sublimevelo,netpastor,dtt101,fkazimierczak,merlex,mrlundis,restless,eged,shanx,ptoal',
        # usage=[129, 50, 43, 183, 87, 204, 1, 231, 233, 239, 241, 248, 252, 262, 263, 268, 282, 284, 298, 32, 338, 342, 344, 345, 348, 355, 388, 401, 295, 36, 444, 422, 449, 157, 457, 462, 271, 143, 433, 554, 448, 470, 562, 86, 73, 504, 610, 621, 651, 663, 688, 661, 766, 770, 773, 799, 821, 834, 847, 848, 850, 322, 883, 823, 958, 387, 361, 123, 1026, 516, 715, 1105],
        
        repo_forks=283,
        slug=u'django-cms',
        repo_description=u'An Advanced Django CMS.',
    )

    user, created = User.objects.get_or_create(
        pk=129,
        username=u'unbracketed',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-08-28 20:48:35',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$a5c47$0e9be0aee0cb60648a3e0a70f462e0943a46aeab',
        email=u'brian@unbracketed.com',
        date_joined=u'2010-08-28 20:47:52',
    )

    user, created = User.objects.get_or_create(
        pk=50,
        username=u'ojii',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-09 14:50:02',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$a7428$563858792ba94c8706db374eed9d2708536ea2a5',
        email=u'jonas.obrist@divio.ch',
        date_joined=u'2010-08-18 03:35:23',
    )
    user, created = User.objects.get_or_create(
        pk=43,
        username=u'vvarp',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-29 12:08:01',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$ed0c0$ec7ed6b92a963fd02cd0e1e1fcd90d66591a29b8',
        email=u'maciek@id43.net',
        date_joined=u'2010-08-17 18:43:12',
    )
    user, created = User.objects.get_or_create(
        pk=183,
        username=u'onjin',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-09 07:47:11',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$1965c$9b8cc38cec3672b515787c227a3ef7ceea2ae785',
        email=u'onjinx@gmail.com',
        date_joined=u'2010-09-07 02:23:11',
    )
    user, created = User.objects.get_or_create(
        pk=87,
        username=u'jezdez',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-02-09 09:29:33',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$97523$0d3cdbbd2930052fe89ebf38ef7267bc85479032',
        email=u'jannis@leidel.info',
        date_joined=u'2010-08-21 04:14:03',
    )
    user, created = User.objects.get_or_create(
        pk=204,
        username=u'flmendes',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-14 18:01:16',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$68ef6$750d02a7c6a1b8d14adb31a8374cb18d6f37708e',
        email=u'flmendes@gmail.com',
        date_joined=u'2010-09-08 22:49:34',
    )
    user, created = User.objects.get_or_create(
        pk=1,
        username=u'audreyr',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2011-03-13 23:44:00',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c84c1$dfd3748f63f48e2639d3c4d1caa113acf6bde51f',
        email=u'audreyr@gmail.com',
        date_joined=u'2010-08-15 22:15:50',
    )
    user, created = User.objects.get_or_create(
        pk=231,
        username=u'digi604',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-12 07:34:07',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$0f7f5$523594505138d1182fa413826c02b1e32ee8b95c',
        email=u'digi@treepy.com',
        date_joined=u'2010-09-12 07:32:42',
    )
    user, created = User.objects.get_or_create(
        pk=233,
        username=u'mikl',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-12 08:57:34',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c4af2$e50af5facac17d8b6cd83e7ccc06dee27e33a6a1',
        email=u'mikkel@hoegh.org',
        date_joined=u'2010-09-12 08:56:36',
    )
    user, created = User.objects.get_or_create(
        pk=239,
        username=u'arthurk',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-12 19:13:47',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$dbc73$f0d8c4476121c8a66fae45f7131db9df71e9aab4',
        email=u'arthur@arthurkoziel.com',
        date_joined=u'2010-09-12 19:12:55',
    )
    user, created = User.objects.get_or_create(
        pk=241,
        username=u'juacompe',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-13 03:23:21',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$d08ef$4f9c0272cafe2ce6b5619c79f8ecf7f6dd3c024e',
        email=u'juacompe@gmail.com',
        date_joined=u'2010-09-13 03:10:39',
    )
    user, created = User.objects.get_or_create(
        pk=248,
        username=u'kocakafa',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-13 10:09:36',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$624bd$101a762ea78432c4a4c25c3a4f2558e14126b0d5',
        email=u'cemrekutluay@gmail.com',
        date_joined=u'2010-09-13 10:08:40',
    )
    user, created = User.objects.get_or_create(
        pk=252,
        username=u'dmoisset',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-09 09:21:27',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$0b205$20bbdba061603ed658ef772d360dd30f34b6aad6',
        email=u'dmoisset@machinalis.com',
        date_joined=u'2010-09-13 13:53:32',
    )
    user, created = User.objects.get_or_create(
        pk=262,
        username=u'eged',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-10-06 04:22:27',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$b81b9$76327ae4d11587d816a7dc0da89b71c2e36be73d',
        email=u'viliam.segeda@gmail.com',
        date_joined=u'2010-09-14 06:50:44',
    )
    user, created = User.objects.get_or_create(
        pk=263,
        username=u'rtpm',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-14 07:48:22',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$7d578$d69bb08ff132271fa1725245ec79dfb8296a0a4b',
        email=u'rtpm@gazeta.pl',
        date_joined=u'2010-09-14 07:47:29',
    )
    user, created = User.objects.get_or_create(
        pk=268,
        username=u'flynnguy',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-14 09:21:21',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$615f8$2286dc5ce690fcd70ebc796f7ffd9742a0fbce8e',
        email=u'chris@flynnguy.com',
        date_joined=u'2010-09-14 09:20:08',
    )
    user, created = User.objects.get_or_create(
        pk=282,
        username=u'mcosta',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-14 18:41:59',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$7a4e1$8f37adee1eaa107354d0400cfbd7e7a678506aa9',
        email=u'm.costacano@gmail.com',
        date_joined=u'2010-09-14 18:41:02',
    )
    user, created = User.objects.get_or_create(
        pk=284,
        username=u'chromano',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-10-13 12:50:44',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$7c7b3$5c009b3002d04f2ef3db01a17501f8d852a8e3ee',
        email=u'chromano@gmail.com',
        date_joined=u'2010-09-14 19:30:41',
    )
    user, created = User.objects.get_or_create(
        pk=298,
        username=u'robedwards',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-15 07:50:34',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$cc020$29594e7501c4697ba86c8ff0698f7d5eaf16ff14',
        email=u'rob@brycefarrah.com',
        date_joined=u'2010-09-15 07:42:18',
    )
    user, created = User.objects.get_or_create(
        pk=32,
        username=u'markusgattol',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-01-07 04:14:45',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$289e4$fb00c9de77f991b423ba91edcd91f14ab91afcd7',
        email=u'markus.gattol@sunoano.org',
        date_joined=u'2010-08-17 14:05:10',
    )
    user, created = User.objects.get_or_create(
        pk=338,
        username=u'iamsk',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 04:26:17',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$7f703$cf45848f28e30adfee3a30cc329e66a14d25bbce',
        email=u'iamsk.info@gmail.com',
        date_joined=u'2010-09-17 04:14:36',
    )
    user, created = User.objects.get_or_create(
        pk=342,
        username=u'kiello',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 05:40:20',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$72adc$31bd0fc2440d9ded4b816e6812165f3565801807',
        email=u'mauro.doglio@gmail.com',
        date_joined=u'2010-09-17 05:39:00',
    )
    user, created = User.objects.get_or_create(
        pk=344,
        username=u'nimnull',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 07:32:43',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$08b73$b8c7e885cffcc351540dbae0b5d35cdf3123a3c2',
        email=u'nimnull@gmail.com',
        date_joined=u'2010-09-17 07:31:45',
    )
    user, created = User.objects.get_or_create(
        pk=345,
        username=u'dblkey',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 08:17:44',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$1f412$5c7a8e402e0f9e588632d6662ec6da3029eaf72f',
        email=u'thedoublekey@gmail.com',
        date_joined=u'2010-09-17 08:16:44',
    )
    user, created = User.objects.get_or_create(
        pk=348,
        username=u'netpastor',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 10:18:34',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$9971f$cffb9546d3f399a0c6e7f34ad57144e8c9a66b32',
        email=u'vadimshatalov@yandex.ru',
        date_joined=u'2010-09-17 10:17:26',
    )
    user, created = User.objects.get_or_create(
        pk=355,
        username=u'limpbrains',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-17 17:45:01',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$d521e$ac48433870ff69fbbdf8e67b6d5b9341b3f70565',
        email=u'limpbrains@mail.ru',
        date_joined=u'2010-09-17 17:43:45',
    )
    user, created = User.objects.get_or_create(
        pk=388,
        username=u'mrbox',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-18 13:01:33',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c34a1$c228bbe096cd1cce6f6121aa3502f88a3df271a1',
        email=u'jakub@paczkowski.eu',
        date_joined=u'2010-09-21 09:20:54',
    )
    user, created = User.objects.get_or_create(
        pk=401,
        username=u'archatas',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-10-14 12:54:28',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$42d2e$39b36644f6246297e77af51837d898bd784b62ff',
        email=u'aidasbend@yahoo.com',
        date_joined=u'2010-09-21 23:45:16',
    )
    user, created = User.objects.get_or_create(
        pk=295,
        username=u'mat',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-15 07:49:20',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$2cb8b$09abc15052a91cd123c32f1a3cd1402a3f5759bf',
        email=u'mat@apinc.org',
        date_joined=u'2010-09-15 07:08:21',
    )
    user, created = User.objects.get_or_create(
        pk=36,
        username=u'joshourisman',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-02-11 08:41:47',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$8a414$44a1517f3443f3c2094d760fcf10c06ac6fca38f',
        email=u'josh@joshourisman.com',
        date_joined=u'2010-08-17 14:53:18',
    )
    user, created = User.objects.get_or_create(
        pk=444,
        username=u'piquadrat',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-28 04:51:17',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$e048a$fc0ea2dc56c3ec7a4ea3c2af981d0e5633f0a1b6',
        email=u'piquadrat@gmail.com',
        date_joined=u'2010-09-28 04:49:14',
    )
    user, created = User.objects.get_or_create(
        pk=422,
        username=u'evotech',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-05 11:33:42',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c4056$24151ba166330bc8a113432f35d549bec8e603de',
        email=u'ivzak@yandex.ru',
        date_joined=u'2010-09-24 05:41:49',
    )
    user, created = User.objects.get_or_create(
        pk=449,
        username=u'partizan',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-28 17:58:49',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c5658$5738a1688c1ed065eeda86eed5441b4a3f564dff',
        email=u'psychotechnik@gmail.com',
        date_joined=u'2010-09-28 13:03:59',
    )
    user, created = User.objects.get_or_create(
        pk=157,
        username=u'feuervogel',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-10-21 07:46:40',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$b62ba$b0002edb8ce814228b3812112f2878d44dd880ee',
        email=u'jumo@gmx.de',
        date_joined=u'2010-08-31 13:47:05',
    )
    user, created = User.objects.get_or_create(
        pk=457,
        username=u'LukaszDziedzia',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-30 05:44:58',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$651bc$71ea97a3322ea5720884654a6fa360f415fca698',
        email=u'l.dziedzia@gmail.com',
        date_joined=u'2010-09-29 07:43:26',
    )
    user, created = User.objects.get_or_create(
        pk=462,
        username=u'emencia',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-15 16:25:23',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$28466$0cd6b9fbb628c2837c0e4dcdc3e433aed1174ead',
        email=u'roger@emencia.com',
        date_joined=u'2010-09-29 12:00:32',
    )
    user, created = User.objects.get_or_create(
        pk=271,
        username=u'zenweasel',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-10 22:41:53',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$705e8$5759884e7222e061d08de3cbff31b53b068fd266',
        email=u'brent@thebuddhalodge.com',
        date_joined=u'2010-09-14 11:35:25',
    )
    user, created = User.objects.get_or_create(
        pk=143,
        username=u'spookylukey',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-02-19 17:09:12',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$70e5d$50c6a37cbac336cf1a08f4672bfa2002b4d2a55f',
        email=u'L.Plant.98@cantab.net',
        date_joined=u'2010-08-30 08:33:49',
    )
    user, created = User.objects.get_or_create(
        pk=433,
        username=u'avoine',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-03 10:57:01',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$9d041$240309830d9ca972b2dc2fe24158e01ee7ba4a9d',
        email=u'patrick@koumbit.org',
        date_joined=u'2010-09-26 16:31:53',
    )
    user, created = User.objects.get_or_create(
        pk=554,
        username=u'ethan',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-15 15:59:39',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$92dd1$37703fa27808c902fcd58792936afe41c02a70d0',
        email=u'Ethan.Leland@gmail.com',
        date_joined=u'2010-10-20 18:23:30',
    )
    user, created = User.objects.get_or_create(
        pk=448,
        username=u'chem',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-23 11:47:50',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$f45bb$40332f58b55706b6f6059f855b18b3cd588b8948',
        email=u'chemt@ukr.net',
        date_joined=u'2010-09-28 11:36:56',
    )
    user, created = User.objects.get_or_create(
        pk=470,
        username=u'wires',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-09-30 10:26:07',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$e15d5$a18fc4b6f8b628cc6fb6ae0d8133a423e9ad1d1e',
        email=u'jelle@defekt.nl',
        date_joined=u'2010-09-30 10:20:20',
    )
    user, created = User.objects.get_or_create(
        pk=562,
        username=u'rasca',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-01-06 11:59:42',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$edd41$bd2c72f9c2c2b59aac5775bbc59d4b529494aabf',
        email=u'rasca7@hotmail.com',
        date_joined=u'2010-10-24 12:24:08',
    )
    user, created = User.objects.get_or_create(
        pk=86,
        username=u'justhamade',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-06 18:57:20',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$b7a5a$53b2cb1cd3c20a2cee79b170b56ea88ec73d9685',
        email=u'justhamade@gmail.com',
        date_joined=u'2010-08-21 00:11:33',
    )
    user, created = User.objects.get_or_create(
        pk=73,
        username=u'slav0nic',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-13 16:46:13',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$13d6f$fafddd832ac31aff59ec6ff155e4d5284e675c56',
        email=u'slav0nic0@gmail.com',
        date_joined=u'2010-08-19 06:24:12',
    )
    user, created = User.objects.get_or_create(
        pk=504,
        username=u'Fantomas42',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-02 08:55:17',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$1166e$cc6971b2eb92eeed5ea0d43f896dcc46a47102eb',
        email=u'fantomas42@gmail.com',
        date_joined=u'2010-10-07 09:26:41',
    )
    user, created = User.objects.get_or_create(
        pk=610,
        username=u'globalnamespace',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-04 13:38:34',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$d3fbf$f3a1fc7fe6ca203ace449497d437cf06c67e905d',
        email=u'mbest@pendragon.org',
        date_joined=u'2010-11-04 13:37:57',
    )
    user, created = User.objects.get_or_create(
        pk=621,
        username=u'btubbs',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-06 19:45:21',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$6ebe8$04ff06448cbf632a9d54f13e7d3c5b808e08b528',
        email=u'brent.tubbs@gmail.com',
        date_joined=u'2010-11-06 19:36:22',
    )
    user, created = User.objects.get_or_create(
        pk=651,
        username=u'HounD',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-15 16:02:52',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$e5fc1$0ad97a61ed9bb34904e9df36ba4bbb4eca7c35c9',
        email=u'vladshikhov@gmail.com',
        date_joined=u'2010-11-13 00:45:44',
    )
    user, created = User.objects.get_or_create(
        pk=663,
        username=u'encinas',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-15 10:11:00',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$900ea$2044dfec30282981ce4094db6a0c7f1d9bba0ca9',
        email=u'list@encinas-fernandez.eu',
        date_joined=u'2010-11-15 10:05:27',
    )
    user, created = User.objects.get_or_create(
        pk=688,
        username=u'nasp',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-11-20 22:31:48',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$ed6f2$964b18357a346a3063ab299fbe34f38268aaf41f',
        email=u'charette.s@gmail.com',
        date_joined=u'2010-11-20 22:27:37',
    )
    user, created = User.objects.get_or_create(
        pk=661,
        username=u'ralphleyga',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-11 04:32:15',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$52255$9263926740de1d194152697f9f9da2466b547ce4',
        email=u'ralphfleyga@gmail.com',
        date_joined=u'2010-11-15 08:46:31',
    )
    user, created = User.objects.get_or_create(
        pk=766,
        username=u'xigit',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-06 04:28:14',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$917d2$cbead9bd51c7b47651e92dfd315485a054794187',
        email=u'xigitech@gmail.com',
        date_joined=u'2010-12-06 04:26:04',
    )
    user, created = User.objects.get_or_create(
        pk=770,
        username=u'espenhogbakk',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-06 06:13:29',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$e354e$d7c7d6cf7a80f6ccd6e96c688362e5e55a651b62',
        email=u'espen@hogbakk.no',
        date_joined=u'2010-12-06 06:12:27',
    )
    user, created = User.objects.get_or_create(
        pk=773,
        username=u'petko',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-06 07:02:29',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$86046$91b8739ec7172f6381ae9827a16745084ac960d8',
        email=u'petko@magicbg.com',
        date_joined=u'2010-12-06 07:01:57',
    )
    user, created = User.objects.get_or_create(
        pk=799,
        username=u'eallik',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-06 12:49:19',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$601f6$e0a658e028c87227715b617f31c4c04f479daf0f',
        email=u'eallik+djangopackages@gmail.com',
        date_joined=u'2010-12-06 12:47:55',
    )
    user, created = User.objects.get_or_create(
        pk=821,
        username=u'digitaldreamer',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-09 23:39:29',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$920b7$590a350f467603856b41b302f4dbb3cf76c99f52',
        email=u'poyzer@gmail.com',
        date_joined=u'2010-12-09 23:37:03',
    )
    user, created = User.objects.get_or_create(
        pk=834,
        username=u'andrey_shipilov',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-13 06:56:07',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$59dc2$e720ca75bb1e1aeb66b50a716b74428955c86122',
        email=u'tezro.gb@gmail.com',
        date_joined=u'2010-12-13 06:54:28',
    )
    user, created = User.objects.get_or_create(
        pk=847,
        username=u'john',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-15 23:10:14',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$fa281$87df6e12a569a9383986d0047f36e54a93d0812c',
        email=u'xjh8619kl93@163.com',
        date_joined=u'2010-12-15 23:01:23',
    )
    user, created = User.objects.get_or_create(
        pk=848,
        username=u'tmilovan',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-16 13:03:30',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$a2979$2c86ec53cd382a822ff4ac9764e2f65bd8d7e7c9',
        email=u'tmilovan@fwd.hr',
        date_joined=u'2010-12-16 13:02:12',
    )
    user, created = User.objects.get_or_create(
        pk=850,
        username=u'silvergeko',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-17 15:22:38',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$c9c20$7b4cf6b907147e30a105360888ac4a903ba782ab',
        email=u'scopel.emanuele@gmail.com',
        date_joined=u'2010-12-17 15:21:25',
    )
    user, created = User.objects.get_or_create(
        pk=322,
        username=u'tino',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-21 06:01:06',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$3cb5f$36e621a1d7d38a9159e9e7bc86cd93f0636d330d',
        email=u'tinodb@gmail.com',
        date_joined=u'2010-09-16 16:27:02',
    )
    user, created = User.objects.get_or_create(
        pk=883,
        username=u'mariocesar',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-12-29 08:36:45',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$705d5$63af6bfa8f27b759b755574f6c7d8158d240c526',
        email=u'mariocesar.c50@gmail.com',
        date_joined=u'2010-12-29 08:35:49',
    )
    user, created = User.objects.get_or_create(
        pk=823,
        username=u'qrilka',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-01-19 17:17:17',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$37911$f2622929d7f460a9a4d6204325b1349940aafe83',
        email=u'qrilka@gmail.com',
        date_joined=u'2010-12-10 05:15:35',
    )
    user, created = User.objects.get_or_create(
        pk=958,
        username=u'dmpeters63',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-01-28 03:06:30',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$66668$0eb23655452720bdb2e2ff8874bd84d5ae599dfb',
        email=u'dmpeters63@gmail.com',
        date_joined=u'2011-01-28 03:04:11',
    )
    user, created = User.objects.get_or_create(
        pk=387,
        username=u'oversize',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-01-28 07:37:47',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$f291f$d08c5869b9dafc8a61c460599e4c2519f3e60cda',
        email=u'manuel@schmidtman.de',
        date_joined=u'2010-09-21 05:44:08',
    )
    user, created = User.objects.get_or_create(
        pk=361,
        username=u'moskrc',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-05 04:35:45',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$3627b$3a2d7e40c2adb5f6fe459737e1c6abfc242b225c',
        email=u'moskrc@gmail.com',
        date_joined=u'2010-09-18 15:53:47',
    )
    user, created = User.objects.get_or_create(
        pk=123,
        username=u'stefanfoulis',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-02-21 03:18:48',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$8ef17$5559490fac93e0e40ac637e84b3c8069d2091879',
        email=u'stefan.foulis@gmail.com',
        date_joined=u'2010-08-28 13:54:39',
    )
    user, created = User.objects.get_or_create(
        pk=1026,
        username=u'gmh04',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-14 16:02:05',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$d82a2$96d68a17ce55446037d67b3cf076f5e47cca1718',
        email=u'gmh04@netscape.net',
        date_joined=u'2011-02-16 16:05:47',
    )
    user, created = User.objects.get_or_create(
        pk=516,
        username=u'azizmb',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-02-25 13:20:16',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$dd3cb$321edb091caa16a8fd2231dfc61bbb27ecc455eb',
        email=u'aziz.mansur@gmail.com',
        date_joined=u'2010-10-09 13:54:45',
    )
    user, created = User.objects.get_or_create(
        pk=715,
        username=u'mwalling',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-02 16:57:24',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$114c6$195ee166ab51a5727641915fe4bc822d1ba9052f',
        email=u'mark@markwalling.org',
        date_joined=u'2010-11-28 13:36:12',
    )
    user, created = User.objects.get_or_create(
        pk=1105,
        username=u'evilkarlothian',
        first_name=u'',
        last_name=u'',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2011-03-14 18:54:25',
        # groups=[],
        # user_permissions=[],
        password=u'sha1$e509f$a44e555f6c7aee67fde34dbe995fce20a4af2b96',
        email=u'karlbowden@gmail.com',
        date_joined=u'2011-03-14 18:52:34',
    )

    package6 = Package.objects.get(pk=6)

    version, created = Version.objects.get_or_create(
        pk=2278,
        license=u'BSD License',
        downloads=1904,
        package=package6,
        number=u'2.1.3',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=2252,
        license=u'BSD License',
        downloads=715,
        package=package6,
        number=u'2.1.2',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=2177,
        license=u'BSD License',
        downloads=906,
        package=package6,
        number=u'2.1.1',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=2041,
        license=u'BSD License',
        downloads=1613,
        package=package6,
        number=u'2.1.0',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=1977,
        license=u'BSD License',
        downloads=850,
        package=package6,
        number=u'2.1.0.rc3',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=1913,
        license=u'BSD License',
        downloads=726,
        package=package6,
        number=u'2.1.0.rc2',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=1870,
        license=u'BSD License',
        downloads=299,
        package=package6,
        number=u'2.1.0.rc1',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=12,
        license=u'BSD License',
        downloads=1062,
        package=package6,
        number=u'2.0.0',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=11,
        license=u'BSD License',
        downloads=212,
        package=package6,
        number=u'2.0.1',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=10,
        license=u'BSD License',
        downloads=4326,
        package=package6,
        number=u'2.0.2',
        hidden=False,
    )
    version, created = Version.objects.get_or_create(
        pk=9,
        license=u'BSD License',
        downloads=13644,
        package=package6,
        number=u'2.1.0.beta3',
        hidden=False,
    )

    datautil.reset_sequences(Category, Package, Profile, Version, User)


########NEW FILE########
__FILENAME__ = initial_data
from grid.models import Grid
from django.contrib.auth.models import Group, User, Permission
from package.models import Category, PackageExample, Package
from grid.models import Element, Feature, GridPackage
from core.tests import datautil


def load():
    category, created = Category.objects.get_or_create(
        pk=1,
        slug=u'apps',
        title=u'App',
        description=u'Small components used to build projects.',
    )

    package1, created = Package.objects.get_or_create(
        pk=1,
        category=category,
        repo_watchers=0,
        title=u'Testability',
        pypi_url='',
        participants=u'malcomt,jacobian',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-la-facebook',

        repo_forks=0,
        slug=u'testability',
        repo_description=u'Increase your testing ability with this steroid free supplement.',
    )
    package2, created = Package.objects.get_or_create(
        pk=2,
        category=category,
        repo_watchers=0,
        title=u'Supertester',
        pypi_url='',
        participants=u'thetestman',
        pypi_downloads=0,
        repo_url=u'https://github.com/pydanny/django-uni-form',

        repo_forks=0,
        slug=u'supertester',
        repo_description=u'Test everything under the sun with one command!',
    )
    package3, created = Package.objects.get_or_create(
        pk=3,
        category=category,
        repo_watchers=0,
        title=u'Serious Testing',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/opencomparison/opencomparison',

        repo_forks=0,
        slug=u'serious-testing',
        repo_description=u'Make testing as painless as waxing your legs.',
    )
    package4, created = Package.objects.get_or_create(
        pk=4,
        category=category,
        repo_watchers=0,
        title=u'Another Test',
        pypi_url='',
        participants=u'pydanny',
        pypi_downloads=0,
        repo_url=u'https://github.com/djangopackages/djangopackages',

        repo_forks=0,
        slug=u'another-test',
        repo_description=u'Yet another test package, with no grid affiliation.',
    )

    grid1, created = Grid.objects.get_or_create(
        pk=1,
        description=u'A grid for testing.',
        title=u'Testing',
        is_locked=False,
        slug=u'testing',
    )
    grid2, created = Grid.objects.get_or_create(
        pk=2,
        description=u'Another grid for testing.',
        title=u'Another Testing',
        is_locked=False,
        slug=u'another-testing',
    )

    gridpackage1, created = GridPackage.objects.get_or_create(
        pk=1,
        package=package1,
        grid=grid1,
    )
    gridpackage2, created = GridPackage.objects.get_or_create(
        pk=2,
        package=package1,
        grid=grid1,
    )
    gridpackage3, created = GridPackage.objects.get_or_create(
        pk=3,
        package=package3,
        grid=grid1,
    )
    gridpackage4, created = GridPackage.objects.get_or_create(
        pk=4,
        package=package3,
        grid=grid2,
    )
    gridpackage5, created = GridPackage.objects.get_or_create(
        pk=5,
        package=package2,
        grid=grid1,
    )

    feature1, created = Feature.objects.get_or_create(
        pk=1,
        title=u'Has tests?',
        grid=grid1,
        description=u'Does this package come with tests?',
    )
    feature2, created = Feature.objects.get_or_create(
        pk=2,
        title=u'Coolness?',
        grid=grid1,
        description=u'Is this package cool?',
    )

    element, created = Element.objects.get_or_create(
        pk=1,
        text=u'Yes',
        feature=feature1,
        grid_package=gridpackage1,
    )

    group1, created = Group.objects.get_or_create(
        pk=1,
        name=u'Moderators',
        #permissions=[[u'delete_gridpackage', u'grid', u'gridpackage'], [u'delete_feature', u'grid', u'feature']],
    )
    group1.permissions.clear()
    group1.permissions = [
        Permission.objects.get(codename='delete_gridpackage'),
        Permission.objects.get(codename='delete_feature')
        ]

    # password is 'user'
    user1, created = User.objects.get_or_create(
        pk=1,
        username=u'user',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$644c9$347f3dd85fb609a5745ebe33d0791929bf08f22e',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2, created = User.objects.get_or_create(
        pk=2,
        username=u'cleaner',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=False,
        last_login=u'2010-01-01 12:00:00',
        #groups=[group1],
        password=u'sha1$e6fe2$78b744e21cddb39117997709218f4c6db4e91894',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    user2.groups = [group1]

    user3, created = User.objects.get_or_create(
        pk=3,
        username=u'staff',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=False,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$8894d$c4814980edd6778f0ab1632c4270673c0fd40efe',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )
    # password is 'admin'
    user4, created = User.objects.get_or_create(
        pk=4,
        username=u'admin',
        first_name='',
        last_name='',
        is_active=True,
        is_superuser=True,
        is_staff=True,
        last_login=u'2010-01-01 12:00:00',
        password=u'sha1$52c7f$59b4f64ffca593e6abd23f90fd1f95cf71c367a4',
        email='',
        date_joined=u'2010-01-01 12:00:00',
    )

    packageexample, created = PackageExample.objects.get_or_create(
        pk=1,
        package=package1,
        url=u'http://www.example.com/',
        active=True,
        title=u'www.example.com',
    )

    datautil.reset_sequences(Grid, Group, User, Permission, Category, PackageExample,
                             Package, Element, Feature, GridPackage)


########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase

from package.models import Package, Version, versioner
from package.tests import data, initial_data

class VersionTests(TestCase):
    def setUp(self):
        data.load()

    def test_version_order(self):
        p = Package.objects.get(slug='django-cms')
        versions = p.version_set.by_version()
        expected_values = [ '2.0.0',
                            '2.0.1',
                            '2.0.2',
                            '2.1.0',
                            '2.1.0.beta3',
                            '2.1.0.rc1',
                            '2.1.0.rc2',
                            '2.1.0.rc3',
                            '2.1.1',
                            '2.1.2',
                            '2.1.3']
        returned_values = [v.number for v in versions]
        self.assertEquals(returned_values,expected_values)

    def test_version_license_length(self):
        v = Version.objects.all()[0]
        v.license = "x"*50
        v.save()
        self.assertEquals(v.license,"Custom")

class PackageTests(TestCase):
    def setUp(self):
        initial_data.load()

    def test_license_latest(self):
        for p in Package.objects.all():
            self.assertEquals("UNKNOWN", p.license_latest)
########NEW FILE########
__FILENAME__ = test_repos
import json

from django.test import TestCase

from package.repos import get_repo_for_repo_url
from package.repos.bitbucket import repo_handler as bitbucket_handler
from package.repos.github import repo_handler as github_handler
from package.repos.base_handler import BaseHandler
from package.repos.unsupported import UnsupportedHandler
from package.models import Commit, Package, Category


class BaseBase(TestCase):

    def setUp(self):

        self.category = Category.objects.create(
            title='dummy',
            slug='dummy'
        )
        self.category.save()


class TestBaseHandler(BaseBase):
    def setUp(self):
        super(TestBaseHandler, self).setUp()
        self.package = Package.objects.create(
            title="Django Piston",
            slug="django-piston",
            repo_url="https://bitbucket.org/jespern/django-piston",
            category=self.category
        )

    def test_not_implemented(self):
        # TODO switch the NotImplemented to the other side
        handler = BaseHandler()
        self.assertEquals(NotImplemented, handler.title)
        self.assertEquals(NotImplemented, handler.url)
        self.assertEquals(NotImplemented, handler.repo_regex)
        self.assertEquals(NotImplemented, handler.slug_regex)
        self.assertEquals(NotImplemented, handler.__str__())
        self.assertEquals(NotImplemented, handler.fetch_metadata(self.package))
        self.assertEquals(NotImplemented, handler.fetch_commits(self.package))

    def test_is_other(self):
        handler = BaseHandler()
        self.assertEquals(handler.is_other, False)

    def test_get_repo_for_repo_url(self):
        samples = """u'http://repos.entrouvert.org/authentic.git/tree
http://code.basieproject.org/
http://znc-sistemas.github.com/django-municipios
http://django-brutebuster.googlecode.com/svn/trunk/BruteBuster/
http://hg.piranha.org.ua/byteflow/
http://code.google.com/p/classcomm
http://savannah.nongnu.org/projects/dina-project/
tyrion/django-acl/
izi/django-admin-tools/
bkonkle/django-ajaxcomments/
http://django-ajax-selects.googlecode.com/svn/trunk/
http://django-antivirus.googlecode.com/svn/trunk/
codekoala/django-articles/
https://launchpad.net/django-audit
https://django-audit.googlecode.com/hg/
tyrion/django-autocomplete/
http://code.google.com/p/django-autocomplete/
http://pypi.python.org/pypi/django-autoreports
http://code.google.com/p/django-basic-tumblelog/
schinckel/django-biometrics/
discovery/django-bitly/
bkroeze/django-bursar/src
http://hg.mornie.org/django/c5filemanager/
https://code.launchpad.net/django-cachepurge
http://code.google.com/p/django-campaign/
http://code.google.com/p/django-cas/
http://code.google.com/p/django-chat
http://code.google.com/p/django-compress/
https://launchpad.net/django-configglue
dantario/djelfinder/
ubernostrum/django-contact-form/
http://bitbucket.org/smileychris/django-countries/
http://code.google.com/p/django-courier
http://django-cube.googlecode.com/hg
http://launchpad.net/django-debian
http://pypi.python.org/pypi/django-debug-toolbar-extra
http://code.playfire.com/django-debug-toolbar-user-panel
http://svn.os4d.org/svn/djangodevtools/trunk
http://code.google.com/p/django-dynamic-formset
http://code.google.com/p/django-evolution/
http://pypi.python.org/pypi/django-form-admin
muhuk/django-formfieldset/
http://code.google.com/p/django-forum/
http://code.google.com/p/django-generic-confirmation
http://pypi.python.org/pypi/django-genericforeignkey
https://launchpad.net/django-genshi
http://code.google.com/p/django-gmapi/
http://code.google.com/p/django-ids
http://pypi.python.org/pypi/django-inlinetrans
http://www.github.com/rosarior/django-inventory
codekoala/django-ittybitty/overview
http://bitbucket.org/mrpau/django-jobsboard
http://code.google.com/p/django-jqchat
http://code.google.com/p/djangokit/
http://code.google.com/p/django-ldap-groups/
carljm/django-localeurl/
http://code.google.com/p/django-messages/
robcharlwood/django-mothertongue/
fivethreeo/django-mptt-comments/
http://code.google.com/p/django-multilingual
http://code.google.com/p/django-navbar/
http://code.larlet.fr/django-oauth-plus/wiki/Home
http://django-observer.googlecode.com/svn/trunk/
aaronmader/django-parse_rss/tree/master/parse_rss
http://bitbucket.org/fhahn/django-permission-backend-nonrel
https://code.google.com/p/django-pgsql-interval-field
http://code.google.com/p/django-profile/
lukaszb/django-projector/
http://pypi.python.org/pypi/django-proxy-users
https://bitbucket.org/dias.kev/django-quotidian
nabucosound/django-rbac/
http://djangorestmodel.sourceforge.net/index.html
kmike/django-robokassa/
http://code.google.com/p/django-selectreverse/
http://code.google.com/p/django-simple-newsletter/
http://code.google.com/p/django-simplepages/
http://code.google.com/p/django-simple-wiki
http://pypi.python.org/pypi/django-smart-extends
vgavro/django-smsgate/
schinckel/django-sms-gateway/
http://pypi.python.org/pypi/django-staticmedia
http://opensource.washingtontimes.com/projects/django-supertagging/
http://code.google.com/p/django-tagging-autocomplete
https://source.codetrax.org/hgroot/django-taggit-autocomplete-modified
feuervogel/django-taggit-templatetags/
http://code.google.com/p/django-tasks/
http://code.google.com/p/djangotechblog/
https://launchpad.net/django-testscenarios/
http://django-thumbs.googlecode.com/svn/trunk/
http://code.google.com/p/django-trackback/
http://code.google.com/p/django-transmeta
http://sourceforge.net/projects/django-ui
daks/django-userthemes/
https://django-valuate.googlecode.com/hg
kmike/django-vkontakte-iframe/
http://code.google.com/p/django-voice
http://code.google.com/p/django-wikiapp
cleemesser/django-wsgiserver/
http://code.google.com/p/djapian/
http://code.google.com/p/djfacet
http://code.google.com/p/dojango-datable
http://evennia.googlecode.com/svn/trunk
http://feedjack.googlecode.com/hg
http://code.google.com/p/fullhistory
http://code.google.com/p/goflow
https://launchpad.net/django-jsonfield
https://launchpad.net/linaro-django-xmlrpc/
http://linkexchange.org.ua/browser
http://code.google.com/p/mango-py
http://dev.merengueproject.org/
http://code.google.com/p/django-inoutboard/
http://svn.osqa.net/svnroot/osqa/trunk
http://peach3.nl/trac/
jespern/django-piston/
http://code.google.com/p/django-provinceitaliane/
http://bitbucket.org/kmike/pymorphy
schinckel/django-rest-api/
chris1610/satchmo/
spookylukey/semanticeditor/
http://code.google.com/p/sorethumb/
andrewgodwin/south/
http://source.sphene.net/svn/root/django/communitytools/trunk
http://source.sphene.net/svn/root/django/communitytools
sebpiq/spiteat/
schinckel/django-timedelta-field/
http://projects.unbit.it/hg/uwsgi
http://www.dataportal.it"""
        for sample in samples.split("\n"):
            self.assertTrue(isinstance(get_repo_for_repo_url(sample), UnsupportedHandler))


class TestBitbucketRepo(TestBaseHandler):
    def setUp(self):
        super(TestBitbucketRepo, self).setUp()
        self.package = Package.objects.create(
            title="django",
            slug="django",
            repo_url="https://bitbucket.org/django/django",
            category=self.category
        )

    def test_fetch_commits(self):
        self.assertEqual(Commit.objects.count(), 0)
        bitbucket_handler.fetch_commits(self.package)
        self.assertNotEqual(Commit.objects.count(), 0)

    def test_fetch_metadata(self):
        package = bitbucket_handler.fetch_metadata(self.package)
        self.assertTrue(
            package.repo_description.startswith("Official clone of the Subversion repo")
        )
        self.assertTrue(package.repo_watchers > 0)
        self.assertTrue(package.repo_forks > 0)
        self.assertEquals(package.participants, "django")


class TestGithubRepo(TestBaseHandler):
    def setUp(self):
        super(TestGithubRepo, self).setUp()
        self.package = Package.objects.create(
            title="Django",
            slug="django",
            repo_url="https://github.com/django/django",
            category=self.category
        )

    def test_fetch_commits(self):
        self.assertEqual(Commit.objects.count(), 0)
        github_handler.fetch_commits(self.package)
        self.assertTrue(Commit.objects.count() > 0)

    def test_fetch_metadata(self):
        # Currently a live tests that access github
        package = github_handler.fetch_metadata(self.package)
        self.assertEqual(package.repo_description, "The Web framework for perfectionists with deadlines.")
        self.assertTrue(package.repo_watchers > 100)

        # test what happens when setting up an unsupported repo
        self.package.repo_url = "https://example.com"
        self.package.fetch_metadata()
        self.assertEqual(self.package.repo_description, "")
        self.assertEqual(self.package.repo_watchers, 0)
        self.package.fetch_commits()


class TestRepos(BaseBase):
    def test_repo_registry(self):
        from package.repos import get_repo, supported_repos

        g = get_repo("github")
        self.assertEqual(g.title, "Github")
        self.assertEqual(g.url, "https://github.com")
        self.assertTrue("github" in supported_repos())
        self.assertRaises(ImportError, lambda: get_repo("xyzzy"))

########NEW FILE########
__FILENAME__ = test_signals
from django.test import TestCase
from package.models import Package, Category
from package.signals import signal_fetch_latest_metadata


class SignalTests(TestCase):
    sender_name = ''

    def test_fetch_metadata(self):
        category = Category.objects.create(
                        title='dumb category',
                        slug='blah'
                        )
        category.save()
        package = Package.objects.create(slug='dummy', category=category)

        def handle_signal(sender, **kwargs):
            self.sender_name = sender.slug
        signal_fetch_latest_metadata.connect(handle_signal)
        package.fetch_metadata()
        self.assertEquals(self.sender_name, 'dummy')

########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase

from package.utils import uniquer, normalize_license


class UtilsTest(TestCase):
    def test_uniquer(self):
        items = ['apple', 'apple', 'apple', 'banana', 'cherry']
        unique_items = ['apple', 'banana', 'cherry']
        self.assertEqual(uniquer(items), unique_items)

    def test_normalize_license(self):
        self.assertEqual(normalize_license(None), "UNKNOWN")
        self.assertEqual(
                normalize_license("""License :: OSI Approved :: MIT License
                """),
                "License :: OSI Approved :: MIT License")
        self.assertEqual(normalize_license("Pow" * 80), "Custom")
        self.assertEqual(normalize_license("MIT"), "MIT")

########NEW FILE########
__FILENAME__ = test_views
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from package.models import Category, Package, PackageExample
from package.tests import initial_data

from profiles.models import Profile


class FunctionalPackageTest(TestCase):
    def setUp(self):
        initial_data.load()
        for user in User.objects.all():
            profile = Profile.objects.create(user=user)
            profile.save()
        settings.RESTRICT_PACKAGE_EDITORS = False
        settings.RESTRICT_GRID_EDITORS = True

    def test_package_list_view(self):
        url = reverse('packages')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/package_list.html')
        packages = Package.objects.all()
        for p in packages:
            self.assertContains(response, p.title)

    def test_package_detail_view(self):
        url = reverse('package', kwargs={'slug': 'testability'})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'package/package.html')
        p = Package.objects.get(slug='testability')
        self.assertContains(response, p.title)
        self.assertContains(response, p.repo_description)
        for participant in p.participant_list():
            self.assertContains(response, participant)
        for g in p.grids():
            self.assertContains(response, g.title)
        for e in p.active_examples:
            self.assertContains(response, e.title)

    def test_latest_packages_view(self):
        url = reverse('latest_packages')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/package_archive.html')
        packages = Package.objects.all()
        for p in packages:
            self.assertContains(response, p.title)
            self.assertContains(response, p.repo_description)

    def test_add_package_view(self):
        url = reverse('add_package')
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/package_form.html')
        for c in Category.objects.all():
            self.assertContains(response, c.title)
        count = Package.objects.count()
        response = self.client.post(url, {
            'category': Category.objects.all()[0].pk,
            'repo_url': 'https://github.com/django/django',
            'slug': 'django',
            'title': 'django',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Package.objects.count(), count + 1)

    def test_edit_package_view(self):
        p = Package.objects.get(slug='testability')
        url = reverse('edit_package', kwargs={'slug': 'testability'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/package_form.html')
        self.assertContains(response, p.title)
        self.assertContains(response, p.slug)

        # Make a test post
        response = self.client.post(url, {
            'category': Category.objects.all()[0].pk,
            'repo_url': 'https://github.com/django/django',
            'slug': p.slug,
            'title': 'TEST TITLE',
        })
        self.assertEqual(response.status_code, 302)

        # Check that it actually changed the package
        p = Package.objects.get(slug='testability')
        self.assertEqual(p.title, 'TEST TITLE')

    def test_add_example_view(self):
        url = reverse('add_example', kwargs={'slug': 'testability'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/add_example.html')

        count = PackageExample.objects.count()
        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'url': 'https://github.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PackageExample.objects.count(), count + 1)

    def test_edit_example_view(self):
        e = PackageExample.objects.all()[0]
        id = e.pk
        url = reverse('edit_example', kwargs={'slug': e.package.slug,
            'id': e.pk})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        # Once we log in the user, we should get back the appropriate response.
        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'package/edit_example.html')

        response = self.client.post(url, {
            'title': 'TEST TITLE',
            'url': 'https://github.com',
        })
        self.assertEqual(response.status_code, 302)
        e = PackageExample.objects.get(pk=id)
        self.assertEqual(e.title, 'TEST TITLE')

    def test_usage_view(self):
        url = reverse('usage', kwargs={'slug': 'testability', 'action': 'add'})
        response = self.client.get(url)

        # The response should be a redirect, since the user is not logged in.
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username='user')
        count = user.package_set.count()
        self.assertTrue(self.client.login(username='user', password='user'))

        # Now that the user is logged in, make sure that the number of packages
        # they use has increased by one.
        response = self.client.get(url)
        self.assertEqual(count + 1, user.package_set.count())

        # Now we remove that same package from the user's list of used packages,
        # making sure that the total number has decreased by one.
        url = reverse('usage', kwargs={'slug': 'testability', 'action': 'remove'})
        response = self.client.get(url)
        self.assertEqual(count, user.package_set.count())


class PackagePermissionTest(TestCase):
    def setUp(self):
        initial_data.load()
        for user in User.objects.all():
            profile = Profile.objects.create(user=user)
            profile.save()

        settings.RESTRICT_PACKAGE_EDITORS = True
        self.test_add_url = reverse('add_package')
        self.test_edit_url = reverse('edit_package',
                                     kwargs={'slug': 'testability'})
        self.login = self.client.login(username='user', password='user')
        self.user = User.objects.get(username='user')

    def test_login(self):
        self.assertTrue(self.login)

    def test_switch_permissions(self):
        settings.RESTRICT_PACKAGE_EDITORS = False
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 200)
        settings.RESTRICT_PACKAGE_EDITORS = True
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 403)

    def test_add_package_permission_fail(self):
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 403)

    def test_add_package_permission_success(self):
        add_package_perm = Permission.objects.get(codename="add_package",
                content_type__app_label='package')
        self.user.user_permissions.add(add_package_perm)
        response = self.client.get(self.test_add_url)
        self.assertEqual(response.status_code, 200)

    def test_edit_package_permission_fail(self):
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 403)

    def test_edit_package_permission_success(self):
        edit_package_perm = Permission.objects.get(codename="change_package",
                content_type__app_label='package')
        self.user.user_permissions.add(edit_package_perm)
        response = self.client.get(self.test_edit_url)
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic.dates import ArchiveIndexView

from package.models import Package
from package.views import (
                            add_example,
                            add_package,
                            ajax_package_list,
                            edit_package,
                            edit_example,
                            update_package,
                            usage,
                            package_list,
                            package_detail,
                            post_data,
                            edit_documentation,
                            github_webhook
                            )

urlpatterns = patterns("",

    url(
        regex=r"^$",
        view=package_list,
        name="packages",
    ),

    url(
        regex=r"^latest/$",
        view=ArchiveIndexView.as_view(
                        queryset=Package.objects.filter().select_related(),
                        paginate_by=50,
                        date_field="created"
        ),
        name="latest_packages",
    ),
    url(
        regex="^add/$",
        view=add_package,
        name="add_package",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/edit/$",
        view=edit_package,
        name="edit_package",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/fetch-data/$",
        view=update_package,
        name="fetch_package_data",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/post-data/$",
        view=post_data,
        name="post_package_data",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/example/add/$",
        view=add_example,
        name="add_example",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/example/(?P<id>\d+)/edit/$",
        view=edit_example,
        name="edit_example",
    ),

    url(
        regex="^p/(?P<slug>[-\w]+)/$",
        view=package_detail,
        name="package",
    ),

    url(
        regex="^ajax_package_list/$",
        view=ajax_package_list,
        name="ajax_package_list",
    ),

    url(
        regex="^usage/(?P<slug>[-\w]+)/(?P<action>add|remove)/$",
        view=usage,
        name="usage",
    ),

    url(
        regex="^(?P<slug>[-\w]+)/document/$",
        view=edit_documentation,
        name="edit_documentation",
    ),
    url(
        regex="^github-webhook/$",
        view=github_webhook,
        name="github_webhook"
    ),
)

########NEW FILE########
__FILENAME__ = utils
from distutils.version import LooseVersion as versioner

from requests.compat import quote

from django.conf import settings
from django.db import models


#this is gross, but requests doesn't import quote_plus into compat,
#so we re-implement it here
def quote_plus(s, safe=''):
    """Quote the query fragment of a URL; replacing ' ' with '+'"""
    if ' ' in s:
        s = quote(s, safe + ' ')
        return s.replace(' ', '+')
    return quote(s, safe)


def uniquer(seq, idfun=None):
    if idfun is None:
        def idfun(x):
            return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result


def get_version(package):

    versions = package.version_set.exclude(upload_time=None)
    try:
        return versions.latest()
    except models.ObjectDoesNotExist:
        return None


def get_pypi_version(package):
    string_ver_list = package.version_set.values_list('number', flat=True)
    if string_ver_list:
        vers_list = [versioner(v) for v in string_ver_list]
        latest = sorted(vers_list)[-1]
        return str(latest)
    return ''


def normalize_license(license):
    """ Handles when:

        * No license is passed
        * Made up licenses are submitted
        * Official PyPI trove classifier licenses
        * Common abbreviations of licenses

    """
    if license is None:
        return "UNKNOWN"
    if license.strip() in settings.LICENSES:
        return license.strip()
    if len(license.strip()) > 20:
        return "Custom"
    return license.strip()

########NEW FILE########
__FILENAME__ = views
import importlib
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_view_exempt


from grid.models import Grid
from homepage.models import Dpotw, Gotw
from package.forms import PackageForm, PackageExampleForm, DocumentationForm
from package.models import Category, Package, PackageExample
from package.repos import get_all_repos

from .utils import quote_plus


def repo_data_for_js():
    repos = [handler.serialize() for handler in get_all_repos()]
    return json.dumps(repos)


def get_form_class(form_name):
    bits = form_name.split('.')
    form_module_name = '.'.join(bits[:-1])
    form_module = importlib.import_module(form_module_name)
    form_name = bits[-1]
    return getattr(form_module, form_name)


@login_required
def add_package(request, template_name="package/package_form.html"):

    if not request.user.get_profile().can_add_package:
        return HttpResponseForbidden("permission denied")

    new_package = Package()
    form = PackageForm(request.POST or None, instance=new_package)

    if form.is_valid():
        new_package = form.save()
        new_package.created_by = request.user
        new_package.last_modified_by = request.user
        new_package.save()
        #new_package.fetch_metadata()
        #new_package.fetch_commits()

        return HttpResponseRedirect(reverse("package", kwargs={"slug": new_package.slug}))

    return render(request, template_name, {
        "form": form,
        "repo_data": repo_data_for_js(),
        "action": "add",
        })


@login_required
def edit_package(request, slug, template_name="package/package_form.html"):

    if not request.user.get_profile().can_edit_package:
        return HttpResponseForbidden("permission denied")

    package = get_object_or_404(Package, slug=slug)
    form = PackageForm(request.POST or None, instance=package)

    if form.is_valid():
        modified_package = form.save()
        modified_package.last_modified_by = request.user
        modified_package.save()
        messages.add_message(request, messages.INFO, 'Package updated successfully')
        return HttpResponseRedirect(reverse("package", kwargs={"slug": modified_package.slug}))

    return render(request, template_name, {
        "form": form,
        "package": package,
        "repo_data": repo_data_for_js(),
        "action": "edit",
        })


@login_required
def update_package(request, slug):

    package = get_object_or_404(Package, slug=slug)
    package.fetch_metadata()
    package.fetch_commits()
    package.last_fetched = timezone.now()
    messages.add_message(request, messages.INFO, 'Package updated successfully')

    return HttpResponseRedirect(reverse("package", kwargs={"slug": package.slug}))


@login_required
def add_example(request, slug, template_name="package/add_example.html"):

    package = get_object_or_404(Package, slug=slug)
    new_package_example = PackageExample()
    form = PackageExampleForm(request.POST or None, instance=new_package_example)

    if form.is_valid():
        package_example = PackageExample(package=package,
                title=request.POST["title"],
                url=request.POST["url"])
        package_example.save()
        return HttpResponseRedirect(reverse("package", kwargs={"slug": package_example.package.slug}))

    return render(request, template_name, {
        "form": form,
        "package": package
        })


@login_required
def edit_example(request, slug, id, template_name="package/edit_example.html"):

    package_example = get_object_or_404(PackageExample, id=id)
    form = PackageExampleForm(request.POST or None, instance=package_example)

    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("package", kwargs={"slug": package_example.package.slug}))

    return render(request, template_name, {
        "form": form,
        "package": package_example.package
        })


def package_autocomplete(request):
    """
    Provides Package matching based on matches of the beginning
    """
    titles = []
    q = request.GET.get("q", "")
    if q:
        titles = (x.title for x in Package.objects.filter(title__istartswith=q))

    response = HttpResponse("\n".join(titles))

    setattr(response, "djangologging.suppress_output", True)
    return response


def category(request, slug, template_name="package/category.html"):
    category = get_object_or_404(Category, slug=slug)
    packages = category.package_set.select_related().annotate(usage_count=Count("usage")).order_by("-repo_watchers", "title")
    return render(request, template_name, {
        "category": category,
        "packages": packages,
        }
    )


def ajax_package_list(request, template_name="package/ajax_package_list.html"):
    q = request.GET.get("q", "")
    packages = []
    if q:
        _dash = "%s-%s" % (settings.PACKAGINATOR_SEARCH_PREFIX, q)
        _space = "%s %s" % (settings.PACKAGINATOR_SEARCH_PREFIX, q)
        _underscore = '%s_%s' % (settings.PACKAGINATOR_SEARCH_PREFIX, q)
        packages = Package.objects.filter(
                        Q(title__istartswith=q) |
                        Q(title__istartswith=_dash) |
                        Q(title__istartswith=_space) |
                        Q(title__istartswith=_underscore)
                    )

    packages_already_added_list = []
    grid_slug = request.GET.get("grid", "")
    if packages and grid_slug:
        grids = Grid.objects.filter(slug=grid_slug)
        if grids:
            grid = grids[0]
            packages_already_added_list = [x['slug'] for x in grid.packages.all().values('slug')]
            new_packages = tuple(packages.exclude(slug__in=packages_already_added_list))[:20]
            number_of_packages = len(new_packages)
            if number_of_packages < 20:
                try:
                    old_packages = packages.filter(slug__in=packages_already_added_list)[:20 - number_of_packages]
                except AssertionError:
                    old_packages = None

                if old_packages:
                    old_packages = tuple(old_packages)
                    packages = new_packages + old_packages
            else:
                packages = new_packages

    return render(request, template_name, {
        "packages": packages,
        'packages_already_added_list': packages_already_added_list,
        }
    )


def usage(request, slug, action):
    success = False
    # Check if the user is authenticated, redirecting them to the login page if
    # they're not.
    if not request.user.is_authenticated():

        url = settings.LOGIN_URL
        referer = request.META.get('HTTP_REFERER')
        if referer:
            url += quote_plus('?next=/%s' % referer.split('/', 3)[-1])
        else:
            url += '?next=%s' % reverse('usage', args=(slug, action))
        url = reverse("login")
        if request.is_ajax():
            response = {}
            response['success'] = success
            response['redirect'] = url
            return HttpResponse(json.dumps(response))
        return HttpResponseRedirect(url)

    package = get_object_or_404(Package, slug=slug)

    # Update the current user's usage of the given package as specified by the
    # request.
    if package.usage.filter(username=request.user.username):
        if action.lower() == 'add':
            # The user is already using the package
            success = True
            change = 0
        else:
            # If the action was not add and the user has already specified
            # they are a use the package then remove their usage.
            package.usage.remove(request.user)
            success = True
            change = -1
    else:
        if action.lower() == 'lower':
            # The user is not using the package
            success = True
            change = 0
        else:
            # If the action was not lower and the user is not already using
            # the package then add their usage.
            package.usage.add(request.user)
            success = True
            change = 1

    # Invalidate the cache of this users's used_packages_list.
    if change == 1 or change == -1:
        cache_key = "sitewide_used_packages_list_%s" % request.user.pk
        cache.delete(cache_key)
        package.grid_clear_detail_template_cache()

    # Return an ajax-appropriate response if necessary
    if request.is_ajax():
        response = {'success': success}
        if success:
            response['change'] = change

        return HttpResponse(json.dumps(response))

    # Intelligently determine the URL to redirect the user to based on the
    # available information.
    next = request.GET.get('next') or request.META.get("HTTP_REFERER") or reverse("package", kwargs={"slug": package.slug})
    return HttpResponseRedirect(next)


def package_list(request, template_name="package/package_list.html"):

    categories = []
    for category in Category.objects.annotate(package_count=Count("package")):
        element = {
            "title": category.title,
            "description": category.description,
            "count": category.package_count,
            "slug": category.slug,
            "title_plural": category.title_plural,
            "show_pypi": category.show_pypi,
            "packages": category.package_set.annotate(usage_count=Count("usage")).order_by("-pypi_downloads", "-repo_watchers", "title")[:9]
        }
        categories.append(element)

    return render(
        request,
        template_name, {
            "categories": categories,
            "dpotw": Dpotw.objects.get_current(),
            "gotw": Gotw.objects.get_current(),
        }
    )


def package_detail(request, slug, template_name="package/package.html"):

    package = get_object_or_404(Package, slug=slug)
    no_development = package.no_development
    try:
        if package.category == Category.objects.get(slug='projects'):
            # projects get a bye because they are a website
            pypi_ancient = False
            pypi_no_release = False
        else:
            pypi_ancient = package.pypi_ancient
            pypi_no_release = package.pypi_ancient is None
        warnings = no_development or pypi_ancient or pypi_no_release
    except Category.DoesNotExist:
        pypi_ancient = False
        pypi_no_release = False
        warnings = no_development

    if request.GET.get("message"):
        messages.add_message(request, messages.INFO, request.GET.get("message"))

    return render(request, template_name,
            dict(
                package=package,
                pypi_ancient=pypi_ancient,
                no_development=no_development,
                pypi_no_release=pypi_no_release,
                warnings=warnings,
                latest_version=package.last_released(),
                repo=package.repo
            )
        )


def int_or_0(value):
    try:
        return int(value)
    except ValueError:
        return 0


@login_required
def post_data(request, slug):
    # if request.method == "POST":
        # try:
        #     # TODO Do this this with a form, really. Duh!
        #     package.repo_watchers = int_or_0(request.POST.get("repo_watchers"))
        #     package.repo_forks = int_or_0(request.POST.get("repo_forks"))
        #     package.repo_description = request.POST.get("repo_description")
        #     package.participants = request.POST.get('contributors')
        #     package.fetch_commits()  # also saves
        # except Exception as e:
        #     print e
    package = get_object_or_404(Package, slug=slug)
    package.fetch_pypi_data()
    package.repo.fetch_metadata(package)
    package.repo.fetch_commits(package)
    package.last_fetched = timezone.now()
    package.save()
    return HttpResponseRedirect(reverse("package", kwargs={"slug": package.slug}))


@login_required
def edit_documentation(request, slug, template_name="package/documentation_form.html"):
    package = get_object_or_404(Package, slug=slug)
    form = DocumentationForm(request.POST or None, instance=package)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.INFO, 'Package documentation updated successfully')
        return redirect(package)
    return render(request, template_name,
            dict(
                package=package,
                form=form
            )
        )


@csrf_view_exempt
def github_webhook(request):
    if request.method == "POST":
        data = json.loads(request.POST['payload'])

        # Webhook Test
        if "zen" in data:
            return HttpResponse(data['hook_id'])

        repo_url = data['repository']['url']

        # service test
        if repo_url == "http://github.com/mojombo/grit":
            return HttpResponse("Service Test pass")

        package = get_object_or_404(Package, repo_url=repo_url)
        package.repo.fetch_commits(package)
        package.last_fetched = timezone.now()
        package.save()
    return HttpResponse()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from reversion.admin import VersionAdmin

from profiles.models import Profile


def username(obj):
    return (obj.user.username)
username.short_description = "User username"


def user_email(obj):
    return (obj.user.email)
username.short_description = "User email"


class ProfileAdmin(VersionAdmin):

    search_fields = ("user__username", "github_account", "user__email", "email")
    list_display = ("github_account", "email", username, user_email)

admin.site.register(Profile, ProfileAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from django.utils.functional import lazy, memoize, SimpleLazyObject


def lazy_profile(request):
    """
    Returns context variables required by templates that assume a profile
    on each request
    """

    def get_user_profile():
        if hasattr(request, 'profile'):
            return request.profile
        else:
            return request.user.get_profile()

    data = {
        'profile': SimpleLazyObject(get_user_profile),
        }
    return data

########NEW FILE########
__FILENAME__ = forms
from django import forms

from profiles.models import Profile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, HTML

class ProfileForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_action = 'profile_edit'
        self.helper.layout = Layout(
            Fieldset(
                '',
                HTML("""
                    <p>Github account, <strong>{{ profile.github_account }}</strong></p>
                """),
                'bitbucket_url',
                'google_code_url',
            ),
            ButtonHolder(
                Submit('edit', 'Edit', css_class='btn btn-default')
            )
        )

    class Meta:
        fields = (
            'bitbucket_url',
            'google_code_url',
        )
        model = Profile

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Profile'
        db.create_table('profiles_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('github_url', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('bitbucket_url', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('google_code_url', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('profiles', ['Profile'])


    def backwards(self, orm):
        
        # Deleting model 'Profile'
        db.delete_table('profiles_profile')


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
        'profiles.profile': {
            'Meta': {'object_name': 'Profile'},
            'bitbucket_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'google_code_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_profile_created__add_field_profile_modified
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Profile.created'
        db.add_column('profiles_profile', 'created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True), keep_default=False)

        # Adding field 'Profile.modified'
        db.add_column('profiles_profile', 'modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Profile.created'
        db.delete_column('profiles_profile', 'created')

        # Deleting field 'Profile.modified'
        db.delete_column('profiles_profile', 'modified')


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
        'profiles.profile': {
            'Meta': {'object_name': 'Profile'},
            'bitbucket_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'google_code_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_profile_email
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Profile.email'
        db.add_column('profiles_profile', 'email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Profile.email'
        db.delete_column('profiles_profile', 'email')


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
        'profiles.profile': {
            'Meta': {'object_name': 'Profile'},
            'bitbucket_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'google_code_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_profile_github_account
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Profile.github_account'
        db.add_column('profiles_profile', 'github_account', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Profile.github_account'
        db.delete_column('profiles_profile', 'github_account')


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
        'profiles.profile': {
            'Meta': {'object_name': 'Profile'},
            'bitbucket_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'github_account': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'google_code_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.models import BaseModel


class Profile(BaseModel):
    user = models.OneToOneField(User)

    # Note to coders: The '_url' fields below need to JUST be the name of the account.
    #     Examples:
    #       github_url = 'pydanny'
    #       bitbucket_url = 'pydanny'
    #       google_code_url = 'pydanny'
    github_account = models.CharField(_("Github account"), null=True, blank=True, max_length=40)
    github_url = models.CharField(_("Github account"), null=True, blank=True, max_length=100, editable=False)
    bitbucket_url = models.CharField(_("Bitbucket account"), null=True, blank=True, max_length=100)
    google_code_url = models.CharField(_("Google Code account"), null=True, blank=True, max_length=100)
    email = models.EmailField(_("Email"), null=True, blank=True)

    def __unicode__(self):
        if not self.github_account:
            return self.user.username
        return self.github_account

    def save(self, **kwargs):
        """ Override save to always populate email changes to auth.user model
        """
        if self.email is not None:

            email = self.email.strip()
            user_obj = User.objects.get(username=self.user.username)
            user_obj.email = email
            user_obj.save()

        super(Profile, self).save(**kwargs)

    def url_for_repo(self, repo):
        """Return the profile's URL for a given repo.

        If url doesn't exist return None.
        """
        url_mapping = {
            'Github': self.github_account,
            'BitBucket': self.bitbucket_url,
            'Google Code': self.google_code_url}
        return url_mapping.get(repo.title)

    def my_packages(self):
        """Return a list of all packages the user contributes to.

        List is sorted by package name.
        """
        from package.repos import get_repo, supported_repos

        packages = []
        for repo in supported_repos():
            repo = get_repo(repo)
            repo_packages = repo.packages_for_profile(self)
            packages.extend(repo_packages)
        packages.sort(lambda a, b: cmp(a.title, b.title))
        return packages
        
    @models.permalink
    def get_absolute_url(self):
        return ("profile_detail", [self.github_account])

    # define permission properties as properties so we can access in templates

    @property
    def can_add_package(self):
        if getattr(settings, 'RESTRICT_PACKAGE_EDITORS', False):
            return self.user.has_perm('package.add_package')
        # anyone can add
        return True

    @property
    def can_edit_package(self):
        if getattr(settings, 'RESTRICT_PACKAGE_EDITORS', False):
            # this is inconsistent, fix later?
            return self.user.has_perm('package.change_package')
        # anyone can edit
        return True

    # Grids
    @property
    def can_edit_grid(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.change_grid')
        return True

    @property
    def can_add_grid(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.add_grid')
        return True

    # Grid Features
    @property
    def can_add_grid_feature(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.add_feature')
        return True

    @property
    def can_edit_grid_feature(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.change_feature')
        return True

    @property
    def can_delete_grid_feature(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.delete_feature')
        return True

    # Grid Packages
    @property
    def can_add_grid_package(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.add_gridpackage')
        return True

    @property
    def can_delete_grid_package(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.delete_gridpackage')
        return True

    # Grid Element (cells in grid)
    @property
    def can_edit_grid_element(self):
        if getattr(settings, 'RESTRICT_GRID_EDITORS', False):
            return self.user.has_perm('grid.change_element')
        return True
########NEW FILE########
__FILENAME__ = profile_tags
from django import template

register = template.Library()


@register.filter
def package_usage(user):
    return user.package_set.all()

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase


class MockGithubRepo(object):
    title = "Github"


class TestModel(TestCase):
    def test_profile(self):
        from profiles.models import Profile
        p = Profile()
        self.assertEqual(len(p.my_packages()), 0)

        r = MockGithubRepo()
        self.assertEqual(p.url_for_repo(r), None)

########NEW FILE########
__FILENAME__ = test_views
from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from core.tests.data import create_users, STOCK_PASSWORD
from profiles.models import Profile


class TestProfile(TestCase):

    def setUp(self):
        super(TestProfile, self).setUp()
        create_users()
        self.user = User.objects.get(username="user")
        self.profile = Profile.objects.create(
            github_account="user",
            user=self.user,
        )

    def test_view(self):
        self.assertTrue(self.client.login(username=self.user.username, password=STOCK_PASSWORD))
        url = reverse('profile_detail', kwargs={'github_account': self.profile.github_account})
        response = self.client.get(url)
        self.assertContains(response, "Profile for user")

    def test_view_not_loggedin(self):
        url = reverse('profile_detail', kwargs={'github_account': self.profile.github_account})
        response = self.client.get(url)
        self.assertContains(response, "Profile for user")

    def test_edit(self):
        self.assertTrue(self.client.login(username=self.user.username, password=STOCK_PASSWORD))

        # give me a view
        url = reverse('profile_edit')
        response = self.client.get(url)
        stuff = """<input id="id_bitbucket_url" type="text" class="textInput textinput" name="bitbucket_url" maxlength="100" />"""
        stuff = """<input id="id_bitbucket_url" type="text" class="textinput textInput form-control" name="bitbucket_url" maxlength="100" />"""
        self.assertContains(response, stuff)

        # submit some content
        data = {
            'bitbucket_url': 'zerg',
            }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "Profile for user")
        p = Profile.objects.get(user=self.user)
        self.assertEquals(p.bitbucket_url, "zerg")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from profiles import views

urlpatterns = patterns("",
    url(
        regex=r"^edit/$",
        view=views.ProfileEditUpdateView.as_view(),
        name="profile_edit"
    ),
    url(r"^$", views.profile_list, name="profile_list"),
    url(r"^(?P<github_account>[-\w]+)/$", views.profile_detail, name="profile_detail"),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView

from braces.views import LoginRequiredMixin

from social_auth.signals import pre_update
from social_auth.backends.contrib.github import GithubBackend

from profiles.forms import ProfileForm
from profiles.models import Profile


def profile_detail(request, github_account, template_name="profiles/profile.html"):

    profile = get_object_or_404(Profile, github_account=github_account)

    return render(request, template_name,
        {"local_profile": profile, "user": profile.user},)


def profile_list(request, template_name="profiles/profiles.html"):

    if request.user.is_staff:
        users = User.objects.all()
    else:
        users = User.objects.filter(is_active=True)

    return render(request, template_name,
        {
            "users": users
        })


class ProfileEditUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "profiles/profile_edit.html"

    def get_object(self):
        return self.request.user.get_profile()

    def form_valid(self, form):
        form.save()
        messages.add_message(self.request, messages.INFO, "Profile Saved")
        return HttpResponseRedirect(reverse("profile_detail", kwargs={"github_account": self.get_object()}))


def github_user_update(sender, user, response, details, **kwargs):
    profile_instance, created = Profile.objects.get_or_create(user=user)
    profile_instance.github_account = details['username']
    profile_instance.email = details['email']
    profile_instance.save()
    return True

pre_update.connect(github_user_update, sender=GithubBackend)


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from searchv2.models import SearchV2


class SearchV2Admin(admin.ModelAdmin):

    search_fields = ("title", "title_no_prefix")

admin.site.register(SearchV2, SearchV2Admin)

########NEW FILE########
__FILENAME__ = builders
from datetime import datetime, timedelta
import json
from sys import stdout

import requests

from grid.models import Grid
from package.models import Package, Commit
from searchv2.models import SearchV2
from searchv2.utils import remove_prefix, clean_title


def build_1(print_out=False):

    now = datetime.now()
    quarter_delta = timedelta(90)
    half_year_delta = timedelta(182)
    year_delta = timedelta(365)
    last_week = now - timedelta(7)

    SearchV2.objects.filter(created__lte=last_week).delete()
    for package in Package.objects.filter():

        obj, created = SearchV2.objects.get_or_create(
            item_type="package",
            slug=package.slug,
        )
        obj.slug_no_prefix = remove_prefix(package.slug)
        obj.clean_title = clean_title(remove_prefix(package.slug))
        obj.title = package.title
        obj.title_no_prefix = remove_prefix(package.title)
        obj.description = package.repo_description
        obj.category = package.category.title
        obj.absolute_url = package.get_absolute_url()
        obj.repo_watchers = package.repo_watchers
        obj.repo_forks = package.repo_forks
        obj.pypi_downloads = package.pypi_downloads
        obj.usage = package.usage.count()
        obj.participants = package.participants

        optional_save = False
        try:
            obj.last_committed = package.last_updated()
            optional_save = True
        except Commit.DoesNotExist:
            pass

        last_released = package.last_released()
        if last_released and last_released.upload_time:
            obj.last_released = last_released.upload_time
            optional_save = True

        if optional_save:
            obj.save()

        # Weighting part
        # Weighting part
        # Weighting part
        weight = 0
        optional_save = False

        # Read the docs!
        rtfd_url = "http://readthedocs.org/api/v1/build/{0}/".format(obj.slug)
        r = requests.get(rtfd_url)
        if r.status_code == 200:
            data = json.loads(r.content)
            if data['meta']['total_count']:
                weight += 20

        if obj.description.strip():
            weight += 20

        if obj.repo_watchers:
            weight += min(obj.repo_watchers, 20)

        if obj.repo_forks:
            weight += min(obj.repo_forks, 20)

        if obj.pypi_downloads:
            weight += min(obj.pypi_downloads / 1000, 20)

        if obj.usage:
            weight += min(obj.usage, 20)

        # Is there ongoing work or is this forgotten?
        if obj.last_committed:
            if now - obj.last_committed < quarter_delta:
                weight += 20
            elif now - obj.last_committed < half_year_delta:
                weight += 10
            elif now - obj.last_committed < year_delta:
                weight += 5

        # Is the last release less than a year old?
        last_released = obj.last_released
        if last_released:
            if now - last_released < year_delta:
                weight += 20

        if weight:
            obj.weight = weight
            obj.save()

        if print_out:
            print >> stdout, obj.slug, created

    print >> stdout, '----------------------'
    max_weight = SearchV2.objects.all()[0].weight
    increment = max_weight / 6
    for grid in Grid.objects.all():
        obj, created = SearchV2.objects.get_or_create(
            item_type="grid",
            slug=grid.slug,
        )
        obj.slug_no_prefix = remove_prefix(grid.slug)
        obj.clean_title = clean_title(remove_prefix(grid.slug))
        obj.title = grid.title
        obj.title_no_prefix = remove_prefix(grid.title)
        obj.description = grid.description
        obj.absolute_url = grid.get_absolute_url()

        weight = max_weight - increment

        if not grid.is_locked:
            weight -= increment

        if not grid.header:
            weight -= increment

        if not grid.packages.count():
            weight -= increment

        obj.weight = weight
        obj.save()

        print >> stdout, obj, created

    return SearchV2.objects.all()

########NEW FILE########
__FILENAME__ = forms
from django import forms


class SearchForm(forms.Form):
    """ Simple q based search form """

    q = forms.CharField(label="Search Packages", max_length=100)

########NEW FILE########
__FILENAME__ = searchv2_build
from sys import stdout
from time import gmtime, strftime

from django.core.management.base import NoArgsCommand

from searchv2.builders import build_1


class Command(NoArgsCommand):

    help = "Constructs the search results for the system"

    def handle(self, *args, **options):

        print >> stdout, "Commencing search result building now %s " % strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        build_1()
        print >> stdout, "Finished at %s" % strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SearchV2'
        db.create_table('searchv2_searchv2', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('weight', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('item_type', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length='100')),
            ('title_no_prefix', self.gf('django.db.models.fields.CharField')(max_length='100')),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('absolute_url', self.gf('django.db.models.fields.CharField')(max_length='255')),
            ('repo_watchers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('repo_forks', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('pypi_downloads', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('usage', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('participants', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('last_committed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_released', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('searchv2', ['SearchV2'])


    def backwards(self, orm):
        
        # Deleting model 'SearchV2'
        db.delete_table('searchv2_searchv2')


    models = {
        'searchv2.searchv2': {
            'Meta': {'ordering': "['-weight']", 'object_name': 'SearchV2'},
            'absolute_url': ('django.db.models.fields.CharField', [], {'max_length': "'255'"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'last_committed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_released': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'title_no_prefix': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['searchv2']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_searchv2_slug__add_field_searchv2_slug_no_prefix
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'SearchV2.slug'
        db.add_column('searchv2_searchv2', 'slug', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, db_index=True), keep_default=False)

        # Adding field 'SearchV2.slug_no_prefix'
        db.add_column('searchv2_searchv2', 'slug_no_prefix', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, db_index=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'SearchV2.slug'
        db.delete_column('searchv2_searchv2', 'slug')

        # Deleting field 'SearchV2.slug_no_prefix'
        db.delete_column('searchv2_searchv2', 'slug_no_prefix')


    models = {
        'searchv2.searchv2': {
            'Meta': {'ordering': "['-weight']", 'object_name': 'SearchV2'},
            'absolute_url': ('django.db.models.fields.CharField', [], {'max_length': "'255'"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'last_committed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_released': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'slug_no_prefix': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'title_no_prefix': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['searchv2']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_searchv2_clean_title
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'SearchV2.clean_title'
        db.add_column('searchv2_searchv2', 'clean_title', self.gf('django.db.models.fields.CharField')(default='x', max_length='100'), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'SearchV2.clean_title'
        db.delete_column('searchv2_searchv2', 'clean_title')


    models = {
        'searchv2.searchv2': {
            'Meta': {'ordering': "['-weight']", 'object_name': 'SearchV2'},
            'absolute_url': ('django.db.models.fields.CharField', [], {'max_length': "'255'"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'clean_title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'last_committed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_released': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'slug_no_prefix': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'title_no_prefix': ('django.db.models.fields.CharField', [], {'max_length': "'100'"}),
            'usage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['searchv2']

########NEW FILE########
__FILENAME__ = 0004_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'SearchV2', fields ['title_no_prefix']
        db.create_index('searchv2_searchv2', ['title_no_prefix'])

        # Adding index on 'SearchV2', fields ['title']
        db.create_index('searchv2_searchv2', ['title'])

        # Adding index on 'SearchV2', fields ['clean_title']
        db.create_index('searchv2_searchv2', ['clean_title'])


    def backwards(self, orm):
        # Removing index on 'SearchV2', fields ['clean_title']
        db.delete_index('searchv2_searchv2', ['clean_title'])

        # Removing index on 'SearchV2', fields ['title']
        db.delete_index('searchv2_searchv2', ['title'])

        # Removing index on 'SearchV2', fields ['title_no_prefix']
        db.delete_index('searchv2_searchv2', ['title_no_prefix'])


    models = {
        'searchv2.searchv2': {
            'Meta': {'ordering': "['-weight']", 'object_name': 'SearchV2'},
            'absolute_url': ('django.db.models.fields.CharField', [], {'max_length': "'255'"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'clean_title': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'last_committed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_released': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'participants': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pypi_downloads': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo_watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'slug_no_prefix': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'db_index': 'True'}),
            'title_no_prefix': ('django.db.models.fields.CharField', [], {'max_length': "'100'", 'db_index': 'True'}),
            'usage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['searchv2']
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.models import BaseModel
from package.models import Package

ITEM_TYPE_CHOICES = (
    ('package', 'Package'),
    ('grid', 'Grid'),
)


class SearchV2(BaseModel):
    """
        Searches available on:

            title
            description
            grids
            pacakges
            categories
            number of watchers
            number of forks
            last repo commit
            last release on PyPI
    """

    weight = models.IntegerField(_("Weight"), default=0)
    item_type = models.CharField(_("Item Type"), max_length=40, choices=ITEM_TYPE_CHOICES)
    title = models.CharField(_("Title"), max_length="100", db_index=True)
    title_no_prefix = models.CharField(_("No Prefix Title"), max_length="100", db_index=True)
    slug = models.SlugField(_("Slug"), db_index=True)
    slug_no_prefix = models.SlugField(_("No Prefix Slug"), db_index=True)
    clean_title = models.CharField(_("Clean title with no crud"), max_length="100", db_index=True)
    description = models.TextField(_("Repo Description"), blank=True)
    category = models.CharField(_("Category"), blank=True, max_length=50)
    absolute_url = models.CharField(_("Absolute URL"), max_length="255")
    repo_watchers = models.IntegerField(_("repo watchers"), default=0)
    repo_forks = models.IntegerField(_("repo forks"), default=0)
    pypi_downloads = models.IntegerField(_("Pypi downloads"), default=0)
    usage = models.IntegerField(_("Number of users"), default=0)
    participants = models.TextField(_("Participants"),
                        help_text="List of collaborats/participants on the project", blank=True)
    last_committed = models.DateTimeField(_("Last commit"), blank=True, null=True)
    last_released = models.DateTimeField(_("Last release"), blank=True, null=True)

    class Meta:
        ordering = ['-weight', ]
        verbose_name_plural = 'SearchV2s'

    def __unicode__(self):
        return "{0}:{1}".format(self.weight, self.title)

    @models.permalink
    def get_absolute_url(self):
        return self.absolute_url

    def pypi_name(self):
        key = "SEARCH_PYPI_NAME-{0}".format(self.slug)
        pypi_name = cache.get(key)
        if pypi_name:
            return pypi_name
        try:
            package = Package.objects.get(slug=self.slug)
        except Package.DoesNotExist:
            return ""
        pypi_name = package.pypi_name
        cache.set(key, pypi_name, 24 * 60 * 60)
        return pypi_name

########NEW FILE########
__FILENAME__ = test_builders
from django.test import TestCase

from package.tests import initial_data
from searchv2.models import SearchV2
from searchv2.builders import build_1


class BuilderTest(TestCase):

    def setUp(self):
        initial_data.load()

    def test_build_1_count(self):
        self.assertEquals(SearchV2.objects.count(), 0)
        build_1(False)
        self.assertEquals(SearchV2.objects.count(), 6)

########NEW FILE########
__FILENAME__ = test_models
from datetime import datetime

from django.test import TestCase

from searchv2.models import SearchV2


class SearchV2Test(TestCase):

    def test_create(self):
        SearchV2.objects.create(
            item_type='package',
            title='Django Uni-Form',
            title_no_prefix='uni-form',
            slug='django-uni-form',
            slug_no_prefix='uni-form',
            clean_title='uniform',
            description="Blah blah blah",
            category='app',
            absolute_url='/packages/p/django-uni-form/',
            repo_watchers=500,
            repo_forks=85,
            pypi_downloads=30000,
            participants="pydanny,maraujop,et,al",
            last_committed=datetime.now(),
            last_released=datetime.now(),
        )
        self.assertEquals(SearchV2.objects.count(), 1)

########NEW FILE########
__FILENAME__ = test_utils
from django.conf import settings
from django.test import TestCase

from searchv2.utils import remove_prefix, clean_title


class UtilFunctionTest(TestCase):

    def setUp(self):
        self.values = []
        for value in ["-me", ".me", "/me", "_me"]:
            value = "{0}{1}".format(settings.PACKAGINATOR_SEARCH_PREFIX.lower(), value)
            self.values.append(value)

    def test_remove_prefix(self):
        for value in self.values:
            self.assertEqual(remove_prefix(value), "me")

    def test_clean_title(self):
        test_value = "{0}me".format(settings.PACKAGINATOR_SEARCH_PREFIX.lower())
        for value in self.values:
            self.assertEqual(clean_title(value), test_value)

########NEW FILE########
__FILENAME__ = test_views
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from package.tests import initial_data
from profiles.models import Profile
from searchv2.builders import build_1
from searchv2.models import SearchV2
from searchv2.views import search_function


class FunctionalPackageTest(TestCase):
    def setUp(self):
        initial_data.load()
        for user in User.objects.all():
            profile = Profile.objects.create(user=user)
            profile.save()

    def test_build_search(self):

        count = SearchV2.objects.count()
        url = reverse('build_search')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(count, 0)

        self.assertTrue(self.client.login(username='user', password='user'))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)
        self.assertEquals(SearchV2.objects.count(), 0)

        self.assertTrue(self.client.login(username='admin', password='admin'))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(SearchV2.objects.count(), 0)

        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(SearchV2.objects.count(), 6)

    def test_search_function(self):
        build_1(False)
        results = search_function('ser')
        self.assertEquals(results[0].title, 'Serious Testing')


class ViewTest(TestCase):

    def setUp(self):
        initial_data.load()
        for user in User.objects.all():
            profile = Profile.objects.create(user=user)
            profile.save()
        build_1()

    def test_search(self):
        """ TODO Get this stupid test working """
        self.assertTrue(self.client.login(username='admin', password='admin'))
        url = reverse('search') + '?q=django-uni-form'
        data = {'q': 'another-test'}
        response = self.client.get(url, data, follow=True)
        self.assertContains(response, 'another-test')
        # print response
        # print Package.objects.all()
        # print SearchV2.objects.all()

    def test_multiple_items(self):
        self.assertTrue(self.client.login(username='admin', password='admin'))
        SearchV2.objects.get_or_create(
            item_type="package",
            title="django-uni-form",
            slug="django-uni-form",
            slug_no_prefix="uni-form",
            clean_title="django-uni-form"
        )
        url = reverse('search') + '?q=django-uni-form'
        response = self.client.get(url)
        #print response

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from searchv2 import views

urlpatterns = patterns("",

    url(
        regex   = '^build$',
        view    = views.build_search,
        name    = 'build_search',
    ),

    url(
        regex   = '^$',
        view    = views.search2,
        name    = 'search',
    ),

    url(
        regex   = '^packages/autocomplete/$',
        view    = views.search_packages_autocomplete,
        name    = 'search_packages_autocomplete',
    ),

)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.template.defaultfilters import slugify

CHARS = ["_", ",", ".", "-", " ", "/", "|"]


def remove_prefix(value):
    value = value.lower()
    for char in CHARS:
        value = value.replace("{0}{1}".format(settings.PACKAGINATOR_SEARCH_PREFIX.lower(), char), "")
    return value


def clean_title(value):
    value = slugify(value)
    for char in CHARS:
        value = value.replace(char, "")
    return value

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals
import json

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db.models import Max
from django.http import HttpResponseForbidden, HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from rest_framework.generics import ListAPIView, RetrieveAPIView

from homepage.views import homepage
from package.models import Package
from searchv2.forms import SearchForm
from searchv2.builders import build_1
from searchv2.models import SearchV2
from searchv2.utils import remove_prefix, clean_title


@login_required
def build_search(request, template_name="searchv2/build_results.html"):

    if not request.user.is_superuser:
        return HttpResponseForbidden()

    results = []
    if request.method == 'POST':
        results = build_1(False)

    return render(request, template_name,
                {'results': results})


def search_function(q):
    """ TODO - make generic title searches have lower weight """

    items = []
    if q:
        items = SearchV2.objects.filter(
                    Q(clean_title__startswith=clean_title(remove_prefix(q))) |
                    Q(title__icontains=q) |
                    Q(title_no_prefix__startswith=q.lower()) |
                    Q(slug__startswith=q.lower()) |
                    Q(slug_no_prefix__startswith=q.lower()))
        #grids    = Grid.objects.filter(Q(title__icontains=q) | Q(description__icontains=q))
    return items


def search(request, template_name='searchv2/search.html'):
    """
    Searches in Grids and Packages
    """
    q = request.GET.get('q', '')

    if '/' in q:
        lst = q.split('/')
        try:
            if lst[-1]:
                q = lst[-1]
            else:
                q = lst[-2]
        except IndexError:
            pass
    try:
        package = Package.objects.get(title=q)
        url = reverse("package", args=[package.slug.lower()])
        return HttpResponseRedirect(url)
    except Package.DoesNotExist:
        pass
    except Package.MultipleObjectsReturned:
        pass

    try:
        package = Package.objects.get(slug=q)
        url = reverse("package", args=[package.slug.lower()])
        return HttpResponseRedirect(url)
    except Package.DoesNotExist:
        pass
    except Package.MultipleObjectsReturned:
        pass

    form = SearchForm(request.GET or None)

    return render(request, template_name, {
            'items': search_function(q),
            'form': form,
            'max_weight': SearchV2.objects.all().aggregate(Max('weight'))['weight__max']
        })

def search2(request, template_name='searchv2/search.html'):
    """
    Searches in Grids and Packages
    """
    return homepage(request, template_name=template_name)


def search_packages_autocomplete(request):
    """
    Searches in Packages
    """
    q = request.GET.get('term', '')
    if q:
        objects = search_function(q)[:15]
        objects = objects.values_list('title', flat=True)
        json_response = json.dumps(list(objects))
    else:
        json_response = json.dumps([])

    return HttpResponse(json_response, mimetype='text/javascript')


class SearchListAPIView(ListAPIView):
    model = SearchV2
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        return search_function(q)


class SearchDetailAPIView(RetrieveAPIView):
    model = SearchV2

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
# Django settings

import os.path
from os import environ

from django.template.defaultfilters import slugify

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# serve media through the staticfiles app.
SERVE_MEDIA = DEBUG

INTERNAL_IPS = [
    "127.0.0.1",
]

ADMINS = [
    ("Daniel Greenfeld", "pydanny@gmail.com"),
]

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "US/Eastern"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = "/media/"

# Absolute path to the directory that holds static files like app media.
# Example: "/home/media/media.lawrence.com/apps/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "collected_static")

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = "/static/"

# Additional directories which hold static files
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, "static"),
]

# Use the default admin media prefix, which is...
#ADMIN_MEDIA_PREFIX = "/static/admin/"

# List of callables that know how to import templates from various sources.
from memcacheify import memcacheify
CACHES = memcacheify()
TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.UserBasedExceptionMiddleware",
    "reversion.middleware.RevisionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "pagination.middleware.PaginationMiddleware",
    "django_sorting.middleware.SortingMiddleware"
)

TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, "templates"),
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",

    "django.core.context_processors.static",

    "package.context_processors.used_packages_list",
    "grid.context_processors.grid_headers",
    "core.context_processors.current_path",
    "profiles.context_processors.lazy_profile",
    "core.context_processors.core_values",
]

PROJECT_APPS = [
    "grid",
    'core',
    "homepage",
    "package",
    "profiles",
    "apiv1",
    "feeds",
    "searchv2",
    "apiv3"
]

PREREQ_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",

    # external
    "crispy_forms",
    "pagination",
    "django_extensions",
    "south",
    "tastypie",
    "reversion",
    "django_sorting",
    #"django_modeler",

    'social_auth',
    'floppyforms',
    'rest_framework',

]

INSTALLED_APPS = PREREQ_APPS + PROJECT_APPS


MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/profiles/profile/%s/" % o.username,
}

AUTH_PROFILE_MODULE = "profiles.Profile"

LOGIN_URL = "/login/github/"
LOGIN_REDIRECT_URLNAME = "home"

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = DEBUG

CACHE_TIMEOUT = 60 * 60

ROOT_URLCONF = "urls"

SECRET_KEY = "CHANGEME"

URCHIN_ID = ""

DEFAULT_FROM_EMAIL = 'Django Packages <djangopackages-noreply@djangopackages.com>'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_SUBJECT_PREFIX = '[Django Packages] '
try:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_PASSWORD = os.environ['SENDGRID_PASSWORD']
    EMAIL_HOST_USER = os.environ['SENDGRID_USERNAME']
    EMAIL_PORT = 587
    SERVER_EMAIL = 'info@cartwheelweb.com'
    EMAIL_USE_TLS = True
    DEBUG = False
except Exception as e:
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025

EMAIL_SUBJECT_PREFIX = '[Cartwheel Web]'

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

PACKAGINATOR_HELP_TEXT = {
    "REPO_URL": "Enter your project repo hosting URL here. Example: https://github.com/opencomparison/opencomparison",
    "PYPI_URL": "<strong>Leave this blank if this package does not have a PyPI release.</strong> What PyPI uses to index your package. Example: django-uni-form",
}

PACKAGINATOR_SEARCH_PREFIX = "django"

# if set to False any auth user can add/modify packages
# only django admins can delete
RESTRICT_PACKAGE_EDITORS = True

# if set to False  any auth user can add/modify grids
# only django admins can delete
RESTRICT_GRID_EDITORS = True


LOCAL_INSTALLED_APPS = []
SUPPORTED_REPO = []

########################## Site specific stuff
FRAMEWORK_TITLE = "Django"
SITE_TITLE = "Django Packages"

if LOCAL_INSTALLED_APPS:
    INSTALLED_APPS.extend(LOCAL_INSTALLED_APPS)

SUPPORTED_REPO.extend(["bitbucket", "github"])


AUTHENTICATION_BACKENDS = (
    'social_auth.backends.contrib.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
)
GITHUB_API_SECRET = environ.get('GITHUB_API_SECRET')
GITHUB_APP_ID = environ.get('GITHUB_APP_ID')
GITHUB_USERNAME = environ.get('GITHUB_USERNAME')
GITHUB_PASSWORD = environ.get('GITHUB_PASSWORD')
SOCIAL_AUTH_ENABLED_BACKENDS = ('github')
SOCIAL_AUTH_COMPLETE_URL_NAME = 'socialauth_complete'
SOCIAL_AUTH_ASSOCIATE_URL_NAME = 'associate_complete'
SOCIAL_AUTH_DEFAULT_USERNAME = lambda u: slugify(u)
SOCIAL_AUTH_EXTRA_DATA = False
SOCIAL_AUTH_CHANGE_SIGNAL_ONLY = True
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
LOGIN_REDIRECT_URL = '/'

# associate user via email
#SOCIAL_AUTH_ASSOCIATE_BY_MAIL = True

DATABASES = {

    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "oc",          # Or path to database file if using sqlite3.
        "USER": "",              # Not used with sqlite3.
        "PASSWORD": "",                  # Not used with sqlite3.
        "HOST": "",             # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "",                  # Set to empty string for default. Not used with sqlite3.
    },
}


WSGI_APPLICATION = 'wsgi.application'

if DEBUG:

    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS += ('debug_toolbar',)
    
    INTERNAL_IPS = ('127.0.0.1',)
    
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TEMPLATE_CONTEXT': True,
    }
    x = 1

ADMIN_URL_BASE = environ.get('ADMIN_URL_BASE', r"^admin/")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logutils.colorize.ColorizingStreamHandler',
            'formatter': 'standard'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', ],
            'propagate': True,
            'level': 'ERROR',
        },
        'django.request': {

            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        '': {
            'handlers': ['console', ],
            'level': os.environ.get('DEBUG_LEVEL', 'ERROR'),
        },
    }
}


URL_REGEX_GITHUB = r'(?:http|https|git)://github.com/[^/]*/([^/]*)/{0,1}'

########### redis setup

# import redis
# from rq import Worker, Queue, Connection

########### end redis setup

########### crispy_forms setup
CRISPY_TEMPLATE_PACK = "bootstrap3"
########### end crispy_forms setup


########### LICENSES from PyPI
LICENSES = """License :: Aladdin Free Public License (AFPL)
License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
License :: DFSG approved
License :: Eiffel Forum License (EFL)
License :: Free For Educational Use
License :: Free For Home Use
License :: Free for non-commercial use
License :: Freely Distributable
License :: Free To Use But Restricted
License :: Freeware
License :: Netscape Public License (NPL)
License :: Nokia Open Source License (NOKOS)
License :: OSI Approved
License :: OSI Approved :: Academic Free License (AFL)
License :: OSI Approved :: Apache Software License
License :: OSI Approved :: Apple Public Source License
License :: OSI Approved :: Artistic License
License :: OSI Approved :: Attribution Assurance License
License :: OSI Approved :: BSD License
License :: OSI Approved :: Common Public License
License :: OSI Approved :: Eiffel Forum License
License :: OSI Approved :: European Union Public Licence 1.0 (EUPL 1.0)
License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)
License :: OSI Approved :: GNU Affero General Public License v3
License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)
License :: OSI Approved :: GNU Free Documentation License (FDL)
License :: OSI Approved :: GNU General Public License (GPL)
License :: OSI Approved :: GNU General Public License v2 (GPLv2)
License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)
License :: OSI Approved :: GNU General Public License v3 (GPLv3)
License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)
License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)
License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)
License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)
License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)
License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)
License :: OSI Approved :: IBM Public License
License :: OSI Approved :: Intel Open Source License
License :: OSI Approved :: ISC License (ISCL)
License :: OSI Approved :: Jabber Open Source License
License :: OSI Approved :: MIT License
License :: OSI Approved :: MITRE Collaborative Virtual Workspace License (CVW)
License :: OSI Approved :: Motosoto License
License :: OSI Approved :: Mozilla Public License 1.0 (MPL)
License :: OSI Approved :: Mozilla Public License 1.1 (MPL 1.1)
License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)
License :: OSI Approved :: Nethack General Public License
License :: OSI Approved :: Nokia Open Source License
License :: OSI Approved :: Open Group Test Suite License
License :: OSI Approved :: Python License (CNRI Python License)
License :: OSI Approved :: Python Software Foundation License
License :: OSI Approved :: Qt Public License (QPL)
License :: OSI Approved :: Ricoh Source Code Public License
License :: OSI Approved :: Sleepycat License
License :: OSI Approved :: Sun Industry Standards Source License (SISSL)
License :: OSI Approved :: Sun Public License
License :: OSI Approved :: University of Illinois/NCSA Open Source License
License :: OSI Approved :: Vovida Software License 1.0
License :: OSI Approved :: W3C License
License :: OSI Approved :: X.Net License
License :: OSI Approved :: zlib/libpng License
License :: OSI Approved :: Zope Public License
License :: Other/Proprietary License
License :: Public Domain
License :: Repoze Public License""".splitlines()
########### End LICENSES from PyPI
########NEW FILE########
__FILENAME__ = heroku
# -*- coding: utf-8 -*-
"""Heroku specific settings. These are used to deploy opencomparison to
Heroku's platform.
"""


from os import environ

from memcacheify import memcacheify
from postgresify import postgresify
from S3 import CallingFormat

from settings.base import *


########## CACHE
CACHE_TIMEOUT = 60 * 60 * 24 * 30
CACHES = memcacheify()


########## WSGI SERVER
INSTALLED_APPS += ['gunicorn']


########## EMAIL
DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL',
        'Django Packages <djangopackages-noreply@djangopackages.com>')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = environ.get('EMAIL_HOST', 'smtp.sendgrid.com')
EMAIL_HOST_PASSWORD = os.environ.get('SENDGRID_PASSWORD', '')
EMAIL_HOST_USER = os.environ.get('SENDGRID_USERNAME', '')
EMAIL_PORT = environ.get('EMAIL_PORT', 587)
EMAIL_SUBJECT_PREFIX = environ.get('EMAIL_SUBJECT_PREFIX', '[Django Packages] ')
EMAIL_USE_TLS = True
SERVER_EMAIL = EMAIL_HOST_USER


########## SECRET
SECRET_KEY = environ.get('SECRET_KEY', '')


########## GITHUB
GITHUB_API_SECRET = environ.get('GITHUB_API_SECRET')
GITHUB_APP_ID = environ.get('GITHUB_APP_ID')


########## SITE
SITE_TITLE = environ.get('SITE_TITLE')
FRAMEWORK_TITLE = environ.get('FRAMEWORK_TITLE')


########## STORAGE
INSTALLED_APPS += ['storages']
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = environ.get('AWS_STORAGE_BUCKET_NAME')

AWS_CALLING_FORMAT = CallingFormat.SUBDOMAIN
AWS_HEADERS = {
    'Expires': 'Thu, 15 Apr 2020 20:00:00 GMT',
    'Cache-Control': 'max-age=86400',
}
AWS_QUERYSTRING_AUTH = False

STATIC_URL = 'https://s3.amazonaws.com/%s/' % AWS_STORAGE_BUCKET_NAME
MEDIA_URL = STATIC_URL


########### Permissions
RESTRICT_PACKAGE_EDITORS = False
RESTRICT_GRID_EDITORS = False

########### Errors
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
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


########## DATABASE CONFIGURATION
# Setting PGSQL_POOLING to True means:
#   We use django_postgrespool to handle the database connection.
#   What this means is we use SqlAlchemy to handle the pool to PGSQL on Heroku, meaning we don't have
#   to reestablish connection to the database as often. Which means a faster app. The downside is there
#   is some risk as it's still a new project.
#
# Setting PGSQL_POOLING to False means:
#   We use the standard Django pgsql connection. The pooling isn't as good but we have more stability.
PGSQL_POOLING = False


if PGSQL_POOLING:
    import dj_database_url

    DATABASES = {'default': dj_database_url.config()}
    DATABASES['default']['ENGINE'] = 'django_postgrespool'

    SOUTH_DATABASE_ADAPTERS = {
        'default': 'south.db.postgresql_psycopg2'
    }

    DATABASE_POOL_ARGS = {
        'max_overflow': 10,
        'pool_size': 5,
        'recycle': 300
    }
else:
    from postgresify import postgresify

    DATABASES = postgresify()
########## END DATABASE CONFIGURATION


########## sslify
MIDDLEWARE_CLASSES = ('sslify.middleware.SSLifyMiddleware',) + MIDDLEWARE_CLASSES
########## end sslify

########## django-secure

INSTALLED_APPS += ["djangosecure", ]

# set this to 60 seconds and then to 518400 when you can prove it works
SECURE_HSTS_SECONDS = 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_FRAME_DENY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = True

########## end django-secure


########## templates
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

########## end templates

########## appenlight-client
import appenlight_client.client as e_client
APPENLIGHT = e_client.get_config({'appenlight.api_key': environ.get('APPENLIGHT_KEY', '')})

MIDDLEWARE_CLASSES = (
    'appenlight_client.django_middleware.AppenlightMiddleware',
) + MIDDLEWARE_CLASSES
########## end appenlight-client
########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
"""Local test settings and globals which allows us to run our test suite
locally.
"""


from settings.base import *


########## DEBUG
DEBUG = True
TEMPLATE_DEBUG = DEBUG
SERVE_MEDIA = DEBUG


########## TEST
TEST_RUNNER = 'testrunner.OurCoverageRunner'

COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'big_email_send$',
    'load_dev_data$', 'fix_grid_element$',
    'package_updater$', 'searchv2_build$', 'debug_toolbar',
    'pypi_updater', 'repo_updater'
]
COVERAGE_REPORT_HTML_OUTPUT_DIR = "coverage"

########NEW FILE########
__FILENAME__ = testrunner
# Make our own testrunner that by default only tests our own apps

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
from django_coverage.coverage_runner import CoverageRunner


class OurTestRunner(DjangoTestSuiteRunner):
    def build_suite(self, test_labels, *args, **kwargs):
        return super(OurTestRunner, self).build_suite(test_labels or settings.PROJECT_APPS, *args, **kwargs)


class OurCoverageRunner(OurTestRunner, CoverageRunner):
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.conf.urls.static import static
from django.views.generic.base import TemplateView, RedirectView


from django.contrib import admin
admin.autodiscover()

from homepage.views import homepage, error_404_view, error_500_view, py3_compat
from package.views import category

urlpatterns = patterns("",

    url(r'^login/\{\{item\.absolute_url\}\}/', RedirectView.as_view(url="/login/github/")),
    url('', include('social_auth.urls')),
    url(r"^$", homepage, name="home"),
    url(r"^404$", error_404_view, name="404"),
    url(r"^500$", error_500_view, name="500"),
    url(settings.ADMIN_URL_BASE, include(admin.site.urls)),
    url(r"^profiles/", include("profiles.urls")),
    url(r"^packages/", include("package.urls")),
    url(r"^grids/", include("grid.urls")),
    url(r"^feeds/", include("feeds.urls")),

    url(r"^categories/(?P<slug>[-\w]+)/$", category, name="category"),
    url(r"^categories/$", homepage, name="categories"),
    url(r"^python3/$", py3_compat, name="py3_compat"),

    url(regex=r'^login/$', view=TemplateView.as_view(template_name='pages/login.html'), name='login',),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, 'logout',),

    # static pages
    url(r"^about/$", TemplateView.as_view(template_name='pages/faq.html'), name="about"),
    url(r"^terms/$", TemplateView.as_view(template_name='pages/terms.html'), name="terms"),
    url(r"^faq/$", TemplateView.as_view(template_name='pages/faq.html'), name="faq"),
    url(r"^syndication/$", TemplateView.as_view(template_name='pages/syndication.html'), name="syndication"),
    url(r"^contribute/$", TemplateView.as_view(template_name='pages/contribute.html'), name="contribute"),
    url(r"^help/$", TemplateView.as_view(template_name='pages/help.html'), name="help"),

    # new apps
    url(r"^search/", include("searchv2.urls")),

    # apiv2
    url(r'^api/v2/', include('core.apiv2', namespace="apiv2")),

    # apiv3
    url(r'^api/v3/', include('apiv3.urls', namespace="apiv3")),
)

from apiv1.api import Api
from apiv1.resources import (
                    GotwResource, DpotwResource,
                    PackageResource, CategoryResource,
                    GridResource, UserResource
                    )

v1_api = Api()
v1_api.register(PackageResource())
v1_api.register(CategoryResource())
v1_api.register(GridResource())
v1_api.register(GotwResource())
v1_api.register(DpotwResource())
v1_api.register(UserResource())

urlpatterns += patterns('',
    url(r"^api/", include(v1_api.urls)),
)


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


########NEW FILE########
__FILENAME__ = worker
import os

import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for Open Comparison project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


########NEW FILE########
