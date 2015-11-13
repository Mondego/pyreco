__FILENAME__ = clean_kombu_messages
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    requires_model_validation = True

    def handle(self, *args, **options):
        from djkombu.models import Message

        print("Removing %s invisible messages... " % (
            Message.objects.filter(visible=False).count(), ))
        Message.objects.cleanup()




########NEW FILE########
__FILENAME__ = managers
# Partially stolen from Django Queue Service
# (http://code.google.com/p/django-queue-service)
from django.db import transaction, connection, models
try:
    from django.db import connections, router
except ImportError:  # pre-Django 1.2
    connections = router = None


class QueueManager(models.Manager):

    def publish(self, queue_name, payload):
        queue, created = self.get_or_create(name=queue_name)
        queue.messages.create(payload=payload)

    def fetch(self, queue_name):
        try:
            queue = self.get(name=queue_name)
        except self.model.DoesNotExist:
            return

        return queue.messages.pop()

    def size(self, queue_name):
        return self.get(name=queue_name).messages.count()

    def purge(self, queue_name):
        try:
            queue = self.get(name=queue_name)
        except self.model.DoesNotExist:
            return

        messages = queue.messages.all()
        count = messages.count()
        messages.delete()
        return count


class MessageManager(models.Manager):
    _messages_received = [0]
    cleanup_every = 10

    def pop(self):
        try:
            resultset = self.filter(visible=True).order_by('sent_at', 'id')
            result = resultset[0:1].get()
            result.visible = False
            result.save()
            recv = self.__class__._messages_received
            recv[0] += 1
            if not recv[0] % self.cleanup_every:
                self.cleanup()
            return result.payload
        except self.model.DoesNotExist:
            pass

    def cleanup(self):
        cursor = self.connection_for_write().cursor()
        try:
            cursor.execute("DELETE FROM %s WHERE visible=%%s" % (
                            self.model._meta.db_table, ), (False, ))
        except:
            transaction.rollback_unless_managed()
        else:
            transaction.commit_unless_managed()

    def connection_for_write(self):
        if connections:
            return connections[router.db_for_write(self.model)]
        return connection

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from djkombu.managers import QueueManager, MessageManager


class Queue(models.Model):
    name = models.CharField(_("name"), max_length=200, unique=True)

    objects = QueueManager()

    class Meta:
        verbose_name = _("queue")
        verbose_name_plural = _("queues")


class Message(models.Model):
    visible = models.BooleanField(default=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True,
                auto_now_add=True)
    payload = models.TextField(_("payload"), null=False)
    queue = models.ForeignKey(Queue, related_name="messages")

    objects = MessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

########NEW FILE########
__FILENAME__ = transport
from Queue import Empty

from anyjson import serialize, deserialize
from kombu.transport import virtual

from django.conf import settings
from django.core import exceptions as errors

from djkombu.models import Queue

POLLING_INTERVAL = getattr(settings, "DJKOMBU_POLLING_INTERVAL", 5.0)


class Channel(virtual.Channel):

    def _new_queue(self, queue, **kwargs):
        Queue.objects.get_or_create(name=queue)

    def _put(self, queue, message, **kwargs):
        Queue.objects.publish(queue, serialize(message))

    def basic_consume(self, queue, *args, **kwargs):
        qinfo = self.state.bindings[queue]
        exchange = qinfo[0]
        if self.typeof(exchange).type == "fanout":
            return
        super(Channel, self).basic_consume(queue, *args, **kwargs)

    def _get(self, queue):
        #self.refresh_connection()
        m = Queue.objects.fetch(queue)
        if m:
            return deserialize(m)
        raise Empty()

    def _size(self, queue):
        return Queue.objects.size(queue)

    def _purge(self, queue):
        return Queue.objects.purge(queue)

    def refresh_connection(self):
        from django import db
        db.close_connection()


class DatabaseTransport(virtual.Transport):
    Channel = Channel

    default_port = 0
    polling_interval = POLLING_INTERVAL
    connection_errors = ()
    channel_errors = (errors.ObjectDoesNotExist,
                      errors.MultipleObjectsReturned)

########NEW FILE########
