__FILENAME__ = models
# This module intentionally left blank. Only here for testing.

########NEW FILE########
__FILENAME__ = sites
from django.contrib.admin.sites import AdminSite
from django.utils.text import capfirst


class AdminPlusMixin(object):
    """Mixin for AdminSite to allow registering custom admin views."""

    index_template = 'adminplus/index.html'  # That was easy.

    def __init__(self, *args, **kwargs):
        self.custom_views = []
        return super(AdminPlusMixin, self).__init__(*args, **kwargs)

    def register_view(self, path, name=None, urlname=None, visible=True,
                      view=None):
        """Add a custom admin view. Can be used as a function or a decorator.

        * `path` is the path in the admin where the view will live, e.g.
            http://example.com/admin/somepath
        * `name` is an optional pretty name for the list of custom views. If
            empty, we'll guess based on view.__name__.
        * `urlname` is an optional parameter to be able to call the view with a
            redirect() or reverse()
        * `visible` is a boolean to set if the custom view should be visible in
            the admin dashboard or not.
        * `view` is any view function you can imagine.
        """
        if view is not None:
            self.custom_views.append((path, view, name, urlname, visible))
            return

        def decorator(fn):
            self.custom_views.append((path, fn, name, urlname, visible))
            return fn
        return decorator

    def get_urls(self):
        """Add our custom views to the admin urlconf."""
        urls = super(AdminPlusMixin, self).get_urls()
        from django.conf.urls import patterns, url
        for path, view, name, urlname, visible in self.custom_views:
            urls = patterns(
                '',
                url(r'^%s$' % path, self.admin_view(view), name=urlname),
            ) + urls
        return urls

    def index(self, request, extra_context=None):
        """Make sure our list of custom views is on the index page."""
        if not extra_context:
            extra_context = {}
        custom_list = []
        for path, view, name, urlname, visible in self.custom_views:
            if visible is True:
                if name:
                    custom_list.append((path, name))
                else:
                    custom_list.append((path, capfirst(view.__name__)))

        # Sort views alphabetically.
        custom_list.sort(key=lambda x: x[1])
        extra_context.update({
            'custom_list': custom_list
        })
        return super(AdminPlusMixin, self).index(request, extra_context)


class AdminSitePlus(AdminPlusMixin, AdminSite):
    """A Django AdminSite with the AdminPlusMixin to allow registering custom
    views not connected to models."""

########NEW FILE########
__FILENAME__ = tests
from django.template.loader import render_to_string
from django.test import TestCase

from adminplus.sites import AdminSitePlus


class AdminPlusTests(TestCase):
    def test_decorator(self):
        """register_view works as a decorator."""
        site = AdminSitePlus()

        @site.register_view(r'foo/bar')
        def foo_bar(request):
            return 'foo-bar'

        urls = site.get_urls()
        assert any(u.resolve('foo/bar') for u in urls)

    def test_function(self):
        """register_view works as a function."""
        site = AdminSitePlus()

        def foo(request):
            return 'foo'
        site.register_view('foo', view=foo)

        urls = site.get_urls()
        assert any(u.resolve('foo') for u in urls)

    def test_path(self):
        """Setting the path works correctly."""
        site = AdminSitePlus()

        def foo(request):
            return 'foo'
        site.register_view('foo', view=foo)
        site.register_view('bar/baz', view=foo)
        site.register_view('baz-qux', view=foo)

        urls = site.get_urls()

        foo_urls = [u for u in urls if u.resolve('foo')]
        self.assertEqual(1, len(foo_urls))
        bar_urls = [u for u in urls if u.resolve('bar/baz')]
        self.assertEqual(1, len(bar_urls))
        qux_urls = [u for u in urls if u.resolve('baz-qux')]
        self.assertEqual(1, len(qux_urls))

    def test_urlname(self):
        """Set URL pattern names correctly."""
        site = AdminSitePlus()

        @site.register_view('foo', urlname='foo')
        def foo(request):
            return 'foo'

        @site.register_view('bar')
        def bar(request):
            return 'bar'

        urls = site.get_urls()
        foo_urls = [u for u in urls if u.resolve('foo')]
        self.assertEqual(1, len(foo_urls))
        self.assertEqual('foo', foo_urls[0].name)

        bar_urls = [u for u in urls if u.resolve('bar')]
        self.assertEqual(1, len(bar_urls))
        assert bar_urls[0].name is None

    def test_base_template(self):
        """Make sure extending the base template works everywhere."""
        result = render_to_string('adminplus/test/index.html')
        assert 'Ohai' in result

########NEW FILE########
__FILENAME__ = test_settings
INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.auth',
    'django.contrib.admin',
    'adminplus',
)

SECRET_KEY = 'adminplus'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    },
}

ROOT_URLCONF = 'test_urlconf'

########NEW FILE########
__FILENAME__ = test_urlconf
from django.conf.urls import patterns, url, include
from django.contrib import admin

from adminplus.sites import AdminSitePlus


admin.site = AdminSitePlus()
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
