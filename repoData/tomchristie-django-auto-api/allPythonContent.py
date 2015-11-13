__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from autoapi import views


def get_format_urlpatterns(urlpatterns):
    """
    Supplement existing urlpatterns with corrosponding patterns that also
    include a '.format' suffix.  Retains urlpattern ordering.
    """
    ret = []
    for urlpattern in urlpatterns:
        # Form our complementing '.format' urlpattern
        regex = urlpattern.regex.pattern.rstrip('$') + '.(?P<format>[a-z]+)$'
        view = urlpattern._callback or urlpattern._callback_str
        kwargs = urlpattern.default_args
        name = urlpattern.name
        # Add in both the existing and the new urlpattern
        ret.append(urlpattern)
        ret.append(url(regex, view, kwargs, name))
    return ret


urlpatterns = patterns('',
    url(regex=r'^$',
        view=views.root),
    url(regex=r'^(?P<app_name>[a-z]+)\.(?P<model>[a-z]+)$',
        view=views.list,
        name='list'),
    url(regex=r'^(?P<app_name>[a-z]+)\.(?P<model>[a-z]+)/(?P<pk>\d+)$',
        view=views.instance,
        name='instance'),
)

urlpatterns = get_format_urlpatterns(urlpatterns)

########NEW FILE########
__FILENAME__ = views
from django.db.models import get_model, get_models
from django.http import HttpResponse
from django.core.urlresolvers import reverse as _reverse
from serializers import ModelSerializer, Field, RelatedField


mime_types = {
    'json': 'application/json',
    'xml': 'application/xml',
    'yaml': 'application/yaml',
    'csv': 'text/csv',
    'html': 'text/html'
}


def reverse(viewname, kwargs=None, request=None, format=None):
    """
    Like the regular 'reverse' function, but returns fully qualified urls,
    and takes an additional 'format' argument.
    """
    if format:
        kwargs['format'] = format
    url = _reverse(viewname, kwargs=kwargs)
    return request.build_absolute_uri(url)


def url_for_object(obj, request, format):
    """
    Return the canonical URL for a given model instance.
    Use the request to form an absolute URL, rather than a relative one,
    and use a format suffix (eg '.json') if one is provided.
    """
    app_name = obj._meta.app_label
    model_name = obj._meta.object_name.lower()
    kwargs = {'app_name': app_name, 'model': model_name, 'pk': obj.pk}
    return reverse('autoapi:instance', kwargs=kwargs,
                   request=request, format=format)


def get_api_root(request, format):
    """
    Return a dict of `model label` -> `url`.
    """
    ret = {}
    for model in get_models():
        app_name = model._meta.app_label
        model_name = model._meta.object_name.lower()
        kwargs = {'app_name': app_name, 'model': model_name}
        url = reverse('autoapi:list', kwargs=kwargs,
                      request=request, format=format)
        ret[app_name + '.' + model_name] = url
    return ret


class URLField(Field):
    def field_to_native(self, obj, field_name):
        request = self.context['request']
        format = self.context['format']
        return url_for_object(obj, request, format)


class URLRelatedField(RelatedField):
    def to_native(self, obj):
        request = self.context['request']
        format = self.context['format']
        return url_for_object(obj, request, format)


class APISerializer(ModelSerializer):
    url = URLField()

    class Meta:
        exclude = ('pk', 'id', 'password')

    def get_related_field(self, model_field):
        return URLRelatedField()


def root(request, format=None):
    root = get_api_root(request, format)
    format = format or 'html'
    content = APISerializer().serialize(format, root)
    return HttpResponse(content, mime_types[format])


def list(request, app_name, model, format=None):
    queryset = get_model(app_name, model)._default_manager.all()
    context = {'request': request, 'format': format}
    format = format or 'html'
    content = APISerializer().serialize(format, queryset, context)
    return HttpResponse(content, mime_types[format])


def instance(request, app_name, model, pk, format=None):
    instance = get_model(app_name, model)._default_manager.get(pk=pk)
    context = {'request': request, 'format': format}
    format = format or 'html'
    content = APISerializer().serialize(format, instance, context)
    return HttpResponse(content, mime_types[format])

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = testsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        #'NAME': ':memory:',
        'NAME': 'sqlite3.db'
    },
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
)

ROOT_URLCONF = 'testurls'
DEBUG = True

########NEW FILE########
__FILENAME__ = testurls
from django.conf.urls.defaults import patterns, url, include

urlpatterns = patterns('',
    url(r'^', include('autoapi.urls', namespace='autoapi')),
)

########NEW FILE########
