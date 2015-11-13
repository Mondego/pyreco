__FILENAME__ = queued_indexer
from django.db.models import signals
from django.db.models.loading import get_model

from haystack import indexes
from haystack import site

from tasks import SearchIndexUpdateTask

def remove_instance_from_index(instance):
    model_class = get_model(instance._meta.app_label, instance._meta.module_name)
    search_index = site.get_index(model_class)
    search_index.remove_object(instance)

class QueuedSearchIndex(indexes.SearchIndex):
    """
    A ``SearchIndex`` subclass that enqueues updates for later processing.

    Deletes are handled instantly since a reference, not the instance, is put on the queue. It would not be hard
    to update this to handle deletes as well (with a delete task).
    """
    # We override the built-in _setup_* methods to connect the enqueuing operation.
    def _setup_save(self, model):
        signals.post_save.connect(self.enqueue_save, sender=model)

    def _setup_delete(self, model):
        signals.post_delete.connect(self.enqueue_delete, sender=model)

    def _teardown_save(self, model):
        signals.post_save.disconnect(self.enqueue_save, sender=model)

    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)

    def enqueue_save(self, instance, **kwargs):
        SearchIndexUpdateTask.delay(instance._meta.app_label, instance._meta.module_name, instance._get_pk_val())

    def enqueue_delete(self, instance, **kwargs):
        remove_instance_from_index(instance)

########NEW FILE########
__FILENAME__ = tasks
from django.db.models.loading import get_model

from haystack import site
from haystack.management.commands import update_index

from celery.task import Task, PeriodicTask
from celery.task.schedules import crontab

class SearchIndexUpdateTask(Task):
    name = "search.index.update"
    routing_key = 'search.index.update'
    default_retry_delay = 5 * 60
    max_retries = 1

    def run(self, app_name, model_name, pk, **kwargs):
        logger = self.get_logger(**kwargs)
        try:
            model_class = get_model(app_name, model_name)
            instance = model_class.objects.get(pk=pk)
            search_index = site.get_index(model_class)
            search_index.update_object(instance)
        except Exception, exc:
            logger.error(exc)
            self.retry([app_name, model_name, pk], kwargs, exc=exc)

class SearchIndexUpdatePeriodicTask(PeriodicTask):
    routing_key = 'periodic.search.update_index'
    run_every = crontab(hour=4, minute=0)

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info("Starting update index")
        # Run the update_index management command
        update_index.Command().handle()
        logger.info("Finishing update index")


########NEW FILE########
