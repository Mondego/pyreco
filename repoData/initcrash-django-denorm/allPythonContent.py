__FILENAME__ = daemon
#!/usr/bin/env python
#
# $Id: daemon.py 7274 2008-03-05 01:00:09Z bmc $

# NOTE: Documentation is intended to be processed by epydoc and contains
# epydoc markup.

"""
Overview
========

Convert the calling process to a daemon. To make the current Python process
into a daemon process, you need two lines of code::

    import daemon
    daemon.daemonize()

If C{daemonize()} fails for any reason, it throws an exception. It also
logs debug messages, using the standard Python 'logging' package, to
channel 'daemon'.

Adapted from:

  - U{http://www.clapper.org/software/daemonize/}

See Also
========

Stevens, W. Richard. I{Unix Network Programming} (Addison-Wesley, 1990).
"""

__version__ = "1.0.1"
__author__ = "Brian Clapper, bmc@clapper.org"
__url__ = "http://www.clapper.org/software/python/daemon/"
__copyright__ = "(c) 2008 Brian M. Clapper"
__license__ = "BSD-style license"

__all__ = ['daemonize', 'DaemonException']

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import logging
import os
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default daemon parameters.
# File mode creation mask of the daemon.
UMASK = 0

# Default working directory for the daemon.
WORKDIR = "/"

# Default maximum for the number of available file descriptors.
MAXFD = 1024

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
    NULL_DEVICE = os.devnull
else:
    NULL_DEVICE = "/dev/null"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger('daemonize')


# ---------------------------------------------------------------------------
# Public classes
# ---------------------------------------------------------------------------

class DaemonException(Exception):
    """
    Thrown by C{daemonize()} when an error occurs while attempting to create
    a daemon. A C{DaemonException} object always contains a single string
    value that contains an error message describing the problem.
    """
    def __init__(self, errorMessage):
        """
        Create a new C{DaemonException}.

        @type errorMessage:  string
        @param errorMessage: the error message
        """
        self.errorMessage = errorMessage

    def __str__(self):
        """
        Get a string version of the exception.

        @return: a string representing the exception
        """
        return self.errorMessage


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def daemonize(noClose=False, pidfile=None):
    """
    Convert the calling process into a daemon.

    @type noClose:  boolean
    @param noClose: If True, don't close the file descriptors. Useful
                    if the calling process has already redirected file
                    descriptors to an output file. WARNING: Only set this
                    parameter to True if you're SURE there are no open file
                    descriptors to the calling terminal. Otherwise, you'll
                    risk having the daemon re-acquire a control terminal,
                    which can cause it to be killed if someone logs off that
                    terminal.

    @raise DaemonException: Error during daemonizing
    """
    global log

    if os.name != 'posix':
        log.warn('Daemon is only supported on Posix-compliant systems.')
        return

    try:
        # Fork once to go into the background.

        log.debug('Forking first child.')
        pid = _fork()
        if pid != 0:
            # Parent. Exit using os._exit(), which doesn't fire any atexit
            # functions.
            os._exit(0)

        # First child. Create a new session. os.setsid() creates the session
        # and makes this (child) process the process group leader. The process
        # is guaranteed not to have a control terminal.
        log.debug('Creating new session')
        os.setsid()

        # Fork a second child to ensure that the daemon never reacquires
        # a control terminal.
        log.debug('Forking second child.')
        pid = _fork()
        if pid != 0:
            # Original child. Exit.
            if pidfile:
                print pid
                file(pidfile, "w").write(str(pid))
            os._exit(0)

        # This is the second child. Set the umask.
        log.debug('Setting umask')
        os.umask(UMASK)

        # Go to a neutral corner (i.e., the primary file system, so
        # the daemon doesn't prevent some other file system from being
        # unmounted).
        log.debug('Changing working directory to "%s"' % WORKDIR)
        os.chdir(WORKDIR)

        # Unless noClose was specified, close all file descriptors.
        if not noClose:
            log.debug('Redirecting file descriptors')
            _redirectFileDescriptors()

    except DaemonException:
        raise

    except OSError, e:
        raise DaemonException('Error during daemonizing: %s [%d]' %\
              (e.strerror, e.errno))


# ---------------------------------------------------------------------------
# Private functions
# ---------------------------------------------------------------------------

def _fork():
    try:
        return os.fork()
    except OSError, e:
        raise DaemonException('Cannot fork: %s [%d]' % (e.strerror, e.errno))


def _redirectFileDescriptors():
    import resource  # POSIX resource information
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = MAXFD

    # Close all file descriptors.

    for fd in range(0, maxfd):
        # Only close TTYs.
        try:
            os.ttyname(fd)
        except:
            continue

        try:
            os.close(fd)
        except OSError:
            # File descriptor wasn't open. Ignore.
            pass

    # Redirect standard input, output and error to something safe.
    # os.open() is guaranteed to return the lowest available file
    # descriptor (0, or standard input). Then, we can dup that descriptor
    # for standard output and standard error.

    os.open(NULL_DEVICE, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)

# ---------------------------------------------------------------------------
# Main program (for testing)
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    log = logging.getLogger('daemon')
    hdlr = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%T')
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    log.setLevel(logging.DEBUG)

    log.debug('Before daemonizing, PID=%d' % os.getpid())
    daemonize(noClose=True)
    log.debug('After daemonizing, PID=%d' % os.getpid())
    log.debug('Daemon is sleeping for 10 seconds')

    import time
    time.sleep(10)

    log.debug('Daemon exiting')
    sys.exit(0)

########NEW FILE########
__FILENAME__ = base
from django.db import models, connections, connection
from django.contrib.contenttypes.generic import GenericRelation
from django.db.models.related import RelatedObject


class RandomBigInt(object):
    def sql(self):
        raise NotImplementedError


class TriggerNestedSelect:
    def __init__(self, table, columns, **kwargs):
        self.table = table
        self.columns = ", ".join(columns)
        self.kwargs = kwargs

    def sql(self):
        raise NotImplementedError


class TriggerAction(object):
    def __init__(self):
        pass

    def sql(self):
        pass


class TriggerActionInsert(TriggerAction):
    def __init__(self, model, columns, values):
        self.model = model
        self.columns = columns
        self.values = values

    def sql(self):
        raise NotImplementedError


class TriggerActionUpdate(TriggerAction):
    def __init__(self, model, columns, values, where):
        self.model = model
        self.columns = columns
        self.where = where

        self.values = []
        for value in values:
            if hasattr(value, 'sql'):
                self.values.append(value.sql())
            else:
                self.values.append(value)

    def sql(self):
        raise NotImplementedError


class Trigger(object):

    def __init__(self, subject, time, event, actions, content_type, using=None, skip=None):
        self.subject = subject
        self.time = time
        self.event = event
        self.content_type = content_type
        self.content_type_field = None
        self.actions = []
        self.append(actions)
        self.using = using

        if self.using:
            cconnection = connections[self.using]
        else:
            cconnection = connection

        if isinstance(subject, models.ManyToManyField):
            self.model = None
            self.db_table = subject.m2m_db_table()
            self.fields = [(subject.m2m_column_name(), ''), (subject.m2m_reverse_name(), '')]
        elif isinstance(subject, GenericRelation):
            self.model = None
            self.db_table = subject.m2m_db_table()
            self.fields = [(k.attname, k.db_type(connection=cconnection)) for k, v in subject.rel.to._meta.get_fields_with_model() if not v]
            self.content_type_field = subject.content_type_field_name + '_id'
        elif isinstance(subject, models.ForeignKey):
            self.model = subject.model
            self.db_table = self.model._meta.db_table
            skip = skip or ()
            self.fields = [(k.attname, k.db_type(connection=cconnection)) for k,v in self.model._meta.get_fields_with_model() if not v and k.attname not in skip]

        elif hasattr(subject, "_meta"):
            self.model = subject
            self.db_table = self.model._meta.db_table
            # FIXME, need to check get_parent_list and add triggers to those
            # The below will only check the fields on *this* model, not parents
            skip = skip or () + getattr(subject, 'denorm_always_skip', ())
            self.fields = [(k.attname, k.db_type(connection=cconnection)) for k, v in self.model._meta.get_fields_with_model() if not v and k.attname not in skip]
        else:
            raise NotImplementedError

    def append(self, actions):
        if not isinstance(actions, list):
            actions = [actions]

        for action in actions:
            self.actions.append(action)

    def name(self):
        return "_".join([
            "denorm",
            self.time,
            "row",
            self.event,
            "on",
            self.db_table
        ])

    def sql(self):
        raise NotImplementedError


class TriggerSet(object):
    def __init__(self, using=None):
        self.using = using
        self.triggers = {}

    def cursor(self):
        if self.using:
            return connections[self.using].cursor()
        else:
            return connection.cursor()

    def append(self, triggers):
        if not isinstance(triggers, list):
            triggers = [triggers]

        for trigger in triggers:
            name = trigger.name()
            if name in self.triggers:
                self.triggers[name].append(trigger.actions)
            else:
                self.triggers[name] = trigger

    def install(self):
        raise NotImplementedError

    def drop(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = triggers
import random
import string
from denorm.db import base


class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return '(9223372036854775806 * ((RAND()-0.5)*2.0) )'


class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ",".join(self.columns) + ")"
        params = []
        if isinstance(self.values, TriggerNestedSelect):
            sql, nested_params = self.values.sql()
            values = "(" + sql + ")"
            params.extend(nested_params)
        else:
            values = "VALUES(" + ",".join(self.values) + ")"

        return 'INSERT IGNORE INTO %(table)s %(columns)s %(values)s' % locals(), tuple()


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ','.join(["%s=%s" % (k, v) for k,  v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []

        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), tuple(where_params)

class Trigger(base.Trigger):

    def sql(self):
        name = self.name()
        if len(name) > 50:
            name = name[:45] + ''.join(
                random.choice(string.ascii_uppercase + string.digits)
                for x in range(5)
            )
        params = []
        action_list = []
        for a in self.actions:
            sql, action_params = a.sql()
            if sql:
                action_list.append(sql)
                params.extend(action_params)

        # FIXME: actions should depend on content_type and content_type_field, if applicable
        # now we flag too many things dirty, e.g. a change for ('forum', 1) also flags ('post', 1)
        actions = ";\n   ".join(action_list) + ';'
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()

        if event == "UPDATE":
            conditions = list()
            for field, native_type in self.fields:
                # TODO: find out if we need to compare some fields as text like in postgres
                conditions.append("(NOT( OLD.%(f)s <=> NEW.%(f)s ))" % {'f': field})

            cond = "(%s)" % "OR".join(conditions)
        else:
            cond = 'TRUE'

        sql = """
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW BEGIN
        IF %(cond)s THEN
            %(actions)s
        END IF;
    END;
""" % locals()
        return sql, tuple(params)

class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()

        # FIXME: according to MySQL docs the LIKE statement should work
        # but it doesn't. MySQL reports a Syntax Error
        #cursor.execute(r"SHOW TRIGGERS WHERE Trigger LIKE 'denorm_%%'")
        cursor.execute('SHOW TRIGGERS')
        for result in cursor.fetchall():
            if result[0].startswith('denorm_'):
                cursor.execute('DROP TRIGGER %s;' % result[0])

    def install(self):
        cursor = self.cursor()
        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)

########NEW FILE########
__FILENAME__ = triggers
from django.db import transaction
from denorm.db import base


class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return '(9223372036854775806::INT8 * ((RANDOM()-0.5)*2.0) )::INT8'


class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ",".join(self.columns) + ")"
        params = []
        if isinstance(self.values, TriggerNestedSelect):
            sql, nested_params = self.values.sql()
            values = "(" + sql + ")"
            params.extend(nested_params)
        else:
            values = "VALUES(" + ",".join(self.values) + ")"

        sql = (
            'BEGIN\n'
            'INSERT INTO %(table)s %(columns)s %(values)s;\n'
            'EXCEPTION WHEN unique_violation THEN  -- do nothing\n'
            'END\n'
        ) % locals()
        return sql, params

class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        params = []
        updates = ','.join(["%s=%s" % (k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []
        params.extend(where_params)
        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), params

class Trigger(base.Trigger):
    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self):
        name = self.name()
        params = []
        action_list = []
        for a in self.actions:
            sql, action_params = a.sql()
            if sql:
                action_list.append(sql)
                params.extend(action_params)
        actions = ";\n   ".join(action_list) + ';'
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()
        content_type = self.content_type
        ct_field = self.content_type_field

        conditions = []

        if event == "UPDATE":
            for field, native_type in self.fields:
                if native_type is None:
                    # If Django didn't know what this field type should be
                    # then compare it as text - Fixes a problem of trying to
                    # compare PostGIS geometry fields.
                    conditions.append("(OLD.%(f)s::%(t)s IS DISTINCT FROM NEW.%(f)s::%(t)s)" % {'f': field, 't': 'text'})
                else:
                    conditions.append("( OLD.%(f)s IS DISTINCT FROM NEW.%(f)s )" % {'f': field})

            conditions = ["(%s)" % "OR".join(conditions)]

        if ct_field:
            if event == "UPDATE":
                conditions.append("(OLD.%(ctf)s=%(ct)s)OR(NEW.%(ctf)s=%(ct)s)" % {'ctf': ct_field, 'ct': content_type})
            elif event == "INSERT":
                conditions.append("(NEW.%s=%s)" % (ct_field, content_type))
            elif event == "DELETE":
                conditions.append("(OLD.%s=%s)" % (ct_field, content_type))

        if not conditions:
            cond = "TRUE"
        else:
            cond = "AND".join(conditions)

        sql = """
CREATE OR REPLACE FUNCTION func_%(name)s()
    RETURNS TRIGGER AS $$
    BEGIN
        IF %(cond)s THEN
            %(actions)s
        END IF;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW EXECUTE PROCEDURE func_%(name)s();
""" % locals()
        return sql, params


class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()
        cursor.execute("SELECT pg_class.relname, pg_trigger.tgname FROM pg_trigger LEFT JOIN pg_class ON (pg_trigger.tgrelid = pg_class.oid) WHERE pg_trigger.tgname LIKE 'denorm_%%';")
        for table_name, trigger_name in cursor.fetchall():
            cursor.execute('DROP TRIGGER %s ON %s;' % (trigger_name, table_name))
            transaction.commit_unless_managed(using=self.using)

    def install(self):
        cursor = self.cursor()
        cursor.execute("SELECT lanname FROM pg_catalog.pg_language WHERE lanname ='plpgsql'")
        if not cursor.fetchall():
            cursor.execute('CREATE LANGUAGE plpgsql')
        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)
            transaction.commit_unless_managed(using=self.using)

########NEW FILE########
__FILENAME__ = triggers
from django.db import transaction
from denorm.db import base


import logging

logger = logging.getLogger('denorm-sqlite')

class RandomBigInt(base.RandomBigInt):
    def sql(self):
        return 'RANDOM()'


class TriggerNestedSelect(base.TriggerNestedSelect):

    def sql(self):
        columns = self.columns
        table = self.table
        where = ",".join(["%s = %s" % (k, v) for k, v in self.kwargs.iteritems()])
        return 'SELECT DISTINCT %(columns)s FROM %(table)s WHERE %(where)s' % locals(), tuple()


class TriggerActionInsert(base.TriggerActionInsert):

    def sql(self):
        table = self.model._meta.db_table
        columns = "(" + ",".join(self.columns) + ")"
        if isinstance(self.values, TriggerNestedSelect):
            sql, params = self.values.sql()
            values = ""+ sql +""
        else:
            values = "VALUES(" + ",".join(self.values) + ")"
            params = []

        return 'INSERT OR REPLACE INTO %(table)s %(columns)s %(values)s' % locals(), tuple(params)


class TriggerActionUpdate(base.TriggerActionUpdate):

    def sql(self):
        table = self.model._meta.db_table
        updates = ','.join(["%s=%s"%(k, v) for k, v in zip(self.columns, self.values)])
        if isinstance(self.where, tuple):
            where, where_params = self.where
        else:
            where, where_params = self.where, []

        return 'UPDATE %(table)s SET %(updates)s WHERE %(where)s' % locals(), where_params


class Trigger(base.Trigger):

    def name(self):
        name = base.Trigger.name(self)
        if self.content_type_field:
            name += "_%s" % self.content_type
        return name

    def sql(self):
        name = self.name()
        params = []
        action_list = []
        for a in self.actions:
            sql, action_params = a.sql()
            if sql:
                action_list.append(sql)
                params.extend(action_params)
        actions = ";\n   ".join(action_list) + ';'
        table = self.db_table
        time = self.time.upper()
        event = self.event.upper()
        content_type = self.content_type
        ct_field = self.content_type_field

        when = []
        if event == "UPDATE":
            when.append("(" + "OR".join(["(OLD.%s IS NOT NEW.%s)" % (f, f) for f, t in self.fields]) + ")")
        if ct_field:
            if event == "DELETE":
                when.append("(OLD.%s==%s)" % (ct_field, content_type))
            elif event == "INSERT":
                when.append("(NEW.%s==%s)" % (ct_field, content_type))
            elif event == "UPDATE":
                when.append("((OLD.%(ctf)s==%(ct)s)OR(NEW.%(ctf)s==%(ct)s))" % {'ctf': ct_field, 'ct': content_type})

        when = "AND".join(when)
        if when:
            when = "WHEN(%s)" % (when,)

        return """
CREATE TRIGGER %(name)s
    %(time)s %(event)s ON %(table)s
    FOR EACH ROW %(when)s BEGIN
        %(actions)s
    END;
""" % locals(), tuple(params)


class TriggerSet(base.TriggerSet):
    def drop(self):
        cursor = self.cursor()

        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'denorm_%%';")
        for trigger_name, table_name in cursor.fetchall():
            cursor.execute("DROP TRIGGER %s;" % (trigger_name,))
            transaction.commit_unless_managed(using=self.using)

    def install(self):
        cursor = self.cursor()

        for name, trigger in self.triggers.iteritems():
            sql, args = trigger.sql()
            cursor.execute(sql, args)
            transaction.commit_unless_managed(using=self.using)

########NEW FILE########
__FILENAME__ = denorms
# -*- coding: utf-8 -*-
import abc

from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers
from django.db import connection
from django.db.models import sql, ManyToManyField
from django.db.models.aggregates import Sum
from django.db.models.fields.related import ManyToManyField
from django.db.models.manager import Manager
from denorm.models import DirtyInstance

# remember all denormalizations.
# this is used to rebuild all denormalized values in the whole DB
from django.db.models.query_utils import Q
from django.db.models.sql import Query
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import JoinInfo
from django.db.models.sql.query import Query
from django.db.models.sql.where import WhereNode

# Remember all denormalizations.
# This is used to rebuild all denormalized values in the whole DB.
alldenorms = []


def many_to_many_pre_save(sender, instance, **kwargs):
    """
    Updates denormalised many-to-many fields for the model
    """
    if instance.pk:
        # Need a primary key to do m2m stuff
        for m2m in sender._meta.local_many_to_many:
            # This gets us all m2m fields, so limit it to just those that are denormed
            if hasattr(m2m, 'denorm'):
                # Does some extra jiggery-pokery for "through" m2m models.
                # May not work under lots of conditions.
                if hasattr(m2m.rel, 'through_model'):
                    # Clear exisiting through records (bit heavy handed?)
                    kwargs = {m2m.related.var_name: instance}

                    # Can't use m2m_column_name in a filter
                    # kwargs = { m2m.m2m_column_name(): instance.pk, }
                    m2m.rel.through_model.objects.filter(**kwargs).delete()

                    values = m2m.denorm.func(instance)
                    for value in values:
                        kwargs.update({m2m.m2m_reverse_name(): value.pk})
                        m2m.rel.through_model.objects.create(**kwargs)

                else:
                    values = m2m.denorm.func(instance)
                    setattr(instance, m2m.attname, values)


def many_to_many_post_save(sender, instance, created, **kwargs):
    if created:
        def check_resave():
            for m2m in sender._meta.local_many_to_many:
                if hasattr(m2m, 'denorm'):
                    return True
            return False

        if check_resave():
            instance.save()


class Denorm(object):
    def __init__(self, skip=None):
        self.func = None
        self.skip = skip

    def setup(self, **kwargs):
        """
        Adds 'self' to the global denorm list
        and connects all needed signals.
        """
        global alldenorms
        if self not in alldenorms:
            alldenorms.append(self)

    def update(self, qs):
        """
        Updates the denormalizations in all instances in the queryset 'qs'.
        """
        for instance in qs.distinct().iterator():
            # only write new values to the DB if they actually changed
            new_value = self.func(instance)

            # Get attribute name (required for denormalising ForeignKeys)
            attname = instance._meta.get_field(self.fieldname).attname

            if isinstance(getattr(instance, attname), Manager):
                # for a many to many field the decorated
                # function should return a list of either model instances
                # or primary keys
                old_pks = set([x.pk for x in getattr(instance, attname).all()])
                new_pks = set([])

                for x in new_value:
                    # we need to compare sets of objects based on pk values,
                    # as django lacks an identity map.
                    if hasattr(x,'pk'):
                        new_pks.add(x.pk)
                    else:
                        new_pks.add(x)

                if old_pks != new_pks:
                    print old_pks
                    for o in qs.filter(pk=instance.pk):
                        o.attname = new_value
                    instance.save()

            elif not getattr(instance, attname) == new_value:
                setattr(instance, attname, new_value)
                # an update before the save is needed to handle CountFields
                # CountField does not update its value during pre_save
                qs.filter(pk=instance.pk).update(**{self.fieldname: new_value})
                instance.save()
        flush()

    def get_triggers(self, using):
        return []


class BaseCallbackDenorm(Denorm):
    """
    Handles the denormalization of one field, using a python function
    as a callback.
    """

    def setup(self, **kwargs):
        """
        Calls setup() on all DenormDependency resolvers
        """
        super(BaseCallbackDenorm, self).setup(**kwargs)

        for dependency in self.depend:
            dependency.setup(self.model)

    def get_triggers(self, using):
        """
        Creates a list of all triggers needed to keep track of changes
        to fields this denorm depends on.
        """
        trigger_list = list()

        # Get the triggers of all DenormDependency instances attached
        # to our callback.
        for dependency in self.depend:
            trigger_list += dependency.get_triggers(using=using)

        return trigger_list + super(BaseCallbackDenorm, self).get_triggers(using=using)


class CallbackDenorm(BaseCallbackDenorm):
    """
    As above, but with extra triggers on self as described below
    """

    def get_triggers(self, using):
        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        # Create a trigger that marks any updated or newly created
        # instance of the model containing the denormalized field
        # as dirty.
        # This is only really needed if the instance was changed without
        # using the ORM or if it was part of a bulk update.
        # In those cases the self_save_handler won't get called by the
        # pre_save signal, so we need to ensure flush() does this later.
        action = triggers.TriggerActionInsert(
            model=DirtyInstance,
            columns=("content_type_id", "object_id"),
            values=(content_type, "NEW.%s" % self.model._meta.pk.get_attname_column()[1])
        )
        trigger_list = [
            triggers.Trigger(self.model, "after", "update", [action], content_type, using, self.skip),
            triggers.Trigger(self.model, "after", "insert", [action], content_type, using, self.skip),
        ]

        return trigger_list + super(CallbackDenorm, self).get_triggers(using=using)


class BaseCacheKeyDenorm(Denorm):
    def __init__(self, depend_on_related, *args, **kwargs):
        self.depend = depend_on_related
        super(BaseCacheKeyDenorm, self).__init__(*args, **kwargs)
        import random
        self.func = lambda o: random.randint(-9223372036854775808, 9223372036854775807)

    def setup(self, **kwargs):
        """
        Calls setup() on all DenormDependency resolvers
        """
        super(BaseCacheKeyDenorm, self).setup(**kwargs)

        for dependency in self.depend:
            dependency.setup(self.model)

    def get_triggers(self, using):
        """
        Creates a list of all triggers needed to keep track of changes
        to fields this denorm depends on.
        """
        trigger_list = list()

        # Get the triggers of all DenormDependency instances attached
        # to our callback.
        for dependency in self.depend:
            trigger_list += dependency.get_triggers(using=using)

        return trigger_list + super(BaseCacheKeyDenorm, self).get_triggers(using=using)


class CacheKeyDenorm(BaseCacheKeyDenorm):
    """
    As above, but with extra triggers on self as described below
    """

    def get_triggers(self, using):
        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        # This is only really needed if the instance was changed without
        # using the ORM or if it was part of a bulk update.
        # In those cases the self_save_handler won't get called by the
        # pre_save signal
        action = triggers.TriggerActionUpdate(
            model=self.model,
            columns=(self.fieldname,),
            values=(triggers.RandomBigInt(),),
            where="%s=NEW.%s" % ((self.model._meta.pk.get_attname_column()[1],) * 2),
        )
        trigger_list = [
            triggers.Trigger(self.model, "after", "update", [action], content_type, using, self.skip),
            triggers.Trigger(self.model, "after", "insert", [action], content_type, using, self.skip),
        ]

        return trigger_list + super(CacheKeyDenorm, self).get_triggers(using=using)


class TriggerWhereNode(WhereNode):
    def sql_for_columns(self, data, qn, connection):
        """
        Returns the SQL fragment used for the left-hand side of a column
        constraint (for example, the "T1.foo" portion in the clause
        "WHERE ... T1.foo = 6").
        """
        table_alias, name, db_type = data
        if table_alias:
            if table_alias in ('NEW', 'OLD'):
                lhs = '%s.%s' % (table_alias, qn(name))
            else:
                lhs = '%s.%s' % (qn(table_alias), qn(name))
        else:
            lhs = qn(name)
        return connection.ops.field_cast_sql(db_type) % lhs


class TriggerFilterQuery(sql.Query):
    def __init__(self, model, trigger_alias, where=TriggerWhereNode):
        super(TriggerFilterQuery, self).__init__(model, where)
        self.trigger_alias = trigger_alias

    def get_initial_alias(self):
        return self.trigger_alias

class AggregateDenorm(Denorm):
    __metaclass__ = abc.ABCMeta

    def __init__(self, skip=None):
        self.manager = None
        self.skip = skip

    def setup(self, sender, **kwargs):
        # as we connected to the ``class_prepared`` signal for any sender
        # and we only need to setup once, check if the sender is our model.
        if sender is self.model:
            super(AggregateDenorm, self).setup(sender=sender, **kwargs)

        # related managers will only be available after both models are initialized
        # so check if its available already, and get our manager
        if not self.manager and hasattr(self.model, self.manager_name):
            self.manager = getattr(self.model, self.manager_name)

    def get_related_where(self, fk_name, using, type):
        related_where = ["%s=%s.%s" % (self.model._meta.pk.get_attname_column()[1], type, fk_name)]
        related_query = Query(self.manager.related.model)
        for name, value in self.filter.iteritems():
            related_query.add_q(Q(**{name: value}))
        for name, value in self.exclude.iteritems():
            related_query.add_q(~Q(**{name: value}))
        related_query.add_extra(None, None,
            ["%s=%s.%s" % (self.model._meta.pk.get_attname_column()[1], type, self.manager.related.field.m2m_column_name())],
            None, None, None)
        related_query.add_count_column()
        related_query.clear_ordering(force_empty=True)
        related_query.default_cols = False
        related_filter_where, related_where_params = related_query.get_compiler(using=using,
            connection=connection).as_sql()
        if related_filter_where is not None:
            related_where.append('(' + related_filter_where + ') > 0')
        return related_where, related_where_params

    def m2m_triggers(self, content_type, fk_name, related_field, using):
        """
        Returns triggers for m2m relation
        """
        related_inc_where, _ = self.get_related_where(fk_name, using, 'NEW')
        related_dec_where, related_where_params = self.get_related_where(fk_name, using, 'OLD')
        related_increment = triggers.TriggerActionUpdate(
            model=self.model,
            columns=(self.fieldname,),
            values=(self.get_related_increment_value(),),
            where=(' AND '.join(related_inc_where), related_where_params),
        )
        related_decrement = triggers.TriggerActionUpdate(
            model=self.model,
            columns=(self.fieldname,),
            values=(self.get_related_decrement_value(),),
            where=(' AND '.join(related_dec_where), related_where_params),
        )
        trigger_list = [
            triggers.Trigger(related_field, "after", "update", [related_increment, related_decrement], content_type,
                using,
                self.skip),
            triggers.Trigger(related_field, "after", "insert", [related_increment], content_type, using, self.skip),
            triggers.Trigger(related_field, "after", "delete", [related_decrement], content_type, using, self.skip),
            ]
        return trigger_list

    def get_triggers(self, using):
        related_field = self.manager.related.field
        if isinstance(related_field, ManyToManyField):
            fk_name = related_field.m2m_reverse_name()
            inc_where = ["%(id)s IN (SELECT %(reverse_related)s FROM %(m2m_table)s WHERE %(related)s=NEW.%(id)s)" % {
                'id': self.model._meta.pk.get_attname_column()[0],
                'related': related_field.m2m_column_name(),
                'm2m_table': related_field.m2m_db_table(),
                'reverse_related': fk_name,
                }]
            dec_where = [action.replace('NEW.', 'OLD.') for action in inc_where]
        else:
            fk_name = related_field.attname
            inc_where = ["%s=NEW.%s" % (self.model._meta.pk.get_attname_column()[1], fk_name)]
            dec_where = ["%s=OLD.%s" % (self.model._meta.pk.get_attname_column()[1], fk_name)]

        content_type = str(ContentType.objects.get_for_model(self.model).pk)

        inc_query = TriggerFilterQuery(self.manager.related.model, trigger_alias='NEW')
        inc_query.add_q(Q(**self.filter))
        inc_query.add_q(~Q(**self.exclude))
        inc_filter_where, _ = inc_query.where.as_sql(SQLCompiler(inc_query, connection, using).quote_name_unless_alias,
            connection)
        dec_query = TriggerFilterQuery(self.manager.related.model, trigger_alias='OLD')
        dec_query.add_q(Q(**self.filter))
        dec_query.add_q(~Q(**self.exclude))
        dec_filter_where, where_params = dec_query.where.as_sql(
            SQLCompiler(dec_query, connection, using).quote_name_unless_alias, connection)

        if inc_filter_where:
            inc_where.append(inc_filter_where)
        if dec_filter_where:
            dec_where.append(dec_filter_where)
            # create the triggers for the incremental updates
        increment = triggers.TriggerActionUpdate(
            model=self.model,
            columns=(self.fieldname,),
            values=(self.get_increment_value(),),
            where=(' AND '.join(inc_where), where_params),
        )
        decrement = triggers.TriggerActionUpdate(
            model=self.model,
            columns=(self.fieldname,),
            values=(self.get_decrement_value(),),
            where=(' AND '.join(dec_where), where_params),
        )

        other_model = self.manager.related.model
        trigger_list = [
            triggers.Trigger(other_model, "after", "update", [increment, decrement], content_type, using, self.skip),
            triggers.Trigger(other_model, "after", "insert", [increment], content_type, using, self.skip),
            triggers.Trigger(other_model, "after", "delete", [decrement], content_type, using, self.skip),
            ]
        if isinstance(related_field, ManyToManyField):
            trigger_list.extend(self.m2m_triggers(content_type, fk_name, related_field, using))
        return trigger_list

    @abc.abstractmethod
    def get_increment_value(self):
        """
        Returns SQL for incrementing value
        """

    @abc.abstractmethod
    def get_decrement_value(self):
        """
        Returns SQL for decrementing value
        """

class SumDenorm(AggregateDenorm):
    """
    Handles denormalization of a sum field by doing incrementally updates.
    """
    def __init__(self, skip=None, field = None):
        super(SumDenorm, self).__init__(skip)
        # in case we want to set the value without relying on the
        # correctness of the incremental updates we create a function that
        # calculates it from scratch.
        self.sum_field = field
        self.func = lambda obj: (getattr(obj, self.manager_name).filter(**self.filter).exclude(**self.exclude).aggregate(Sum(self.sum_field)).values()[0] or 0)

    def get_increment_value(self):
        return "%s+NEW.%s" % (self.fieldname, self.sum_field)

    def get_decrement_value(self):
        return "%s-OLD.%s" % (self.fieldname, self.sum_field)

    def get_related_increment_value(self):
        related_query = Query(self.manager.related.model)
        related_query.add_extra(None, None,
            ["%s=%s.%s" % (self.model._meta.pk.get_attname_column()[1], 'NEW', self.manager.related.field.m2m_column_name())],
                                None, None, None)
        related_query.add_fields([self.fieldname])
        related_query.clear_ordering(force_empty=True)
        related_query.default_cols = False
        related_filter_where, related_where_params = related_query.get_compiler(connection=connection).as_sql()
        return "%s + (%s)" % (self.fieldname, related_filter_where)

    def get_related_decrement_value(self):
        related_query = Query(self.manager.related.model)
        related_query.add_extra(None, None,
            ["%s=%s.%s" % (self.model._meta.pk.get_attname_column()[1], 'OLD', self.manager.related.field.m2m_column_name())],
                                None, None, None)
        related_query.add_fields([self.fieldname])
        related_query.clear_ordering(force_empty=True)
        related_query.default_cols = False
        related_filter_where, related_where_params = related_query.get_compiler(connection=connection).as_sql()
        return "%s - (%s)" % (self.fieldname, related_filter_where)

class CountDenorm(AggregateDenorm):
    """
    Handles the denormalization of a count field by doing incrementally
    updates.
    """

    def __init__(self, skip=None):
        super(CountDenorm, self).__init__(skip)
        # in case we want to set the value without relying on the
        # correctness of the incremental updates we create a function that
        # calculates it from scratch.
        self.func = lambda obj: getattr(obj, self.manager_name).filter(**self.filter).exclude(**self.exclude).count()

    def get_increment_value(self):
        return "%s+1" % self.fieldname

    def get_decrement_value(self):
        return "%s-1" % self.fieldname

    def get_related_increment_value(self):
        return self.get_increment_value()

    def get_related_decrement_value(self):
        return self.get_decrement_value()


def rebuildall(verbose=False, model_name=None):
    """
    Updates all models containing denormalized fields.
    Used by the 'denormalize' management command.
    """
    global alldenorms
    for i, denorm in enumerate(alldenorms):
        if model_name is None or denorm.model.__name__ == model_name:
            if verbose:
                print 'rebuilding', '%s/%s' % (i + 1, len(alldenorms)), denorm.fieldname, 'in', denorm.model
            denorm.update(denorm.model.objects.all())


def drop_triggers(using=None):
    triggerset = triggers.TriggerSet(using=using)
    triggerset.drop()


def install_triggers(using=None):
    """
    Installs all required triggers in the database
    """
    build_triggerset(using=using).install()


def build_triggerset(using=None):
    global alldenorms

    # Use a TriggerSet to ensure each event gets just one trigger
    triggerset = triggers.TriggerSet(using=using)
    for denorm in alldenorms:
        triggerset.append(denorm.get_triggers(using=using))
    return triggerset


def flush():
    """
    Updates all model instances marked as dirty by the DirtyInstance
    model.
    After this method finishes the DirtyInstance table is empty and
    all denormalized fields have consistent data.
    """

    # Loop until break.
    # We may need multiple passes, because an update on one instance
    # may cause an other instance to be marked dirty (dependency chains)
    while True:
        # Get all dirty markers
        qs = DirtyInstance.objects.all()

        # DirtyInstance table is empty -> all data is consistent -> we're done
        if not qs:
            break

        # Call save() on all dirty instances, causing the self_save_handler()
        # getting called by the pre_save signal.
        for dirty_instance in qs.iterator():
            if dirty_instance.content_object:
                dirty_instance.content_object.save()
            dirty_instance.delete()

########NEW FILE########
__FILENAME__ = dependencies
# -*- coding: utf-8 -*-
from denorm.helpers import find_fks, find_m2ms
from django.db import models
from django.db.models.fields import related
from denorm.models import DirtyInstance
from django.contrib.contenttypes.models import ContentType
from denorm.db import triggers


class DenormDependency(object):

    """
    Base class for real dependency classes.
    """

    def get_triggers(self, using):
        """
        Must return a list of ``denorm.triggers.Trigger`` instances
        """
        return []

    def setup(self, this_model):
        """
        Remembers the model this dependency was declared in.
        """
        self.this_model = this_model


class DependOnRelated(DenormDependency):
    def __init__(self, othermodel, foreign_key=None, type=None, skip=None):
        self.other_model = othermodel
        self.fk_name = foreign_key
        self.type = type
        self.skip = skip or () + getattr(othermodel, 'denorm_always_skip', ())

    def setup(self, this_model):
        super(DependOnRelated, self).setup(this_model)

        # FIXME: this should not be necessary
        if self.other_model == related.RECURSIVE_RELATIONSHIP_CONSTANT:
            self.other_model = self.this_model

        if isinstance(self.other_model, (str, unicode)):
            # if ``other_model`` is a string, it certainly is a lazy relation.
            related.add_lazy_relation(self.this_model, None, self.other_model, self.resolved_model)
        else:
            # otherwise it can be resolved directly
            self.resolved_model(None, self.other_model, None)

    def resolved_model(self, data, model, cls):
        """
        Does all the initialization that had to wait until we knew which
        model we depend on.
        """
        self.other_model = model

        # Create a list of all ForeignKeys and ManyToManyFields between both related models, in both directions
        candidates = [('forward', fk) for fk in find_fks(self.this_model, self.other_model, self.fk_name)]
        candidates += [('backward', fk) for fk in find_fks(self.other_model, self.this_model, self.fk_name)]
        candidates += [('forward_m2m', fk) for fk in find_m2ms(self.this_model, self.other_model, self.fk_name)]
        candidates += [('backward_m2m', fk) for fk in find_m2ms(self.other_model, self.this_model, self.fk_name)]

        # If a relation type was given (forward,backward,forward_m2m or backward_m2m),
        # filter out all relations that do not match this type.
        candidates = [x for x in candidates if not self.type or self.type == x[0]]

        if len(candidates) > 1:
            raise ValueError("%s has more than one ForeignKey or ManyToManyField to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))
        if not candidates:
            raise ValueError("%s has no ForeignKeys or ManyToManyFields to %s (or reverse); cannot auto-resolve."
                             % (self.this_model, self.other_model))

        # Now the candidates list contains exactly one item, thats our winner.
        self.type, self.field = candidates[0]


class CacheKeyDependOnRelated(DependOnRelated):

    def get_triggers(self, using):

        if not self.type:
            # 'resolved_model' model never got called...
            raise ValueError("The model '%s' could not be resolved, it probably does not exist" % self.other_model)

        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            action_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % (
                    self.field.get_attname_column()[1],
                    self.other_model._meta.pk.get_attname_column()[1],
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.field.get_attname_column()[1],
                    self.other_model._meta.pk.get_attname_column()[1],
                ),
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    self.field.get_attname_column()[1],
                ),
            )
            action_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    self.field.get_attname_column()[1],
                ),
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if "forward" in self.type:
                column_name = self.field.m2m_column_name()
                reverse_column_name = self.field.m2m_reverse_name()
            if "backward" in self.type:
                column_name = self.field.m2m_reverse_name()
                reverse_column_name = self.field.m2m_column_name()

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=NEW.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    column_name,
                ),
            )
            action_m2m_old = triggers.TriggerActionUpdate(
                model=self.this_model,
                columns=(self.fieldname,),
                values=(triggers.RandomBigInt(),),
                where="%s=OLD.%s" % (
                    self.this_model._meta.pk.get_attname_column()[1],
                    column_name,
                ),
            )

            trigger_list = [
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using, self.skip),
            ]

            if isinstance(self.field, models.ManyToManyField):
                # Additionally to the dependency on the intermediate table
                # ``this_model`` is dependant on updates to the ``other_model``-
                # There is no need to track insert or delete events here,
                # because a relation can only be created or deleted by
                # by modifying the intermediate table.
                #
                # Generic relations are excluded because they have the
                # same m2m_table and model table.
                sql, params = triggers.TriggerNestedSelect(
                    self.field.m2m_db_table(),
                    (column_name,),
                    **{reverse_column_name: "NEW.id"}
                ).sql()
                action_new = triggers.TriggerActionUpdate(
                    model=self.this_model,
                    columns=(self.fieldname,),
                    values=(triggers.RandomBigInt(),),
                    where=(self.this_model._meta.pk.get_attname_column()[1]+' IN ('+ sql +')', params),
                )
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip))

            return trigger_list

        return []


class CallbackDependOnRelated(DependOnRelated):

    """
    A DenormDependency that handles callbacks depending on fields
    in other models that are related to the dependent model.

    Two models are considered related if there is a ForeignKey or ManyToManyField
    on either of them pointing to the other one.
    """

    def __init__(self, othermodel, foreign_key=None, type=None, skip=None):
        """
        Attaches a dependency to a callable, indicating the return value depends on
        fields in an other model that is related to the model the callable belongs to
        either through a ForeignKey in either direction or a ManyToManyField.

        **Arguments:**

        othermodel (required)
            Either a model class or a string naming a model class.

        foreign_key
            The name of the ForeignKey or ManyToManyField that creates the relation
            between the two models.
            Only necessary if there is more than one relationship between the two models.

        type
            One of 'forward', 'backward', 'forward_m2m' or 'backward_m2m'.
            If there are relations in both directions specify which one to use.

        skip
            Use this to specify what fields change on every save().
            These fields will not be checked and will not make a model dirty when they change, to prevent infinite loops.
        """
        super(CallbackDependOnRelated, self).__init__(othermodel, foreign_key, type, skip)

    def get_triggers(self, using):

        if not self.type:
            # 'resolved_model' model never got called...
            raise ValueError("The model '%s' could not be resolved, it probably does not exist" % self.other_model)

        content_type = str(ContentType.objects.get_for_model(self.this_model).id)

        if self.type == "forward":
            # With forward relations many instances of ``this_model``
            # may be related to one instance of ``other_model``
            # so we need to do a nested select query in the trigger
            # to find them all.
            action_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,
                        self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "NEW.%s" % self.other_model._meta.pk.get_attname_column()[1]}
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=triggers.TriggerNestedSelect(
                    self.this_model._meta.db_table,
                    (content_type,
                        self.this_model._meta.pk.get_attname_column()[1]),
                    **{self.field.get_attname_column()[1]: "OLD.%s" % self.other_model._meta.pk.get_attname_column()[1]}
                )
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if self.type == "backward":
            # With backward relations a change in ``other_model`` can affect
            # only one or two instances of ``this_model``.
            # If the ``other_model`` instance changes the value its ForeignKey
            # pointing to ``this_model`` both the old and the new related instance
            # are affected, otherwise only the one it is pointing to is affected.
            action_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "NEW.%s" % self.field.get_attname_column()[1],
                )
            )
            action_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % self.field.get_attname_column()[1],
                )
            )
            return [
                triggers.Trigger(self.other_model, "after", "update", [action_new, action_old], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "insert", [action_new], content_type, using, self.skip),
                triggers.Trigger(self.other_model, "after", "delete", [action_old], content_type, using, self.skip),
            ]

        if "m2m" in self.type:
            # The two directions of M2M relations only differ in the column
            # names used in the intermediate table.
            if "forward" in self.type:
                column_name = self.field.m2m_column_name()
                reverse_column_name = self.field.m2m_reverse_name()
            if "backward" in self.type:
                column_name = self.field.m2m_reverse_name()
                reverse_column_name = self.field.m2m_column_name()

            # The first part of a M2M dependency is exactly like a backward
            # ForeignKey dependency. ``this_model`` is backward FK related
            # to the intermediate table.
            action_m2m_new = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "NEW.%s" % column_name,
                )
            )
            action_m2m_old = triggers.TriggerActionInsert(
                model=DirtyInstance,
                columns=("content_type_id", "object_id"),
                values=(
                    content_type,
                    "OLD.%s" % column_name,
                )
            )

            trigger_list = [
                triggers.Trigger(self.field, "after", "update", [action_m2m_new, action_m2m_old], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "insert", [action_m2m_new], content_type, using, self.skip),
                triggers.Trigger(self.field, "after", "delete", [action_m2m_old], content_type, using, self.skip),
            ]

            if isinstance(self.field, models.ManyToManyField):
                # Additionally to the dependency on the intermediate table
                # ``this_model`` is dependant on updates to the ``other_model``-
                # There is no need to track insert or delete events here,
                # because a relation can only be created or deleted by
                # by modifying the intermediate table.
                #
                # Generic relations are excluded because they have the
                # same m2m_table and model table.
                action_new = triggers.TriggerActionInsert(
                    model=DirtyInstance,
                    columns=("content_type_id", "object_id"),
                    values=triggers.TriggerNestedSelect(
                        self.field.m2m_db_table(),
                        (content_type, column_name),
                        **{reverse_column_name: "NEW.id"}
                        )
                    )
                trigger_list.append(triggers.Trigger(self.other_model, "after", "update", [action_new], content_type, using, self.skip))

            return trigger_list

        return []


def make_depend_decorator(Class):
    """
    Create a decorator that attaches an instance of the given class
    to the decorated function, passing all remaining arguments to the classes
    __init__.
    """
    import functools

    def decorator(*args, **kwargs):
        def deco(func):
            if not hasattr(func, 'depend'):
                func.depend = []
            func.depend.append((Class, args, kwargs))
            return func
        return deco
    functools.update_wrapper(decorator, Class.__init__)
    return decorator

depend_on_related = make_depend_decorator(CallbackDependOnRelated)

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
import denorm.denorms
from django.db import models
from denorm import denorms
from django.conf import settings
import django.db.models

def denormalized(DBField, *args, **kwargs):
    """
    Turns a callable into model field, analogous to python's ``@property`` decorator.
    The callable will be used to compute the value of the field every time the model
    gets saved.
    If the callable has dependency information attached to it the fields value will
    also be recomputed if the dependencies require it.

    **Arguments:**

    DBField (required)
        The type of field you want to use to save the data.
        Note that you have to use the field class and not an instance
        of it.

    \*args, \*\*kwargs:
        Those will be passed unaltered into the constructor of ``DBField``
        once it gets actually created.
    """

    class DenormDBField(DBField):

        """
        Special subclass of the given DBField type, with a few extra additions.
        """

        def __init__(self, func, *args, **kwargs):
            self.func = func
            self.skip = kwargs.pop('skip', None)
            kwargs['editable'] = False
            DBField.__init__(self, *args, **kwargs)

        def contribute_to_class(self, cls, name, *args, **kwargs):
            if hasattr(settings, 'DENORM_BULK_UNSAFE_TRIGGERS') and settings.DENORM_BULK_UNSAFE_TRIGGERS:
                self.denorm = denorms.BaseCallbackDenorm(skip=self.skip)
            else:
                self.denorm = denorms.CallbackDenorm(skip=self.skip)
            self.denorm.func = self.func
            self.denorm.depend = [dcls(*dargs, **dkwargs) for (dcls, dargs, dkwargs) in getattr(self.func, 'depend', [])]
            self.denorm.model = cls
            self.denorm.fieldname = name
            self.field_args = (args, kwargs)
            models.signals.class_prepared.connect(self.denorm.setup, sender=cls)
            # Add The many to many signal for this class
            models.signals.pre_save.connect(denorms.many_to_many_pre_save, sender=cls)
            models.signals.post_save.connect(denorms.many_to_many_post_save, sender=cls)
            DBField.contribute_to_class(self, cls, name, *args, **kwargs)

        def pre_save(self, model_instance, add):
            """
            Updates the value of the denormalized field before it gets saved.
            """
            value = self.denorm.func(model_instance)
            setattr(model_instance, self.attname, value)
            return value

        def south_field_triple(self):
            """
            Because this field will be defined as a decorator, give
            South hints on how to recreate it for database use.
            """
            from south.modelsinspector import introspector
            field_class = DBField.__module__ + "." + DBField.__name__
            args, kwargs = introspector(self)
            return (field_class, args, kwargs)

    def deco(func):
        kwargs["blank"] = True
        if 'default' not in kwargs:
            kwargs["null"] = True
        dbfield = DenormDBField(func, *args, **kwargs)
        return dbfield
    return deco

class AggregateField(models.PositiveIntegerField):

    def get_denorm(self, *args, **kwargs):
        """
        Returns denorm instance
        """
        raise NotImplemented('You need to override this method')

    def __init__(self,manager_name,**kwargs):
        """
        **Arguments:**

        manager_name:
            The name of the related manager to be counted.

        filter:
            Filter, which is applied to manager. For example:

        >>> active_item_count = CountField('item_set', filter={'active__exact':True})
        >>> adult_user_count = CountField('user_set', filter={'age__gt':18})

        exclude:
            Do not include filter in aggregation

        Any additional arguments are passed on to the contructor of
        PositiveIntegerField.
        """
        skip = kwargs.pop('skip', None)
        qs_filter = kwargs.pop('filter', {})
        if qs_filter and hasattr(django.db.backend,'sqlite3'):
            raise NotImplementedError('filters for aggregate fields are currently not supported for sqlite')
        qs_exclude = kwargs.pop('exclude', {})
        self.denorm = self.get_denorm(skip)
        self.denorm.manager_name = manager_name
        self.denorm.filter = qs_filter
        self.denorm.exclude = qs_exclude
        self.kwargs = kwargs
        kwargs['default'] = 0
        kwargs['editable'] = False
        super(AggregateField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name, *args, **kwargs):
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(AggregateField,self).contribute_to_class(cls, name, *args, **kwargs)

    def south_field_triple(self):
        return (
            '.'.join(('django', 'db', 'models', models.PositiveIntegerField.__name__)),
            [],
            {
                'default': '0',
            },
        )

    def pre_save(self, model_instance, add):
        """
        Makes sure we never overwrite the count with an outdated value.
        This is necessary because if the count was changed by
        a trigger after this model instance was created, the value
        we would write has not been updated.
        """
        if add:
            # if this is a new instance there can't be any related objects yet
            value = 0
        else:
            # if we're updating, get the most recent value from the DB
            value = self.denorm.model.objects.filter(
                pk=model_instance.pk,
            ).values_list(
                self.attname, flat=True,
            )[0]

        setattr(model_instance, self.attname, value)
        return value


class CountField(AggregateField):
    """
    A ``PositiveIntegerField`` that stores the number of rows
    related to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    """

    def __init__(self, manager_name, **kwargs):
        """
        **Arguments:**

        manager_name:
            The name of the related manager to be counted.

        filter:
            Filter, which is applied to manager. For example:

        >>> active_item_count = CountField('item_set', filter={'active__exact':True})
        >>> adult_user_count = CountField('user_set', filter={'age__gt':18})

        Any additional arguments are passed on to the contructor of
        PositiveIntegerField.
        """

        kwargs['editable'] = False
        super(CountField, self).__init__(manager_name, **kwargs)

    def get_denorm(self, skip):
        return denorms.CountDenorm(skip)

class SumField(AggregateField):
    """
    A ``PositiveIntegerField`` that stores sub of related field values
    to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    """

    def __init__(self, manager_name, field, **kwargs):
        self.field = field
        kwargs['editable'] = False
        super(SumField, self).__init__(manager_name, **kwargs)

    def get_denorm(self, skip):
        return denorms.SumDenorm(skip, self.field)

class CopyField(AggregateField):
    """
    Field, which makes two field identical. Any change in related field will change this field
    """
    # TODO: JFDI

class CacheKeyField(models.BigIntegerField):
    """
    A ``BigIntegerField`` that gets set to a random value anytime
    the model is saved or a dependency is triggered.
    The field gets updated immediately and does not require *denorm.flush()*.
    It currently cannot detect a direct (bulk)update to the model
    it is declared in.
    """

    def __init__(self, **kwargs):
        """
        All arguments are passed on to the contructor of
        BigIntegerField.
        """
        self.dependencies = []
        kwargs['default'] = 0
        kwargs['editable'] = False
        self.kwargs = kwargs
        super(CacheKeyField, self).__init__(**kwargs)

    def depend_on_related(self, *args, **kwargs):
        """
        Add dependency information to the CacheKeyField.
        Accepts the same arguments like the *denorm.depend_on_related* decorator
        """
        from dependencies import CacheKeyDependOnRelated
        self.dependencies.append(CacheKeyDependOnRelated(*args, **kwargs))

    def contribute_to_class(self, cls, name, *args, **kwargs):
        for depend in self.dependencies:
            depend.fieldname = name
        self.denorm = denorms.BaseCacheKeyDenorm(depend_on_related=self.dependencies)
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(CacheKeyField, self).contribute_to_class(cls, name, *args, **kwargs)

    def pre_save(self, model_instance, add):
        if add:
            value = self.denorm.func(model_instance)
        else:
            value = self.denorm.model.objects.filter(
                pk=model_instance.pk,
            ).values_list(
                self.attname, flat=True,
            )[0]
        setattr(model_instance, self.attname, value)
        return value

    def south_field_triple(self):
        return (
            '.'.join(('django', 'db', 'models', models.BigIntegerField.__name__)),
            [],
            {
                'default': '0',
            },
        )

class CacheWrapper(object):
    def __init__(self,field):
        self.field = field

    def __set__(self, obj, value):
        key = 'CachedField_%s' % value
        cached = self.field.cache.get(key)
        if not cached:
            cached = self.field.func(obj)
            self.field.cache.set(key,cached,60*60*24*30)
        obj.__dict__[self.field.name] = cached

class CachedField(CacheKeyField):

    def __init__(self, func, cache, *args, **kwargs):
        self.func = func
        self.cache = cache
        super(CachedField, self).__init__(*args, **kwargs)
        for c,a,kw in self.func.depend:
            self.depend_on_related(*a,**kw)

    def contribute_to_class(self, cls, name, *args, **kwargs):
        super(CachedField, self).contribute_to_class(cls, name, *args, **kwargs)
        setattr(cls, self.name, CacheWrapper(self))


def cached(cache,*args,**kwargs):
    def deco(func):
        dbfield = CachedField(func, cache, *args, **kwargs)
        return dbfield
    return deco

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
from django.db import models


def find_fks(from_model, to_model, fk_name=None):
    """
    Finds all ForeignKeys on 'from_model' pointing to 'to_model'.
    If 'fk_name' is given only ForeignKeys matching that name are returned.
    """
    # get all ForeignKeys
    fkeys = [x for x in from_model._meta.fields if isinstance(x, models.ForeignKey)]

    # filter out all FKs not pointing to 'to_model'
    fkeys = [x for x in fkeys if repr(x.rel.to).lower() == repr(to_model).lower()]

    # if 'fk_name' was given, filter out all FKs not matching that name, leaving
    # only one (or none)
    if fk_name:
        fk_name = fk_name if isinstance(fk_name, (str, unicode)) else fk_name.attname
        fkeys = [x for x in fkeys if x.attname in (fk_name, fk_name + '_id')]

    return fkeys


def find_m2ms(from_model, to_model, m2m_name=None):
    """
    Finds all ManyToManyFields on 'from_model' pointing to 'to_model'.
    If 'm2m_name' is given only ManyToManyFields matching that name are returned.
    """
    # get all ManyToManyFields
    m2ms = from_model._meta.many_to_many

    # filter out all M2Ms not pointing to 'to_model'
    m2ms = [x for x in m2ms if repr(x.rel.to).lower() == repr(to_model).lower()]

    # if 'm2m_name' was given, filter out all M2Ms not matching that name, leaving
    # only one (or none)
    if m2m_name:
        m2m_name = m2m_name if isinstance(m2m_name, (str, unicode)) else m2m_name.attname
        m2ms = [x for x in m2ms if x.attname == m2m_name]

    return m2ms

########NEW FILE########
__FILENAME__ = denormalize
from django.core.management.base import NoArgsCommand, CommandError


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        raise CommandError("This management command is deprecated. "
            "Please consult the documentation for a command reference.")

########NEW FILE########
__FILENAME__ = denorm_daemon
import os
import sys
from time import sleep
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import transaction

from denorm import denorms

PID_FILE = "/tmp/django-denorm-daemon-pid"


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('-n',
            action='store_true',
            dest='foreground',
            default=False,
            help='Run in foreground',
        ),
        make_option('-i',
            action='store',
            type='int',
            dest='interval',
            default=1,
            help='The interval - in seconds - between each update',
        ),
        make_option('-f', '--pidfile',
            action='store',
            type='string',
            dest='pidfile',
            default=PID_FILE,
            help='The pid file to use. Defaults to "%s".' % PID_FILE)
    )
    help = "Runs a daemon that checks for dirty fields and updates them in regular intervals."

    def pid_exists(self, pidfile):
        try:
            pid = int(file(pidfile, 'r').read())
            os.kill(pid, 0)
            self.stderr.write(self.style.ERROR("daemon already running as pid: %s\n" % (pid,)))
            return True
        except OSError, err:
            return err.errno == os.errno.EPERM
        except IOError, err:
            if err.errno == 2:
                return False
            else:
                raise

    @transaction.commit_manually
    def handle_noargs(self, **options):
        foreground = options['foreground']
        interval = options['interval']
        pidfile = options['pidfile']

        if self.pid_exists(pidfile):
            return

        if not foreground:
            from denorm import daemon
            daemon.daemonize(noClose=True, pidfile=pidfile)

        while True:
            try:
                denorms.flush()
                sleep(interval)
                transaction.commit()
            except KeyboardInterrupt:
                transaction.commit()
                sys.exit()

########NEW FILE########
__FILENAME__ = denorm_drop
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import DEFAULT_DB_ALIAS

from denorm import denorms


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to execute '
                'SQL into. Defaults to the "default" database.'),
    )
    help = "Removes all triggers created by django-denorm."

    def handle_noargs(self, **options):
        using = options['database']
        denorms.drop_triggers(using=using)

########NEW FILE########
__FILENAME__ = denorm_flush
from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every denormalized field that was marked dirty."

    def handle(self, **kwargs):
        denorms.flush()

########NEW FILE########
__FILENAME__ = denorm_init
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import DEFAULT_DB_ALIAS

from denorm import denorms


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to execute '
                'SQL into. Defaults to the "default" database.'),
    )
    help = "Creates all triggers needed by django-denorm."

    def handle_noargs(self, **options):
        using = options['database']
        denorms.install_triggers(using=using)

########NEW FILE########
__FILENAME__ = denorm_rebuild
from django.core.management.base import BaseCommand
from denorm import denorms


class Command(BaseCommand):
    help = "Recalculates the value of every single denormalized model field in the whole project."

    def handle(self, model_name=None, *args, **kwargs):
        verbosity = int((kwargs.get('verbosity',0)))
        denorms.rebuildall(verbose=verbosity > 1, model_name=model_name)

########NEW FILE########
__FILENAME__ = denorm_sql
from django.core.management.base import NoArgsCommand
from denorm import denorms


class Command(NoArgsCommand):
    help = "Prints out the SQL used to create all triggers needed to track changes to models that may cause data to become inconsistent."

    def handle_noargs(self, **options):
        triggerset = denorms.build_triggerset()
        sql_list = []
        for name,trigger in triggerset.triggers.iteritems():
            sql, params = trigger.sql()
            sql_list.append(sql % tuple(params))
        print '\n'.join(sql_list)

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from denorm import flush
from django.db import DatabaseError
import logging

logger = logging.getLogger(__name__)

class DenormMiddleware(object):
    """
    Calls ``denorm.flush`` during the response stage of every request. If your data mostly or only changes during requests
    this should be a good idea. If you run into performance problems with this (because ``flush()`` takes
    to long to complete) you can try using a daemon or handle flushing manually instead.

    As usual the order of middleware classes matters. It makes a lot of sense to put ``DenormMiddleware``
    after ``TransactionMiddleware`` in your ``MIDDLEWARE_CLASSES`` setting.
    """
    def process_response(self, request, response):
        try:
            flush()
        except DatabaseError as e:
            logger.error(e)
        return response

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'DirtyInstance'
        db.create_table('denorm_dirtyinstance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('denorm', ['DirtyInstance'])

        # Adding unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.create_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

    def backwards(self, orm):

        # Removing unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.delete_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

        # Deleting model 'DirtyInstance'
        db.delete_table('denorm_dirtyinstance')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'denorm.dirtyinstance': {
            'Meta': {'unique_together': "(('object_id', 'content_type'),)", 'object_name': 'DirtyInstance'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['denorm']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_dirtyinstance_object_id
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Remove unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.delete_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

        # Changing field 'DirtyInstance.object_id'
        db.alter_column('denorm_dirtyinstance', 'object_id', self.gf('django.db.models.fields.TextField')(null=True))



    def backwards(self, orm):

        # Adding unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.create_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

        # Changing field 'DirtyInstance.object_id'
        db.alter_column('denorm_dirtyinstance', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'denorm.dirtyinstance': {
            'Meta': {'unique_together': "(('object_id', 'content_type'),)", 'object_name': 'DirtyInstance'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['denorm']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class DirtyInstance(models.Model):
    """
    Holds a reference to a model instance that may contain inconsistent data
    that needs to be recalculated.
    DirtyInstance instances are created by the insert/update/delete triggers
    when related objects change.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField(blank=True, null=True)
    content_object = generic.GenericForeignKey(fk_field="object_id")

    def __unicode__(self):
        return u'DirtyInstance: %s,%s' % (self.content_type, self.object_id)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-denorm documentation build configuration file, created by
# sphinx-quickstart on Fri May 22 22:07:05 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions (or modules documented by autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_sqlite'
sys.path.append(os.path.abspath('../../../'))
sys.path.append(os.path.abspath('../test_project/'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc','sphinxtogithub']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-denorm'
copyright = u'2009, Christian Schilling'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

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
html_static_path = ['.static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-denormdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'django-denorm.tex', ur'django-denorm Documentation',
   ur'Christian Schilling', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/python
import sys
import os

try:
    dbtypes = [sys.argv[1]]
except:
    dbtypes = ['sqlite', 'mysql', 'postgres']

os.environ['PYTHONPATH'] = '.:..'

for dbtype in dbtypes:
    print 'running tests on', dbtype
    os.environ['DJANGO_SETTINGS_MODULE'] = 'test_denorm_project.settings_%s' % dbtype

    if os.system("cd test_denorm_project; python manage.py test test_app"):
        exit(1)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_denorm_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from denorm.fields import SumField
import django
from django.db import models
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from denorm import denormalized, depend_on_related, CountField, CacheKeyField, cached
from django.core.cache import cache

class CachedModelA(models.Model):

    b = models.ForeignKey('CachedModelB')

    @cached(cache)
    @depend_on_related('CachedModelB')
    def cached_data(self):
        return {
            'upper':self.b.data.upper(),
            'lower':self.b.data.lower(),
        }

class CachedModelB(models.Model):
    data = models.CharField(max_length=255)


class Tag(models.Model):
    name = models.CharField(max_length=255)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class TaggedModel(models.Model):
    tags = GenericRelation(Tag)

    @denormalized(models.TextField)
    @depend_on_related(Tag)
    def tags_string(self):
        return ', '.join(sorted([t.name for t in self.tags.all()]))

    class Meta:
        abstract = True


class Forum(TaggedModel):

    title = models.CharField(max_length=255)

    # Simple count() aggregate
    post_count = CountField('post_set')

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post')

    @denormalized(models.CharField, max_length=255)
    @depend_on_related('Post')
    def author_names(self):
        return ', '.join((m.author_name for m in self.post_set.all()))

    @denormalized(models.ManyToManyField, 'Member', null=True, blank=True)
    @depend_on_related('Post')
    def authors(self):
        return [m.author for m in self.post_set.all() if m.author]

    # let's say this forums supports subforums, sub-subforums and so forth
    # so we can test depend_on_related('self') (for tree structures).
    parent_forum = models.ForeignKey('self', blank=True, null=True)

    @denormalized(models.TextField)
    @depend_on_related('self', type='forward')
    def path(self):
        if self.parent_forum:
            return self.parent_forum.path + self.title + '/'
        else:
            return '/' + self.title + '/'


class Post(TaggedModel):

    forum = models.ForeignKey(Forum, blank=True, null=True)
    author = models.ForeignKey('Member', blank=True, null=True)
    response_to = models.ForeignKey('self', blank=True, null=True, related_name='responses')
    title = models.CharField(max_length=255, blank=True)

    # Brings down the forum title
    @denormalized(models.CharField, max_length=255)
    @depend_on_related(Forum)
    def forum_title(self):
        return self.forum.title

    @denormalized(models.CharField, max_length=255)
    @depend_on_related('Member', foreign_key="author")
    def author_name(self):
        if self.author:
            return self.author.name
        else:
            return ''

    @denormalized(models.PositiveIntegerField)
    @depend_on_related('self', type='backward')
    def response_count(self):
        # Work around odd issue during testing with PostgresDB
        if not self.pk:
            return 0
        rcount = self.responses.count()
        rcount += sum((x.response_count for x in self.responses.all()))
        return rcount


class Attachment(models.Model):

    post = models.ForeignKey(Post, blank=True, null=True)

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post')

    @denormalized(models.ForeignKey, Forum, blank=True, null=True)
    @depend_on_related(Post)
    def forum(self):
        if self.post and self.post.forum:
            return self.post.forum.pk
        return None


class Member(models.Model):

    first_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    bookmarks = models.ManyToManyField('Post', blank=True)

    cachekey = CacheKeyField()
    cachekey.depend_on_related('Post', foreign_key='bookmarks')

    @denormalized(models.CharField, max_length=255)
    def full_name(self):
        return u"%s %s" % (self.first_name, self.name)

    @denormalized(models.TextField)
    @depend_on_related('Post', foreign_key="bookmarks")
    def bookmark_titles(self):
        if self.id:
            return '\n'.join([p.title for p in self.bookmarks.all()])


class SkipPost(models.Model):
    # Skip feature test main model.
    text = models.TextField()


class SkipComment(models.Model):
    post = models.ForeignKey(SkipPost)
    text = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class SkipCommentWithoutSkip(SkipComment):
    # Skip feature test model without a skip parameter on an updatable field.
    # he updatable field will not be skipped.
    @denormalized(models.TextField)
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text


class SkipCommentWithSkip(SkipComment):
    # Skip feature test model with a skip parameter on an updatable field.
    @denormalized(models.TextField, skip=('updated_on',))
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text

class SkipCommentWithAttributeSkip(SkipComment):
    @denormalized(models.TextField)
    @depend_on_related(SkipPost)
    def post_text(self):
        return self.post.text

    denorm_always_skip = ('updated_on',)


if not hasattr(django.db.backend,'sqlite3'):
    class FilterSumModel(models.Model):
        # Simple count() aggregate
        active_item_sum = SumField('counts', field='active_item_count', filter = {'age__gte':18})

    class FilterSumItem(models.Model):
        parent = models.ForeignKey(FilterSumModel, related_name='counts')
        age = models.IntegerField(default=18)
        active_item_count = models.PositiveIntegerField(default=False)

    class FilterCountModel(models.Model):
        # Simple count() aggregate
        active_item_count = CountField('items', filter = {'active__exact':True}, exclude = {'text':''})

    class FilterCountItem(models.Model):
        parent = models.ForeignKey(FilterCountModel, related_name='items')
        active = models.BooleanField(default=False)
        text = models.CharField(max_length=10, default='')


########NEW FILE########
__FILENAME__ = tests
import django
from django.test import TestCase
from django.contrib.auth.models import User,  Permission
from django.contrib.contenttypes.models import ContentType

import denorm
from denorm import denorms
import models

class TestCached(TestCase):

    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

    def tearDown(self):
        models.CachedModelA.objects.all().delete()
        models.CachedModelB.objects.all().delete()

    def test_depends_related(self):
        models.CachedModelB.objects.create(data='Hello')
        b = models.CachedModelB.objects.all()[0]
        self.assertEqual('Hello',b.data)

        models.CachedModelA.objects.create(b=b)
        a = models.CachedModelA.objects.all()[0]

        self.assertEqual("HELLO",a.cached_data['upper'])
        self.assertEqual("hello",a.cached_data['lower'])

        b.data = 'World'
        self.assertEqual("HELLO",a.cached_data['upper'])
        self.assertEqual("hello",a.cached_data['lower'])

        b.save()
        a = models.CachedModelA.objects.all()[0]
        self.assertEqual("WORLD",a.cached_data['upper'])
        self.assertEqual("world",a.cached_data['lower'])

class TestSkip(TestCase):
    """
    Tests for the skip feature.
    """

    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

        post = models.SkipPost(text='Here be ponies.')
        post.save()

        self.post = post

    # TODO: Enable and check!
    # Unsure on how to test this behaviour. It results in an endless loop:
    # update -> trigger -> update -> trigger -> ...
    #
    #def test_without_skip(self):
    #    # This results in an infinate loop on SQLite.
    #    comment = SkipCommentWithoutSkip(post=self.post,  text='Oh really?')
    #    comment.save()
    #
    #    denorm.flush()

    # TODO: Check if an infinate loop happens and stop it.
    def test_with_skip(self):
        # This should not result in an endless loop.
        comment = models.SkipCommentWithSkip(post=self.post,  text='Oh really?')
        comment.save()

        denorm.flush()

    def test_meta_skip(self):
        """Test a model with the attribute listed under denorm_always_skip."""
        comment = models.SkipCommentWithAttributeSkip(post=self.post, text='Yup, and they have wings!')
        comment.save()

        denorm.flush()


class TestDenormalisation(TestCase):
    """
    Tests for the denormalisation fields.
    """

    def setUp(self):
        denorms.drop_triggers()
        denorms.install_triggers()

        self.testuser = User.objects.create_user("testuser", "testuser",  "testuser")
        self.testuser.is_staff = True
        ctype = ContentType.objects.get_for_model(models.Member)
        Permission.objects.filter(content_type=ctype).get(name='Can change member').user_set.add(self.testuser)
        self.testuser.save()

    def tearDown(self):
        # delete all model instances
        self.testuser.delete()
        models.Attachment.objects.all().delete()
        models.Post.objects.all().delete()
        models.Forum.objects.all().delete()

    def test_depends_related(self):
        """
        Test the DependsOnRelated stuff.
        """
        # Make a forum,  check it's got no posts
        f1 = models.Forum.objects.create(title="forumone")
        self.assertEqual(f1.post_count,  0)
        # Check its database copy too
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  0)

        # Add a post
        p1 = models.Post.objects.create(forum=f1)
        # Has the post count updated?
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  1)

        denorm.flush()

        # Check its title,  in p1 and the DB
        self.assertEqual(p1.forum_title,  "forumone")
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title,  "forumone")

        # Update the forum title
        f1.title = "forumtwo"
        f1.save()

        denorm.flush()

        # Has the post's title changed?
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title,  "forumtwo")

        # Add and remove some posts and check the post count
        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  2)
        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  3)
        p1.delete()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  2)

        # Delete everything,  check once more.
        models.Post.objects.all().delete()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  0)

        # Make an orphaned post,  see what its title is.
        # Doesn't work yet - no support for null FKs
        #p4 = Post.objects.create(forum=None)
        #self.assertEqual(p4.forum_title,  None)

    def test_dependency_chains(self):
        # create a forum,  a member and a post
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1,  author=m1)
        denorm.flush()

        # check the forums author list contains the member
        self.assertEqual(models.Forum.objects.get(id=f1.id).author_names,  "memberone")

        # change the member's name
        m1.name = "membertwo"
        m1.save()
        denorm.flush()

        # check again
        self.assertEqual(models.Forum.objects.get(id=f1.id).author_names,  "membertwo")

    def test_trees(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo",  parent_forum=f1)
        f3 = models.Forum.objects.create(title="forumthree",  parent_forum=f2)
        denorm.flush()

        self.assertEqual(f1.path, '/forumone/')
        self.assertEqual(f2.path, '/forumone/forumtwo/')
        self.assertEqual(f3.path, '/forumone/forumtwo/forumthree/')

        f1.title = 'someothertitle'
        f1.save()
        denorm.flush()

        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)
        f3 = models.Forum.objects.get(id=f3.id)

        self.assertEqual(f1.path,  '/someothertitle/')
        self.assertEqual(f2.path,  '/someothertitle/forumtwo/')
        self.assertEqual(f3.path, '/someothertitle/forumtwo/forumthree/')

    def test_reverse_fk_null(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1, author=m1)
        models.Attachment.objects.create()
        denorm.flush()

    def test_bulk_update(self):
        """
        Test the DependsOnRelated stuff.
        """
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        p1 = models.Post.objects.create(forum=f1)
        p2 = models.Post.objects.create(forum=f2)
        denorm.flush()

        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title,  "forumone")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title,  "forumtwo")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  1)

        models.Post.objects.update(forum=f1)
        denorm.flush()
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title,  "forumone")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title,  "forumone")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  2)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  0)

        models.Forum.objects.update(title="oneforall")
        denorm.flush()
        self.assertEqual(models.Post.objects.get(id=p1.id).forum_title,  "oneforall")
        self.assertEqual(models.Post.objects.get(id=p2.id).forum_title,  "oneforall")

    def test_no_dependency(self):
        m1 = models.Member.objects.create(first_name="first", name="last")
        denorm.flush()

        self.assertEqual(models.Member.objects.get(id=m1.id).full_name, "first last")

        models.Member.objects.filter(id=m1.id).update(first_name="second")
        denorm.flush()
        self.assertEqual(models.Member.objects.get(id=m1.id).full_name, "second last")

    def test_self_backward_relation(self):

        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(forum=f1, )
        p2 = models.Post.objects.create(forum=f1, response_to=p1)
        p3 = models.Post.objects.create(forum=f1, response_to=p1)
        p4 = models.Post.objects.create(forum=f1, response_to=p2)
        denorm.flush()

        self.assertEqual(models.Post.objects.get(id=p1.id).response_count,  3)
        self.assertEqual(models.Post.objects.get(id=p2.id).response_count,  1)
        self.assertEqual(models.Post.objects.get(id=p3.id).response_count,  0)
        self.assertEqual(models.Post.objects.get(id=p4.id).response_count,  0)

    def test_m2m_relation(self):
        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(forum=f1, title="post1")
        m1 = models.Member.objects.create(first_name="first1", name="last1")

        denorm.flush()
        m1.bookmarks.add(p1)
        denorm.flush()

        self.assertTrue('post1' in models.Member.objects.get(id=m1.id).bookmark_titles)
        p1.title = "othertitle"
        p1.save()
        denorm.flush()
        self.assertTrue('post1' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

        p2 = models.Post.objects.create(forum=f1, title="thirdtitle")
        m1.bookmarks.add(p2)
        denorm.flush()
        self.assertTrue('post1' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('othertitle' in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

        m1.bookmarks.remove(p1)
        denorm.flush()
        self.assertTrue('othertitle' not in models.Member.objects.get(id=m1.id).bookmark_titles)
        self.assertTrue('thirdtitle' in models.Member.objects.get(id=m1.id).bookmark_titles)

    def test_middleware(self):
        # FIXME,  this test currently does not work with a transactional
        # database,  so it's skipped for now.
        return
        # FIXME,  set and de-set middleware values
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(first_name="first1", name="last1")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        self.assertEqual(models.Post.objects.get(id=p1.id).author_name,  "last1")

        self.client.login(username="testuser", password="testuser")
        self.client.post("/admin/denorm_testapp/member/%s/" % (m1.pk), {
            'name': 'last2',
            'first_name': 'first2',
        })

        self.assertEqual(models.Post.objects.get(id=p1.id).author_name,  "last2")

    def test_countfield(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumone")
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  0)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  0)

        models.Post.objects.create(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  0)

        p2 = models.Post.objects.create(forum=f2)
        p3 = models.Post.objects.create(forum=f2)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  1)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  2)

        p2.forum = f1
        p2.save()
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  2)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  1)

        models.Post.objects.filter(pk=p3.pk).update(forum=f1)
        self.assertEqual(models.Forum.objects.get(id=f1.id).post_count,  3)
        self.assertEqual(models.Forum.objects.get(id=f2.id).post_count,  0)

    def test_foreignkey(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        m1 = models.Member.objects.create(first_name="first1", name="last1")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        a1 = models.Attachment.objects.create(post=p1)
        self.assertEqual(models.Attachment.objects.get(id=a1.id).forum,  f1)

        a2 = models.Attachment.objects.create()
        self.assertEqual(models.Attachment.objects.get(id=a2.id).forum,  None)

        # Change forum
        p1.forum = f2
        p1.save()
        denorm.flush()
        self.assertEqual(models.Attachment.objects.get(id=a1.id).forum,  f2)

    def test_m2m(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        models.Post.objects.create(forum=f1, author=m1)
        denorm.flush()

        # check the forums author list contains the member
        self.assertTrue(m1 in models.Forum.objects.get(id=f1.id).authors.all())

        m2 = models.Member.objects.create(name="membertwo")
        p2 = models.Post.objects.create(forum=f1, author=m2)
        denorm.flush()

        self.assertTrue(m1 in models.Forum.objects.get(id=f1.id).authors.all())
        self.assertTrue(m2 in models.Forum.objects.get(id=f1.id).authors.all())

        p2.delete()
        denorm.flush()

        self.assertTrue(m2 not in models.Forum.objects.get(id=f1.id).authors.all())

    def test_denorm_rebuild(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        denorm.denorms.rebuildall()

        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.post_count,  1)
        self.assertEqual(f1.authors.all()[0], m1)

    def test_denorm_update(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)
        a1 = models.Attachment.objects.create(post=p1)

        denorm.denorms.rebuildall()

        f2 = models.Forum.objects.create(title="forumtwo")
        p1.forum = f2
        p1.save()

        # BUG https://github.com/initcrash/django-denorm/issues/24
        # We have to update the Attachment.forum field first to trigger this bug. Simply doing rebuildall() will
        # trigger an a1.save() at an some earlier point during the update. By the time we get to updating the value of
        # forum field the value is already correct and no update is done bypassing the broken code.
        for d in denorms.alldenorms:
            if d.model == models.Attachment and d.fieldname == 'forum':
                d.update(models.Attachment.objects.all())

    def test_denorm_subclass(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(forum=f1, author=m1)

        self.assertEqual(f1.tags_string,  '')
        self.assertEqual(p1.tags_string,  '')

        models.Tag.objects.create(name='tagone',  content_object=f1)
        models.Tag.objects.create(name='tagtwo',  content_object=f1)

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagone, tagtwo')
        self.assertEqual(p1.tags_string,  '')

        models.Tag.objects.create(name='tagthree',  content_object=p1)
        t4 = models.Tag.objects.create(name='tagfour',  content_object=p1)

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagone, tagtwo')
        self.assertEqual(p1.tags_string, 'tagfour, tagthree')

        t4.content_object = f1
        t4.save()

        denorm.denorms.flush()
        f1 = models.Forum.objects.get(id=f1.id)
        m1 = models.Member.objects.get(id=m1.id)
        p1 = models.Post.objects.get(id=p1.id)

        self.assertEqual(f1.tags_string, 'tagfour, tagone, tagtwo')
        self.assertEqual(p1.tags_string,  'tagthree')

    def test_cache_key_field_backward(self):
        f1 = models.Forum.objects.create(title="forumone")
        f2 = models.Forum.objects.create(title="forumtwo")
        ck1 = f1.cachekey
        ck2 = f2.cachekey

        p1 = models.Post.objects.create(forum=f1)
        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)
        self.assertNotEqual(ck1, f1.cachekey)
        self.assertEqual(ck2, f2.cachekey)

        ck1 = f1.cachekey
        ck2 = f2.cachekey

        p1 = models.Post.objects.get(id=p1.id)
        p1.forum = f2
        p1.save()

        f1 = models.Forum.objects.get(id=f1.id)
        f2 = models.Forum.objects.get(id=f2.id)

        self.assertNotEqual(ck1, f1.cachekey)
        self.assertNotEqual(ck2, f2.cachekey)

    def test_cache_key_field_forward(self):
        f1 = models.Forum.objects.create(title="forumone")
        p1 = models.Post.objects.create(title='initial_title', forum=f1)
        a1 = models.Attachment.objects.create(post=p1)
        a2 = models.Attachment.objects.create(post=p1)

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(a1.cachekey, a2.cachekey)

        ck1 = a1.cachekey
        ck2 = a2.cachekey
        p1.title = 'new_title'
        p1.save()

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(ck1, a1.cachekey)
        self.assertNotEqual(ck2, a2.cachekey)

        a1 = models.Attachment.objects.get(id=a1.id)
        a2 = models.Attachment.objects.get(id=a2.id)
        self.assertNotEqual(a1.cachekey, a2.cachekey)

    def test_cache_key_field_m2m(self):
        f1 = models.Forum.objects.create(title="forumone")
        m1 = models.Member.objects.create(name="memberone")
        p1 = models.Post.objects.create(title='initial_title', forum=f1)

        m1 = models.Member.objects.get(id=m1.id)
        ck1 = m1.cachekey

        m1.bookmarks.add(p1)

        m1 = models.Member.objects.get(id=m1.id)
        self.assertNotEqual(ck1, m1.cachekey)

        ck1 = m1.cachekey

        p1 = models.Post.objects.get(id=p1.id)
        p1.title = 'new_title'
        p1.save()

        m1 = models.Member.objects.get(id=m1.id)
        self.assertNotEqual(ck1, m1.cachekey)
        

if not hasattr(django.db.backend,'sqlite3'):
    class TestFilterCount(TestCase):
        """
        Tests for the filtered count feature.
        """
        
        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()

        def test_filter_count(self):
            master = models.FilterCountModel.objects.create()
            self.assertEqual(master.active_item_count,0)
            master.items.create(active = True, text='text')
            master.items.create(active = True, text='')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count,1, 'created active item')
            master.items.create(active = False)
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count,1, 'created inactive item')
            master.items.create(active = True, text='true')
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,2)
            master.items.filter(active = False).delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,2)
            master.items.filter(active = True, text='true')[0].delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,1)
            item = master.items.filter(active = True, text='text')[0]
            item.active = False
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,0)
            item = master.items.filter(active = False, text='text')[0]
            item.active = True
            item.text = ''
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,0)
            item = master.items.filter(active = True, text='')[0]
            item.text = '123'
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,1)

    class TestFilterCountM2M(TestCase):
        """
        Tests for the filtered count feature.
        """
        
        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()
        def test_filter_count(self):
            master = models.FilterCountModel.objects.create()
            self.assertEqual(master.active_item_count,0)
            master.items.create(active = True, text='true')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count,1, 'created active item')
            master.items.create(active = False, text='true')
            master = models.FilterCountModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_count,1, 'created inactive item')
            master.items.create(active = True, text='true')
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,2)
            master.items.filter(active = False).delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,2)
            master.items.filter(active = True)[0].delete()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,1)
            item = master.items.filter(active = True)[0]
            item.active = False
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,0)
            item = master.items.filter(active = False)[0]
            item.active = True
            item.save()
            master = models.FilterCountModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_count,1)

    class TestFilterSum(TestCase):
        """
        Tests for the filtered count feature.
        """

        def setUp(self):
            denorms.drop_triggers()
            denorms.install_triggers()

        def test_filter_count(self):
            master = models.FilterSumModel.objects.create()
            self.assertEqual(master.active_item_sum,0)
            master.counts.create(age = 18, active_item_count=8)
            master = models.FilterSumModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_sum,8)
            master.counts.create(age = 16, active_item_count=10)
            master = models.FilterSumModel.objects.get(id=master.id)
            self.assertEqual(master.active_item_sum,8, 'created inactive item')
            master.counts.create(age = 19, active_item_count=9)
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum,17)
            master.counts.filter(age__lt = 18).delete()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum,17)
            master.counts.filter(age = 19)[0].delete()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum,8)
            item = master.counts.filter(age = 18)[0]
            item.age = 15
            item.save()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum,0)
            item = master.counts.filter(age = 15)[0]
            item.age = 18
            item.save()
            master = models.FilterSumModel.objects.get(pk=master.pk)
            self.assertEqual(master.active_item_sum,8)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
# TEST_RUNNER = "djangosanetesting.testrunner.DstNoseTestSuiteRunner"

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '#54vuj)xosdlk%%a$ifuj8v-^z4fvupm2vmr_!2cno&g6_a-wg'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'test_denorm_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',

    # 'django_nose',
    'test_app',
    'denorm',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = settings_mysql
from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'denorm_test',
        'HOST': 'localhost',
        'USER': 'root',
        'PASSWORD': '',
    }
}

########NEW FILE########
__FILENAME__ = settings_postgres
from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'denorm_test',
        'HOST': 'localhost',
        'USER': 'postgres',
        'PASSWORD': '',
    }
}

########NEW FILE########
__FILENAME__ = settings_sqlite
from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/1.sqlite',
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_project.views.home', name='home'),
    # url(r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
