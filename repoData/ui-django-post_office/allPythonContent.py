__FILENAME__ = admin
from django.contrib import admin
from django.utils.text import Truncator

from .models import Email, Log, EmailTemplate


def get_message_preview(instance):
    return (u'{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)

get_message_preview.short_description = 'Message'


class LogInline(admin.StackedInline):
    model = Log
    extra = 0


class EmailAdmin(admin.ModelAdmin):
    list_display = ('to', 'subject', get_message_preview, 'status', 'last_updated')
    inlines = [LogInline]


def to(instance):
    return instance.email.to


class LogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'status', get_message_preview)


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_shortened', 'subject', 'created')
    search_fields = ('name', 'description', 'subject')
    fieldsets = [
        (None, {
            'fields': ('name', 'description'),
        }),
        ('Email', {
            'fields': ('subject', 'content', 'html_content'),
        }),
    ]

    def description_shortened(self, instance):
        return Truncator(instance.description.split('\n')[0]).chars(200)
    description_shortened.short_description = 'description'
    description_shortened.admin_order_field = 'description'


admin.site.register(Email, EmailAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)

########NEW FILE########
__FILENAME__ = backends
from django.core.files.base import ContentFile
from django.core.mail.backends.base import BaseEmailBackend

from .mail import create
from .settings import get_default_priority
from .utils import create_attachments


class EmailBackend(BaseEmailBackend):

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        """
        Queue one or more EmailMessage objects and returns the number of
        email messages sent.
        """
        if not email_messages:
            return

        for email in email_messages:
            subject = email.subject
            from_email = email.from_email
            message = email.body
            headers = email.extra_headers

            # Check whether email has 'text/html' alternative
            alternatives = getattr(email, 'alternatives', ())
            for alternative in alternatives:
                if alternative[1] == 'text/html':
                    html_message = alternative[0]
                    break
            else:
                html_message = ''

            attachment_files = dict([(name, ContentFile(content))
                                    for name, content, _ in email.attachments])

            emails = [create(sender=from_email, recipient=recipient, subject=subject,
                             message=message, html_message=html_message, headers=headers)
                      for recipient in email.to]

            if attachment_files:
                attachments = create_attachments(attachment_files)

                for email in emails:
                    email.attachments.add(*attachments)

            if get_default_priority() == 'now':
                for email in emails:
                    email.dispatch()

########NEW FILE########
__FILENAME__ = cache
from django.core.cache import get_cache
from django.template.defaultfilters import slugify

from .settings import get_cache_backend

# Stripped down version of caching functions from django-dbtemplates
# https://github.com/jezdez/django-dbtemplates/blob/develop/dbtemplates/utils/cache.py
cache_backend = get_cache_backend()


def get_cache_key(name):
    """
    Prefixes and slugify the key name
    """
    return 'post_office:template:%s' % (slugify(name))


def set(name, content):
    return cache_backend.set(get_cache_key(name), content)


def get(name):
    return cache_backend.get(get_cache_key(name))


def delete(name):
    return cache_backend.delete(get_cache_key(name))

########NEW FILE########
__FILENAME__ = compat
from django.utils import importlib
import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


if PY3:
    string_types = str
    text_type = str
else:
    string_types = basestring
    text_type = unicode


# Django 1.4 doesn't have ``import_string`` or ``import_by_path``
def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)

########NEW FILE########
__FILENAME__ = lockfile
# This module is taken from https://gist.github.com/ionrock/3015700

# A file lock implementation that tries to avoid platform specific
# issues. It is inspired by a whole bunch of different implementations
# listed below.

#  - https://bitbucket.org/jaraco/yg.lockfile/src/6c448dcbf6e5/yg/lockfile/__init__.py
#  - http://svn.zope.org/zc.lockfile/trunk/src/zc/lockfile/__init__.py?rev=121133&view=markup
#  - http://stackoverflow.com/questions/489861/locking-a-file-in-python
#  - http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/
#  - http://packages.python.org/lockfile/lockfile.html

# There are some tests below and a blog posting conceptually the
# problems I wanted to try and solve. The tests reflect these ideas.

#  - http://ionrock.wordpress.com/2012/06/28/file-locking-in-python/

# I'm not advocating using this package. But if you do happen to try it
# out and have suggestions please let me know.

import os
import time


class FileLocked(Exception):
    pass


class FileLock(object):

    def __init__(self, lock_filename, timeout=None, force=False):
        self.lock_filename = '%s.lock' % lock_filename
        self.timeout = timeout
        self.force = force
        self._pid = str(os.getpid())
        # Store pid in a file in the same directory as desired lockname
        self.pid_filename = os.path.join(
            os.path.dirname(self.lock_filename),
            self._pid,
        ) + '.lock'

    def get_lock_pid(self):
        try:
            return int(open(self.lock_filename).read())
        except IOError:
            # If we can't read symbolic link, there are two possibilities:
            # 1. The symbolic link is dead (point to non existing file)
            # 2. Symbolic link is not there
            # In either case, we can safely release the lock
            self.release()

    def valid_lock(self):
        """
        See if the lock exists and is left over from an old process.
        """

        lock_pid = self.get_lock_pid()

        # If we're unable to get lock_pid
        if lock_pid is None:
            return False

        # this is our process
        if self._pid == lock_pid:
            return True

        # it is/was another process
        # see if it is running
        try:
            os.kill(lock_pid, 0)
        except OSError:
            os.unlink(self.lock_filename)
            os.remove(self.pid_filename)
            return False

        # it is running
        return True

    def is_locked(self, force=False):
        # We aren't locked
        if not self.valid_lock():
            return False

        # We are locked, but we want to force it without waiting
        if not self.timeout:
            if self.force:
                self.release()
                return False
            else:
                # We're not waiting or forcing the lock
                raise FileLocked()

        # Locked, but want to wait for an unlock
        interval = .1
        intervals = int(self.timeout / interval)

        while intervals:
            if self.valid_lock():
                intervals -= 1
                time.sleep(interval)
                #print('stopping %s' % intervals)
            else:
                return True

        # check one last time
        if self.valid_lock():
            if self.force:
                self.release()
            else:
                # still locked :(
                raise FileLocked()

    def acquire(self):
        """Create a pid filename and create a symlink (the actual lock file)
        across platforms that points to it. Symlink is used because it's an
        atomic operation across platforms.
        """

        pid_file = os.open(self.pid_filename, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(pid_file, str(os.getpid()).encode('utf-8'))
        os.close(pid_file)
        os.symlink(self.pid_filename, self.lock_filename)

    def release(self):
        """Try to delete the lock files. Doesn't matter if we fail"""
        try:
            os.unlink(self.lock_filename)
        except OSError:
            pass
        try:
            os.remove(self.pid_filename)
        except OSError:
            pass

    def __enter__(self):
        if not self.is_locked():
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

########NEW FILE########
__FILENAME__ = logutils
import logging

from django.utils.log import dictConfig


# Taken from https://github.com/nvie/rq/blob/master/rq/logutils.py
def setup_loghandlers(level=None):
    # Setup logging for post_office if not already configured
    logger = logging.getLogger('post_office')
    if not logger.handlers:
        dictConfig({
            "version": 1,
            "disable_existing_loggers": False,

            "formatters": {
                "post_office": {
                    "format": "[%(levelname)s]%(asctime)s PID %(process)d: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },

            "handlers": {
                "post_office": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "post_office"
                },
            },

            "loggers": {
                "post_office": {
                    "handlers": ["post_office"],
                    "level": level or "DEBUG"
                }
            }
        })
    return logger

########NEW FILE########
__FILENAME__ = mail
import sys

from multiprocessing import Pool

from django.conf import settings
from django.core.mail import get_connection
from django.db import connection as db_connection
from django.db.models import Q
from django.template import Context, Template

from .compat import string_types
from .models import Email, EmailTemplate, PRIORITY, STATUS
from .settings import get_batch_size, get_email_backend, get_default_priority
from .utils import get_email_template, split_emails, create_attachments
from .logutils import setup_loghandlers

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    import datetime
    now = datetime.datetime.now


logger = setup_loghandlers("INFO")


def parse_priority(priority):
    if priority is None:
        priority = get_default_priority()
    # If priority is given as a string, returns the enum representation
    if isinstance(priority, string_types):
        priority = getattr(PRIORITY, priority, None)

        if priority is None:
            raise ValueError('Invalid priority, must be one of: %s' %
                             ', '.join(PRIORITY._fields))
    return priority


def create(sender, recipient, subject='', message='', html_message='',
           context=None, scheduled_time=None, headers=None, template=None,
           priority=None, render_on_delivery=False, commit=True):
    """
    Creates an email from supplied keyword arguments. If template is
    specified, email subject and content will be rendered during delivery.
    """
    priority = parse_priority(priority)
    status = None if priority == PRIORITY.now else STATUS.queued

    if context is None:
        context = ''

    # If email is to be rendered during delivery, save all necessary
    # information
    if render_on_delivery:
        email = Email(
            from_email=sender, to=recipient,
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
            context=context, template=template
        )

    else:

        if template:
            subject = template.subject
            message = template.content
            html_message = template.html_content

        if context:
            _context = Context(context)
            subject = Template(subject).render(_context)
            message = Template(message).render(_context)
            html_message = Template(html_message).render(_context)

        email = Email(
            from_email=sender, to=recipient,
            subject=subject,
            message=message,
            html_message=html_message,
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
        )

    if commit:
        email.save()

    return email


def send(recipients, sender=None, template=None, context={}, subject='',
         message='', html_message='', scheduled_time=None, headers=None,
         priority=None, attachments=None, render_on_delivery=False,
         log_level=2, commit=True):

    if not isinstance(recipients, (tuple, list)):
        raise ValueError('Recipient emails must be in list/tuple format')

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    priority = parse_priority(priority)
    if not commit:
        if priority == PRIORITY.now:
            raise ValueError("send_many() can't be used to send emails with priority = 'now'")
        if attachments:
            raise ValueError("Can't add attachments with send_many()")

    if template:
        if subject:
            raise ValueError('You can\'t specify both "template" and "subject" arguments')
        if message:
            raise ValueError('You can\'t specify both "template" and "message" arguments')
        if html_message:
            raise ValueError('You can\'t specify both "template" and "html_message" arguments')

        # template can be an EmailTemplate instance or name
        if isinstance(template, EmailTemplate):
            template = template
        else:
            template = get_email_template(template)

    emails = [create(sender, recipient, subject, message, html_message,
                     context, scheduled_time, headers, template, priority,
                     render_on_delivery, commit=commit)
              for recipient in recipients]

    if attachments:
        attachments = create_attachments(attachments)
        for email in emails:
            email.attachments.add(*attachments)

    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch(log_level=log_level)

    return emails


def send_many(kwargs_list):
    """
    Similar to mail.send(), but this function accepts a list of kwargs.
    Internally, it uses Django's bulk_create command for efficiency reasons.
    Currently send_many() can't be used to send emails with priority = 'now'.
    """
    emails = []
    for kwargs in kwargs_list:
        emails.extend(send(commit=False, **kwargs))
    Email.objects.bulk_create(emails)


def get_queued():
    """
    Returns a list of emails that should be sent:
     - Status is queued
     - Has scheduled_time lower than the current time or None
    """
    return Email.objects.filter(status=STATUS.queued) \
        .select_related('template') \
        .filter(Q(scheduled_time__lte=now()) | Q(scheduled_time=None)) \
        .order_by('-priority').prefetch_related('attachments')[:get_batch_size()]


def send_queued(processes=1, log_level=2):
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    queued_emails = get_queued()
    total_sent, total_failed = 0, 0
    total_email = len(queued_emails)

    logger.info('Started sending %s emails with %s processes.' %
                (total_email, processes))

    if queued_emails:

        # Don't use more processes than number of emails
        if total_email < processes:
            processes = total_email

        if processes == 1:
            total_sent, total_failed = _send_bulk(queued_emails,
                                                  uses_multiprocessing=False,
                                                  log_level=log_level)
        else:
            email_lists = split_emails(queued_emails, processes)
            pool = Pool(processes)
            results = pool.map(_send_bulk, email_lists)
            total_sent = sum([result[0] for result in results])
            total_failed = sum([result[1] for result in results])
    message = '%s emails attempted, %s sent, %s failed' % (
        total_email,
        total_sent,
        total_failed
    )
    logger.info(message)
    return (total_sent, total_failed)


def _send_bulk(emails, uses_multiprocessing=True, log_level=2):
    # Multiprocessing does not play well with database connection
    # Fix: Close connections on forking process
    # https://groups.google.com/forum/#!topic/django-users/eCAIY9DAfG0
    if uses_multiprocessing:
        db_connection.close()
    sent_count, failed_count = 0, 0
    email_count = len(emails)
    logger.info('Process started, sending %s emails' % email_count)

    # Try to open a connection, if we can't just pass in None as connection
    try:
        connection = get_connection(get_email_backend())
        connection.open()
    except Exception:
        connection = None

    try:
        for email in emails:
            status = email.dispatch(connection, log_level)
            if status == STATUS.sent:
                sent_count += 1
                logger.debug('Successfully sent email #%d' % email.id)
            else:
                failed_count += 1
                logger.debug('Failed to send email #%d' % email.id)
    except Exception as e:
        logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})

    if connection:
        connection.close()

    logger.info('Process finished, %s emails attempted, %s sent, %s failed' %
               (email_count, sent_count, failed_count))

    return (sent_count, failed_count)

########NEW FILE########
__FILENAME__ = cleanup_mail
import datetime
from optparse import make_option

from django.core.management.base import BaseCommand

from ...models import Email


try:
    from django.utils.timezone import now
    now = now
except ImportError:
    now = datetime.now


class Command(BaseCommand):
    help = 'Place deferred messages back in the queue.'
    option_list = BaseCommand.option_list + (
        make_option('-d', '--days', type='int', default=90,
            help="Cleanup mails older than this many days, defaults to 90."),
    )

    def handle(self, verbosity, days, **options):
        # Delete mails and their related logs and queued created before X days

        cutoff_date = now() - datetime.timedelta(days)
        count = Email.objects.filter(created__lt=cutoff_date).count()
        Email.objects.only('id').filter(created__lt=cutoff_date).delete()
        print("Deleted {0} mails created before {1} ".format(count, cutoff_date))
########NEW FILE########
__FILENAME__ = send_queued_mail
import tempfile
import sys
from optparse import make_option

from django.core.management.base import BaseCommand

from ...lockfile import FileLock, FileLocked
from ...mail import send_queued
from ...logutils import setup_loghandlers


logger = setup_loghandlers()
default_lockfile = tempfile.gettempdir() + "/post_office"


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--processes', type='int',
                    help='Number of processes used to send emails', default=1),
        make_option('-L', '--lockfile', type='string', default=default_lockfile,
                    help='Absolute path of lockfile to acquire'),
        make_option('-l', '--log-level', type='int', default=2,
                    help='"0" to log nothing, "1" to log errors'),
    )

    def handle(self, *args, **options):
        logger.info('Acquiring lock for sending queued emails at %s.lock' %
                    options['lockfile'])
        try:
            with FileLock(options['lockfile']):
                try:
                    send_queued(options['processes'], options['log_level'])
                except Exception as e:
                    logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
                    raise
        except FileLocked:
            logger.info('Failed to acquire lock, terminating now.')

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Email'
        db.create_table('post_office_email', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('from_email', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('to', self.gf('django.db.models.fields.EmailField')(max_length=254)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('html_message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True, null=True, blank=True)),
            ('priority', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0), db_index=True)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
        ))
        db.send_create_signal('post_office', ['Email'])

        # Adding model 'Log'
        db.create_table('post_office_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(related_name='logs', to=orm['post_office.Email'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0), db_index=True)),
            ('status', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('post_office', ['Log'])

        # Adding model 'EmailTemplate'
        db.create_table('post_office_emailtemplate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('html_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0))),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0))),
        ))
        db.send_create_signal('post_office', ['EmailTemplate'])


    def backwards(self, orm):
        # Deleting model 'Email'
        db.delete_table('post_office_email')

        # Deleting model 'Log'
        db.delete_table('post_office_log')

        # Deleting model 'EmailTemplate'
        db.delete_table('post_office_emailtemplate')


    models = {
        'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)', 'db_index': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)', 'db_index': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['post_office.Email']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_emailtemplate_last_updated__chg_field_emailtemplate_cr
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'EmailTemplate.last_updated'
        db.alter_column('post_office_emailtemplate', 'last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # Changing field 'EmailTemplate.created'
        db.alter_column('post_office_emailtemplate', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # Changing field 'Log.date'
        db.alter_column('post_office_log', 'date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # Changing field 'Email.created'
        db.alter_column('post_office_email', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

    def backwards(self, orm):

        # Changing field 'EmailTemplate.last_updated'
        db.alter_column('post_office_emailtemplate', 'last_updated', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'EmailTemplate.created'
        db.alter_column('post_office_emailtemplate', 'created', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'Log.date'
        db.alter_column('post_office_log', 'date', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'Email.created'
        db.alter_column('post_office_email', 'created', self.gf('django.db.models.fields.DateTimeField')())

    models = {
        'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['post_office.Email']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_email_headers
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Email.headers'
        db.add_column(u'post_office_email', 'headers',
                      self.gf('jsonfield.fields.JSONField')(default={}),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Email.headers'
        db.delete_column(u'post_office_email', 'headers')


    models = {
        u'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_email_scheduled_at__chg_field_email_headers
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Email.scheduled_time'
        db.add_column(u'post_office_email', 'scheduled_time',
                      self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True),
                      keep_default=False)


        # Changing field 'Email.headers'
        db.alter_column(u'post_office_email', 'headers', self.gf('jsonfield.fields.JSONField')(null=True))

    def backwards(self, orm):
        # Deleting field 'Email.scheduled_time'
        db.delete_column(u'post_office_email', 'scheduled_time')


        # Changing field 'Email.headers'
        db.alter_column(u'post_office_email', 'headers', self.gf('jsonfield.fields.JSONField')())

    models = {
        u'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0005_auto__add_attachment
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Attachment'
        db.create_table(u'post_office_attachment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'post_office', ['Attachment'])

        # Adding M2M table for field emails on 'Attachment'
        m2m_table_name = db.shorten_name(u'post_office_attachment_emails')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('attachment', models.ForeignKey(orm[u'post_office.attachment'], null=False)),
            ('email', models.ForeignKey(orm[u'post_office.email'], null=False))
        ))
        db.create_unique(m2m_table_name, ['attachment_id', 'email_id'])


    def backwards(self, orm):
        # Deleting model 'Attachment'
        db.delete_table(u'post_office_attachment')

        # Removing M2M table for field emails on 'Attachment'
        db.delete_table(db.shorten_name(u'post_office_attachment_emails'))


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'attachments'", 'symmetrical': 'False', 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_emailtemplate_description
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'EmailTemplate.description'
        db.add_column(u'post_office_emailtemplate', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'EmailTemplate.description'
        db.delete_column(u'post_office_emailtemplate', 'description')


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'attachments'", 'symmetrical': 'False', 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_email_template__add_field_email_context
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Email.template'
        db.add_column(u'post_office_email', 'template',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['post_office.EmailTemplate'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Email.context'
        db.add_column(u'post_office_email', 'context',
                      self.gf('jsonfield.fields.JSONField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Email.template'
        db.delete_column(u'post_office_email', 'template_id')

        # Deleting field 'Email.context'
        db.delete_column(u'post_office_email', 'context')


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'attachments'", 'symmetrical': 'False', 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'object_name': 'Email'},
            'context': ('jsonfield.fields.JSONField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['post_office.EmailTemplate']", 'null': 'True', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = 0008_auto__del_index_log_date__del_index_log_status__del_index_email_priori
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing index on 'Log', fields ['date']
        db.delete_index(u'post_office_log', ['date'])

        # Removing index on 'Log', fields ['status']
        db.delete_index(u'post_office_log', ['status'])

        # Removing index on 'Email', fields ['priority']
        db.delete_index(u'post_office_email', ['priority'])


    def backwards(self, orm):
        # Adding index on 'Email', fields ['priority']
        db.create_index(u'post_office_email', ['priority'])

        # Adding index on 'Log', fields ['status']
        db.create_index(u'post_office_log', ['status'])

        # Adding index on 'Log', fields ['date']
        db.create_index(u'post_office_log', ['date'])


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'attachments'", 'symmetrical': 'False', 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'object_name': 'Email'},
            'context': ('jsonfield.fields.JSONField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['post_office.EmailTemplate']", 'null': 'True', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        }
    }

    complete_apps = ['post_office']
########NEW FILE########
__FILENAME__ = models
import sys
import warnings
from uuid import uuid4

from collections import namedtuple

from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.db import models

try:
    from django.utils.encoding import smart_text # For Django >= 1.5
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from django.template import Context, Template

from jsonfield import JSONField
from post_office import cache
from .compat import text_type
from .settings import get_email_backend, context_field_class
from .validators import validate_email_with_name, validate_template_syntax


PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


# TODO: This will be deprecated, replaced by mail.from_template
class EmailManager(models.Manager):
    def from_template(self, from_email, to_email, template,
                      context={}, priority=PRIORITY.medium):
        warnings.warn(
            "`Email.objects.from_template()` is deprecated and will be removed "
            "in a future relase. Use `post_office.mail.from_template` instead.",
            DeprecationWarning)

        status = None if priority == PRIORITY.now else STATUS.queued
        context = Context(context)
        template_content = Template(template.content)
        template_content_html = Template(template.html_content)
        template_subject = Template(template.subject)
        return Email.objects.create(
            from_email=from_email, to=to_email,
            subject=template_subject.render(context),
            message=template_content.render(context),
            html_message=template_content_html.render(context),
            priority=priority, status=status
        )


class Email(models.Model):
    """
    A model to hold email information.
    """

    PRIORITY_CHOICES = [(PRIORITY.low, 'low'), (PRIORITY.medium, 'medium'),
                        (PRIORITY.high, 'high'), (PRIORITY.now, 'now')]
    STATUS_CHOICES = [(STATUS.sent, 'sent'), (STATUS.failed, 'failed'), (STATUS.queued, 'queued')]

    from_email = models.CharField(max_length=254, validators=[validate_email_with_name])
    to = models.EmailField(max_length=254)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    html_message = models.TextField(blank=True)
    """
    Emails having 'queued' status will get processed by ``send_all`` command.
    This status field will then be set to ``failed`` or ``sent`` depending on
    whether it's successfully delivered.
    """
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, db_index=True,
                                              blank=True, null=True)
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES,
                                                blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(blank=True, null=True, db_index=True)
    headers = JSONField(blank=True, null=True)
    template = models.ForeignKey('post_office.EmailTemplate', blank=True, null=True)
    context = context_field_class(blank=True)

    objects = EmailManager()

    def __unicode__(self):
        return self.to

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object
        from a ``Message`` instance, depending on whether html_message is empty.
        """
        subject = smart_text(self.subject)

        if self.template is not None:
            _context = Context(self.context)
            subject = Template(self.template.subject).render(_context)
            message = Template(self.template.content).render(_context)
            html_message = Template(self.template.html_content).render(_context)
        else:
            subject = self.subject
            message = self.message
            html_message = self.html_message
        
        if html_message:
            msg = EmailMultiAlternatives(subject, message, self.from_email,
                                         [self.to], connection=connection,
                                         headers=self.headers)
            msg.attach_alternative(html_message, "text/html")
        else:
            msg = EmailMessage(subject, message, self.from_email,
                               [self.to], connection=connection,
                               headers=self.headers)

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read())

        return msg

    def dispatch(self, connection=None, log_level=2):
        """
        Actually send out the email and log the result
        """
        connection_opened = False
        try:
            if connection is None:
                connection = get_connection(get_email_backend())
                connection.open()
                connection_opened = True

            self.email_message(connection=connection).send()
            status = STATUS.sent
            message = 'Sent'

            if connection_opened:
                connection.close()

        except Exception as err:
            status = STATUS.failed
            message = sys.exc_info()[1]

        self.status = status
        self.save()

        # If log level is 0, log nothing, 1 logs only sending failures
        # and 2 means log both successes and failures
        if log_level == 1:
            if status == STATUS.failed:
                self.logs.create(status=status, message=message)
        elif log_level == 2:
            self.logs.create(status=status, message=message)
        
        return status

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(Email, self).save(*args, **kwargs)


class Log(models.Model):
    """
    A model to record sending email sending activities.
    """

    STATUS_CHOICES = [(STATUS.sent, 'sent'), (STATUS.failed, 'failed')]

    email = models.ForeignKey(Email, editable=False, related_name='logs')
    date = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    message = models.TextField()

    class Meta:
        ordering = ('-date',)

    def __unicode__(self):
        return text_type(self.date)


class EmailTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(max_length=255, help_text=("Example: 'emails/customers/id/welcome.html'"))
    description = models.TextField(blank=True,
                                   help_text='Description of this email template.')
    subject = models.CharField(max_length=255, blank=True,
                               validators=[validate_template_syntax])
    content = models.TextField(blank=True,
                               validators=[validate_template_syntax])
    html_content = models.TextField(blank=True,
                                    validators=[validate_template_syntax])
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        template = super(EmailTemplate, self).save(*args, **kwargs)
        cache.delete(self.name)
        return template


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    def get_upload_path(self, filename):
        """Overriding to store the original filename"""
        if not self.name:
            self.name = filename  # set original filename

        filename = '{name}.{ext}'.format(name=uuid4().hex, ext=filename.split('.')[-1])

        return 'post_office_attachments/' + filename

    file = models.FileField(upload_to=get_upload_path)
    name = models.CharField(max_length=255, help_text='The original filename')
    emails = models.ManyToManyField(Email, related_name='attachments')

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from django.core.cache import get_cache
from django.core.cache.backends.base import InvalidCacheBackendError

from .compat import import_attribute


def get_email_backend():
    if hasattr(settings, 'POST_OFFICE_BACKEND'):
        backend = getattr(settings, 'POST_OFFICE_BACKEND')
    else:
        backend = getattr(settings, 'EMAIL_BACKEND',
                          'django.core.mail.backends.smtp.EmailBackend')
        # If EMAIL_BACKEND is set to use PostOfficeBackend
        # and POST_OFFICE_BACKEND is not set, fall back to SMTP
        if 'post_office.EmailBackend' in backend:
            backend = 'django.core.mail.backends.smtp.EmailBackend'
    return backend


def get_cache_backend():
    if hasattr(settings, 'CACHES'):
        if "post_office" in settings.CACHES:
            return get_cache("post_office")
        else:
            # Sometimes this raises InvalidCacheBackendError, which is ok too
            try:
                return get_cache("default")
            except InvalidCacheBackendError:
                pass
    return None


def get_config():
    """
    Returns Post Office's configuration in dictionary format. e.g:
    POST_OFFICE = {
        'BATCH_SIZE': 1000
    }
    """
    return getattr(settings, 'POST_OFFICE', {})


def get_batch_size():
    return get_config().get('BATCH_SIZE', 5000)


def get_default_priority():
    return get_config().get('DEFAULT_PRIORITY', 'medium')


CONTEXT_FIELD_CLASS = get_config().get('CONTEXT_FIELD_CLASS',
                                       'jsonfield.JSONField')
context_field_class = import_attribute(CONTEXT_FIELD_CLASS)

########NEW FILE########
__FILENAME__ = backends
from django.conf import settings
from django.core.mail import backends, EmailMultiAlternatives, send_mail, EmailMessage
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY
from ..settings import get_email_backend


class ErrorRaisingBackend(backends.base.BaseEmailBackend):
    '''
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    '''
    def send_messages(self, email_messages):
        raise Exception('Fake Error')


class BackendTest(TestCase):

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_backend(self):
        """
        Ensure that email backend properly queue email messages.
        """
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.subject, 'Test')
        self.assertEqual(email.status, STATUS.queued)
        self.assertEqual(email.priority, PRIORITY.medium)

    def test_email_backend_setting(self):
        """

        """
        old_email_backend = getattr(settings, 'EMAIL_BACKEND', None)
        old_post_office_backend = getattr(settings, 'POST_OFFICE_BACKEND', None)
        if hasattr(settings, 'EMAIL_BACKEND'):
            delattr(settings, 'EMAIL_BACKEND')
        if hasattr(settings, 'POST_OFFICE_BACKEND'):
            delattr(settings, 'POST_OFFICE_BACKEND')
        # If no email backend is set, backend should default to SMTP
        self.assertEqual(get_email_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If EMAIL_BACKEND is set to PostOfficeBackend, use SMTP to send by default
        setattr(settings, 'EMAIL_BACKEND', 'post_office.EmailBackend')
        self.assertEqual(get_email_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If POST_OFFICE_BACKEND is given, use that
        setattr(settings, 'POST_OFFICE_BACKEND', 'whatever.Whatever')
        self.assertEqual(get_email_backend(), 'whatever.Whatever')

        if old_email_backend:
            setattr(settings, 'EMAIL_BACKEND', old_email_backend)
        else:
            delattr(settings, 'EMAIL_BACKEND')

        if old_post_office_backend:
            setattr(settings, 'POST_OFFICE_BACKEND', old_post_office_backend)
        else:
            delattr(settings, 'POST_OFFICE_BACKEND')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_sending_html_email(self):
        """
        "text/html" attachments to Email should be persisted into the database
        """
        message = EmailMultiAlternatives('subject', 'body', 'from@example.com',
                                         ['recipient@example.com'])
        message.attach_alternative('html', "text/html")
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.html_message, 'html')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_headers_sent(self):
        """
        Test that headers are correctly set on the outgoing emails.
        """
        message = EmailMessage('subject', 'body', 'from@example.com',
                               ['recipient@example.com'],
                               headers={'Reply-To': 'reply@example.com'})
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.headers, {'Reply-To': 'reply@example.com'})

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com',
                               ['recipient@example.com'])

        message.attach('attachment.txt', 'attachment content')
        message.send()

        email = Email.objects.latest('id')
        self.assertEqual(email.attachments.count(), 1)
        self.assertEqual(email.attachments.all()[0].name, 'attachment.txt')
        self.assertEqual(email.attachments.all()[0].file.read(), b'attachment content')

    @override_settings(POST_OFFICE={'DEFAULT_PRIORITY': 'now'},
                       EMAIL_BACKEND='post_office.EmailBackend',
                       POST_OFFICE_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_default_priority_now(self):
        # If DEFAULT_PRIORITY is "now", mails should be sent right away
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)

########NEW FILE########
__FILENAME__ = cache
from django.conf import settings
from django.test import TestCase

from post_office import cache
from ..settings import get_cache_backend


class CacheTest(TestCase):

    def test_get_backend_settings(self):
        """Test basic get backend function and its settings"""
        # Sanity check
        self.assertTrue('post_office' in settings.CACHES)
        self.assertTrue(get_cache_backend())

        # If no post office key is defined, it should return default
        del(settings.CACHES['post_office'])
        self.assertTrue(get_cache_backend())

        # If no caches key in settings, it should return None
        delattr(settings, 'CACHES')
        self.assertEqual(None, get_cache_backend())

    def test_get_cache_key(self):
        """
            Test for converting names to cache key
        """
        self.assertEqual('post_office:template:test', cache.get_cache_key('test'))
        self.assertEqual('post_office:template:test-slugify', cache.get_cache_key('test slugify'))

    def test_basic_cache_operations(self):
        """
            Test basic cache operations
        """
        # clean test cache
        cache.cache_backend.clear()
        self.assertEqual(None, cache.get('test-cache'))
        cache.set('test-cache', 'awesome content')
        self.assertTrue('awesome content', cache.get('test-cache'))
        cache.delete('test-cache')
        self.assertEqual(None, cache.get('test-cache'))

########NEW FILE########
__FILENAME__ = commands
import datetime

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS

try:
    from django.utils.timezone import now
    now = now
except ImportError:
    now = datetime.now


class CommandTest(TestCase):

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        self.assertEqual(Email.objects.count(), 0)

        # The command shouldn't delete today's email
        email = Email.objects.create(from_email='from@example.com', to='to@example.com')
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should be deleted
        email.created = now() - datetime.timedelta(31)
        email.save()
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)

    def test_send_queued_mail(self):
        """
        Quick check that ``send_queued_mail`` doesn't error out.
        """
        # Make sure that send_queued_mail with empty queue does not raise error
        call_command('send_queued_mail', processes=1)

        Email.objects.create(from_email='from@example.com', to='to@example.com',
                             status=STATUS.queued)
        call_command('send_queued_mail', processes=1)
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 1)

    def test_successful_deliveries_logging(self):
        """
        Successful deliveries are only logged when log_level is 2.
        """
        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)

    @override_settings(EMAIL_BACKEND='post_office.tests.backends.ErrorRaisingBackend')
    def test_failed_deliveries_logging(self):
        """
        Failed deliveries are logged when log_level is 1 and 2.
        """
        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 1)

        email = Email.objects.create(from_email='from@example.com',
                                     to='to@example.com', status=STATUS.queued)
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)

########NEW FILE########
__FILENAME__ = lockfile
import time
import os

from django.test import TestCase

from ..lockfile import FileLock, FileLocked


def setup_fake_lock(lock_file_name):
    pid = os.getpid()
    lockfile = '%s.lock' % pid
    try:
        os.remove(lock_file_name)
    except OSError:
        pass
    os.symlink(lockfile, lock_file_name)


class LockTest(TestCase):

    def test_process_killed_force_unlock(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.lock')

        with open(lockfile, 'w+') as f:
            f.write('9999999')
        assert os.path.exists(lockfile)
        with FileLock('test'):
            assert True

    def test_force_unlock_in_same_process(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        os.symlink(lockfile, 'test.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        with FileLock('test', force=True):
            assert True

    def test_exception_after_timeout(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        try:
            with FileLock('test', timeout=1):
                assert False
        except FileLocked:
            assert True

    def test_force_after_timeout(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        timeout = 1
        start = time.time()
        with FileLock('test', timeout=timeout, force=True):
            assert True
        end = time.time()
        assert end - start > timeout

    def test_get_lock_pid(self):
        """Ensure get_lock_pid() works properly"""
        with FileLock('test', timeout=1, force=True) as lock:
            self.assertEqual(lock.get_lock_pid(), int(os.getpid()))

########NEW FILE########
__FILENAME__ = mail
from datetime import date, datetime

from django.core import mail
from django.core.files.base import ContentFile
from django.conf import settings

from django.test import TestCase
from django.test.utils import override_settings

from ..settings import get_batch_size
from ..models import Email, EmailTemplate, Attachment, PRIORITY, STATUS
from ..mail import (create, get_queued, parse_priority,
                    send, send_many, send_queued, _send_bulk)


connection_counter = 0


class ConnectionTestingBackend(mail.backends.base.BaseEmailBackend):
    '''
    An EmailBackend that increments a global counter when connection is opened
    '''

    def open(self):
        global connection_counter
        connection_counter += 1

    def send_messages(self, email_messages):
        pass


class MailTest(TestCase):

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_queued_mail(self):
        """
        Check that only queued messages are sent.
        """
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
        }
        failed_mail = Email.objects.create(status=STATUS.failed, **kwargs)
        none_mail = Email.objects.create(status=None, **kwargs)

        # This should be the only email that gets sent
        queued_mail = Email.objects.create(status=STATUS.queued, **kwargs)
        send_queued()
        self.assertNotEqual(Email.objects.get(id=failed_mail.id).status, STATUS.sent)
        self.assertNotEqual(Email.objects.get(id=none_mail.id).status, STATUS.sent)
        self.assertEqual(Email.objects.get(id=queued_mail.id).status, STATUS.sent)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_queued_mail_multi_processes(self):
        """
        Check that send_queued works well with multiple processes
        """
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
            'status': STATUS.queued
        }

        # All three emails should be sent
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 0)
        for i in range(3):
            Email.objects.create(**kwargs)
        total_sent, total_failed = send_queued(processes=2)
        self.assertEqual(total_sent, 3)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_bulk(self):
        """
        Ensure _send_bulk() properly sends out emails.
        """
        email = Email.objects.create(
            to='to@example.com', from_email='bob@example.com',
            subject='send bulk', message='Message', status=STATUS.queued)
        _send_bulk([email])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'send bulk')

    @override_settings(EMAIL_BACKEND='post_office.tests.mail.ConnectionTestingBackend')
    def test_send_bulk_reuses_open_connection(self):
        """
        Ensure _send_bulk() only opens connection once to send multiple emails.
        """
        global connection_counter
        self.assertEqual(connection_counter, 0)
        email = Email.objects.create(to='to@example.com',
                                     from_email='bob@example.com', subject='',
                                     message='', status=STATUS.queued)
        email_2 = Email.objects.create(to='to@example.com',
                                       from_email='bob@example.com', subject='',
                                       message='', status=STATUS.queued)
        _send_bulk([email, email_2])
        self.assertEqual(connection_counter, 1)

    def test_get_queued(self):
        """
        Ensure get_queued returns only emails that should be sent
        """
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
        }
        self.assertEqual(list(get_queued()), [])

        # Emails with statuses failed, sent or None shouldn't be returned
        Email.objects.create(status=STATUS.failed, **kwargs)
        Email.objects.create(status=None, **kwargs)
        Email.objects.create(status=STATUS.sent, **kwargs)
        self.assertEqual(list(get_queued()), [])

        # Email with queued status and None as scheduled_time should be included
        queued_email = Email.objects.create(status=STATUS.queued,
                                            scheduled_time=None, **kwargs)
        self.assertEqual(list(get_queued()), [queued_email])

        # Email scheduled for the future should not be included
        Email.objects.create(status=STATUS.queued,
                             scheduled_time=date(2020, 12, 13), **kwargs)
        self.assertEqual(list(get_queued()), [queued_email])

        # Email scheduled in the past should be included
        past_email = Email.objects.create(status=STATUS.queued,
                                          scheduled_time=date(2010, 12, 13), **kwargs)
        self.assertEqual(list(get_queued()), [queued_email, past_email])

    def test_get_batch_size(self):
        """
        Ensure BATCH_SIZE setting is read correctly.
        """
        self.assertEqual(get_batch_size(), 5000)
        setattr(settings, 'POST_OFFICE', {'BATCH_SIZE': 100})
        self.assertEqual(get_batch_size(), 100)

    def test_create(self):
        """
        Test basic email creation
        """

        # Test that email is persisted only when commi=True
        email = create(
            sender='from@example.com', recipient='to@example.com',
            commit=False
        )
        self.assertEqual(email.id, None)
        email = create(
            sender='from@example.com', recipient='to@example.com',
            commit=True
        )
        self.assertNotEqual(email.id, None)

        # Test that email is created with the right status
        email = create(
            sender='from@example.com', recipient='to@example.com',
            priority=PRIORITY.now
        )
        self.assertEqual(email.status, None)
        email = create(
            sender='from@example.com', recipient='to@example.com',
            priority=PRIORITY.high
        )
        self.assertEqual(email.status, STATUS.queued)

        # Test that email is created with the right content
        context = {
            'subject': 'My subject',
            'message': 'My message',
            'html': 'My html',
        }
        now = datetime.now()
        email = create(
            sender='from@example.com', recipient='to@example.com',
            subject='Test {{ subject }}', message='Test {{ message }}',
            html_message='Test {{ html }}', context=context,
            scheduled_time=now, headers={'header': 'Test header'},
        )
        self.assertEqual(email.from_email, 'from@example.com')
        self.assertEqual(email.to, 'to@example.com')
        self.assertEqual(email.subject, 'Test My subject')
        self.assertEqual(email.message, 'Test My message')
        self.assertEqual(email.html_message, 'Test My html')
        self.assertEqual(email.scheduled_time, now)
        self.assertEqual(email.headers, {'header': 'Test header'})

    def test_parse_priority(self):
        self.assertEqual(parse_priority('now'), PRIORITY.now)
        self.assertEqual(parse_priority('high'), PRIORITY.high)
        self.assertEqual(parse_priority('medium'), PRIORITY.medium)
        self.assertEqual(parse_priority('low'), PRIORITY.low)

    def test_send_many(self):
        """Test send_many creates the right emails """
        kwargs_list = [
            {'sender': 'from@example.com', 'recipients': ['a@example.com']},
            {'sender': 'from@example.com', 'recipients': ['b@example.com']},
        ]
        send_many(kwargs_list)
        self.assertEqual(Email.objects.filter(to='a@example.com').count(), 1)

    def test_send_with_attachments(self):
        attachments = {
            'attachment_file1.txt': ContentFile('content'),
            'attachment_file2.txt': ContentFile('content'),
        }
        emails = send(recipients=['a@example.com', 'b@example.com'],
                      sender='from@example.com', message='message',
                      subject='subject', attachments=attachments)

        self.assertEquals(len(emails), 2)

        email = emails[0]
        self.assertTrue(email.pk)
        self.assertEquals(email.attachments.count(), 2)

    def test_send_with_render_on_delivery(self):
        """
        Ensure that mail.send() create email instances with appropriate
        fields being saved
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = send(recipients=['a@example.com', 'b@example.com'],
                     template=template, context=context,
                     render_on_delivery=True)[0]
        self.assertEqual(email.subject, '')
        self.assertEqual(email.message, '')
        self.assertEqual(email.html_message, '')
        self.assertEqual(email.template, template)

        # context shouldn't be persisted when render_on_delivery = False
        email = send(recipients=['a@example.com'],
                     template=template, context=context,
                     render_on_delivery=False)[0]
        self.assertEqual(email.context, '')

    def test_send_with_attachments_multiple_emails(self):
        """Test reusing the same attachment objects for several email objects"""
        attachments = {
            'attachment_file1.txt': ContentFile('content'),
            'attachment_file2.txt': ContentFile('content'),
        }
        emails = send(recipients=['a@example.com', 'b@example.com'],
                      sender='from@example.com', message='message',
                      subject='subject', attachments=attachments)

        self.assertEquals(emails[0].attachments.count(), 2)
        self.assertEquals(emails[1].attachments.count(), 2)
        self.assertEquals(Attachment.objects.count(), 2)

    def test_create_with_template(self):
        """If render_on_delivery is True, subject and content
        won't be rendered, context also won't be saved."""
        
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = create(
            sender='from@example.com', recipient='to@example.com',
            template=template, context=context, render_on_delivery=True
        )
        self.assertEqual(email.subject, '')
        self.assertEqual(email.message, '')
        self.assertEqual(email.html_message, '')
        self.assertEqual(email.context, context)
        self.assertEqual(email.template, template)

    def test_send_with_template(self):
        """If render_on_delivery is False, subject and content
        will be rendered, context won't be saved."""
        
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = send(['to@example.com'], 'from@example.com',
                     template=template, context=context)[0]
        email = Email.objects.get(id=email.id)
        self.assertEqual(email.subject, 'Subject test')
        self.assertEqual(email.message, 'Content test')
        self.assertEqual(email.html_message, 'HTML test')
        self.assertEqual(email.context, '')
        self.assertEqual(email.template, None)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta

from django.conf import settings as django_settings
from django.core import mail
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.forms.models import modelform_factory
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, Log, PRIORITY, STATUS, EmailTemplate, Attachment
from ..mail import send


class ModelTest(TestCase):

    def test_email_message(self):
        """
        Test to make sure that model's "email_message" method
        returns proper email classes.
        """

        # If ``html_message`` is set, ``EmailMultiAlternatives`` is expected
        email = Email.objects.create(to='to@example.com',
            from_email='from@example.com', subject='Subject',
            message='Message', html_message='<p>HTML</p>')
        message = email.email_message()
        self.assertEqual(type(message), EmailMultiAlternatives)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')
        self.assertEqual(message.alternatives, [('<p>HTML</p>', 'text/html')])

        # Without ``html_message``, ``EmailMessage`` class is expected
        email = Email.objects.create(to='to@example.com',
            from_email='from@example.com', subject='Subject',
            message='Message')
        message = email.email_message()
        self.assertEqual(type(message), EmailMessage)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')

    def test_email_message_render(self):
        """
        Ensure Email instance with template is properly rendered.
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = Email.objects.create(to='to@example.com', template=template,
                                     from_email='from@e.com', context=context)
        message = email.email_message()
        self.assertEqual(message.subject, 'Subject test')
        self.assertEqual(message.body, 'Content test')
        self.assertEqual(message.alternatives[0][0], 'HTML test')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_dispatch(self):
        """
        Ensure that email.dispatch() actually sends out the email
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test dispatch', message='Message')
        email.dispatch()
        self.assertEqual(mail.outbox[0].subject, 'Test dispatch')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_status_and_log(self):
        """
        Ensure that status and log are set properly on successful sending
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(log.email, email)

    @override_settings(EMAIL_BACKEND='post_office.tests.backends.ErrorRaisingBackend')
    def test_status_and_log_on_error(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertEqual(log.message, 'Fake Error')

    def test_dispatch_uses_opened_connection(self):
        """
        Test that the ``dispatch`` method uses the argument supplied connection.
        We test this by overriding the email backend with a dummy backend,
        but passing in a previously opened connection from locmem backend.
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        django_settings.EMAIL_BACKEND = \
            'django.core.mail.backends.dummy.EmailBackend'
        email.dispatch()
        # Outbox should be empty since dummy backend doesn't do anything
        self.assertEqual(len(mail.outbox), 0)

        # Message should go to outbox since locmem connection is explicitly passed in
        connection = get_connection('django.core.mail.backends.locmem.EmailBackend')
        email.dispatch(connection=connection)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='random.backend')
    def test_errors_while_getting_connection_are_logged(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertIn('does not define a "backend"', log.message)

    def test_default_sender(self):
        emails = send(['to@example.com'], subject='foo')
        self.assertEqual(emails[0].from_email,
                         django_settings.DEFAULT_FROM_EMAIL)

    def test_send_argument_checking(self):
        """
        mail.send() should raise an Exception if:
        - "template" is used with "subject", "message" or "html_message"
        - recipients is not in tuple or list format
        """
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', subject='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', message='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, 'to@example.com', 'from@a.com',
                          template='foo', html_message='bar')

    def test_send_with_template(self):
        """
        Ensure mail.send correctly creates templated emails to recipients
        """
        Email.objects.all().delete()
        headers = {'Reply-to': 'reply@email.com'}
        email_template = EmailTemplate.objects.create(name='foo', subject='bar',
                                                      content='baz')
        scheduled_time = datetime.now() + timedelta(days=1)
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      headers=headers, template=email_template,
                      scheduled_time=scheduled_time)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].headers, headers)
        self.assertEqual(emails[0].scheduled_time, scheduled_time)

        self.assertEqual(emails[1].to, 'to2@example.com')
        self.assertEqual(emails[1].headers, headers)

        # Test without header
        Email.objects.all().delete()
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      template=email_template)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].headers, None)

        self.assertEqual(emails[1].to, 'to2@example.com')
        self.assertEqual(emails[1].headers, None)

    def test_send_without_template(self):
        headers = {'Reply-to': 'reply@email.com'}
        scheduled_time = datetime.now() + timedelta(days=1)
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      subject='foo', message='bar', html_message='baz',
                      context={'name': 'Alice'}, headers=headers,
                      scheduled_time=scheduled_time, priority=PRIORITY.low)

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].subject, 'foo')
        self.assertEqual(emails[0].message, 'bar')
        self.assertEqual(emails[0].html_message, 'baz')
        self.assertEqual(emails[0].headers, headers)
        self.assertEqual(emails[0].priority, PRIORITY.low)
        self.assertEqual(emails[0].scheduled_time, scheduled_time)
        self.assertEqual(emails[1].to, 'to2@example.com')

        # Same thing, but now with context
        emails = send(['to1@example.com'], 'from@a.com',
                      subject='Hi {{ name }}', message='Message {{ name }}',
                      html_message='<b>{{ name }}</b>',
                      context={'name': 'Bob'}, headers=headers)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].subject, 'Hi Bob')
        self.assertEqual(emails[0].message, 'Message Bob')
        self.assertEqual(emails[0].html_message, '<b>Bob</b>')
        self.assertEqual(emails[0].headers, headers)

    def test_invalid_syntax(self):
        """
        Ensures that invalid template syntax will result in validation errors
        when saving a ModelForm of an EmailTemplate.
        """
        data = dict(
            name='cost',
            subject='Hi there!{{ }}',
            content='Welcome {{ name|titl }} to the site.',
            html_content='{% block content %}<h1>Welcome to the site</h1>'
        )

        EmailTemplateForm = modelform_factory(EmailTemplate)
        form = EmailTemplateForm(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'subject': [u"Empty variable tag"],
            'content': [u"Invalid filter: 'titl'"],
            'html_content': [u"Unclosed tags: endblock "]
        })

    def test_string_priority(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/23
        """
        emails = send(['to1@example.com'], 'from@a.com', priority='low')
        self.assertEqual(emails[0].priority, PRIORITY.low)

    def test_default_priority(self):
        emails = send(['to1@example.com'], 'from@a.com')
        self.assertEqual(emails[0].priority, PRIORITY.medium)

    def test_string_priority_exception(self):
        invalid_priority_send = lambda: send(['to1@example.com'], 'from@a.com', priority='hgh')

        with self.assertRaises(ValueError) as context:
            invalid_priority_send()

        self.assertEqual(
            str(context.exception),
            'Invalid priority, must be one of: low, medium, high, now'
        )

    def test_attachment_filename(self):
        attachment = Attachment()

        attachment.file.save(
            'test.txt',
            content=ContentFile('test file content'),
            save=True
        )
        self.assertEquals(attachment.name, 'test.txt')

    def test_attachments_email_message(self):
        email = Email.objects.create(to='to@example.com',
                                     from_email='from@example.com',
                                     subject='Subject')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        email.attachments.add(attachment)
        message = email.email_message()

        self.assertEqual(message.attachments,
                         [('test.txt', b'test file content', None)])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_dispatch_with_attachments(self):
        email = Email.objects.create(to='to@example.com',
                                     from_email='from@example.com',
                                     subject='Subject', message='message')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        email.attachments.add(attachment)
        email.dispatch()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Subject')
        self.assertEqual(mail.outbox[0].attachments,
                         [('test.txt', b'test file content', None)])

########NEW FILE########
__FILENAME__ = runtests
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))


from django.conf import settings


settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        },
    },
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 36000,
            'KEY_PREFIX': 'post-office',
        },
        'post_office': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 36000,
            'KEY_PREFIX': 'post-office',
        }
    },
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'post_office',
    ),
    DEFAULT_FROM_EMAIL='default@example.com',
    ROOT_URLCONF = 'post_office.test_urls',
    TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner',
)

from django.test.utils import get_runner

def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    TestRunner = get_runner(settings)

    test_runner = TestRunner()
    if len(sys.argv) == 2:
        test_case = '.' + sys.argv[1]
    elif len(sys.argv) == 1:
        test_case = ''
    else:
        print(usage())
        sys.exit(1)
    failures = test_runner.run_tests(['post_office'])

    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
from datetime import datetime, timedelta

from django.core import mail
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY, EmailTemplate, Attachment
from ..utils import (send_mail, send_queued_mail, get_email_template, send_templated_mail,
                     split_emails, create_attachments)
from ..validators import validate_email_with_name


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UtilsTest(TestCase):

    def test_mail_status(self):
        """
        Check that send_mail assigns the right status field to Email instances
        """
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.medium)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.queued)

        # Emails sent with "now" priority don't get sent right away
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.now)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)

    def test_email_validator(self):
        # These should validate
        validate_email_with_name('email@example.com')
        validate_email_with_name('Alice Bob <email@example.com>')
        Email.objects.create(to='to@example.com', from_email='Alice <from@example.com>',
                             subject='Test', message='Message', status=STATUS.sent)

        # Should also support international domains
        validate_email_with_name('Alice Bob <email@example.co.id>')

        # These should raise ValidationError
        self.assertRaises(ValidationError, validate_email_with_name, 'invalid_mail')
        self.assertRaises(ValidationError, validate_email_with_name, 'Alice <invalid_mail>')

    def test_get_template_email(self):
        # Sanity Check
        template_name = 'customer/en/happy-holidays'
        self.assertRaises(EmailTemplate.DoesNotExist, get_email_template, template_name)
        email_template = EmailTemplate.objects.create(name=template_name, content='Happy Holiday!')

        # First query should hit database
        self.assertNumQueries(1, lambda: get_email_template(template_name))
        # Second query should hit cache instead
        self.assertNumQueries(0, lambda: get_email_template(template_name))

        # It should return the correct template
        self.assertEqual(email_template, get_email_template(template_name))

    def test_send_templated_email(self):
        template_name = 'customer/en/happy-holidays'
        to_addresses = ['to@example1.com', 'to@example2.com']

        # Create email template
        EmailTemplate.objects.create(name=template_name, content='Hi {{name}}',
                                     html_content='<p>Hi {{name}}</p>',
                                     subject='Happy Holidays!')

        # Send templated mail
        send_templated_mail(template_name, 'from@example.com', to_addresses,
                            context={'name': 'AwesomeBoy'}, priority=PRIORITY.medium)

        send_queued_mail()

        # Check for the message integrity
        self.assertEqual(len(mail.outbox), 2)
        for email, to_address in zip(mail.outbox, to_addresses):
            self.assertEqual(email.subject, 'Happy Holidays!')
            self.assertEqual(email.body, 'Hi AwesomeBoy')
            self.assertEqual(email.alternatives, [('<p>Hi AwesomeBoy</p>', 'text/html')])
            self.assertEqual(email.to, [to_address])

    def test_split_emails(self):
        """
        Check that split emails correctly divide email lists for multiprocessing
        """
        for i in range(225):
            Email.objects.create(from_email='from@example.com', to='to@example.com')
        expected_size = [57, 56, 56, 56]
        email_list = split_emails(Email.objects.all(), 4)
        self.assertEqual(expected_size, [len(emails) for emails in email_list])

    def test_create_attachments(self):
        attachments = create_attachments({
            'attachment_file1.txt': ContentFile('content'),
            'attachment_file2.txt': ContentFile('content'),
        })

        self.assertEqual(len(attachments), 2)
        self.assertIsInstance(attachments[0], Attachment)
        self.assertTrue(attachments[0].pk)
        self.assertEquals(attachments[0].file.read(), b'content')
        self.assertTrue(attachments[0].name.startswith('attachment_file'))

    def test_create_attachments_open_file(self):
        attachments = create_attachments({
            'attachment_file.py': __file__,
        })

        self.assertEqual(len(attachments), 1)
        self.assertIsInstance(attachments[0], Attachment)
        self.assertTrue(attachments[0].pk)
        self.assertTrue(attachments[0].file.read())
        self.assertEquals(attachments[0].name, 'attachment_file.py')

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase

from post_office import mail
from post_office.models import Email


admin_username = 'real_test_admin'
admin_email = 'read@admin.com'
admin_pass = 'admin_pass'


class AdminViewTest(TestCase):
    def setUp(self):
        user = User.objects.create_superuser(admin_username, admin_email, admin_pass)
        self.client = Client()
        self.client.login(username=user.username, password=admin_pass)

    # Small test to make sure the admin interface is loaded
    def test_admin_interface(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)

    def test_admin_change_page(self):
        """Ensure that changing an email object in admin works."""
        mail.send(recipients=['test@example.com'], headers={'foo': 'bar'})
        email = Email.objects.latest('id')
        response = self.client.get(reverse('admin:post_office_email_change', args=[email.id]))
        self.assertEqual(response.status_code, 200)
########NEW FILE########
__FILENAME__ = test_settings
# -*- coding: utf-8 -*-


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'post-office',
    },
    'post_office': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'post-office',
    }
}

POST_OFFICE = {
    # 'CONTEXT_FIELD_CLASS': 'picklefield.fields.PickledObjectField',
}


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'post_office',
)

SECRET_KEY = 'a'

ROOT_URLCONF = 'post_office.test_urls'

DEFAULT_FROM_EMAIL = 'webmaster@example.com'

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls), name='admin'),
)

########NEW FILE########
__FILENAME__ = utils
import warnings

from django.conf import settings
from django.core.files import File
from django.core.mail import get_connection
from django.db.models import Q

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from post_office import cache
from .compat import string_types
from .models import Email, PRIORITY, STATUS, EmailTemplate, Attachment
from .settings import get_email_backend

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    import datetime
    now = datetime.datetime.now


def send_mail(subject, message, from_email, recipient_list, html_message='',
              scheduled_time=None, headers=None, priority=PRIORITY.medium):
    """
    Add a new message to the mail queue. This is a replacement for Django's
    ``send_mail`` core email method.
    """

    subject = force_text(subject)
    status = None if priority == PRIORITY.now else STATUS.queued
    emails = []
    for address in recipient_list:
        emails.append(
            Email.objects.create(
                from_email=from_email, to=address, subject=subject,
                message=message, html_message=html_message, status=status,
                headers=headers, priority=priority, scheduled_time=scheduled_time
            )
        )
    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch()
    return emails


def send_queued_mail():
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    sent_count = 0
    failed_count = 0
    queued_emails = Email.objects.filter(status=STATUS.queued) \
        .filter(Q(scheduled_time__lte=now()) | Q(scheduled_time=None)) \
        .order_by('-priority')

    if queued_emails:

        # Try to open a connection, if we can't just pass in None as connection
        try:
            connection = get_connection(get_email_backend())
            connection.open()
        except Exception:
            connection = None

        for mail in queued_emails:
            status = mail.dispatch(connection)
            if status == STATUS.sent:
                sent_count += 1
            else:
                failed_count += 1
        if connection:
            connection.close()
    print('%s emails attempted, %s sent, %s failed' % (
        len(queued_emails), sent_count, failed_count)
    )


def send_templated_mail(template_name, from_address, to_addresses,
                        context={}, priority=PRIORITY.medium):
    warnings.warn(
        "The `send_templated_mail` command is deprecated and will be removed "
        "in a future relase. Please use `post_office.mail.send` instead.",
        DeprecationWarning)
    email_template = get_email_template(template_name)
    for address in to_addresses:
        email = Email.objects.from_template(from_address, address, email_template,
                                            context, priority)
        if priority == PRIORITY.now:
            email.dispatch()


def get_email_template(name):
    """
    Function to get email template object that checks from cache first if caching is enabled
    """
    if hasattr(settings, 'POST_OFFICE_CACHE') and settings.POST_OFFICE_TEMPLATE_CACHE is False:
        return EmailTemplate.objects.get(name=name)
    else:
        email_template = cache.get(name)
        if email_template is not None:
            return email_template
        else:
            email_template = EmailTemplate.objects.get(name=name)
            cache.set(name, email_template)
            return email_template


def split_emails(emails, split_count=1):
    # Group emails into X sublists
    # taken from http://www.garyrobinson.net/2008/04/splitting-a-pyt.html
    # Strange bug, only return 100 email if we do not evaluate the list
    if list(emails):
        return [emails[i::split_count] for i in range(split_count)]


def create_attachments(attachment_files):
    """
    Create Attachment instances from files

    attachment_files is a dict of:
        * Key - the filename to be used for the attachment.
        * Value - file-like object, or a filename to open.

    Returns a list of Attachment objects
    """
    attachments = []
    for filename, content in attachment_files.items():
        opened_file = None

        if isinstance(content, string_types):
            # `content` is a filename - try to open the file
            opened_file = open(content, 'rb')
            content = File(opened_file)

        attachment = Attachment()
        attachment.file.save(filename, content=content, save=True)

        attachments.append(attachment)

        if opened_file is not None:
            opened_file.close()

    return attachments

########NEW FILE########
__FILENAME__ = validators
import re

from django.core.exceptions import ValidationError
from django.template import Template, TemplateSyntaxError

from .compat import text_type


email_re = re.compile(r'\b[A-Z0-9._%-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b', re.IGNORECASE)


def validate_email_with_name(value):
    """
    In addition to validating valid email address, it also accepts email address
    in the format of "Recipient Name <email@example.com>"
    """
    # Try matching straight email address "alice@example.com"
    if email_re.match(value):
        return

    # Now try to match "Alice <alice@example.com>"
    if '<' and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            email = value[start:end]
            if email_re.match(email):
                return

    raise ValidationError('Enter a valid e-mail address.', code='invalid')


def validate_template_syntax(source):
    """
    Basic Django Template syntax validation. This allows for robuster template
    authoring.
    """
    try:
        t = Template(source)
    except TemplateSyntaxError as err:
        raise ValidationError(text_type(err))


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
