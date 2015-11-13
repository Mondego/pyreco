__FILENAME__ = admin
from django.contrib import admin

from rest_hooks.models import Hook


class HookAdmin(admin.ModelAdmin):
    list_display = [f.name for f in Hook._meta.fields]
    raw_id_fields = ['user',]
admin.site.register(Hook, HookAdmin)

########NEW FILE########
__FILENAME__ = client
import threading
import collections

import requests


class FlushThread(threading.Thread):
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        self.client.sync_flush()


class Client(object):
    """
    Manages a simple pool of threads to flush the queue of requests.
    """
    def __init__(self, num_threads=3):
        self.queue = collections.deque()

        self.flush_lock = threading.Lock()
        self.num_threads = num_threads
        self.flush_threads = [FlushThread(self) for _ in range(self.num_threads)]
        self.total_sent = 0

    def enqueue(self, method, *args, **kwargs):
        self.queue.append((method, args, kwargs))
        self.refresh_threads()

    def get(self, *args, **kwargs):
        self.enqueue('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        self.enqueue('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        self.enqueue('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        self.enqueue('delete', *args, **kwargs)

    def refresh_threads(self):
        with self.flush_lock:
            # refresh if there are jobs to do and no threads are alive
            if len(self.queue) > 0:
                to_refresh = [index for index, thread in enumerate(self.flush_threads) if not thread.is_alive()]
                for index in to_refresh:
                    self.flush_threads[index] = FlushThread(self)
                    self.flush_threads[index].start()

    def sync_flush(self):
        while len(self.queue) > 0:
            method, args, kwargs = self.queue.pop()
            getattr(requests, method)(*args, **kwargs)
            self.total_sent += 1

########NEW FILE########
__FILENAME__ = models
import requests

from django.conf import settings
from django.core import serializers, exceptions
from django.db import models
from django.utils import simplejson as json

from rest_hooks.utils import get_module, find_and_fire_hook, distill_model_event

from rest_hooks import signals


HOOK_EVENTS = getattr(settings, 'HOOK_EVENTS', None)
if HOOK_EVENTS is None:
    raise Exception('You need to define settings.HOOK_EVENTS!')

if getattr(settings, 'HOOK_THREADING', True):
    from rest_hooks.client import Client
    client = Client()
else:
    client = requests

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class Hook(models.Model):
    """
    Stores a representation of a Hook.
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(AUTH_USER_MODEL, related_name='hooks')
    event = models.CharField('Event', max_length=64,
                                      db_index=True,
                                      choices=[(e, e) for e in HOOK_EVENTS.keys()])
    target = models.URLField('Target URL', max_length=255)

    def dict(self):
        return {
            'id': self.id,
            'event': self.event,
            'target': self.target
        }

    def serialize_hook(self, instance):
        """
        Serialize the object down to Python primitives.

        By default it uses Django's built in serializer.
        """
        if getattr(instance, 'serialize_hook', None) and callable(instance.serialize_hook):
            return instance.serialize_hook(hook=self)
        if getattr(settings, 'HOOK_SERIALIZER', None):
            serializer = get_module(settings.HOOK_SERIALIZER)
            return serializer(instance, hook=self)
        # if no user defined serializers, fallback to the django builtin!
        return {
            'hook': self.dict(),
            'data': serializers.serialize('python', [instance])[0]
        }

    def deliver_hook(self, instance, payload_override=None):
        """
        Deliver the payload to the target URL.

        By default it serializes to JSON and POSTs.
        """
        payload = payload_override or self.serialize_hook(instance)
        if getattr(settings, 'HOOK_DELIVERER', None):
            deliverer = get_module(settings.HOOK_DELIVERER)
            deliverer(self.target, payload, instance=instance, hook=self)
        else:
            client.post(
                url=self.target,
                data=json.dumps(payload, cls=serializers.json.DjangoJSONEncoder),
                headers={'Content-Type': 'application/json'}
            )

        signals.hook_sent_event.send_robust(sender=self.__class__, payload=payload, instance=instance, hook=self)
        return None


    def __unicode__(self):
        return u'{} => {}'.format(self.event, self.target)


##############
### EVENTS ###
##############

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from rest_hooks.signals import hook_event, raw_hook_event


get_opts = lambda m: m._meta.concrete_model._meta

@receiver(post_save, dispatch_uid='instance-saved-hook')
def model_saved(sender, instance,
                        created,
                        raw,
                        using,
                        **kwargs):
    """
    Automatically triggers "created" and "updated" actions.
    """
    opts = get_opts(instance)
    model = '.'.join([opts.app_label, opts.object_name])
    action = 'created' if created else 'updated'
    distill_model_event(instance, model, action)

@receiver(post_delete, dispatch_uid='instance-deleted-hook')
def model_deleted(sender, instance,
                          using,
                          **kwargs):
    """
    Automatically triggers "deleted" actions.
    """
    opts = get_opts(instance)
    model = '.'.join([opts.app_label, opts.object_name])
    distill_model_event(instance, model, 'deleted')

@receiver(hook_event, dispatch_uid='instance-custom-hook')
def custom_action(sender, action,
                          instance,
                          user=None,
                          **kwargs):
    """
    Manually trigger a custom action (or even a standard action).
    """
    opts = get_opts(instance)
    model = '.'.join([opts.app_label, opts.object_name])
    distill_model_event(instance, model, action, user_override=user)

@receiver(raw_hook_event, dispatch_uid='raw-custom-hook')
def raw_custom_event(sender, event_name,
                             payload,
                             user,
                             send_hook_meta=True,
                             instance=None,
                             **kwargs):
    """
    Give a full payload
    """
    hooks = Hook.objects.filter(user=user, event=event_name)

    for hook in hooks:
        new_payload = payload
        if send_hook_meta:
            new_payload = {
                'hook': hook.dict(),
                'data': payload
            }

        hook.deliver_hook(instance, payload_override=new_payload)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


hook_event = Signal(providing_args=['action', 'instance'])
raw_hook_event = Signal(providing_args=['event_name', 'payload', 'user'])
hook_sent_event = Signal(providing_args=['payload', 'instance', 'hook'])

########NEW FILE########
__FILENAME__ = tasks
import requests
import json

from celery.task import Task

from django.core.serializers.json import DjangoJSONEncoder

from rest_hooks.models import Hook


class DeliverHook(Task):
    def run(self, target, payload, instance=None, hook_id=None, **kwargs):
        """
        target:     the url to receive the payload.
        payload:    a python primitive data structure
        instance:   a possibly null "trigger" instance
        hook:       the defining Hook object (useful for removing)
        """
        response = requests.post(
            url=target,
            data=json.dumps(payload, cls=DjangoJSONEncoder),
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 410 and hook_id:
            hook = Hook.object.get(id=hook_id)
            hook.delete()

        # would be nice to log this, at least for a little while...

def deliver_hook_wrapper(target, payload, instance=None, hook=None, **kwargs):
    if hook:
        kwargs['hook_id'] = hook.id
    return DeliverHook.delay(target, payload, **kwargs)

########NEW FILE########
__FILENAME__ = tests
import requests
import time
from mock import patch, MagicMock, ANY

from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils import simplejson as json

from rest_hooks import models
Hook = models.Hook

from rest_hooks import signals


class RESTHooksTest(TestCase):
    """
    This test Class uses real HTTP calls to a requestbin service, making it easy
    to check responses and endpoint history.
    """

    #############
    ### TOOLS ###
    #############

    def setUp(self):
        self.HOOK_EVENTS = getattr(settings, 'HOOK_EVENTS', None)
        self.HOOK_DELIVERER = getattr(settings, 'HOOK_DELIVERER', None)
        self.client = requests # force non-async for test cases

        self.user = User.objects.create_user('bob', 'bob@example.com', 'password')
        self.site = Site.objects.create(domain='example.com', name='example.com')

        models.HOOK_EVENTS = {
            'comment.added':        'comments.Comment.created',
            'comment.changed':      'comments.Comment.updated',
            'comment.removed':      'comments.Comment.deleted',
            'comment.moderated':    'comments.Comment.moderated',
            'special.thing':        None
        }

        settings.HOOK_DELIVERER = None

    def tearDown(self):
        models.HOOK_EVENTS = self.HOOK_EVENTS
        settings.HOOK_DELIVERER = self.HOOK_DELIVERER

    def make_hook(self, event, target):
        return Hook.objects.create(
            user=self.user,
            event=event,
            target=target
        )

    #############
    ### TESTS ###
    #############

    def test_no_user_property_fail(self):
        self.assertRaises(models.find_and_fire_hook, args=('some.fake.event', self.user))
        self.assertRaises(models.find_and_fire_hook, args=('special.thing', self.user))

    def test_no_hook(self):
        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )

    @patch('requests.post', autospec=True)
    def perform_create_request_cycle(self, method_mock):
        method_mock.return_value = None

        target = 'http://example.com/perform_create_request_cycle'
        hook = self.make_hook('comment.added', target)

        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )
        # time.sleep(1) # should change a setting to turn off async

        return hook, comment, json.loads(method_mock.call_args_list[0][1]['data'])

    def test_simple_comment_hook(self):
        """
        Uses the default serializer.
        """
        hook, comment, payload = self.perform_create_request_cycle()

        self.assertEquals(hook.id, payload['hook']['id'])
        self.assertEquals('comment.added', payload['hook']['event'])
        self.assertEquals(hook.target, payload['hook']['target'])

        self.assertEquals(comment.id, payload['data']['pk'])
        self.assertEquals('Hello world!', payload['data']['fields']['comment'])
        self.assertEquals(comment.user.id, payload['data']['fields']['user'])

    def test_comment_hook_serializer_method(self):
        """
        Use custom serialize_hook on the Comment model.
        """
        def serialize_hook(comment, hook):
            return { 'hook': hook.dict(),
                     'data': { 'id': comment.id,
                               'comment': comment.comment,
                               'user': { 'username': comment.user.username,
                                         'email': comment.user.email}}}
        Comment.serialize_hook = serialize_hook
        hook, comment, payload = self.perform_create_request_cycle()

        self.assertEquals(hook.id, payload['hook']['id'])
        self.assertEquals('comment.added', payload['hook']['event'])
        self.assertEquals(hook.target, payload['hook']['target'])

        self.assertEquals(comment.id, payload['data']['id'])
        self.assertEquals('Hello world!', payload['data']['comment'])
        self.assertEquals('bob', payload['data']['user']['username'])

        del Comment.serialize_hook

    @patch('requests.post')
    def test_full_cycle_comment_hook(self, method_mock):
        method_mock.return_value = None
        target = 'http://example.com/test_full_cycle_comment_hook'

        hooks = [self.make_hook(event, target) for event in ['comment.added', 'comment.changed', 'comment.removed']]

        # created
        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )
        # time.sleep(0.5) # should change a setting to turn off async

        # updated
        comment.comment = 'Goodbye world...'
        comment.save()
        # time.sleep(0.5) # should change a setting to turn off async

        # deleted
        comment.delete()
        # time.sleep(0.5) # should change a setting to turn off async

        payloads = [json.loads(call[2]['data']) for call in method_mock.mock_calls]

        self.assertEquals('comment.added', payloads[0]['hook']['event'])
        self.assertEquals('comment.changed', payloads[1]['hook']['event'])
        self.assertEquals('comment.removed', payloads[2]['hook']['event'])

        self.assertEquals('Hello world!', payloads[0]['data']['fields']['comment'])
        self.assertEquals('Goodbye world...', payloads[1]['data']['fields']['comment'])
        self.assertEquals('Goodbye world...', payloads[2]['data']['fields']['comment'])

    @patch('requests.post')
    def test_custom_instance_hook(self, method_mock):
        from rest_hooks.signals import hook_event

        method_mock.return_value = None
        target = 'http://example.com/test_custom_instance_hook'

        hook = self.make_hook('comment.moderated', target)

        comment = Comment.objects.create(
            site=self.site,
            content_object=self.user,
            user=self.user,
            comment='Hello world!'
        )

        hook_event.send(
            sender=comment.__class__,
            action='moderated',
            instance=comment
        )
        # time.sleep(1) # should change a setting to turn off async

        payloads = [json.loads(call[2]['data']) for call in method_mock.mock_calls]

        self.assertEquals('comment.moderated', payloads[0]['hook']['event'])
        self.assertEquals('Hello world!', payloads[0]['data']['fields']['comment'])

    @patch('requests.post')
    def test_raw_custom_event(self, method_mock):
        from rest_hooks.signals import raw_hook_event

        method_mock.return_value = None
        target = 'http://example.com/test_raw_custom_event'

        hook = self.make_hook('special.thing', target)

        raw_hook_event.send(
            sender=None,
            event_name='special.thing',
            payload={
                'hello': 'world!'
            },
            user=self.user
        )
        # time.sleep(1) # should change a setting to turn off async

        payload = json.loads(method_mock.mock_calls[0][2]['data'])

        self.assertEquals('special.thing', payload['hook']['event'])
        self.assertEquals('world!', payload['data']['hello'])

    def test_timed_cycle(self):
        return # basically a debug test for thread pool bit
        target = 'http://requestbin.zapier.com/api/v1/bin/test_timed_cycle'

        hooks = [self.make_hook(event, target) for event in ['comment.added', 'comment.changed', 'comment.removed']]

        for n in range(4):
            early = datetime.now()
            # fires N * 3 http calls
            for x in range(10):
                comment = Comment.objects.create(
                    site=self.site,
                    content_object=self.user,
                    user=self.user,
                    comment='Hello world!'
                )
                comment.comment = 'Goodbye world...'
                comment.save()
                comment.delete()
            total = datetime.now() - early

            print total

            while True:
                response = requests.get(target + '/view')
                sent = response.json
                if sent:
                    print len(sent), models.async_requests.total_sent
                if models.async_requests.total_sent >= (30 * (n+1)):
                    time.sleep(5)
                    break
                time.sleep(1)

        requests.delete(target + '/view') # cleanup to be polite

    def test_signal_emitted_upon_success(self):
        wrapper =  lambda *args, **kwargs: None
        mock_handler = MagicMock(wraps=wrapper)

        signals.hook_sent_event.connect(mock_handler, sender=Hook)

        hook, comment, payload = self.perform_create_request_cycle()

        payload['data']['fields']['submit_date'] = ANY
        mock_handler.assert_called_with(signal=ANY, sender=Hook, payload=payload, instance=comment, hook=hook)

########NEW FILE########
__FILENAME__ = utils
def get_module(path):
    """
    A modified duplicate from Django's built in backend
    retriever.

        slugify = get_module('django.template.defaultfilters.slugify')
    """
    from django.utils.importlib import import_module

    try:
        mod_name, func_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError, e:
        raise ImportError(
            'Error importing alert function {0}: "{1}"'.format(mod_name, e))

    try:
        func = getattr(mod, func_name)
    except AttributeError:
        raise ImportError(
            ('Module "{0}" does not define a "{1}" function'
                            ).format(mod_name, func_name))

    return func

def find_and_fire_hook(event_name, instance, user_override=None):
    """
    Look up Hooks that apply
    """
    from django.contrib.auth.models import User
    from rest_hooks.models import Hook, HOOK_EVENTS

    if user_override:
        user = user_override
    elif hasattr(instance, 'user'):
        user = instance.user
    elif isinstance(instance, User):
        user = instance
    else:
        raise Exception(
            '{} has no `user` property. REST Hooks needs this.'.format(repr(instance))
        )

    if not event_name in HOOK_EVENTS.keys():
        raise Exception(
            '"{}" does not exist in `settings.HOOK_EVENTS`.'.format(event_name)
        )

    hooks = Hook.objects.filter(user=user, event=event_name)
    for hook in hooks:
        hook.deliver_hook(instance)

def distill_model_event(instance, model, action, user_override=None):
    """
    Take created, updated and deleted actions for built-in 
    app/model mappings, convert to the defined event.name
    and let hooks fly.

    If that model isn't represented, we just quit silenty.
    """
    from rest_hooks.models import HOOK_EVENTS

    event_name = None
    for maybe_event_name, auto in HOOK_EVENTS.items():
        if auto:
            # break auto into App.Model, Action
            maybe_model, maybe_action = auto.rsplit('.', 1)
            if model == maybe_model and action == maybe_action:
                event_name = maybe_event_name

    if event_name:
        find_and_fire_hook(event_name, instance, user_override=user_override)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import sys
from django.conf import settings


APP_NAME = 'rest_hooks'

settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    USE_TZ=True,
    ROOT_URLCONF='{0}.tests'.format(APP_NAME),
    MIDDLEWARE_CLASSES=(
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ),
    SITE_ID=1,
    HOOK_EVENTS={},
    HOOK_THREADING=False,
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'django.contrib.sites',
        'django.contrib.comments',
        APP_NAME,
    ),
)

from django.test.utils import get_runner
TestRunner = get_runner(settings)
test_runner = TestRunner()
failures = test_runner.run_tests([APP_NAME])
if failures:
    sys.exit(failures)

########NEW FILE########
