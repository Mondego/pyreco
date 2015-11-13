__FILENAME__ = admin
import logging

from django.conf import settings
from django.contrib import admin

from django_mailbox.models import MessageAttachment, Message, Mailbox
from django_mailbox.signals import message_received
from django_mailbox.utils import convert_header_to_unicode

logger = logging.getLogger(__name__)


def get_new_mail(mailbox_admin, request, queryset):
    for mailbox in queryset.all():
        logger.debug('Receiving mail for %s' % mailbox)
        mailbox.get_new_mail()
get_new_mail.short_description = 'Get new mail'


def resend_message_received_signal(message_admin, request, queryset):
    for message in queryset.all():
        logger.debug('Resending \'message_received\' signal for %s' % message)
        message_received.send(sender=message_admin, message=message)
resend_message_received_signal.short_description = (
    'Re-send message received signal'
)


class MailboxAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'uri',
        'from_email',
        'active',
    )
    actions = [get_new_mail]


class MessageAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('message', )
    list_display = ('message', 'document',)


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0


class MessageAdmin(admin.ModelAdmin):
    def attachment_count(self, msg):
        return msg.attachments.count()

    def subject(self, msg):
        return convert_header_to_unicode(msg.subject)

    inlines = [
        MessageAttachmentInline,
    ]
    list_display = (
        'subject',
        'processed',
        'read',
        'mailbox',
        'outgoing',
        'attachment_count',
    )
    ordering = ['-processed']
    list_filter = (
        'mailbox',
        'outgoing',
        'processed',
        'read',
    )
    exclude = (
        'body',
    )
    raw_id_fields = (
        'in_reply_to',
    )
    readonly_fields = (
        'text',
    )
    actions = [resend_message_received_signal]

if getattr(settings, 'DJANGO_MAILBOX_ADMIN_ENABLED', True):
    admin.site.register(Message, MessageAdmin)
    admin.site.register(MessageAttachment, MessageAttachmentAdmin)
    admin.site.register(Mailbox, MailboxAdmin)

########NEW FILE########
__FILENAME__ = getmail
from django.core.management.base import BaseCommand

from django_mailbox.models import Mailbox

class Command(BaseCommand):
    def handle(self, *args, **options):
        mailboxes = Mailbox.active_mailboxes.all()
        if args:
            mailboxes = mailboxes.filter(name = ' '.join(args))
        for mailbox in mailboxes:
            self.stdout.write('Gathering messages for %s\n' % mailbox.name)
            messages = mailbox.get_new_mail()
            for message in messages:
                self.stdout.write('Received %s (from %s)\n' % (
                        message.subject,
                        message.from_address
                    ))

########NEW FILE########
__FILENAME__ = processincomingmessage
import email
import logging
import rfc822
import sys

from django.core.management.base import BaseCommand

from django_mailbox.models import Mailbox

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    args = "<[Mailbox Name (optional)]>"
    command = "Receive incoming mail via stdin"

    def handle(self, mailbox_name=None, *args, **options):
        message = email.message_from_string(sys.stdin.read())
        if message:
            if mailbox_name:
                mailbox = self.get_mailbox_by_name(mailbox_name)
            else:
                mailbox = self.get_mailbox_for_message(message)
            mailbox.process_incoming_message(message)
            logger.info("Message received from %s" % message['from'])
        else:
            logger.warning("Message not processable.")

    def get_mailbox_by_name(self, name):
        mailbox, created = Mailbox.objects.get_or_create(
                name=name,
                )
        return mailbox

    def get_mailbox_for_message(self, message):
        email_address = rfc822.parseaddr(message['to'])[1][0:255]
        return self.get_mailbox_by_name(email_address)

########NEW FILE########
__FILENAME__ = rebuildmessageattachments
import email
import hashlib
import logging

from django.core.management.base import BaseCommand

from django_mailbox.models import MessageAttachment, Message

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """ Briefly, a bug existed in a migration that may have caused message
    attachments to become disassociated with their messages.  This management
    command will read through existing message attachments and attempt to
    re-associate them with their original message.

    This isn't foolproof, I'm afraid.  If an attachment exists twice, it will
    be associated only with the most recent e-mail message.  That said,
    I'm quite sure that the bug in the migration is gone (and you'd have to
    have been quite unlucky to have ran the bad migration).

    """
    def handle(self, *args, **options):
        ATTACHMENT_HASH_MAP = {}

        attachments_without_messages = MessageAttachment.objects.filter(
            message=None
        ).order_by(
            'id'
        )

        if attachments_without_messages.count() < 1:
            return

        for attachment in attachments_without_messages:
            md5 = hashlib.md5()
            for chunk in attachment.document.file.chunks():
                md5.update(chunk)
            ATTACHMENT_HASH_MAP[md5.hexdigest()] = attachment.pk

        for message_record in Message.objects.all().order_by('id'):
            message = email.message_from_string(message_record.body)
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get('Content-Disposition') is None:
                        continue
                    md5 = hashlib.md5()
                    md5.update(part.get_payload(decode=True))
                    digest = md5.hexdigest()
                    if digest in ATTACHMENT_HASH_MAP:
                        attachment = MessageAttachment.objects.get(
                            pk=ATTACHMENT_HASH_MAP[digest]
                        )
                        attachment.message = message_record
                        attachment.save()
                        logger.info(
                            "Associated message %s with attachment %s (%s)",
                            message_record.pk,
                            attachment.pk,
                            digest
                        )
                    else:
                        logger.info(
                            "%s(%s) not found in currently-stored attachments",
                            part.get_filename(),
                            digest
                        )

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Mailbox'
        db.create_table('django_mailbox_mailbox', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('uri', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('django_mailbox', ['Mailbox'])

        # Adding model 'Message'
        db.create_table('django_mailbox_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mailbox', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_mailbox.Mailbox'])),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('message_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('from_address', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('received', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('django_mailbox', ['Message'])


    def backwards(self, orm):
        # Deleting model 'Mailbox'
        db.delete_table('django_mailbox_mailbox')

        # Deleting model 'Message'
        db.delete_table('django_mailbox_message')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'received': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_mailbox_uri
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Mailbox.uri'
        db.alter_column('django_mailbox_mailbox', 'uri', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Mailbox.uri'
        raise RuntimeError("Cannot reverse this migration. 'Mailbox.uri' and its values cannot be restored.")

    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'received': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_mailbox_active
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Mailbox.active'
        db.add_column('django_mailbox_mailbox', 'active',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Mailbox.active'
        db.delete_column('django_mailbox_mailbox', 'active')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'received': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_message_outgoing
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Message.outgoing'
        db.add_column('django_mailbox_message', 'outgoing',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Message.outgoing'
        db.delete_column('django_mailbox_message', 'outgoing')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'received': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0005_rename_fields
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_column('django_mailbox_message', 'from_address', 'address')
        db.rename_column('django_mailbox_message', 'received', 'processed')

    def backwards(self, orm):
        db.rename_column('django_mailbox_message', 'address', 'from_address')
        db.rename_column('django_mailbox_message', 'processed', 'received')

    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_message_in_reply_to
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Message.in_reply_to'
        db.add_column('django_mailbox_message', 'in_reply_to',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='replies', null=True, to=orm['django_mailbox.Message']),
                      keep_default=False)

        # Adding M2M table for field references on 'Message'
        db.create_table('django_mailbox_message_references', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_message', models.ForeignKey(orm['django_mailbox.message'], null=False)),
            ('to_message', models.ForeignKey(orm['django_mailbox.message'], null=False))
        ))
        db.create_unique('django_mailbox_message_references', ['from_message_id', 'to_message_id'])


    def backwards(self, orm):
        # Deleting field 'Message.in_reply_to'
        db.delete_column('django_mailbox_message', 'in_reply_to_id')

        # Removing M2M table for field references on 'Message'
        db.delete_table('django_mailbox_message_references')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'references': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'referenced_by'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['django_mailbox.Message']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0007_auto__del_field_message_address__add_field_message_from_header__add_fi
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Message.address'
        db.delete_column('django_mailbox_message', 'address')

        # Adding field 'Message.from_header'
        db.add_column('django_mailbox_message', 'from_header',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255),
                      keep_default=False)

        # Adding field 'Message.to_header'
        db.add_column('django_mailbox_message', 'to_header',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Message.address'
        raise RuntimeError("Cannot reverse this migration. 'Message.address' and its values cannot be restored.")
        # Deleting field 'Message.from_header'
        db.delete_column('django_mailbox_message', 'from_header')

        # Deleting field 'Message.to_header'
        db.delete_column('django_mailbox_message', 'to_header')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'references': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'referenced_by'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['django_mailbox.Message']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0008_populate_from_to_fields
# -*- coding: utf-8 -*-
import datetime
import email
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        for message in orm['django_mailbox.message'].objects.all():
            msg_object = email.message_from_string(
                    message.body
                )
            message.from_header = msg_object['from']
            message.to_header = msg_object['to']
            message.save()

    def backwards(self, orm):
        raise RuntimeError('Cannot reverse this migration.')

    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'references': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'referenced_by'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['django_mailbox.Message']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['django_mailbox']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0009_remove_references_table
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing M2M table for field references on 'Message'
        db.delete_table('django_mailbox_message_references')


    def backwards(self, orm):
        # Adding M2M table for field references on 'Message'
        db.create_table('django_mailbox_message_references', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_message', models.ForeignKey(orm['django_mailbox.message'], null=False)),
            ('to_message', models.ForeignKey(orm['django_mailbox.message'], null=False))
        ))
        db.create_unique('django_mailbox_message_references', ['from_message_id', 'to_message_id'])


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_mailbox_from_email
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Mailbox.from_email'
        db.add_column('django_mailbox_mailbox', 'from_email',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Mailbox.from_email'
        db.delete_column('django_mailbox_mailbox', 'from_email')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0011_auto__add_field_message_read
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Message.read'
        db.add_column('django_mailbox_message', 'read',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Message.read'
        db.delete_column('django_mailbox_message', 'read')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0012_auto__add_messageattachment
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'MessageAttachment'
        db.create_table('django_mailbox_messageattachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('document', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('django_mailbox', ['MessageAttachment'])

        # Adding M2M table for field attachments on 'Message'
        db.create_table('django_mailbox_message_attachments', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('message', models.ForeignKey(orm['django_mailbox.message'], null=False)),
            ('messageattachment', models.ForeignKey(orm['django_mailbox.messageattachment'], null=False))
        ))
        db.create_unique('django_mailbox_message_attachments', ['message_id', 'messageattachment_id'])


    def backwards(self, orm):
        
        # Deleting model 'MessageAttachment'
        db.delete_table('django_mailbox_messageattachment')

        # Removing M2M table for field attachments on 'Message'
        db.delete_table('django_mailbox_message_attachments')


    models = {
        'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_mailbox.MessageAttachment']", 'symmetrical': 'False'}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        },
        'django_mailbox.messageattachment': {
            'Meta': {'object_name': 'MessageAttachment'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0013_auto__add_field_messageattachment_message
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'MessageAttachment.message'
        db.add_column(u'django_mailbox_messageattachment', 'message',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='attachments', null=True, to=orm['django_mailbox.Message']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'MessageAttachment.message'
        db.delete_column(u'django_mailbox_messageattachment', 'message_id')


    models = {
        u'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        u'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'messages_old'", 'blank': 'True', 'to': u"orm['django_mailbox.MessageAttachment']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        },
        u'django_mailbox.messageattachment': {
            'Meta': {'object_name': 'MessageAttachment'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attachments_new'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0014_migrate_message_attachments
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    no_dry_run = True
    def forwards(self, orm):
        for message in orm['django_mailbox.Message'].objects.all():
            for attachment in message.attachments.all():
                attachment.message = message
                attachment.save()

    def backwards(self, orm):
        for attachment in orm['django_mailbox.MessageAttachment'].objects.all():
            if attachment.message:
                attachment.message.attachments.add(
                    attachment
                )

    models = {
        u'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        u'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'messages_old'", 'blank': 'True', 'to': u"orm['django_mailbox.MessageAttachment']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        },
        u'django_mailbox.messageattachment': {
            'Meta': {'object_name': 'MessageAttachment'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attachments_new'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"})
        }
    }

    complete_apps = ['django_mailbox']

########NEW FILE########
__FILENAME__ = 0015_auto__add_field_messageattachment_headers
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing M2M table for field attachments on 'Message'
        db.delete_table('django_mailbox_message_attachments')

        # Adding field 'MessageAttachment.headers'
        db.add_column(u'django_mailbox_messageattachment', 'headers',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding M2M table for field attachments on 'Message'
        db.create_table(u'django_mailbox_message_attachments', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('message', models.ForeignKey(orm[u'django_mailbox.message'], null=False)),
            ('messageattachment', models.ForeignKey(orm[u'django_mailbox.messageattachment'], null=False))
        ))
        db.create_unique(u'django_mailbox_message_attachments', ['message_id', 'messageattachment_id'])

        # Deleting field 'MessageAttachment.headers'
        db.delete_column(u'django_mailbox_messageattachment', 'headers')


    models = {
        u'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        u'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        },
        u'django_mailbox.messageattachment': {
            'Meta': {'object_name': 'MessageAttachment'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'headers': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attachments'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = 0016_auto__add_field_message_encoded
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Message.encoded'
        db.add_column(u'django_mailbox_message', 'encoded',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Message.encoded'
        db.delete_column(u'django_mailbox_message', 'encoded')


    models = {
        u'django_mailbox.mailbox': {
            'Meta': {'object_name': 'Mailbox'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        u'django_mailbox.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'encoded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'from_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"}),
            'mailbox': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['django_mailbox.Mailbox']"}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'read': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'to_header': ('django.db.models.fields.TextField', [], {})
        },
        u'django_mailbox.messageattachment': {
            'Meta': {'object_name': 'MessageAttachment'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'headers': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attachments'", 'null': 'True', 'to': u"orm['django_mailbox.Message']"})
        }
    }

    complete_apps = ['django_mailbox']
########NEW FILE########
__FILENAME__ = models
import base64
import email
from email.message import Message as EmailMessage
from email.utils import formatdate, parseaddr
from email.encoders import encode_base64
import mimetypes
import os.path
from quopri import encode as encode_quopri
import sys
import uuid

from django.conf import settings
from django.core.mail.message import make_msgid
from django.core.files.base import ContentFile
from django.db import models
from django_mailbox.transports import Pop3Transport, ImapTransport,\
    MaildirTransport, MboxTransport, BabylTransport, MHTransport, \
    MMDFTransport
from django_mailbox.signals import message_received
import six
from six.moves.urllib.parse import parse_qs, unquote, urlparse

from .utils import convert_header_to_unicode


STRIP_UNALLOWED_MIMETYPES = getattr(
    settings,
    'DJANGO_MAILBOX_STRIP_UNALLOWED_MIMETYPES',
    False
)
ALLOWED_MIMETYPES = getattr(
    settings,
    'DJANGO_MAILBOX_ALLOWED_MIMETYPES',
    [
        'text/plain',
        'text/html'
    ]
)
TEXT_STORED_MIMETYPES = getattr(
    settings,
    'DJANGO_MAILBOX_TEXT_STORED_MIMETYPES',
    [
        'text/plain',
        'text/html'
    ]
)
ALTERED_MESSAGE_HEADER = getattr(
    settings,
    'DJANGO_MAILBOX_ALTERED_MESSAGE_HEADER',
    'X-Django-Mailbox-Altered-Message'
)
ATTACHMENT_INTERPOLATION_HEADER = getattr(
    settings,
    'DJANGO_MAILBOX_ATTACHMENT_INTERPOLATION_HEADER',
    'X-Django-Mailbox-Interpolate-Attachment'
)


class ActiveMailboxManager(models.Manager):
    def get_query_set(self):
        return super(ActiveMailboxManager, self).get_query_set().filter(
            active=True,
        )


class Mailbox(models.Model):
    name = models.CharField(max_length=255)
    uri = models.CharField(
        max_length=255,
        help_text=(
            "Example: imap+ssl://myusername:mypassword@someserver <br />"
            "<br />"
            "Internet transports include 'imap' and 'pop3'; "
            "common local file transports include 'maildir', 'mbox', "
            "and less commonly 'babyl', 'mh', and 'mmdf'. <br />"
            "<br />"
            "Be sure to urlencode your username and password should they "
            "contain illegal characters (like @, :, etc)."
        ),
        blank=True,
        null=True,
        default=None,
    )
    from_email = models.CharField(
        max_length=255,
        help_text=(
            "Example: MailBot &lt;mailbot@yourdomain.com&gt;<br />"
            "'From' header to set for outgoing email.<br />"
            "<br />"
            "If you do not use this e-mail inbox for outgoing mail, this "
            "setting is unnecessary.<br />"
            "If you send e-mail without setting this, your 'From' header will'"
            "be set to match the setting `DEFAULT_FROM_EMAIL`."
        ),
        blank=True,
        null=True,
        default=None,
    )
    active = models.BooleanField(
        help_text=(
            "Check this e-mail inbox for new e-mail messages during polling "
            "cycles.  This checkbox does not have an effect upon whether "
            "mail is collected here when this mailbox receives mail from a "
            "pipe, and does not affect whether e-mail messages can be "
            "dispatched from this mailbox. "
        ),
        blank=True,
        default=True,
    )

    objects = models.Manager()
    active_mailboxes = ActiveMailboxManager()

    @property
    def _protocol_info(self):
        return urlparse(self.uri)

    @property
    def _query_string(self):
        return parse_qs(self._protocol_info.query)

    @property
    def _domain(self):
        return self._protocol_info.hostname

    @property
    def port(self):
        return self._protocol_info.port

    @property
    def username(self):
        return unquote(self._protocol_info.username)

    @property
    def password(self):
        return unquote(self._protocol_info.password)

    @property
    def location(self):
        return self._domain if self._domain else '' + self._protocol_info.path

    @property
    def type(self):
        scheme = self._protocol_info.scheme.lower()
        if '+' in scheme:
            return scheme.split('+')[0]
        return scheme

    @property
    def use_ssl(self):
        return '+ssl' in self._protocol_info.scheme.lower()

    @property
    def archive(self):
        archive_folder = self._query_string.get('archive', None)
        if not archive_folder:
            return None
        return archive_folder[0]

    def get_connection(self):
        if not self.uri:
            return None
        elif self.type == 'imap':
            conn = ImapTransport(
                self.location,
                port=self.port if self.port else None,
                ssl=self.use_ssl,
                archive=self.archive
            )
            conn.connect(self.username, self.password)
        elif self.type == 'pop3':
            conn = Pop3Transport(
                self.location,
                port=self.port if self.port else None,
                ssl=self.use_ssl
            )
            conn.connect(self.username, self.password)
        elif self.type == 'maildir':
            conn = MaildirTransport(self.location)
        elif self.type == 'mbox':
            conn = MboxTransport(self.location)
        elif self.type == 'babyl':
            conn = BabylTransport(self.location)
        elif self.type == 'mh':
            conn = MHTransport(self.location)
        elif self.type == 'mmdf':
            conn = MMDFTransport(self.location)
        return conn

    def process_incoming_message(self, message):
        msg = self._process_message(message)
        msg.outgoing = False
        msg.save()

        try:
            message_received.send(sender=self, message=msg)
        except:
            pass

        return msg

    def record_outgoing_message(self, message):
        msg = self._process_message(message)
        msg.outgoing = True
        msg.save()
        return msg

    def _get_dehydrated_message(self, msg, record):
        new = EmailMessage()
        if msg.is_multipart():
            for header, value in msg.items():
                new[header] = value
            for part in msg.get_payload():
                new.attach(
                    self._get_dehydrated_message(part, record)
                )
        elif (
            STRIP_UNALLOWED_MIMETYPES
            and not msg.get_content_type() in ALLOWED_MIMETYPES
        ):
            for header, value in msg.items():
                new[header] = value
            # Delete header, otherwise when attempting to  deserialize the
            # payload, it will be expecting a body for this.
            del new['Content-Transfer-Encoding']
            new[ALTERED_MESSAGE_HEADER] = (
                'Stripped; Content type %s not allowed' % (
                    msg.get_content_type()
                )
            )
            new.set_payload('')
        elif msg.get_content_type() not in TEXT_STORED_MIMETYPES:
            filename = msg.get_filename()
            if not filename:
                extension = mimetypes.guess_extension(msg.get_content_type())
            else:
                _, extension = os.path.splitext(filename)
            if not extension:
                extension = '.bin'

            attachment = MessageAttachment()

            attachment.document.save(
                uuid.uuid4().hex + extension,
                ContentFile(
                    six.BytesIO(
                        msg.get_payload(decode=True)
                    ).getvalue()
                )
            )
            attachment.message = record
            for key, value in msg.items():
                attachment[key] = value
            attachment.save()

            placeholder = EmailMessage()
            placeholder[ATTACHMENT_INTERPOLATION_HEADER] = str(attachment.pk)
            new = placeholder
        else:
            content_charset = msg.get_content_charset()
            if not content_charset:
                content_charset = 'ascii'
            try:
                # Make sure that the payload can be properly decoded in the
                # defined charset, if it can't, let's mash some things
                # inside the payload :-\
                msg.get_payload(decode=True).decode(content_charset)
            except UnicodeDecodeError:
                msg.set_payload(
                    msg.get_payload(decode=True).decode(
                        content_charset,
                        'ignore'
                    )
                )
            new = msg
        return new

    def _process_message(self, message):
        msg = Message()
        msg.mailbox = self
        if 'subject' in message:
            msg.subject = convert_header_to_unicode(message['subject'])[0:255]
        if 'message-id' in message:
            msg.message_id = message['message-id'][0:255]
        if 'from' in message:
            msg.from_header = convert_header_to_unicode(message['from'])
        if 'to' in message:
            msg.to_header = convert_header_to_unicode(message['to'])
        msg.save()
        message = self._get_dehydrated_message(message, msg)
        msg.set_body(message.as_string())
        if message['in-reply-to']:
            try:
                msg.in_reply_to = Message.objects.filter(
                    message_id=message['in-reply-to']
                )[0]
            except IndexError:
                pass
        msg.save()
        return msg

    def get_new_mail(self):
        new_mail = []
        connection = self.get_connection()
        if not connection:
            return new_mail
        for message in connection.get_message():
            msg = self.process_incoming_message(message)
            new_mail.append(msg)
        return new_mail

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Mailboxes"


class IncomingMessageManager(models.Manager):
    def get_query_set(self):
        return super(IncomingMessageManager, self).get_query_set().filter(
            outgoing=False,
        )


class OutgoingMessageManager(models.Manager):
    def get_query_set(self):
        return super(OutgoingMessageManager, self).get_query_set().filter(
            outgoing=True,
        )


class UnreadMessageManager(models.Manager):
    def get_query_set(self):
        return super(UnreadMessageManager, self).get_query_set().filter(
            read=None
        )


class Message(models.Model):
    mailbox = models.ForeignKey(Mailbox, related_name='messages')
    subject = models.CharField(max_length=255)
    message_id = models.CharField(max_length=255)
    in_reply_to = models.ForeignKey(
        'django_mailbox.Message',
        related_name='replies',
        blank=True,
        null=True,
    )
    from_header = models.CharField(
        max_length=255,
    )
    to_header = models.TextField()
    outgoing = models.BooleanField(
        default=False,
        blank=True,
    )

    body = models.TextField()
    encoded = models.BooleanField(
        default=False,
        help_text='True if the e-mail body is Base64 encoded'
    )

    processed = models.DateTimeField(
        auto_now_add=True
    )
    read = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
    )

    objects = models.Manager()
    unread_messages = UnreadMessageManager()
    incoming_messages = IncomingMessageManager()
    outgoing_messages = OutgoingMessageManager()

    @property
    def address(self):
        """Property allowing one to get the relevant address(es).

        In earlier versions of this library, the model had an `address` field
        storing the e-mail address from which a message was received.  During
        later refactorings, it became clear that perhaps storing sent messages
        would also be useful, so the address field was replaced with two
        separate fields.

        """
        addresses = []
        addresses = self.to_addresses + self.from_address
        return addresses

    @property
    def from_address(self):
        if self.from_header:
            return [parseaddr(self.from_header)[1].lower()]
        else:
            return []

    @property
    def to_addresses(self):
        addresses = []
        for address in self.to_header.split(','):
            if address:
                addresses.append(
                    parseaddr(
                        address
                    )[1].lower()
                )
        return addresses

    def reply(self, message):
        """Sends a message as a reply to this message instance.

        Although Django's e-mail processing will set both Message-ID
        and Date upon generating the e-mail message, we will not be able
        to retrieve that information through normal channels, so we must
        pre-set it.

        """
        if self.mailbox.from_email:
            message.from_email = self.mailbox.from_email
        else:
            message.from_email = settings.DEFAULT_FROM_EMAIL
        message.extra_headers['Message-ID'] = make_msgid()
        message.extra_headers['Date'] = formatdate()
        message.extra_headers['In-Reply-To'] = self.message_id
        message.send()
        return self.mailbox.record_outgoing_message(
            email.message_from_string(
                message.message().as_string()
            )
        )

    @property
    def text(self):
        return self.get_text_body()

    def get_text_body(self):
        def get_body_from_message(message):
            body = ''
            for part in message.walk():
                if (
                    part.get_content_maintype() == 'text'
                    and part.get_content_subtype() == 'plain'
                ):
                    charset = part.get_content_charset()
                    this_part = part.get_payload(decode=True)
                    if charset:
                        this_part = this_part.decode(charset, 'replace')

                    body += this_part
            return body

        return get_body_from_message(
            self.get_email_object()
        ).replace('=\n', '').strip()

    def _rehydrate(self, msg):
        new = EmailMessage()
        if msg.is_multipart():
            for header, value in msg.items():
                new[header] = value
            for part in msg.get_payload():
                new.attach(
                    self._rehydrate(part)
                )
        elif ATTACHMENT_INTERPOLATION_HEADER in msg.keys():
            try:
                attachment = MessageAttachment.objects.get(
                    pk=msg[ATTACHMENT_INTERPOLATION_HEADER]
                )
                for header, value in attachment.items():
                    new[header] = value
                encoding = new['Content-Transfer-Encoding']
                if encoding and encoding.lower() == 'quoted-printable':
                    # Cannot use `email.encoders.encode_quopri due to
                    # bug 14360: http://bugs.python.org/issue14360
                    output = six.BytesIO()
                    encode_quopri(
                        six.BytesIO(
                            attachment.document.read()
                        ),
                        output,
                        quotetabs=True,
                        header=False,
                    )
                    new.set_payload(
                        output.getvalue().decode().replace(' ', '=20')
                    )
                    del new['Content-Transfer-Encoding']
                    new['Content-Transfer-Encoding'] = 'quoted-printable'
                else:
                    new.set_payload(
                        attachment.document.read()
                    )
                    del new['Content-Transfer-Encoding']
                    encode_base64(new)
            except MessageAttachment.DoesNotExist:
                new[ALTERED_MESSAGE_HEADER] = (
                    'Missing; Attachment %s not found' % (
                        msg[ATTACHMENT_INTERPOLATION_HEADER]
                    )
                )
                new.set_payload('')
        else:
            for header, value in msg.items():
                new[header] = value
            new.set_payload(
                msg.get_payload()
            )
        return new

    def get_body(self):
        if self.encoded:
            return base64.b64decode(self.body.encode('ascii'))
        return self.body.encode('utf-8')

    def set_body(self, body):
        if six.PY3:
            body = body.encode('utf-8')
        self.encoded = True
        self.body = base64.b64encode(body).decode('ascii')

    def get_email_object(self):
        """ Returns an `email.message.Message` instance for this message."""
        body = self.get_body()
        if six.PY3:
            flat = email.message_from_bytes(body)
        else:
            flat = email.message_from_string(body)
        return self._rehydrate(flat)

    def delete(self, *args, **kwargs):
        for attachment in self.attachments.all():
            # This attachment is attached only to this message.
            attachment.delete()
        return super(Message, self).delete(*args, **kwargs)

    def __unicode__(self):
        return self.subject


class MessageAttachment(models.Model):
    message = models.ForeignKey(
        Message,
        related_name='attachments',
        null=True,
        blank=True,
    )
    headers = models.TextField(null=True, blank=True)
    document = models.FileField(upload_to='mailbox_attachments/%Y/%m/%d/')

    def delete(self, *args, **kwargs):
        self.document.delete()
        return super(MessageAttachment, self).delete(*args, **kwargs)

    def _get_rehydrated_headers(self):
        headers = self.headers
        if headers is None:
            return EmailMessage()
        if sys.version_info < (3, 0):
            headers = headers.encode('utf-8')
        return email.message_from_string(headers)

    def _set_dehydrated_headers(self, email_object):
        self.headers = email_object.as_string()

    def __delitem__(self, name):
        rehydrated = self._get_rehydrated_headers()
        del rehydrated[name]
        self._set_dehydrated_headers(rehydrated)

    def __setitem__(self, name, value):
        rehydrated = self._get_rehydrated_headers()
        rehydrated[name] = value
        self._set_dehydrated_headers(rehydrated)

    def get_filename(self):
        file_name = self._get_rehydrated_headers().get_filename()
        if file_name:
            return convert_header_to_unicode(file_name)
        else:
            return None

    def items(self):
        return self._get_rehydrated_headers().items()

    def __getitem__(self, name):
        value = self._get_rehydrated_headers()[name]
        if value is None:
            raise KeyError('Header %s does not exist' % name)
        return value

    def __unicode__(self):
        return self.document.url

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            },
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django_mailbox',
        ]
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args):
    if not test_args:
        test_args = ['django_mailbox']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    runner = DjangoTestSuiteRunner(
        verbosity=1,
        interactive=False,
        failfast=False
    )
    failures = runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = signals
from django.dispatch.dispatcher import Signal

message_received = Signal(providing_args=['message'])

########NEW FILE########
__FILENAME__ = base
import email
import os.path

import six

from django.test import TestCase

from django_mailbox import models
from django_mailbox.models import Mailbox, Message


class EmailMessageTestCase(TestCase):
    ALLOWED_EXTRA_HEADERS = [
        'MIME-Version',
        'Content-Transfer-Encoding',
    ]

    def setUp(self):
        self._ALLOWED_MIMETYPES = models.ALLOWED_MIMETYPES
        self._STRIP_UNALLOWED_MIMETYPES = models.STRIP_UNALLOWED_MIMETYPES
        self._TEXT_STORED_MIMETYPES = models.TEXT_STORED_MIMETYPES

        self.mailbox = Mailbox.objects.create()
        super(EmailMessageTestCase, self).setUp()

    def _get_email_as_text(self, name):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                'messages',
                name,
            ),
            'rb'
        ) as f:
            return f.read()

    def _get_email_object(self, name):
        copy = self._get_email_as_text(name)
        if six.PY3:
            return email.message_from_bytes(copy)
        else:
            return email.message_from_string(copy)

    def _headers_identical(self, left, right, header=None):
        """ Check if headers are (close enough to) identical.

         * This is particularly tricky because Python 2.6, Python 2.7 and
           Python 3 each handle header strings slightly differently.  This
           should mash away all of the differences, though.
         * This also has a small loophole in that when re-writing e-mail
           payload encodings, we re-build the Content-Type header, so if the
           header was originally unquoted, it will be quoted when rehydrating
           the e-mail message.

        """
        if header.lower() == 'content-type':
            # Special case; given that we re-write the header, we'll be quoting
            # the new content type; we need to make sure that doesn't cause
            # this comparison to fail.  Also, the case of the encoding could
            # be changed, etc. etc. etc.
            left = left.replace('"', '').upper()
            right = right.replace('"', '').upper()
        left = left.replace('\n\t', ' ').replace('\n ', ' ')
        right = right.replace('\n\t', ' ').replace('\n ', ' ')
        if right != left:
            return False
        return True

    def compare_email_objects(self, left, right):
        # Compare headers
        for key, value in left.items():
            if not right[key] and key in self.ALLOWED_EXTRA_HEADERS:
                continue
            if not right[key]:
                raise AssertionError("Extra header '%s'" % key)
            if not self._headers_identical(right[key], value, header=key):
                raise AssertionError(
                    "Header '%s' unequal:\n%s\n%s" % (
                        key,
                        repr(value),
                        repr(right[key]),
                    )
                )
        for key, value in right.items():
            if not left[key] and key in self.ALLOWED_EXTRA_HEADERS:
                continue
            if not left[key]:
                raise AssertionError("Extra header '%s'" % key)
            if not self._headers_identical(left[key], value, header=key):
                raise AssertionError(
                    "Header '%s' unequal:\n%s\n%s" % (
                        key,
                        repr(value),
                        repr(right[key]),
                    )
                )
        if left.is_multipart() != right.is_multipart():
            self._raise_mismatched(left, right)
        if left.is_multipart():
            left_payloads = left.get_payload()
            right_payloads = right.get_payload()
            if len(left_payloads) != len(right_payloads):
                self._raise_mismatched(left, right)
            for n in range(len(left_payloads)):
                self.compare_email_objects(
                    left_payloads[n],
                    right_payloads[n]
                )
        else:
            if left.get_payload() is None or right.get_payload() is None:
                if left.get_payload() is None:
                    if right.get_payload is not None:
                        self._raise_mismatched(left, right)
                if right.get_payload() is None:
                    if left.get_payload is not None:
                        self._raise_mismatched(left, right)
            elif left.get_payload().strip() != right.get_payload().strip():
                self._raise_mismatched(left, right)

    def _raise_mismatched(self, left, right):
        raise AssertionError(
            "Message payloads do not match:\n%s\n%s" % (
                left.as_string(),
                right.as_string()
            )
        )

    def assertEqual(self, left, right):
        if not isinstance(left, email.message.Message):
            return super(EmailMessageTestCase, self).assertEqual(left, right)
        return self.compare_email_objects(left, right)

    def tearDown(self):
        for message in Message.objects.all():
            message.delete()
        models.ALLOWED_MIMETYPES = self._ALLOWED_MIMETYPES
        models.STRIP_UNALLOWED_MIMETYPES = self._STRIP_UNALLOWED_MIMETYPES
        models.TEXT_STORED_MIMETYPES = self._TEXT_STORED_MIMETYPES

        self.mailbox.delete()
        super(EmailMessageTestCase, self).tearDown()

########NEW FILE########
__FILENAME__ = test_mailbox
from django.test import TestCase

from django_mailbox.models import Mailbox


__all__ = ['TestMailbox']


class TestMailbox(TestCase):
    def test_protocol_info(self):
        mailbox = Mailbox()
        mailbox.uri = 'alpha://test.com'

        expected_protocol = 'alpha'
        actual_protocol = mailbox._protocol_info.scheme

        self.assertEqual(
            expected_protocol,
            actual_protocol,
        )

########NEW FILE########
__FILENAME__ = test_message_flattening
from django_mailbox import models
from django_mailbox.models import Message
from django_mailbox.tests.base import EmailMessageTestCase


__all__ = ['TestMessageFlattening']


class TestMessageFlattening(EmailMessageTestCase):
    def test_quopri_message_is_properly_rehydrated(self):
        incoming_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        expected_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        models.TEXT_STORED_MIMETYPES = ['text/plain']

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_base64_message_is_properly_rehydrated(self):
        incoming_email_object = self._get_email_object(
            'message_with_attachment.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        expected_email_object = self._get_email_object(
            'message_with_attachment.eml',
        )

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_message_handles_rehydration_problems(self):
        incoming_email_object = self._get_email_object(
            'message_with_defective_attachment_association.eml',
        )
        expected_email_object = self._get_email_object(
            'message_with_defective_attachment_association_result.eml',
        )
        # Note: this is identical to the above, but it appears that
        # while reading-in an e-mail message, we do alter it slightly
        message = Message()
        message.body = incoming_email_object.as_string()

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

    def test_message_content_type_stripping(self):
        incoming_email_object = self._get_email_object(
            'message_with_many_multiparts.eml',
        )
        expected_email_object = self._get_email_object(
            'message_with_many_multiparts_stripped_html.eml',
        )
        models.STRIP_UNALLOWED_MIMETYPES = True
        models.ALLOWED_MIMETYPES = ['text/plain']

        msg = self.mailbox.process_incoming_message(incoming_email_object)

        actual_email_object = msg.get_email_object()

        self.assertEqual(
            actual_email_object,
            expected_email_object,
        )

########NEW FILE########
__FILENAME__ = test_process_email
import os.path
import sys

import six

from django_mailbox.models import Mailbox, Message
from django_mailbox.tests.base import EmailMessageTestCase


__all__ = ['TestProcessEmail']


class TestProcessEmail(EmailMessageTestCase):
    def test_message_without_attachments(self):
        message = self._get_email_object('generic_message.eml')

        mailbox = Mailbox.objects.create()
        msg = mailbox.process_incoming_message(message)

        self.assertEqual(
            msg.mailbox,
            mailbox
        )
        self.assertEqual(msg.subject, 'Message Without Attachment')
        self.assertEqual(
            msg.message_id,
            (
                '<CAMdmm+hGH8Dgn-_0xnXJCd=PhyNAiouOYm5zFP0z'
                '-foqTO60zA@mail.gmail.com>'
            )
        )
        self.assertEqual(
            msg.from_header,
            'Adam Coddington <test@adamcoddington.net>',
        )
        self.assertEqual(
            msg.to_header,
            'Adam Coddington <test@adamcoddington.net>',
        )

    def test_message_with_attachments(self):
        message = self._get_email_object('message_with_attachment.eml')

        mailbox = Mailbox.objects.create()
        msg = mailbox.process_incoming_message(message)

        expected_count = 1
        actual_count = msg.attachments.count()

        self.assertEqual(
            expected_count,
            actual_count,
        )

        attachment = msg.attachments.all()[0]
        self.assertEqual(
            attachment.get_filename(),
            'heart.png',
        )

    def test_message_get_text_body(self):
        message = self._get_email_object('multipart_text.eml')

        mailbox = Mailbox.objects.create()
        msg = mailbox.process_incoming_message(message)

        expected_results = 'Hello there!'
        actual_results = msg.get_text_body().strip()

        self.assertEqual(
            expected_results,
            actual_results,
        )

    def test_get_text_body_properly_recomposes_line_continuations(self):
        message = Message()
        email_object = self._get_email_object(
            'message_with_long_text_lines.eml'
        )

        message.get_email_object = lambda: email_object

        actual_text = message.get_text_body()
        expected_text = (
            'The one of us with a bike pump is far ahead, '
            'but a man stopped to help us and gave us his pump.'
        )

        self.assertEqual(
            actual_text,
            expected_text
        )

    def test_get_body_properly_handles_unicode_body(self):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                'messages/generic_message.eml'
            )
        ) as f:
            unicode_body = six.u(f.read())

        message = Message()
        message.body = unicode_body

        expected_body = unicode_body
        actual_body = message.get_email_object().as_string()

        self.assertEqual(
            expected_body,
            actual_body
        )

    def test_message_with_misplaced_utf8_content(self):
        """ Ensure that we properly handle incorrectly encoded messages

        ``message_with_utf8_char.eml``'s primary text payload is marked
        as being iso-8859-1 data, but actually contains UTF-8 bytes.

        """
        email_object = self._get_email_object('message_with_utf8_char.eml')

        msg = self.mailbox.process_incoming_message(email_object)

        actual_text = msg.get_text_body()
        expected_text = six.u(
            'This message contains funny UTF16 characters like this one: '
            '"\xc2\xa0" and this one "\xe2\x9c\xbf".'
        )

        self.assertEqual(
            expected_text,
            actual_text,
        )

    def test_message_with_invalid_content_for_declared_encoding(self):
        """ Ensure that we gracefully handle mis-encoded bodies.

        Should a payload body be misencoded, we should:

        - Not explode

        Note: there is (intentionally) no assertion below; the only guarantee
        we make via this library is that processing this e-mail message will
        not cause an exception to be raised.

        """
        email_object = self._get_email_object(
            'message_with_invalid_content_for_declared_encoding.eml',
        )

        msg = self.mailbox.process_incoming_message(email_object)

        msg.get_text_body()

    def test_message_with_valid_content_in_single_byte_encoding(self):
        email_object = self._get_email_object(
            'message_with_single_byte_encoding.eml',
        )

        msg = self.mailbox.process_incoming_message(email_object)

        actual_body = msg.get_text_body()

        expected_body = six.u(
            '\u042d\u0442\u043e '
            '\u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 '
            '\u0438\u043c\u0435\u0435\u0442 '
            '\u043d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d'
            '\u0443\u044e '
            '\u043a\u043e\u0434\u0438\u0440\u043e\u0432\u043a\u0430.'
        )

        self.assertEqual(
            actual_body,
            expected_body,
        )

    def test_message_with_single_byte_subject_encoding(self):
        email_object = self._get_email_object(
            'message_with_single_byte_extended_subject_encoding.eml',
        )

        msg = self.mailbox.process_incoming_message(email_object)

        expected_subject = six.u(
            '\u00D3\u00E7\u00ED\u00E0\u00E9 \u00EA\u00E0\u00EA '
            '\u00E7\u00E0\u00F0\u00E0\u00E1\u00E0\u00F2\u00FB\u00E2'
            '\u00E0\u00F2\u00FC \u00EE\u00F2 1000$ \u00E2 '
            '\u00ED\u00E5\u00E4\u00E5\u00EB\u00FE!'
        )
        actual_subject = msg.subject
        self.assertEqual(actual_subject, expected_subject)

        if sys.version_info >= (3, 3):
            # There were various bugfixes in Py3k's email module,
            # this is apparently one of them.
            expected_from = six.u('test test <mr.test32@mail.ru>')
        else:
            expected_from = six.u('test test<mr.test32@mail.ru>')
        actual_from = msg.from_header

        self.assertEqual(expected_from, actual_from)

########NEW FILE########
__FILENAME__ = test_transports
import mock
import six

from django_mailbox.tests.base import EmailMessageTestCase
from django_mailbox.transports import ImapTransport, Pop3Transport


class TestImapTransport(EmailMessageTestCase):
    def setUp(self):
        self.arbitrary_hostname = 'one.two.three'
        self.arbitrary_port = 100
        self.ssl = False
        self.transport = ImapTransport(
            self.arbitrary_hostname,
            self.arbitrary_port,
            self.ssl
        )
        self.transport.server = None
        super(TestImapTransport, self).setUp()

    def test_get_email_message(self):
        with mock.patch.object(self.transport, 'server') as server:
            server.search.return_value = (
                'OK',
                [
                    'One',  # This is totally arbitrary
                ]
            )
            server.fetch.return_value = (
                'OK',
                [
                    [
                        '1 (RFC822 {8190}',  # Wat?
                        self._get_email_as_text('generic_message.eml')
                    ],
                    ')',
                ]
            )
            actual_messages = list(self.transport.get_message())

        self.assertEqual(len(actual_messages), 1)

        actual_message = actual_messages[0]
        expected_message = self._get_email_object('generic_message.eml')

        self.assertEqual(expected_message, actual_message)


class TestImapArchivedTransport(EmailMessageTestCase):
    def setUp(self):
        self.arbitrary_hostname = 'one.two.three'
        self.arbitrary_port = 100
        self.ssl = False
        self.archive = 'Archive'
        self.transport = ImapTransport(
            self.arbitrary_hostname,
            self.arbitrary_port,
            self.ssl,
            self.archive
        )
        self.transport.server = None
        super(TestImapArchivedTransport, self).setUp()

    def test_get_email_message(self):
        with mock.patch.object(self.transport, 'server') as server:
            server.search.return_value = (
                'OK',
                [
                    'One',  # This is totally arbitrary
                ]
            )
            server.fetch.return_value = (
                'OK',
                [
                    [
                        '1 (RFC822 {8190}',  # Wat?
                        self._get_email_as_text('generic_message.eml')
                    ],
                    ')',
                ]
            )
            server.list.return_value = (
                'OK',
                [
                    '(\\HasNoChildren) "/" "Archive"'
                ]
            )
            server.copy.return_value = (
                'OK',
                [
                    '[COPYUID 1 2 2] (Success)'
                ]
            )
            actual_messages = list(self.transport.get_message())

        self.assertEqual(len(actual_messages), 1)

        actual_message = actual_messages[0]
        expected_message = self._get_email_object('generic_message.eml')

        self.assertEqual(expected_message, actual_message)



class TestPop3Transport(EmailMessageTestCase):
    def setUp(self):
        self.arbitrary_hostname = 'one.two.three'
        self.arbitrary_port = 100
        self.ssl = False
        self.transport = Pop3Transport(
            self.arbitrary_hostname,
            self.arbitrary_port,
            self.ssl
        )
        self.transport.server = None
        super(TestPop3Transport, self).setUp()

    def test_get_email_message(self):
        with mock.patch.object(self.transport, 'server') as server:
            # Consider this value arbitrary, the second parameter
            # should have one entry per message in the inbox
            server.list.return_value = [None, ['some_msg']]
            server.retr.return_value = [
                '+OK message follows',
                [
                    line.encode('ascii')
                    for line in self._get_email_as_text(
                        'generic_message.eml'
                    ).decode('ascii').split('\n')
                ],
                10018,  # Some arbitrary size, ideally matching the above
            ]

            actual_messages = list(self.transport.get_message())

        self.assertEqual(len(actual_messages), 1)

        actual_message = actual_messages[0]
        expected_message = self._get_email_object('generic_message.eml')

        self.assertEqual(expected_message, actual_message)

########NEW FILE########
__FILENAME__ = babyl
from mailbox import Babyl
from django_mailbox.transports.generic import GenericFileMailbox


class BabylTransport(GenericFileMailbox):
    _variant = Babyl

########NEW FILE########
__FILENAME__ = base
import email

import six

# Do *not* remove this, we need to use this in subclasses of EmailTransport
if six.PY3:
    from email.errors import MessageParseError
else:
    from email.Errors import MessageParseError


class EmailTransport(object):
    def get_email_from_bytes(self, contents):
        if six.PY3:
            message = email.message_from_bytes(contents)
        else:
            message = email.message_from_string(contents)

        return message

########NEW FILE########
__FILENAME__ = generic
from .base import EmailTransport


class GenericFileMailbox(EmailTransport):
    _variant = None
    _path = None

    def __init__(self, path):
        super(GenericFileMailbox, self).__init__()
        self._path = path

    def get_instance(self):
        return self._variant(self._path)

    def get_message(self):
        repository = self.get_instance()
        repository.lock()
        for key, message in repository.items():
            repository.remove(key)
            yield message
        repository.unlock()

########NEW FILE########
__FILENAME__ = imap
from imaplib import IMAP4, IMAP4_SSL

from .base import EmailTransport, MessageParseError


class ImapTransport(EmailTransport):
    def __init__(self, hostname, port=None, ssl=False, archive=''):
        self.hostname = hostname
        self.port = port
        self.archive = archive
        if ssl:
            self.transport = IMAP4_SSL
            if not self.port:
                self.port = 993
        else:
            self.transport = IMAP4
            if not self.port:
                self.port = 143

    def connect(self, username, password):
        self.server = self.transport(self.hostname, self.port)
        typ, msg = self.server.login(username, password)
        self.server.select()

    def get_message(self):
        typ, inbox = self.server.search(None, 'ALL')

        if not inbox[0]:
            return

        if self.archive:
            typ, folders = self.server.list(pattern=self.archive)
            if folders[0] is None:
                # If the archive folder does not exist, create it
                self.server.create(self.archive)

        for key in inbox[0].split():
            try:
                typ, msg_contents = self.server.fetch(key, '(RFC822)')
                message = self.get_email_from_bytes(msg_contents[0][1])
                yield message
            except MessageParseError:
                continue

            if self.archive:
                self.server.copy(key, self.archive)

            self.server.store(key, "+FLAGS", "\\Deleted")
        self.server.expunge()
        return

########NEW FILE########
__FILENAME__ = maildir
from mailbox import Maildir
from django_mailbox.transports.generic import GenericFileMailbox


class MaildirTransport(GenericFileMailbox):
    _variant = Maildir

    def get_instance(self):
        return self._variant(self._path, None)

########NEW FILE########
__FILENAME__ = mbox
from mailbox import mbox
from django_mailbox.transports.generic import GenericFileMailbox


class MboxTransport(GenericFileMailbox):
    _variant = mbox

########NEW FILE########
__FILENAME__ = mh
from mailbox import MH
from django_mailbox.transports.generic import GenericFileMailbox


class MHTransport(GenericFileMailbox):
    _variant = MH

########NEW FILE########
__FILENAME__ = mmdf
from mailbox import MMDF
from django_mailbox.transports.generic import GenericFileMailbox


class MMDFTransport(GenericFileMailbox):
    _variant = MMDF

########NEW FILE########
__FILENAME__ = pop3
import six

from poplib import POP3, POP3_SSL

from .base import EmailTransport, MessageParseError


class Pop3Transport(EmailTransport):
    def __init__(self, hostname, port=None, ssl=False):
        self.hostname = hostname
        self.port = port
        if ssl:
            self.transport = POP3_SSL
            if not self.port:
                self.port = 995
        else:
            self.transport = POP3
            if not self.port:
                self.port = 110

    def connect(self, username, password):
        self.server = self.transport(self.hostname, self.port)
        self.server.user(username)
        self.server.pass_(password)

    def get_message_body(self, message_lines):
        if six.PY3:
            return six.binary_type('\r\n', 'ascii').join(message_lines)
        return '\r\n'.join(message_lines)

    def get_message(self):
        message_count = len(self.server.list()[1])
        for i in range(message_count):
            try:
                msg_contents = self.get_message_body(
                    self.server.retr(i + 1)[1]
                )
                message = self.get_email_from_bytes(msg_contents)
                yield message
            except MessageParseError:
                continue
            self.server.dele(i + 1)
        self.server.quit()
        return

########NEW FILE########
__FILENAME__ = utils
import email.header
import logging

import six

from django.conf import settings


logger = logging.getLogger(__name__)


DEFAULT_CHARSET = getattr(
    settings,
    'DJANGO_MAILBOX_DEFAULT_CHARSET',
    'iso8859-1',
)


def convert_header_to_unicode(header):
    def _decode(value, encoding):
        if isinstance(value, six.text_type):
            return value
        if not encoding or encoding == 'unknown-8bit':
            encoding = DEFAULT_CHARSET
        return value.decode(encoding, 'REPLACE')

    try:
        return ''.join(
            [
                (
                    _decode(bytestr, encoding)
                ) for bytestr, encoding in email.header.decode_header(header)
            ]
        )
    except UnicodeDecodeError:
        logger.exception(
            'Errors encountered decoding header %s into encoding %s.',
            header,
            DEFAULT_CHARSET,
        )
        return unicode(header, DEFAULT_CHARSET, 'replace')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-mailbox documentation build configuration file, created by
# sphinx-quickstart on Tue Jan 22 20:29:12 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-mailbox'
copyright = u'2014, Adam Coddington'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '3.3'
# The full version, including alpha/beta/rc tags.
release = '3.3'

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
htmlhelp_basename = 'django-mailboxdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-mailbox.tex', u'django-mailbox Documentation',
   u'Adam Coddington', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-mailbox', u'django-mailbox Documentation',
     [u'Adam Coddington'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-mailbox', u'django-mailbox Documentation',
   u'Adam Coddington', 'django-mailbox', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
