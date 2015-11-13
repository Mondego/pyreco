__FILENAME__ = db_utils
# -*- coding:utf-8 -*-
import logging
import socket
from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS


logger = logging.getLogger('replicated.db_checker')

cache = get_cache(
    getattr(settings, 'REPLICATED_CACHE_BACKEND', DEFAULT_CACHE_ALIAS)
)
host_name = socket.gethostname()


def _db_is_alive(db_name):
    from django.db import connections

    db = connections[db_name]
    try:
        if db.connection is not None and hasattr(db.connection, 'ping'):
            logger.debug(u'Ping db %s.', db_name)
            db.connection.ping()
        else:
            logger.debug(u'Get cursor for db %s.', db_name)
            db.cursor()
        return True
    except Exception:
        logger.exception(u'Error verifying db %s.', db_name)
        return False


def _db_is_not_read_only(db_name):
    from django.db import connections

    db_engine = settings.DATABASES[db_name]['ENGINE']
    if '.' in db_engine:
        db_engine = db_engine.rsplit('.', 1)[1]

    try:
        cursor = connections[db_name].cursor()

        if db_engine == 'mysql':
            cursor.execute('SELECT @@read_only')
            return not int(cursor.fetchone()[0])

        elif db_engine == 'oracle':
            cursor.execute('SELECT open_mode FROM v$database')
            return cursor.fetchone()[0] != 'READ ONLY'

    except Exception:
        logger.exception(u'Error verifying db %s.', db_name)
        return False


def check_db(
    checker, db_name, cache_seconds=0, number_of_tries=1, force=False
):
    assert number_of_tries >= 1, u'Number of tries must be >= 1.'

    cache_td = timedelta(seconds=cache_seconds)

    checker_name = checker.__name__
    cache_key = host_name + checker_name

    check_cache = cache.get(cache_key, {})

    death_time = check_cache.get(db_name)
    if death_time:
        if death_time + cache_td > datetime.now():
            logger.debug(
                u'Last check "%s" %s was less than %d ago, no check needed.',
                checker_name, db_name, cache_seconds
            )
            if not force:
                return False
            logger.debug(u'Force check "%s" %s.', db_name, checker_name)

        else:
            del check_cache[db_name]
            logger.debug(
                u'Last check "%s" %s was more than %d ago, checking again.',
                db_name, checker_name, cache_seconds
            )
    else:
        logger.debug(
            u'%s cache for "%s" is empty.',
            checker_name, db_name
        )

    for count in range(1, number_of_tries + 1):
        result = checker(db_name)
        logger.debug(
            u'Trying to check "%s" %s: %d try.',
            db_name, checker_name, count
        )
        if result:
            logger.debug(
                u'After %d tries "%s" %s = True',
                count, db_name, checker_name
            )
            break

    if not result:
        msg = u'After %d tries "%s" %s = False.'
        logger.warning(msg, number_of_tries, db_name, checker_name)
        check_cache[db_name] = datetime.now()

    cache.set(cache_key, check_cache)

    return result


db_is_alive = partial(check_db, _db_is_alive)
db_is_not_read_only = partial(check_db, _db_is_not_read_only)

########NEW FILE########
__FILENAME__ = decorators
# -*- coding:utf-8 -*-
'''
Decorators for using specific routing state for particular requests.
Used in cases when automatic switching based on request method doesn't
work.

Usage:

    from django_replicated.decorators import use_master, use_slave

    @use_master
    def my_view(request, ...):
        # master database used for all db operations during
        # execution of the view (if not explicitly overriden).

    @use_slave
    def my_view(request, ...):
        # same with slave connection
'''
import utils
from functools import wraps
from utils import routers

def _use_state(state):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            current_state = utils.check_state_override(request, state)
            routers.use_state(current_state)
            try:
                response = func(request, *args, **kwargs)
            finally:
                routers.revert()
            utils.handle_updated_redirect(request, response)
            return response
        return wrapper
    return decorator

use_master = _use_state('master')
use_slave = _use_state('slave')

########NEW FILE########
__FILENAME__ = middleware
# -*- coding:utf-8 -*-

from .utils import (
    check_state_override,
    handle_updated_redirect,
    is_service_read_only,
    routers,
)


class ReplicationMiddleware(object):
    '''
    Middleware for automatically switching routing state to
    master or slave depending on request method.

    In a properly designed web applications GET and HEAD request should
    not require writing to a database (except by side effects). This
    middleware switches database wrapper to slave mode for such requests.

    One special case is handling redirect responses after POST requests
    doing writes to database. They are most commonly used to show updated
    pages to a user. However in this case slave replicas may not yet be
    updated to match master. Thus first redirect after POST is pointed to
    master connection even if it only GETs data.
    '''
    def process_request(self, request):
        state = 'slave' if request.method in ['GET', 'HEAD'] else 'master'
        state = check_state_override(request, state)
        routers.init(state)

    def process_response(self, request, response):
        handle_updated_redirect(request, response)
        return response


class ReadOnlyMiddleware(object):
    def process_request(self, request):
        request.service_is_readonly = is_service_read_only()

########NEW FILE########
__FILENAME__ = router
# -*- coding:utf-8 -*-
import random
from threading import local

from django.conf import settings

from .db_utils import db_is_alive


class ReplicationRouter(object):

    def __init__(self):
        from django.db.utils import DEFAULT_DB_ALIAS
        self._context = local()
        self.DEFAULT_DB_ALIAS = DEFAULT_DB_ALIAS
        self.DOWNTIME = getattr(settings, 'DATABASE_DOWNTIME', 60)
        self.SLAVES = getattr(settings, 'DATABASE_SLAVES', [DEFAULT_DB_ALIAS])

    def _init_context(self):
        self._context.state_stack = []
        self._context.chosen = {}
        self._context.state_change_enabled = True
        self._context.inited = True

    @property
    def context(self):
        if not getattr(self._context, 'inited', False):
            self._init_context()
        return self._context

    def init(self, state):
        self._init_context()
        self.use_state(state)

    def is_alive(self, db_name):
        return db_is_alive(db_name, self.DOWNTIME)

    def set_state_change(self, enabled):
        self.context.state_change_enabled = enabled

    def state(self):
        '''
        Current state of routing: 'master' or 'slave'.
        '''
        if self.context.state_stack:
            return self.context.state_stack[-1]
        else:
            return 'master'

    def use_state(self, state):
        '''
        Switches router into a new state. Requires a paired call
        to 'revert' for reverting to previous state.
        '''
        if not self.context.state_change_enabled:
            state = self.state()
        self.context.state_stack.append(state)
        return self

    def revert(self):
        '''
        Reverts wrapper state to a previous value after calling
        'use_state'.
        '''
        self.context.state_stack.pop()

    def db_for_write(self, model, **hints):
        self.context.chosen['master'] = self.DEFAULT_DB_ALIAS

        return self.DEFAULT_DB_ALIAS

    def db_for_read(self, model, **hints):
        if self.state() == 'master':
            return self.db_for_write(model, **hints)

        if self.state() in self.context.chosen:
            return self.context.chosen[self.state()]

        slaves = self.SLAVES[:]
        random.shuffle(slaves)

        for slave in slaves:
            if self.is_alive(slave):
                chosen = slave
                break
        else:
            chosen = self.DEFAULT_DB_ALIAS

        self.context.chosen[self.state()] = chosen

        return chosen

########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-

import warnings
from functools import partial

from django import db
from django.conf import settings
from django.core import urlresolvers

from .db_utils import db_is_alive, db_is_not_read_only


def _get_func_import_path(func):
    '''
    Returns import path of a class method or a module-level funtion.
    '''
    base = func.__class__ if hasattr(func, '__class__') else func
    return '%s.%s' % (base.__module__, base.__name__)


def check_state_override(request, state):
    '''
    Used to check if a web request should use a master or slave
    database besides default choice.
    '''
    if request.COOKIES.get('just_updated') == 'true':
        return 'master'

    overrides = getattr(settings, 'REPLICATED_VIEWS_OVERRIDES', {})

    if overrides:
        match = urlresolvers.resolve(request.path_info)
        import_path = _get_func_import_path(match.func)

        for lookup_view, forced_state in overrides.iteritems():
            if match.url_name == lookup_view or import_path == lookup_view:
                state = forced_state
                break

    return state


def handle_updated_redirect(request, response):
    '''
    Sets a flag using cookies to redirect requests happening after
    successful write operations to ensure that corresponding read
    request will use master database. This avoids situation when
    replicas lagging behind on updates a little.
    '''
    if response.status_code in [302, 303] and routers.state() == 'master':
        response.set_cookie('just_updated', 'true', max_age=5)
    else:
        if 'just_updated' in request.COOKIES:
            response.delete_cookie('just_updated')


def is_service_read_only():
    from django.db import DEFAULT_DB_ALIAS

    USE_SELECT = getattr(settings, 'REPLICATED_SELECT_READ_ONLY', False)

    check_method = db_is_not_read_only if USE_SELECT else db_is_alive

    return not check_method(
        db_name=DEFAULT_DB_ALIAS,
        cache_seconds=getattr(settings, 'REPLICATED_READ_ONLY_DOWNTIME', 20),
        number_of_tries=getattr(settings, 'REPLICATED_READ_ONLY_TRIES', 1),
    )


# Internal helper function used to access a ReplicationRouter instance(s)
# that Django creates inside its db module.
class Routers(object):
    def __getattr__(self, name):
        for r in db.router.routers:
            if hasattr(r, name):
                return getattr(r, name)
        msg = u'Not found the router with the method "%s".' % name
        raise AttributeError(msg)


routers = Routers()
enable_state_change = partial(routers.set_state_change, True)
disable_state_change = partial(routers.set_state_change, False)


def _use_state(*args, **kwargs):
    warnings.warn(
        'You use a private method _use_state and he is outdated',
        DeprecationWarning
    )

########NEW FILE########
