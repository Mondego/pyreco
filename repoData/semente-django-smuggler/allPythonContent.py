__FILENAME__ = forms
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.
import django
from django.conf import settings
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.serializers import get_serializer_formats
from django.utils.translation import ugettext as _

if django.VERSION > (1, 3):
    ADMIN_MEDIA_PREFIX = 'admin/'
else:
    ADMIN_MEDIA_PREFIX = settings.ADMIN_MEDIA_PREFIX


class ImportFileForm(forms.Form):
    file = forms.FileField(
        label='File to load',
        help_text=_('Existing items with same <i>id</i> will be overwritten.'),
        required=True,
    )

    class Media:
        css = {
            'all': [''.join((ADMIN_MEDIA_PREFIX, 'css/forms.css'))]
        }

    def clean_file(self):
        data = self.cleaned_data['file']
        if not isinstance(data, InMemoryUploadedFile):
            return data
        file_format = data.name.split('.')[-1]
        if not file_format in get_serializer_formats():
            raise forms.ValidationError(_('Invalid file extension.'))
        return data

########NEW FILE########
__FILENAME__ = settings
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.

from django.conf import settings

SMUGGLER_EXCLUDE_LIST = getattr(settings, 'SMUGGLER_EXCLUDE_LIST', [])
SMUGGLER_FIXTURE_DIR = getattr(settings, 'SMUGGLER_FIXTURE_DIR', None)
SMUGGLER_FORMAT = getattr(settings, 'SMUGGLER_FORMAT', 'json') # json or xml
SMUGGLER_INDENT = getattr(settings, 'SMUGGLER_INDENT', 2)

########NEW FILE########
__FILENAME__ = signals
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.

from datetime import datetime
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from smuggler.settings import (SMUGGLER_FIXTURE_DIR, SMUGGLER_FORMAT,
                               SMUGGLER_INDENT)

def save_data_on_filesystem(sender, **kwargs):
    if not SMUGGLER_FIXTURE_DIR:
        raise ImproperlyConfigured('You need to specify SMUGGLER_FIXTURE_DIR in '
                                   'your Django settings file.')
    objects = sender._default_manager.all()
    app_label, model_label = sender._meta.app_label, sender._meta.module_name
    filename = '%s-%s_%s.%s' % (app_label, model_label,
                                datetime.now().isoformat(), SMUGGLER_FORMAT)
    fixture = file(SMUGGLER_FIXTURE_DIR + '/' + filename, 'w')
    serializers.serialize(SMUGGLER_FORMAT, objects, indent=SMUGGLER_INDENT,
                          stream=fixture)
    fixture.close()

########NEW FILE########
__FILENAME__ = urls
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.

try:
    from django.conf.urls import url, patterns
except ImportError:  # Django < 1.4
    from django.conf.urls.defaults import url, patterns
                            
from smuggler.views import (dump_data, dump_app_data, dump_model_data,
                            load_data)

dump_data_url = url(
    regex=r'^dump/$',
    view=dump_data,
    name='dump-data'
)

dump_app_data_url = url(
    regex=r'^(?P<app_label>\w+)/dump/$',
    view=dump_app_data,
    name='dump-app-data'
)

dump_model_data_url = url(
    regex=r'^(?P<app_label>\w+)/(?P<model_label>\w+)/dump/$',
    view=dump_model_data,
    name='dump-model-data'
)

load_data_url = url(
    regex=r'^load/$',
    view=load_data,
    name='load-data'
)

urlpatterns = patterns('', dump_model_data_url, dump_app_data_url,
                       dump_data_url, load_data_url)

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.

import os
import sys
from django.core import serializers
from django.core.management import CommandError
from django.core.management.color import no_style
from django.core.management.commands.dumpdata import Command as DumpData
from django.db import connections, transaction, router
from django.db.utils import DEFAULT_DB_ALIAS
from django.http import HttpResponse
from smuggler.settings import (SMUGGLER_FORMAT, SMUGGLER_INDENT)
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


def get_file_list(path):
    file_list = []
    for file_name in os.listdir(path):
        if not os.path.isdir(file_name):
            file_path = os.path.join(path, file_name)
            file_size = os.path.getsize(file_path)
            file_list.append((file_name, '%0.1f KB'%float(file_size/1024.0)))
    file_list.sort()
    return file_list


def save_uploaded_file_on_disk(uploaded_file, destination_path):
    destination = open(destination_path, 'w')
    for chunk in uploaded_file.chunks():
        destination.write(chunk)
    destination.close()


def serialize_to_response(app_labels=[], exclude=[], response=None,
                          format=SMUGGLER_FORMAT, indent=SMUGGLER_INDENT):
    response = response or HttpResponse(mimetype='text/plain')
    # There's some funky output redirecting going on as Django >= 1.5 writes
    # to a wrapped output stream, instead of just returning the dumped output.
    stream = StringIO()  # this is going to be our stdout
    # We need to fake an OutputWrapper as it's only introduced in Django 1.5
    out = lambda: None
    out.write = lambda s: stream.write(s)  # this seems to be sufficient.
    try:
        # Now make sys.stdout our wrapped StringIO instance and start the dump.
        sys.stdout = out
        dumpdata = DumpData()
        dumpdata.stdout = sys.stdout
        dumpdata.stderr = sys.stderr
        output = dumpdata.handle(*app_labels, **{
            'exclude': exclude,
            'format': format,
            'indent': indent,
            'show_traceback': True,
            'use_natural_keys': True
        })
    except CommandError:
        # We expect and re-raise CommandErrors, these contain "user friendly"
        # error messages.
        raise
    else:
        if output:
            response.write(output)
        else:
            response.write(stream.getvalue())
        return response
    finally:
        # Be nice and cleanup!
        sys.stdout = sys.__stdout__


def load_requested_data(data):
    """
    Load the given data dumps and return the number of imported objects.

    Wraps the entire action in a big transaction.

    """
    style = no_style()

    using = DEFAULT_DB_ALIAS
    connection = connections[using]
    cursor = connection.cursor()

    transaction.commit_unless_managed(using=using)
    transaction.enter_transaction_management(using=using)
    transaction.managed(True, using=using)
    
    models = set()
    counter = 0
    try:
        for format, stream in data:
            objects = serializers.deserialize(format, stream)
            for obj in objects:
                model = obj.object.__class__
                if router.allow_syncdb(using, model):
                    models.add(model)
                    counter += 1
                    obj.save(using=using)
        if counter > 0:
            sequence_sql = connection.ops.sequence_reset_sql(style, models)
            if sequence_sql:
                for line in sequence_sql:
                    cursor.execute(line)
    except Exception, e:
        transaction.rollback(using=using)
        transaction.leave_transaction_management(using=using)
        raise e
    transaction.commit(using=using)
    transaction.leave_transaction_management(using=using)
    connection.close()
    return counter

########NEW FILE########
__FILENAME__ = views
# Copyright (c) 2009 Guilherme Gondim and contributors
#
# This file is part of Django Smuggler.
#
# Django Smuggler is free software under terms of the GNU Lesser
# General Public License version 3 (LGPLv3) as published by the Free
# Software Foundation. See the file README for copying conditions.

import os
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from smuggler.forms import ImportFileForm
from smuggler.settings import (SMUGGLER_FORMAT, SMUGGLER_FIXTURE_DIR,
                               SMUGGLER_EXCLUDE_LIST)
from smuggler.utils import (get_file_list,
                            save_uploaded_file_on_disk, serialize_to_response,
                            load_requested_data)


def dump_to_response(request, app_label=None, exclude=[], filename_prefix=None):
    """Utility function that dumps the given app/model to an HttpResponse.
    """
    try:
        filename = '%s.%s' % (datetime.now().isoformat(), SMUGGLER_FORMAT)
        if filename_prefix:
            filename = '%s_%s' % (filename_prefix, filename)
        response = serialize_to_response(app_label and [app_label] or [], exclude)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response
    except CommandError, e:
        messages.add_message(request, messages.ERROR,
             _('An exception occurred while dumping data: %s' % unicode(e)))
    return HttpResponseRedirect(request.build_absolute_uri().split('dump')[0])


@user_passes_test(lambda u: u.is_superuser)
def dump_data(request):
    """Exports data from whole project.
    """
    return dump_to_response(request, exclude=SMUGGLER_EXCLUDE_LIST)


@user_passes_test(lambda u: u.is_superuser)
def dump_app_data(request, app_label):
    """Exports data from a application.
    """
    return dump_to_response(request, app_label, SMUGGLER_EXCLUDE_LIST,
                            app_label)


@user_passes_test(lambda u: u.is_superuser)
def dump_model_data(request, app_label, model_label):
    """Exports data from a model.
    """
    return dump_to_response(request, '%s.%s' % (app_label, model_label),
                            [], '-'.join((app_label, model_label)))


@user_passes_test(lambda u: u.is_superuser)
def load_data(request):
    """
    Load data from uploaded file or disk.

    Note: A uploaded file will be saved on `SMUGGLER_FIXTURE_DIR` if the submit
          button with name "_loadandsave" was pressed.
    """
    form = ImportFileForm()
    if request.method == 'POST':
        data = []
        if request.POST.has_key('_load') or request.POST.has_key('_loadandsave'):
            form = ImportFileForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = request.FILES['file']
                file_name = uploaded_file.name
                file_format = file_name.split('.')[-1]
                if request.POST.has_key('_loadandsave'):
                    destination_path = os.path.join(SMUGGLER_FIXTURE_DIR,
                                                    file_name)
                    save_uploaded_file_on_disk(uploaded_file, destination_path)
                    file_data = open(destination_path, 'r')
                elif uploaded_file.multiple_chunks():
                    file_data = open(uploaded_file.temporary_file_path(), 'r')
                else:
                    file_data = uploaded_file.read()
                data.append((file_format, file_data))
        elif request.POST.has_key('_loadfromdisk'):
            query_dict = request.POST.copy()        
            del(query_dict['_loadfromdisk'])
            del(query_dict['csrfmiddlewaretoken'])
            selected_files = query_dict.values()
            for file_name in selected_files:
                file_path = os.path.join(SMUGGLER_FIXTURE_DIR, file_name)
                file_format = file_name.split('.')[-1]
                file_data = open(file_path, 'r')
                data.append((file_format, file_data))
        if data:
            try:
                obj_count = load_requested_data(data)
                user_msg = ('%(obj_count)d object(s) from %(file_count)d file(s) '
                            'loaded with success.') # TODO: pluralize
                user_msg = _(user_msg) % {
                    'obj_count': obj_count,
                    'file_count': len(data)
                }
                messages.add_message(request, messages.INFO, user_msg)
            except (IntegrityError, ObjectDoesNotExist, DeserializationError), e:
                messages.add_message(request, messages.ERROR,
                    _(u'An exception occurred while loading data: %s')
                        % unicode(e))
    context = {
        'files_available': get_file_list(SMUGGLER_FIXTURE_DIR) \
            if SMUGGLER_FIXTURE_DIR else [],
        'smuggler_fixture_dir': SMUGGLER_FIXTURE_DIR,
        'import_file_form': form,
    }
    return render_to_response('smuggler/load_data_form.html', context,
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

import os.path
import sys

path, scriptname = os.path.split(__file__)

sys.path.append(os.path.abspath(path))
sys.path.append(os.path.abspath(os.path.join(path, '..')))

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'

from django.core import management

management.call_command('test', 'test_app')

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import re
import StringIO

from django.contrib.flatpages.models import FlatPage
from django.core.management import CommandError
from django.test import TestCase
from unittest2 import TestCase as TestCase2
from smuggler import utils


class BasicDumpTestCase(TestCase, TestCase2):
    SITE_DUMP = '{ "pk": 1, "model": "sites.site", "fields": { "domain": "example.com", "name": "example.com" } }'
    FLATPAGE_DUMP = '{ "pk": 1, "model": "flatpages.flatpage", "fields": { "registration_required": false, "title": "test", "url": "/", "template_name": "", "sites": [], "content": "", "enable_comments": false } }'
    BASIC_DUMP = '[ %s, %s ]' % (SITE_DUMP, FLATPAGE_DUMP)

    def setUp(self):
        f = FlatPage(url='/', title='test')
        f.save()

    def normalize(self, out):
        return re.sub(r'\s\s*', ' ', out).strip()

    def test_serialize_to_response(self):
        stream = StringIO.StringIO()
        utils.serialize_to_response(response=stream)
        out = self.normalize(stream.getvalue())
        self.assertEquals(out, self.BASIC_DUMP)

    def test_serialize_exclude(self):
        stream = StringIO.StringIO()
        utils.serialize_to_response(exclude=['sites'], response=stream)
        out = self.normalize(stream.getvalue())
        self.assertEquals(out, '[ %s ]' % self.FLATPAGE_DUMP)

    def test_serialize_include(self):
        stream = StringIO.StringIO()
        utils.serialize_to_response(app_labels=['sites'], response=stream)
        out = self.normalize(stream.getvalue())
        self.assertEquals(out, '[ %s ]' % self.SITE_DUMP)

    def test_serialize_unknown_app_fail(self):
        self.assertRaises(CommandError, utils.serialize_to_response, 'auth')

########NEW FILE########
__FILENAME__ = test_settings
# Haystack settings for running tests.
DATABASE_ENGINE = 'django.db.backends.sqlite3'
DATABASE_NAME = 'smuggler.db'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'smuggler.db'
    }
}

SECRET_KEY = 'mAtTzVPOV9JY4eJQfqgW8eAS9DWKnt3MkvvpQI2MzkhAz7z3'

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.flatpages',
    'smuggler',
    'test_app',
]

########NEW FILE########
