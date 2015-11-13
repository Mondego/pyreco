__FILENAME__ = env
# -*- coding: utf-8 -*-

"""Boilerplate to run ``alembic`` in online mode, using the ``DATABASE_URL``
  environment variable to connect to the right database.
"""

import os

from alembic import context
from sqlalchemy import create_engine
from torque.model import Base

# Get a database connection.
engine = create_engine(os.environ['DATABASE_URL'])
connection = engine.connect()

# Configure the alembic environment context.
context.configure(connection=connection, target_metadata=Base.metadata)

# Run the migrations.
try:
    with context.begin_transaction():
        context.run_migrations()
finally:
    connection.close()


########NEW FILE########
__FILENAME__ = create_application
# -*- coding: utf-8 -*-

"""Create an application, with random API key."""

import argparse
import os
import transaction

from torque.model import CreateApplication
from torque.model import GetActiveKey

from torque.work.main import Bootstrap

def parse_args():
    """Parse the command line arguments."""
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--name')
    args = parser.parse_args()
    if not args.name:
        raise ValueError(parser.format_help())
    return args

def main():
    """Main entry point."""
    
    # Bootstrap the pyramid environment.
    bootstrapper = Bootstrap()
    config = bootstrapper()
    config.commit()
    
    # Parse the command line args.
    args = parse_args()
    name = args.name
    
    # Create the app.
    create_app = CreateApplication()
    get_key = GetActiveKey()
    with transaction.manager:
        app = create_app(name)
        api_key = get_key(app).value
    
    print u'Created application with API key: {0}\n'.format(api_key)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = 4ae58a31c179_
"""Initial migration.
  
  Revision ID: 4ae58a31c179
  Revises: None
  Create Date: 2014-01-30 14:33:48.166748
"""

# Revision identifiers, used by Alembic.
revision = '4ae58a31c179'
down_revision = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('c', sa.DateTime(), nullable=False),
        sa.Column('m', sa.DateTime(), nullable=False),
        sa.Column('v', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('activated', sa.DateTime(), nullable=True),
        sa.Column('deactivated', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.DateTime(), nullable=True),
        sa.Column('undeleted', sa.DateTime(), nullable=True),
        sa.Column('name', sa.Unicode(length=96), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('c', sa.DateTime(), nullable=False),
        sa.Column('m', sa.DateTime(), nullable=False),
        sa.Column('v', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('timeout', sa.Integer(), nullable=False),
        sa.Column('due', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum(u'FAILED', u'COMPLETED', u'PENDING', name='task_statuses'), nullable=False),
        sa.Column('url', sa.Unicode(length=256), nullable=False),
        sa.Column('charset', sa.Unicode(length=24), nullable=False),
        sa.Column('enctype', sa.Unicode(length=256), nullable=False),
        sa.Column('headers', sa.UnicodeText(), nullable=True),
        sa.Column('body', sa.UnicodeText(), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('c', sa.DateTime(), nullable=False),
        sa.Column('m', sa.DateTime(), nullable=False),
        sa.Column('v', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('activated', sa.DateTime(), nullable=True),
        sa.Column('deactivated', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.DateTime(), nullable=True),
        sa.Column('undeleted', sa.DateTime(), nullable=True),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Unicode(length=40), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('value')
    )

def downgrade():
    op.drop_table('api_keys')
    op.drop_table('tasks')
    op.drop_table('applications')


########NEW FILE########
__FILENAME__ = gunicorn
# -*- coding: utf-8 -*-

"""Gunicorn configuration."""

import logging
import sys

import os
import signal

from pyramid.settings import asbool

def _post_fork(server, worker):
    import psycogreen.gevent
    psycogreen.gevent.patch_psycopg()

def _on_starting(server):
    import gevent.monkey
    gevent.monkey.patch_socket()

def _when_ready(server):
    def monitor():
        modify_times = {}
        while True:
            for module in sys.modules.values():
                path = getattr(module, "__file__", None)
                if not path: continue
                if path.endswith(".pyc") or path.endswith(".pyo"):
                    path = path[:-1]
                try:
                    modified = os.stat(path).st_mtime
                except:
                    continue
                if path not in modify_times:
                    modify_times[path] = modified
                    continue
                if modify_times[path] != modified:
                    logging.info("%s modified; restarting server", path)
                    os.kill(os.getpid(), signal.SIGHUP)
                    modify_times = {}
                    break
            gevent.sleep(0.5)
    
    import gevent
    gevent.spawn(monitor)


backlog = int(os.environ.get('GUNICORN_BACKLOG', 64))
bind = '0.0.0.0:{0}'.format(os.environ.get('PORT', 5100))
daemon = asbool(os.environ.get('GUNICORN_DAEMON', False))
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 24000))
mode = os.environ.get('MODE', 'development')
preload_app = asbool(os.environ.get('GUNICORN_PRELOAD_APP', False))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 10))
workers = int(os.environ.get('GUNICORN_WORKERS', 2))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')

if 'gevent' in worker_class.lower():
    post_fork = _post_fork
    if mode == 'development':
        on_starting = _on_starting
        when_ready = _when_ready


########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-

"""Authenticate applications using API keys."""

__all__ = [
    'AuthenticationPolicy',
    'GetAuthenticatedApplication',
]

import logging
logger = logging.getLogger(__name__)

import os
import re

from zope.interface import implementer

from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import unauthenticated_userid
from pyramid.settings import asbool

from torque import model

VALID_API_KEY = re.compile(r'^\w{40}$')

@implementer(IAuthenticationPolicy)
class AuthenticationPolicy(CallbackAuthenticationPolicy):
    """A Pyramid authentication policy which obtains credential data from the
      ``request.headers['TORQUE_API_KEY']``.
    """
    
    def __init__(self, header_key='TORQUE_API_KEY', **kwargs):
        self.header_key = header_key
        self.valid_key = kwargs.get('valid_key', VALID_API_KEY)
    
    def unauthenticated_userid(self, request):
        """The ``api_key`` value found within the ``request.headers``."""
        
        api_key = request.headers.get(self.header_key, None)
        if api_key and self.valid_key.match(api_key):
            return api_key.decode('utf8')
    
    def remember(self, request, principal, **kw):
        """A no-op. There's no way to remember the user.
          
              >>> policy = AuthenticationPolicy()
              >>> policy.remember('req', 'ppl')
              []
          
        """
        
        return []
    
    def forget(self, request):
        """A no-op. There's no user to forget.
          
              >>> policy = AuthenticationPolicy()
              >>> policy.forget('req')
              []
          
        """
        
        return []
    

class GetAuthenticatedApplication(object):
    """A Pyramid request method that looks up ``model.Application``s from the
      ``api_key`` provided by the ``AuthenticationPolicy``.
    """
    
    def __init__(self, **kwargs):
        self.get_app = kwargs.get('get_app', model.LookupApplication())
        self.get_userid = kwargs.get('get_userid', unauthenticated_userid)
    
    def __call__(self, request):
        api_key = self.get_userid(request)
        if api_key:
            return self.get_app(api_key)
    


########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -*-

"""Exception views."""

__all__ = [
    'MethodNotSupportedView',
    'HTTPErrorView',
    'SystemErrorView',
]

import logging
logger = logging.getLogger(__name__)

from pyramid import httpexceptions
from pyramid.view import view_config

from torque import model
from . import tree

@view_config(context=tree.APIRoot)
@view_config(context=tree.TaskRoot)
@view_config(context=model.Task)
class MethodNotSupportedView(object):
    """Generic view exposed to throw 405 errors when endpoints are requested
      with an unsupported request method.
    """
    
    def __init__(self, request, **kwargs):
        self.request = request
        self.exc_cls = kwargs.get('exc_cls', httpexceptions.HTTPMethodNotAllowed)
    
    def __call__(self):
        raise self.exc_cls
    


@view_config(context=httpexceptions.HTTPError, renderer='string')
class HTTPErrorView(object):
    def __init__(self, request):
        self.request = request
    
    def __call__(self):
        request = self.request
        settings = request.registry.settings
        if settings.get('torque.mode') == 'development':
            raise
        return request.exception
    


@view_config(context=Exception, renderer='string')
class SystemErrorView(object):
    """Handle an internal system error."""
    
    def __init__(self, request, **kwargs):
        self.request = request
        self.exc_cls = kwargs.get('exc_cls', httpexceptions.HTTPInternalServerError)
    
    def __call__(self):
        request = self.request
        settings = request.registry.settings
        if request.exception:
            if settings.get('torque.mode') == 'development':
                raise
            logger.error(request.exception, exc_info=True)
        return self.exc_cls()
    


########NEW FILE########
__FILENAME__ = rate
# XXX todo: rate limits.
########NEW FILE########
__FILENAME__ = tree
# -*- coding: utf-8 -*-

"""Support Pyramid traversal to ``/tasks/:task_id``."""

__all__ = [
    'APIRoot',
    'TaskRoot',
]

import logging
logger = logging.getLogger(__name__)
logger.warn(
    """
  
    It's much simpler to use a named `tasks` route for the api endpoints
    than to hardcode the tasks key in the api root and to hack the faux
    root onto the tasks model -- i.e.: just generate the urls using
    ``request.route_path('tasks', ...)``.
    
    
    """
)

import re
VALID_INT = re.compile(r'^[0-9]+$')

from torque import model
from torque import root

class APIRoot(root.TraversalRoot):
    """Support ``tasks`` traversal."""
    
    def __init__(self, *args, **kwargs):
        super(APIRoot, self).__init__(*args, **kwargs)
        self.tasks_root = kwargs.get('tasks_root', TaskRoot)
    
    def __getitem__(self, key):
        if key == 'tasks':
            return self.tasks_root(self.request, key=key, parent=self)
        raise KeyError(key)
    

class TaskRoot(root.TraversalRoot):
    """Lookup tasks by ID."""
    
    def __init__(self, *args, **kwargs):
        super(TaskRoot, self).__init__(*args, **kwargs)
        self.get_task = kwargs.get('get_task', model.LookupTask())
        self.valid_id = kwargs.get('valid_id', VALID_INT)
    
    def __getitem__(self, key):
        """Lookup task by ID and, if found, make sure the task is locatable."""
        
        if self.valid_id.match(key):
            int_id = int(key)
            context = self.get_task(int_id)
            if context:
                return self.locatable(context, key)
        raise KeyError(key)
    


########NEW FILE########
__FILENAME__ = view
# -*- coding: utf-8 -*-

"""Expose and implement the Torque API endpoints."""

__all__ = [
    'EnqueTask',
]

import logging
logger = logging.getLogger(__name__)

import re

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config

from torque import model
from . import tree

# From `colander.url`.
URL_PATTERN = r"""(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""

VALID_INT = re.compile(r'^[0-9]+$')
VALID_URL = re.compile(URL_PATTERN) 

@view_config(context=tree.APIRoot, permission=NO_PERMISSION_REQUIRED,
        request_method='GET', renderer='string')
def installed_view(object):
    """``POST /`` endpoint."""
    
    return u'Torque installed and reporting for duty, sir!'


@view_config(context=tree.APIRoot, permission='create', request_method='POST',
        renderer='string')
class EnqueTask(object):
    """``POST /`` endpoint."""
    
    def __init__(self, request, **kwargs):
        self.request = request
        self.bad_request = kwargs.get('bad_request', httpexceptions.HTTPBadRequest)
        self.create_task = kwargs.get('create_task', model.CreateTask())
        self.valid_int = kwargs.get('valid_int', VALID_INT)
        self.valid_url = kwargs.get('valid_url', VALID_URL)
    
    def __call__(self):
        """Validate, store the task and return a 201 response."""
        
        # Unpack.
        request = self.request
        settings = request.registry.settings
        
        # Validate.
        url = request.GET.get('url', None)
        has_valid_url = url and self.valid_url.match(url)
        if not has_valid_url:
            raise self.bad_request(u'You must provide a valid web hook URL.')
        default_timeout = settings.get('torque.default_timeout')
        raw_timeout = request.GET.get('timeout', default_timeout)
        try:
            timeout = int(raw_timeout)
        except ValueError:
            raise self.bad_request(u'You must provide a valid integer timeout.')
        
        # Store the task.
        task = self.create_task(request.application, url, timeout, request)
        
        # Notify.
        channel = settings['torque.redis_channel']
        instruction = '{0}:0'.format(task.id)
        request.redis.rpush(channel, instruction)
        
        # Return a 201 response with the task url as the Location header.
        response = request.response
        response.status_int = 201
        response.headers['Location'] = request.resource_url(task)[:-1]
        return ''
    


@view_config(context=model.Task, permission='view', request_method='GET',
        renderer='json')
class TaskStatus(object):
    """``GET /tasks/task:id`` endpoint."""
    
    def __init__(self, request, **kwargs):
        self.request = request
    
    def __call__(self):
        """Validate, store the task and return a 201 response."""
        
        # Unpack.
        request = self.request
        task = request.context
        
        # Return a 200 response with a JSON repr of the task.
        return task
    


########NEW FILE########
__FILENAME__ = backoff
# -*- coding: utf-8 -*-

"""Provides ``Backoff``, a numerical value adapter that provides ``linear()`` and
  ``exponential()`` backoff value calculation::
  
      >>> b = Backoff(1)
      >>> b.linear()
      2
      >>> b.linear()
      3
      >>> b.exponential()
      6
      >>> b.exponential()
      12
  
  The default linear increment is the start value::
  
      >>> b = Backoff(2)
      >>> b.linear()
      4
      >>> b.linear()
      6
  
  You can override this by passing an ``incr`` kwarg to the constructor::
  
      >>> b = Backoff(10, incr=2)
      >>> b.linear()
      12
  
  You can override this by passing an arg to the linear method::
  
      >>> b.linear(4)
      16
  
  The default exponential factor is ``2``. You can override this by providing
  a ``factor`` kwarg to the constructor, or an arg to the method::
  
      >>> b = Backoff(1, factor=3)
      >>> b.exponential()
      3
      >>> b.exponential(1.5)
      4.5
  
  Both can be limited to a maximum value::
  
      >>> b = Backoff(1, max_value=2)
      >>> b.linear()
      2
      >>> b.linear()
      2
      >>> b = Backoff(2, max_value=5)
      >>> b.exponential()
      4
      >>> b.exponential()
      5
  
"""

__all__ = [
    'Backoff',
]

import logging
logger = logging.getLogger(__name__)

class Backoff(object):
    """Adapts a ``start_value`` to provide ``linear()`` and ``exponential()``
      backoff value calculation.
    """
    
    def __init__(self, start_value, factor=2, incr=None, max_value=None):
        """Store the ``value`` and setup the defaults, using the start value
          as the default increment if not provided.
        """
        
        if incr is None:
            incr = start_value
        if max_value is None:
            max_value = float('inf')
        
        self.default_factor = factor
        self.default_incr = incr
        self.max_value = max_value
        self.value = start_value
    
    def limit(self, value):
        if value > self.max_value:
            return self.max_value
        return value
    
    def linear(self, incr=None):
        """Add ``incr`` to the current value."""
        
        if incr is None:
            incr = self.default_incr
        
        value = self.value + incr
        self.value = self.limit(value)
        return self.value
    
    def exponential(self, factor=None):
        """Multiple the current value by (fraction * itself)."""
        
        if factor is None:
            factor = self.default_factor
        
        value = self.value * factor
        self.value = self.limit(value)
        return self.value
    


########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-

"""Provides business logic to read and write data using the ORM."""

__all__ = [
    'CreateApplication',
    'CreateTask',
    'DeleteOldTasks',
    'GetActiveKey',
    'GetDueTasks',
    'LookupApplication',
    'LookupTask',
    'TaskManager',
]

import logging
logger = logging.getLogger(__name__)

import json
import transaction

from datetime import datetime

from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Allow, Deny
from pyramid.security import Authenticated, Everyone

from . import constants
from . import due
from . import orm as model

class CreateApplication(object):
    """Create an application."""
    
    def __init__(self, **kwargs):
        self.app_cls = kwargs.get('app_cls', model.Application)
        self.key_cls = kwargs.get('key_cls', model.APIKey)
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self, name):
        """Create a named application with an auto-generated api_key."""
        
        key = self.key_cls()
        app = self.app_cls(name=name, api_keys=[key])
        self.session.add(app)
        self.session.flush()
        return app
    

class CreateTask(object):
    """Create a task."""
    
    def __init__(self, **kwargs):
        self.default_charset = kwargs.get('default_charset',
                constants.DEFAULT_CHARSET)
        self.default_enctype = kwargs.get('default_enctype',
                constants.DEFAULT_ENCTYPE)
        self.proxy_header_prefix = kwargs.get('proxy_header_prefix',
                constants.PROXY_HEADER_PREFIX)
        self.task_cls = kwargs.get('task_cls', model.Task)
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self, app, url, timeout, request):
        """Create and return a task belonging to the given ``app`` using the
          ``url`` and ``request`` provided.
        """
        
        # Get the content type and parse the encoding type out of it.
        content_type = request.headers.get('Content-Type', None)
        if not content_type:
            enctype = self.default_enctype
        else: # Extract just the enctype and decode to unicode.
            enctype = content_type.split(';')[0].decode('utf8')
        
        # Get the charset.
        charset = request.charset
        charset = charset.decode('utf8') if charset else self.default_charset
        
        # Use it to decode the body to a unicode string.
        body = request.body.decode(charset)
        
        # Extract any headers to pass through.
        headers = {}
        for key, value in request.headers.items():
            if key.lower().startswith(self.proxy_header_prefix.lower()):
                k = key[len(self.proxy_header_prefix):]
                headers[k] = value
        headers_json = json.dumps(headers)
        
        # Create, save and return.
        task = self.task_cls(app=app, body=body, charset=charset,
                enctype=enctype, headers=headers_json, timeout=timeout,
                url=url)
        self.session.add(task)
        self.session.flush()
        return task
    


class GetActiveKey(object):
    """Lookup an application's active ``api_key``."""
    
    def __init__(self, **kwargs):
        self.key_cls = kwargs.get('key_cls', model.APIKey)
    
    def __call__(self, app):
        """Return the first active key for the ``app`` provided."""
        
        # Unpack.
        key_cls = self.key_cls
        
        # Query active keys.
        query = key_cls.query.filter(*key_cls.active_clauses())
        
        # Belonging to this app.
        query = query.filter(key_cls.app==app)
        
        # Matching the value provided.
        return query.first()
    

class GetActiveKeyValues(object):
    """Lookup all the active ``api_key`` values's for an application."""
    
    def __init__(self, **kwargs):
        self.key_cls = kwargs.get('key_cls', model.APIKey)
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self, app):
        """Return all the active key values for the ``app`` provided."""
        
        # Unpack.
        key_cls = self.key_cls
        
        # Query active key values.
        query = self.session.query(key_cls.value)
        query = query.filter(*key_cls.active_clauses())
        
        # Belonging to this app.
        query = query.filter(key_cls.app==app)
        return [item[0] for item in query]
    


class GetDueTasks(object):
    """Get tasks that are due and pending."""
    
    def __init__(self, **kwargs):
        self.utcnow = kwargs.get('utcnow', datetime.utcnow)
        self.statuses = kwargs.get('statuses', constants.TASK_STATUSES)
        self.task_cls = kwargs.get('task_cls', model.Task)
    
    def __call__(self, limit=99, offset=0):
        """Get the tasks."""
        
        # Unpack.
        model_cls = self.task_cls
        now = self.utcnow()
        status = self.statuses['pending']
        
        # Build the query.
        query = model_cls.query.filter(model_cls.status==status)
        query = query.filter(model_cls.due<self.utcnow())
        
        # Batch.
        query = query.offset(offset).limit(limit)
        
        # Return the results.
        return query.all()
    

class DeleteOldTasks(object):
    """Delete tasks last modified more than a time delta ago."""
    
    def __init__(self, **kwargs):
        self.utcnow = kwargs.get('utcnow', datetime.utcnow)
        self.task_cls = kwargs.get('task_cls', model.Task)
    
    def __call__(self, delta):
        """Build a query and call a bulk delete."""
        
        # Unpack.
        model_cls = self.task_cls
        delta_ago = self.utcnow() - delta
        
        # Build the query.
        query = model_cls.query.filter(model_cls.modified<delta_ago)
        with transaction.manager:
            num_deleted = query.delete()
        return num_deleted
    


class LookupApplication(object):
    """Lookup an application by ``api_key``."""
    
    def __init__(self, **kwargs):
        self.app_cls = kwargs.get('app_cls', model.Application)
        self.key_cls = kwargs.get('key_cls', model.APIKey)
    
    def __call__(self, api_key):
        """Query active applications which have an active api key matching the
          value provided.
        """
        
        # Unpack.
        app_cls = self.app_cls
        key_cls = self.key_cls
        
        # Query active applications.
        query = app_cls.query.filter(*app_cls.active_clauses())
        
        # With an active api key.
        query = query.join(key_cls, key_cls.app_id==app_cls.id)
        query = query.filter(*key_cls.active_clauses())
        
        # Matching the value provided.
        query = query.filter(key_cls.value==api_key)
        return query.first()
    

class LookupTask(object):
    """Lookup a task by ``id``."""
    
    def __init__(self, **kwargs):
        self.patch_acl = kwargs.get('patch_acl', PatchTaskACL())
        self.task_cls = kwargs.get('task_cls', model.Task)
    
    def __call__(self, id_):
        """Get the task. If it exists, patch its ACL."""
        
        task = self.task_cls.query.get(id_)
        if task:
            self.patch_acl(task)
        return task
    

class PatchTaskACL(object):
    def __init__(self, **kwargs):
        self.get_keys = kwargs.get('get_keys', GetActiveKeyValues())
    
    def __call__(self, task):
        """If the ACL is NotImplemented, implement it."""
        
        # Exit if already patched.
        if task.__acl__ is not NotImplemented:
            return
        
        # Start off denying access.
        rules = [(Deny, Everyone, ALL_PERMISSIONS),]
        
        # And then grant access to ``task.app``.
        if task.app:
            for api_key in self.get_keys(task.app):
                rule = (Allow, api_key, ALL_PERMISSIONS)
                rules.insert(0, rule)
        
        # Set the ACL to the rules list.
        task.__acl__ = rules
    


class TaskManager(object):
    """Provide methods to ``acquire`` a task and then ``reschedule``,
      ``complete`` or ``fail`` it.
      
      Encapsulates the ``task_data`` returned from ``__json__()``ing the
      instance returned from the ``acquire`` query and uses this data to
      update the right task with the right values when setting the status.
    """
    
    def __init__(self, **kwargs):
        self.due_factory = kwargs.get('due_factory', due.DueFactory())
        self.session = kwargs.get('session', model.Session)
        self.statuses = kwargs.get('statuses', constants.TASK_STATUSES)
        self.task_cls = kwargs.get('task_cls', model.Task)
        self.tx_manager = kwargs.get('tx_manager', transaction.manager)
    
    def _update(self, **values):
        """Consistent logic to update the task. Note that it includes
          the retry_count and timeout as these are used by the onupdate
          functions and thus need to be in the sqlalchemy execution
          context's current params.
        """
        
        # Unpack.
        retry_count = self.task_data['retry_count']
        timeout = self.task_data['timeout']
        
        # Merge the values with a consistent values dict.
        values_dict = {
            'retry_count': retry_count,
            'timeout': timeout,
        }
        values_dict.update(values)
        query = self.task_cls.query.filter_by(id=self.task_id,
                retry_count=retry_count)
        with self.tx_manager:
            query.update(values_dict)
    
    def acquire(self, id_, retry_count):
        """Get a task by ``id`` and ``retry_count``, transactionally setting the
          status to ``in_progress`` and incrementing the ``retry_count``.
        """
        
        self.task_id = id_
        self.task_data = None
        query = self.task_cls.query
        query = query.filter_by(id=id_, retry_count=retry_count)
        with self.tx_manager:
            task = query.first()
            if task:
                task.retry_count = retry_count + 1
                self.session.add(task)
                self.task_data = task.__json__(include_request_data=True)
        return self.task_data
    
    def reschedule(self):
        """Reschedule a task by setting the due date -- does the same as the
          default / onupdate machinery but with a timeout of 0.
        """
        
        retry_count = self.task_data['retry_count']
        self._update(due=self.due_factory(0, retry_count))
        return self.statuses['pending']
    
    def complete(self):
        """Flag a task as completed."""
        
        status = self.statuses['completed']
        self._update(status=status)
        return status
    
    def fail(self):
        """Flag a task as failed."""
        
        status = self.statuses['failed']
        self._update(status=status)
        return status
    


########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

"""Shared constant values."""

DEFAULT_CHARSET = u'utf8'
DEFAULT_ENCTYPE = u'application/x-www-form-urlencoded'
PROXY_HEADER_PREFIX = u'TORQUE-PASSTHROUGH-'
TASK_STATUSES = {
    'completed': u'COMPLETED',
    'failed': u'FAILED',
    'pending': u'PENDING', 
}

########NEW FILE########
__FILENAME__ = due
# -*- coding: utf-8 -*-

"""Provides core logic to auto-generate task status and due date based on the
  task's retry count.
"""

__all__ = [
    'DueFactory',
    'StatusFactory',
]

import logging
logger = logging.getLogger(__name__)

import datetime
import os
import transaction

from torque import backoff
from . import constants

DEFAULT_SETTINGS = {
    'backoff': os.environ.get('TORQUE_BACKOFF', u'exponential'),
    'min_delay': os.environ.get('TORQUE_MIN_DUE_DELAY', 2),
    'max_delay': os.environ.get('TORQUE_MAX_DUE_DELAY', 7200),
    'max_retries': os.environ.get('TORQUE_MAX_RETRIES', 36),
}

class DueFactory(object):
    """Simple callable that uses the current datetime and a task's timeout,
      and retry count to generate a future datetime when the task should
      be retried.
    """
    
    def __init__(self, **kwargs):
        self.backoff_cls = kwargs.get('backoff', backoff.Backoff)
        self.datetime = kwargs.get('datetime', datetime.datetime)
        self.timedelta = kwargs.get('timedelta', datetime.timedelta)
        self.settings = kwargs.get('settings', DEFAULT_SETTINGS)
    
    def __call__(self, timeout, retry_count):
        """Return a datetime instance ``timeout + min_delay`` seconds in the
          future, plus, if there's a retry count, generate additional seconds
          into the future using an exponential backoff algorithm.
        """
        
        # Unpack.
        settings = self.settings
        algorithm = settings.get('backoff')
        min_delay = settings.get('min_delay')
        max_delay = settings.get('max_delay')
        
        # Coerce.
        if not timeout:
            timeout = 0
        
        # Use the ``retry_count`` to exponentially backoff from the ``min_delay``.
        backoff = self.backoff_cls(min_delay)
        backoff_method = getattr(backoff, algorithm)
        for i in range(retry_count):
            backoff_method()
        
        # Add the timeout and limit at the ``max_delay``.
        delay = backoff.value + timeout
        if delay > max_delay:
            delay = max_delay
        
        # Generate a datetime ``delay`` seconds in the future.
        return self.datetime.utcnow() + self.timedelta(seconds=delay)
    

class StatusFactory(object):
    """Simple callable that uses a retry count to choose a task status."""
    
    def __init__(self, **kwargs):
        self.settings = kwargs.get('settings', DEFAULT_SETTINGS)
        self.statuses = kwargs.get('statuses', constants.TASK_STATUSES)
    
    def __call__(self, retry_count):
        """Return pending if within the retry limit, else failed."""
        
        key = 'pending'
        if retry_count > self.settings.get('max_retries'):
            key = 'failed'
        return self.statuses[key]
    


########NEW FILE########
__FILENAME__ = orm
# -*- coding: utf-8 -*-

"""Provides declarative SQLAlchemy ORM classes."""

__all__ = [
    'APIKey',
    'Application',
    'Base',
    'Session',
    'Task',
]

import logging
logger = logging.getLogger(__name__)

import json
from datetime import datetime

from zope.sqlalchemy import ZopeTransactionExtension

from sqlalchemy import orm
from sqlalchemy.ext import declarative

from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import ForeignKey

from sqlalchemy.types import Boolean
from sqlalchemy.types import DateTime
from sqlalchemy.types import Enum
from sqlalchemy.types import Integer
from sqlalchemy.types import Unicode
from sqlalchemy.types import UnicodeText

from torque import root
faux_root = lambda **kwargs: root.TraversalRoot(None, **kwargs)

from torque import util
generate_api_key = lambda: util.generate_random_digest(num_bytes=20)

Session = orm.scoped_session(orm.sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative.declarative_base()

from .constants import DEFAULT_CHARSET
from .constants import DEFAULT_ENCTYPE
from .constants import TASK_STATUSES

from .due import DueFactory
from .due import StatusFactory

def next_due(context, get_due=None):
    """Tie the due date factory into the SQLAlchemy onupdate machinery."""
    
    # Compose.
    if get_due is None:
        get_due = DueFactory()
    
    # Unpack.
    params = context.current_parameters
    retry_count = params.get('retry_count')
    timeout = params.get('timeout')
    
    # Return the next due date.
    return get_due(timeout, retry_count)

def next_status(context, get_status=None):
    """Tie the status factory into the SQLAlchemy onupdate machinery."""
    
    # Compose.
    if get_status is None:
        get_status = StatusFactory()
    
    # Unpack.
    params = context.current_parameters
    retry_count = params.get('retry_count')
    
    # Return the next due date.
    return get_status(retry_count)


class BaseMixin(object):
    """Provides an int ``id`` as primary key, ``version``, ``created`` and
      ``modified`` columns and a scoped ``self.query`` property.
    """
    
    id = Column(Integer, primary_key=True)
    created = Column('c', DateTime, default=datetime.utcnow, nullable=False)
    modified = Column('m', DateTime, default=datetime.utcnow, nullable=False,
            onupdate=datetime.utcnow)
    version = Column('v', Integer, default=1, nullable=False)
    
    query = Session.query_property()

class LifeCycleMixin(object):
    """Provide life cycle flags for `is_active`` and ``is_deleted``."""
    
    # Flags.
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    @classmethod
    def active_clauses(cls):
        return cls.is_active==True, cls.is_deleted==False
    
    
    # Datetimes to record when the actions occured.
    activated = Column(DateTime)
    deactivated = Column(DateTime)
    deleted = Column(DateTime)
    undeleted = Column(DateTime)
    
    def _set_life_cycle_state(self, flag_name, flag_value, dt_name, now=None):
        """Shared logic to set a flag and its datetime record."""
        
        # Compose.
        if now is None:
            now = datetime.utcnow
        
        # Get the flag value.
        stored_value = getattr(self, flag_name)
        
        # Set the flag.
        setattr(self, flag_name, flag_value)
        
        # If it changed, then record when.
        if stored_value != flag_value:
            setattr(self, dt_name, now())
            identifier = getattr(self, 'slug', getattr(self, 'id', None))
            logger.debug(('Lifecycle', dt_name, self, identifier))
    
    
    # API.
    def activate(self):
        self._set_life_cycle_state('is_active', True, 'activated')
    
    def deactivate(self):
        self._set_life_cycle_state('is_active', False, 'deactivated')
    
    def delete(self):
        self._set_life_cycle_state('is_deleted', True, 'deleted')
    
    def undelete(self):
        self._set_life_cycle_state('is_deleted', False, 'undeleted')
    


class Application(Base, BaseMixin, LifeCycleMixin):
    """Encapsulate an application."""
    
    __tablename__ = 'applications'
    
    name = Column(Unicode(96), nullable=False)


class APIKey(Base, BaseMixin, LifeCycleMixin):
    """Encapsulate an api key used to authenticate an application."""
    
    __tablename__ = 'api_keys'
    __table_args__ = (
        Index('ix_api_keys', 'is_active', 'is_deleted', 'value'),
    )
    
    # Belongs to an ``Application``.
    app_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    app = orm.relationship(Application, backref=orm.backref('api_keys',
            cascade="all, delete-orphan", single_parent=True))
    
    # Has a unique, randomly generated value.
    value = Column(Unicode(40), default=generate_api_key, nullable=False,
            unique=True)

class Task(Base, BaseMixin):
    """Encapsulate a task."""
    
    __tablename__ = 'tasks'
    
    # Implemented during traversal to grant ``self.app`` access.
    __acl__ = NotImplemented
    
    # Faux root allows us to generate urls with request.resource_url, even
    # when tasks aren't looked up using traversal.
    __parent__ = faux_root(key='tasks', parent=faux_root())
    
    @property
    def __name__(self):
        return self.id
    
    
    # Can belong to an ``Application``.
    app_id = Column(Integer, ForeignKey('applications.id'))
    app = orm.relationship(Application, backref=orm.backref('tasks',
            cascade="all, delete-orphan", single_parent=True))
    
    # Count of the number of times the task has been (re)tried.
    retry_count = Column(Integer, default=0, nullable=False)
    
    # How long to wait before assuming task execution wasn't sucessful.
    timeout = Column(Integer, default=20, nullable=False) # in seconds
    
    # When should the task be retried? By default, this is the current time
    # plus the timeout, plus one second.
    due = Column(DateTime, default=next_due, onupdate=next_due, nullable=False)
    
    # Is it completed or not?
    status = Column(Enum(*TASK_STATUSES.values(), name='task_statuses'),
            default=next_status, onupdate=next_status, index=True,
            nullable=False)
    
    # The web hook url and POST body with charset and content type. Note that
    # the data is decoded from the charset to unicode.
    url = Column(Unicode(256), nullable=False)
    charset = Column(Unicode(24), default=DEFAULT_CHARSET, nullable=False)
    enctype = Column(Unicode(256), default=DEFAULT_ENCTYPE, nullable=False)
    headers = Column(UnicodeText, default=u'{}')
    body = Column(UnicodeText)
    
    def __json__(self, request=None, include_request_data=False):
        data = {
            'due': self.due.isoformat(),
            'id': self.id,
            'retry_count': self.retry_count,
            'status': self.status,
            'timeout': self.timeout,
            'url': self.url,
        }
        if include_request_data:
            data['charset'] = self.charset
            data['enctype'] = self.enctype
            data['headers'] = json.loads(self.headers)
            data['body'] = self.body
        return data
    


########NEW FILE########
__FILENAME__ = root
# -*- coding: utf-8 -*-

"""Base traversal root."""

__all__ = [
    'TraversalRoot',
]

import logging
logger = logging.getLogger(__name__)

from zope.interface import alsoProvides
from zope.interface import implementer

from pyramid.interfaces import ILocation

from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Allow, Deny
from pyramid.security import Authenticated, Everyone

@implementer(ILocation)
class TraversalRoot(object):
    """Traversal boilerplate and a base access control policy."""
    
    __acl__ = [
        (Allow, Authenticated, ALL_PERMISSIONS),
        (Deny, Everyone, ALL_PERMISSIONS),
    ]
    __name__ = ''
    __parent__ = None
    
    def __init__(self, request, key='', parent=None, **kwargs):
        self.request = request
        self.__name__ = key
        self.__parent__ = parent
        self.alsoProvides = kwargs.get('alsoProvides', alsoProvides)
    
    def locatable(self, context, key):
        """Make a context object locatable and return it."""
        
        if not hasattr(context, '__name__'):
            context.__name__ = key
        context.__parent__ = self
        context.request = self.request
        if not ILocation.providedBy(context):
            self.alsoProvides(context, ILocation)
        return context
    


########NEW FILE########
__FILENAME__ = boilerplate
# -*- coding: utf-8 -*-

"""Provide a consistent factory to make the WSGI app to be tested."""

__all__ = [
    'TestAppFactory',
    'TestConfigFactory',
]

try:
    import webtest
except ImportError: #pragma: no cover
    pass

import os

from torque import api
from torque import model
from torque.work import main as work

from pyramid_redis import hooks as redis_hooks

TEST_SETTINGS = {
    'redis.db': 5,
    'redis.url': 'redis://localhost:6379',
    'sqlalchemy.url': os.environ.get('TEST_DATABASE_URL',
            u'postgresql:///torque_test'),
    'torque.mode': 'testing',
    'torque.redis_channel': 'torque:testing',
}

class TestAppFactory(object):
    """Callable utility that returns a testable WSGI app and manages db state."""
    
    def __init__(self, **kwargs):
        self.app_factory = kwargs.get('app_factory', api.wsgi_app_factory)
        self.base = kwargs.get('base', model.Base)
        self.json_method = kwargs.get('get_json', webtest.utils.json_method)
        self.redis_factory = kwargs.get('redis_factory', redis_hooks.RedisFactory())
        self.session = kwargs.get('session', model.Session)
        self.test_app = kwargs.get('test_app', webtest.TestApp)
        self.test_settings = kwargs.get('test_settings', TEST_SETTINGS)
        self.has_created = False
    
    def __call__(self, **kwargs):
        """Create the WSGI app and wrap it with a patched webtest.TestApp."""
        
        # Patch TestApp.
        self.test_app.get_json = self.json_method('GET')
        
        # Instantiate.
        self.settings = self.test_settings.copy()
        self.settings.update(kwargs)
        app = self.app_factory(settings=self.settings)
        
        # Create the db.
        self.create()
        
        # Wrap and return.
        return self.test_app(app)
    
    def create(self):
        engine = self.session.get_bind()
        self.base.metadata.create_all(engine)
        self.redis_client = self.redis_factory(self.settings)
        self.has_created = True
        self.session.remove()
    
    def drop(self):
        if self.has_created:
            engine = self.session.get_bind()
            self.base.metadata.drop_all(engine)
            self.redis_client.flushdb()
        self.session.remove()
        
    

class TestConfigFactory(TestAppFactory):
    """Callable utility that returns a bootstrapped configurator."""
    
    def __init__(self, **kwargs):
        self.get_config = kwargs.get('get_config', work.Bootstrap())
        self.base = kwargs.get('base', model.Base)
        self.json_method = kwargs.get('get_json', webtest.utils.json_method)
        self.redis_factory = kwargs.get('redis_factory', redis_hooks.RedisFactory())
        self.session = kwargs.get('session', model.Session)
        self.test_settings = kwargs.get('test_settings', TEST_SETTINGS)
        self.has_created = False
    
    def __call__(self, **kwargs):
        """Bootstrap and return the registry."""
        
        # Instantiate.
        self.settings = self.test_settings.copy()
        self.settings.update(kwargs)
        self.config = self.get_config(settings=self.settings)
        
        # Create the db.
        self.create()
        
        # Return the registry
        return self.config
    


########NEW FILE########
__FILENAME__ = test_api
# -*- coding: utf-8 -*-

"""Functional tests for the torque API."""

import logging
logger = logging.getLogger(__name__)

import json
import transaction
import urllib
import unittest

from torque.tests import boilerplate

class TestRootEndpoint(unittest.TestCase):
    """Test the ``POST /`` endpoint to create tasks."""
    
    def setUp(self):
        self.app_factory = boilerplate.TestAppFactory()
    
    def tearDown(self):
        self.app_factory.drop()
    
    def test_get(self):
        """GET returns an installation message."""
        
        api = self.app_factory()
        r = api.get('/', status=200)
        self.assertTrue(u'installed' in r.body)
    
    def test_post(self):
        """Unauthenticated POST should be forbidden by default."""
        
        api = self.app_factory()
        r = api.post('/', status=403)
    
    def test_post_without_authentication(self):
        """POST should not be forbidden if told not to authenticate."""
        
        settings = {'torque.authenticate': False}
        api = self.app_factory(**settings)
        r = api.post('/', status=400)
    
    def test_post_authenticated(self):
        """Authenticated POST should not be forbidden."""
        
        from torque import model
        create_app = model.CreateApplication()
        get_key = model.GetActiveKey()
        
        # Create the wsgi app, which also sets up the db.
        api = self.app_factory()
        
        # Create an application and get its api key.
        with transaction.manager:
            app = create_app(u'example')
            api_key = get_key(app).value.encode('utf-8')
        
        # Now the request should make it through auth to fail on validation.
        r = api.post('/', headers={'TORQUE_API_KEY': api_key}, status=400)
    
    def test_post_task(self):
        """POSTing a valid url should enque a task."""
        
        from torque import model
        create_app = model.CreateApplication()
        get_key = model.GetActiveKey()
        get_task = model.LookupTask()
        
        # Create the wsgi app, which also sets up the db.
        api = self.app_factory()
        
        # Create an application and get its api key.
        with transaction.manager:
            app = create_app(u'example')
            api_key = get_key(app).value.encode('utf-8')
        headers={'TORQUE_API_KEY': api_key}
        
        # Invent a web hook url.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        
        # Enquing the task should respond with 201.
        r = api.post(endpoint, headers=headers, status=201)
        
        # With the url to the task as the Location header.
        task_id = int(r.headers['Location'].split('/')[-1])
        with transaction.manager:
            task = get_task(task_id)
            task_url = task.url
            task_app_name = task.app.name
        self.assertEqual(task_url, url)
        self.assertEqual(task_app_name, u'example')
    
    def test_post_invalid_url(self):
        """POSTing an invalid url should not."""
        
        from torque import model
        create_app = model.CreateApplication()
        get_key = model.GetActiveKey()
        
        # Create the wsgi app, which also sets up the db.
        api = self.app_factory()
        
        # Create an application and get its api key.
        with transaction.manager:
            app = create_app(u'example')
            api_key = get_key(app).value.encode('utf-8')
        headers={'TORQUE_API_KEY': api_key}
        
        # Invent an invalid web hook url.
        url = u'not a url'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        
        # Enquing the task should fail.
        r = api.post(endpoint, headers=headers, status=400)
    
    def test_post_task_without_authentication(self):
        """POSTing without auth should enque a task with ``app==None``."""
        
        from torque import model
        get_task = model.LookupTask()
        
        # Create the wsgi app, which also sets up the db.
        settings = {'torque.authenticate': False}
        api = self.app_factory(**settings)
        
        # Invent a web hook url.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        
        # Enquing the task should respond with 201.
        r = api.post(endpoint, status=201)
        
        # With the url to the task as the Location header.
        task_id = int(r.headers['Location'].split('/')[-1])
        with transaction.manager:
            task = get_task(task_id)
            task_app = task.app
        self.assertIsNone(task_app)
    
    def test_post_task_with_body(self):
        """Enqued tasks should store the charset and encoding and the decoded
          POST body.
        """
        
        from torque import model
        get_task = model.LookupTask()
        
        # Create the wsgi app, which also sets up the db.
        settings = {'torque.authenticate': False}
        api = self.app_factory(**settings)
        
        # Setup a request with form encoded latin-1.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=latin1'}
        params = {'foo': u'bçr'.encode('latin1')}
        
        # Enquing the task should respond with 201.
        r = api.post(endpoint, headers=headers, params=params, status=201)
        
        # With the url to the task as the Location header.
        task_id = int(r.headers['Location'].split('/')[-1])
        with transaction.manager:
            task = get_task(task_id)
            task_charset = task.charset
            task_enctype = task.enctype
            task_body = task.body
        self.assertEquals(task_charset, u'latin1')
        self.assertEquals(task_enctype, u'application/x-www-form-urlencoded')
        self.assertTrue(task_body, urllib.urlencode(params).decode('latin1'))
    
    def test_post_task_with_json_body(self):
        """Test enqueing a task with a JSON body and UTF-8 charset."""
        
        from torque import model
        get_task = model.LookupTask()
        
        # Create the wsgi app, which also sets up the db.
        settings = {'torque.authenticate': False}
        api = self.app_factory(**settings)
        
        # Setup a request with form encoded latin-1.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        params = {u'foo': u'b€r'}
        
        # Enquing the task should respond with 201.
        r = api.post_json(endpoint, params=params, status=201)
        
        # With the url to the task as the Location header.
        task_id = int(r.headers['Location'].split('/')[-1])
        with transaction.manager:
            task = get_task(task_id)
            task_charset = task.charset
            task_enctype = task.enctype
            task_body = task.body
        self.assertEquals(task_charset, u'UTF-8')
        self.assertEquals(task_enctype, u'application/json')
        self.assertTrue(json.loads(task_body), params)
    

class TestGetCreatedTaskLocation(unittest.TestCase):
    """Test that the task location returned by ``POST /`` works."""
    
    def setUp(self):
        self.app_factory = boilerplate.TestAppFactory()
    
    def tearDown(self):
        self.app_factory.drop()
    
    def test_get_created_task_location(self):
        """The location returned after enquing a task should be gettable."""
        
        # Create the wsgi app, which also sets up the db.
        settings = {'torque.authenticate': False}
        api = self.app_factory(**settings)
        
        # Invent a web hook url.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        
        # Enquing the task should respond with 201 and the location header.
        r = api.post(endpoint, status=201)
        location = r.headers['Location']
        
        # Getting that location should return JSON and a 200.
        r = api.get_json(location, status=200)
    
    def test_get_created_task_access_control(self):
        """When using authentication, the task is only accessible to the app
          that created it.
        """
        
        from torque import model
        create_app = model.CreateApplication()
        get_key = model.GetActiveKey()
        get_task = model.LookupTask()
        
        # Create the wsgi app, which also sets up the db.
        api = self.app_factory()
        
        # Create an application and get its api key.
        with transaction.manager:
            app = create_app(u'example')
            api_key = get_key(app).value.encode('utf-8')
        headers={'TORQUE_API_KEY': api_key}
        
        # Invent a web hook url.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        
        # Enquing the task should respond with 201.
        r = api.post(endpoint, headers=headers, status=201)
        location = r.headers['Location']
        
        # Getting that location should be forbidden unless authenticated.
        r = api.get_json(location, status=403)
        r = api.get_json(location, headers=headers, status=200)
    

class TestCreatedTaskNotification(unittest.TestCase):
    """Test new task notifications."""
    
    def setUp(self):
        self.app_factory = boilerplate.TestAppFactory()
    
    def tearDown(self):
        self.app_factory.drop()
    
    def test_notification_channel_is_empty(self):
        """Before creating a task, the redis channel should be empty."""
        
        api = self.app_factory()
        settings = self.app_factory.settings
        channel = settings.get('torque.redis_channel')
        redis = self.app_factory.redis_client
        
        # Enquing the task should respond with 201 and the location header.
        self.assertEquals(redis.llen(channel), 0)
    
    def test_notification(self):
        """After creating a task, its `id:retry_count` should be in redis."""
        
        # Setup.
        api = self.app_factory(**{'torque.authenticate': False})
        settings = self.app_factory.settings
        channel = settings.get('torque.redis_channel')
        redis = self.app_factory.redis_client
        
        # Enque the task.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        r = api.post(endpoint, status=201)
        location = r.headers['Location']
        
        # Its id should be in the redis channel list.
        self.assertEquals(redis.llen(channel), 1)
        task_id, retry_count = map(int, redis.lpop(channel).split(':'))
        self.assertTrue(task_id > 0)
        self.assertTrue(retry_count is 0)
        self.assertTrue(location.endswith(str(task_id)))
    
    def test_notification_order(self):
        """Task notifications should be added to the tail of the channel list."""
        
        # Setup.
        api = self.app_factory(**{'torque.authenticate': False})
        settings = self.app_factory.settings
        channel = settings.get('torque.redis_channel')
        redis = self.app_factory.redis_client
        
        # Enque two tasks.
        url = u'http://example.com/hook'
        endpoint = '/?url=' + urllib.quote_plus(url.encode('utf-8'))
        r1 = api.post(endpoint, status=201)
        r2 = api.post(endpoint, status=201)
        location1 = r1.headers['Location']
        location2 = r2.headers['Location']
        
        # Pop them in order from the head of the list -- the first task should
        # come first.
        id1, _ = map(int, redis.lpop(channel).split(':'))
        id2, _ = map(int, redis.lpop(channel).split(':'))
        self.assertTrue(location1.endswith(str(id1)))
        self.assertTrue(location2.endswith(str(id2)))
    


########NEW FILE########
__FILENAME__ = test_work
# -*- coding: utf-8 -*-

"""Functional tests for the ``torque.work`` package."""

import logging
logger = logging.getLogger(__name__)

import json
import transaction
import urllib
import unittest

from torque.tests import boilerplate

class TestChannelConsumer(unittest.TestCase):
    """Test consuming instructions from the redis channel."""
    
    def setUp(self):
        self.config_factory = boilerplate.TestConfigFactory()
        self.registry = self.config_factory().registry
    
    def tearDown(self):
        self.config_factory.drop()
    
    #def test_foo(self):
    #    """XXX"""
    #    
    #    self.assertTrue('foo' == 'foo')
    

class TestTaskPerformer(unittest.TestCase):
    """Test performing tasks."""
    
    def setUp(self):
        self.config_factory = boilerplate.TestConfigFactory()
        self.registry = self.config_factory().registry
    
    def tearDown(self):
        self.config_factory.drop()
    
    def test_performing_task_miss(self):
        """Performing a task that doesn't exist returns None."""
        
        from torque.work.perform import TaskPerformer
        performer = TaskPerformer()
        
        status = performer('1234:0', None)
        self.assertIsNone(status)
    
    def test_performing_task(self):
        """Performing a task successfully marks it as completed."""
        
        from mock import Mock
        from pyramid.request import Request
        from threading import Event
        flag = Event()
        flag.set()
        
        from torque.model import TASK_STATUSES
        from torque.model import CreateTask
        from torque.model import Session
        from torque.work.perform import TaskPerformer
        
        # Create a task.
        req = Request.blank('/')
        create_task = CreateTask()
        with transaction.manager:
            task = create_task(None, 'http://example.com', 20, req)
            instruction = '{0}:0'.format(task.id)
        
        # Instantiate a performer with the requests.post method mocked
        # to return 200 without making a request.
        mock_post = Mock()
        mock_post.return_value.status_code = 200
        performer = TaskPerformer(post=mock_post)
        
        # When performed, the task should be marked as completed.
        status = performer(instruction, flag)
        self.assertTrue(status is TASK_STATUSES[u'completed'])
    
    def test_performing_task_connection_error(self):
        """Tasks are retried when arbitrary connection errors occur."""
        
        from mock import Mock
        from pyramid.request import Request
        from requests.exceptions import RequestException
        from threading import Event
        flag = Event()
        flag.set()
        
        from torque.model import TASK_STATUSES
        from torque.model import CreateTask
        from torque.model import Session
        from torque.work.perform import TaskPerformer
        
        # Create a task.
        req = Request.blank('/')
        create_task = CreateTask()
        with transaction.manager:
            task = create_task(None, 'http://example.com', 20, req)
            instruction = '{0}:0'.format(task.id)
        
        # Instantiate a performer with the requests.post method mocked
        # to raise a connection error.
        mock_post = Mock()
        mock_post.side_effect = RequestException()
        performer = TaskPerformer(post=mock_post)
        
        # The task should be pending a retry.
        status = performer(instruction, flag)
        self.assertTrue(status is TASK_STATUSES[u'pending'])
    
    def test_performing_task_server_error(self):
        """Tasks are retried when internal server errors occur."""
        
        from mock import Mock
        from pyramid.request import Request
        from threading import Event
        flag = Event()
        flag.set()
        
        from torque.model import TASK_STATUSES
        from torque.model import CreateTask
        from torque.model import Session
        from torque.work.perform import TaskPerformer
        
        # Create a task.
        req = Request.blank('/')
        create_task = CreateTask()
        with transaction.manager:
            task = create_task(None, 'http://example.com', 20, req)
            instruction = '{0}:0'.format(task.id)
        
        # Instantiate a performer with the requests.post method mocked
        # to raise a connection error.
        mock_post = Mock()
        mock_post.return_value.status_code = 500
        performer = TaskPerformer(post=mock_post)
        
        # The task should be pending a retry.
        status = performer(instruction, flag)
        self.assertTrue(status is TASK_STATUSES[u'pending'])
    
    def test_performing_task_bad_request(self):
        """Tasks are failed when invalid."""
        
        from mock import Mock
        from pyramid.request import Request
        from threading import Event
        flag = Event()
        flag.set()
        
        from torque.model import TASK_STATUSES
        from torque.model import CreateTask
        from torque.model import Session
        from torque.work.perform import TaskPerformer
        
        # Create a task.
        req = Request.blank('/')
        create_task = CreateTask()
        with transaction.manager:
            task = create_task(None, 'http://example.com', 20, req)
            instruction = '{0}:0'.format(task.id)
        
        # Instantiate a performer with the requests.post method mocked
        # to raise a connection error.
        mock_post = Mock()
        mock_post.return_value.status_code = 400
        performer = TaskPerformer(post=mock_post)
        
        # The task should be pending a retry.
        status = performer(instruction, flag)
        self.assertTrue(status is TASK_STATUSES[u'failed'])
    
    def test_performing_task_waits(self):
        """Performing a task exponentially backs off polling the greenlet
          to see whether it has completed.
        """
        
        from gevent import sleep
        from mock import Mock
        from pyramid.request import Request
        from threading import Event
        flag = Event()
        flag.set()
        
        from torque.model import TASK_STATUSES
        from torque.model import CreateTask
        from torque.model import Session
        from torque.work.perform import TaskPerformer
        
        # Create a task.
        req = Request.blank('/')
        create_task = CreateTask()
        with transaction.manager:
            task = create_task(None, 'http://example.com', 20, req)
            instruction = '{0}:0'.format(task.id)
        
        # Instantiate a performer with the requests.post method mocked
        # to take 0.6 seconds to return 200.
        def mock_post(*args, **kwargs):
            sleep(0.4)
            mock_response = Mock()
            mock_response.status_code = 200
            return mock_response
        
        # And the sleep method mocked so we can check its calls.
        counter = Mock()
        def mock_sleep(delay):
            counter(delay)
            sleep(delay)
        
        performer = TaskPerformer(post=mock_post, sleep=mock_sleep)
        status = performer(instruction, flag)
        self.assertTrue(status is TASK_STATUSES[u'completed'])
        
        # And gevent.sleep was called with exponential backoff.
        self.assertTrue(0.1499 < counter.call_args_list[1][0][0] < 0.1501)
        self.assertTrue(0.2249 < counter.call_args_list[2][0][0] < 0.2251)
    


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

"""Utility functions."""

__all__ = [
    'generate_random_digest',
]

import logging
logger = logging.getLogger(__name__)

import os
from binascii import hexlify

def generate_random_digest(num_bytes=20):
    """Generates a random hash and returns the hex digest as a unicode string.
      
      Defaults to sha1::
      
          >>> import hashlib
          >>> h = hashlib.sha1()
          >>> digest = generate_random_digest()
          >>> len(h.hexdigest()) == len(digest)
          True
      
      Pass in ``num_bytes`` to specify a different length hash::
      
          >>> h = hashlib.sha512()
          >>> digest = generate_random_digest(num_bytes=64)
          >>> len(h.hexdigest()) == len(digest)
          True
      
      Returns unicode::
      
          >>> type(digest) == type(u'')
          True
      
    """
    
    r = os.urandom(num_bytes)
    return unicode(hexlify(r))


########NEW FILE########
__FILENAME__ = cleanup
# -*- coding: utf-8 -*-

"""Provides ``Cleaner``, a utility that polls the db and deletes old tasks."""

__all__ = [
    'Cleaner',
]

import logging
logger = logging.getLogger(__name__)

import time
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from torque import model
from .main import Bootstrap

class Cleaner(object):
    """Polls the db and delete old tasks."""
    
    def __init__(self, days, interval=7200, **kwargs):
        self.days = days
        self.interval = interval
        self.delete_tasks = kwargs.get('delete_tasks', model.DeleteOldTasks())
        self.logger = kwargs.get('logger', logger)
        self.session = kwargs.get('session', model.Session)
        self.time = kwargs.get('time', time)
        self.timedelta = kwargs.get('timedelta', timedelta)
    
    def start(self):
        self.poll()
    
    def poll(self):
        """Poll the db ad-infinitum."""
        
        delta = self.timedelta(days=self.days)
        while True:
            t1 = self.time.time()
            try:
                self.delete_tasks(delta)
            except SQLAlchemyError as err:
                self.logger.warn(err, exc_info=True)
            finally:
                self.session.remove()
            self.time.sleep(self.interval)
    

class ConsoleScript(object):
    """Bootstrap the environment and run the consumer."""
    
    def __init__(self, **kwargs):
        self.cleaner_cls = kwargs.get('cleaner_cls', Cleaner)
        self.get_config = kwargs.get('get_config', Bootstrap())
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self):
        """Get the configured registry. Unpack the redis client and input
          channel(s), instantiate and start the consumer.
        """
        
        # Get the configured registry.
        config = self.get_config()
        
        # Unpack the redis client and input channels.
        settings = config.registry.settings
        days = int(settings.get('torque.cleanup_after_days'))
        
        # Instantiate and start the consumer.
        cleaner = self.cleaner_cls(days)
        try:
            cleaner.start()
        finally:
            self.session.remove()
    

main = ConsoleScript()

########NEW FILE########
__FILENAME__ = consume
# -*- coding: utf-8 -*-

"""Provides ``ChannelConsumer``, a utility that consumes task instructions from
  a redis channel and spawns a new (green) thread to perform each task.
"""

__all__ = [
    'ChannelConsumer',
]

import logging
logger = logging.getLogger(__name__)

import threading
import time

from redis.exceptions import RedisError
from pyramid_redis.hooks import RedisFactory

from torque import model

from .main import Bootstrap
from .perform import TaskPerformer

class ChannelConsumer(object):
    """Takes instructions from one or more redis channels. Calls a handle
      function in a new thread, passing through a flag that the handle
      function can periodically check to exit.
    """
    
    def __init__(self, redis, channels, delay=0.001, timeout=10, **kwargs):
        self.redis = redis
        self.channels = channels
        self.connect_delay = delay
        self.timeout = timeout
        self.handler_cls = kwargs.get('handler_cls', TaskPerformer)
        self.logger = kwargs.get('logger', logger)
        self.sleep = kwargs.get('sleep', time.sleep)
        self.thread_cls = kwargs.get('thread_cls', threading.Thread)
        self.flag_cls = kwargs.get('flag_cls', threading.Event)
    
    def start(self):
        self.control_flag = self.flag_cls()
        self.control_flag.set()
        try:
            self.consume()
        finally:
            self.control_flag.clear()
    
    def consume(self):
        """Consume the redis channel ad-infinitum."""
        
        while True:
            try:
                return_value = self.redis.blpop(self.channels, timeout=self.timeout)
            except RedisError as err:
                self.logger.warn(err, exc_info=True)
                self.sleep(self.timeout)
            else:
                if return_value is not None:
                    channel, data = return_value
                    self.spawn(data)
                    self.sleep(self.connect_delay)
    
    def spawn(self, data):
        """Handle the ``data`` in a new thread."""
        
        args = (data, self.control_flag)
        handler = self.handler_cls()
        thread = self.thread_cls(target=handler, args=args)
        thread.start()
    

class ConsoleScript(object):
    """Bootstrap the environment and run the consumer."""
    
    def __init__(self, **kwargs):
        self.consumer_cls = kwargs.get('consumer_cls', ChannelConsumer)
        self.get_redis = kwargs.get('get_redis', RedisFactory())
        self.get_config = kwargs.get('get_config', Bootstrap())
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self):
        """Get the configured registry. Unpack the redis client and input
          channel(s), instantiate and start the consumer.
        """
        
        # Get the configured registry.
        config = self.get_config()
        
        # Unpack the redis client and input channels.
        settings = config.get_settings()
        redis_client = self.get_redis(settings, registry=config.registry)
        input_channels = settings.get('torque.redis_channel').strip().split()
        
        # Instantiate and start the consumer.
        consumer = self.consumer_cls(redis_client, input_channels)
        try:
            consumer.start()
        finally:
            self.session.remove()
    

main = ConsoleScript()

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

"""Provides ``ConsoleEnvironment``, a callable utility that sets up a gevent
  patched environment for long running console scripts.
"""

__all__ = [
    'ConsoleEnvironment',
]

# Patch everything with gevent.
import gevent.monkey
gevent.monkey.patch_all()

#import psycogreen.gevent
#psycogreen.gevent.patch_psycopg()

# Enable logging to stderr
import logging
logging.basicConfig()

import os
from pyramid.config import Configurator
from torque import model

DEFAULTS = {
    'mode': os.environ.get('MODE', 'development'),
    'redis_channel': os.environ.get('TORQUE_REDIS_CHANNEL', 'torque'),
    'cleanup_after_days': os.environ.get('TORQUE_CLEANUP_AFTER_DAYS', 7),
}

class Bootstrap(object):
    """Bootstrap Pyramid dependencies and return the configured registry."""
    
    def __init__(self, **kwargs):
        self.configurator_cls = kwargs.get('configurator_cls', Configurator)
        self.default_settings = kwargs.get('default_settings', DEFAULTS)
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self, **kwargs):
        """Configure and patch, making sure to explicitly close any connections
          opened by the thread local session.
        """
        
        # Unpack settings.
        config = self.configurator_cls(**kwargs)
        settings = config.get_settings()
        for key, value in self.default_settings.items():
            settings.setdefault('torque.{0}'.format(key), value)
        
        # Configure redis and the db connection.
        config.include('torque.model')
        config.include('pyramid_redis')
        config.commit()
        
        # Explicitly remove any db connections.
        self.session.remove()
        
        # Return the registry (the only part of the "environment" we're
        # interested in).
        return config
    


########NEW FILE########
__FILENAME__ = perform
# -*- coding: utf-8 -*-

"""Provides ``TaskPerformer``, a utility that aquires a task from the db,
  and performs it by making a POST request to the task's web hook url.
"""

__all__ = [
    'TaskPerformer',
]

import logging
logger = logging.getLogger(__name__)

import gevent
import requests

from sqlalchemy.exc import SQLAlchemyError

from torque import backoff
from torque import model

class TaskPerformer(object):
    def __init__(self, **kwargs):
        self.task_manager_cls = kwargs.get('task_manager_cls', model.TaskManager)
        self.backoff_cls = kwargs.get('backoff', backoff.Backoff)
        self.post = kwargs.get('post', requests.post)
        self.sleep = kwargs.get('sleep', gevent.sleep)
        self.spawn = kwargs.get('spawn', gevent.spawn)
    
    def __call__(self, instruction, control_flag):
        """Acquire a task, perform it and update its status accordingly."""
        
        # Parse the instruction to transactionally
        # get-the-task-and-incr-its-retry-count. This ensures that even if the
        # next instruction off the queue is for the same task, or if a parallel
        # worker has the same instruction, the task will only be acquired once.
        task_data = None
        task_manager = self.task_manager_cls()
        task_id, retry_count = map(int, instruction.split(':'))
        try:
            task_data = task_manager.acquire(task_id, retry_count)
        except SQLAlchemyError as err:
            logger.warn(err)
        if not task_data:
            return
        
        # Unpack the task data.
        url = task_data['url']
        body = task_data['body']
        timeout = task_data['timeout']
        headers = task_data['headers']
        headers['content-type'] = '{0}; charset={1}'.format(
                task_data['enctype'], task_data['charset'])
        
        # Spawn a POST to the web hook in a greenlet -- so we can monitor
        # the control flag in case we want to exit whilst waiting.
        kwargs = dict(data=body, headers=headers, timeout=timeout)
        greenlet = self.spawn(self.post, url, **kwargs)
        
        # Wait for the request to complete, checking the greenlet's progress
        # with an expoential backoff.
        response = None
        delay = 0.1 # secs
        max_delay = 2 # secs - XXX really this should be the configurable
                      # min delay in the due logic's `timeout + min delay`.
                      # The issue being that we could end up checking the
                      # ready max delay after the timout, which means that
                      # the task is likely to be re-queued already.
        backoff = self.backoff_cls(delay, max_value=max_delay)
        while control_flag.is_set():
            self.sleep(delay)
            if greenlet.ready():
                response = greenlet.value
                break
            delay = backoff.exponential(1.5) # 0.15, 0.225, 0.3375, ... 2
        
        # If we didn't get a response, or if the response was not successful,
        # reschedule it. Note that rescheduling *accelerates* the due date --
        # doing nothing here would leave the task to be retried anyway, as its
        # due date was set when the task was aquired.
        if response is None or response.status_code > 499:
            # XXX what we could also do here are:
            # - set a more informative status flag (even if only descriptive)
            # - noop if the greenlet request timed out
            status = task_manager.reschedule()
        elif response.status_code > 201:
            status = task_manager.fail()
        else:
            status = task_manager.complete()
        return status
    


########NEW FILE########
__FILENAME__ = requeue
# -*- coding: utf-8 -*-

"""Provides ``RequeuePoller``, a utility that polls the db and add tasks
  to the queue.
"""

__all__ = [
    'RequeuePoller',
]

import logging
logger = logging.getLogger(__name__)

import time

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from pyramid_redis.hooks import RedisFactory
from torque import model
from .main import Bootstrap

class RequeuePoller(object):
    """Takes instructions from one or more redis channels. Calls a handle
      function in a new thread, passing through a flag that the handle
      function can periodically check to exit.
    """
    
    def __init__(self, redis, channel, delay=0.001, interval=10, **kwargs):
        self.redis = redis
        self.channel = channel
        self.delay = delay
        self.interval = interval
        self.get_tasks = kwargs.get('get_tasks', model.GetDueTasks())
        self.logger = kwargs.get('logger', logger)
        self.session = kwargs.get('session', model.Session)
        self.time = kwargs.get('time', time)
    
    def start(self):
        self.poll()
    
    def poll(self):
        """Poll the db ad-infinitum."""
        
        while True:
            t1 = self.time.time()
            try:
                tasks = self.get_tasks()
            except SQLAlchemyError as err:
                self.logger.warn(err, exc_info=True)
            else:
                if tasks:
                    for task in tasks:
                        try:
                            self.enqueue(task)
                        except RedisError as err:
                            self.logger.warn(err, exc_info=True)
                        self.time.sleep(self.delay)
            finally:
                self.session.remove()
            current_time = self.time.time()
            due_time = t1 + self.interval
            if current_time < due_time:
                self.time.sleep(due_time - current_time)
    
    def enqueue(self, task):
        """Push an instruction to re-try the task on the redis channel."""
        
        instruction = '{0}:{1}'.format(task.id, task.retry_count)
        self.redis.rpush(self.channel, instruction)
    

class ConsoleScript(object):
    """Bootstrap the environment and run the consumer."""
    
    def __init__(self, **kwargs):
        self.requeue_cls = kwargs.get('requeue_cls', RequeuePoller)
        self.get_redis = kwargs.get('get_redis', RedisFactory())
        self.get_config = kwargs.get('get_config', Bootstrap())
        self.session = kwargs.get('session', model.Session)
    
    def __call__(self):
        """Get the configured registry. Unpack the redis client and input
          channel(s), instantiate and start the consumer.
        """
        
        # Get the configured registry.
        config = self.get_config()
        
        # Unpack the redis client and input channels.
        settings = config.registry.settings
        redis_client = self.get_redis(settings, registry=config.registry)
        channel = settings.get('torque.redis_channel')
        
        # Instantiate and start the consumer.
        poller = self.requeue_cls(redis_client, channel)
        try:
            poller.start()
        finally:
            self.session.remove()
    

main = ConsoleScript()

########NEW FILE########
