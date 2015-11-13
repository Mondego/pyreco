__FILENAME__ = admin
from __future__ import absolute_import, unicode_literals

from anyjson import loads

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.views import main as main_views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from celery import current_app
from celery import states
from celery.task.control import broadcast, revoke, rate_limit
from celery.utils.text import abbrtask

from .admin_utils import action, display_field, fixedwidth
from .models import (
    TaskState, WorkerState,
    PeriodicTask, IntervalSchedule, CrontabSchedule,
)
from .humanize import naturaldate
from .utils import is_database_scheduler

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text  # noqa


TASK_STATE_COLORS = {states.SUCCESS: 'green',
                     states.FAILURE: 'red',
                     states.REVOKED: 'magenta',
                     states.STARTED: 'yellow',
                     states.RETRY: 'orange',
                     'RECEIVED': 'blue'}
NODE_STATE_COLORS = {'ONLINE': 'green',
                     'OFFLINE': 'gray'}


class MonitorList(main_views.ChangeList):

    def __init__(self, *args, **kwargs):
        super(MonitorList, self).__init__(*args, **kwargs)
        self.title = self.model_admin.list_page_title


@display_field(_('state'), 'state')
def colored_state(task):
    state = escape(task.state)
    color = TASK_STATE_COLORS.get(task.state, 'black')
    return '<b><span style="color: {0};">{1}</span></b>'.format(color, state)


@display_field(_('state'), 'last_heartbeat')
def node_state(node):
    state = node.is_alive() and 'ONLINE' or 'OFFLINE'
    color = NODE_STATE_COLORS[state]
    return '<b><span style="color: {0};">{1}</span></b>'.format(color, state)


@display_field(_('ETA'), 'eta')
def eta(task):
    if not task.eta:
        return '<span style="color: gray;">none</span>'
    return escape(task.eta)


@display_field(_('when'), 'tstamp')
def tstamp(task):
    return '<div title="{0}">{1}</div>'.format(
        escape(str(task.tstamp)), escape(naturaldate(task.tstamp)),
    )


@display_field(_('name'), 'name')
def name(task):
    short_name = abbrtask(task.name, 16)
    return '<div title="{0}"><b>{1}</b></div>'.format(
        escape(task.name), escape(short_name),
    )


class ModelMonitor(admin.ModelAdmin):
    can_add = False
    can_delete = False

    def get_changelist(self, request, **kwargs):
        return MonitorList

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context.setdefault('title', self.detail_title)
        return super(ModelMonitor, self).change_view(
            request, object_id, extra_context=extra_context,
        )

    def has_delete_permission(self, request, obj=None):
        if not self.can_delete:
            return False
        return super(ModelMonitor, self).has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if not self.can_add:
            return False
        return super(ModelMonitor, self).has_add_permission(request)


class TaskMonitor(ModelMonitor):
    detail_title = _('Task detail')
    list_page_title = _('Tasks')
    rate_limit_confirmation_template = 'djcelery/confirm_rate_limit.html'
    date_hierarchy = 'tstamp'
    fieldsets = (
        (None, {
            'fields': ('state', 'task_id', 'name', 'args', 'kwargs',
                       'eta', 'runtime', 'worker', 'tstamp'),
            'classes': ('extrapretty', ),
        }),
        ('Details', {
            'classes': ('collapse', 'extrapretty'),
            'fields': ('result', 'traceback', 'expires'),
        }),
    )
    list_display = (
        fixedwidth('task_id', name=_('UUID'), pt=8),
        colored_state,
        name,
        fixedwidth('args', pretty=True),
        fixedwidth('kwargs', pretty=True),
        eta,
        tstamp,
        'worker',
    )
    readonly_fields = (
        'state', 'task_id', 'name', 'args', 'kwargs',
        'eta', 'runtime', 'worker', 'result', 'traceback',
        'expires', 'tstamp',
    )
    list_filter = ('state', 'name', 'tstamp', 'eta', 'worker')
    search_fields = ('name', 'task_id', 'args', 'kwargs', 'worker__hostname')
    actions = ['revoke_tasks',
               'terminate_tasks',
               'kill_tasks',
               'rate_limit_tasks']

    class Media:
        css = {'all': ('djcelery/style.css', )}

    @action(_('Revoke selected tasks'))
    def revoke_tasks(self, request, queryset):
        with current_app.default_connection() as connection:
            for state in queryset:
                revoke(state.task_id, connection=connection)

    @action(_('Terminate selected tasks'))
    def terminate_tasks(self, request, queryset):
        with current_app.default_connection() as connection:
            for state in queryset:
                revoke(state.task_id, connection=connection, terminate=True)

    @action(_('Kill selected tasks'))
    def kill_tasks(self, request, queryset):
        with current_app.default_connection() as connection:
            for state in queryset:
                revoke(state.task_id, connection=connection,
                       terminate=True, signal='KILL')

    @action(_('Rate limit selected tasks'))
    def rate_limit_tasks(self, request, queryset):
        tasks = set([task.name for task in queryset])
        opts = self.model._meta
        app_label = opts.app_label
        if request.POST.get('post'):
            rate = request.POST['rate_limit']
            with current_app.default_connection() as connection:
                for task_name in tasks:
                    rate_limit(task_name, rate, connection=connection)
            return None

        context = {
            'title': _('Rate limit selection'),
            'queryset': queryset,
            'object_name': force_text(opts.verbose_name),
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'opts': opts,
            'app_label': app_label,
        }

        return render_to_response(
            self.rate_limit_confirmation_template, context,
            context_instance=RequestContext(request),
        )

    def get_actions(self, request):
        actions = super(TaskMonitor, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def get_queryset(self, request):
        qs = super(TaskMonitor, self).get_queryset(request)
        return qs.select_related('worker')


class WorkerMonitor(ModelMonitor):
    can_add = True
    detail_title = _('Node detail')
    list_page_title = _('Worker Nodes')
    list_display = ('hostname', node_state)
    readonly_fields = ('last_heartbeat', )
    actions = ['shutdown_nodes',
               'enable_events',
               'disable_events']

    @action(_('Shutdown selected worker nodes'))
    def shutdown_nodes(self, request, queryset):
        broadcast('shutdown', destination=[n.hostname for n in queryset])

    @action(_('Enable event mode for selected nodes.'))
    def enable_events(self, request, queryset):
        broadcast('enable_events',
                  destination=[n.hostname for n in queryset])

    @action(_('Disable event mode for selected nodes.'))
    def disable_events(self, request, queryset):
        broadcast('disable_events',
                  destination=[n.hostname for n in queryset])

    def get_actions(self, request):
        actions = super(WorkerMonitor, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

admin.site.register(TaskState, TaskMonitor)
admin.site.register(WorkerState, WorkerMonitor)


# ### Periodic Tasks


class LaxChoiceField(forms.ChoiceField):

    def valid_value(self, value):
        return True


def periodic_task_form():
    current_app.loader.import_default_modules()
    tasks = list(sorted(name for name in current_app.tasks
                        if not name.startswith('celery.')))
    choices = (('', ''), ) + tuple(zip(tasks, tasks))

    class PeriodicTaskForm(forms.ModelForm):
        regtask = LaxChoiceField(label=_('Task (registered)'),
                                 choices=choices, required=False)
        task = forms.CharField(label=_('Task (custom)'), required=False,
                               max_length=200)

        class Meta:
            model = PeriodicTask
            exclude = ()

        def clean(self):
            data = super(PeriodicTaskForm, self).clean()
            regtask = data.get('regtask')
            if regtask:
                data['task'] = regtask
            if not data['task']:
                exc = forms.ValidationError(_('Need name of task'))
                self._errors['task'] = self.error_class(exc.messages)
                raise exc
            return data

        def _clean_json(self, field):
            value = self.cleaned_data[field]
            try:
                loads(value)
            except ValueError as exc:
                raise forms.ValidationError(
                    _('Unable to parse JSON: %s') % exc,
                )
            return value

        def clean_args(self):
            return self._clean_json('args')

        def clean_kwargs(self):
            return self._clean_json('kwargs')

    return PeriodicTaskForm


class PeriodicTaskAdmin(admin.ModelAdmin):
    model = PeriodicTask
    form = periodic_task_form()
    list_display = ('__unicode__', 'enabled')
    fieldsets = (
        (None, {
            'fields': ('name', 'regtask', 'task', 'enabled'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab'),
            'classes': ('extrapretty', 'wide', ),
        }),
        ('Arguments', {
            'fields': ('args', 'kwargs'),
            'classes': ('extrapretty', 'wide', 'collapse'),
        }),
        ('Execution Options', {
            'fields': ('expires', 'queue', 'exchange', 'routing_key'),
            'classes': ('extrapretty', 'wide', 'collapse'),
        }),
    )

    def __init__(self, *args, **kwargs):
        super(PeriodicTaskAdmin, self).__init__(*args, **kwargs)
        self.form = periodic_task_form()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        scheduler = getattr(settings, 'CELERYBEAT_SCHEDULER', None)
        extra_context['wrong_scheduler'] = not is_database_scheduler(scheduler)
        return super(PeriodicTaskAdmin, self).changelist_view(request,
                                                              extra_context)

    def get_queryset(self, request):
        qs = super(PeriodicTaskAdmin, self).get_queryset(request)
        return qs.select_related('interval', 'crontab')


admin.site.register(IntervalSchedule)
admin.site.register(CrontabSchedule)
admin.site.register(PeriodicTask, PeriodicTaskAdmin)

########NEW FILE########
__FILENAME__ = admin_utils
from __future__ import absolute_import, unicode_literals

from pprint import pformat

from django.utils.html import escape

FIXEDWIDTH_STYLE = '''\
<span title="{0}" style="font-size: {1}pt; \
font-family: Menlo, Courier; ">{2}</span> \
'''


def attrs(**kwargs):
    def _inner(fun):
        for attr_name, attr_value in kwargs.items():
            setattr(fun, attr_name, attr_value)
        return fun
    return _inner


def display_field(short_description, admin_order_field,
                  allow_tags=True, **kwargs):
    return attrs(short_description=short_description,
                 admin_order_field=admin_order_field,
                 allow_tags=allow_tags, **kwargs)


def action(short_description, **kwargs):
    return attrs(short_description=short_description, **kwargs)


def fixedwidth(field, name=None, pt=6, width=16, maxlen=64, pretty=False):

    @display_field(name or field, field)
    def f(task):
        val = getattr(task, field)
        if pretty:
            val = pformat(val, width=width)
        if val.startswith("u'") or val.startswith('u"'):
            val = val[2:-1]
        shortval = val.replace(',', ',\n')
        shortval = shortval.replace('\n', '|br/|')

        if len(shortval) > maxlen:
            shortval = shortval[:maxlen] + '...'
        styled = FIXEDWIDTH_STYLE.format(
            escape(val[:255]), pt, escape(shortval),
        )
        return styled.replace('|br/|', '<br/>')
    return f

########NEW FILE########
__FILENAME__ = app
from __future__ import absolute_import, unicode_literals

from celery import current_app


#: The Django-Celery app instance.
app = current_app._get_current_object()

########NEW FILE########
__FILENAME__ = cache
"""celery.backends.cache"""
from __future__ import absolute_import, unicode_literals

from datetime import timedelta

import django
from django.utils.encoding import smart_str
from django.core.cache import cache, get_cache

from celery import current_app
from celery.utils.timeutils import timedelta_seconds
from celery.backends.base import KeyValueStoreBackend

# CELERY_CACHE_BACKEND overrides the django-global(tm) backend settings.
if current_app.conf.CELERY_CACHE_BACKEND:
    cache = get_cache(current_app.conf.CELERY_CACHE_BACKEND)  # noqa


class DjangoMemcacheWrapper(object):
    """Wrapper class to django's memcache backend class, that overrides the
    :meth:`get` method in order to remove the forcing of unicode strings
    since it may cause binary or pickled data to break."""

    def __init__(self, cache):
        self.cache = cache

    def get(self, key, default=None):
        val = self.cache._cache.get(smart_str(key))
        if val is None:
            return default
        else:
            return val

    def set(self, key, value, timeout=0):
        self.cache.set(key, value, timeout)

# Check if django is using memcache as the cache backend. If so, wrap the
# cache object in a DjangoMemcacheWrapper for Django < 1.2 that fixes a bug
# with retrieving pickled data.
from django.core.cache.backends.base import InvalidCacheBackendError
try:
    from django.core.cache.backends.memcached import CacheClass
except (ImportError, AttributeError, InvalidCacheBackendError):
    pass
else:
    if django.VERSION[0:2] < (1, 2) and isinstance(cache, CacheClass):
        cache = DjangoMemcacheWrapper(cache)


class CacheBackend(KeyValueStoreBackend):
    """Backend using the Django cache framework to store task metadata."""

    def __init__(self, *args, **kwargs):
        super(CacheBackend, self).__init__(*args, **kwargs)
        expires = kwargs.get('expires',
                             current_app.conf.CELERY_TASK_RESULT_EXPIRES)
        if isinstance(expires, timedelta):
            expires = int(timedelta_seconds(expires))
        self.expires = expires

    def get(self, key):
        return cache.get(key)

    def set(self, key, value):
        cache.set(key, value, self.expires)

    def delete(self, key):
        cache.delete(key)

########NEW FILE########
__FILENAME__ = database
from __future__ import absolute_import, unicode_literals

from celery import current_app
from celery.backends.base import BaseDictBackend
from celery.utils.timeutils import maybe_timedelta

from ..models import TaskMeta, TaskSetMeta


class DatabaseBackend(BaseDictBackend):
    """The database backend.

    Using Django models to store task state.

    """
    TaskModel = TaskMeta
    TaskSetModel = TaskSetMeta

    expires = current_app.conf.CELERY_TASK_RESULT_EXPIRES
    create_django_tables = True

    subpolling_interval = 0.5

    def _store_result(self, task_id, result, status,
                      traceback=None, request=None):
        """Store return value and status of an executed task."""
        self.TaskModel._default_manager.store_result(
            task_id, result, status,
            traceback=traceback, children=self.current_task_children(request),
        )
        return result

    def _save_group(self, group_id, result):
        """Store the result of an executed group."""
        self.TaskSetModel._default_manager.store_result(group_id, result)
        return result

    def _get_task_meta_for(self, task_id):
        """Get task metadata for a task by id."""
        return self.TaskModel._default_manager.get_task(task_id).to_dict()

    def _restore_group(self, group_id):
        """Get group metadata for a group by id."""
        meta = self.TaskSetModel._default_manager.restore_taskset(group_id)
        if meta:
            return meta.to_dict()

    def _delete_group(self, group_id):
        self.TaskSetModel._default_manager.delete_taskset(group_id)

    def _forget(self, task_id):
        try:
            self.TaskModel._default_manager.get(task_id=task_id).delete()
        except self.TaskModel.DoesNotExist:
            pass

    def cleanup(self):
        """Delete expired metadata."""
        expires = maybe_timedelta(self.expires)
        for model in self.TaskModel, self.TaskSetModel:
            model._default_manager.delete_expired(expires)

########NEW FILE########
__FILENAME__ = common
from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager
from functools import wraps

from django.utils import translation


@contextmanager
def respect_language(language):
    """Context manager that changes the current translation language for
    all code inside the following block.

    Can e.g. be used inside tasks like this::

        from celery import task
        from djcelery.common import respect_language

        @task
        def my_task(language=None):
            with respect_language(language):
                pass
    """
    if language:
        prev = translation.get_language()
        translation.activate(language)
        try:
            yield
        finally:
            translation.activate(prev)
    else:
        yield


def respects_language(fun):
    """Decorator for tasks with respect to site's current language.
    You can use this decorator on your tasks together with default @task
    decorator (remember that the task decorator must be applied last).

    See also the with-statement alternative :func:`respect_language`.

    **Example**:

    .. code-block:: python

        @task
        @respects_language
        def my_task()
            # localize something.

    The task will then accept a ``language`` argument that will be
    used to set the language in the task, and the task can thus be
    called like:

    .. code-block:: python

        from django.utils import translation
        from myapp.tasks import my_task

        # Pass the current language on to the task
        my_task.delay(language=translation.get_language())

        # or set the language explicitly
        my_task.delay(language='no.no')

    """

    @wraps(fun)
    def _inner(*args, **kwargs):
        with respect_language(kwargs.pop('language', None)):
            return fun(*args, **kwargs)
    return _inner

########NEW FILE########
__FILENAME__ = test_runner
from __future__ import absolute_import, unicode_literals

from django.conf import settings
try:
    from django.test.runner import DiscoverRunner
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as DiscoverRunner

from celery import current_app
from celery.task import Task
from djcelery.backends.database import DatabaseBackend


USAGE = """\
Custom test runner to allow testing of celery delayed tasks.
"""


def _set_eager():
    settings.CELERY_ALWAYS_EAGER = True
    current_app.conf.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True  # Issue #75
    current_app.conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


class CeleryTestSuiteRunner(DiscoverRunner):
    """Django test runner allowing testing of celery delayed tasks.

    All tasks are run locally, not in a worker.

    To use this runner set ``settings.TEST_RUNNER``::

        TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

    """
    def setup_test_environment(self, **kwargs):
        _set_eager()
        super(CeleryTestSuiteRunner, self).setup_test_environment(**kwargs)


class CeleryTestSuiteRunnerStoringResult(DiscoverRunner):
    """Django test runner allowing testing of celery delayed tasks,
    and storing the results of those tasks in ``TaskMeta``.

    Requires setting CELERY_RESULT_BACKEND = 'database'.

    USAGE:

    In ``settings.py``::

        TEST_RUNNER = '''
            djcelery.contrib.test_runner.CeleryTestSuiteRunnerStoringResult
        '''.strip()

    """

    def setup_test_environment(self, **kwargs):
        # Monkey-patch Task.on_success() method
        def on_success_patched(self, retval, task_id, args, kwargs):
            app = current_app._get_current_object()
            DatabaseBackend(app=app).store_result(task_id, retval, 'SUCCESS')
        Task.on_success = classmethod(on_success_patched)

        super(CeleryTestSuiteRunnerStoringResult, self).setup_test_environment(
            **kwargs
        )

        settings.CELERY_RESULT_BACKEND = 'database'
        _set_eager()

########NEW FILE########
__FILENAME__ = db
from __future__ import absolute_import

import django

from contextlib import contextmanager
from django.db import transaction

if django.VERSION < (1, 6):  # pragma: no cover

    def get_queryset(s):
        return s.get_query_set()
else:
    def get_queryset(s):  # noqa
        return s.get_queryset()

try:
    from django.db.transaction import atomic  # noqa
except ImportError:  # pragma: no cover

    try:
        from django.db.transaction import Transaction  # noqa
    except ImportError:
        @contextmanager
        def commit_on_success(*args, **kwargs):
            try:
                transaction.enter_transaction_management(*args, **kwargs)
                transaction.managed(True, *args, **kwargs)
                try:
                    yield
                except:
                    if transaction.is_dirty(*args, **kwargs):
                        transaction.rollback(*args, **kwargs)
                    raise
                else:
                    if transaction.is_dirty(*args, **kwargs):
                        try:
                            transaction.commit(*args, **kwargs)
                        except:
                            transaction.rollback(*args, **kwargs)
                            raise
            finally:
                transaction.leave_transaction_management(*args, **kwargs)
    else:  # pragma: no cover
        from django.db.transaction import commit_on_success  # noqa

    commit_unless_managed = transaction.commit_unless_managed
    rollback_unless_managed = transaction.rollback_unless_managed
else:
    @contextmanager
    def commit_on_success(using=None):  # noqa
        connection = transaction.get_connection(using)
        if connection.features.autocommits_when_autocommit_is_off:
            # ignore stupid warnings and errors
            yield
        else:
            with transaction.atomic(using):
                yield

    def commit_unless_managed(*args, **kwargs):  # noqa
        pass

    def rollback_unless_managed(*args, **kwargs):  # noqa
        pass

########NEW FILE########
__FILENAME__ = humanize
from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.utils.translation import ungettext, ugettext as _
from .utils import now


def pluralize_year(n):
    return ungettext(_('{num} year ago'), _('{num} years ago'), n)


def pluralize_month(n):
    return ungettext(_('{num} month ago'), _('{num} months ago'), n)


def pluralize_week(n):
    return ungettext(_('{num} week ago'), _('{num} weeks ago'), n)


def pluralize_day(n):
    return ungettext(_('{num} day ago'), _('{num} days ago'), n)


OLDER_CHUNKS = (
    (365.0, pluralize_year),
    (30.0, pluralize_month),
    (7.0, pluralize_week),
    (1.0, pluralize_day),
)


def _un(singular__plural, n=None):
    singular, plural = singular__plural
    return ungettext(singular, plural, n)


def naturaldate(date, include_seconds=False):
    """Convert datetime into a human natural date string."""

    if not date:
        return ''

    right_now = now()
    today = datetime(right_now.year, right_now.month,
                     right_now.day, tzinfo=right_now.tzinfo)
    delta = right_now - date
    delta_midnight = today - date

    days = delta.days
    hours = int(round(delta.seconds / 3600, 0))
    minutes = delta.seconds / 60
    seconds = delta.seconds

    if days < 0:
        return _('just now')

    if days == 0:
        if hours == 0:
            if minutes > 0:
                return ungettext(
                    _('{minutes} minute ago'),
                    _('{minutes} minutes ago'), minutes
                ).format(minutes=minutes)
            else:
                if include_seconds and seconds:
                    return ungettext(
                        _('{seconds} second ago'),
                        _('{seconds} seconds ago'), seconds
                    ).format(seconds=seconds)
                return _('just now')
        else:
            return ungettext(
                _('{hours} hour ago'), _('{hours} hours ago'), hours
            ).format(hours=hours)

    if delta_midnight.days == 0:
        return _('yesterday at {time}').format(time=date.strftime('%H:%M'))

    count = 0
    for chunk, pluralizefun in OLDER_CHUNKS:
        if days >= chunk:
            count = round((delta_midnight.days + 1) / chunk, 0)
            fmt = pluralizefun(count)
            return fmt.format(num=count)

########NEW FILE########
__FILENAME__ = loaders
from __future__ import absolute_import

import os
import imp
import importlib

from datetime import datetime
from warnings import warn

from celery import signals
from celery.datastructures import DictAttribute
from celery.loaders.base import BaseLoader

import django
from django import db
from django.conf import settings
from django.core import cache
from django.core.mail import mail_admins

from .utils import DATABASE_ERRORS, now

_RACE_PROTECTION = False
NO_TZ = django.VERSION < (1, 4)


def _maybe_close_fd(fh):
    try:
        os.close(fh.fileno())
    except (AttributeError, OSError, TypeError):
        # TypeError added for celery#962
        pass


class DjangoLoader(BaseLoader):
    """The Django loader."""
    _db_reuse = 0

    override_backends = {
        'database': 'djcelery.backends.database.DatabaseBackend',
        'cache': 'djcelery.backends.cache.CacheBackend',
    }

    def __init__(self, *args, **kwargs):
        super(DjangoLoader, self).__init__(*args, **kwargs)
        self._install_signal_handlers()

    def _install_signal_handlers(self):
        # Need to close any open database connection after
        # any embedded celerybeat process forks.
        signals.beat_embedded_init.connect(self.close_database)
        signals.worker_ready.connect(self.warn_if_debug)

    def now(self, utc=False):
        return datetime.utcnow() if utc else now()

    def read_configuration(self):
        """Load configuration from Django settings."""
        self.configured = True
        # Default backend needs to be the database backend for backward
        # compatibility.
        backend = (getattr(settings, 'CELERY_RESULT_BACKEND', None) or
                   getattr(settings, 'CELERY_BACKEND', None))
        if not backend:
            settings.CELERY_RESULT_BACKEND = 'database'
        if NO_TZ:
            if getattr(settings, 'CELERY_ENABLE_UTC', None):
                warn('CELERY_ENABLE_UTC requires Django 1.4+')
            settings.CELERY_ENABLE_UTC = False
        return DictAttribute(settings)

    def _close_database(self):
        try:
            funs = [conn.close for conn in db.connections]
        except AttributeError:
            if hasattr(db, 'close_old_connections'):  # Django 1.6+
                funs = [db.close_old_connections]
            else:
                funs = [db.close_connection]  # pre multidb

        for close in funs:
            try:
                close()
            except DATABASE_ERRORS as exc:
                str_exc = str(exc)
                if 'closed' not in str_exc and 'not connected' not in str_exc:
                    raise

    def close_database(self, **kwargs):
        db_reuse_max = self.conf.get('CELERY_DB_REUSE_MAX', None)
        if not db_reuse_max:
            return self._close_database()
        if self._db_reuse >= db_reuse_max * 2:
            self._db_reuse = 0
            self._close_database()
        self._db_reuse += 1

    def close_cache(self):
        try:
            cache.cache.close()
        except (TypeError, AttributeError):
            pass

    def on_process_cleanup(self):
        """Does everything necessary for Django to work in a long-living,
        multiprocessing environment.

        """
        # See http://groups.google.com/group/django-users/
        #            browse_thread/thread/78200863d0c07c6d/
        self.close_database()
        self.close_cache()

    def on_task_init(self, task_id, task):
        """Called before every task."""
        try:
            is_eager = task.request.is_eager
        except AttributeError:
            is_eager = False
        if not is_eager:
            self.close_database()

    def on_worker_init(self):
        """Called when the worker starts.

        Automatically discovers any ``tasks.py`` files in the applications
        listed in ``INSTALLED_APPS``.

        """
        self.import_default_modules()

        self.close_database()
        self.close_cache()

    def warn_if_debug(self, **kwargs):
        if settings.DEBUG:
            warn('Using settings.DEBUG leads to a memory leak, never '
                 'use this setting in production environments!')

    def import_default_modules(self):
        super(DjangoLoader, self).import_default_modules()
        self.autodiscover()

    def autodiscover(self):
        self.task_modules.update(mod.__name__ for mod in autodiscover() or ())

    def on_worker_process_init(self):
        # the parent process may have established these,
        # so need to close them.

        # calling db.close() on some DB connections will cause
        # the inherited DB conn to also get broken in the parent
        # process so we need to remove it without triggering any
        # network IO that close() might cause.
        try:
            for c in db.connections.all():
                if c and c.connection:
                    _maybe_close_fd(c.connection)
        except AttributeError:
            if db.connection and db.connection.connection:
                _maybe_close_fd(db.connection.connection)

        # use the _ version to avoid DB_REUSE preventing the conn.close() call
        self._close_database()
        self.close_cache()

    def mail_admins(self, subject, body, fail_silently=False, **kwargs):
        return mail_admins(subject, body, fail_silently=fail_silently)


def autodiscover():
    """Include tasks for all applications in ``INSTALLED_APPS``."""
    global _RACE_PROTECTION

    if _RACE_PROTECTION:
        return
    _RACE_PROTECTION = True
    try:
        return filter(None, [find_related_module(app, 'tasks')
                             for app in settings.INSTALLED_APPS])
    finally:
        _RACE_PROTECTION = False


def find_related_module(app, related_name):
    """Given an application name and a module name, tries to find that
    module in the application."""

    try:
        app_path = importlib.import_module(app).__path__
    except ImportError as exc:
        warn('Autodiscover: Error importing %s.%s: %r' % (
            app, related_name, exc,
        ))
        return
    except AttributeError:
        return

    try:
        imp.find_module(related_name, app_path)
    except ImportError:
        return

    return importlib.import_module('{0}.{1}'.format(app, related_name))

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, unicode_literals

import os
import sys

from django.core.management.base import BaseCommand

import celery
import djcelery

DB_SHARED_THREAD = """\
DatabaseWrapper objects created in a thread can only \
be used in that same thread.  The object with alias '{0}' \
was created in thread id {1} and this is thread id {2}.\
"""


def patch_thread_ident():
    # monkey patch django.
    # This patch make sure that we use real threads to get the ident which
    # is going to happen if we are using gevent or eventlet.
    # -- patch taken from gunicorn
    if getattr(patch_thread_ident, 'called', False):
        return
    try:
        from django.db.backends import BaseDatabaseWrapper, DatabaseError

        if 'validate_thread_sharing' in BaseDatabaseWrapper.__dict__:
            import thread
            _get_ident = thread.get_ident

            __old__init__ = BaseDatabaseWrapper.__init__

            def _init(self, *args, **kwargs):
                __old__init__(self, *args, **kwargs)
                self._thread_ident = _get_ident()

            def _validate_thread_sharing(self):
                if (not self.allow_thread_sharing
                        and self._thread_ident != _get_ident()):
                    raise DatabaseError(
                        DB_SHARED_THREAD % (
                            self.alias, self._thread_ident, _get_ident()),
                    )

            BaseDatabaseWrapper.__init__ = _init
            BaseDatabaseWrapper.validate_thread_sharing = \
                _validate_thread_sharing

        patch_thread_ident.called = True
    except ImportError:
        pass
patch_thread_ident()


class CeleryCommand(BaseCommand):
    options = BaseCommand.option_list
    skip_opts = ['--app', '--loader', '--config']
    keep_base_opts = False

    def get_version(self):
        return 'celery {c.__version__}\ndjango-celery {d.__version__}'.format(
            c=celery, d=djcelery,
        )

    def execute(self, *args, **options):
        broker = options.get('broker')
        if broker:
            self.set_broker(broker)
        super(CeleryCommand, self).execute(*args, **options)

    def set_broker(self, broker):
        os.environ['CELERY_BROKER_URL'] = broker

    def run_from_argv(self, argv):
        self.handle_default_options(argv[2:])
        return super(CeleryCommand, self).run_from_argv(argv)

    def handle_default_options(self, argv):
        acc = []
        broker = None
        for i, arg in enumerate(argv):
            # --settings and --pythonpath are also handled
            # by BaseCommand.handle_default_options, but that is
            # called with the resulting options parsed by optparse.
            if '--settings=' in arg:
                _, settings_module = arg.split('=')
                os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
            elif '--pythonpath=' in arg:
                _, pythonpath = arg.split('=')
                sys.path.insert(0, pythonpath)
            elif '--broker=' in arg:
                _, broker = arg.split('=')
            elif arg == '-b':
                broker = argv[i + 1]
            else:
                acc.append(arg)
        if broker:
            self.set_broker(broker)
        return argv if self.keep_base_opts else acc

    def die(self, msg):
        sys.stderr.write(msg)
        sys.stderr.write('\n')
        sys.exit()

    def _is_unwanted_option(self, option):
        return option._long_opts and option._long_opts[0] in self.skip_opts

    @property
    def option_list(self):
        return [x for x in self.options if not self._is_unwanted_option(x)]

########NEW FILE########
__FILENAME__ = celery
from __future__ import absolute_import, unicode_literals

from celery.bin import celery

from djcelery.app import app
from djcelery.management.base import CeleryCommand

base = celery.CeleryCommand(app=app)


class Command(CeleryCommand):
    """The celery command."""
    help = 'celery commands, see celery help'
    requires_model_validation = True
    options = (CeleryCommand.options
               + base.get_options()
               + base.preload_options)

    def run_from_argv(self, argv):
        argv = self.handle_default_options(argv)
        if self.requires_model_validation:
            self.validate()
        base.execute_from_commandline(
            ['{0[0]} {0[1]}'.format(argv)] + argv[2:],
        )

########NEW FILE########
__FILENAME__ = celerybeat
"""

Start the celery clock service from the Django management command.

"""
from __future__ import absolute_import, unicode_literals

from celery.bin import beat

from djcelery.app import app
from djcelery.management.base import CeleryCommand

beat = beat.beat(app=app)


class Command(CeleryCommand):
    """Run the celery periodic task scheduler."""
    options = (CeleryCommand.options
               + beat.get_options()
               + beat.preload_options)
    help = 'Old alias to the "celery beat" command.'

    def handle(self, *args, **options):
        beat.run(*args, **options)

########NEW FILE########
__FILENAME__ = celerycam
"""

Shortcut to the Django snapshot service.

"""
from __future__ import absolute_import, unicode_literals

from celery.bin import events

from djcelery.app import app
from djcelery.management.base import CeleryCommand

ev = events.events(app=app)


class Command(CeleryCommand):
    """Run the celery curses event viewer."""
    options = (CeleryCommand.options
               + ev.get_options()
               + ev.preload_options)
    help = 'Takes snapshots of the clusters state to the database.'

    def handle(self, *args, **options):
        """Handle the management command."""
        options['camera'] = 'djcelery.snapshot.Camera'
        ev.run(*args, **options)

########NEW FILE########
__FILENAME__ = celeryd
"""

Start the celery daemon from the Django management command.

"""
from __future__ import absolute_import, unicode_literals

from celery.bin import worker

from djcelery.app import app
from djcelery.management.base import CeleryCommand

worker = worker.worker(app=app)


class Command(CeleryCommand):
    """Run the celery daemon."""
    help = 'Old alias to the "celery worker" command.'
    requires_model_validation = True
    options = (CeleryCommand.options
               + worker.get_options()
               + worker.preload_options)

    def handle(self, *args, **options):
        worker.check_args(args)
        worker.run(**options)

########NEW FILE########
__FILENAME__ = celeryd_detach
"""

Start detached worker node from the Django management utility.

"""
from __future__ import absolute_import, unicode_literals

import os
import sys

from celery.bin import celeryd_detach

from djcelery.management.base import CeleryCommand


class Command(CeleryCommand):
    """Run the celery daemon."""
    help = 'Runs a detached Celery worker node.'
    requires_model_validation = True
    options = celeryd_detach.OPTION_LIST

    def run_from_argv(self, argv):

        class detached(celeryd_detach.detached_celeryd):
            execv_argv = [os.path.abspath(sys.argv[0]), 'celery', 'worker']
        detached().execute_from_commandline(argv)

########NEW FILE########
__FILENAME__ = celeryd_multi
"""

Utility to manage multiple worker instances.

"""
from __future__ import absolute_import, unicode_literals

from celery.bin import multi

from djcelery.management.base import CeleryCommand


class Command(CeleryCommand):
    """Run the celery daemon."""
    args = '[name1, [name2, [...]> [worker options]'
    help = 'Manage multiple Celery worker nodes.'
    requires_model_validation = True
    options = ()
    keep_base_opts = True

    def run_from_argv(self, argv):
        argv = self.handle_default_options(argv)
        argv.append('--cmd={0[0]} celeryd_detach'.format(argv))
        multi.MultiTool().execute_from_commandline(
            ['{0[0]} {0[1]}'.format(argv)] + argv[2:],
        )

########NEW FILE########
__FILENAME__ = celerymon
"""

Start the celery clock service from the Django management command.

"""
from __future__ import absolute_import, unicode_literals

import sys

from djcelery.app import app
from djcelery.management.base import CeleryCommand

try:
    from celerymon.bin.celerymon import MonitorCommand
    mon = MonitorCommand(app=app)
except ImportError:
    mon = None

MISSING = """
You don't have celerymon installed, please install it by running the following
command:

    $ pip install -U celerymon

or if you're still using easy_install (shame on you!)

    $ easy_install -U celerymon
"""


class Command(CeleryCommand):
    """Run the celery monitor."""
    options = (CeleryCommand.options
               + (mon and mon.get_options() + mon.preload_options or ()))
    help = 'Run the celery monitor'

    def handle(self, *args, **options):
        """Handle the management command."""
        if mon is None:
            sys.stderr.write(MISSING)
        else:
            mon.run(**options)

########NEW FILE########
__FILENAME__ = djcelerymon
from __future__ import absolute_import, unicode_literals

import sys
import threading

from celery.bin import events

from django.core.management.commands import runserver

from djcelery.app import app
from djcelery.management.base import CeleryCommand

ev = events.events(app=app)


class WebserverThread(threading.Thread):

    def __init__(self, addrport='', *args, **options):
        threading.Thread.__init__(self)
        self.addrport = addrport
        self.args = args
        self.options = options

    def run(self):
        options = dict(self.options, use_reloader=False)
        command = runserver.Command()
        # see http://code.djangoproject.com/changeset/13319
        command.stdout, command.stderr = sys.stdout, sys.stderr
        command.handle(self.addrport, *self.args, **options)


class Command(CeleryCommand):
    """Run the celery curses event viewer."""
    args = '[optional port number, or ipaddr:port]'
    options = (runserver.Command.option_list
               + ev.get_options()
               + ev.preload_options)
    help = 'Starts Django Admin instance and celerycam in the same process.'
    # see http://code.djangoproject.com/changeset/13319.
    stdout, stderr = sys.stdout, sys.stderr

    def handle(self, addrport='', *args, **options):
        """Handle the management command."""
        server = WebserverThread(addrport, *args, **options)
        server.start()
        options['camera'] = 'djcelery.snapshot.Camera'
        options['prog_name'] = 'djcelerymon'
        ev.run(*args, **options)

########NEW FILE########
__FILENAME__ = managers
from __future__ import absolute_import, unicode_literals

import warnings

from functools import wraps
from itertools import count

from django.db import connection
try:
    from django.db import connections, router
except ImportError:  # pre-Django 1.2
    connections = router = None  # noqa

from django.db import models
from django.db.models.query import QuerySet
from django.conf import settings

from celery.utils.timeutils import maybe_timedelta

from .db import commit_on_success, get_queryset, rollback_unless_managed
from .utils import now


class TxIsolationWarning(UserWarning):
    pass


def transaction_retry(max_retries=1):
    """Decorator for methods doing database operations.

    If the database operation fails, it will retry the operation
    at most ``max_retries`` times.

    """
    def _outer(fun):

        @wraps(fun)
        def _inner(*args, **kwargs):
            _max_retries = kwargs.pop('exception_retry_count', max_retries)
            for retries in count(0):
                try:
                    return fun(*args, **kwargs)
                except Exception:   # pragma: no cover
                    # Depending on the database backend used we can experience
                    # various exceptions. E.g. psycopg2 raises an exception
                    # if some operation breaks the transaction, so saving
                    # the task result won't be possible until we rollback
                    # the transaction.
                    if retries >= _max_retries:
                        raise
                    try:
                        rollback_unless_managed()
                    except Exception:
                        pass
        return _inner

    return _outer


def update_model_with_dict(obj, fields):
    [setattr(obj, attr_name, attr_value)
        for attr_name, attr_value in fields.items()]
    obj.save()
    return obj


class ExtendedQuerySet(QuerySet):

    def update_or_create(self, **kwargs):
        obj, created = self.get_or_create(**kwargs)

        if not created:
            fields = dict(kwargs.pop('defaults', {}))
            fields.update(kwargs)
            update_model_with_dict(obj, fields)

        return obj


class ExtendedManager(models.Manager):

    def get_queryset(self):
        return ExtendedQuerySet(self.model)
    get_query_set = get_queryset  # Pre django 1.6

    def update_or_create(self, **kwargs):
        return get_queryset(self).update_or_create(**kwargs)

    def connection_for_write(self):
        if connections:
            return connections[router.db_for_write(self.model)]
        return connection

    def connection_for_read(self):
        if connections:
            return connections[self.db]
        return connection

    def current_engine(self):
        try:
            return settings.DATABASES[self.db]['ENGINE']
        except AttributeError:
            return settings.DATABASE_ENGINE


class ResultManager(ExtendedManager):

    def get_all_expired(self, expires):
        """Get all expired task results."""
        return self.filter(date_done__lt=now() - maybe_timedelta(expires))

    def delete_expired(self, expires):
        """Delete all expired taskset results."""
        meta = self.model._meta
        with commit_on_success():
            self.get_all_expired(expires).update(hidden=True)
            cursor = self.connection_for_write().cursor()
            cursor.execute(
                'DELETE FROM {0.db_table} WHERE hidden=%s'.format(meta),
                (True, ),
            )


class PeriodicTaskManager(ExtendedManager):

    def enabled(self):
        return self.filter(enabled=True)


class TaskManager(ResultManager):
    """Manager for :class:`celery.models.Task` models."""
    _last_id = None

    def get_task(self, task_id):
        """Get task meta for task by ``task_id``.

        :keyword exception_retry_count: How many times to retry by
            transaction rollback on exception. This could theoretically
            happen in a race condition if another worker is trying to
            create the same task. The default is to retry once.

        """
        try:
            return self.get(task_id=task_id)
        except self.model.DoesNotExist:
            if self._last_id == task_id:
                self.warn_if_repeatable_read()
            self._last_id = task_id
            return self.model(task_id=task_id)

    @transaction_retry(max_retries=2)
    def store_result(self, task_id, result, status,
                     traceback=None, children=None):
        """Store the result and status of a task.

        :param task_id: task id

        :param result: The return value of the task, or an exception
            instance raised by the task.

        :param status: Task status. See
            :meth:`celery.result.AsyncResult.get_status` for a list of
            possible status values.

        :keyword traceback: The traceback at the point of exception (if the
            task failed).

        :keyword children: List of serialized results of subtasks
            of this task.

        :keyword exception_retry_count: How many times to retry by
            transaction rollback on exception. This could theoretically
            happen in a race condition if another worker is trying to
            create the same task. The default is to retry twice.

        """
        return self.update_or_create(task_id=task_id,
                                     defaults={'status': status,
                                               'result': result,
                                               'traceback': traceback,
                                               'meta': {'children': children}})

    def warn_if_repeatable_read(self):
        if 'mysql' in self.current_engine().lower():
            cursor = self.connection_for_read().cursor()
            if cursor.execute('SELECT @@tx_isolation'):
                isolation = cursor.fetchone()[0]
                if isolation == 'REPEATABLE-READ':
                    warnings.warn(TxIsolationWarning(
                        'Polling results with transaction isolation level '
                        'repeatable-read within the same transaction '
                        'may give outdated results. Be sure to commit the '
                        'transaction for each poll iteration.'))


class TaskSetManager(ResultManager):
    """Manager for :class:`celery.models.TaskSet` models."""

    def restore_taskset(self, taskset_id):
        """Get the async result instance by taskset id."""
        try:
            return self.get(taskset_id=taskset_id)
        except self.model.DoesNotExist:
            pass

    def delete_taskset(self, taskset_id):
        """Delete a saved taskset result."""
        s = self.restore_taskset(taskset_id)
        if s:
            s.delete()

    @transaction_retry(max_retries=2)
    def store_result(self, taskset_id, result):
        """Store the async result instance of a taskset.

        :param taskset_id: task set id

        :param result: The return value of the taskset

        """
        return self.update_or_create(taskset_id=taskset_id,
                                     defaults={'result': result})


class TaskStateManager(ExtendedManager):

    def active(self):
        return self.filter(hidden=False)

    def expired(self, states, expires, nowfun=now):
        return self.filter(state__in=states,
                           tstamp__lte=nowfun() - maybe_timedelta(expires))

    def expire_by_states(self, states, expires):
        if expires is not None:
            return self.expired(states, expires).update(hidden=True)

    def purge(self):
        with commit_on_success():
            meta = self.model._meta
            cursor = self.connection_for_write().cursor()
            cursor.execute(
                'DELETE FROM {0.db_table} WHERE hidden=%s'.format(meta),
                (True, ),
            )

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from __future__ import absolute_import

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.db import DatabaseError


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'TaskMeta'
        db.create_table('celery_taskmeta', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('task_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
                ('status', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=50)),
                ('result', self.gf('djcelery.picklefield.PickledObjectField')(default=None, null=True)),
                ('date_done', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
                ('traceback', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),))
        db.send_create_signal('djcelery', ['TaskMeta'])

        # Adding model 'TaskSetMeta'
        db.create_table('celery_tasksetmeta', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('taskset_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
                ('result', self.gf('djcelery.picklefield.PickledObjectField')()),
                ('date_done', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),))
        db.send_create_signal('djcelery', ['TaskSetMeta'])

        # Adding model 'IntervalSchedule'
        db.create_table('djcelery_intervalschedule', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('every', self.gf('django.db.models.fields.IntegerField')()),
                ('period', self.gf('django.db.models.fields.CharField')(max_length=24)),))
        db.send_create_signal('djcelery', ['IntervalSchedule'])

        # Adding model 'CrontabSchedule'
        db.create_table('djcelery_crontabschedule', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('minute', self.gf('django.db.models.fields.CharField')(default='*', max_length=64)),
                ('hour', self.gf('django.db.models.fields.CharField')(default='*', max_length=64)),
                ('day_of_week', self.gf('django.db.models.fields.CharField')(default='*', max_length=64)),))
        db.send_create_signal('djcelery', ['CrontabSchedule'])

        # Adding model 'PeriodicTasks'
        db.create_table('djcelery_periodictasks', (
                ('ident', self.gf('django.db.models.fields.SmallIntegerField')(default=1, unique=True, primary_key=True)),
                ('last_update', self.gf('django.db.models.fields.DateTimeField')()),))
        db.send_create_signal('djcelery', ['PeriodicTasks'])

        # Adding model 'PeriodicTask'
        db.create_table('djcelery_periodictask', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
                ('task', self.gf('django.db.models.fields.CharField')(max_length=200)),
                ('interval', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djcelery.IntervalSchedule'], null=True, blank=True)),
                ('crontab', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djcelery.CrontabSchedule'], null=True, blank=True)),
                ('args', self.gf('django.db.models.fields.TextField')(default='[]', blank=True)),
                ('kwargs', self.gf('django.db.models.fields.TextField')(default='{}', blank=True)),
                ('queue', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
                ('exchange', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
                ('routing_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
                ('expires', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
                ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
                ('last_run_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
                ('total_run_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
                ('date_changed', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),))
        db.send_create_signal('djcelery', ['PeriodicTask'])

        # Adding model 'WorkerState'
        db.create_table('djcelery_workerstate', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('hostname', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
                ('last_heartbeat', self.gf('django.db.models.fields.DateTimeField')(null=True, db_index=True)),))
        db.send_create_signal('djcelery', ['WorkerState'])

        # Adding model 'TaskState'
        db.create_table('djcelery_taskstate', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('state', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
                ('task_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=36)),
                ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, db_index=True)),
                ('tstamp', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
                ('args', self.gf('django.db.models.fields.TextField')(null=True)),
                ('kwargs', self.gf('django.db.models.fields.TextField')(null=True)),
                ('eta', self.gf('django.db.models.fields.DateTimeField')(null=True)),
                ('expires', self.gf('django.db.models.fields.DateTimeField')(null=True)),
                ('result', self.gf('django.db.models.fields.TextField')(null=True)),
                ('traceback', self.gf('django.db.models.fields.TextField')(null=True)),
                ('runtime', self.gf('django.db.models.fields.FloatField')(null=True)),
                ('retries', self.gf('django.db.models.fields.IntegerField')(default=0)),
                ('worker', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djcelery.WorkerState'], null=True)),
                ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),))
        db.send_create_signal('djcelery', ['TaskState'])


    def backwards(self, orm):

        # Deleting model 'TaskMeta'
        db.delete_table('celery_taskmeta')

        # Deleting model 'TaskSetMeta'
        db.delete_table('celery_tasksetmeta')

        # Deleting model 'IntervalSchedule'
        db.delete_table('djcelery_intervalschedule')

        # Deleting model 'CrontabSchedule'
        db.delete_table('djcelery_crontabschedule')

        # Deleting model 'PeriodicTasks'
        db.delete_table('djcelery_periodictasks')

        # Deleting model 'PeriodicTask'
        db.delete_table('djcelery_periodictask')

        # Deleting model 'WorkerState'
        db.delete_table('djcelery_workerstate')

        # Deleting model 'TaskState'
        db.delete_table('djcelery_taskstate')


    models = {
        'djcelery.crontabschedule': {
            'Meta': {'object_name': 'CrontabSchedule'},
            'day_of_week': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'minute': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'})
        },
        'djcelery.intervalschedule': {
            'Meta': {'object_name': 'IntervalSchedule'},
            'every': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        'djcelery.periodictask': {
            'Meta': {'object_name': 'PeriodicTask'},
            'args': ('django.db.models.fields.TextField', [], {'default': "'[]'", 'blank': 'True'}),
            'crontab': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.CrontabSchedule']", 'null': 'True', 'blank': 'True'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exchange': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.IntervalSchedule']", 'null': 'True', 'blank': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            'last_run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'queue': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_run_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'djcelery.periodictasks': {
            'Meta': {'object_name': 'PeriodicTasks'},
            'ident': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'unique': 'True', 'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {})
        },
        'djcelery.taskmeta': {
            'Meta': {'object_name': 'TaskMeta', 'db_table': "'celery_taskmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {'default': 'None', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'djcelery.tasksetmeta': {
            'Meta': {'object_name': 'TaskSetMeta', 'db_table': "'celery_tasksetmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {}),
            'taskset_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'djcelery.taskstate': {
            'Meta': {'ordering': "['-tstamp']", 'object_name': 'TaskState'},
            'args': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'eta': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_index': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'runtime': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'tstamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.WorkerState']", 'null': 'True'})
        },
        'djcelery.workerstate': {
            'Meta': {'ordering': "['-last_heartbeat']", 'object_name': 'WorkerState'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['djcelery']

########NEW FILE########
__FILENAME__ = 0002_v25_changes
# encoding: utf-8
from __future__ import absolute_import
from south.db import db
from south.v2 import SchemaMigration
from django.db import connections


class Migration(SchemaMigration):

    def forwards(self, orm):
        conn = connections[db.db_alias]
        table_list = conn.introspection.get_table_list(conn.cursor())
        if 'celery_taskmeta' not in table_list:
            self.create_celery_taskmeta()
        if 'celery_tasksetmeta' not in table_list:
            self.create_celery_tasksetmeta()
        self.apply_current_migration()

    def create_celery_taskmeta(self):
        # Adding model 'TaskMeta'
        db.create_table('celery_taskmeta', (
                    ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                    ('task_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
                    ('status', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=50)),
                    ('result', self.gf('djcelery.picklefield.PickledObjectField')(default=None, null=True)),
                    ('date_done', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
                    ('traceback', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('djcelery', ['TaskMeta'])

    def create_celery_tasksetmeta(self):
        # Adding model 'TaskSetMeta'
        db.create_table('celery_tasksetmeta', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('taskset_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
                ('result', self.gf('djcelery.picklefield.PickledObjectField')()),
                ('date_done', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('djcelery', ['TaskSetMeta'])

    def apply_current_migration(self):
        # Adding field 'PeriodicTask.description'
        db.add_column('djcelery_periodictask', 'description', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'TaskMeta.hidden'
        db.add_column('celery_taskmeta', 'hidden', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True), keep_default=False)

        # Adding field 'TaskSetMeta.hidden'
        db.add_column('celery_tasksetmeta', 'hidden', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'PeriodicTask.description'
        db.delete_column('djcelery_periodictask', 'description')

        # Deleting field 'TaskMeta.hidden'
        db.delete_column('celery_taskmeta', 'hidden')

        # Deleting field 'TaskSetMeta.hidden'
        db.delete_column('celery_tasksetmeta', 'hidden')


    models = {
        'djcelery.crontabschedule': {
            'Meta': {'object_name': 'CrontabSchedule'},
            'day_of_week': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'minute': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'})
        },
        'djcelery.intervalschedule': {
            'Meta': {'object_name': 'IntervalSchedule'},
            'every': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        'djcelery.periodictask': {
            'Meta': {'object_name': 'PeriodicTask'},
            'args': ('django.db.models.fields.TextField', [], {'default': "'[]'", 'blank': 'True'}),
            'crontab': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.CrontabSchedule']", 'null': 'True', 'blank': 'True'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exchange': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.IntervalSchedule']", 'null': 'True', 'blank': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            'last_run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'queue': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_run_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'djcelery.periodictasks': {
            'Meta': {'object_name': 'PeriodicTasks'},
            'ident': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'unique': 'True', 'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {})
        },
        'djcelery.taskmeta': {
            'Meta': {'object_name': 'TaskMeta', 'db_table': "'celery_taskmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {'default': 'None', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'djcelery.tasksetmeta': {
            'Meta': {'object_name': 'TaskSetMeta', 'db_table': "'celery_tasksetmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {}),
            'taskset_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'djcelery.taskstate': {
            'Meta': {'ordering': "['-tstamp']", 'object_name': 'TaskState'},
            'args': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'eta': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_index': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'runtime': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'tstamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.WorkerState']", 'null': 'True'})
        },
        'djcelery.workerstate': {
            'Meta': {'ordering': "['-last_heartbeat']", 'object_name': 'WorkerState'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['djcelery']

########NEW FILE########
__FILENAME__ = 0003_v26_changes
# encoding: utf-8
from __future__ import absolute_import
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'CrontabSchedule.day_of_month'
        db.add_column('djcelery_crontabschedule', 'day_of_month', self.gf('django.db.models.fields.CharField')(default='*', max_length=64), keep_default=False)

        # Adding field 'CrontabSchedule.month_of_year'
        db.add_column('djcelery_crontabschedule', 'month_of_year', self.gf('django.db.models.fields.CharField')(default='*', max_length=64), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'CrontabSchedule.day_of_month'
        db.delete_column('djcelery_crontabschedule', 'day_of_month')

        # Deleting field 'CrontabSchedule.month_of_year'
        db.delete_column('djcelery_crontabschedule', 'month_of_year')


    models = {
        'djcelery.crontabschedule': {
            'Meta': {'object_name': 'CrontabSchedule'},
            'day_of_month': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'day_of_week': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'minute': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'month_of_year': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'})
        },
        'djcelery.intervalschedule': {
            'Meta': {'object_name': 'IntervalSchedule'},
            'every': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        'djcelery.periodictask': {
            'Meta': {'object_name': 'PeriodicTask'},
            'args': ('django.db.models.fields.TextField', [], {'default': "'[]'", 'blank': 'True'}),
            'crontab': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.CrontabSchedule']", 'null': 'True', 'blank': 'True'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exchange': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.IntervalSchedule']", 'null': 'True', 'blank': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            'last_run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'queue': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_run_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'djcelery.periodictasks': {
            'Meta': {'object_name': 'PeriodicTasks'},
            'ident': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'unique': 'True', 'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {})
        },
        'djcelery.taskmeta': {
            'Meta': {'object_name': 'TaskMeta', 'db_table': "'celery_taskmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {'default': 'None', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'djcelery.tasksetmeta': {
            'Meta': {'object_name': 'TaskSetMeta', 'db_table': "'celery_tasksetmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {}),
            'taskset_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'djcelery.taskstate': {
            'Meta': {'ordering': "['-tstamp']", 'object_name': 'TaskState'},
            'args': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'eta': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_index': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'runtime': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'tstamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.WorkerState']", 'null': 'True'})
        },
        'djcelery.workerstate': {
            'Meta': {'ordering': "['-last_heartbeat']", 'object_name': 'WorkerState'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['djcelery']

########NEW FILE########
__FILENAME__ = 0004_v30_changes
# encoding: utf-8
from __future__ import absolute_import
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TaskMeta.meta'
        db.add_column('celery_taskmeta', 'meta', self.gf('djcelery.picklefield.PickledObjectField')(default=None, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TaskMeta.meta'
        db.delete_column('celery_taskmeta', 'meta')


    models = {
        'djcelery.crontabschedule': {
            'Meta': {'object_name': 'CrontabSchedule'},
            'day_of_month': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'day_of_week': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'hour': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'minute': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'}),
            'month_of_year': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '64'})
        },
        'djcelery.intervalschedule': {
            'Meta': {'object_name': 'IntervalSchedule'},
            'every': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.CharField', [], {'max_length': '24'})
        },
        'djcelery.periodictask': {
            'Meta': {'object_name': 'PeriodicTask'},
            'args': ('django.db.models.fields.TextField', [], {'default': "'[]'", 'blank': 'True'}),
            'crontab': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.CrontabSchedule']", 'null': 'True', 'blank': 'True'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exchange': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.IntervalSchedule']", 'null': 'True', 'blank': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            'last_run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'queue': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total_run_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'djcelery.periodictasks': {
            'Meta': {'object_name': 'PeriodicTasks'},
            'ident': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'unique': 'True', 'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {})
        },
        'djcelery.taskmeta': {
            'Meta': {'object_name': 'TaskMeta', 'db_table': "'celery_taskmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('djcelery.picklefield.PickledObjectField', [], {'default': 'None', 'null': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {'default': 'None', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'djcelery.tasksetmeta': {
            'Meta': {'object_name': 'TaskSetMeta', 'db_table': "'celery_tasksetmeta'"},
            'date_done': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('djcelery.picklefield.PickledObjectField', [], {}),
            'taskset_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'djcelery.taskstate': {
            'Meta': {'ordering': "['-tstamp']", 'object_name': 'TaskState'},
            'args': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'eta': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_index': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'runtime': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'tstamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djcelery.WorkerState']", 'null': 'True'})
        },
        'djcelery.workerstate': {
            'Meta': {'ordering': "['-last_heartbeat']", 'object_name': 'WorkerState'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['djcelery']

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import, unicode_literals

from datetime import timedelta, datetime
from time import time, mktime

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _

from celery import schedules
from celery import states
from celery.events.state import heartbeat_expires
from celery.utils.timeutils import timedelta_seconds

from . import managers
from .picklefield import PickledObjectField
from .utils import now

TASK_STATE_CHOICES = zip(states.ALL_STATES, states.ALL_STATES)


class TaskMeta(models.Model):
    """Task result/status."""
    task_id = models.CharField(_('task id'), max_length=255, unique=True)
    status = models.CharField(
        _('state'),
        max_length=50, default=states.PENDING, choices=TASK_STATE_CHOICES,
    )
    result = PickledObjectField(null=True, default=None, editable=False)
    date_done = models.DateTimeField(_('done at'), auto_now=True)
    traceback = models.TextField(_('traceback'), blank=True, null=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    # TODO compression was enabled by mistake, we need to disable it
    # but this is a backwards incompatible change that needs planning.
    meta = PickledObjectField(
        compress=True, null=True, default=None, editable=False,
    )

    objects = managers.TaskManager()

    class Meta:
        verbose_name = _('task state')
        verbose_name_plural = _('task states')
        db_table = 'celery_taskmeta'

    def to_dict(self):
        return {'task_id': self.task_id,
                'status': self.status,
                'result': self.result,
                'date_done': self.date_done,
                'traceback': self.traceback,
                'children': (self.meta or {}).get('children')}

    def __unicode__(self):
        return '<Task: {0.task_id} state={0.status}>'.format(self)


class TaskSetMeta(models.Model):
    """TaskSet result"""
    taskset_id = models.CharField(_('group id'), max_length=255, unique=True)
    result = PickledObjectField()
    date_done = models.DateTimeField(_('created at'), auto_now=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)

    objects = managers.TaskSetManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('saved group result')
        verbose_name_plural = _('saved group results')
        db_table = 'celery_tasksetmeta'

    def to_dict(self):
        return {'taskset_id': self.taskset_id,
                'result': self.result,
                'date_done': self.date_done}

    def __unicode__(self):
        return '<TaskSet: {0.taskset_id}>'.format(self)


PERIOD_CHOICES = (('days', _('Days')),
                  ('hours', _('Hours')),
                  ('minutes', _('Minutes')),
                  ('seconds', _('Seconds')),
                  ('microseconds', _('Microseconds')))


class IntervalSchedule(models.Model):
    every = models.IntegerField(_('every'), null=False)
    period = models.CharField(
        _('period'), max_length=24, choices=PERIOD_CHOICES,
    )

    class Meta:
        verbose_name = _('interval')
        verbose_name_plural = _('intervals')
        ordering = ['period', 'every']

    @property
    def schedule(self):
        return schedules.schedule(timedelta(**{self.period: self.every}))

    @classmethod
    def from_schedule(cls, schedule, period='seconds'):
        every = timedelta_seconds(schedule.run_every)
        try:
            return cls.objects.get(every=every, period=period)
        except cls.DoesNotExist:
            return cls(every=every, period=period)
        except MultipleObjectsReturned:
            cls.objects.filter(every=every, period=period).delete()
            return cls(every=every, period=period)

    def __unicode__(self):
        if self.every == 1:
            return _('every {0.period_singular}').format(self)
        return _('every {0.every} {0.period}').format(self)

    @property
    def period_singular(self):
        return self.period[:-1]


class CrontabSchedule(models.Model):
    minute = models.CharField(_('minute'), max_length=64, default='*')
    hour = models.CharField(_('hour'), max_length=64, default='*')
    day_of_week = models.CharField(
        _('day of week'), max_length=64, default='*',
    )
    day_of_month = models.CharField(
        _('day of month'), max_length=64, default='*',
    )
    month_of_year = models.CharField(
        _('month of year'), max_length=64, default='*',
    )

    class Meta:
        verbose_name = _('crontab')
        verbose_name_plural = _('crontabs')
        ordering = ['month_of_year', 'day_of_month',
                    'day_of_week', 'hour', 'minute']

    def __unicode__(self):
        rfield = lambda f: f and str(f).replace(' ', '') or '*'
        return '{0} {1} {2} {3} {4} (m/h/d/dM/MY)'.format(
            rfield(self.minute), rfield(self.hour), rfield(self.day_of_week),
            rfield(self.day_of_month), rfield(self.month_of_year),
        )

    @property
    def schedule(self):
        return schedules.crontab(minute=self.minute,
                                 hour=self.hour,
                                 day_of_week=self.day_of_week,
                                 day_of_month=self.day_of_month,
                                 month_of_year=self.month_of_year)

    @classmethod
    def from_schedule(cls, schedule):
        spec = {'minute': schedule._orig_minute,
                'hour': schedule._orig_hour,
                'day_of_week': schedule._orig_day_of_week,
                'day_of_month': schedule._orig_day_of_month,
                'month_of_year': schedule._orig_month_of_year}
        try:
            return cls.objects.get(**spec)
        except cls.DoesNotExist:
            return cls(**spec)
        except MultipleObjectsReturned:
            cls.objects.filter(**spec).delete()
            return cls(**spec)


class PeriodicTasks(models.Model):
    ident = models.SmallIntegerField(default=1, primary_key=True, unique=True)
    last_update = models.DateTimeField(null=False)

    objects = managers.ExtendedManager()

    @classmethod
    def changed(cls, instance, **kwargs):
        if not instance.no_changes:
            cls.objects.update_or_create(ident=1,
                                         defaults={'last_update': now()})

    @classmethod
    def last_change(cls):
        try:
            return cls.objects.get(ident=1).last_update
        except cls.DoesNotExist:
            pass


class PeriodicTask(models.Model):
    name = models.CharField(
        _('name'), max_length=200, unique=True,
        help_text=_('Useful description'),
    )
    task = models.CharField(_('task name'), max_length=200)
    interval = models.ForeignKey(
        IntervalSchedule,
        null=True, blank=True, verbose_name=_('interval'),
    )
    crontab = models.ForeignKey(
        CrontabSchedule, null=True, blank=True, verbose_name=_('crontab'),
        help_text=_('Use one of interval/crontab'),
    )
    args = models.TextField(
        _('Arguments'), blank=True, default='[]',
        help_text=_('JSON encoded positional arguments'),
    )
    kwargs = models.TextField(
        _('Keyword arguments'), blank=True, default='{}',
        help_text=_('JSON encoded keyword arguments'),
    )
    queue = models.CharField(
        _('queue'), max_length=200, blank=True, null=True, default=None,
        help_text=_('Queue defined in CELERY_QUEUES'),
    )
    exchange = models.CharField(
        _('exchange'), max_length=200, blank=True, null=True, default=None,
    )
    routing_key = models.CharField(
        _('routing key'), max_length=200, blank=True, null=True, default=None,
    )
    expires = models.DateTimeField(
        _('expires'), blank=True, null=True,
    )
    enabled = models.BooleanField(
        _('enabled'), default=True,
    )
    last_run_at = models.DateTimeField(
        auto_now=False, auto_now_add=False,
        editable=False, blank=True, null=True,
    )
    total_run_count = models.PositiveIntegerField(
        default=0, editable=False,
    )
    date_changed = models.DateTimeField(auto_now=True)
    description = models.TextField(_('description'), blank=True)

    objects = managers.PeriodicTaskManager()
    no_changes = False

    class Meta:
        verbose_name = _('periodic task')
        verbose_name_plural = _('periodic tasks')

    def validate_unique(self, *args, **kwargs):
        super(PeriodicTask, self).validate_unique(*args, **kwargs)
        if not self.interval and not self.crontab:
            raise ValidationError(
                {'interval': ['One of interval or crontab must be set.']})
        if self.interval and self.crontab:
            raise ValidationError(
                {'crontab': ['Only one of interval or crontab must be set']})

    def save(self, *args, **kwargs):
        self.exchange = self.exchange or None
        self.routing_key = self.routing_key or None
        self.queue = self.queue or None
        if not self.enabled:
            self.last_run_at = None
        super(PeriodicTask, self).save(*args, **kwargs)

    def __unicode__(self):
        fmt = '{0.name}: {{no schedule}}'
        if self.interval:
            fmt = '{0.name}: {0.interval}'
        if self.crontab:
            fmt = '{0.name}: {0.crontab}'
        return fmt.format(self)

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        if self.crontab:
            return self.crontab.schedule

signals.pre_delete.connect(PeriodicTasks.changed, sender=PeriodicTask)
signals.pre_save.connect(PeriodicTasks.changed, sender=PeriodicTask)


class WorkerState(models.Model):
    hostname = models.CharField(_('hostname'), max_length=255, unique=True)
    last_heartbeat = models.DateTimeField(_('last heartbeat'), null=True,
                                          db_index=True)

    objects = managers.ExtendedManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('worker')
        verbose_name_plural = _('workers')
        get_latest_by = 'last_heartbeat'
        ordering = ['-last_heartbeat']

    def __unicode__(self):
        return self.hostname

    def __repr__(self):
        return '<WorkerState: {0.hostname}>'.format(self)

    def is_alive(self):
        if self.last_heartbeat:
            return time() < heartbeat_expires(self.heartbeat_timestamp)
        return False

    @property
    def heartbeat_timestamp(self):
        return mktime(self.last_heartbeat.timetuple())


class TaskState(models.Model):
    state = models.CharField(
        _('state'), max_length=64, choices=TASK_STATE_CHOICES, db_index=True,
    )
    task_id = models.CharField(_('UUID'), max_length=36, unique=True)
    name = models.CharField(
        _('name'), max_length=200, null=True, db_index=True,
    )
    tstamp = models.DateTimeField(_('event received at'), db_index=True)
    args = models.TextField(_('Arguments'), null=True)
    kwargs = models.TextField(_('Keyword arguments'), null=True)
    eta = models.DateTimeField(_('ETA'), null=True)
    expires = models.DateTimeField(_('expires'), null=True)
    result = models.TextField(_('result'), null=True)
    traceback = models.TextField(_('traceback'), null=True)
    runtime = models.FloatField(
        _('execution time'), null=True,
        help_text=_('in seconds if task succeeded'),
    )
    retries = models.IntegerField(_('number of retries'), default=0)
    worker = models.ForeignKey(
        WorkerState, null=True, verbose_name=_('worker'),
    )
    hidden = models.BooleanField(editable=False, default=False, db_index=True)

    objects = managers.TaskStateManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('task')
        verbose_name_plural = _('tasks')
        get_latest_by = 'tstamp'
        ordering = ['-tstamp']

    def save(self, *args, **kwargs):
        if self.eta is not None:
            self.eta = datetime.utcfromtimestamp(float('%d.%s' % (
                mktime(self.eta.timetuple()), self.eta.microsecond,
            )))
        if self.expires is not None:
            self.expires = datetime.utcfromtimestamp(float('%d.%s' % (
                mktime(self.expires.timetuple()), self.expires.microsecond,
            )))
        super(TaskState, self).save(*args, **kwargs)

    def __unicode__(self):
        name = self.name or 'UNKNOWN'
        s = '{0.state:<10} {0.task_id:<36} {1}'.format(self, name)
        if self.eta:
            s += ' eta:{0.eta}'.format(self)
        return s

    def __repr__(self):
        return '<TaskState: {0.state} {1}[{0.task_id}] ts:{0.tstamp}>'.format(
            self, self.name or 'UNKNOWN',
        )

########NEW FILE########
__FILENAME__ = mon
from __future__ import absolute_import, unicode_literals

import os
import sys
import types

from celery.app.defaults import strtobool
from celery.utils import import_from_cwd

DEFAULT_APPS = ('django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.admin',
                'django.contrib.admindocs',
                'djcelery')

DEFAULTS = {'ROOT_URLCONF': 'djcelery.monproj.urls',
            'DATABASE_ENGINE': 'sqlite3',
            'DATABASE_NAME': 'djcelerymon.db',
            'DATABASES': {'default': {
                            'ENGINE': 'django.db.backends.sqlite3',
                            'NAME': 'djcelerymon.db'}},
            'BROKER_URL': 'amqp://',
            'SITE_ID': 1,
            'INSTALLED_APPS': DEFAULT_APPS,
            'DEBUG': strtobool(os.environ.get('DJCELERYMON_DEBUG', '0'))}


def default_settings(name='__default_settings__'):
    c = type(name, (types.ModuleType, ), DEFAULTS)(name)
    c.__dict__.update({'__file__': __file__})
    sys.modules[name] = c
    return name


def configure():
    from celery import current_app
    from celery.loaders.default import DEFAULT_CONFIG_MODULE
    from django.conf import settings

    app = current_app
    conf = {}

    if not settings.configured:
        if 'loader' in app.__dict__ and app.loader.configured:
            conf = current_app.loader.conf
        else:
            os.environ.pop('CELERY_LOADER', None)
            settings_module = os.environ.get('CELERY_CONFIG_MODULE',
                                             DEFAULT_CONFIG_MODULE)
            try:
                import_from_cwd(settings_module)
            except ImportError:
                settings_module = default_settings()
        settings.configure(SETTINGS_MODULE=settings_module,
                           **dict(DEFAULTS, **conf))


def run_monitor(argv):
    from .management.commands import djcelerymon
    djcelerymon.Command().run_from_argv([argv[0], 'djcelerymon'] + argv[1:])


def main(argv=sys.argv):
    from django.core import management
    os.environ['CELERY_LOADER'] = 'default'
    configure()
    management.call_command('syncdb')
    run_monitor(argv)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import, unicode_literals

try:
    from django.conf.urls import (patterns, include, url,
                                  handler500, handler404)
except ImportError:
    from django.conf.urls.defaults import (patterns, include, url,  # noqa
                                  handler500, handler404)
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    (r'^doc/', include('django.contrib.admindocs.urls')),

    (r'', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = picklefield
"""
    Based on django-picklefield which is
    Copyright (c) 2009-2010 Gintautas Miliauskas
    but some improvements including not deepcopying values.

    Provides an implementation of a pickled object field.
    Such fields can contain any picklable objects.

    The implementation is taken and adopted from Django snippet #1694
    <http://www.djangosnippets.org/snippets/1694/> by Taavi Taijala,
    which is in turn based on Django snippet #513
    <http://www.djangosnippets.org/snippets/513/> by Oliver Beattie.

"""
from __future__ import absolute_import, unicode_literals

from base64 import b64encode, b64decode
from zlib import compress, decompress

from celery.five import with_metaclass
from celery.utils.serialization import pickle
from kombu.utils.encoding import bytes_to_str, str_to_bytes

from django.db import models

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text  # noqa

DEFAULT_PROTOCOL = 2

NO_DECOMPRESS_HEADER = b'\x1e\x00r8d9qwwerwhA@'


@with_metaclass(models.SubfieldBase, skip_attrs=set([
    'db_type',
    'get_db_prep_save'
    ]))
class BaseField(models.Field):
    pass


class PickledObject(str):
    pass


def maybe_compress(value, do_compress=False):
    if do_compress:
        return compress(str_to_bytes(value))
    return value


def maybe_decompress(value, do_decompress=False):
    if do_decompress:
        if str_to_bytes(value[:15]) != NO_DECOMPRESS_HEADER:
            return decompress(str_to_bytes(value))
    return value


def encode(value, compress_object=False, pickle_protocol=DEFAULT_PROTOCOL):
    return bytes_to_str(b64encode(maybe_compress(
        pickle.dumps(value, pickle_protocol), compress_object),
    ))


def decode(value, compress_object=False):
    return pickle.loads(maybe_decompress(b64decode(value), compress_object))


class PickledObjectField(BaseField):

    def __init__(self, compress=False, protocol=DEFAULT_PROTOCOL,
                 *args, **kwargs):
        self.compress = compress
        self.protocol = protocol
        kwargs.setdefault('editable', False)
        super(PickledObjectField, self).__init__(*args, **kwargs)

    def get_default(self):
        if self.has_default():
            return self.default() if callable(self.default) else self.default
        return super(PickledObjectField, self).get_default()

    def to_python(self, value):
        if value is not None:
            try:
                return decode(value, self.compress)
            except Exception:
                if isinstance(value, PickledObject):
                    raise
                return value

    def get_db_prep_value(self, value, **kwargs):
        if value is not None and not isinstance(value, PickledObject):
            return force_text(encode(value, self.compress, self.protocol))
        return value

    def value_to_string(self, obj):
        return self.get_db_prep_value(self._get_val_from_obj(obj))

    def get_internal_type(self):
        return 'TextField'

    def get_db_prep_lookup(self, lookup_type, value, *args, **kwargs):
        if lookup_type not in ['exact', 'in', 'isnull']:
            raise TypeError(
                'Lookup type {0} is not supported.'.format(lookup_type))
        return super(PickledObjectField, self) \
            .get_db_prep_lookup(*args, **kwargs)

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules(
        [], [r'^djcelery\.picklefield\.PickledObjectField'],
    )

########NEW FILE########
__FILENAME__ = schedulers
from __future__ import absolute_import

import logging

from multiprocessing.util import Finalize

from anyjson import loads, dumps
from celery import current_app
from celery import schedules
from celery.beat import Scheduler, ScheduleEntry
from celery.utils.encoding import safe_str, safe_repr
from celery.utils.log import get_logger
from celery.utils.timeutils import is_naive

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .db import commit_on_success
from .models import (PeriodicTask, PeriodicTasks,
                     CrontabSchedule, IntervalSchedule)
from .utils import DATABASE_ERRORS, make_aware

# This scheduler must wake up more frequently than the
# regular of 5 minutes because it needs to take external
# changes to the schedule into account.
DEFAULT_MAX_INTERVAL = 5  # seconds

ADD_ENTRY_ERROR = """\
Couldn't add entry %r to database schedule: %r. Contents: %r
"""

logger = get_logger(__name__)
debug, info, error = logger.debug, logger.info, logger.error


class ModelEntry(ScheduleEntry):
    model_schedules = ((schedules.crontab, CrontabSchedule, 'crontab'),
                       (schedules.schedule, IntervalSchedule, 'interval'))
    save_fields = ['last_run_at', 'total_run_count', 'no_changes']

    def __init__(self, model):
        self.app = current_app._get_current_object()
        self.name = model.name
        self.task = model.task
        try:
            self.schedule = model.schedule
        except model.DoesNotExist:
            logger.error('Schedule was removed from database')
            logger.warning('Disabling %s', self.name)
            self._disable(model)
        try:
            self.args = loads(model.args or '[]')
            self.kwargs = loads(model.kwargs or '{}')
        except ValueError:
            logging.error('Failed to serialize arguments for %s.', self.name,
                          exc_info=1)
            logging.warning('Disabling %s', self.name)
            self._disable(model)

        self.options = {'queue': model.queue,
                        'exchange': model.exchange,
                        'routing_key': model.routing_key,
                        'expires': model.expires}
        self.total_run_count = model.total_run_count
        self.model = model

        if not model.last_run_at:
            model.last_run_at = self._default_now()
        orig = self.last_run_at = model.last_run_at
        if not is_naive(self.last_run_at):
            self.last_run_at = self.last_run_at.replace(tzinfo=None)
        assert orig.hour == self.last_run_at.hour  # timezone sanity

    def _disable(self, model):
        model.no_changes = True
        model.enabled = False
        model.save()

    def is_due(self):
        if not self.model.enabled:
            return False, 5.0   # 5 second delay for re-enable.
        return self.schedule.is_due(self.last_run_at)

    def _default_now(self):
        return self.app.now()

    def __next__(self):
        self.model.last_run_at = self.app.now()
        self.model.total_run_count += 1
        self.model.no_changes = True
        return self.__class__(self.model)
    next = __next__  # for 2to3

    def save(self):
        # Object may not be synchronized, so only
        # change the fields we care about.
        obj = self.model._default_manager.get(pk=self.model.pk)
        for field in self.save_fields:
            setattr(obj, field, getattr(self.model, field))
        obj.last_run_at = make_aware(obj.last_run_at)
        obj.save()

    @classmethod
    def to_model_schedule(cls, schedule):
        for schedule_type, model_type, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                model_schedule = model_type.from_schedule(schedule)
                model_schedule.save()
                return model_schedule, model_field
        raise ValueError(
            'Cannot convert schedule type {0!r} to model'.format(schedule))

    @classmethod
    def from_entry(cls, name, skip_fields=('relative', 'options'), **entry):
        options = entry.get('options') or {}
        fields = dict(entry)
        for skip_field in skip_fields:
            fields.pop(skip_field, None)
        schedule = fields.pop('schedule')
        model_schedule, model_field = cls.to_model_schedule(schedule)
        fields[model_field] = model_schedule
        fields['args'] = dumps(fields.get('args') or [])
        fields['kwargs'] = dumps(fields.get('kwargs') or {})
        fields['queue'] = options.get('queue')
        fields['exchange'] = options.get('exchange')
        fields['routing_key'] = options.get('routing_key')
        return cls(PeriodicTask._default_manager.update_or_create(
            name=name, defaults=fields,
        ))

    def __repr__(self):
        return '<ModelEntry: {0} {1}(*{2}, **{3}) {{4}}>'.format(
            safe_str(self.name), self.task, safe_repr(self.args),
            safe_repr(self.kwargs), self.schedule,
        )


class DatabaseScheduler(Scheduler):
    Entry = ModelEntry
    Model = PeriodicTask
    Changes = PeriodicTasks
    _schedule = None
    _last_timestamp = None
    _initial_read = False

    def __init__(self, *args, **kwargs):
        self._dirty = set()
        self._finalize = Finalize(self, self.sync, exitpriority=5)
        Scheduler.__init__(self, *args, **kwargs)
        self.max_interval = (
            kwargs.get('max_interval') or
            self.app.conf.CELERYBEAT_MAX_LOOP_INTERVAL or
            DEFAULT_MAX_INTERVAL)

    def setup_schedule(self):
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.CELERYBEAT_SCHEDULE)

    def all_as_schedule(self):
        debug('DatabaseScheduler: Fetching database schedule')
        s = {}
        for model in self.Model.objects.enabled():
            try:
                s[model.name] = self.Entry(model)
            except ValueError:
                pass
        return s

    def schedule_changed(self):
        try:
            # If MySQL is running with transaction isolation level
            # REPEATABLE-READ (default), then we won't see changes done by
            # other transactions until the current transaction is
            # committed (Issue #41).
            try:
                transaction.commit()
            except transaction.TransactionManagementError:
                pass  # not in transaction management.

            last, ts = self._last_timestamp, self.Changes.last_change()
        except DATABASE_ERRORS as exc:
            error('Database gave error: %r', exc, exc_info=1)
            return False
        try:
            if ts and ts > (last if last else ts):
                return True
        finally:
            self._last_timestamp = ts
        return False

    def reserve(self, entry):
        new_entry = Scheduler.reserve(self, entry)
        # Need to store entry by name, because the entry may change
        # in the mean time.
        self._dirty.add(new_entry.name)
        return new_entry

    def sync(self):
        info('Writing entries...')
        _tried = set()
        try:
            with commit_on_success():
                while self._dirty:
                    try:
                        name = self._dirty.pop()
                        _tried.add(name)
                        self.schedule[name].save()
                    except (KeyError, ObjectDoesNotExist):
                        pass
        except DATABASE_ERRORS as exc:
            # retry later
            self._dirty |= _tried
            error('Database error while sync: %r', exc, exc_info=1)

    def update_from_dict(self, dict_):
        s = {}
        for name, entry in dict_.items():
            try:
                s[name] = self.Entry.from_entry(name, **entry)
            except Exception as exc:
                error(ADD_ENTRY_ERROR, name, exc, entry)
        self.schedule.update(s)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.CELERY_TASK_RESULT_EXPIRES:
            entries.setdefault(
                'celery.backend_cleanup', {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*'),
                    'options': {'expires': 12 * 3600},
                },
            )
        self.update_from_dict(entries)

    @property
    def schedule(self):
        update = False
        if not self._initial_read:
            debug('DatabaseScheduler: intial read')
            update = True
            self._initial_read = True
        elif self.schedule_changed():
            info('DatabaseScheduler: Schedule changed.')
            update = True

        if update:
            self.sync()
            self._schedule = self.all_as_schedule()
            if logger.isEnabledFor(logging.DEBUG):
                debug('Current schedule:\n%s', '\n'.join(
                    repr(entry) for entry in self._schedule.itervalues()),
                )
        return self._schedule

########NEW FILE########
__FILENAME__ = snapshot
from __future__ import absolute_import, unicode_literals

from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings

from celery import states
from celery.events.state import Task
from celery.events.snapshot import Polaroid
from celery.five import monotonic
from celery.utils.log import get_logger
from celery.utils.timeutils import maybe_iso8601

from .models import WorkerState, TaskState
from .utils import maybe_make_aware

WORKER_UPDATE_FREQ = 60  # limit worker timestamp write freq.
SUCCESS_STATES = frozenset([states.SUCCESS])

# Expiry can be timedelta or None for never expire.
EXPIRE_SUCCESS = getattr(settings, 'CELERYCAM_EXPIRE_SUCCESS',
                         timedelta(days=1))
EXPIRE_ERROR = getattr(settings, 'CELERYCAM_EXPIRE_ERROR',
                       timedelta(days=3))
EXPIRE_PENDING = getattr(settings, 'CELERYCAM_EXPIRE_PENDING',
                         timedelta(days=5))
NOT_SAVED_ATTRIBUTES = frozenset(['name', 'args', 'kwargs', 'eta'])

logger = get_logger(__name__)
debug = logger.debug


def aware_tstamp(secs):
    """Event timestamps uses the local timezone."""
    return maybe_make_aware(datetime.utcfromtimestamp(secs))


class Camera(Polaroid):
    TaskState = TaskState
    WorkerState = WorkerState

    clear_after = True
    worker_update_freq = WORKER_UPDATE_FREQ
    expire_states = {
        SUCCESS_STATES: EXPIRE_SUCCESS,
        states.EXCEPTION_STATES: EXPIRE_ERROR,
        states.UNREADY_STATES: EXPIRE_PENDING,
    }

    def __init__(self, *args, **kwargs):
        super(Camera, self).__init__(*args, **kwargs)
        self._last_worker_write = defaultdict(lambda: (None, None))

    def get_heartbeat(self, worker):
        try:
            heartbeat = worker.heartbeats[-1]
        except IndexError:
            return
        # Check for timezone settings
        if getattr(settings, "USE_TZ", False):
            return aware_tstamp(heartbeat)
        return datetime.fromtimestamp(heartbeat)

    def handle_worker(self, hostname_worker):
        (hostname, worker) = hostname_worker
        last_write, obj = self._last_worker_write[hostname]
        if not last_write or \
                monotonic() - last_write > self.worker_update_freq:
            obj = self.WorkerState.objects.update_or_create(
                hostname=hostname,
                defaults={'last_heartbeat': self.get_heartbeat(worker)},
            )
            self._last_worker_write[hostname] = (monotonic(), obj)
        return obj

    def handle_task(self, uuid_task, worker=None):
        """Handle snapshotted event."""
        uuid, task = uuid_task
        if task.worker and task.worker.hostname:
            worker = self.handle_worker(
                (task.worker.hostname, task.worker),
            )

        defaults = {
            'name': task.name,
            'args': task.args,
            'kwargs': task.kwargs,
            'eta': maybe_make_aware(maybe_iso8601(task.eta)),
            'expires': maybe_make_aware(maybe_iso8601(task.expires)),
            'state': task.state,
            'tstamp': aware_tstamp(task.timestamp),
            'result': task.result or task.exception,
            'traceback': task.traceback,
            'runtime': task.runtime,
            'worker': worker
        }
        # Some fields are only stored in the RECEIVED event,
        # so we should remove these from default values,
        # so that they are not overwritten by subsequent states.
        [defaults.pop(attr, None) for attr in NOT_SAVED_ATTRIBUTES
         if defaults[attr] is None]
        return self.update_task(task.state,
                                task_id=uuid, defaults=defaults)

    def update_task(self, state, **kwargs):
        objects = self.TaskState.objects
        defaults = kwargs.pop('defaults', None) or {}
        if not defaults.get('name'):
            return
        obj, created = objects.get_or_create(defaults=defaults, **kwargs)
        if created:
            return obj
        else:
            if states.state(state) < states.state(obj.state):
                keep = Task.merge_rules[states.RECEIVED]
                defaults = dict(
                    (k, v) for k, v in defaults.items()
                    if k not in keep
                )

        for k, v in defaults.items():
            setattr(obj, k, v)
        for datefield in ('eta', 'expires', 'tstamp'):
            # Brute force trying to fix #183
            setattr(obj, datefield, maybe_make_aware(getattr(obj, datefield)))
        obj.save()

        return obj

    def on_shutter(self, state, commit_every=100):

        def _handle_tasks():
            for i, task in enumerate(state.tasks.items()):
                self.handle_task(task)

        for worker in state.workers.items():
            self.handle_worker(worker)
        _handle_tasks()

    def on_cleanup(self):
        expired = (self.TaskState.objects.expire_by_states(states, expires)
                   for states, expires in self.expire_states.items())
        dirty = sum(item for item in expired if item is not None)
        if dirty:
            debug('Cleanup: Marked %s objects as dirty.', dirty)
            self.TaskState.objects.purge()
            debug('Cleanup: %s objects purged.', dirty)
            return dirty
        return 0

########NEW FILE########
__FILENAME__ = req
from __future__ import absolute_import, unicode_literals

from django.test import Client
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.base import BaseHandler

from celery.utils.compat import WhateverIO


class RequestFactory(Client):
    """Class that lets you create mock Request objects for use in testing.

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
        """Similar to parent class, but returns the request object as
        soon as it has created it."""
        environ = {
            'HTTP_COOKIE': self.cookies,
            'HTTP_USER_AGENT': 'Django UnitTest Client 1.0',
            'REMOTE_ADDR': '127.0.0.1',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': WhateverIO(),
        }

        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


class MockRequest(object):

    def __init__(self):
        handler = BaseHandler()
        handler.load_middleware()
        self.request_factory = RequestFactory()
        self.middleware = handler._request_middleware

    def _make_request(self, request_method, *args, **kwargs):
        request_method_handler = getattr(self.request_factory, request_method)
        request = request_method_handler(*args, **kwargs)
        [middleware_processor(request)
            for middleware_processor in self.middleware]
        return request

    def get(self, *args, **kwargs):
        return self._make_request('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._make_request('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._make_request('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._make_request('delete', *args, **kwargs)

########NEW FILE########
__FILENAME__ = test_cache
from __future__ import absolute_import, unicode_literals

import sys

from datetime import timedelta

from billiard.einfo import ExceptionInfo
import django
from django.core.cache.backends.base import InvalidCacheBackendError

from celery import result
from celery import states
from celery.utils import gen_unique_id

from djcelery.app import app
from djcelery.backends.cache import CacheBackend
from djcelery.tests.utils import unittest


class SomeClass(object):

    def __init__(self, data):
        self.data = data


class test_CacheBackend(unittest.TestCase):

    def test_mark_as_done(self):
        cb = CacheBackend(app=app)

        tid = gen_unique_id()

        self.assertEqual(cb.get_status(tid), states.PENDING)
        self.assertIsNone(cb.get_result(tid))

        cb.mark_as_done(tid, 42)
        self.assertEqual(cb.get_status(tid), states.SUCCESS)
        self.assertEqual(cb.get_result(tid), 42)
        self.assertTrue(cb.get_result(tid), 42)

    def test_forget(self):
        b = CacheBackend(app=app)
        tid = gen_unique_id()
        b.mark_as_done(tid, {'foo': 'bar'})
        self.assertEqual(b.get_result(tid).get('foo'), 'bar')
        b.forget(tid)
        self.assertNotIn(tid, b._cache)
        self.assertIsNone(b.get_result(tid))

    def test_save_restore_delete_group(self):
        backend = CacheBackend(app=app)
        group_id = gen_unique_id()
        subtask_ids = [gen_unique_id() for i in range(10)]
        subtasks = map(result.AsyncResult, subtask_ids)
        res = result.GroupResult(group_id, subtasks)
        res.save(backend=backend)
        saved = result.GroupResult.restore(group_id, backend=backend)
        self.assertListEqual(saved.subtasks, subtasks)
        self.assertEqual(saved.id, group_id)
        saved.delete(backend=backend)
        self.assertIsNone(result.GroupResult.restore(group_id,
                                                     backend=backend))

    def test_is_pickled(self):
        cb = CacheBackend(app=app)

        tid2 = gen_unique_id()
        result = {'foo': 'baz', 'bar': SomeClass(12345)}
        cb.mark_as_done(tid2, result)
        # is serialized properly.
        rindb = cb.get_result(tid2)
        self.assertEqual(rindb.get('foo'), 'baz')
        self.assertEqual(rindb.get('bar').data, 12345)

    def test_mark_as_failure(self):
        cb = CacheBackend(app=app)

        einfo = None
        tid3 = gen_unique_id()
        try:
            raise KeyError('foo')
        except KeyError as exception:
            einfo = ExceptionInfo(sys.exc_info())
            pass
        cb.mark_as_failure(tid3, exception, traceback=einfo.traceback)
        self.assertEqual(cb.get_status(tid3), states.FAILURE)
        self.assertIsInstance(cb.get_result(tid3), KeyError)
        self.assertEqual(cb.get_traceback(tid3), einfo.traceback)

    def test_process_cleanup(self):
        cb = CacheBackend(app=app)
        cb.process_cleanup()

    def test_set_expires(self):
        cb1 = CacheBackend(app=app, expires=timedelta(seconds=16))
        self.assertEqual(cb1.expires, 16)
        cb2 = CacheBackend(app=app, expires=32)
        self.assertEqual(cb2.expires, 32)


class test_custom_CacheBackend(unittest.TestCase):

    def test_custom_cache_backend(self):
        from celery import current_app
        prev_backend = current_app.conf.CELERY_CACHE_BACKEND
        prev_module = sys.modules['djcelery.backends.cache']

        if django.VERSION >= (1, 3):
            current_app.conf.CELERY_CACHE_BACKEND = \
                'django.core.cache.backends.dummy.DummyCache'
        else:
            # Django 1.2 used 'scheme://' style cache backends
            current_app.conf.CELERY_CACHE_BACKEND = 'dummy://'
        sys.modules.pop('djcelery.backends.cache')
        try:
            from djcelery.backends.cache import cache
            from django.core.cache import cache as django_cache
            self.assertEqual(cache.__class__.__module__,
                             'django.core.cache.backends.dummy')
            self.assertIsNot(cache, django_cache)
        finally:
            current_app.conf.CELERY_CACHE_BACKEND = prev_backend
            sys.modules['djcelery.backends.cache'] = prev_module


class test_MemcacheWrapper(unittest.TestCase):

    def test_memcache_wrapper(self):

        try:
            from django.core.cache.backends import memcached
            from django.core.cache.backends import locmem
        except InvalidCacheBackendError:
            sys.stderr.write(
                '\n* Memcache library is not installed. Skipping test.\n')
            return
        try:
            prev_cache_cls = memcached.CacheClass
            memcached.CacheClass = locmem.CacheClass
        except AttributeError:
            return
        prev_backend_module = sys.modules.pop('djcelery.backends.cache')
        try:
            from djcelery.backends.cache import cache
            key = 'cu.test_memcache_wrapper'
            val = 'The quick brown fox.'
            default = 'The lazy dog.'

            self.assertEqual(cache.get(key, default=default), default)
            cache.set(key, val)
            self.assertEqual(cache.get(key, default=default), val)
        finally:
            memcached.CacheClass = prev_cache_cls
            sys.modules['djcelery.backends.cache'] = prev_backend_module

########NEW FILE########
__FILENAME__ = test_database
from __future__ import absolute_import, unicode_literals

import celery

from datetime import timedelta

from celery import current_app
from celery import states
from celery.result import AsyncResult
from celery.task import PeriodicTask
from celery.utils import gen_unique_id

from djcelery.app import app
from djcelery.backends.database import DatabaseBackend
from djcelery.utils import now
from djcelery.tests.utils import unittest


class SomeClass(object):

    def __init__(self, data):
        self.data = data


class MyPeriodicTask(PeriodicTask):
    name = 'c.u.my-periodic-task-244'
    run_every = timedelta(seconds=1)

    def run(self, **kwargs):
        return 42


class TestDatabaseBackend(unittest.TestCase):

    def test_backend(self):
        b = DatabaseBackend(app=app)
        tid = gen_unique_id()

        self.assertEqual(b.get_status(tid), states.PENDING)
        self.assertIsNone(b.get_result(tid))

        b.mark_as_done(tid, 42)
        self.assertEqual(b.get_status(tid), states.SUCCESS)
        self.assertEqual(b.get_result(tid), 42)

        tid2 = gen_unique_id()
        result = {'foo': 'baz', 'bar': SomeClass(12345)}
        b.mark_as_done(tid2, result)
        # is serialized properly.
        rindb = b.get_result(tid2)
        self.assertEqual(rindb.get('foo'), 'baz')
        self.assertEqual(rindb.get('bar').data, 12345)

        tid3 = gen_unique_id()
        try:
            raise KeyError('foo')
        except KeyError as exception:
            pass
        b.mark_as_failure(tid3, exception)
        self.assertEqual(b.get_status(tid3), states.FAILURE)
        self.assertIsInstance(b.get_result(tid3), KeyError)

    def test_forget(self):
        b = DatabaseBackend(app=app)
        tid = gen_unique_id()
        b.mark_as_done(tid, {'foo': 'bar'})
        x = AsyncResult(tid)
        self.assertEqual(x.result.get('foo'), 'bar')
        x.forget()
        if celery.VERSION[0:3] == (3, 1, 10):
            # bug in 3.1.10 means result did not clear cache after forget.
            x._cache = None
        self.assertIsNone(x.result)

    def test_group_store(self):
        b = DatabaseBackend(app=app)
        tid = gen_unique_id()

        self.assertIsNone(b.restore_group(tid))

        result = {'foo': 'baz', 'bar': SomeClass(12345)}
        b.save_group(tid, result)
        rindb = b.restore_group(tid)
        self.assertIsNotNone(rindb)
        self.assertEqual(rindb.get('foo'), 'baz')
        self.assertEqual(rindb.get('bar').data, 12345)
        b.delete_group(tid)
        self.assertIsNone(b.restore_group(tid))

    def test_cleanup(self):
        b = DatabaseBackend(app=app)
        b.TaskModel._default_manager.all().delete()
        ids = [gen_unique_id() for _ in xrange(3)]
        for i, res in enumerate((16, 32, 64)):
            b.mark_as_done(ids[i], res)

        self.assertEqual(b.TaskModel._default_manager.count(), 3)

        then = now() - current_app.conf.CELERY_TASK_RESULT_EXPIRES * 2
        # Have to avoid save() because it applies the auto_now=True.
        b.TaskModel._default_manager.filter(task_id__in=ids[:-1]) \
                                    .update(date_done=then)

        b.cleanup()
        self.assertEqual(b.TaskModel._default_manager.count(), 1)

########NEW FILE########
__FILENAME__ = test_discovery
from __future__ import absolute_import, unicode_literals

import warnings

from django.conf import settings

from celery.registry import tasks

from djcelery.loaders import autodiscover
from djcelery.tests.utils import unittest


class TestDiscovery(unittest.TestCase):

    def assertDiscovery(self):
        apps = autodiscover()
        self.assertTrue(apps)
        self.assertIn('c.unittest.SomeAppTask', tasks)
        self.assertEqual(tasks['c.unittest.SomeAppTask'].run(), 42)

    def test_discovery(self):
        if 'someapp' in settings.INSTALLED_APPS:
            self.assertDiscovery()

    def test_discovery_with_broken(self):
        warnings.resetwarnings()
        if 'someapp' in settings.INSTALLED_APPS:
            installed_apps = list(settings.INSTALLED_APPS)
            settings.INSTALLED_APPS = installed_apps + ['xxxnot.aexist']
            try:
                with warnings.catch_warnings(record=True) as log:
                    autodiscover()
                    self.assertTrue(log)
            finally:
                settings.INSTALLED_APPS = installed_apps

########NEW FILE########
__FILENAME__ = test_loaders
from __future__ import absolute_import, unicode_literals

from celery import loaders

from djcelery import loaders as djloaders
from djcelery.app import app
from djcelery.tests.utils import unittest


class TestDjangoLoader(unittest.TestCase):

    def setUp(self):
        self.loader = djloaders.DjangoLoader(app=app)

    def test_get_loader_cls(self):

        self.assertEqual(loaders.get_loader_cls('django'),
                         self.loader.__class__)
        # Execute cached branch.
        self.assertEqual(loaders.get_loader_cls('django'),
                         self.loader.__class__)

    def test_on_worker_init(self):
        from django.conf import settings
        old_imports = getattr(settings, 'CELERY_IMPORTS', ())
        settings.CELERY_IMPORTS = ('xxx.does.not.exist', )
        try:
            self.assertRaises(ImportError, self.loader.import_default_modules)
        finally:
            settings.CELERY_IMPORTS = old_imports

    def test_race_protection(self):
        djloaders._RACE_PROTECTION = True
        try:
            self.assertFalse(self.loader.on_worker_init())
        finally:
            djloaders._RACE_PROTECTION = False

    def test_find_related_module_no_path(self):
        self.assertFalse(djloaders.find_related_module('sys', 'tasks'))

    def test_find_related_module_no_related(self):
        self.assertFalse(
            djloaders.find_related_module('someapp', 'frobulators'),
        )

########NEW FILE########
__FILENAME__ = test_models
from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

from celery import states
from celery.utils import gen_unique_id

from djcelery import celery
from djcelery.models import TaskMeta, TaskSetMeta
from djcelery.utils import now
from djcelery.tests.utils import unittest


class TestModels(unittest.TestCase):

    def createTaskMeta(self):
        id = gen_unique_id()
        taskmeta, created = TaskMeta.objects.get_or_create(task_id=id)
        return taskmeta

    def createTaskSetMeta(self):
        id = gen_unique_id()
        tasksetmeta, created = TaskSetMeta.objects.get_or_create(taskset_id=id)
        return tasksetmeta

    def test_taskmeta(self):
        m1 = self.createTaskMeta()
        m2 = self.createTaskMeta()
        m3 = self.createTaskMeta()
        self.assertTrue(unicode(m1).startswith('<Task:'))
        self.assertTrue(m1.task_id)
        self.assertIsInstance(m1.date_done, datetime)

        self.assertEqual(
            TaskMeta.objects.get_task(m1.task_id).task_id,
            m1.task_id,
        )
        self.assertNotEqual(TaskMeta.objects.get_task(m1.task_id).status,
                            states.SUCCESS)
        TaskMeta.objects.store_result(m1.task_id, True, status=states.SUCCESS)
        TaskMeta.objects.store_result(m2.task_id, True, status=states.SUCCESS)
        self.assertEqual(TaskMeta.objects.get_task(m1.task_id).status,
                         states.SUCCESS)
        self.assertEqual(TaskMeta.objects.get_task(m2.task_id).status,
                         states.SUCCESS)

        # Have to avoid save() because it applies the auto_now=True.
        TaskMeta.objects.filter(
            task_id=m1.task_id
        ).update(date_done=now() - timedelta(days=10))

        expired = TaskMeta.objects.get_all_expired(
            celery.conf.CELERY_TASK_RESULT_EXPIRES,
        )
        self.assertIn(m1, expired)
        self.assertNotIn(m2, expired)
        self.assertNotIn(m3, expired)

        TaskMeta.objects.delete_expired(
            celery.conf.CELERY_TASK_RESULT_EXPIRES,
        )
        self.assertNotIn(m1, TaskMeta.objects.all())

    def test_tasksetmeta(self):
        m1 = self.createTaskSetMeta()
        m2 = self.createTaskSetMeta()
        m3 = self.createTaskSetMeta()
        self.assertTrue(unicode(m1).startswith('<TaskSet:'))
        self.assertTrue(m1.taskset_id)
        self.assertIsInstance(m1.date_done, datetime)

        self.assertEqual(
            TaskSetMeta.objects.restore_taskset(m1.taskset_id).taskset_id,
            m1.taskset_id,
        )

        # Have to avoid save() because it applies the auto_now=True.
        TaskSetMeta.objects.filter(
            taskset_id=m1.taskset_id,
        ).update(date_done=now() - timedelta(days=10))

        expired = TaskSetMeta.objects.get_all_expired(
            celery.conf.CELERY_TASK_RESULT_EXPIRES,
        )
        self.assertIn(m1, expired)
        self.assertNotIn(m2, expired)
        self.assertNotIn(m3, expired)

        TaskSetMeta.objects.delete_expired(
            celery.conf.CELERY_TASK_RESULT_EXPIRES,
        )
        self.assertNotIn(m1, TaskSetMeta.objects.all())

        m4 = self.createTaskSetMeta()
        self.assertEqual(
            TaskSetMeta.objects.restore_taskset(m4.taskset_id).taskset_id,
            m4.taskset_id,
        )

        TaskSetMeta.objects.delete_taskset(m4.taskset_id)
        self.assertIsNone(TaskSetMeta.objects.restore_taskset(m4.taskset_id))

########NEW FILE########
__FILENAME__ = test_schedulers
from __future__ import absolute_import

from datetime import datetime, timedelta
from itertools import count

from celery.five import monotonic
from celery.schedules import schedule, crontab
from celery.utils.timeutils import timedelta_seconds

from djcelery import schedulers
from djcelery import celery
from djcelery.app import app
from djcelery.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from djcelery.models import PeriodicTasks
from djcelery.tests.utils import unittest


def create_model_interval(schedule, **kwargs):
    return create_model(interval=IntervalSchedule.from_schedule(schedule),
                        **kwargs)


def create_model_crontab(schedule, **kwargs):
    return create_model(crontab=CrontabSchedule.from_schedule(schedule),
                        **kwargs)

_next_id = count(0).next


def create_model(Model=PeriodicTask, **kwargs):
    entry = dict(name='thefoo{0}'.format(_next_id()),
                 task='djcelery.unittest.add{0}'.format(_next_id()),
                 args='[2, 2]',
                 kwargs='{"callback": "foo"}',
                 queue='xaz',
                 routing_key='cpu',
                 exchange='foo')
    return Model(**dict(entry, **kwargs))


class EntryTrackSave(schedulers.ModelEntry):

    def __init__(self, *args, **kwargs):
        self.saved = 0
        super(EntryTrackSave, self).__init__(*args, **kwargs)

    def save(self):
        self.saved += 1
        super(EntryTrackSave, self).save()


class EntrySaveRaises(schedulers.ModelEntry):

    def save(self):
        raise RuntimeError('this is expected')


class TrackingScheduler(schedulers.DatabaseScheduler):
    Entry = EntryTrackSave

    def __init__(self, *args, **kwargs):
        self.flushed = 0
        schedulers.DatabaseScheduler.__init__(self, *args, **kwargs)

    def sync(self):
        self.flushed += 1
        schedulers.DatabaseScheduler.sync(self)


class test_ModelEntry(unittest.TestCase):
    Entry = EntryTrackSave

    def tearDown(self):
        PeriodicTask.objects.all().delete()

    def test_entry(self):
        m = create_model_interval(schedule(timedelta(seconds=10)))
        e = self.Entry(m)

        self.assertListEqual(e.args, [2, 2])
        self.assertDictEqual(e.kwargs, {'callback': 'foo'})
        self.assertTrue(e.schedule)
        self.assertEqual(e.total_run_count, 0)
        self.assertIsInstance(e.last_run_at, datetime)
        self.assertDictContainsSubset({'queue': 'xaz',
                                       'exchange': 'foo',
                                       'routing_key': 'cpu'}, e.options)

        right_now = celery.now()
        m2 = create_model_interval(schedule(timedelta(seconds=10)),
                                   last_run_at=right_now)
        self.assertTrue(m2.last_run_at)
        e2 = self.Entry(m2)
        self.assertIs(e2.last_run_at, right_now)

        e3 = e2.next()
        self.assertGreater(e3.last_run_at, e2.last_run_at)
        self.assertEqual(e3.total_run_count, 1)


class test_DatabaseScheduler(unittest.TestCase):
    Scheduler = TrackingScheduler

    def setUp(self):
        PeriodicTask.objects.all().delete()
        self.prev_schedule = celery.conf.CELERYBEAT_SCHEDULE
        celery.conf.CELERYBEAT_SCHEDULE = {}
        m1 = create_model_interval(schedule(timedelta(seconds=10)))
        m2 = create_model_interval(schedule(timedelta(minutes=20)))
        m3 = create_model_crontab(crontab(minute='2,4,5'))
        for obj in m1, m2, m3:
            obj.save()
        self.s = self.Scheduler(app=app)
        self.m1 = PeriodicTask.objects.get(name=m1.name)
        self.m2 = PeriodicTask.objects.get(name=m2.name)
        self.m3 = PeriodicTask.objects.get(name=m3.name)

    def tearDown(self):
        celery.conf.CELERYBEAT_SCHEDULE = self.prev_schedule
        PeriodicTask.objects.all().delete()

    def test_constructor(self):
        self.assertIsInstance(self.s._dirty, set)
        self.assertIsNone(self.s._last_sync)
        self.assertTrue(self.s.sync_every)

    def test_all_as_schedule(self):
        sched = self.s.schedule
        self.assertTrue(sched)
        self.assertEqual(len(sched), 4)
        self.assertIn('celery.backend_cleanup', sched)
        for n, e in sched.items():
            self.assertIsInstance(e, self.s.Entry)

    def test_schedule_changed(self):
        self.m2.args = '[16, 16]'
        self.m2.save()
        e2 = self.s.schedule[self.m2.name]
        self.assertListEqual(e2.args, [16, 16])

        self.m1.args = '[32, 32]'
        self.m1.save()
        e1 = self.s.schedule[self.m1.name]
        self.assertListEqual(e1.args, [32, 32])
        e1 = self.s.schedule[self.m1.name]
        self.assertListEqual(e1.args, [32, 32])

        self.m3.delete()
        self.assertRaises(KeyError, self.s.schedule.__getitem__, self.m3.name)

    def test_should_sync(self):
        self.assertTrue(self.s.should_sync())
        self.s._last_sync = monotonic()
        self.assertFalse(self.s.should_sync())
        self.s._last_sync -= self.s.sync_every
        self.assertTrue(self.s.should_sync())

    def test_reserve(self):
        e1 = self.s.schedule[self.m1.name]
        self.s.schedule[self.m1.name] = self.s.reserve(e1)
        self.assertEqual(self.s.flushed, 1)

        e2 = self.s.schedule[self.m2.name]
        self.s.schedule[self.m2.name] = self.s.reserve(e2)
        self.assertEqual(self.s.flushed, 1)
        self.assertIn(self.m2.name, self.s._dirty)

    def test_sync_saves_last_run_at(self):
        e1 = self.s.schedule[self.m2.name]
        last_run = e1.last_run_at
        last_run2 = last_run - timedelta(days=1)
        e1.model.last_run_at = last_run2
        self.s._dirty.add(self.m2.name)
        self.s.sync()

        e2 = self.s.schedule[self.m2.name]
        self.assertEqual(e2.last_run_at, last_run2)

    def test_sync_syncs_before_save(self):
        # Get the entry for m2
        e1 = self.s.schedule[self.m2.name]

        # Increment the entry (but make sure it doesn't sync)
        self.s._last_sync = monotonic()
        e2 = self.s.schedule[e1.name] = self.s.reserve(e1)
        self.assertEqual(self.s.flushed, 1)

        # Fetch the raw object from db, change the args
        # and save the changes.
        m2 = PeriodicTask.objects.get(pk=self.m2.pk)
        m2.args = '[16, 16]'
        m2.save()

        # get_schedule should now see the schedule has changed.
        # and also sync the dirty objects.
        e3 = self.s.schedule[self.m2.name]
        self.assertEqual(self.s.flushed, 2)
        self.assertEqual(e3.last_run_at, e2.last_run_at)
        self.assertListEqual(e3.args, [16, 16])

    def test_sync_not_dirty(self):
        self.s._dirty.clear()
        self.s.sync()

    def test_sync_object_gone(self):
        self.s._dirty.add('does-not-exist')
        self.s.sync()

    def test_sync_rollback_on_save_error(self):
        self.s.schedule[self.m1.name] = EntrySaveRaises(self.m1)
        self.s._dirty.add(self.m1.name)
        self.assertRaises(RuntimeError, self.s.sync)


class test_models(unittest.TestCase):

    def test_IntervalSchedule_unicode(self):
        self.assertEqual(unicode(IntervalSchedule(every=1, period='seconds')),
                         'every second')
        self.assertEqual(unicode(IntervalSchedule(every=10, period='seconds')),
                         'every 10 seconds')

    def test_CrontabSchedule_unicode(self):
        self.assertEqual(unicode(CrontabSchedule(minute=3,
                                                 hour=3,
                                                 day_of_week=None)),
                         '3 3 * * * (m/h/d/dM/MY)')
        self.assertEqual(unicode(CrontabSchedule(minute=3,
                                                 hour=3,
                                                 day_of_week='tue',
                                                 day_of_month='*/2',
                                                 month_of_year='4,6')),
                         '3 3 tue */2 4,6 (m/h/d/dM/MY)')

    def test_PeriodicTask_unicode_interval(self):
        p = create_model_interval(schedule(timedelta(seconds=10)))
        self.assertEqual(unicode(p),
                         '{0}: every 10.0 seconds'.format(p.name))

    def test_PeriodicTask_unicode_crontab(self):
        p = create_model_crontab(crontab(hour='4, 5', day_of_week='4, 5'))
        self.assertEqual(unicode(p),
                         '{0}: * 4,5 4,5 * * (m/h/d/dM/MY)'.format(p.name))

    def test_PeriodicTask_schedule_property(self):
        p1 = create_model_interval(schedule(timedelta(seconds=10)))
        s1 = p1.schedule
        self.assertEqual(timedelta_seconds(s1.run_every), 10)

        p2 = create_model_crontab(crontab(hour='4, 5',
                                          minute='10,20,30',
                                          day_of_month='1-7',
                                          month_of_year='*/3'))
        s2 = p2.schedule
        self.assertSetEqual(s2.hour, set([4, 5]))
        self.assertSetEqual(s2.minute, set([10, 20, 30]))
        self.assertSetEqual(s2.day_of_week, set([0, 1, 2, 3, 4, 5, 6]))
        self.assertSetEqual(s2.day_of_month, set([1, 2, 3, 4, 5, 6, 7]))
        self.assertSetEqual(s2.month_of_year, set([1, 4, 7, 10]))

    def test_PeriodicTask_unicode_no_schedule(self):
        p = create_model()
        self.assertEqual(unicode(p), '{0}: {{no schedule}}'.format(p.name))

    def test_CrontabSchedule_schedule(self):
        s = CrontabSchedule(minute='3, 7', hour='3, 4', day_of_week='*',
                            day_of_month='1, 16', month_of_year='1, 7')
        self.assertEqual(s.schedule.minute, set([3, 7]))
        self.assertEqual(s.schedule.hour, set([3, 4]))
        self.assertEqual(s.schedule.day_of_week, set([0, 1, 2, 3, 4, 5, 6]))
        self.assertEqual(s.schedule.day_of_month, set([1, 16]))
        self.assertEqual(s.schedule.month_of_year, set([1, 7]))


class test_model_PeriodicTasks(unittest.TestCase):

    def setUp(self):
        PeriodicTasks.objects.all().delete()

    def test_track_changes(self):
        self.assertIsNone(PeriodicTasks.last_change())
        m1 = create_model_interval(schedule(timedelta(seconds=10)))
        m1.save()
        x = PeriodicTasks.last_change()
        self.assertTrue(x)
        m1.args = '(23, 24)'
        m1.save()
        y = PeriodicTasks.last_change()
        self.assertTrue(y)
        self.assertGreater(y, x)

########NEW FILE########
__FILENAME__ = test_snapshot
from __future__ import absolute_import, unicode_literals

from datetime import datetime
from itertools import count
from time import time

from celery import states
from celery.events import Event as _Event
from celery.events.state import State, Worker, Task
from celery.utils import gen_unique_id

from djcelery import celery
from djcelery import snapshot
from djcelery import models
from djcelery.utils import make_aware
from djcelery.tests.utils import unittest

_next_id = count(0).next
_next_clock = count(1).next


def Event(*args, **kwargs):
    kwargs.setdefault('clock', _next_clock())
    kwargs.setdefault('local_received', time())
    return _Event(*args, **kwargs)


def create_task(worker, **kwargs):
    d = dict(uuid=gen_unique_id(),
             name='djcelery.unittest.task{0}'.format(_next_id()),
             worker=worker)
    return Task(**dict(d, **kwargs))


class test_Camera(unittest.TestCase):
    Camera = snapshot.Camera

    def setUp(self):
        self.state = State()
        self.cam = self.Camera(self.state)

    def test_constructor(self):
        cam = self.Camera(State())
        self.assertTrue(cam.state)
        self.assertTrue(cam.freq)
        self.assertTrue(cam.cleanup_freq)
        self.assertTrue(cam.logger)

    def test_get_heartbeat(self):
        worker = Worker(hostname='fuzzie')
        self.assertIsNone(self.cam.get_heartbeat(worker))
        t1 = time()
        t2 = time()
        t3 = time()
        for t in t1, t2, t3:
            worker.event('heartbeat', t, t, {})
        self.state.workers[worker.hostname] = worker
        self.assertEqual(self.cam.get_heartbeat(worker),
                         make_aware(datetime.fromtimestamp(t3)))

    def test_handle_worker(self):
        worker = Worker(hostname='fuzzie')
        worker.event('online', time(), time(), {})
        self.cam._last_worker_write.clear()
        m = self.cam.handle_worker((worker.hostname, worker))
        self.assertTrue(m)
        self.assertTrue(m.hostname)
        self.assertTrue(m.last_heartbeat)
        self.assertTrue(m.is_alive())
        self.assertEqual(unicode(m), unicode(m.hostname))
        self.assertTrue(repr(m))

    def test_handle_task_received(self):
        worker = Worker(hostname='fuzzie')
        worker.event('oneline', time(), time(), {})
        self.cam.handle_worker((worker.hostname, worker))

        task = create_task(worker)
        task.event('received', time(), time(), {})
        self.assertEqual(task.state, 'RECEIVED')
        mt = self.cam.handle_task((task.uuid, task))
        self.assertEqual(mt.name, task.name)
        self.assertTrue(unicode(mt))
        self.assertTrue(repr(mt))
        mt.eta = celery.now()
        self.assertIn('eta', unicode(mt))
        self.assertIn(mt, models.TaskState.objects.active())

    def test_handle_task(self):
        worker1 = Worker(hostname='fuzzie')
        worker1.event('online', time(), time(), {})
        mw = self.cam.handle_worker((worker1.hostname, worker1))
        task1 = create_task(worker1)
        task1.event('received', time(), time(), {})
        mt = self.cam.handle_task((task1.uuid, task1))
        self.assertEqual(mt.worker, mw)

        worker2 = Worker(hostname=None)
        task2 = create_task(worker2)
        task2.event('received', time(), time(), {})
        mt = self.cam.handle_task((task2.uuid, task2))
        self.assertIsNone(mt.worker)

        task1.event('succeeded', time(), time(), {'result': 42})
        self.assertEqual(task1.state, states.SUCCESS)
        self.assertEqual(task1.result, 42)
        mt = self.cam.handle_task((task1.uuid, task1))
        self.assertEqual(mt.name, task1.name)
        self.assertEqual(mt.result, 42)

        task3 = create_task(worker1, name=None)
        task3.event('revoked', time(), time(), {})
        mt = self.cam.handle_task((task3.uuid, task3))
        self.assertIsNone(mt)

    def assertExpires(self, dec, expired, tasks=10):
        worker = Worker(hostname='fuzzie')
        worker.event('online', time(), time(), {})
        for total in xrange(tasks):
            task = create_task(worker)
            task.event('received', time() - dec, time() - dec, {})
            task.event('succeeded', time() - dec, time() - dec, {'result': 42})
            self.assertTrue(task.name)
            self.assertTrue(self.cam.handle_task((task.uuid, task)))
        self.assertEqual(self.cam.on_cleanup(), expired)

    def test_on_cleanup_expires(self, dec=332000):
        self.assertExpires(dec, 10)

    def test_on_cleanup_does_not_expire_new(self, dec=0):
        self.assertExpires(dec, 0)

    def test_on_shutter(self):
        state = self.state
        cam = self.cam

        ws = ['worker1.ex.com', 'worker2.ex.com', 'worker3.ex.com']
        uus = [gen_unique_id() for i in xrange(50)]

        events = [Event('worker-online', hostname=ws[0]),
                  Event('worker-online', hostname=ws[1]),
                  Event('worker-online', hostname=ws[2]),
                  Event('task-received',
                        uuid=uus[0], name='A', hostname=ws[0]),
                  Event('task-started',
                        uuid=uus[0], name='A', hostname=ws[0]),
                  Event('task-received',
                        uuid=uus[1], name='B', hostname=ws[1]),
                  Event('task-revoked',
                        uuid=uus[2], name='C', hostname=ws[2])]

        for event in events:
            event['local_received'] = time()
            state.event(event)
        cam.on_shutter(state)

        for host in ws:
            worker = models.WorkerState.objects.get(hostname=host)
            self.assertTrue(worker.is_alive())

        t1 = models.TaskState.objects.get(task_id=uus[0])
        self.assertEqual(t1.state, 'STARTED')
        self.assertEqual(t1.name, 'A')
        t2 = models.TaskState.objects.get(task_id=uus[1])
        self.assertEqual(t2.state, 'RECEIVED')
        t3 = models.TaskState.objects.get(task_id=uus[2])
        self.assertEqual(t3.state, 'REVOKED')

        events = [Event('task-succeeded',
                        uuid=uus[0], hostname=ws[0], result=42),
                  Event('task-failed',
                        uuid=uus[1], exception="KeyError('foo')",
                        hostname=ws[1]),
                  Event('worker-offline', hostname=ws[0])]
        map(state.event, events)
        cam._last_worker_write.clear()
        cam.on_shutter(state)

        w1 = models.WorkerState.objects.get(hostname=ws[0])
        self.assertFalse(w1.is_alive())

        t1 = models.TaskState.objects.get(task_id=uus[0])
        self.assertEqual(t1.state, 'SUCCESS')
        self.assertEqual(t1.result, '42')
        self.assertEqual(t1.worker, w1)

        t2 = models.TaskState.objects.get(task_id=uus[1])
        self.assertEqual(t2.state, 'FAILURE')
        self.assertEqual(t2.result, "KeyError('foo')")
        self.assertEqual(t2.worker.hostname, ws[1])

        cam.on_shutter(state)

########NEW FILE########
__FILENAME__ = test_views
from __future__ import absolute_import, unicode_literals

import sys

from functools import partial

from billiard.einfo import ExceptionInfo
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test.testcases import TestCase as DjangoTestCase
from django.template import TemplateDoesNotExist

from anyjson import deserialize

from celery import current_app
from celery import states
from celery.task import task
from celery.utils import gen_unique_id, get_full_cls_name

from djcelery.views import task_webhook
from djcelery.tests.req import MockRequest


def reversestar(name, **kwargs):
    return reverse(name, kwargs=kwargs)


class MyError(Exception):
    # On Py2.4 repr(exc) includes the object id, so comparing
    # texts is pointless when the id the "same" KeyError does not match.

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.args!r}>'.format(self)


class MyRetryTaskError(MyError):
    pass


task_is_successful = partial(reversestar, 'celery-is_task_successful')
task_status = partial(reversestar, 'celery-task_status')
task_apply = partial(reverse, 'celery-apply')
registered_tasks = partial(reverse, 'celery-tasks')
scratch = {}


@task()
def mytask(x, y):
    ret = scratch['result'] = int(x) * int(y)
    return ret


def create_exception(name, base=Exception):
    return type(name, (base, ), {})


def catch_exception(exception):
    try:
        raise exception
    except exception.__class__ as exc:
        exc = current_app.backend.prepare_exception(exc)
        return exc, ExceptionInfo(sys.exc_info()).traceback


class ViewTestCase(DjangoTestCase):

    def assertJSONEqual(self, json, py):
        json = isinstance(json, HttpResponse) and json.content or json
        try:
            self.assertEqual(deserialize(json), py)
        except TypeError as exc:
            raise TypeError('{0}: {1}'.format(exc, json))

    def assertIn(self, expected, source, *args):
        try:
            DjangoTestCase.assertIn(self, expected, source, *args)
        except AttributeError:
            self.assertTrue(expected in source)

    def assertDictContainsSubset(self, a, b, *args):
        try:
            DjangoTestCase.assertDictContainsSubset(self, a, b, *args)
        except AttributeError:
            for key, value in a.items():
                self.assertTrue(key in b)
                self.assertEqual(b[key], value)


class test_task_apply(ViewTestCase):

    def test_apply(self):
        current_app.conf.CELERY_ALWAYS_EAGER = True
        try:
            self.client.get(
                task_apply(kwargs={'task_name': mytask.name}) + '?x=4&y=4',
            )
            self.assertEqual(scratch['result'], 16)
        finally:
            current_app.conf.CELERY_ALWAYS_EAGER = False

    def test_apply_raises_404_on_unregistered_task(self):
        current_app.conf.CELERY_ALWAYS_EAGER = True
        try:
            name = 'xxx.does.not.exist'
            action = partial(
                self.client.get,
                task_apply(kwargs={'task_name': name}) + '?x=4&y=4',
            )
            try:
                res = action()
            except TemplateDoesNotExist:
                pass   # pre Django 1.5
            else:
                self.assertEqual(res.status_code, 404)
        finally:
            current_app.conf.CELERY_ALWAYS_EAGER = False


class test_registered_tasks(ViewTestCase):

    def test_list_registered_tasks(self):
        json = self.client.get(registered_tasks())
        tasks = deserialize(json.content)
        self.assertIn('celery.backend_cleanup', tasks['regular'])


class test_webhook_task(ViewTestCase):

    def test_successful_request(self):

        @task_webhook
        def add_webhook(request):
            x = int(request.GET['x'])
            y = int(request.GET['y'])
            return x + y

        request = MockRequest().get('/tasks/add', dict(x=10, y=10))
        response = add_webhook(request)
        self.assertDictContainsSubset({'status': 'success', 'retval': 20},
                                      deserialize(response.content))

    def test_failed_request(self):

        @task_webhook
        def error_webhook(request):
            x = int(request.GET['x'])
            y = int(request.GET['y'])
            raise MyError(x + y)

        request = MockRequest().get('/tasks/error', dict(x=10, y=10))
        response = error_webhook(request)
        self.assertDictContainsSubset({'status': 'failure',
                                       'reason': '<MyError: (20,)>'},
                                      deserialize(response.content))


class test_task_status(ViewTestCase):

    def assertStatusForIs(self, status, res, traceback=None):
        uuid = gen_unique_id()
        current_app.backend.store_result(uuid, res, status,
                                         traceback=traceback)
        json = self.client.get(task_status(task_id=uuid))
        expect = dict(id=uuid, status=status, result=res)
        if status in current_app.backend.EXCEPTION_STATES:
            instore = current_app.backend.get_result(uuid)
            self.assertEqual(str(instore.args[0]), str(res.args[0]))
            expect['result'] = repr(res)
            expect['exc'] = get_full_cls_name(res.__class__)
            expect['traceback'] = traceback

        self.assertJSONEqual(json, dict(task=expect))

    def test_success(self):
        self.assertStatusForIs(states.SUCCESS, 'The quick brown fox')

    def test_failure(self):
        exc, tb = catch_exception(MyError('foo'))
        self.assertStatusForIs(states.FAILURE, exc, tb)

    def test_retry(self):
        oexc, _ = catch_exception(MyError('Resource not available'))
        exc, tb = catch_exception(MyRetryTaskError(str(oexc), oexc))
        self.assertStatusForIs(states.RETRY, exc, tb)


class test_task_is_successful(ViewTestCase):

    def assertStatusForIs(self, status, outcome):
        uuid = gen_unique_id()
        result = gen_unique_id()
        current_app.backend.store_result(uuid, result, status)
        json = self.client.get(task_is_successful(task_id=uuid))
        self.assertJSONEqual(json, {'task': {'id': uuid,
                                             'executed': outcome}})

    def test_success(self):
        self.assertStatusForIs(states.SUCCESS, True)

    def test_pending(self):
        self.assertStatusForIs(states.PENDING, False)

    def test_failure(self):
        self.assertStatusForIs(states.FAILURE, False)

    def test_retry(self):
        self.assertStatusForIs(states.RETRY, False)

########NEW FILE########
__FILENAME__ = test_worker_job
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.core import cache

from celery.utils import gen_unique_id
from celery.task import task as task_dec

from celery.tests.worker.test_request import jail

from djcelery.app import app
from djcelery.tests.utils import unittest


@task_dec()
def mytask(i):
    return i ** i


@task_dec()
def get_db_connection(i):
    from django.db import connection
    return id(connection)
get_db_connection.ignore_result = True


class TestJail(unittest.TestCase):

    def test_django_db_connection_is_closed(self):
        from django.db import connection
        connection._was_closed = False
        old_connection_close = connection.close

        def monkeypatched_connection_close(*args, **kwargs):
            connection._was_closed = True
            return old_connection_close(*args, **kwargs)

        connection.close = monkeypatched_connection_close
        try:
            jail(app, gen_unique_id(), get_db_connection.name, [2], {})
            self.assertTrue(connection._was_closed)
        finally:
            connection.close = old_connection_close

    def test_django_cache_connection_is_closed(self):
        old_cache_close = getattr(cache.cache, 'close', None)
        cache._was_closed = False
        old_cache_parse_backend = getattr(cache, 'parse_backend_uri', None)
        if old_cache_parse_backend:     # checks to make sure attr exists
            delattr(cache, 'parse_backend_uri')

        def monkeypatched_cache_close(*args, **kwargs):
            cache._was_closed = True

        cache.cache.close = monkeypatched_cache_close

        jail(app, gen_unique_id(), mytask.name, [4], {})
        self.assertTrue(cache._was_closed)
        cache.cache.close = old_cache_close
        if old_cache_parse_backend:
            cache.parse_backend_uri = old_cache_parse_backend

    def test_django_cache_connection_is_closed_django_1_1(self):
        old_cache_close = getattr(cache.cache, 'close', None)
        cache._was_closed = False
        old_cache_parse_backend = getattr(cache, 'parse_backend_uri', None)
        cache.parse_backend_uri = lambda uri: ['libmemcached', '1', '2']

        def monkeypatched_cache_close(*args, **kwargs):
            cache._was_closed = True

        cache.cache.close = monkeypatched_cache_close

        jail(app, gen_unique_id(), mytask.name, [4], {})
        self.assertTrue(cache._was_closed)
        cache.cache.close = old_cache_close
        if old_cache_parse_backend:
            cache.parse_backend_uri = old_cache_parse_backend
        else:
            del(cache.parse_backend_uri)

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import, unicode_literals

try:
    import unittest
    unittest.skip
except AttributeError:
    import unittest2 as unittest  # noqa

########NEW FILE########
__FILENAME__ = urls
"""

URLs defined for celery.

* ``/$task_id/done/``

    URL to :func:`~celery.views.is_successful`.

* ``/$task_id/status/``

    URL  to :func:`~celery.views.task_status`.

"""
from __future__ import absolute_import, unicode_literals

try:
    from django.conf.urls import patterns, url
except ImportError:  # deprecated since Django 1.4
    from django.conf.urls.defaults import patterns, url  # noqa

from . import views

task_pattern = r'(?P<task_id>[\w\d\-\.]+)'

urlpatterns = patterns(
    '',
    url(r'^%s/done/?$' % task_pattern, views.is_task_successful,
        name='celery-is_task_successful'),
    url(r'^%s/status/?$' % task_pattern, views.task_status,
        name='celery-task_status'),
    url(r'^tasks/?$', views.registered_tasks, name='celery-tasks'),
)

########NEW FILE########
__FILENAME__ = utils
# -- XXX This module must not use translation as that causes
# -- a recursive loader import!
from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.conf import settings

# Database-related exceptions.
from django.db import DatabaseError
try:
    import MySQLdb as mysql
    _my_database_errors = (mysql.DatabaseError,
                           mysql.InterfaceError,
                           mysql.OperationalError)
except ImportError:
    _my_database_errors = ()      # noqa
try:
    import psycopg2 as pg
    _pg_database_errors = (pg.DatabaseError,
                           pg.InterfaceError,
                           pg.OperationalError)
except ImportError:
    _pg_database_errors = ()      # noqa
try:
    import sqlite3
    _lite_database_errors = (sqlite3.DatabaseError,
                             sqlite3.InterfaceError,
                             sqlite3.OperationalError)
except ImportError:
    _lite_database_errors = ()    # noqa
try:
    import cx_Oracle as oracle
    _oracle_database_errors = (oracle.DatabaseError,
                               oracle.InterfaceError,
                               oracle.OperationalError)
except ImportError:
    _oracle_database_errors = ()  # noqa

DATABASE_ERRORS = ((DatabaseError, ) +
                   _my_database_errors +
                   _pg_database_errors +
                   _lite_database_errors +
                   _oracle_database_errors)


try:
    from django.utils import timezone
    is_aware = timezone.is_aware

    # see Issue #222
    now_localtime = getattr(timezone, 'template_localtime', timezone.localtime)

    def make_aware(value):
        if getattr(settings, 'USE_TZ', False):
            # naive datetimes are assumed to be in UTC.
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone.utc)
            # then convert to the Django configured timezone.
            default_tz = timezone.get_default_timezone()
            value = timezone.localtime(value, default_tz)
        return value

    def make_naive(value):
        if getattr(settings, 'USE_TZ', False):
            default_tz = timezone.get_default_timezone()
            value = timezone.make_naive(value, default_tz)
        return value

    def now():
        if getattr(settings, 'USE_TZ', False):
            return now_localtime(timezone.now())
        else:
            return timezone.now()

except ImportError:
    now = datetime.now
    make_aware = make_naive = lambda x: x
    is_aware = lambda x: False


def maybe_make_aware(value):
    if isinstance(value, datetime) and is_aware(value):
        return value
    if value:
        return make_aware(value)
    return value


def is_database_scheduler(scheduler):
    if not scheduler:
        return False
    from kombu.utils import symbol_by_name
    from .schedulers import DatabaseScheduler
    return issubclass(symbol_by_name(scheduler), DatabaseScheduler)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import, unicode_literals

from functools import wraps

from django.http import HttpResponse, Http404

from anyjson import serialize

from celery import states
from celery.registry import tasks
from celery.result import AsyncResult
from celery.utils import get_full_cls_name, kwdict
from celery.utils.encoding import safe_repr

# Ensure built-in tasks are loaded for task_list view
import celery.task  # noqa


def JsonResponse(response):
    return HttpResponse(serialize(response), content_type='application/json')


def task_view(task):
    """Decorator turning any task into a view that applies the task
    asynchronously. Keyword arguments (via URLconf, etc.) will
    supercede GET or POST parameters when there are conflicts.

    Returns a JSON dictionary containing the keys ``ok``, and
        ``task_id``.

    """

    def _applier(request, **options):
        kwargs = kwdict(request.method == 'POST' and
                        request.POST or request.GET)
        # no multivalue
        kwargs = dict(((k, v) for k, v in kwargs.iteritems()), **options)
        result = task.apply_async(kwargs=kwargs)
        return JsonResponse({'ok': 'true', 'task_id': result.task_id})

    return _applier


def apply(request, task_name):
    """View applying a task.

    **Note:** Please use this with caution. Preferably you shouldn't make this
        publicly accessible without ensuring your code is safe!

    """
    try:
        task = tasks[task_name]
    except KeyError:
        raise Http404('apply: no such task')
    return task_view(task)(request)


def is_task_successful(request, task_id):
    """Returns task execute status in JSON format."""
    return JsonResponse({'task': {
        'id': task_id,
        'executed': AsyncResult(task_id).successful(),
    }})


def task_status(request, task_id):
    """Returns task status and result in JSON format."""
    result = AsyncResult(task_id)
    state, retval = result.state, result.result
    response_data = dict(id=task_id, status=state, result=retval)
    if state in states.EXCEPTION_STATES:
        traceback = result.traceback
        response_data.update({'result': safe_repr(retval),
                              'exc': get_full_cls_name(retval.__class__),
                              'traceback': traceback})
    return JsonResponse({'task': response_data})


def registered_tasks(request):
    """View returning all defined tasks as a JSON object."""
    return JsonResponse({'regular': tasks.regular().keys(),
                         'periodic': tasks.periodic().keys()})


def task_webhook(fun):
    """Decorator turning a function into a task webhook.

    If an exception is raised within the function, the decorated
    function catches this and returns an error JSON response, otherwise
    it returns the result as a JSON response.


    Example:

    .. code-block:: python

        @task_webhook
        def add(request):
            x = int(request.GET['x'])
            y = int(request.GET['y'])
            return x + y

        def view(request):
            response = add(request)
            print(response.content)

    Gives::

        "{'status': 'success', 'retval': 100}"

    """

    @wraps(fun)
    def _inner(*args, **kwargs):
        try:
            retval = fun(*args, **kwargs)
        except Exception as exc:
            response = {'status': 'failure', 'reason': safe_repr(exc)}
        else:
            response = {'status': 'success', 'retval': retval}

        return JsonResponse(response)

    return _inner

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.insert(0, os.getcwd())
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
if django.VERSION < (1, 4):
    from django.core.management import setup_environ
    setup_environ(__import__(os.environ['DJANGO_SETTINGS_MODULE']))
import djcelery

# General configuration
# ---------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinxcontrib.issuetracker',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-celery'
copyright = u'2009-2011, Ask Solem'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(map(str, djcelery.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = djcelery.__version__

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
    ('index', 'django-celery.tex',
     u'django-celery Documentation',
     u'Ask Solem', 'manual'),
]

html_theme = 'celery'
html_theme_path = ['_theme']
html_sidebars = {
    'index': ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**': ['sidebarlogo.html', 'localtoc.html', 'relations.html',
           'sourcelink.html', 'searchbox.html'],
}

### Issuetracker
issuetracker = 'github'
issuetracker_project = 'celery/django-celery'
issuetracker_issue_pattern = r'[Ii]ssue #(\d+)'

########NEW FILE########
__FILENAME__ = settings
# Django settings for docs project.

# import source code dir
import os
import sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))

SITE_ID = 303
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {"default": {"NAME": ":memory:",
                         "ENGINE": "django.db.backends.sqlite3",
                         "USER": '',
                         "PASSWORD": '',
                         "PORT": ''}}


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'djcelery',
)

SECRET_KEY='a'

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = ('./index.txt', )


def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')


def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()


def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]


def fixliterals(fname):
    data = open(fname).read()

    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})

    for m in refre.finditer(data):

        new.append(data[last:m.start()])
        last = m.end()

        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)

        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue

        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue

        sys.stdout.write("\n" + "-" * 80 + "\n")
        sys.stdout.write(data[prev_start + 1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")

        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None

        if replace_type == "":
            new.append(m.group(0))
            continue

        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue

        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") +
            default +
            colorize("]: ", fg="yellow"),
        ).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print

########NEW FILE########
__FILENAME__ = sphinx-to-rst
#!/usr/bin/even/python
import os
import re
import sys

dirname = ""

RE_CODE_BLOCK = re.compile(r'.. code-block:: (.+?)\s*$')
RE_INCLUDE = re.compile(r'.. include:: (.+?)\s*$')
RE_REFERENCE = re.compile(r':(.+?):`(.+?)`')


def include_file(lines, pos, match):
    global dirname
    orig_filename = match.groups()[0]
    filename = os.path.join(dirname, orig_filename)
    fh = open(filename)
    try:
        old_dirname = dirname
        dirname = os.path.dirname(orig_filename)
        try:
            lines[pos] = sphinx_to_rst(fh)
        finally:
            dirname = old_dirname
    finally:
        fh.close()


def replace_code_block(lines, pos, match):
    lines[pos] = ""
    curpos = pos - 1
    # Find the first previous line with text to append "::" to it.
    while True:
        prev_line = lines[curpos]
        if not prev_line.isspace():
            prev_line_with_text = curpos
            break
        curpos -= 1

    if lines[prev_line_with_text].endswith(":"):
        lines[prev_line_with_text] += ":"
    else:
        lines[prev_line_with_text] += "::"

TO_RST_MAP = {RE_CODE_BLOCK: replace_code_block,
              RE_REFERENCE: r'``\2``',
              RE_INCLUDE: include_file}


def _process(lines):
    lines = list(lines)     # non-destructive
    for i, line in enumerate(lines):
        for regex, alt in TO_RST_MAP.items():
            if callable(alt):
                match = regex.match(line)
                if match:
                    alt(lines, i, match)
                    line = lines[i]
            else:
                lines[i] = regex.sub(alt, line)
    return lines


def sphinx_to_rst(fh):
    return "".join(_process(fh))


if __name__ == "__main__":
    dirname = os.path.dirname(sys.argv[1])
    fh = open(sys.argv[1])
    try:
        print(sphinx_to_rst(fh))
    finally:
        fh.close()

########NEW FILE########
__FILENAME__ = pavement
import os
import sys

from paver.easy import path, sh, needs, task, options, Bunch, cmdopts

PYCOMPILE_CACHES = ['*.pyc', '*$py.class']

options(
    sphinx=Bunch(builddir='.build'),
)


def sphinx_builddir(options):
    return path('docs') / options.sphinx.builddir / 'html'


@task
def clean_docs(options):
    sphinx_builddir(options).rmtree()


@task
@needs('clean_docs', 'paver.doctools.html')
def html(options):
    destdir = path('Documentation')
    destdir.rmtree()
    builtdocs = sphinx_builddir(options)
    builtdocs.move(destdir)


@task
@needs('paver.doctools.html')
def qhtml(options):
    destdir = path('Documentation')
    builtdocs = sphinx_builddir(options)
    sh('rsync -az %s/ %s' % (builtdocs, destdir))


@task
@needs('clean_docs', 'paver.doctools.html')
def ghdocs(options):
    builtdocs = sphinx_builddir(options)
    sh('git checkout gh-pages && \
            cp -r %s/* .    && \
            git commit . -m "Rendered documentation for Github Pages." && \
            git push origin gh-pages && \
            git checkout master' % builtdocs)


@task
@needs('clean_docs', 'paver.doctools.html')
def upload_pypi_docs(options):
    builtdocs = path('docs') / options.builddir / 'html'
    sh('%s setup.py upload_sphinx --upload-dir="%s"' % (
        sys.executable, builtdocs))


@task
@needs('upload_pypi_docs', 'ghdocs')
def upload_docs(options):
    pass


@task
def autodoc(options):
    sh('extra/release/doc4allmods djcelery')


@task
def verifyindex(options):
    sh('extra/release/verify-reference-index.sh')


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def flake8(options):
    noerror = getattr(options, 'noerror', False)
    complexity = getattr(options, 'complexity', 22)
    migrations_path = os.path.join('djcelery', 'migrations', '0.+?\.py')
    sh("""flake8 djcelery | perl -mstrict -mwarnings -nle'
        my $ignore = (m/too complex \((\d+)\)/ && $1 le %s)
                   || (m{^%s});
        if (! $ignore) { print STDERR; our $FOUND_FLAKE = 1 }
        }{exit $FOUND_FLAKE;
        '""" % (complexity, migrations_path), ignore_error=noerror)


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def flakeplus(options):
    noerror = getattr(options, 'noerror', False)
    sh('flakeplus --2.6 djcelery', ignore_error=noerror)


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors')
])
def flakes(options):
    flake8(options)
    flakeplus(options)


@task
def clean_readme(options):
    path('README').unlink_p()
    path('README.rst').unlink_p()


@task
@needs('clean_readme')
def readme(options):
    sh('%s extra/release/sphinx-to-rst.py docs/introduction.rst \
            > README.rst' % (sys.executable, ))
    sh('ln -sf README.rst README')


@task
def bump(options):
    sh('bump -c djcelery')


@task
@cmdopts([
    ('coverage', 'c', 'Enable coverage'),
    ('quick', 'q', 'Quick test'),
    ('verbose', 'V', 'Make more noise'),
])
def test(options):
    sh('%s setup.py test' % (sys.executable, ))


@task
@cmdopts([
    ('noerror', 'E', 'Ignore errors'),
])
def pep8(options):
    noerror = getattr(options, 'noerror', False)
    return sh("""find . -name "*.py" | xargs pep8 | perl -nle'\
            print; $a=1 if $_}{exit($a)'""", ignore_error=noerror)


@task
def removepyc(options):
    sh('find . -type f -a \\( %s \\) | xargs rm' % (
        ' -o '.join('-name "%s"' % (pat, ) for pat in PYCOMPILE_CACHES), ))
    sh('find . -type d -name "__pycache__" | xargs rm -r')


@task
@needs('removepyc')
def gitclean(options):
    sh('git clean -xdn')


@task
@needs('removepyc')
def gitcleanforce(options):
    sh('git clean -xdf')


@task
@needs('flakes', 'autodoc', 'verifyindex', 'test', 'gitclean')
def releaseok(options):
    pass


@task
@needs('releaseok', 'removepyc', 'upload_docs')
def release(options):
    pass


@task
def testloc(options):
    sh('sloccount djcelery/tests')


@task
def loc(options):
    sh('sloccount djcelery')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproj project.

import warnings
warnings.filterwarnings(
    'error', r'DateTimeField received a naive datetime',
    RuntimeWarning, r'django\.db\.models\.fields')

import os
import sys
# import source code dir
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))

import djcelery
djcelery.setup_loader()

NO_NOSE = os.environ.get('DJCELERY_NO_NOSE', False)

SITE_ID = 300

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'tests.urls'
SECRET_KEY = 'skskqlqlaskdsd'

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

AUTOCOMMIT = True

if not NO_NOSE:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
here = os.path.abspath(os.path.dirname(__file__))
COVERAGE_EXCLUDE_MODULES = (
    'djcelery',
    'djcelery.tests.*',
    'djcelery.management.*',
    'djcelery.contrib.*',
)

NOSE_ARGS = [
    os.path.join(here, os.pardir, 'djcelery', 'tests'),
    os.environ.get('NOSE_VERBOSE') and '--verbose' or '',
    '--cover3-package=djcelery',
    '--cover3-branch',
    '--cover3-exclude=%s' % ','.join(COVERAGE_EXCLUDE_MODULES),
]

BROKER_URL = 'amqp://'

TT_HOST = 'localhost'
TT_PORT = 1978

CELERY_DEFAULT_EXCHANGE = 'testcelery'
CELERY_DEFAULT_ROUTING_KEY = 'testcelery'
CELERY_DEFAULT_QUEUE = 'testcelery'

CELERY_QUEUES = {'testcelery': {'binding_key': 'testcelery'}}

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'djcelery-test-db',
        'ENGINE': 'django.db.backends.sqlite3',
        'USER': '',
        'PASSWORD': '',
        'PORT': '',
    },
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'djcelery',
    'someapp',
    'someappwotask',
)

if not NO_NOSE:
    INSTALLED_APPS = INSTALLED_APPS + ('django_nose', )

CELERY_SEND_TASK_ERROR_EMAILS = False

USE_TZ = True
TIME_ZONE = 'UTC'

########NEW FILE########
__FILENAME__ = models
from django.db import models  # noqa


class Thing(models.Model):
    name = models.CharField(max_length=10)

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task

from django.db.models import get_model


@task(name='c.unittest.SomeAppTask')
def SomeAppTask(**kwargs):
    return 42


@task(name='c.unittest.SomeModelTask')
def SomeModelTask(pk):
    model = get_model('someapp', 'Thing')
    thing = model.objects.get(pk=pk)
    return thing.name

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from django.test.testcases import TestCase as DjangoTestCase

from someapp.models import Thing
from someapp.tasks import SomeModelTask


class SimpleTest(DjangoTestCase):

    def setUp(self):
        self.thing = Thing.objects.create(name=u'Foo')

    def test_apply_task(self):
        """Apply task function."""
        result = SomeModelTask.apply(kwargs={'pk': self.thing.pk})
        self.assertEqual(result.get(), self.thing.name)

    def test_task_function(self):
        """Run task function."""
        result = SomeModelTask(pk=self.thing.pk)
        self.assertEqual(result, self.thing.name)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models  # noqa

# Create your models here.

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import (patterns, include, url,
                                  handler500, handler404)
except ImportError:
    from django.conf.urls.defaults import (patterns, include, url,  # noqa
                                  handler500, handler404)
from djcelery.views import apply

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns(
    '',
    # Example:
    # (r'^tests/', include('tests.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
    url(r'^apply/(?P<task_name>.+?)/', apply, name='celery-apply'),
    url(r'^celery/', include('djcelery.urls')),

)

########NEW FILE########
