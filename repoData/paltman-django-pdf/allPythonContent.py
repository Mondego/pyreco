__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys, os
sys.path.append(os.path.abspath(os.curdir))
sys.path.append(os.path.abspath(os.pardir))
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

VERSION = __import__('pdf').__version__

extensions = ['sphinx.ext.autodoc']
templates_path = ['_templates']
source_suffix = '.txt'
master_doc = 'index'

project = u'django-pdf'
copyright = u'2010, Patrick Altman'
version = VERSION
release = VERSION

exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
html_last_updated_fmt = '%b %d, %Y'
htmlhelp_basename = 'django-pdfdoc'

latex_documents = [
  ('index', 'django-pdf.tex', u'django-pdf Documentation',
   u'Patrick Altman', 'manual'),
]

man_pages = [
    ('index', 'django-pdf', u'django-pdf Documentation',
     [u'Patrick Altman'], 1)
]

########NEW FILE########
__FILENAME__ = settings

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from pdf.models import Document


admin.site.register(Document)

########NEW FILE########
__FILENAME__ = forms
import os

from django import forms
from django.utils.translation import ugettext_lazy as _

from pdf.models import Document


class DocumentValidationError(forms.ValidationError):
    def __init__(self):
        msg = _(u'Only PDF files are valid uploads.')
        super(DocumentValidationError, self).__init__(msg)


class DocumentField(forms.FileField):
    """A validating PDF document upload field"""

    def clean(self, data, initial=None):
        f = super(DocumentField, self).clean(data, initial)
        ext = os.path.splitext(f.name)[1][1:].lower()
        if ext == 'pdf' and f.content_type == 'application/pdf':
            return f
        raise DocumentValidationError()


class DocumentForm(forms.ModelForm):
    local_document = DocumentField()

    class Meta:
        model = Document
        fields = ('name', 'local_document')

########NEW FILE########
__FILENAME__ = models
import os
import uuid
import simplejson

from datetime import datetime

import boto

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _


DOCUMENT_STATES = (
    ('U', _('Uploaded')),
    ('S', _('Stored Remotely')),
    ('Q', _('Queued')),
    ('P', _('Processing')),
    ('F', _('Finished')),
    ('E', _('Processing Error')))


DEFAULT_PATH = os.path.join(settings.MEDIA_ROOT, "uploads")
UPLOAD_PATH = getattr(settings, "PDF_UPLOAD_PATH", DEFAULT_PATH)


class Document(models.Model):
    """
    A simple model which stores data about an uploaded document.
    """
    user = models.ForeignKey(User, verbose_name=_('user'))
    name = models.CharField(_("Title"), max_length=100)
    uuid = models.CharField(_('Unique Identifier'), max_length=36)
    local_document = models.FileField(_("Local Document"), null=True, blank=True, upload_to=UPLOAD_PATH)
    remote_document = models.URLField(_("Remote Document"), null=True, blank=True)
    status = models.CharField(_("Remote Processing Status"), default='U', max_length=1, choices=DOCUMENT_STATES)
    exception = models.TextField(_("Processing Exception"), null=True, blank=True)
    pages = models.IntegerField(_("Number of Pages in Document"), null=True, blank=True)

    date_uploaded = models.DateTimeField(_("Date Uploaded"))
    date_stored = models.DateTimeField(_("Date Stored Remotely"), null=True, blank=True)
    date_queued = models.DateTimeField(_("Date Queued"), null=True, blank=True)
    date_process_start = models.DateTimeField(_("Date Process Started"), null=True, blank=True)
    date_process_end = models.DateTimeField(_("Date Process Completed"), null=True, blank=True)
    date_exception = models.DateTimeField(_("Date of Exception"), null=True, blank=True)

    date_created = models.DateTimeField(_("Date Created"), default=datetime.utcnow)

    class Meta:
        verbose_name = _('document')
        verbose_name_plural = _('documents')

    def __unicode__(self):
        return unicode(_("%s's uploaded document." % self.user))

    def get_detail_url(self):
        return reverse("pdf_detail", kwargs={'uuid': self.uuid})

    @property
    def page_images(self):
        if self.remote_document is None:
            return []
        base = self.remote_document.replace(os.path.basename(self.remote_document), '')
        images = []
        if self.pages == 1:
            images = ["%spage.png" % base, ]
        if self.pages > 1:
            images = ["%spage-%s.png" % (base, x) for x in range(0, self.pages)]
        return images

    def save(self, **kwargs):
        if self.id is None:
            self.uuid = str(uuid.uuid4())
        super(Document, self).save(**kwargs)

    @staticmethod
    def process_response(data):
        c = boto.connect_s3(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET)
        key = c.get_bucket(data['bucket']).get_key(data['key'])
        if key is not None:
            response_data = simplejson.loads(key.get_contents_as_string())
            doc = Document.objects.get(uuid=response_data['uuid'])
            status = response_data['status']
            now = response_data.get("now", None)
            if now is not None:
                now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
            if status == 'E':
                doc.status = "E"
                doc.exception = response_data.get('exception', None)
                doc.date_exception = now
            if status == 'F':
                if doc.status != 'E':
                    doc.status = 'F'
                doc.date_process_end = now
                doc.pages = response_data.get("pages", None)
            if status == 'P':
                if doc.status not in ('E', 'F'):
                    doc.status = 'P'
                doc.date_process_start = now
            doc.save()
            return True
        return False

########NEW FILE########
__FILENAME__ = tasks
import os
import simplejson

from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings

import boto

from celery.decorators import task
from celery.task import PeriodicTask

from pdf.models import Document


BOOTSTRAP_SCRIPT = """#!/bin/bash
apt-get update
apt-get install -y imagemagick

python -c "import os
import json

from datetime import datetime
from subprocess import Popen, PIPE
from time import sleep
from uuid import uuid4

import boto

KEY = '%(KEY)s'
SECRET = '%(SECRET)s'

request_queue = boto.connect_sqs(KEY, SECRET).create_queue('%(REQUEST_QUEUE)s')
response_queue = boto.connect_sqs(KEY, SECRET).create_queue('%(RESPONSE_QUEUE)s')
count = 0


def read_json_pointer_message():
    m = request_queue.read(3600) # Give the job an hour to run, plenty of time to avoid double-runs
    if m is not None:
        pointer = json.loads(m.get_body())
        k = boto.connect_s3(KEY, SECRET).get_bucket(pointer['bucket']).get_key(pointer['key'])
        data = json.loads(k.get_contents_as_string())
        data['pointer'] = m
        return data

def delete_json_pointer_message(data):
    request_queue.delete_message(data['pointer'])

def write_json_pointer_message(data, bucket, key_name, base_key):
    b = boto.connect_s3(KEY, SECRET).get_bucket(bucket)
    k = b.new_key(base_key.replace(os.path.basename(base_key), key_name))
    k.set_contents_from_string(json.dumps(data))
    response_message = {'bucket': b.name, 'key': k.name}
    message = response_queue.new_message(body=json.dumps(response_message))
    response_queue.write(message)

def download(bucket, key, local_file):
    b = boto.connect_s3(KEY, SECRET).get_bucket(bucket)
    k = b.get_key(key)
    k.get_contents_to_filename(local_file)

def upload_file(local_file, bucket, key, public=False):
    b = boto.connect_s3(KEY, SECRET).get_bucket(bucket)
    k = b.new_key(key)
    k.set_contents_from_filename(local_file)
    if public:
        k.set_acl('public-read')

def get_tstamp():
    return datetime.utcnow().isoformat(' ').split('.')[0]


while True:
    request_data = read_json_pointer_message()
    start = get_tstamp()
    if request_data is None:
        count += 1
        if count > 10:
            break
        else:
            sleep(5)
    else:
        RUN_ID = str(uuid4())
        WORKING_PATH = '/mnt/' + RUN_ID
        try:
            os.makedirs(WORKING_PATH)
        except:
            pass
        count = 0
        try:
            try:
                bname = request_data['bucket']
                kname = request_data['key']
                doc_uuid = request_data['uuid']
                local_filename = os.path.join(WORKING_PATH, os.path.basename(kname))
                output = os.path.join(WORKING_PATH, 'page.png')
                cmd = 'convert -density 400 ' + local_filename + ' ' + output

                start_data = {'status': 'P', 'uuid': doc_uuid, 'now': start}
                write_json_pointer_message(start_data, bucket=bname, key_name='start.json', base_key=kname)
                download(bname, kname, local_filename)
                p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
                rc = p.wait()
                images = [f for f in os.listdir(WORKING_PATH) if f.endswith('png')]
                for image in images:
                    new_key_name = kname.replace(os.path.basename(kname), image)
                    local_image = os.path.join(WORKING_PATH, image)
                    upload_file(local_image, bname, new_key_name, public=True)
                data = {'status': 'F', 'uuid': doc_uuid, 'pages': len(images), 'now': get_tstamp()}
                write_json_pointer_message(data, bucket=bname, key_name='results.json', base_key=kname)
            except:
                import sys, traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                e = traceback.format_exception(exc_type, exc_value, exc_traceback)
                e = ''.join(e)
                data = {'status': 'E', 'uuid': doc_uuid, 'exception': str(e), 'now': get_tstamp()}
                write_json_pointer_message(data, bucket=bname, key_name='error.json', base_key=kname)
        except Exception, e:
            pass
        delete_json_pointer_message(request_data)
"

/sbin/shutdown now -h
"""


REQUEST_QUEUE = getattr(settings, "PDF_REQUEST_QUEUE", "pdf_requests")
RESPONSE_QUEUE = getattr(settings, "PDF_RESPONSE_QUEUE", "pdf_responses")
ACL = getattr(settings, "PDF_AWS_ACL", "public-read")
AMI_ID = getattr(settings, "PDF_AMI_ID", "ami-bb709dd2")
KEYPAIR = getattr(settings, "PDF_KEYPAIR_NAME", None)
MAX_INSTANCES = getattr(settings, 'PDF_MAX_NODES', 20)
SECURITY_GROUPS = getattr(settings, 'PDF_SECURITY_GROUPS', None)


def queue_json_message(doc, doc_key):
    key_name = doc_key.name.replace(os.path.basename(doc_key.name), "message-%s.json" % str(uuid4()))
    key = doc_key.bucket.new_key(key_name)
    message_data = simplejson.dumps({'bucket': doc_key.bucket.name, 'key': doc_key.name, 'uuid': doc.uuid})
    key.set_contents_from_string(message_data)
    msg_body = {'bucket': key.bucket.name, 'key': key.name}
    queue = boto.connect_sqs(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET).create_queue(REQUEST_QUEUE)
    msg = queue.new_message(body=simplejson.dumps(msg_body))
    queue.write(msg)


def upload_file_to_s3(doc):
    file_path = doc.local_document.path
    b = boto.connect_s3(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET).get_bucket(settings.PDF_UPLOAD_BUCKET)
    name = '%s/%s' % (doc.uuid, os.path.basename(file_path))
    k = b.new_key(name)
    k.set_contents_from_filename(file_path)
    k.set_acl(ACL)
    return k


@task
def process_file(doc):
    """Transfer uploaded file to S3 and queue up message to process PDF."""
    key = upload_file_to_s3(doc)
    doc.remote_document = "http://%s.s3.amazonaws.com/%s" % (key.bucket.name, key.name)
    doc.date_stored = datetime.utcnow()
    doc.status = 'S'
    doc.save()

    queue_json_message(doc, key)
    doc.status = 'Q'
    doc.date_queued = datetime.utcnow()
    doc.save()

    return True


class CheckResponseQueueTask(PeriodicTask):
    """
    Checks response queue for messages returned from running processes in the
    cloud.  The messages are read and corresponding `pdf.models.Document`
    records are updated.
    """
    run_every = timedelta(seconds=30)

    def _dequeue_json_message(self):
        sqs = boto.connect_sqs(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET)
        queue = sqs.create_queue(RESPONSE_QUEUE)
        msg = queue.read()
        if msg is not None:
            data = simplejson.loads(msg.get_body())
            bucket = data.get('bucket', None)
            key = data.get("key", None)
            queue.delete_message(msg)
            if bucket is not None and key is not None:
                return data

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info("Running periodic task!")
        data = self._dequeue_json_message()
        if data is not None:
            Document.process_response(data)
            return True
        return False


class CheckQueueLevelsTask(PeriodicTask):
    """
    Checks the number of messages in the queue and compares it with the number
    of instances running, only booting nodes if the number of queued messages
    exceed the number of nodes running.
    """
    run_every = timedelta(seconds=60)

    def run(self, **kwargs):
        ec2 = boto.connect_ec2(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET)
        sqs = boto.connect_sqs(settings.PDF_AWS_KEY, settings.PDF_AWS_SECRET)

        queue = sqs.create_queue(REQUEST_QUEUE)
        num = queue.count()
        launched = 0
        icount = 0

        reservations = ec2.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                if instance.state == "running" and instance.image_id == AMI_ID:
                    icount += 1
        to_boot = min(num - icount, MAX_INSTANCES)

        if to_boot > 0:
            startup = BOOTSTRAP_SCRIPT % {
                'KEY': settings.PDF_AWS_KEY,
                'SECRET': settings.PDF_AWS_SECRET,
                'RESPONSE_QUEUE': RESPONSE_QUEUE,
                'REQUEST_QUEUE': REQUEST_QUEUE}
            r = ec2.run_instances(
                image_id=AMI_ID,
                min_count=to_boot,
                max_count=to_boot,
                key_name=KEYPAIR,
                security_groups=SECURITY_GROUPS,
                user_data=startup)
            launched = len(r.instances)
        return launched

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from pdf.views import doc_detail
from pdf.views import doc_list
from pdf.views import doc_upload


urlpatterns = patterns('',
    url(r'^$', doc_list, name='pdf_list'),
    url(r'^upload/$', doc_upload, name='pdf_upload'),
    url(r'^(?P<uuid>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/$', doc_detail, name='pdf_detail'),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from pdf.forms import DocumentForm
from pdf.tasks import process_file
from pdf.models import Document


@login_required
def doc_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.date_uploaded = datetime.utcnow()
            doc.save()
            process_file.delay(doc)
            return HttpResponseRedirect(reverse('pdf_list'))
    else:
        form = DocumentForm()
    return render_to_response('pdf/upload.html', {'form': form}, context_instance=RequestContext(request))


@login_required
def doc_list(request):
    context = {'pdfs': Document.objects.filter(user=request.user)}
    return render_to_response('pdf/list.html', context, context_instance=RequestContext(request))


@login_required
def doc_detail(request, uuid):
    context = {'pdf': Document.objects.get(uuid=uuid)}
    return render_to_response('pdf/detail.html', context, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3", # Add "postgresql_psycopg2", "postgresql", "mysql", "sqlite3" or "oracle".
        "NAME": "dev.db",                       # Or path to database file if using sqlite3.
        "USER": "",                             # Not used with sqlite3.
        "PASSWORD": "",                         # Not used with sqlite3.
        "HOST": "",                             # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "",                             # Set to empty string for default. Not used with sqlite3.
    }
}

ROOT_URLCONF = 'sample.urls'
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/media/'
SECRET_KEY = ''

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATE_DIRS = (
    ('%s/templates' % (os.path.dirname(__file__)))
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    
    # apps for this sample project
    "ghettoq",
    'celery',
    'pdf'
)

# pdf app settings
PDF_UPLOAD_BUCKET = ''       # Where the documents should be uploaded to
PDF_AWS_KEY = ''             # AWS Key for accessing Bootstrap Bucket and Queues
PDF_AWS_SECRET = ''          # AWS Secret Key for accessing Bootstrap Bucket and Queues

CARROT_BACKEND = "ghettoq.taproot.Database"
CELERY_RESULT_BACKEND = "amqp"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

from pdf import urls as pdf_urls


admin.autodiscover()

urlpatterns = patterns('',
    (r'^docs/', include(pdf_urls)),
    
    # Default login url
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
