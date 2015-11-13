__FILENAME__ = base_settings
ALLOWED_HOSTS = ['*']

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    },
}

SECRET_KEY = "NOT REALLY SECRET"

########NEW FILE########
__FILENAME__ = benchmark
from django.test.client import Client, FakePayload
from django.conf import global_settings
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.wsgi import WSGIHandler

from djangobench.utils import run_comparison_benchmark


class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.
    
    Usage:
    
    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})
    
    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client
    
    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.
    
    Author: Simon (http://djangosnippets.org/users/simon/)
    djangosnippet URL: (http://djangosnippets.org/snippets/963/)
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies.output(header='', sep='; '),
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': FakePayload(''),
        }
        environ.update(self.defaults)
        environ.update(request)

        return WSGIRequest(environ)


def setup():
    global req_factory, handler_default_middleware, handler_no_middleware
    req_factory = RequestFactory()
    
    settings.MIDDLEWARE_CLASSES = global_settings.MIDDLEWARE_CLASSES
    handler_default_middleware = WSGIHandler()
    handler_default_middleware.load_middleware()
    
    settings.MIDDLEWARE_CLASSES = []
    handler_no_middleware = WSGIHandler()
    handler_no_middleware.load_middleware()


def benchmark_request(middleware_classes):
    settings.MIDDLEWARE_CLASSES = middleware_classes
    req_factory = RequestFactory()
    handler = WSGIHandler()
    handler.load_middleware()
    handler.get_response(req_factory.get('/'))


def benchmark_default_middleware():
    global req_factory, handler_default_middleware
    handler_default_middleware.get_response(req_factory.get('/'))


def benchmark_no_middleware():
    global req_factory, handler_no_middleware
    handler_no_middleware.get_response(req_factory.get('/'))


run_comparison_benchmark(
    benchmark_default_middleware,
    benchmark_no_middleware, 
    setup=setup,
    syncdb=False,
    meta={
        'description': 'Request/response overhead added by the default middleware.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['default_middleware']
ROOT_URLCONF = 'default_middleware.urls'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns
except ImportError:
    from django.conf.urls.defaults import patterns


urlpatterns = patterns('default_middleware',
    (r'^.*$', 'views.index'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

def index(request):
    return HttpResponse('Hello World!')

########NEW FILE########
__FILENAME__ = benchmark
from django import forms
from djangobench.utils import run_benchmark


class BookForm(forms.Form):
    title = forms.CharField(max_length=100)

form = None


def setup():
    # Can't initialize a form during import as __init__ uses
    # ugettext
    global form
    form = BookForm({'title': 'hi'})


def benchmark():
    form.full_clean()

run_benchmark(
    benchmark,
    syncdb=False,
    meta={
        'description': 'Speed of a Form.clean call.',
    },
    setup=setup
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *
########NEW FILE########
__FILENAME__ = benchmark
from django import forms
from djangobench.utils import run_benchmark

class BookForm(forms.Form):
    title = forms.CharField(max_length=100)

def benchmark():
    BookForm({'title': 'a'})

run_benchmark(
    benchmark,
    syncdb = False,
    meta = {
        'description': 'Time required to instantiate and bind a form.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *
########NEW FILE########
__FILENAME__ = benchmark
import os
import sys

from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render_to_response
from django.template  import RequestContext
from django.test.client import Client

from djangobench.utils import run_benchmark


def make_request():
    environ = {
        'PATH_INFO': '/',
        'QUERY_STRING': '',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': 80,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        "wsgi.input": sys.stdin
        }

    return WSGIRequest(environ)


req_object = make_request()


def benchmark():
    render_to_response('list.html',
                       {'numbers': range(0, 200)},
                       context_instance=RequestContext(req_object))


run_benchmark(
    benchmark,
    syncdb = False,
    meta = {
        'description': 'Render a l10n intensive template.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = settings
import os

from djangobench.base_settings import *

USE_I18N = False
USE_L10N = True
TEMPLATE_DIRS = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
)
INSTALLED_APPS = ['l10n_render']

########NEW FILE########
__FILENAME__ = benchmark
from django.test import RequestFactory
from django.utils.translation import get_language_from_request

from djangobench.utils import run_benchmark


LANGUAGES = (
    # no language preference
    '',
    # a few known languages
    'af', 'ar', 'az', 'bg', 'be', 'bn', 'br', 'bs', 'ca', 'cs', 'cy', 'da',
    'en', 'en-gb',
    # a few generic languages (fr-fr -> fr)
    'fr-fr',
    'fy-nl',
    'nl-nl',
    'en-us',
    # one non-strict language (zh -> zh-?)
    'zh',
    # multiple preferences
    'en-us,en', 'nl-be,nl'
    # some invalid
    'INVALID', 'UNKNOWN', 'NONE', 'KLINGON',
)


def benchmark():
    for lang in LANGUAGES:
        request.META = {'HTTP_ACCEPT_LANGUAGE': lang}
        get_language_from_request(request)


def setup():
    global request
    rf = RequestFactory()
    request = rf.get('/')
    request.COOKIES = {}


run_benchmark(
    benchmark,
    setup=setup,
    meta={
        'description': 'Raw speed of locale detecting',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

ROOT_URLCONF = None

########NEW FILE########
__FILENAME__ = benchmark
import time
from djangobench.utils import run_benchmark
from model_creation.models import Book

def benchmark():
    Book.objects.create(title='hi!')

run_benchmark(
    benchmark, 
    meta = {
        'description': 'Time of a Model.objects.create() call.',
    }
)
########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['model_creation']

########NEW FILE########
__FILENAME__ = benchmark
import time
from djangobench.utils import run_benchmark
from model_delete.models import Book

def benchmark():
    b = Book.objects.create(title='hi')
    start = time.time()
    b.delete()
    return time.time() - start

run_benchmark(
    benchmark,
    meta = {
        'description': 'Delete an object via Model.delete().',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['model_delete']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from model_save_existing.models import Book

def benchmark():
    b = Book.objects.get(id=1)
    for i in range(0, 30):
        b.save()

run_benchmark(
    benchmark,
    meta={
        'description': 'A simple Model.save() call, instance exists in DB.',
    },
    setup=lambda: Book.objects.create(id=1, title='Foo')
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['model_save_existing']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from model_save_new.models import Book

def benchmark():
    for i in range(0, 30):
        b = Book(id=i, title='Foo')
        b.save()

run_benchmark(
    benchmark,
    meta={
        'description': 'A simple Model.save() call, instance not in DB.',
    },
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['model_save_new']

########NEW FILE########
__FILENAME__ = benchmark
from time import time
import copy

from django.utils.datastructures import MultiValueDict

from djangobench.utils import run_comparison_benchmark

case = {'a': ['a'], 'b': ['a','b'], 'c':['a','b','c']}
update = {'a': ['a'], 'b': ['a','b'], 'c':['a','b','c']}

def benchmark_multi():
    # Instantiate a new MultiValueDict and call key method (i.e. that do
    # something diff than dict)
    caseDict = MultiValueDict(case)

    caseDict['a']
    caseDict['b']
    caseDict['c']
    
    caseDict.update(update)
    copy.copy(caseDict)
    copy.deepcopy(caseDict)
    
    caseDict.items()
    caseDict.lists()
    for i in caseDict:
        i

    caseDict['a'] = 'A'
    caseDict['b'] = 'B'
    caseDict['c'] = 'C'

def benchmark_dict():
    # Instantiate a new dict and call same methods as above - to be fair,
    # get unlistify in this method where required
    caseDict = dict(case)
    
    caseDict['a'][0]
    caseDict['b'][1]
    caseDict['c'][2]
    
    caseDict.items()
    caseDict.values()
    for i in caseDict:
        i
    
    caseDict.update(update)
    copy.copy(caseDict)
    copy.deepcopy(caseDict)
    
    caseDict['a'] = ['A']
    caseDict['b'] = ['B']
    caseDict['c'] = ['C']

run_comparison_benchmark(
    benchmark_multi,
    benchmark_dict,
    syncdb = False,
    meta = {
        'description': 'Overhead of a MultiValueDict compared to a builtin dict.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *
########NEW FILE########
__FILENAME__ = benchmark
import datetime
import time
from djangobench.utils import run_benchmark
from qs_filter_chaining.models import Book

def benchmark():
    Book.objects.filter(title='Talent')\
                .filter(description__icontains='top performers')\
                .filter(author_name__startswith='Geoff')\
                .filter(date_created__lt=datetime.datetime(year=2010, month=1, day=1))\
                .filter(date_created__gte=datetime.date(year=2007, month=1, day=1))\
                .filter(date_published=datetime.datetime.now())\
                .filter(enabled=True)

run_benchmark(
    benchmark,
    meta = {
        'description': 'Filter (but do not execute) a queryset mutliple times.',
    }
)
########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    author_name = models.TextField()
    date_created = models.DateTimeField(default=datetime.datetime.now)
    date_published = models.DateTimeField()
    enabled = models.BooleanField()
########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['qs_filter_chaining']
########NEW FILE########
__FILENAME__ = benchmark
from django.db.models import Count
from djangobench.utils import run_benchmark
from query_aggregate.models import Book

def benchmark():
    Book.objects.all().aggregate(Count('title'))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.aggregate() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_aggregate']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_all.models import Book

def benchmark():
    list(Book.objects.iterator())

def setup():
    for i in range(0, 3000):
        Book(pk=i,title='foobar_%s' % i ).save()

run_benchmark(
    benchmark,
    setup=setup,
    meta = {
        'description': 'A simple Model.objects.iterator() call for large number of objects.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_all']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_all_multifield.models import MultiField

def benchmark():
    list(MultiField.objects.iterator())

def setup():
    for i in range(0, 3000):
        kwargs = {}
        for j in range(1, 11):
            kwargs['field%s' % j] = 'foobar_%s_%s' % (i, j)
        MultiField(**kwargs).save()

run_benchmark(
    benchmark,
    setup=setup,
    meta = {
        'description': 'A simple Model.objects.iterator() call for large number of objects and large number of fields.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class MultiField(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.CharField(max_length=100)
    field9 = models.CharField(max_length=100)
    field10 = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_all_multifield']

########NEW FILE########
__FILENAME__ = benchmark
from django.db.models import Count
from djangobench.utils import run_benchmark
from query_annotate.models import Book

def benchmark():
    list(Book.objects.values('title').annotate(books_total=Count('id')))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.annotate() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_annotate']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_complex_filter.models import Book

def benchmark():
    Book.objects.complex_filter({'pk': 1})

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.complex_filter() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_complex_filter']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_count.models import Book

def benchmark():
    Book.objects.count()

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.count() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_count']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_dates.models import Book

def benchmark():
    list(Book.objects.dates("created_date", "year", "ASC"))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.dates() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models
import datetime

class Book(models.Model):
    title = models.CharField(max_length=100)
    created_date = models.DateTimeField(default=datetime.datetime.now())

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_dates']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_delete.models import Book

def benchmark():
    Book.objects.all().delete()

run_benchmark(
    benchmark,
    meta={
        'description': 'Delete an object via QuerySet.delete().',
    },
    setup=lambda: [Book.objects.create(title='hi') for i in range(0, 10)]
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_delete']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_delete_related.models import Book, Chapter

def benchmark():
    Book.objects.all().delete()

def setup():
    b1 = Book.objects.create(title='hi')
    b2 = Book.objects.create(title='hi')
    b3 = Book.objects.create(title='hi')
    for i in range(0, 5):
        Chapter.objects.create(book=b1, title='chapter%d' % i)
        Chapter.objects.create(book=b2, title='chapter%d' % i)
        Chapter.objects.create(book=b3, title='chapter%d' % i)

run_benchmark(
    benchmark,
    meta={
        'description': 'Delete an object via QuerySet.delete(), '
                       'objects deleted have related objects.',
    },
    setup=setup
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

class Chapter(models.Model):
    book = models.ForeignKey(Book)
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_delete_related']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_distinct.models import Book

def benchmark():
    list(Book.objects.distinct())

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.distinct() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_distinct']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_exclude.models import Book

def benchmark():
    list(Book.objects.exclude(id=1))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.exclude() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_exclude']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_exists.models import Book


def benchmark():
    #Checking for object that exists
    Book.objects.filter(id=1).exists()

    #Checking for object that does not exist
    Book.objects.filter(id=11).exists()

if hasattr(Book.objects, 'exists'):
    run_benchmark(
        benchmark,
        meta={
            'description': 'A Model.objects.exists() call for both existing and non-existing objects.'
        }
    )
else:
    print("SKIP: Django before 1.2 doesn't have QuerySet.exists()")

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_exists']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_filter.models import Book

def benchmark():
    list(Book.objects.filter(id=1))

run_benchmark(
    benchmark, 
    meta = {
        'description': 'A simple Model.objects.filter() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_filter']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_get.models import Book

def benchmark():
    for i in range(0, 30):
        # This will succeed
        Book.objects.get(id=1)
        try:
            # This will fail, due to too many objects
            Book.objects.get()
        except:
            pass

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.get() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_get']

########NEW FILE########
__FILENAME__ = benchmark
import itertools
from djangobench.utils import run_benchmark
from query_get_or_create.models import Book

counter = itertools.count(1)


def benchmark():
    nextid = next(counter)

    # This will do a create ...
    Book.objects.get_or_create(id=nextid, defaults={'title': 'hi'})
    
    # ... and this a get.
    Book.objects.get_or_create(id=nextid, defaults={'title': 'hi'})

run_benchmark(
    benchmark,
    meta={
        'description': 'A Model.objects.get_or_create() call, both for '
                       'existing and non-existing objects.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_get_or_create']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_in_bulk.models import Book

def benchmark():
    Book.objects.in_bulk([1]) 

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.in_bulk() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_in_bulk']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_iterator.models import Book

def benchmark():
    list(Book.objects.iterator())

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.iterator() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_iterator']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_latest.models import Book

def benchmark():
    Book.objects.latest()

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.latest() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

    class Meta:
        get_latest_by = 'pk'

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_latest']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_none.models import Book

def benchmark():
    list(Book.objects.none())

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.none() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_none']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_order_by.models import Book

def benchmark():
    list(Book.objects.order_by('id'))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.order_by() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_order_by']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from django import VERSION
from query_prefetch_related.models import Book, Author


def benchmark():
    for i in range(10):
        for a in Author.objects.prefetch_related('books'):
            list(a.books.all())


def setup():
    for i in range(0, 20):
        a = Author.objects.create(author="Author %s" % i)
        bset = set()
        for j in range(0, 3):
            b = Book.objects.create(title="Title %s" % j)
            bset.add(b)
        a.books = bset

if VERSION < (1, 4):
    print("SKIP: prefetch_related not supported before Django 1.4")
else:
    run_benchmark(
        benchmark,
        setup=setup,
        meta={
            'description': 'A simple Model.objects.select_related() call.',
        }
    )

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

class Author(models.Model):
    author = models.CharField(max_length=100)
    books = models.ManyToManyField(Book)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_prefetch_related']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_raw.models import MultiField

def benchmark():
    list(MultiField.objects.raw('select * from query_raw_multifield'))

def setup():
    for i in range(0, 1000):
        kwargs = {}
        for j in range(1, 11):
            kwargs['field%s' % j] = 'foobar_%s_%s' % (i, j)
        MultiField(**kwargs).save() 

run_benchmark(
    benchmark,
    setup=setup,
    meta = {
        'description': 'A test for fetching large number of objects by Model.objects.all()',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class MultiField(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.CharField(max_length=100)
    field9 = models.CharField(max_length=100)
    field10 = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_raw']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_raw_deferred.models import MultiField

def benchmark():
    list(MultiField.objects.raw('select id from query_raw_deferred_multifield'))

def setup():
    for i in range(0, 1000):
        kwargs = {}
        for j in range(1, 11):
            kwargs['field%s' % j] = 'foobar_%s_%s' % (i, j)
        MultiField(**kwargs).save() 

run_benchmark(
    benchmark,
    setup=setup,
    meta = {
        'description': 'A test for fetching large number of objects by Model.objects.all() with deferred fields.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class MultiField(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.CharField(max_length=100)
    field9 = models.CharField(max_length=100)
    field10 = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_raw_deferred']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_select_related.models import Book


def benchmark():
    for i in range(20):
        list(Book.objects.select_related('author'))

run_benchmark(
    benchmark,
    meta={
        'description': 'A simple Model.objects.select_related() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey('Author')

class Author(models.Model):
    author = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_select_related']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_update.models import Book

def benchmark():
    Book.objects.all().update(title='z')

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple QuerySet.update().',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_update']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_values.models import Book

def benchmark():
    list(Book.objects.values('title'))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.values() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_values']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from query_values_list.models import Book

def benchmark():
    list(Book.objects.values_list('title'))

run_benchmark(
    benchmark,
    meta = {
        'description': 'A simple Model.objects.values_list() call.',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['query_values_list']

########NEW FILE########
__FILENAME__ = benchmark
from djangobench.utils import run_benchmark
from raw_sql.models import OneField
from django.db import connection

def benchmark():
    cursor = connection.cursor()
    cursor.execute("select field1 from raw_sql_onefield")
    list(cursor.fetchall())

def setup():
    for i in range(0, 10):
        OneField(field1=i).save()

run_benchmark(
    benchmark,
    setup=setup,
    meta={
        'description': 'A test for stressing direct SQL performance',
    }
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class OneField(models.Model):
    field1 = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['raw_sql']

########NEW FILE########
__FILENAME__ = benchmark
# XXX FIXME - has to spawn a new process to measure load time

from djangobench.utils import run_benchmark

def benchmark():
    # Make sure the models and settings are loaded, then we're done. Calling
    # get_models() will make sure settings get loaded.
    from django.db import models
    models.get_models()

run_benchmark(
    benchmark,
    syncdb = False,
    trials = 1,
    meta = {
        'description': 'Startup time for a simple app.',
    }
)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['startup']

########NEW FILE########
__FILENAME__ = benchmark
from django.template import Template
from djangobench.utils import run_benchmark

def benchmark():
    # Just compile the template, no rendering
    t = Template("""
        {% for v in vals %}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
            {{ v }}
        {% endfor %}
    """)

run_benchmark(
    benchmark,
    syncdb = False,
    meta = {
        'description': 'Template compilation time.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *
########NEW FILE########
__FILENAME__ = benchmark
from django import VERSION
from django.shortcuts import render_to_response
from djangobench.utils import run_benchmark

#set up some vars
objects1 = [object(), object(), object(), object(), object()]
objects2 = [object(), object(), object(), object(), object()]
object1 = object()
object2 = object()
object3 = None
num1 = 1
num2 = 2
boolean1 = True
SCRIPT_CONTENT_URL = '/some/prefix'
WEBSITE_DOMAIN = 'http://www.somedomain.com'
SHOW_ALT_HEADER = 'True'

def benchmark_django_lte_13():
    context = {
        'objects1': objects1,
        'objects2': objects2,
        'object1': object1,
        'object2': object2,
        'object3': object3,
        'num1' : num1,
        'num2' : num2,
        'boolean1': boolean1,
        'SCRIPT_CONTENT_URL': SCRIPT_CONTENT_URL,
        'WEBSITE_DOMAIN': WEBSITE_DOMAIN,
        'SHOW_ALT_HEADER': SHOW_ALT_HEADER
    }
    render_to_response('permalink_django_lte_13.html', context)

def benchmark_django_gt_13():
    context = {
        'objects1': objects1,
        'objects2': objects2,
        'object1': object1,
        'object2': object2,
        'object3': object3,
        'num1' : num1,
        'num2' : num2,
        'boolean1': boolean1,
        'SCRIPT_CONTENT_URL': SCRIPT_CONTENT_URL,
        'WEBSITE_DOMAIN': WEBSITE_DOMAIN,
        'SHOW_ALT_HEADER': SHOW_ALT_HEADER
    }
    render_to_response('permalink.html', context)

run_benchmark(
    benchmark_django_gt_13 if VERSION > (1, 3) else benchmark_django_lte_13,
    syncdb=False,
    meta={
        'description': ('Render a somewhat complex, fairly typical template '
                        '(including inheritance, reverse URL resolution, etc.).'),
    }
)

########NEW FILE########
__FILENAME__ = settings
import os

from djangobench.base_settings import *

INSTALLED_APPS = ['template_render']
TEMPLATE_DIRS = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
)
ROOT_URLCONF = 'template_render.urls'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('template_render.views',
    url(r'/join/?$', 'join', name='join'),
    url(r'/login/?$', 'login', name='login'),
    url(r'/logout/?$', 'logout', name='logout'),
)

########NEW FILE########
__FILENAME__ = views
#some dummy classes for the url reverse
def join(request):
    pass

def login(request):
    pass

def logout(request):
    pass

########NEW FILE########
__FILENAME__ = benchmark
import os
from django import template
from djangobench.utils import run_benchmark

def benchmark():
    context = template.Context({
        'stuff': 'something'
    });
    t = template.Template('{{ stuff }}')
    t.render(context)

run_benchmark(
    benchmark,
    syncdb = False,
    meta = {
        'description': 'Render an extremely simple template (from string)',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

########NEW FILE########
__FILENAME__ = benchmark
from django.core.urlresolvers import resolve
from djangobench.utils import run_benchmark

def benchmark():
    for i in range(0, 100):
        resolve('/basic/')
        resolve('/fallthroughview/')
        resolve('/replace/1')

run_benchmark(
    benchmark,
    meta = {
        'description': 'URL resolution.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['url_resolve']
ROOT_URLCONF = 'url_resolve.urls'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns
except ImportError:
    from django.conf.urls.defaults import patterns

def generate_filler_patterns(num=1):
    """ Returns a list of url pattern inputs for garbage views """
    for n in range(num):
        yield (r''.join((r'^', r'x'*3*n, r'/$')), str(n))

patterns_input = ['']
patterns_input += generate_filler_patterns(10)
patterns_input.append((r'^basic/$', 'url_resolve.views.basic'))
patterns_input.append((r'^[a-z]*/$', 'url_resolve.views.catchall'))
patterns_input.append((r'^replace/(?P<var>.*?)', 'url_resolve.views.vars'))

urlpatterns = patterns(*patterns_input)

########NEW FILE########
__FILENAME__ = views
﻿def basic():
    pass

def catchall():
    pass
    
def vars(var=None):
    pass

########NEW FILE########
__FILENAME__ = benchmark
from django.core.urlresolvers import resolve
from djangobench.utils import run_benchmark

def benchmark():
    for i in range(0, 100):
        for path in (
          '/user/repo/feature19',
          '/section0/feature0',
          '/en/feature10',
          '/ru/feature10',
          '/missing'):
            try:
                resolve(path)
            except:
                pass
run_benchmark(
    benchmark,
    meta = {
        'description': 'URL resolution with long-flat list of patterns.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['url_resolve_flat']
ROOT_URLCONF = 'url_resolve_flat.urls'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

def ok_view(request, *a, **kw):
    pass

def handler404(request):
    pass

sections = ["section%d" % i for i in range(10)]
features = ["feature%d" % i for i in range(20)]

urlpatterns = patterns('', *[
    url("^%s/%s$" % (s, f), ok_view) for s in sections for f in features
])

urlpatterns += patterns('', *[
    url("^(?P<locale>en|ru)/%s$" % f, ok_view)
        for f in features
])

urlpatterns += patterns('', *[
    url("^(?P<user>\w+)/(?P<repo>\w+)/%s$" % f, ok_view) for f in features
])

# Total: 240 patterns

########NEW FILE########
__FILENAME__ = benchmark
from django.core.urlresolvers import resolve
from djangobench.utils import run_benchmark

def benchmark():
    for i in range(0, 100):
        for path in (
          '/user/repo/feature19',
          '/section0/feature0',
          '/en/feature10',
          '/ru/feature10',
          '/missing'):
            try:
                resolve(path)
            except:
                pass
run_benchmark(
    benchmark,
    meta = {
        'description': 'URL resolution with long-flat list of patterns. With USE_I18N=False.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['url_resolve_flat_i18n_off']
ROOT_URLCONF = 'url_resolve_flat_i18n_off.urls'
USE_I18N = False

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

def ok_view(request, *a, **kw):
    pass

def handler404(request):
    pass

sections = ["section%d" % i for i in range(10)]
features = ["feature%d" % i for i in range(20)]

urlpatterns = patterns('', *[
    url("^%s/%s$" % (s, f), ok_view) for s in sections for f in features
])

urlpatterns += patterns('', *[
    url("^(?P<locale>en|ru)/%s$" % f, ok_view)
        for f in features
])

urlpatterns += patterns('', *[
    url("^(?P<user>\w+)/(?P<repo>\w+)/%s$" % f, ok_view) for f in features
])

# Total: 240 patterns

########NEW FILE########
__FILENAME__ = benchmark
from django.core.urlresolvers import resolve, Resolver404
from djangobench.utils import run_benchmark



def benchmark():
    resolve("/0/00/000/0000/00000/000000/0000000/00000000/leaf")

run_benchmark(
    benchmark,
    meta = {
        'description': 'URL resolution with long-flat list of patterns.',
    }
)

########NEW FILE########
__FILENAME__ = settings
from djangobench.base_settings import *

INSTALLED_APPS = ['url_resolve_nested']
ROOT_URLCONF = 'url_resolve_nested.urls'

########NEW FILE########
__FILENAME__ = urls
import string

try:
    from django.conf.urls import include, patterns, url
except ImportError:
    from django.conf.urls.defaults import include, patterns, url


def ok_view(request, *a, **kw):
    pass

def handler500(request):
    pass

leaf_patterns = patterns('', url(r"^leaf$", ok_view))

def int2ascii(x, mod, alphabet=string.digits + string.ascii_letters):
    alphabet = alphabet[:mod]
    result = []
    while x:
        x, rem = divmod(x, mod)
        result.append(alphabet[rem])
    return (''.join(reversed(result))).rjust(1, alphabet[0])

def pattern_tree(parent, height, level):
    if height == 0:
        return leaf_patterns
    ids = [parent + int2ascii(i, level) for i in range(level)]
    return patterns('',
       *(url("^%s/" % id_, include(pattern_tree(id_, height-1, level)))
         for id_ in ids)
    )

urlpatterns = pattern_tree("", 8, 2)
# Total: 2**8 = 256 leafs, 511 nodes

########NEW FILE########
__FILENAME__ = benchmark
﻿from django.core.urlresolvers import reverse
from djangobench.utils import run_benchmark

def benchmark():
    reverse('url_resolve.views.basic')
    reverse('url_resolve.views.catchall')
    reverse('url_resolve.views.vars',args=[1,])
    reverse('url_resolve.views.vars',kwargs={'var':1})

run_benchmark(
    benchmark,
    meta = {
        'description': 'Reverse URL resolution.',
    }
)

########NEW FILE########
__FILENAME__ = settings
﻿from djangobench.base_settings import *

INSTALLED_APPS = ['url_reverse']
ROOT_URLCONF = 'url_resolve.urls'

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

"""
Run us some Django benchmarks.
"""
import logging
import os

import subprocess
import argparse
import email
import simplejson
import sys
from djangobench import perf

__version__ = '0.10'

DEFAULT_BENCHMARK_DIR = os.path.join(os.path.dirname(__file__), 'benchmarks')


def run_benchmarks(control, experiment, benchmark_dir, benchmarks, trials,
                   vcs=None, record_dir=None, profile_dir=None,
                   continue_on_error=False, control_python=sys.executable,
                   experiment_python=sys.executable):
    if benchmarks:
        print("Running benchmarks: %s" % " ".join(benchmarks))
    else:
        print("Running all benchmarks")

    if record_dir:
        record_dir = os.path.abspath(record_dir)
        if not os.path.isdir(record_dir):
            raise ValueError('Recording directory "%s" does not exist' % record_dir)
        print("Recording data to '%s'" % record_dir)
    if profile_dir:
        profile_dir = os.path.abspath(profile_dir)
        if not os.path.isdir(profile_dir):
            raise ValueError('Profile directory "%s" does not exist' % profile_dir)
        print("Recording profile data to '%s'" % profile_dir)

    control_label = get_django_version(control, vcs=vcs)
    experiment_label = get_django_version(experiment, vcs=vcs)
    branch_info = "%s branch " % vcs if vcs else ""
    print("Control: Django %s (in %s%s)" % (control_label, branch_info, control))
    print("Experiment: Django %s (in %s%s)" % (experiment_label, branch_info, experiment))
    print('')

    # Calculate the subshell envs that we'll use to execute the
    # benchmarks in.
    if vcs:
        control_env = {
            'PYTHONPATH': '%s:%s' % (os.path.abspath(os.getcwd()), benchmark_dir),
        }
        experiment_env = control_env.copy()
    else:
        control_env = {'PYTHONPATH': '%s:%s' % (os.path.abspath(control), benchmark_dir)}
        experiment_env = {'PYTHONPATH': '%s:%s' % (os.path.abspath(experiment), benchmark_dir)}

    for benchmark in discover_benchmarks(benchmark_dir):
        if not benchmarks or benchmark in benchmarks:
            print("Running '%s' benchmark ..." % benchmark)
            settings_mod = '%s.settings' % benchmark
            control_env['DJANGO_SETTINGS_MODULE'] = settings_mod
            experiment_env['DJANGO_SETTINGS_MODULE'] = settings_mod
            if profile_dir is not None:
                control_env['DJANGOBENCH_PROFILE_FILE'] = os.path.join(profile_dir, "con-%s" % benchmark)
                experiment_env['DJANGOBENCH_PROFILE_FILE'] = os.path.join(profile_dir, "exp-%s" % benchmark)
            try:
                if vcs:
                    switch_to_branch(vcs, control)
                control_data = run_benchmark(benchmark, benchmark_dir, trials,
                                             executable=control_python,
                                             env=control_env)
                if vcs:
                    switch_to_branch(vcs, experiment)
                experiment_data = run_benchmark(benchmark, benchmark_dir, trials,
                                                executable=experiment_python,
                                                env=experiment_env)
            except SkipBenchmark as reason:
                print("Skipped: %s\n" % reason)
                continue
            except RuntimeError as error:
                if continue_on_error:
                    print("Failed: %s\n" % error)
                    continue
                raise

            options = argparse.Namespace(
                track_memory=False,
                diff_instrumentation=False,
                benchmark_name=benchmark,
                disable_timelines=True,
                control_label=control_label,
                experiment_label=experiment_label,
            )
            result = perf.CompareBenchmarkData(control_data, experiment_data, options)
            if record_dir:
                record_benchmark_results(
                    dest=os.path.join(record_dir, '%s.json' % benchmark),
                    name=benchmark,
                    result=result,
                    control=control_label,
                    experiment=experiment_label,
                    control_data=control_data,
                    experiment_data=experiment_data,
                )
            print(format_benchmark_result(result, len(control_data.runtimes)))
            print('')


def discover_benchmarks(benchmark_dir):
    for app in os.listdir(benchmark_dir):
        if os.path.exists(os.path.join(benchmark_dir, app, 'benchmark.py')) and \
                os.path.exists(os.path.join(benchmark_dir, app, 'settings.py')):
            yield app


def print_benchmarks(benchmark_dir):
    for app in discover_benchmarks(benchmark_dir):
        print(app)


class SkipBenchmark(Exception):
    pass


def run_benchmark(benchmark, benchmark_dir, trials, executable, env):
    """
    Similar to perf.MeasureGeneric, but modified a bit for our purposes.
    """
    # Remove Pycs, then call the command once to prime the pump and
    # re-generate fresh ones. This makes sure we're measuring as little of
    # Python's startup time as possible.
    remove_pycs()
    command = [os.path.expanduser(executable),
               os.path.join(benchmark_dir, benchmark, 'benchmark.py')]
    out, _, _ = perf.CallAndCaptureOutput(command + ['-t', '1'], env, track_memory=False, inherit_env=[])
    if out.startswith('SKIP:'):
        raise SkipBenchmark(out.replace('SKIP:', '').strip())

    # Now do the actual mesurements.
    output = perf.CallAndCaptureOutput(command + ['-t', str(trials)], env, track_memory=False, inherit_env=[])
    stdout, stderr, mem_usage = output
    message = email.message_from_string(stdout)
    data_points = [float(line) for line in message.get_payload().splitlines()]
    return perf.RawData(data_points, mem_usage, inst_output=stderr)


def record_benchmark_results(dest, **kwargs):
    kwargs['version'] = __version__
    simplejson.dump(kwargs, open(dest, 'w'), default=json_encode_custom)


def json_encode_custom(obj):
    if isinstance(obj, perf.RawData):
        return obj.runtimes
    if isinstance(obj, perf.BenchmarkResult):
        return {
            'min_base': obj.min_base,
            'min_changed': obj.min_changed,
            'delta_min': obj.delta_min,
            'avg_base': obj.avg_base,
            'avg_changed': obj.avg_changed,
            'delta_avg': obj.delta_avg,
            't_msg': obj.t_msg,
            'std_base': obj.std_base,
            'std_changed': obj.std_changed,
            'delta_std': obj.delta_std,
        }
    if isinstance(obj, perf.SimpleBenchmarkResult):
        return {
            'base_time': obj.base_time,
            'changed_time': obj.changed_time,
            'time_delta': obj.time_delta,
        }
    raise TypeError("%r is not JSON serializable" % obj)


def supports_color():
    return sys.platform != 'win32' and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


class colorize(object):
    GOOD = INSIGNIFICANT = SIGNIFICANT = BAD = ENDC = ''
    if supports_color():
        GOOD = '\033[92m'
        INSIGNIFICANT = '\033[94m'
        SIGNIFICANT = '\033[93m'
        BAD = '\033[91m'
        ENDC = '\033[0m'

    @classmethod
    def colorize(cls, color, text):
        return "%s%s%s" % (color, text, cls.ENDC)

    @classmethod
    def good(cls, text):
        return cls.colorize(cls.GOOD, text)

    @classmethod
    def significant(cls, text):
        return cls.colorize(cls.SIGNIFICANT, text)

    @classmethod
    def insignificant(cls, text):
        return cls.colorize(cls.INSIGNIFICANT, text)

    @classmethod
    def bad(cls, text):
        return cls.colorize(cls.BAD, text)


def format_benchmark_result(result, num_points):
    if isinstance(result, perf.BenchmarkResult):
        output = ''
        delta_min = result.delta_min
        if 'faster' in delta_min:
            delta_min = colorize.good(delta_min)
        elif 'slower' in result.delta_min:
            delta_min = colorize.bad(delta_min)
        output += "Min: %f -> %f: %s\n" % (result.min_base, result.min_changed, delta_min)

        delta_avg = result.delta_avg
        if 'faster' in delta_avg:
            delta_avg = colorize.good(delta_avg)
        elif 'slower' in delta_avg:
            delta_avg = colorize.bad(delta_avg)
        output += "Avg: %f -> %f: %s\n" % (result.avg_base, result.avg_changed, delta_avg)

        t_msg = result.t_msg
        if 'Not significant' in t_msg:
            t_msg = colorize.insignificant(t_msg)
        elif 'Significant' in result.t_msg:
            t_msg = colorize.significant(t_msg)
        output += t_msg

        delta_std = result.delta_std
        if 'larger' in delta_std:
            delta_std = colorize.bad(delta_std)
        elif 'smaller' in delta_std:
            delta_std = colorize.good(delta_std)
        output += "Stddev: %.5f -> %.5f: %s" %(result.std_base, result.std_changed, delta_std)
        output += " (N = %s)" % num_points
        output += result.get_timeline()
        return output
    else:
        return str(result)


def get_django_version(loc, vcs=None):
    if vcs:
        switch_to_branch(vcs, loc, do_cleanup=True)
        pythonpath = os.getcwd()
    else:
        pythonpath = os.path.abspath(loc)
    out, err, _ = perf.CallAndCaptureOutput(
        [sys.executable, '-c' 'import django; print(django.get_version())'],
        env={'PYTHONPATH': pythonpath}
    )
    return out.strip()


def switch_to_branch(vcs, branchname, do_cleanup=False):
    if vcs == 'git':
        cmd = ['git', 'checkout', branchname]
    elif vcs == 'hg':
        cmd = ['hg', 'update', '-C', branchname]
    else:
        raise ValueError("Sorry, %s isn't supported (yet?)" % vcs)
    if do_cleanup:
        remove_pycs(vcs=vcs)
    subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def remove_pycs(vcs=None):
    if vcs == 'git':
        cmd = ['git', 'clean', '-fdX']
        subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        perf.RemovePycs()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--control',
        metavar='BRANCH',
        default='django-control',
        help="Django version to use as control. If --vcs git refers to a git"
             "branch name or commit-id. If --vcs none refers to a path."
    )
    parser.add_argument(
        '--experiment',
        metavar='BRANCH',
        default='django-experiment',
        help="Django version to use as experiment. If --vcs git refers to a git"
             "branch name or commit-id. If --vcs none refers to a path."
    )
    parser.add_argument(
        '--control-python',
        metavar='PATH',
        default=sys.executable,
        help="Python executable to use as control. Can be used to test Python "
             "2 vs 3 performance on the benchmarks."
    )
    parser.add_argument(
        '--experiment-python',
        metavar='PATH',
        default=sys.executable,
        help="Python executable to use as experiment. Can be used to test "
             "Python 2 vs 3 performance on the benchmarks."
    )
    parser.add_argument(
        '--vcs',
        choices=['git', 'hg', 'none'],
        default='git',
        help='Specify which VCS to use for control/experiment. Set to none to '
             'specify paths, not branch or commit-id\'s.'
    )
    parser.add_argument(
        '-t', '--trials',
        type=int,
        default=50,
        help='Number of times to run each benchmark.'
    )
    parser.add_argument(
        '-r', '--record',
        default=None,
        metavar='PATH',
        help='Directory to record detailed output as a series of JSON files.',
    )
    parser.add_argument(
        '--benchmark-dir',
        dest='benchmark_dir',
        metavar='PATH',
        default=DEFAULT_BENCHMARK_DIR,
        help='Directory to inspect for benchmarks. Defaults to the benchmarks '
             'included with djangobench.',
    )
    parser.add_argument(
        'benchmarks',
        metavar='name',
        default=None,
        help="Benchmarks to be run. Defaults to all.",
        nargs='*'
    )
    parser.add_argument(
        '-p',
        '--profile-dir',
        dest='profile_dir',
        default=None,
        metavar='PATH',
        help='Directory to record profiling statistics for the control and '
             'experimental run of each benchmark'
    )
    parser.add_argument(
        '--continue-on-error',
        dest='continue_on_error',
        action='store_true',
        help='Continue with the remaining benchmarks if any fail',
    )
    parser.add_argument(
        '-l',
        '--list',
        dest='list_benchmarks',
        action='store_true',
        help='List all available benchmarks and exit.',
    )
    parser.add_argument(
        '--log',
        dest='loglevel',
        default='WARNING',
        help='Define log level, set to INFO to show executed commands. Useful '
             'for debugging benchmarks.'
    )
    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=numeric_level)

    if args.list_benchmarks:
        print_benchmarks(args.benchmark_dir)
    else:
        run_benchmarks(
            control=args.control,
            experiment=args.experiment,
            benchmark_dir=args.benchmark_dir,
            benchmarks=args.benchmarks,
            trials=args.trials,
            vcs=None if args.vcs == 'none' else args.vcs,
            record_dir=args.record,
            profile_dir=args.profile_dir,
            continue_on_error=args.continue_on_error,
            control_python=args.control_python,
            experiment_python=args.experiment_python,
        )

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = perf
#!/usr/bin/env python

"""
Stolen from Unladen Swallow
(http://unladen-swallow.googlecode.com/svn/tests/perf.py). I'm just using
some parts of this -- stats results, t-tests, etc. -- but I've snagged
the whole file because I'm lazy. --JKM

----

Tool for comparing the performance of two Python implementations.

Typical usage looks like

./perf.py -b 2to3,django control/python experiment/python

This will run the 2to3 and Django template benchmarks, using `control/python`
as the baseline and `experiment/python` as the experiment. The --fast and
--rigorous options can be used to vary the duration/accuracy of the run. Run
--help to get a full list of options that can be passed to -b.

perf.py will run Student's two-tailed T test on the benchmark results at the 95%
confidence level to indicate whether the observed difference is statistically
significant.

Omitting the -b option will result in the default group of benchmarks being run
This currently consists of: 2to3, django, nbody, rietveld, slowspitfire,
slowpickle, slowunpickle, spambayes. Omitting -b is the same as specifying
`-b default`.

To run every benchmark perf.py knows about, use `-b all`. To see a full list of
all available benchmarks, use `--help`.

Negative benchmarks specifications are also supported: `-b -2to3` will run every
benchmark in the default group except for 2to3 (this is the same as
`-b default,-2to3`). `-b all,-django` will run all benchmarks except the Django
templates benchmark. Negative groups (e.g., `-b -default`) are not supported.
Positive benchmarks are parsed before the negative benchmarks are subtracted.

If --track_memory is passed, perf.py will continuously sample the benchmark's
memory usage, then give you the maximum usage and a link to a Google Chart of
the benchmark's memory usage over time. This currently only works on Linux
2.6.16 and higher or Windows with PyWin32. Because --track_memory introduces
performance jitter while collecting memory measurements, only memory usage is
reported in the final report.

If --args is passed, it specifies extra arguments to pass to the test
python binaries. For example,
  perf.py --args="-A -B,-C -D" base_python changed_python
will run benchmarks like
  base_python -A -B the_benchmark.py
  changed_python -C -D the_benchmark.py
while
  perf.py --args="-A -B" base_python changed_python
will pass the same arguments to both pythons:
  base_python -A -B the_benchmark.py
  changed_python -A -B the_benchmark.py
"""

from __future__ import division, with_statement

__author__ = "jyasskin@google.com (Jeffrey Yasskin)"

import contextlib
import logging
import math
import optparse
import os
import os.path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import threading
try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
    from urllib.error import URLError
except ImportError:
    from urlparse import urlparse
    from urllib2 import urlopen, URLError
try:
    import multiprocessing
except ImportError:
    multiprocessing = None
try:
    import win32api
    import win32con
    import win32process
    import pywintypes
except ImportError:
    win32api = None


info = logging.info


def avg(seq):
    return sum(seq) / float(len(seq))


def SampleStdDev(seq):
    """Compute the standard deviation of a sample.

    Args:
        seq: the numeric input data sequence.

    Returns:
        The standard deviation as a float.
    """
    mean = avg(seq)
    squares = ((x - mean) ** 2 for x in seq)
    return math.sqrt(sum(squares) / (len(seq) - 1))


# A table of 95% confidence intervals for a two-tailed t distribution, as a
# function of the degrees of freedom. For larger degrees of freedom, we
# approximate. While this may look less elegant than simply calculating the
# critical value, those calculations suck. Look at
# http://www.math.unb.ca/~knight/utility/t-table.htm if you need more values.
T_DIST_95_CONF_LEVELS = [0, 12.706, 4.303, 3.182, 2.776,
                         2.571, 2.447, 2.365, 2.306, 2.262,
                         2.228, 2.201, 2.179, 2.160, 2.145,
                         2.131, 2.120, 2.110, 2.101, 2.093,
                         2.086, 2.080, 2.074, 2.069, 2.064,
                         2.060, 2.056, 2.052, 2.048, 2.045,
                         2.042]


def TDist95ConfLevel(df):
    """Approximate the 95% confidence interval for Student's T distribution.

    Given the degrees of freedom, returns an approximation to the 95%
    confidence interval for the Student's T distribution.

    Args:
        df: An integer, the number of degrees of freedom.

    Returns:
        A float.
    """
    df = int(round(df))
    highest_table_df = len(T_DIST_95_CONF_LEVELS)
    if df >= 200: return 1.960
    if df >= 100: return 1.984
    if df >= 80: return 1.990
    if df >= 60: return 2.000
    if df >= 50: return 2.009
    if df >= 40: return 2.021
    if df >= highest_table_df:
        return T_DIST_95_CONF_LEVELS[highest_table_df - 1]
    return T_DIST_95_CONF_LEVELS[df]


def PooledSampleVariance(sample1, sample2):
    """Find the pooled sample variance for two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        Pooled sample variance, as a float.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    mean1 = avg(sample1)
    squares1 = ((x - mean1) ** 2 for x in sample1)
    mean2 = avg(sample2)
    squares2 = ((x - mean2) ** 2 for x in sample2)

    return (sum(squares1) + sum(squares2)) / float(deg_freedom)


def TScore(sample1, sample2):
    """Calculate a t-test score for the difference between two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        The t-test score, as a float.
    """
    assert len(sample1) == len(sample2)
    error = PooledSampleVariance(sample1, sample2) / len(sample1)
    return (avg(sample1) - avg(sample2)) / math.sqrt(error * 2)


def IsSignificant(sample1, sample2):
    """Determine whether two samples differ significantly.

    This uses a Student's two-sample, two-tailed t-test with alpha=0.95.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        (significant, t_score) where significant is a bool indicating whether
        the two samples differ significantly; t_score is the score from the
        two-sample T test.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    critical_value = TDist95ConfLevel(deg_freedom)
    t_score = TScore(sample1, sample2)
    return (abs(t_score) >= critical_value, t_score)


### Code to parse Linux /proc/%d/smaps files.
### See http://bmaurer.blogspot.com/2006/03/memory-usage-with-smaps.html for
### a quick introduction to smaps.

def _ParseSmapsData(smaps_data):
    """Parse the contents of a Linux 2.6 smaps file.

    Args:
        smaps_data: the smaps file contents, as a string.

    Returns:
        The size of the process's private data, in kilobytes.
    """
    total = 0
    for line in smaps_data.splitlines():
        # Include both Private_Clean and Private_Dirty sections.
        if line.startswith("Private_"):
            parts = line.split()
            total += int(parts[1])
    return total


def _ReadSmapsFile(pid):
    """Read the Linux smaps file for a pid.

    Args:
        pid: the process id to retrieve smaps data for.

    Returns:
        The data from the smaps file, as a string.

    Raises:
        IOError if the smaps file for the given pid could not be found.
    """
    with open("/proc/%d/smaps" % pid) as f:
        return f.read()


# Code to sample memory usage on Win32

def _GetWin32MemorySample(process_handle):
    """Gets the amount of memory in use by a process on Win32

    Args:
        process_handle: handle to the process to get the memory usage for

    Returns:
        The size of the process's private data, in kilobytes
    """
    pmi = win32process.GetProcessMemoryInfo(process_handle)
    return pmi["PagefileUsage"] // 1024


@contextlib.contextmanager
def _OpenWin32Process(pid):
    """Open a process on Win32 and close it when done

    Args:
        pid: the process id of the process to open

    Yields:
        A handle to the process

    Raises:
        pywintypes.error if the process does not exist or the user
            does not have sufficient privileges to open it

    Example:
        with _OpenWin32Process(pid) as process_handle:
            ...
    """
    h = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            0,
            pid)
    try:
        yield h
    finally:
        win32api.CloseHandle(h)


def CanGetMemoryUsage():
    """Returns True if MemoryUsageFuture is supported on this platform."""
    if win32api:
        try:
            with _OpenWin32Process(win32process.GetCurrentProcessId()):
                return True
        except pywintypes.error:
            pass

    try:
        _ReadSmapsFile(pid=1)
    except IOError:
        pass
    else:
        return True

    return False


class MemoryUsageFuture(threading.Thread):
    """Continuously sample a process's memory usage for its lifetime.

    Example:
        future = MemoryUsageFuture(some_pid)
        ...
        usage = future.GetMemoryUsage()
        print(max(usage))

    Note that calls to GetMemoryUsage() will block until the process exits.
    """

    def __init__(self, pid):
        super(MemoryUsageFuture, self).__init__()
        self._pid = pid
        self._usage = []
        self._done = threading.Event()
        self.start()

    def run(self):
        if win32api:
            with _OpenWin32Process(self._pid) as process_handle:
                while (win32process.GetExitCodeProcess(process_handle) ==
                       win32con.STILL_ACTIVE):
                    sample = _GetWin32MemorySample(process_handle)
                    self._usage.append(sample)
                    time.sleep(0.001)
        else:
            while True:
                try:
                    sample = _ParseSmapsData(_ReadSmapsFile(self._pid))
                    self._usage.append(sample)
                except IOError:
                    # Once the process exits, its smaps file will go away,
                    # leading _ReadSmapsFile() to raise IOError.
                    break
        self._done.set()

    def GetMemoryUsage(self):
        """Get the memory usage over time for the process being sampled.

        This will block until the process has exited.

        Returns:
            A list of all memory usage samples, in kilobytes.
        """
        self._done.wait()
        return self._usage


class RawData(object):
    """Raw data from a benchmark run.

    Attributes:
        runtimes: list of floats, one per iteration.
        mem_usage: list of ints, memory usage in kilobytes.
        inst_output: output from Unladen's --with-instrumentation build. This is
            the empty string if there was no instrumentation output.
    """

    def __init__(self, runtimes, mem_usage, inst_output=""):
        self.runtimes = runtimes
        self.mem_usage = mem_usage
        self.inst_output = inst_output


class BenchmarkResult(object):
    """An object representing data from a succesful benchmark run."""

    def __init__(self, min_base, min_changed, delta_min, avg_base,
                 avg_changed, delta_avg, t_msg, std_base, std_changed,
                 delta_std, timeline_link):
        self.min_base      = min_base
        self.min_changed   = min_changed
        self.delta_min     = delta_min
        self.avg_base      = avg_base
        self.avg_changed   = avg_changed
        self.delta_avg     = delta_avg
        self.t_msg         = t_msg
        self.std_base      = std_base
        self.std_changed   = std_changed
        self.delta_std     = delta_std
        self.timeline_link = timeline_link

    def get_timeline(self):
        if self.timeline_link is None:
            return ""
        return "\nTimeline: %(timeline_link)s" % self.__dict__

    def __str__(self):
        return (("Min: %(min_base)f -> %(min_changed)f:" +
                 " %(delta_min)s\n" +
                 "Avg: %(avg_base)f -> %(avg_changed)f:" +
                 " %(delta_avg)s\n" + self.t_msg +
                 "Stddev: %(std_base).5f -> %(std_changed).5f:" +
                 " %(delta_std)s" + self.get_timeline())
                 % self.__dict__)


class BenchmarkError(object):
    """Object representing the error from a failed benchmark run."""

    def __init__(self, e):
        self.msg = str(e)

    def __str__(self):
        return self.msg


class MemoryUsageResult(object):
    """Memory usage data from a successful benchmark run."""

    def __init__(self, max_base, max_changed, delta_max, timeline_link):
        self.max_base      = max_base
        self.max_changed   = max_changed
        self.delta_max     = delta_max
        self.timeline_link = timeline_link

    def get_usage_over_time(self):
        if self.timeline_link is None:
            return ""
        return "\nUsage over time: %(timeline_link)s" % self.__dict__

    def __str__(self):
        return (("Mem max: %(max_base).3f -> %(max_changed).3f:" +
                 " %(delta_max)s" + self.get_usage_over_time())
                 % self.__dict__)


class SimpleBenchmarkResult(object):
    """Object representing result data from a successful benchmark run."""

    def __init__(self, base_time, changed_time, time_delta):
        self.base_time    = base_time
        self.changed_time = changed_time
        self.time_delta   = time_delta

    def __str__(self):
        return ("%(base_time)f -> %(changed_time)f: %(time_delta)s"
                % self.__dict__)


class InstrumentationResult(object):
    """Object respresenting a --diff_instrumentation result."""

    def __init__(self, inst_diff, options):
        self.inst_diff = inst_diff
        self._control_label = options.control_label
        self._experiment_label = options.experiment_label

    def __str__(self):
        if not self.inst_diff:
            return "No difference in instrumentation"
        output = []
        for header, (control, exp) in self.inst_diff.items():
            output.append(header)
            output.append(self._control_label)
            output.append(control or "No data")
            output.append("")
            output.append(self._experiment_label)
            output.append(exp or "No data")
            output.append("\n")
        return "\n".join(output).strip()


def CompareMemoryUsage(base_usage, changed_usage, options):
    """Like CompareMultipleRuns, but for memory usage.

    Args:
        base_usage: list of the memory usage numbers for the control.
        changed_usage: list of the memory usage numbers for the experiment.
        options: optparse.Values instance.

    Returns:
        A MemoryUsageResult object.
    """
    max_base, max_changed = max(base_usage), max(changed_usage)
    delta_max = QuantityDelta(max_base, max_changed)

    if options.disable_timelines:
        chart_link = None
    else:
        chart_link = GetChart(SummarizeData(base_usage),
                              SummarizeData(changed_usage),
                              options,
                              title=options.benchmark_name,
                              y_label="Memory+(kb)")

    return MemoryUsageResult(max_base, max_changed, delta_max, chart_link)


### Utility functions


def _FormatPerfDataForTable(base_label, changed_label, results):
    """Prepare performance data for tabular output.

    Args:
        base_label: label for the control binary.
        changed_label: label for the experimental binary.
        results: iterable of (bench_name, result) 2-tuples where bench_name is
            the name of the benchmark being reported; and result is a
            BenchmarkResult object.

    Returns:
        A list of 6-tuples, where each tuple corresponds to a row in the output
        table, and each item in the tuples corresponds to a cell in the output
        table.
    """
    table = [("Benchmark", base_label, changed_label, "Change", "Significance",
              "Timeline")]

    for (bench_name, result) in results:
        table.append((bench_name,
                      # Limit the precision for conciseness in the table.
                      str(round(result.avg_base, 2)),
                      str(round(result.avg_changed, 2)),
                      result.delta_avg,
                      result.t_msg.strip(),
                      result.timeline_link))

    return table


def _FormatMemoryUsageForTable(base_label, changed_label, results):
    """Prepare memory usage data for tabular output.

    Args:
        base_label: label for the control binary.
        changed_label: label for the experimental binary.
        results: iterable of (bench_name, result) 2-tuples where bench_name is
            the name of the benchmark being reported; and result is a
            MemoryUsageResult object.

    Returns:
        A list of 5-tuples, where each tuple corresponds to a row in the output
        table, and each item in the tuples corresponds to a cell in the output
        table.
    """
    table = [("Benchmark", base_label, changed_label, "Change", "Timeline")]

    for (bench_name, result) in results:
        table.append((bench_name,
                      # We don't care about fractional kilobytes.
                      str(int(result.max_base)),
                      str(int(result.max_changed)),
                      result.delta_max,
                      result.timeline_link))

    return table


def FormatOutputAsTable(base_label, changed_label, results):
    """Format a benchmark result in a PEP-fiendly ASCII-art table.

    Args:
        base_label: label to use for the baseline binary.
        changed_label: label to use for the experimental binary.
        results: list of (bench_name, result) 2-tuples, where bench_name is the
            name of the just-run benchmark; and result is a BenchmarkResult
            object.

    Returns:
        A string holding the desired ASCII-art table.
    """
    if isinstance(results[0][1], BenchmarkResult):
        table = _FormatPerfDataForTable(base_label, changed_label, results)
    elif isinstance(results[0][1], MemoryUsageResult):
        table = _FormatMemoryUsageForTable(base_label, changed_label, results)
    else:
        raise TypeError("Unknown result type: %r" % type(results[0][1]))

    col_widths = [0] * len(table[0])
    for row in table:
        for col, val in enumerate(row):
            col_widths[col] = max(col_widths[col], len(val))

    outside_line = "+"
    header_sep_line = "+"
    for width in col_widths:
        width += 2  # Compensate for the left and right padding spaces.
        outside_line += "-" * width + "+"
        header_sep_line += "=" * width + "+"

    output = [outside_line]
    for row_i, row in enumerate(table):
        output_row = []
        for col_i, val in enumerate(row):
            output_row.append("| " + val.ljust(col_widths[col_i]) + " ")
        output.append("".join(output_row) + "|")
        if row_i > 0:
            output.append(outside_line)

    output.insert(2, "".join(header_sep_line))
    return "\n".join(output)


def _SegmentInstrumentation(inst_output):
    """Cut --with-instrumentation output into its component sections.

    Instrumentation sections are separated by two newlines, and begin with a
    header that ends in a colon and a newline.

    Args:
        inst_output: text holding full --with-instrumentation output.

    Returns:
        Dict mapping string section headers to section output text.
    """
    if not inst_output:
        return {}

    sections = {}
    text_sections = [s.strip() for s in inst_output.split("\n\n")]
    for section in text_sections:
        header, lines = section.split("\n", 1)
        if header.endswith(":"):
            sections[header] = lines
    return sections


def DiffInstrumentation(control_inst_output, exp_inst_output):
    """Compare the instrumentation output from two Unladen Swallow binaries.

    These binaries should have been configured with Unladen's
    --with-instrumentation flag.

    Args:
        control_inst_output: string; the control binary's instrumentation data.
        exp_inst_output: string; the experimental binary's instrumentation data.

    Returns:
        Dict mapping section headers to (control, exp) 2-tuples, where `control`
        is the output section from control binary, and `exp` is the output
        section from the experimental binary. If either `control` or `exp` is
        the empty string, that binary did not emit the section.
    """
    control_sections = _SegmentInstrumentation(control_inst_output)
    exp_sections = _SegmentInstrumentation(exp_inst_output)
    control_keys = set(control_sections)
    exp_keys = set(exp_sections)

    diff = {}
    for section in (control_keys - exp_keys):
        diff[section] = (control_sections[section], "")
    for section in (exp_keys - control_keys):
        diff[section] = ("", exp_sections[section])
    for section in (exp_keys & control_keys):
        if control_sections[section] != exp_sections[section]:
            diff[section] = (control_sections[section], exp_sections[section])
    return diff


def SimpleBenchmark(benchmark_function, base_python, changed_python, options,
                    *args, **kwargs):
    """Abstract out the body for most simple benchmarks.

    Example usage:
        def BenchmarkSomething(*args, **kwargs):
            return SimpleBenchmark(MeasureSomething, *args, **kwargs)

    The *args, **kwargs style is recommended so as to minimize the number of
    places that have to be changed if we update benchmark arguments.

    Args:
        benchmark_function: callback that takes (python_path, options) and
            returns a RawData instance.
        base_python: path to the reference Python binary.
        changed_python: path to the experimental Python binary.
        options: optparse.Values instance.
        *args, **kwargs: will be passed through to benchmark_function.

    Returns:
        A BenchmarkResult object if the benchmark runs succeeded.
        A BenchmarkError object if either benchmark run failed.
    """
    try:
        changed_data = benchmark_function(changed_python, options,
                                          *args, **kwargs)
        base_data = benchmark_function(base_python, options,
                                       *args, **kwargs)
    except subprocess.CalledProcessError as e:
        return BenchmarkError(e)

    return CompareBenchmarkData(base_data, changed_data, options)


def _FormatData(num):
    return str(round(num, 2))

def GetChart(base_data, changed_data, options, title, y_label,
             chart_margin=100):
    """Build a Google Chart API URL for the given data.

    Args:
        base_data: data points for the base binary.
        changed_data: data points for the changed binary.
        options: optparse.Values instance.
        title: title for the chart.
        y_label: label for Y axis on the chart.
        chart_margin: optional integer margin to add/sub from the max/min.

    Returns:
        Google Chart API URL as a string; or None, if options.disable_timelines
        is true.
    """
    if options.disable_timelines:
        return None
    # We use these to scale the graph.
    max_data = max(max(base_data), max(changed_data)) + chart_margin
    min_data = min(min(base_data), min(changed_data)) - chart_margin
    if min_data < 0:
        min_data = 0
    # Google-bound data, formatted as desired by the Chart API.
    data_for_google = (",".join(map(_FormatData, base_data)) + "|" +
                       ",".join(map(_FormatData, changed_data)))

    # Come up with labels for the X axis; not too many, though, or they'll be
    # unreadable.
    max_len = max(len(base_data), len(changed_data))
    if max_len <= 20:
        points = range(1, max_len + 1)
    else:
        points = SummarizeData(range(1, max_len + 1), points=5)
        if points[0] != 1:
            points.insert(0, 1)
    x_axis_labels = "".join("|%d" % i for i in points)

    # Parameters for the Google Chart API. See
    # http://code.google.com/apis/chart/ for more details.
    # cht=lc: line graph with visible axes.
    # chs: dimensions of the graph, in pixels.
    # chdl: labels for the graph lines.
    # chco: colors for the graph lines.
    # chds: minimum and maximum values for the vertical axis.
    # chxr: minimum and maximum values for the vertical axis labels.
    # chd=t: the data sets, |-separated.
    # chxt: which axes to draw.
    # chxl: labels for the axes.
    # chtt: chart title, using + for space and | for line breaks
    control_label = options.control_label
    experiment_label = options.experiment_label
    title = title.replace(' ', '+').replace('\n', '|')
    raw_url = ("http://chart.apis.google.com/chart?cht=lc&chs=700x400&"
               "chxt=x,y,x,y&"
               "chxr=1,%(min_data)s,%(max_data)s&chco=FF0000,0000FF&"
               "chdl=%(control_label)s|%(experiment_label)s&"
               "chds=%(min_data)s,%(max_data)s&chd=t:%(data_for_google)s&"
               "chxl=0:%(x_axis_labels)s|2:||Iteration|3:||%(y_label)s&"
               "chtt=%(title)s"
               % locals())
    return ShortenUrl(raw_url)


def ShortenUrl(url):
    """Shorten a given URL using tinyurl.com.

    Args:
        url: url to shorten.

    Returns:
        Shorter url. If tinyurl.com is not available, returns the original
        url unaltered.
    """
    tinyurl_api = "http://tinyurl.com/api-create.php?url="
    try:
        url = urlopen(tinyurl_api + url).read()
    except URLError:
        info("failed to call out to tinyurl.com")
    return url


def SummarizeData(data, points=100, summary_func=max):
    """Summarize a large data set using a smaller number of points.

    This will divide up the original data set into `points` windows,
    using `summary_func` to summarize each window into a single point.

    Args:
        data: the original data set, as a list.
        points: optional; how many summary points to take. Default is 100.
        summary_func: optional; function to use when summarizing each window.
            Default is the max() built-in.

    Returns:
        List of summary data points.
    """
    window_size = int(math.ceil(len(data) / points))
    if window_size == 1:
        return data

    summary_points = []
    start = 0
    while start < len(data):
        end = min(start + window_size, len(data))
        summary_points.append(summary_func(data[start:end]))
        start = end
    return summary_points


@contextlib.contextmanager
def ChangeDir(new_cwd):
    former_cwd = os.getcwd()
    os.chdir(new_cwd)
    try:
        yield
    finally:
        os.chdir(former_cwd)


def RemovePycs():
    if sys.platform == "win32":
        for root, dirs, files in os.walk('.'):
            for name in files:
                if name.endswith('.pyc') or name.endswith('.pyo'):
                    os.remove(os.path.join(root, name))
    else:
        subprocess.check_call(["find", ".", "-name", "*.py[co]",
                               "-exec", "rm", "-f", "{}", ";"])


def Relative(path):
    return os.path.join(os.path.dirname(__file__), path)


def LogCall(command):
    info("Running %s", " ".join(str(c) for c in command))
    return command


try:
    import resource
except ImportError:
    # Approximate child time using wall clock time.
    def GetChildUserTime():
        return time.time()
else:
    def GetChildUserTime():
        return resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime


@contextlib.contextmanager
def TemporaryFilename(prefix):
    fd, name = tempfile.mkstemp(prefix=prefix)
    os.close(fd)
    try:
        yield name
    finally:
        os.remove(name)


def TimeDelta(old, new):
    if old == 0 or new == 0:
        return "incomparable (one result was zero)"
    if new > old:
        return "%.4fx slower" % (new / old)
    elif new < old:
        return "%.4fx faster" % (old / new)
    else:
        return "no change"


def QuantityDelta(old, new):
    if old == 0 or new == 0:
        return "incomparable (one result was zero)"
    if new > old:
        return "%.4fx larger" % (new / old)
    elif new < old:
        return "%.4fx smaller" % (old / new)
    else:
        return "no change"


def BuildEnv(env=None, inherit_env=[]):
    """Massage an environment variables dict for the host platform.

    Massaging performed (in this order):
    - Add any variables named in inherit_env.
    - Copy PYTHONPATH to JYTHONPATH to support Jython.
    - Win32 requires certain env vars to be set.

    Args:
        env: optional; environment variables dict. If this is omitted, start
            with an empty environment.
        inherit_env: optional; iterable of strings, each the name of an
            environment variable to inherit from os.environ.

    Returns:
        A copy of `env`, possibly with modifications.
    """
    if env is None:
        env = {}
    fixed_env = env.copy()
    for varname in inherit_env:
        fixed_env[varname] = os.environ[varname]
    if "PYTHONPATH" in fixed_env:
        fixed_env["JYTHONPATH"] = fixed_env["PYTHONPATH"]
    if sys.platform == "win32":
        # Win32 requires certain environment variables be present
        for k in ("COMSPEC", "SystemRoot"):
            if k in os.environ and k not in fixed_env:
                fixed_env[k] = os.environ[k]
    return fixed_env


def CompareMultipleRuns(base_times, changed_times, options):
    """Compare multiple control vs experiment runs of the same benchmark.

    Args:
        base_times: iterable of float times (control).
        changed_times: iterable of float times (experiment).
        options: optparse.Values instance.

    Returns:
        A BenchmarkResult object, summarizing the difference between the two
        runs; or a SimpleBenchmarkResult object, if there was only one data
        point per run.
    """
    assert len(base_times) == len(changed_times)
    if len(base_times) == 1:
        # With only one data point, we can't do any of the interesting stats
        # below.
        base_time, changed_time = base_times[0], changed_times[0]
        time_delta = TimeDelta(base_time, changed_time)
        return SimpleBenchmarkResult(base_time, changed_time, time_delta)

    # Create a chart showing iteration times over time. We round the times so
    # as not to exceed the GET limit for Google's chart server.
    timeline_link = GetChart(SummarizeData(base_times),
                             SummarizeData(changed_times),
                             options,
                             title=options.benchmark_name,
                             y_label="Time+(secs)",
                             chart_margin=1)

    base_times = sorted(base_times)
    changed_times = sorted(changed_times)

    min_base, min_changed = base_times[0], changed_times[0]
    avg_base, avg_changed = avg(base_times), avg(changed_times)
    std_base = SampleStdDev(base_times)
    std_changed = SampleStdDev(changed_times)
    delta_min = TimeDelta(min_base, min_changed)
    delta_avg = TimeDelta(avg_base, avg_changed)
    delta_std = QuantityDelta(std_base, std_changed)

    t_msg = "Not significant\n"
    significant, t_score = IsSignificant(base_times, changed_times)
    if significant:
        t_msg = "Significant (t=%f)\n" % t_score

    return BenchmarkResult(min_base, min_changed, delta_min, avg_base,
                           avg_changed, delta_avg, t_msg, std_base,
                           std_changed, delta_std, timeline_link)


def CompareBenchmarkData(base_data, exp_data, options):
    """Compare performance and memory usage.

    Args:
        base_data: RawData instance for the control binary.
        exp_data: RawData instance for the experimental binary.
        options: optparse.Values instance.

    Returns:
        Something that implements a __str__() method:

        - BenchmarkResult: summarizes the difference between the two runs.
        - SimpleBenchmarkResult: if there was only one data point per run.
        - InstrumentationResult: if --diff_instrumentation was given.
        - MemoryUsageResult: if --track_memory was given.
        - BenchmarkError: if something went wrong.
    """
    # We suppress performance data when running with --track_memory or
    # --diff_instrumentation.
    if options.track_memory:
        if base_data.mem_usage is not None:
            assert exp_data.mem_usage is not None
            return CompareMemoryUsage(base_data.mem_usage, exp_data.mem_usage,
                                      options)
        return BencharkError("Benchmark does not report memory usage yet")
    if options.diff_instrumentation:
        inst_diff = DiffInstrumentation(base_data.inst_output,
                                        exp_data.inst_output)
        return InstrumentationResult(inst_diff, options)

    return CompareMultipleRuns(base_data.runtimes, exp_data.runtimes, options)


def CallAndCaptureOutput(command, env=None, track_memory=False, inherit_env=[]):
    """Run the given command, capturing stdout.

    Args:
        command: the command to run as a list, one argument per element.
        env: optional; environment variables to set.
        track_memory: optional; whether to continuously sample the subprocess's
            memory usage.
        inherit_env: optional; iterable of strings, each the name of an
            environment variable to inherit from os.environ.

    Returns:
        (stdout, stderr, mem_usage), where stdout is the captured stdout as a
        string; stderr is the captured stderr as a string; mem_usage is a list
        of memory usage samples in kilobytes (if track_memory is False,
        mem_usage is None).

    Raises:
        RuntimeError: if the command failed. The value of the exception will
        be the error message from the command.
    """
    mem_usage = None
    subproc = subprocess.Popen(LogCall(command),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               env=BuildEnv(env, inherit_env))
    if track_memory:
        future = MemoryUsageFuture(subproc.pid)
    stdout, stderr = (b.decode('utf-8') for b in subproc.communicate())
    if subproc.returncode != 0:
        raise RuntimeError("Benchmark died: " + stderr)
    if track_memory:
        mem_usage = future.GetMemoryUsage()
    return stdout, stderr, mem_usage


def MeasureGeneric(python, options, bm_path, bm_env=None,
                   extra_args=[], iteration_scaling=1):
    """Abstract measurement function for Unladen's bm_* scripts.

    Based on the values of options.fast/rigorous, will pass -n {5,50,100} to
    the benchmark script. MeasureGeneric takes care of parsing out the running
    times from the memory usage data.

    Args:
        python: start of the argv list for running Python.
        options: optparse.Values instance.
        bm_path: path to the benchmark script.
        bm_env: optional environment dict. If this is unspecified or None,
            use an empty enviroment.
        extra_args: optional list of command line args to be given to the
            benchmark script.
        iteration_scaling: optional multiple by which to scale the -n argument
            to the benchmark.

    Returns:
        RawData instance.
    """
    if bm_env is None:
        bm_env = {}

    trials = 50
    if options.rigorous:
        trials = 100
    elif options.fast:
        trials = 5
    trials = max(1, int(trials * iteration_scaling))

    RemovePycs()
    command = python + [bm_path, "-n", trials] + extra_args
    output = CallAndCaptureOutput(command, bm_env,
                                  track_memory=options.track_memory,
                                  inherit_env=options.inherit_env)
    stdout, stderr, mem_usage = output
    times = [float(line) for line in stdout.splitlines()]
    return RawData(times, mem_usage, inst_output=stderr)


### Benchmarks

class PyBenchBenchmarkResult(object):

    def __init__(self, min_base, min_changed, delta_min,
                 avg_base, avg_changed, delta_avg):
        self.min_base = min_base
        self.min_changed = min_changed
        self.delta_min = delta_min
        self.avg_base = avg_base
        self.avg_changed = avg_changed
        self.delta_avg = delta_avg

    def __str__(self):
        return (("Min: %(min_base)d -> %(min_changed)d: %(delta_min)s\n" +
                 "Avg: %(avg_base)d -> %(avg_changed)d: %(delta_avg)s")
                % self.__dict__)


_PY_BENCH_TOTALS_LINE = re.compile("""
    Totals:\s+(?P<min_base>\d+)ms\s+
    (?P<min_changed>\d+)ms\s+
    \S+\s+  # Percent change, which we re-compute
    (?P<avg_base>\d+)ms\s+
    (?P<avg_changed>\d+)ms\s+
    \S+  # Second percent change, also re-computed
    """, re.X)

def MungePyBenchTotals(line):
    m = _PY_BENCH_TOTALS_LINE.search(line)
    if m:
        min_base, min_changed, avg_base, avg_changed = map(float, m.group(
            "min_base", "min_changed", "avg_base", "avg_changed"))
        delta_min = TimeDelta(min_base, min_changed)
        delta_avg = TimeDelta(avg_base, avg_changed)
        return PyBenchBenchmarkResult(min_base, min_changed, delta_min,
                                      avg_base, avg_changed, delta_avg)
    return BenchmarkError(line)


def BM_PyBench(base_python, changed_python, options):
    if options.track_memory:
        return BenchmarkError("Benchmark does not report memory usage yet")

    warp = "10"
    if options.rigorous:
        warp = "1"
    if options.fast:
        warp = "100"

    PYBENCH_PATH = Relative("performance/pybench/pybench.py")
    PYBENCH_ENV = BuildEnv(inherit_env=options.inherit_env)

    try:
        with contextlib.nested(open(os.devnull, "wb"),
                               TemporaryFilename(prefix="baseline."),
                               TemporaryFilename(prefix="changed.")
                               ) as (dev_null, base_pybench, changed_pybench):
            RemovePycs()
            subprocess.check_call(LogCall(changed_python + [
                                           PYBENCH_PATH,
                                           "-w", warp,
                                           "-f", changed_pybench,
                                           ]), stdout=dev_null,
                                           env=PYBENCH_ENV)
            RemovePycs()
            subprocess.check_call(LogCall(base_python + [
                                           PYBENCH_PATH,
                                           "-w", warp,
                                           "-f", base_pybench,
                                           ]), stdout=dev_null,
                                           env=PYBENCH_ENV)
            comparer = subprocess.Popen(base_python + [
                                         PYBENCH_PATH,
                                         "--debug",
                                         "-s", base_pybench,
                                         "-c", changed_pybench,
                                         ], stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         env=PYBENCH_ENV)
            result, err = comparer.communicate()
            if comparer.returncode != 0:
                return BenchmarkError("pybench died: " + err)
    except subprocess.CalledProcessError as e:
        return BenchmarkError(e)

    if options.verbose:
        return BenchmarkError(result)
    else:
        for line in result.splitlines():
            if line.startswith("Totals:"):
                return MungePyBenchTotals(line)
        # The format's wrong...
        return BenchmarkError(result)


def MeasureCommand(command, iterations, env, track_memory):
    """Helper function to run arbitrary commands multiple times.

    Differences from MeasureGeneric():
        - MeasureGeneric() works with the performance/bm_*.py scripts.
        - MeasureCommand() does not echo every command run; it is intended for
          high-volume commands, like startup benchmarks

    Args:
        command: list of strings to be passed to Popen.
        iterations: number of times to run the command.
        env: environment vars dictionary.
        track_memory: bool to indicate whether to track memory usage.

    Returns:
        RawData instance. Note that we take instrumentation data from the final
        run; merging instrumentation data between multiple runs is
        prohibitively difficult at this point.

    Raises:
        RuntimeError: if the command failed.
    """
    with open(os.devnull, "wb") as dev_null:
        RemovePycs()

        # Priming run (create pyc files, etc).
        CallAndCaptureOutput(command, env=env)

        an_s = "s"
        if iterations == 1:
            an_s = ""
        info("Running `%s` %d time%s", command, iterations, an_s)

        times = []
        mem_usage = []
        for _ in range(iterations):
            start_time = GetChildUserTime()
            subproc = subprocess.Popen(command,
                                       stdout=dev_null, stderr=subprocess.PIPE,
                                       env=env)
            if track_memory:
                future = MemoryUsageFuture(subproc.pid)
            _, stderr = subproc.communicate()
            if subproc.returncode != 0:
                raise RuntimeError("Benchmark died: " + stderr)
            if track_memory:
                mem_samples = future.GetMemoryUsage()
            end_time = GetChildUserTime()
            elapsed = end_time - start_time
            assert elapsed != 0
            times.append(elapsed)
            if track_memory:
                mem_usage.extend(mem_samples)

    if not track_memory:
        mem_usage = None
    return RawData(times, mem_usage, inst_output=stderr)


def Measure2to3(python, options):
    fast_target = Relative("lib/2to3/lib2to3/refactor.py")
    two_to_three_bin = Relative("lib/2to3/2to3")
    two_to_three_dir = Relative("lib/2to3")
    env = BuildEnv({"PYTHONPATH": two_to_three_dir},
                   inherit_env=options.inherit_env)

    # This can be compressed, but it's harder to understand.
    if options.fast:
        trials = 1
        target = fast_target
    elif options.rigorous:
        trials = 5
        target = two_to_three_dir
    else:
        trials = 1
        target = two_to_three_dir

    command = python + [two_to_three_bin, "-f", "all", target]
    return MeasureCommand(command, trials, env, options.track_memory)


def BM_2to3(*args, **kwargs):
    return SimpleBenchmark(Measure2to3, *args, **kwargs)


def MeasureHgStartup(python, options):
    hg_bin = Relative("lib/mercurial/hg")
    hg_dir = Relative("lib/mercurial")
    hg_lib_dir = Relative("lib/mercurial/mercurial/pure")
    hg_path = os.pathsep.join([hg_dir, hg_lib_dir])
    hg_env = BuildEnv({"PYTHONPATH": hg_path}, options.inherit_env)

    trials = 500
    if options.rigorous:
        trials = 1000
    elif options.fast:
        trials = 100

    command = python + [hg_bin, "help"]
    return MeasureCommand(command, trials, hg_env, options.track_memory)


def BM_hg_startup(*args, **kwargs):
    return SimpleBenchmark(MeasureHgStartup, *args, **kwargs)


def MeasureBzrStartup(python, options):
    bzr_bin = Relative("lib/bazaar/bzr")
    bzr_path = Relative("lib/bazaar")
    bzr_env = BuildEnv({"PYTHONPATH": bzr_path}, options.inherit_env)

    trials = 100
    if options.rigorous:
        trials = 200
    elif options.fast:
        trials = 10

    command = python + [bzr_bin, "help"]
    return MeasureCommand(command, trials, bzr_env, options.track_memory)


def BM_bzr_startup(*args, **kwargs):
    return SimpleBenchmark(MeasureBzrStartup, *args, **kwargs)


DJANGO_DIR = Relative("lib/django")


def MeasureDjango(python, options):
    bm_path = Relative("performance/bm_django.py")
    bm_env = {"PYTHONPATH": DJANGO_DIR}
    return MeasureGeneric(python, options, bm_path, bm_env)


def BM_Django(*args, **kwargs):
    return SimpleBenchmark(MeasureDjango, *args, **kwargs)


def MeasureFloat(python, options):
    bm_path = Relative("performance/bm_float.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=5)

def BM_Float(*args, **kwargs):
    return SimpleBenchmark(MeasureFloat, *args, **kwargs)


def MeasureRietveld(python, options):
    PYTHONPATH = os.pathsep.join([DJANGO_DIR,
				  # These paths are lifted from
				  # lib/google_appengine.appcfg.py.  Note that we use
				  # our own version of Django instead of Appengine's.
				  Relative("lib/google_appengine"),
				  Relative("lib/google_appengine/lib/antlr3"),
				  Relative("lib/google_appengine/lib/webob"),
				  Relative("lib/google_appengine/lib/yaml/lib"),
				  Relative("lib/rietveld")])
    bm_path = Relative("performance/bm_rietveld.py")
    bm_env = {"PYTHONPATH": PYTHONPATH, "DJANGO_SETTINGS_MODULE": "settings"}

    return MeasureGeneric(python, options, bm_path, bm_env)


def BM_Rietveld(*args, **kwargs):
    return SimpleBenchmark(MeasureRietveld, *args, **kwargs)


def _ComesWithPsyco(python):
    """Determine whether the given Python binary already has Psyco.

    If the answer is no, we should build it (see BuildPsyco()).

    Args:
        python: prefix of a command line for the Python binary.

    Returns:
        True if we can "import psyco" with the given Python, False if not.
    """
    try:
        with open(os.devnull, "wb") as dev_null:
            subprocess.check_call(python + ["-c", "import psyco"],
                                  stdout=dev_null, stderr=dev_null,
                                  env=BuildEnv())
        return True
    except subprocess.CalledProcessError:
        return False


def _BuildPsyco(python):
    """Build Psyco against the given Python binary.

    Args:
        python: prefix of a command line for the Python binary.

    Returns:
        Path to Psyco's build directory. Putting this on your PYTHONPATH will
        make "import psyco" work.
    """
    PSYCO_SRC_DIR = Relative("lib/psyco")

    info("Building Psyco for %s", python)
    psyco_build_dir = tempfile.mkdtemp()
    abs_python = os.path.abspath(python[0])
    with ChangeDir(PSYCO_SRC_DIR):
        subprocess.check_call(LogCall([abs_python, "setup.py", "build",
                                       "--build-lib=" + psyco_build_dir]))
    return psyco_build_dir


def MeasureSpitfire(python, options, env=None, extra_args=[]):
    """Use Spitfire to test a Python binary's performance.

    Args:
        python: prefix of a command line for the Python binary to test.
        options: optparse.Values instance.
        env: optional; dict of environment variables to pass to Python.
        extra_args: optional; list of arguments to append to the Python
            command.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_spitfire.py")
    return MeasureGeneric(python, options, bm_path, env, extra_args)


def MeasureSpitfireWithPsyco(python, options):
    """Use Spitfire to measure Python's performance.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    SPITFIRE_DIR = Relative("lib/spitfire")

    psyco_dir = ""
    if not _ComesWithPsyco(python):
        psyco_dir = _BuildPsyco(python)

    env_dirs = filter(bool, [SPITFIRE_DIR, psyco_dir])
    spitfire_env = {"PYTHONPATH": os.pathsep.join(env_dirs)}

    try:
        return MeasureSpitfire(python, options, spitfire_env)
    finally:
        try:
            shutil.rmtree(psyco_dir)
        except OSError:
            pass


def BM_Spitfire(*args, **kwargs):
    return SimpleBenchmark(MeasureSpitfireWithPsyco, *args, **kwargs)


def BM_SlowSpitfire(base_python, changed_python, options):
    extra_args = ["--disable_psyco"]
    spitfire_env = {"PYTHONPATH": Relative("lib/spitfire")}

    try:
        changed_data = MeasureSpitfire(changed_python, options,
                                       spitfire_env, extra_args)
        base_data = MeasureSpitfire(base_python, options,
                                    spitfire_env, extra_args)
    except subprocess.CalledProcessError as e:
        return str(e)

    return CompareBenchmarkData(base_data, changed_data, options)


def MeasurePickle(python, options, extra_args):
    """Test the performance of Python's pickle implementations.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.
        extra_args: list of arguments to append to the command line.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_pickle.py")
    return MeasureGeneric(python, options, bm_path, extra_args=extra_args)


def _PickleBenchmark(base_python, changed_python, options, extra_args):
    """Test the performance of Python's pickle implementations.

    Args:
        base_python: prefix of a command line for the reference
                Python binary.
        changed_python: prefix of a command line for the
                experimental Python binary.
        options: optparse.Values instance.
        extra_args: list of arguments to append to the command line.

    Returns:
        Summary of whether the experiemental Python is better/worse than the
        baseline.
    """
    return SimpleBenchmark(MeasurePickle,
                           base_python, changed_python, options, extra_args)


def BM_Pickle(base_python, changed_python, options):
    args = ["--use_cpickle", "pickle"]
    return _PickleBenchmark(base_python, changed_python, options, args)


def BM_Unpickle(base_python, changed_python, options):
    args = ["--use_cpickle", "unpickle"]
    return _PickleBenchmark(base_python, changed_python, options, args)


def BM_Pickle_List(base_python, changed_python, options):
    args = ["--use_cpickle", "pickle_list"]
    return _PickleBenchmark(base_python, changed_python, options, args)


def BM_Unpickle_List(base_python, changed_python, options):
    args = ["--use_cpickle", "unpickle_list"]
    return _PickleBenchmark(base_python, changed_python, options, args)


def BM_Pickle_Dict(base_python, changed_python, options):
    args = ["--use_cpickle", "pickle_dict"]
    return _PickleBenchmark(base_python, changed_python, options, args)


def BM_SlowPickle(base_python, changed_python, options):
    return _PickleBenchmark(base_python, changed_python, options, ["pickle"])


def BM_SlowUnpickle(base_python, changed_python, options):
    return _PickleBenchmark(base_python, changed_python, options, ["unpickle"])


def MeasureNQueens(python, options):
    """Test the performance of an N-Queens solver.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_nqueens.py")
    return MeasureGeneric(python, options, bm_path)


def BM_NQueens(*args, **kwargs):
    return SimpleBenchmark(MeasureNQueens, *args, **kwargs)


def _StartupPython(command, mem_usage, track_memory, inherit_env):
    startup_env = BuildEnv(inherit_env=inherit_env)
    if not track_memory:
        subprocess.check_call(command, env=startup_env)
    else:
        subproc = subprocess.Popen(command, env=startup_env)
        future = MemoryUsageFuture(subproc.pid)
        if subproc.wait() != 0:
            raise RuntimeError("Startup benchmark died")
        mem_usage.extend(future.GetMemoryUsage())


def MeasureStartup(python, cmd_opts, num_loops, track_memory, inherit_env):
    times = []
    work = ""
    if track_memory:
        # Without this, Python may start and exit before the memory sampler
        # thread has time to work. We can't just do 'time.sleep(x)', because
        # under -S, 'import time' fails.
        work = "for _ in range(200000): pass"
    command = python + cmd_opts + ["-c", work]
    mem_usage = []
    info("Running `%s` %d times", command, num_loops * 20)
    for _ in range(num_loops):
        t0 = time.time()
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        _StartupPython(command, mem_usage, track_memory, inherit_env)
        t1 = time.time()
        times.append(t1 - t0)
    if not track_memory:
      mem_usage = None
    return RawData(times, mem_usage)


def BM_normal_startup(base_python, changed_python, options):
    if options.rigorous:
        num_loops = 100
    elif options.fast:
        num_loops = 5
    else:
        num_loops = 50

    opts = []
    changed_data = MeasureStartup(changed_python, opts, num_loops,
                                  options.track_memory, options.inherit_env)
    base_data = MeasureStartup(base_python, opts, num_loops,
                               options.track_memory, options.inherit_env)

    return CompareBenchmarkData(base_data, changed_data, options)


def BM_startup_nosite(base_python, changed_python, options):
    if options.rigorous:
        num_loops = 200
    elif options.fast:
        num_loops = 10
    else:
        num_loops = 100

    opts = ["-S"]
    changed_data = MeasureStartup(changed_python, opts, num_loops,
                                  options.track_memory, options.inherit_env)
    base_data = MeasureStartup(base_python, opts, num_loops,
                               options.track_memory, options.inherit_env)

    return CompareBenchmarkData(base_data, changed_data, options)


def MeasureRegexPerformance(python, options, bm_path):
    """Test the performance of Python's regex engine.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.
        bm_path: relative path; which benchmark script to run.

    Returns:
        RawData instance.
    """
    return MeasureGeneric(python, options, Relative(bm_path))


def RegexBenchmark(base_python, changed_python, options, bm_path):
    return SimpleBenchmark(MeasureRegexPerformance,
                           base_python, changed_python, options, bm_path)


def BM_regex_v8(base_python, changed_python, options):
    bm_path = "performance/bm_regex_v8.py"
    return RegexBenchmark(base_python, changed_python, options, bm_path)


def BM_regex_effbot(base_python, changed_python, options):
    bm_path = "performance/bm_regex_effbot.py"
    return RegexBenchmark(base_python, changed_python, options, bm_path)


def BM_regex_compile(base_python, changed_python, options):
    bm_path = "performance/bm_regex_compile.py"
    return RegexBenchmark(base_python, changed_python, options, bm_path)


def MeasureThreading(python, options, bm_name):
    """Test the performance of Python's threading support.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.
        bm_name: name of the threading benchmark to run.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_threading.py")
    return MeasureGeneric(python, options, bm_path, extra_args=[bm_name])


def ThreadingBenchmark(base_python, changed_python, options, bm_name):
    return SimpleBenchmark(MeasureThreading,
                           base_python, changed_python, options, bm_name)


def BM_threaded_count(base_python, changed_python, options):
    bm_name = "threaded_count"
    return ThreadingBenchmark(base_python, changed_python, options, bm_name)


def BM_iterative_count(base_python, changed_python, options):
    bm_name = "iterative_count"
    return ThreadingBenchmark(base_python, changed_python, options, bm_name)


def MeasureUnpackSequence(python, options):
    """Test the performance of sequence unpacking.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_unpack_sequence.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=1000)


def BM_unpack_sequence(*args, **kwargs):
    return SimpleBenchmark(MeasureUnpackSequence, *args, **kwargs)


def MeasureCallSimple(python, options):
    bm_path = Relative("performance/bm_call_simple.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=3)


def BM_call_simple(*args, **kwargs):
    return SimpleBenchmark(MeasureCallSimple, *args, **kwargs)


def MeasureCallMethod(python, options):
    bm_path = Relative("performance/bm_call_method.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=3)


def BM_call_method(*args, **kwargs):
    return SimpleBenchmark(MeasureCallMethod, *args, **kwargs)


def MeasureCallMethodUnknown(python, options):
    bm_path = Relative("performance/bm_call_method_unknown.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=3)


def BM_call_method_unknown(*args, **kwargs):
    return SimpleBenchmark(MeasureCallMethodUnknown, *args, **kwargs)


def MeasureCallMethodSlots(python, options):
    bm_path = Relative("performance/bm_call_method_slots.py")
    return MeasureGeneric(python, options, bm_path, iteration_scaling=3)


def BM_call_method_slots(*args, **kwargs):
    return SimpleBenchmark(MeasureCallMethodSlots, *args, **kwargs)


def MeasureNbody(python, options):
    """Test the performance of math operations using an n-body benchmark.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_nbody.py")
    return MeasureGeneric(python, options, bm_path)


def BM_nbody(*args, **kwargs):
    return SimpleBenchmark(MeasureNbody, *args, **kwargs)


def MeasureSpamBayes(python, options):
    """Test the performance of the SpamBayes spam filter and its tokenizer.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    pypath = os.pathsep.join([Relative("lib/spambayes"), Relative("lib/lockfile")])
    bm_path = Relative("performance/bm_spambayes.py")
    bm_env = BuildEnv({"PYTHONPATH": pypath}, options.inherit_env)
    return MeasureGeneric(python, options, bm_path, bm_env)


def BM_spambayes(*args, **kwargs):
    return SimpleBenchmark(MeasureSpamBayes, *args, **kwargs)


def MeasureHtml5libWarmup(python, options):
    """Test the performance of the html5lib HTML 5 parser.

    Args:
        python: prefix of a command line for the Python binary.
        options: optparse.Values instance.

    Returns:
        RawData instance.
    """
    bm_path = Relative("performance/bm_html5lib.py")
    bm_env = BuildEnv({"PYTHONPATH": Relative("lib/html5lib")},
                      options.inherit_env)
    return MeasureGeneric(python, options, bm_path, bm_env,
                          iteration_scaling=0.10)


def BM_html5lib_warmup(*args, **kwargs):
    return SimpleBenchmark(MeasureHtml5libWarmup, *args, **kwargs)


def MeasureHtml5lib(python, options):
    bm_path = Relative("performance/bm_html5lib.py")
    bm_env = BuildEnv({"PYTHONPATH": Relative("lib/html5lib")},
                      options.inherit_env)

    trials = 5
    if options.fast:
        trials = 1
    elif options.rigorous:
        trials = 10

    command = python + [bm_path, "-n", "1"]
    return MeasureCommand(command, trials, bm_env, options.track_memory)


def BM_html5lib(*args, **kwargs):
    return SimpleBenchmark(MeasureHtml5lib, *args, **kwargs)


def MeasureRichards(python, options):
    bm_path = Relative("performance/bm_richards.py")
    return MeasureGeneric(python, options, bm_path)

def BM_richards(*args, **kwargs):
    return SimpleBenchmark(MeasureRichards, *args, **kwargs)

### End benchmarks, begin main entry point support.

def _FindAllBenchmarks(namespace):
    return dict((name[3:].lower(), func)
                for (name, func) in sorted(namespace.items())
                if name.startswith("BM_"))

BENCH_FUNCS = _FindAllBenchmarks(globals())

# Benchmark groups. The "default" group is what's run if no -b option is
# specified.
# If you update the default group, be sure to update the module docstring, too.
# An "all" group which includes every benchmark perf.py knows about is generated
# automatically.
BENCH_GROUPS = {"default": ["2to3", "django", "nbody", "rietveld",
                            "slowspitfire", "slowpickle", "slowunpickle",
                            "spambayes"],
                "startup": ["normal_startup", "startup_nosite",
                            "bzr_startup", "hg_startup"],
                "regex": ["regex_v8", "regex_effbot", "regex_compile"],
                "threading": ["threaded_count", "iterative_count"],
                "cpickle": ["pickle", "unpickle"],
                "apps": ["2to3", "html5lib", "rietveld", "spambayes"],
                "calls": ["call_simple", "call_method", "call_method_slots",
                          "call_method_unknown"],
                "math": ["nbody", "float"],
               }


def _ExpandBenchmarkName(bm_name, bench_groups):
    """Recursively expand name benchmark names.

    Args:
        bm_name: string naming a benchmark or benchmark group.

    Yields:
        Names of actual benchmarks, with all group names fully expanded.
    """
    expansion = bench_groups.get(bm_name)
    if expansion:
        for name in expansion:
            for name in _ExpandBenchmarkName(name, bench_groups):
                yield name
    else:
        yield bm_name


def ParseBenchmarksOption(benchmarks_opt, bench_groups):
    """Parses and verifies the --benchmarks option.

    Args:
        benchmarks_opt: the string passed to the -b option on the command line.

    Returns:
        A set() of the names of the benchmarks to run.
    """
    legal_benchmarks = bench_groups["all"]
    benchmarks = benchmarks_opt.split(",")
    positive_benchmarks = set(
        bm.lower() for bm in benchmarks if bm and bm[0] != "-")
    negative_benchmarks = set(
        bm[1:].lower() for bm in benchmarks if bm and bm[0] == "-")

    should_run = set()
    if not positive_benchmarks:
        should_run = set(_ExpandBenchmarkName("default", bench_groups))

    for name in positive_benchmarks:
        for bm in _ExpandBenchmarkName(name, bench_groups):
            if bm not in legal_benchmarks:
                logging.warning("No benchmark named %s", bm)
            else:
                should_run.add(bm)
    for bm in negative_benchmarks:
        if bm in bench_groups:
            raise ValueError("Negative groups not supported: -%s" % bm)
        elif bm not in legal_benchmarks:
            logging.warning("No benchmark named %s", bm)
        else:
            should_run.remove(bm)
    return should_run


def ParsePythonArgsOption(python_args_opt):
    """Parses the --args option.

    Args:
        python_args_opt: the string passed to the -a option on the command line.

    Returns:
        A pair of lists: (base_python_args, changed_python_args).
    """
    args_pair = python_args_opt.split(",")
    base_args = args_pair[0].split()  # On whitespace.
    changed_args = base_args
    if len(args_pair) == 2:
        changed_args = args_pair[1].split()
    elif len(args_pair) > 2:
        logging.warning("Didn't expect two or more commas in --args flag: %s",
                        python_args_opt)
    return base_args, changed_args


def ParseEnvVars(option, opt_str, value, parser):
    """Parser callback to --inherit_env var names."""
    parser.values.inherit_env = [v for v in value.split(",") if v]


def ParseOutputStyle(option, opt_str, value, parser):
    if value not in ("normal", "table"):
        parser.error("Invalid output style: %r" % value)
    parser.values.output_style = value


def main(argv, bench_funcs=BENCH_FUNCS, bench_groups=BENCH_GROUPS):
    bench_groups = bench_groups.copy()
    all_benchmarks = bench_funcs.keys()
    bench_groups["all"] = all_benchmarks

    parser = optparse.OptionParser(
        usage="%prog [options] baseline_python changed_python",
        description=("Compares the performance of baseline_python with" +
                     " changed_python and prints a report."))
    parser.add_option("-r", "--rigorous", action="store_true",
                      help=("Spend longer running tests to get more" +
                            " accurate results"))
    parser.add_option("-f", "--fast", action="store_true",
                      help="Get rough answers quickly")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="Print more output")
    parser.add_option("-m", "--track_memory", action="store_true",
                      help="Track memory usage. This only works on Linux.")
    parser.add_option("-a", "--args", default="",
                      help=("Pass extra arguments to the python binaries."
                            " If there is a comma in this option's value, the"
                            " arguments before the comma (interpreted as a"
                            " space-separated list) are passed to the baseline"
                            " python, and the arguments after are passed to the"
                            " changed python. If there's no comma, the same"
                            " options are passed to both."))
    parser.add_option("-b", "--benchmarks", metavar="BM_LIST", default="",
                      help=("Comma-separated list of benchmarks to run.  Can" +
                            " contain both positive and negative arguments:" +
                            "  --benchmarks=run_this,also_this,-not_this.  If" +
                            " there are no positive arguments, we'll run all" +
                            " benchmarks except the negative arguments. " +
                            " Otherwise we run only the positive arguments. " +
                            " Valid benchmarks are: " +
                            ", ".join(bench_groups.keys() + all_benchmarks)))
    parser.add_option("--inherit_env", metavar="VAR_LIST", type="string",
                      action="callback", callback=ParseEnvVars, default=[],
                      help=("Comma-separated list of environment variable names"
                            " that are inherited from the parent environment"
                            " when running benchmarking subprocesses."))
    parser.add_option("--disable_timelines", default=False, action="store_true",
                      help="Don't use Google charts for displaying timelines.")
    parser.add_option("--output_style", metavar="STYLE", type="string",
                      action="callback", callback=ParseOutputStyle,
                      default="normal",
                      help=("What style the benchmark output should take."
                            " Valid options are 'normal' and 'table'."
                            " Default is '%default'."))
    parser.add_option("--control_label", metavar="LABEL", type="string",
                      action="store", default="",
                      help="Optional label for the control binary")
    parser.add_option("--experiment_label", metavar="LABEL", type="string",
                      action="store", default="",
                      help="Optional label for the experiment binary")
    parser.add_option("--diff_instrumentation", action="store_true",
                      help=("Compare the --with-instrumentation output from two"
                            " Unladen Swallow binaries. This is useful for"
                            " examining many benchmarks for optimization"
                            " effects."))


    options, args = parser.parse_args(argv)
    if len(args) != 2:
        parser.error("incorrect number of arguments")
    base, changed = args
    options.base_binary = base
    options.changed_binary = changed

    if not options.control_label:
        options.control_label = options.base_binary
    if not options.experiment_label:
        options.experiment_label = options.changed_binary

    base_args, changed_args = ParsePythonArgsOption(options.args)
    base_cmd_prefix = [base] + base_args
    changed_cmd_prefix = [changed] + changed_args

    logging.basicConfig(level=logging.INFO)

    if options.track_memory:
        if CanGetMemoryUsage():
            info("Suppressing performance data due to --track_memory")
        else:
            # TODO(collinwinter): make this work on other platforms.
            parser.error("--track_memory requires Windows with PyWin32 or " +
                         "Linux 2.6.16 or above")

    if options.diff_instrumentation:
        info("Suppressing performance data due to --diff_instrumentation")

    should_run = ParseBenchmarksOption(options.benchmarks, bench_groups)

    results = []
    for name in sorted(should_run):
        func = bench_funcs[name]
        print("Running %s..." % name)
        options.benchmark_name = name  # Easier than threading this everywhere.
        results.append((name, func(base_cmd_prefix, changed_cmd_prefix,
                                   options)))

    print('')
    print("Report on %s" % " ".join(platform.uname()))
    if multiprocessing:
        print("Total CPU cores:", multiprocessing.cpu_count())
    if options.output_style == "normal":
        for name, result in results:
            print('')
            print("###", name, "###")
            print(result)
    elif options.output_style == "table":
        print(FormatOutputAsTable(options.control_label,
                                  options.experiment_label,
                                  results))
    else:
        raise ValueError("Invalid output_style: %r" % options.output_style)
    return results

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = utils
import argparse
import inspect
import os

# timeit uses either time.time() or time.clock() depending on which is more
# accurate on the current platform:
from timeit import default_timer as time_f

try:
    import cProfile as profile
except ImportError:
    import profile

benchmark_parser = argparse.ArgumentParser()
benchmark_parser.add_argument('-t', '--trials', type=int, default=100)

def run_benchmark(benchmark, syncdb=True, setup=None, trials=None, handle_argv=True, meta={}):
    """
    Run a benchmark a few times and report the results.

    Arguments:

        benchmark
            The benchmark callable. ``run_benchmark`` will time
            the executation of this function and report those times
            back to the harness. However, if ``benchmark`` returns
            a value, that result will reported instead of the
            raw timing.

        syncdb
            If True, a syncdb will be performed before running
            the benchmark.

        setup
            A function to be called before running the benchmark
            function(s).

        trials
            The number of times to run the benchmark function. If not given
            and if ``handle_argv`` is ``True`` this'll be automatically
            determined from the ``--trials`` flag.

        handle_argv
            ``True`` if the script should handle ``sys.argv`` and set
            the number of trials accordingly.

        meta
            Key/value pairs to be returned as part of the benchmark results.
    """
    if handle_argv:
        args = benchmark_parser.parse_args()
        trials = trials or args.trials

    print_benchmark_header(benchmark, meta)

    import django
    if hasattr(django, 'setup'):
        django.setup()
    if syncdb:
        from django.core.management import call_command
        call_command("syncdb", verbosity=0)

    if setup:
        setup()

    for x in range(trials):
        start = time_f()
        profile_file = os.environ.get('DJANGOBENCH_PROFILE_FILE', None)
        if profile_file is not None:
            loc = locals().copy()
            profile.runctx('benchmark_result = benchmark()', globals(), loc, profile_file)
            benchmark_result = loc['benchmark_result']
        else:
            benchmark_result = benchmark()
        if benchmark_result is not None:
            print(benchmark_result)
        else:
            print(time_f() - start)


def run_comparison_benchmark(benchmark_a, benchmark_b, syncdb=True, setup=None, trials=None, handle_argv=True, meta={}):
    """
    Benchmark the difference between two functions.

    Arguments are as for ``run_benchmark``, except that this takes 2
    benchmark functions, an A and a B, and reports the difference between
    them.

    For example, you could use this to test the overhead of an ORM query
    versus a raw SQL query -- pass the ORM query as ``benchmark_a`` and the
    raw query as ``benchmark_b`` and this function will report the
    difference in time between them.

    For best results, the A function should be the more expensive one
    (otherwise djangobench will report results like "-1.2x slower", which
    is just confusing).
    """
    if handle_argv:
        args = benchmark_parser.parse_args()
        trials = trials or args.trials

    print_benchmark_header(benchmark_a, meta)
    import django
    if hasattr(django, 'setup'):
        django.setup()

    if syncdb:
        from django.core.management import call_command
        call_command("syncdb", verbosity=0)

    if setup:
        setup()

    for x in range(trials):
        start_a = time_f()
        result_a = benchmark_a()
        result_a = result_a or time_f() - start_a

        start_b = time_f()
        result_b = benchmark_b()
        result_b = result_b or time_f() - start_b

        print(result_a - result_b)


def print_benchmark_header(benchmark, meta):
    if 'title' not in map(str.lower, meta.keys()):
        meta['title'] = inspect.getmodule(benchmark).__name__
    for key, value in meta.items():
        print('%s: %s' % (key.lower(), value))
    print('')

########NEW FILE########
