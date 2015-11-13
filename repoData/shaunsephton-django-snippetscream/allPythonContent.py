__FILENAME__ = csv_serializer
from _2240 import *

########NEW FILE########
__FILENAME__ = models
# Purely included to allow for app install.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^some/url/$', 'app.views.view'),
    url(r'^some/other/url/$', 'app.views.other.view', name='this_is_a_named_view'),
)

########NEW FILE########
__FILENAME__ = _1031
# http://djangosnippets.org/snippets/1031/

from django.contrib.contenttypes.models import ContentType
from django.db import models


class PolyModel(models.Model):
    """
    Model class aware of its child models, allowing for child class objects
    to be resolved from parent objects.

    For example:
    Contact is a parent class inheriting from PolyModel. Subclasses might be
    Company, Person, Artist, Label etc. Basic address, email etc. fields can
    be added to the parent class and all subclasses will have those.

    Having searched your database for Contact objects (undifferentiated by
    class) you then want to reload the chosen object as the subclass
    that it really is:

    thing.as_leaf_class()
    """
    content_type = models.ForeignKey(
        ContentType,
        editable=False,
        null=True
    )
    class_name = models.CharField(
        max_length=32,
        editable=False,
        null=True
    )

    class Meta:
        abstract = True

    def as_leaf_class(self):
        """
        Returns the leaf class no matter where the calling instance
        is in the inheritance hierarchy.
        """
        try:
            return self.__getattribute__(self.class_name.lower())
        except AttributeError:
            content_type = self.content_type
            model = content_type.model_class()
            if(PolyModel in model.__bases__):
                return self
            return model.objects.get(id=self.id)

    def save(self, *args, **kwargs):
        """
        Save field required for leaf class resolution.
        """
        # set leaf class content type
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(self.\
                    __class__)

        # set leaf class class name
        if not self.class_name:
            self.class_name = self.__class__.__name__

        super(PolyModel, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = _1378
# http://djangosnippets.org/snippets/1378/

from django.core.urlresolvers import RegexURLPattern, Resolver404, get_resolver

__all__ = ('resolve_to_name',)


def _dispatch(pattern, path):
    if isinstance(pattern, RegexURLPattern):
        return _pattern_resolve_to_name(pattern, path)
    else:
        return _resolver_resolve_to_name(pattern, path)

def _pattern_resolve_to_name(self, path):
    match = self.regex.search(path)
    if match:
        name = ''
        if self.name:
            name = self.name
        elif hasattr(self, '_callback_str'):
            name = self._callback_str
        else:
            name = "%s.%s" % (self.callback.__module__, self.callback.\
                    func_name)
        return name


def _resolver_resolve_to_name(self, path):
    tried = []
    match = self.regex.search(path)
    if match:
        new_path = path[match.end():]
        for pattern in self.url_patterns:
            try:
                name = _dispatch(pattern, new_path)
            except Resolver404, e:
                tried.extend([(pattern.regex.pattern + '   ' + t) for t in \
                        e.args[0]['tried']])
            else:
                if name:
                    return name
                tried.append(pattern.regex.pattern)
        raise Resolver404, {'tried': tried, 'path': new_path}


def resolve_to_name(path, urlconf=None):
    r = get_resolver(urlconf)
    return _dispatch(r, path)

########NEW FILE########
__FILENAME__ = _186
import sys
import tempfile
import hotshot
from django.conf import settings
from cStringIO import StringIO

# Don't fail if profile module not found. Not ideal, but we don't want
# all snippets to be unavailable due to one misbehaving.
try:
    import profile
except ImportError, e:
    pass
else:
    import hotshot.stats


class ProfileMiddleware(object):
    """
    Displays hotshot profiling for any view.
    http://yoursite.com/yourview/?prof

    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode,
    but you really shouldn't add this middleware to any production
    configuration.
    * Only tested on Linux
    """
    def process_request(self, request):
        if settings.DEBUG and ('prof' in request.GET):
            self.tmpfile = tempfile.NamedTemporaryFile()
            self.prof = hotshot.Profile(self.tmpfile.name)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if settings.DEBUG and ('prof' in request.GET):
            return self.prof.runcall(callback, request, *callback_args, \
                    **callback_kwargs)

    def process_response(self, request, response):
        if settings.DEBUG and ('prof' in request.GET):
            self.prof.close()

            out = StringIO()
            old_stdout = sys.stdout
            sys.stdout = out

            stats = hotshot.stats.load(self.tmpfile.name)
            #stats.strip_dirs()

            stats.sort_stats('time', 'calls')
            stats.print_stats()

            sys.stdout = old_stdout
            stats_str = out.getvalue()

            if response and response.content and stats_str:
                response.content = "<pre>" + stats_str + "</pre>"

            response['Content-Type'] = 'text/html'
        return response

########NEW FILE########
__FILENAME__ = _1875
# http://djangosnippets.org/snippets/1875/

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth.management import create_superuser
from django.db.models import signals


def create_default_superuser(app, created_models, verbosity, **kwargs):
    """
    Creates our default superuser.
    """
    try:
        auth_models.User.objects.get(username='admin')
    except auth_models.User.DoesNotExist:
        print 'Creating default superuser:\nUsername: admin\nPassword: \
admin\nEmail: invalid@ddress.com'
        assert auth_models.User.objects.create_superuser('admin', \
                'invalid@ddress.com', 'admin')
    else:
        print 'Default superuser already exists.'

if getattr(settings, 'CREATE_DEFAULT_SUPERUSER', False):
    # From http://stackoverflow.com/questions/1466827/:
    # Prevent interactive question about wanting a superuser created.
    # (This code has to go in this otherwise empty "models" module
    # so that it gets processed by the "syncdb" command during
    # database creation.)
    signals.post_syncdb.disconnect(
        create_superuser,
        sender=auth_models,
        dispatch_uid='django.contrib.auth.management.create_superuser'
    )

    # Trigger default superuser creation.
    signals.post_syncdb.connect(
        create_default_superuser,
        sender=auth_models,
        dispatch_uid='common.models.create_testuser'
    )

########NEW FILE########
__FILENAME__ = _2240
"""
Serialize data to/from CSV

Since CSV deals only in string values, certain conventions must be
employed to represent other data types. The conventions used in this
serializer implementation are as follows:

- Boolean values are serialized as 'TRUE' and 'FALSE'
- The strings 'TRUE' and 'FALSE' are  serialized as "'TRUE'" and "'FALSE'"
- None is serialized as 'NULL'
- The string 'NULL' is serialized as "'NULL'"
- Lists are serialized as comma separated items surrounded by brackets,
  e.g. [foo, bar] becomes '[foo, bar]'
- Strings beginning with '[' and ending in ']' are serialized by being
  wrapped in single quotes, e.g. '[foo, bar]' becomes "'[foo, bar]'"

See also:
http://docs.djangoproject.com/en/1.2/topics/serialization/

"""
import codecs
import csv
import re
import StringIO

from itertools import groupby
from operator import itemgetter

from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.utils.encoding import smart_unicode


class Serializer(PythonSerializer):
    """
    Convert a queryset to CSV.
    """
    internal_use_only = False

    def end_serialization(self):

        def process_item(item):
            if isinstance(item, (list, tuple)):
                item = process_m2m(item)
            elif isinstance(item, bool):
                item = str(item).upper()
            elif isinstance(item, basestring):
                if item in ('TRUE', 'FALSE', 'NULL') or _LIST_RE.match(item):
                    # Wrap these in quotes, so as not to be confused with
                    # builtin types when deserialized
                    item = "'%s'" % item
            elif item is None:
                item = 'NULL'
            return smart_unicode(item)

        def process_m2m(seq):
            parts = []
            for item in seq:
                if isinstance(item, (list, tuple)):
                    parts.append(process_m2m(item))
                else:
                    parts.append(process_item(item))
            return '[%s]' % ', '.join(parts)

        writer = UnicodeWriter(self.stream)
        # Group objects by model and write out a header and rows for each.
        # Multiple models can be present when invoking from the command
        # line, e.g.: `python manage.py dumpdata --format csv auth`
        for k, g in groupby(self.objects, key=itemgetter('model')):
            write_header = True
            for d in g:
                # "flatten" the object. PK and model values come first,
                # then field values. Flat is better than nested, right? :-)
                pk, model, fields = d['pk'], d['model'], d['fields']
                pk, model = smart_unicode(pk), smart_unicode(model)
                row = [pk, model] + map(process_item, fields.values())
                if write_header:
                    header = ['pk', 'model'] + fields.keys()
                    writer.writerow(header)
                    write_header = False
                writer.writerow(row)

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()


_QUOTED_BOOL_NULL = """ 'TRUE' 'FALSE' 'NULL' "TRUE" "FALSE" "NULL" """.split()

# regular expressions used in deserialization
_LIST_PATTERN = r'\[(.*)\]'
_LIST_RE = re.compile(r'\A%s\Z' % _LIST_PATTERN)
_QUOTED_LIST_RE = re.compile(r"""
    \A                 # beginning of string
    (['"])             # quote char
    %s                 # list
    \1                 # matching quote
    \Z                 # end of string""" % _LIST_PATTERN, re.VERBOSE)
_SPLIT_RE = re.compile(r', *')
_NK_LIST_RE = re.compile(r"""
    \A                 # beginning of string
    \[                 # opening bracket
    [^]]+              # one or more non brackets
    \]                 # closing bracket
    (?:, *\[[^]]+\])*  # zero or more of above, separated
                       #   by a comma and optional spaces
    \Z                 # end of string""", re.VERBOSE)
_NK_SPLIT_RE = re.compile(r"""
    (?<=\])            # closing bracket (lookbehind)
    , *                # comma and optional spaces
    (?=\[)             # opening bracket (lookahead)""", re.VERBOSE)


def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of CSV data.
    """
    def process_item(item):
        m = _LIST_RE.match(item)
        if m:
            contents = m.group(1)
            if not contents:
                item = []
            else:
                item = process_m2m(contents)
        else:
            if item == 'TRUE':
                item = True
            elif item == 'FALSE':
                item = False
            elif item == 'NULL':
                item = None
            elif (item in _QUOTED_BOOL_NULL or
                  _QUOTED_LIST_RE.match(item)):
                item = item.strip('\'"')
        return item

    def process_m2m(contents):
        li = []
        if _NK_LIST_RE.match(contents):
            for item in _NK_SPLIT_RE.split(contents):
                li.append(process_item(item))
        else:
            li = _SPLIT_RE.split(contents)
        return li

    if isinstance(stream_or_string, basestring):
        stream = StringIO.StringIO(stream_or_string)
    else:
        stream = stream_or_string

    reader = UnicodeReader(stream)
    header = next(reader)  # first line must be a header

    data = []
    for row in reader:
        # Need to account for the presence of multiple headers in
        # the stream since serialized data can contain them.
        if row[:2] == ['pk', 'model']:
            # Not the best check. Perhaps csv.Sniffer.has_header
            # would be better?
            header = row
            continue
        d = dict(zip(header[:2], row[:2]))
        d['fields'] = dict(zip(header[2:], map(process_item, row[2:])))
        data.append(d)

    for obj in PythonDeserializer(data, **options):
        yield obj


# The classes below taken from http://docs.python.org/library/csv.html

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode('utf-8')


class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, 'utf-8') for s in row]

    def __iter__(self):
        return self


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode('utf-8') for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode('utf-8')
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

########NEW FILE########
__FILENAME__ = _2536
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Adapted From Http://stackoverflow.com/questions/1466827/ --
from django.conf import settings
from django.db.models import signals
from django.contrib.sites.models import Site
from django.contrib.sites import models as site_app
from django.contrib.sites.management import create_default_site as orig_default_site


# Configure default Site creation with better defaults, and provide
# overrides for those defaults via settings and kwargs:
def create_default_site(app, created_models, verbosity, db, **kwargs):
    name  = kwargs.pop('name', None)
    domain = kwargs.pop('domain', None)

    if not name:
        name = getattr(settings, 'DEFAULT_SITE_NAME', 'example.com')
    if not domain:
        domain = getattr(settings, 'DEFAULT_SITE_DOMAIN', 'localhost:8000')

    if Site in created_models:
        if verbosity >= 2:
            print 'Creating default Site object:\nname: %s\ndomain: %s' % (name, domain)
        s = Site(domain=domain, name=name)
        s.save(using=db)
    Site.objects.clear_cache()

if getattr(settings, 'CREATE_DEFAULT_SITE', False):
    # Disconnect original site creator.
    signals.post_syncdb.disconnect(
        orig_default_site,
        sender=site_app,
    )

    # Trigger default site creation.
    signals.post_syncdb.connect(
        create_default_site,
        sender=site_app,
        dispatch_uid='snippetscream._2536.create_default_site'
    )

########NEW FILE########
__FILENAME__ = _963
# http://djangosnippets.org/snippets/963/

from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIRequest
from django.test import Client


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
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        request = WSGIRequest(environ)

        # Add request.user.
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")

        return request

########NEW FILE########
__FILENAME__ = test_settings
DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'snippetscream',
]

ROOT_URLCONF = 'snippetscream.tests.urls'

CREATE_DEFAULT_SITE = True

########NEW FILE########
