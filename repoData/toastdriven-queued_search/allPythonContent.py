__FILENAME__ = indexes
raise DeprecationWarning("This module is no longer used. Please setup & use the ``QueuedSignalProcessor``.")

########NEW FILE########
__FILENAME__ = process_search_queue
import logging
from optparse import make_option
from queues import queues, QueueException
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import NoArgsCommand
from django.db.models.loading import get_model
from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.exceptions import NotHandled
from queued_search.utils import get_queue_name


DEFAULT_BATCH_SIZE = None
LOG_LEVEL = getattr(settings, 'SEARCH_QUEUE_LOG_LEVEL', logging.ERROR)

logging.basicConfig(
    level=LOG_LEVEL
)

class Command(NoArgsCommand):
    help = "Consume any objects that have been queued for modification in search."
    can_import_settings = True
    base_options = (
        make_option('-b', '--batch-size', action='store', dest='batchsize',
            default=None, type='int',
            help='Number of items to index at once.'
        ),
        make_option("-u", "--using", action="store", type="string", dest="using", default=DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        ),
    )
    option_list = NoArgsCommand.option_list + base_options

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('queued_search')
        self.actions = {
            'update': set(),
            'delete': set(),
        }
        self.processed_updates = set()
        self.processed_deletes = set()

    def handle_noargs(self, **options):
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE) or 1000
        self.using = options.get('using')
        # Setup the queue.
        self.queue = queues.Queue(get_queue_name())

        # Check if enough is there to process.
        if not len(self.queue):
            self.log.info("Not enough items in the queue to process.")

        self.log.info("Starting to process the queue.")

        # Consume the whole queue first so that we can group update/deletes
        # for efficiency.
        try:
            while True:
                message = self.queue.read()

                if not message:
                    break

                self.process_message(message)
        except QueueException:
            # We've run out of items in the queue.
            pass

        self.log.info("Queue consumed.")

        try:
            self.handle_updates()
            self.handle_deletes()
        except Exception as e:
            self.log.error('Exception seen during processing: %s' % e)
            self.requeue()
            raise e

        self.log.info("Processing complete.")

    def requeue(self):
        """
        On failure, requeue all unprocessed messages.
        """
        self.log.error('Requeuing unprocessed messages.')
        update_count = 0
        delete_count = 0

        for update in self.actions['update']:
            if not update in self.processed_updates:
                self.queue.write('update:%s' % update)
                update_count += 1

        for delete in self.actions['delete']:
            if not delete in self.processed_deletes:
                self.queue.write('delete:%s' % delete)
                delete_count += 1

        self.log.error('Requeued %d updates and %d deletes.' % (update_count, delete_count))

    def process_message(self, message):
        """
        Given a message added by the ``QueuedSearchIndex``, add it to either
        the updates or deletes for processing.
        """
        self.log.debug("Processing message '%s'..." % message)

        if not ':' in message:
            self.log.error("Unable to parse message '%s'. Moving on..." % message)
            return

        action, obj_identifier = message.split(':')
        self.log.debug("Saw '%s' on '%s'..." % (action, obj_identifier))

        if action == 'update':
            # Remove it from the delete list if it's present.
            # Since we process the queue in order, this could occur if an
            # object was deleted then readded, in which case we should ignore
            # the delete and just update the index.
            if obj_identifier in self.actions['delete']:
                self.actions['delete'].remove(obj_identifier)

            self.actions['update'].add(obj_identifier)
            self.log.debug("Added '%s' to the update list." % obj_identifier)
        elif action == 'delete':
            # Remove it from the update list if it's present.
            # Since we process the queue in order, this could occur if an
            # object was updated then deleted, in which case we should ignore
            # the update and just delete the document from the index.
            if obj_identifier in self.actions['update']:
                self.actions['update'].remove(obj_identifier)

            self.actions['delete'].add(obj_identifier)
            self.log.debug("Added '%s' to the delete list." % obj_identifier)
        else:
            self.log.error("Unrecognized action '%s'. Moving on..." % action)

    def split_obj_identifier(self, obj_identifier):
        """
        Break down the identifier representing the instance.

        Converts 'notes.note.23' into ('notes.note', 23).
        """
        bits = obj_identifier.split('.')

        if len(bits) < 2:
            self.log.error("Unable to parse object identifer '%s'. Moving on..." % obj_identifier)
            return (None, None)

        pk = bits[-1]
        # In case Django ever handles full paths...
        object_path = '.'.join(bits[:-1])
        return (object_path, pk)

    def get_model_class(self, object_path):
        """Fetch the model's class in a standarized way."""
        bits = object_path.split('.')
        app_name = '.'.join(bits[:-1])
        classname = bits[-1]
        model_class = get_model(app_name, classname)

        if model_class is None:
            self.log.error("Could not load model from '%s'. Moving on..." % object_path)
            return None

        return model_class

    def get_instance(self, model_class, pk):
        """Fetch the instance in a standarized way."""
        try:
            instance = model_class.objects.get(pk=pk)
        except ObjectDoesNotExist:
            self.log.error("Couldn't load model instance with pk #%s. Somehow it went missing?" % pk)
            return None
        except MultipleObjectsReturned:
            self.log.error("More than one object with pk #%s. Oops?" % pk)
            return None

        return instance

    def get_index(self, model_class):
        """Fetch the model's registered ``SearchIndex`` in a standarized way."""
        try:
            return connections['default'].get_unified_index().get_index(model_class)
        except NotHandled:
            self.log.error("Couldn't find a SearchIndex for %s." % model_class)
            return None

    def handle_updates(self):
        """
        Process through all updates.

        Updates are grouped by model class for maximum batching/minimized
        merging.
        """
        # For grouping same model classes for efficiency.
        updates = {}
        previous_path = None
        current_index = None

        for obj_identifier in self.actions['update']:
            (object_path, pk) = self.split_obj_identifier(obj_identifier)

            if object_path is None or pk is None:
                self.log.error("Skipping.")
                continue

            if object_path not in updates:
                updates[object_path] = []

            updates[object_path].append(pk)

        # We've got all updates grouped. Process them.
        for object_path, pks in updates.items():
            model_class = self.get_model_class(object_path)

            if object_path != previous_path:
                previous_path = object_path
                current_index = self.get_index(model_class)

            if not current_index:
                self.log.error("Skipping.")
                continue

            instances = [self.get_instance(model_class, pk) for pk in pks]

            # Filter out what we didn't find.
            instances = [instance for instance in instances if instance is not None]

            # Update the batch of instances for this class.
            # Use the backend instead of the index because we can batch the
            # instances.
            total = len(instances)
            self.log.debug("Indexing %d %s." % (total, object_path))

            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                batch_instances = instances[start:end]

                self.log.debug("  indexing %s - %d of %d." % (start+1, end, total))
                current_index._get_backend(self.using).update(current_index, batch_instances)

                for updated in batch_instances:
                    self.processed_updates.add("%s.%s" % (object_path, updated.pk))

            self.log.debug("Updated objects for '%s': %s" % (object_path, ", ".join(pks)))

    def handle_deletes(self):
        """
        Process through all deletes.

        Deletes are grouped by model class for maximum batching.
        """
        deletes = {}
        previous_path = None
        current_index = None

        for obj_identifier in self.actions['delete']:
            (object_path, pk) = self.split_obj_identifier(obj_identifier)

            if object_path is None or pk is None:
                self.log.error("Skipping.")
                continue

            if object_path not in deletes:
                deletes[object_path] = []

            deletes[object_path].append(obj_identifier)

        # We've got all deletes grouped. Process them.
        for object_path, obj_identifiers in deletes.items():
            model_class = self.get_model_class(object_path)

            if object_path != previous_path:
                previous_path = object_path
                current_index = self.get_index(model_class)

            if not current_index:
                self.log.error("Skipping.")
                continue

            pks = []

            for obj_identifier in obj_identifiers:
                current_index.remove_object(obj_identifier, using=self.using)
                pks.append(self.split_obj_identifier(obj_identifier)[1])
                self.processed_deletes.add(obj_identifier)

            self.log.debug("Deleted objects for '%s': %s" % (object_path, ", ".join(pks)))

########NEW FILE########
__FILENAME__ = models
# O HAI.
# Faking ``models.py`` so Django sees the app/management command.

########NEW FILE########
__FILENAME__ = signals
from queues import queues
from django.db import models
from haystack.signals import BaseSignalProcessor
from haystack.utils import get_identifier
from queued_search.utils import get_queue_name


class QueuedSignalProcessor(BaseSignalProcessor):
    def setup(self):
        models.signals.post_save.connect(self.enqueue_save)
        models.signals.post_delete.connect(self.enqueue_delete)

    def teardown(self):
        models.signals.post_save.disconnect(self.enqueue_save)
        models.signals.post_delete.disconnect(self.enqueue_delete)

    def enqueue_save(self, sender, instance, **kwargs):
        return self.enqueue('update', instance)

    def enqueue_delete(self, sender, instance, **kwargs):
        return self.enqueue('delete', instance)

    def enqueue(self, action, instance):
        """
        Shoves a message about how to update the index into the queue.

        This is a standardized string, resembling something like::

            ``update:notes.note.23``
            # ...or...
            ``delete:weblog.entry.8``
        """
        message = "%s:%s" % (action, get_identifier(instance))
        queue = queues.Queue(get_queue_name())
        return queue.write(message)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings


def get_queue_name():
    """
    Standized way to fetch the queue name.

    Can be overridden by specifying ``SEARCH_QUEUE_NAME`` in your settings.

    Given that the queue name is used in disparate places, this is primarily
    for sanity.
    """
    return getattr(settings, 'SEARCH_QUEUE_NAME', 'haystack_search_queue')

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
import logging

from django.conf import settings


settings.configure(
    DATABASES={
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory;'}
    },
    INSTALLED_APPS=[
        'haystack',
        'queued_search',
        'tests',
    ],
    HAYSTACK_CONNECTIONS={
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index')
        }
    },
    HAYSTACK_SIGNAL_PROCESSOR='queued_search.signals.QueuedSignalProcessor',
    QUEUE_BACKEND='dummy',
    SEARCH_QUEUE_LOG_LEVEL=logging.DEBUG
)


def runtests(*test_args):
    import django.test.utils

    runner_class = django.test.utils.get_runner(settings)
    test_runner = runner_class(verbosity=1, interactive=True, failfast=False)
    failures = test_runner.run_tests(['tests'])
    sys.exit(failures)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models


# Ghetto app!
class Note(models.Model):
    title = models.CharField(max_length=128)
    content = models.TextField()
    author = models.CharField(max_length=64)
    created = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes
from .models import Note


# Simplest possible subclass that could work.
class NoteIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='content')

    def get_model(self):
        return Note

########NEW FILE########
__FILENAME__ = tests
import logging
from queues import queues, QueueException
from django.core.management import call_command
from django.test import TestCase
from haystack import connections
from haystack.query import SearchQuerySet
from queued_search.management.commands.process_search_queue import Command as ProcessSearchQueueCommand
from queued_search.utils import get_queue_name
from .models import Note


class AssertableHandler(logging.Handler):
    stowed_messages = []

    def emit(self, record):
        AssertableHandler.stowed_messages.append(record.getMessage())


assertable = AssertableHandler()
logging.getLogger('queued_search').addHandler(assertable)


class QueuedSearchIndexTestCase(TestCase):
    def setUp(self):
        super(QueuedSearchIndexTestCase, self).setUp()

        # Nuke the queue.
        queues.delete_queue(get_queue_name())

        # Nuke the index.
        call_command('clear_index', interactive=False, verbosity=0)

        # Get a queue connection so we can poke at it.
        self.queue = queues.Queue(get_queue_name())

    def test_update(self):
        self.assertEqual(len(self.queue), 0)

        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 1)

        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 2)

        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )

        self.assertEqual(len(self.queue), 3)

        note3.title = 'Final test note FOR REAL'
        note3.save()

        self.assertEqual(len(self.queue), 4)

        # Pull the whole queue.
        messages = []

        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass

        self.assertEqual(messages, [u'update:tests.note.1', u'update:tests.note.2', u'update:tests.note.3', u'update:tests.note.3'])

    def test_delete(self):
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )
        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )

        # Dump the queue in preparation for the deletes.
        queues.delete_queue(get_queue_name())
        self.queue = queues.Queue(get_queue_name())

        self.assertEqual(len(self.queue), 0)
        note1.delete()
        self.assertEqual(len(self.queue), 1)
        note2.delete()
        self.assertEqual(len(self.queue), 2)
        note3.delete()
        self.assertEqual(len(self.queue), 3)

        # Pull the whole queue.
        messages = []

        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass

        self.assertEqual(messages, [u'delete:tests.note.1', u'delete:tests.note.2', u'delete:tests.note.3'])

    def test_complex(self):
        self.assertEqual(len(self.queue), 0)

        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 1)

        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 2)

        note1.delete()
        self.assertEqual(len(self.queue), 3)

        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )

        self.assertEqual(len(self.queue), 4)

        note3.title = 'Final test note FOR REAL'
        note3.save()

        self.assertEqual(len(self.queue), 5)

        note3.delete()
        self.assertEqual(len(self.queue), 6)

        # Pull the whole queue.
        messages = []

        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass

        self.assertEqual(messages, [u'update:tests.note.1', u'update:tests.note.2', u'delete:tests.note.1', u'update:tests.note.3', u'update:tests.note.3', u'delete:tests.note.3'])


class ProcessSearchQueueTestCase(TestCase):
    def setUp(self):
        super(ProcessSearchQueueTestCase, self).setUp()

        # Nuke the queue.
        queues.delete_queue(get_queue_name())

        # Nuke the index.
        call_command('clear_index', interactive=False, verbosity=0)

        # Get a queue connection so we can poke at it.
        self.queue = queues.Queue(get_queue_name())

        # Clear out and capture log messages.
        AssertableHandler.stowed_messages = []

        self.psqc = ProcessSearchQueueCommand()

    def test_process_mesage(self):
        self.assertEqual(self.psqc.actions, {'update': set([]), 'delete': set([])})

        self.psqc.process_message('update:tests.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.1']), 'delete': set([])})

        self.psqc.process_message('delete:tests.note.2')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.1']), 'delete': set(['tests.note.2'])})

        self.psqc.process_message('update:tests.note.2')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.1', 'tests.note.2']), 'delete': set([])})

        self.psqc.process_message('delete:tests.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.2']), 'delete': set(['tests.note.1'])})

        self.psqc.process_message('wtfmate:tests.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.2']), 'delete': set(['tests.note.1'])})

        self.psqc.process_message('just plain wrong')
        self.assertEqual(self.psqc.actions, {'update': set(['tests.note.2']), 'delete': set(['tests.note.1'])})

    def test_split_obj_identifier(self):
        self.assertEqual(self.psqc.split_obj_identifier('tests.note.1'), ('tests.note', '1'))
        self.assertEqual(self.psqc.split_obj_identifier('myproject.tests.note.73'), ('myproject.tests.note', '73'))
        self.assertEqual(self.psqc.split_obj_identifier('wtfmate.1'), ('wtfmate', '1'))
        self.assertEqual(self.psqc.split_obj_identifier('wtfmate'), (None, None))

    def test_processing(self):
        self.assertEqual(len(self.queue), 0)

        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 1)

        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 2)

        note1.delete()
        self.assertEqual(len(self.queue), 3)

        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )

        self.assertEqual(len(self.queue), 4)

        note3.title = 'Final test note FOR REAL'
        note3.save()

        self.assertEqual(len(self.queue), 5)

        note3.delete()
        self.assertEqual(len(self.queue), 6)

        self.assertEqual(AssertableHandler.stowed_messages, [])

        # Call the command.
        call_command('process_search_queue')

        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:tests.note.1'...",
            u"Saw 'update' on 'tests.note.1'...",
            u"Added 'tests.note.1' to the update list.",
            u"Processing message 'update:tests.note.2'...",
            u"Saw 'update' on 'tests.note.2'...",
            u"Added 'tests.note.2' to the update list.",
            u"Processing message 'delete:tests.note.1'...",
            u"Saw 'delete' on 'tests.note.1'...",
            u"Added 'tests.note.1' to the delete list.",
            u"Processing message 'update:tests.note.3'...",
            u"Saw 'update' on 'tests.note.3'...",
            u"Added 'tests.note.3' to the update list.",
            u"Processing message 'update:tests.note.3'...",
            u"Saw 'update' on 'tests.note.3'...",
            u"Added 'tests.note.3' to the update list.",
            u"Processing message 'delete:tests.note.3'...",
            u"Saw 'delete' on 'tests.note.3'...",
            u"Added 'tests.note.3' to the delete list.",
            'Queue consumed.',
            u'Indexing 1 tests.note.',
            '  indexing 1 - 1 of 1.',
            u"Updated objects for 'tests.note': 2",
            u"Deleted objects for 'tests.note': 1, 3",
            'Processing complete.'
        ])
        self.assertEqual(SearchQuerySet().all().count(), 1)

    def test_requeuing(self):
        self.assertEqual(len(self.queue), 0)

        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 1)

        # Write a failed message.
        self.queue.write('update:tests.note.abc')
        self.assertEqual(len(self.queue), 2)

        self.assertEqual(AssertableHandler.stowed_messages, [])

        try:
            # Call the command, which will fail.
            call_command('process_search_queue')
            self.fail("The command ran successfully, which is incorrect behavior in this case.")
        except:
            # We don't care that it failed. We just want to examine the state
            # of things afterward.
            pass

        self.assertEqual(len(self.queue), 2)

        # Pull the whole queue.
        messages = []

        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass

        self.assertEqual(messages, [u'update:tests.note.1', 'update:tests.note.abc'])
        self.assertEqual(len(self.queue), 0)

        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:tests.note.1'...",
            u"Saw 'update' on 'tests.note.1'...",
            u"Added 'tests.note.1' to the update list.",
            "Processing message 'update:tests.note.abc'...",
            "Saw 'update' on 'tests.note.abc'...",
            "Added 'tests.note.abc' to the update list.",
            'Queue consumed.',
            "Exception seen during processing: invalid literal for int() with base 10: 'abc'",
            'Requeuing unprocessed messages.',
            'Requeued 2 updates and 0 deletes.'
        ])

        # Start over.
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 1)

        note2 = Note.objects.create(
            title='Another test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )

        self.assertEqual(len(self.queue), 2)

        # Now delete it.
        note2.delete()

        # Write a failed message.
        self.queue.write('delete:tests.note.abc')
        self.assertEqual(len(self.queue), 4)

        AssertableHandler.stowed_messages = []
        self.assertEqual(AssertableHandler.stowed_messages, [])

        try:
            # Call the command, which will fail again.
            call_command('process_search_queue')
            self.fail("The command ran successfully, which is incorrect behavior in this case.")
        except:
            # We don't care that it failed. We just want to examine the state
            # of things afterward.
            pass

        # Everything but the bad bit of data should have processed.
        self.assertEqual(len(self.queue), 1)

        # Pull the whole queue.
        messages = []

        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass

        self.assertEqual(messages, ['delete:tests.note.abc'])
        self.assertEqual(len(self.queue), 0)

        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:tests.note.2'...",
            u"Saw 'update' on 'tests.note.2'...",
            u"Added 'tests.note.2' to the update list.",
            u"Processing message 'update:tests.note.3'...",
            u"Saw 'update' on 'tests.note.3'...",
            u"Added 'tests.note.3' to the update list.",
            u"Processing message 'delete:tests.note.3'...",
            u"Saw 'delete' on 'tests.note.3'...",
            u"Added 'tests.note.3' to the delete list.",
            "Processing message 'delete:tests.note.abc'...",
            "Saw 'delete' on 'tests.note.abc'...",
            "Added 'tests.note.abc' to the delete list.",
            'Queue consumed.',
            u'Indexing 1 tests.note.',
            '  indexing 1 - 1 of 1.',
            u"Updated objects for 'tests.note': 2",
            "Exception seen during processing: Provided string 'tests.note.abc' is not a valid identifier.",
            'Requeuing unprocessed messages.',
            'Requeued 0 updates and 1 deletes.'
        ])

########NEW FILE########
