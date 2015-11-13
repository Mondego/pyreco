__FILENAME__ = admin
## -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import operator
import re
from functools import reduce
from django.utils.encoding import force_text
from django.contrib import admin, messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models import Q
from django.forms.formsets import (ManagementForm, TOTAL_FORM_COUNT, INITIAL_FORM_COUNT,
                                   MAX_NUM_FORM_COUNT)
from django.forms.models import BaseModelFormSet
from django.utils.safestring import mark_safe
from django.contrib.admin import helpers
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ungettext, ugettext as _
from concurrency import forms
from concurrency import core
from concurrency.api import get_revision_of_object
from concurrency.config import conf, CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL
from concurrency.exceptions import RecordModifiedError
from concurrency.forms import ConcurrentForm, VersionWidget


class ConcurrencyActionMixin(object):
    check_concurrent_action = True

    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        if self.check_concurrent_action:
            return helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME,
                                           force_text("%s,%s" % (obj.pk,
                                                                 get_revision_of_object(obj))))
        else:
            return super(ConcurrencyActionMixin, self).action_checkbox(obj)

    action_checkbox.short_description = mark_safe('<input type="checkbox" id="action-toggle" />')
    action_checkbox.allow_tags = True

    def get_confirmation_template(self):
        return "concurrency/delete_selected_confirmation.html"

    def response_action(self, request, queryset):
        """
        Handle an admin action. This is called if a request is POSTed to the
        changelist; it returns an HttpResponse if the action was handled, and
        None otherwise.
        """
        # There can be multiple action forms on the page (at the top
        # and bottom of the change list, for example). Get the action
        # whose button was pushed.
        try:
            action_index = int(request.POST.get('index', 0))
        except ValueError:
            action_index = 0

        # Construct the action form.
        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        # Use the action whose button was pushed
        try:
            data.update({'action': data.getlist('action')[action_index]})
        except IndexError:
            # If we didn't get an action from the chosen form that's invalid
            # POST data, so by deleting action it'll fail the validation check
            # below. So no need to do anything here
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields['action'].choices = self.get_action_choices(request)

        # If the form's valid we can handle the action.
        if action_form.is_valid():
            action = action_form.cleaned_data['action']
            func, name, description = self.get_actions(request)[action]

            # Get the list of selected PKs. If nothing's selected, we can't
            # perform an action on it, so bail.
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

            revision_field = self.model._concurrencymeta._field
            if not selected:
                return None

            if self.check_concurrent_action:
                self.delete_selected_confirmation_template = self.get_confirmation_template()
                filters = []
                for x in selected:
                    try:
                        pk, version = x.split(",")
                    except ValueError:
                        raise ImproperlyConfigured('`ConcurrencyActionMixin` error.'
                                                   'A tuple with `primary_key, version_number` '
                                                   'expected:  `%s` found' % x)
                    filters.append(Q(**{'pk': pk,
                                        revision_field.attname: version}))

                queryset = queryset.filter(reduce(operator.or_, filters))
                if len(selected) != queryset.count():
                    messages.error(request, 'One or more record were updated. '
                                            '(Probably by other user) '
                                            'The execution was aborted.')
                    return HttpResponseRedirect(".")

            response = func(self, request, queryset)

            # Actions may return an HttpResponse, which will be used as the
            # response from the POST. If not, we'll be a good little HTTP
            # citizen and redirect back to the changelist page.
            if isinstance(response, HttpResponse):
                return response
            else:
                return HttpResponseRedirect(".")


class ConcurrentManagementForm(ManagementForm):
    def __init__(self, *args, **kwargs):
        self._versions = kwargs.pop('versions', [])
        super(ConcurrentManagementForm, self).__init__(*args, **kwargs)

    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        ret = super(ConcurrentManagementForm, self)._html_output(normal_row, error_row, row_ender, help_text_html,
                                                                 errors_on_separate_row)
        v = []
        for pk, version in self._versions:
            v.append('<input type="hidden" name="_concurrency_version_{0}" value="{1}">'.format(pk, version))
        return mark_safe("{0}{1}".format(ret, "".join(v)))


class ConcurrentBaseModelFormSet(BaseModelFormSet):
    def _management_form(self):
        """Returns the ManagementForm instance for this FormSet."""
        if self.is_bound:
            form = ConcurrentManagementForm(self.data, auto_id=self.auto_id,
                                            prefix=self.prefix)
            if not form.is_valid():
                raise ValidationError('ManagementForm data is missing or has been tampered with')
        else:
            form = ConcurrentManagementForm(auto_id=self.auto_id,
                                            prefix=self.prefix,
                                            initial={TOTAL_FORM_COUNT: self.total_form_count(),
                                                     INITIAL_FORM_COUNT: self.initial_form_count(),
                                                     MAX_NUM_FORM_COUNT: self.max_num},
                                            versions=[(form.instance.pk, get_revision_of_object(form.instance)) for form
                                                      in self.initial_forms])
        return form

    management_form = property(_management_form)


class ConcurrencyListEditableMixin(object):
    list_editable_policy = conf.POLICY

    def get_changelist_formset(self, request, **kwargs):
        kwargs['formset'] = ConcurrentBaseModelFormSet
        return super(ConcurrencyListEditableMixin, self).get_changelist_formset(request, **kwargs)

    def _add_conflict(self, request, obj):
        if hasattr(request, '_concurrency_list_editable_errors'):
            request._concurrency_list_editable_errors.append(obj.pk)
        else:
            request._concurrency_list_editable_errors = [obj.pk]

    def _get_conflicts(self, request):
        if hasattr(request, '_concurrency_list_editable_errors'):
            return request._concurrency_list_editable_errors
        else:
            return []

    def save_model(self, request, obj, form, change):
        try:
            if change:
                version = request.POST.get('_concurrency_version_{0.pk}'.format(obj), None)
                if version:
                    core._set_version(obj, version)
            super(ConcurrencyListEditableMixin, self).save_model(request, obj, form, change)
        except RecordModifiedError:
            self._add_conflict(request, obj)
            # If policy is set to 'silent' the user will be informed using message_user
            # raise Exception if not silent.
            # NOTE:
            #   list_editable_policy MUST have the LIST_EDITABLE_POLICY_ABORT_ALL
            #   set to work properly
            if self.list_editable_policy == CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL:
                raise

    def log_change(self, request, object, message):
        if object.pk in self._get_conflicts(request):
            return
        super(ConcurrencyListEditableMixin, self).log_change(request, object, message)

    def log_deletion(self, request, object, object_repr):
        if object.pk in self._get_conflicts(request):
            return
        super(ConcurrencyListEditableMixin, self).log_deletion(request, object, object_repr)

    def message_user(self, request, message, *args, **kwargs):
        # This is ugly but we do not want to touch the changelist_view() code.

        opts = self.model._meta
        conflicts = self._get_conflicts(request)
        if conflicts:
            names = force_text(opts.verbose_name), force_text(opts.verbose_name_plural)
            pattern = r"(?P<num>\d+) ({0}|{1})".format(*names)
            rex = re.compile(pattern)
            m = rex.match(message)
            concurrency_errros = len(conflicts)
            if m:
                updated_record = int(m.group('num')) - concurrency_errros
                if updated_record == 0:
                    message = _("No %(name)s were changed due conflict errors") % {'name': names[0]}
                else:
                    ids = ",".join(map(str, conflicts))
                    messages.error(request,
                                   ungettext("Record with pk `{0}` has been modified and was not updated",
                                             "Records `{0}` have been modified and were not updated",
                                             concurrency_errros).format(ids))
                    if updated_record == 1:
                        name = force_text(opts.verbose_name)
                    else:
                        name = force_text(opts.verbose_name_plural)
                    message = ungettext("%(count)s %(name)s was changed successfully.",
                                        "%(count)s %(name)s were changed successfully.",
                                        updated_record) % {'count': updated_record,
                                                           'name': name}

        return super(ConcurrencyListEditableMixin, self).message_user(request, message, *args, **kwargs)


class ConcurrentModelAdmin(ConcurrencyActionMixin,
                           ConcurrencyListEditableMixin,
                           admin.ModelAdmin):
    form = ConcurrentForm
    formfield_overrides = {forms.VersionField: {'widget': VersionWidget}}

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
from contextlib import contextmanager
from django.core.exceptions import ImproperlyConfigured
from concurrency.core import _select_lock, _wrap_model_save, get_version_fieldname
from concurrency.exceptions import RecordModifiedError

__all__ = ['apply_concurrency_check', 'concurrency_check', 'get_revision_of_object',
           'RecordModifiedError', 'disable_concurrency',
           'get_version', 'is_changed', 'get_version_fieldname']

logger = logging.getLogger(__name__)


def get_revision_of_object(obj):
    """
        returns teh version of the passed object

    @param obj:
    @return:
    """
    return getattr(obj, get_version_fieldname(obj))


def is_changed(obj):
    """
        returns True if `obj` is changed or deleted on the database
    :param obj:
    :return:
    """
    revision_field = get_version_fieldname(obj)
    version = get_revision_of_object(obj)
    return not obj.__class__.objects.filter(**{obj._meta.pk.name: obj.pk,
                                               revision_field: version}).exists()


def get_version(model_instance, version):
    """
        try go load from the database one object with specific version

    :param model_instance: instance in memory
    :param version: version number
    :return:
    """
    version_field = get_version_fieldname(model_instance)
    kwargs = {'pk': model_instance.pk, version_field: version}
    return model_instance.__class__.objects.get(**kwargs)


# def get_object_with_version(manager, pk, version):
#     """
#         try go load from the database one object with specific version.
#         Raises DoesNotExists otherwise.
#
#     :param manager: django.models.Manager
#     :param pk: primaryKey
#     :param version: version number
#     :return:
#     """
#     version_field = manager.model._concurrencymeta._field
#     kwargs = {'pk': pk, version_field.name: version}
#     return manager.get(**kwargs)


def apply_concurrency_check(model, fieldname, versionclass):
    """
    Apply concurrency management to existing Models.

    :param model: Model class to update
    :type model: django.db.Model

    :param fieldname: name of the field
    :type fieldname: basestring

    :param versionclass:
    :type versionclass: concurrency.fields.VersionField subclass
    """
    if hasattr(model, '_concurrencymeta'):
        raise ImproperlyConfigured("%s is already under concurrency management" % model)

    logger.debug('Applying concurrency check to %s' % model)

    ver = versionclass()
    ver.contribute_to_class(model, fieldname)
    model._concurrencymeta._field = ver

    if not model._concurrencymeta._versioned_save:
        _wrap_model_save(model)


def concurrency_check(model_instance, force_insert=False, force_update=False, using=None, **kwargs):
    if not force_insert:
        _select_lock(model_instance)


@contextmanager
def disable_concurrency(model):
    """
        temporary disable concurrency check for passed model
    :param model:
    """
    old_value, model._concurrencymeta.enabled = model._concurrencymeta.enabled, False
    yield
    model._concurrencymeta.enabled = old_value

########NEW FILE########
__FILENAME__ = config
from __future__ import absolute_import, unicode_literals
import warnings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_callable
from django.db.models import Model
from django.utils import six
from django.test.signals import setting_changed


# List Editable Policy
# 0 do not save updated records, save others, show message to the user
# 1 abort whole transaction

CONCURRENCY_LIST_EDITABLE_POLICY_SILENT = 1
CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL = 2
CONCURRENCY_POLICY_RAISE = 4
CONCURRENCY_POLICY_CALLBACK = 8

LIST_EDITABLE_POLICIES = [CONCURRENCY_LIST_EDITABLE_POLICY_SILENT, CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL]


class AppSettings(object):
    """
    Class to manage application related settings
    How to use:

    >>> from django.conf import settings
    >>> settings.APP_OVERRIDE = 'overridden'
    >>> settings.MYAPP_CALLBACK = 100
    >>> class MySettings(AppSettings):
    ...     defaults = {'ENTRY1': 'abc', 'ENTRY2': 123, 'OVERRIDE': None, 'CALLBACK':10}
    ...     def set_CALLBACK(self, value):
    ...         setattr(self, 'CALLBACK', value*2)

    >>> conf = MySettings("APP")
    >>> conf.ENTRY1, settings.APP_ENTRY1
    ('abc', 'abc')
    >>> conf.OVERRIDE, settings.APP_OVERRIDE
    ('overridden', 'overridden')

    >>> conf = MySettings("MYAPP")
    >>> conf.ENTRY2, settings.MYAPP_ENTRY2
    (123, 123)
    >>> conf = MySettings("MYAPP")
    >>> conf.CALLBACK
    200

    """
    defaults = {
        'ENABLED': True,
        'SANITY_CHECK': False,
        'PROTOCOL': 1,
        'FIELD_SIGNER': 'concurrency.forms.VersionFieldSigner',
        'POLICY': CONCURRENCY_LIST_EDITABLE_POLICY_SILENT,
        'CALLBACK': 'concurrency.views.callback',
        'USE_SELECT_FOR_UPDATE': True,
        'HANDLER409': 'concurrency.views.conflict'}

    def __init__(self, prefix):
        """
        Loads our settings from django.conf.settings, applying defaults for any
        that are omitted.
        """
        self.prefix = prefix
        from django.conf import settings

        if hasattr(settings, 'CONCURRENCY_SANITY_CHECK'):
            warnings.warn(
                'Starting from concurrency 0.7 `CONCURRENCY_SANITY_CHECK` has no effect and will be removed in 0.8')
        if hasattr(Model, '_do_update'):
            self.defaults['PROTOCOL'] = 2

        for name, default in self.defaults.items():
            if name != 'SANITY_CHECK':
                prefix_name = (self.prefix + '_' + name).upper()
                value = getattr(settings, prefix_name, default)
                self._set_attr(prefix_name, value)
                setattr(settings, prefix_name, value)
                setting_changed.send(self.__class__, setting=prefix_name, value=value, enter=True)

        setting_changed.connect(self._handler)

    # def _check_config(self):
    #     list_editable_policy = self.POLICY | sum(LIST_EDITABLE_POLICIES)
    #     if list_editable_policy == sum(LIST_EDITABLE_POLICIES):
    #         raise ImproperlyConfigured("Invalid value for `CONCURRENCY_POLICY`: "
    #                                    "Use only one of `CONCURRENCY_LIST_EDITABLE_*` flags")
    #
    #     conflict_policy = self.POLICY | sum(CONFLICTS_POLICIES)
    #     if conflict_policy == sum(CONFLICTS_POLICIES):
    #         raise ImproperlyConfigured("Invalid value for `CONCURRENCY_POLICY`: "
    #                                    "Use only one of `CONCURRENCY_POLICY_*` flags")

    def _set_attr(self, prefix_name, value):
        name = prefix_name[len(self.prefix) + 1:]
        if name == 'CALLBACK':
            if isinstance(value, six.string_types):
                func = get_callable(value)
            elif callable(value):
                func = value
            else:
                raise ImproperlyConfigured("`CALLBACK` must be a callable or a fullpath to callable")
            self._callback = func

        setattr(self, name, value)

    def _handler(self, sender, setting, value, **kwargs):
        """
            handler for ``setting_changed`` signal.

        @see :ref:`django:setting-changed`_
        """
        if setting.startswith(self.prefix):
            self._set_attr(setting, value)


conf = AppSettings('CONCURRENCY')

########NEW FILE########
__FILENAME__ = core
from __future__ import absolute_import
import logging
from django.db import connections, router
from concurrency.config import conf

# Set default logging handler to avoid "No handler found" warnings.
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger('concurrency').addHandler(NullHandler())

logger = logging.getLogger(__name__)

__all__ = []


def get_version_fieldname(obj):
    return obj._concurrencymeta._field.attname


def _set_version(obj, version):
    """
    Set the given version on the passed object

    This function should be used with 'raw' values, any type conversion should be managed in
    VersionField._set_version_value(). This is needed for future enhancement of concurrency.
    """
    obj._concurrencymeta._field._set_version_value(obj, version)


def _select_lock(model_instance, version_value=None):
    if not conf.ENABLED:
        return

    version_field = model_instance._concurrencymeta._field
    value = version_value or getattr(model_instance, version_field.name)
    is_versioned = value != version_field.get_default()

    if model_instance.pk is not None and is_versioned:
        kwargs = {'pk': model_instance.pk, version_field.name: value}
        if conf.PROTOCOL == 1 and conf.USE_SELECT_FOR_UPDATE:
            alias = router.db_for_write(model_instance)
            NOWAIT = connections[alias].features.has_select_for_update_nowait
            entry = model_instance.__class__._base_manager.select_for_update(nowait=NOWAIT).filter(**kwargs)
        else:
            entry = model_instance.__class__._base_manager.filter(**kwargs)

        if not entry:
            logger.debug("Conflict detected on `{0}` pk:`{0.pk}`, "
                         "version `{1}` not found".format(model_instance, value))
            conf._callback(model_instance)


def _wrap_model_save(model, force=False):
    if not force and model._concurrencymeta._versioned_save:
        return
    if conf.PROTOCOL == 2:
        logger.debug('Wrapping _do_update() method of %s' % model)
        old_do_update = getattr(model, '_do_update')
        old_save_base = getattr(model, 'save_base')
        old_save = getattr(model, 'save')
        setattr(model, '_do_update', model._concurrencymeta._field._wrap_do_update(old_do_update))
        setattr(model, 'save_base', model._concurrencymeta._field._wrap_save_base(old_save_base))
        setattr(model, 'save', model._concurrencymeta._field._wrap_save(old_save))

    elif conf.PROTOCOL == 1:
        logger.debug('Wrapping save method of %s' % model)
        old_save = getattr(model, 'save')
        setattr(model, 'save', model._concurrencymeta._field._wrap_save(old_save))

    from concurrency.api import get_version

    setattr(model, 'get_concurrency_version', get_version)
    model._concurrencymeta._versioned_save = True


class ConcurrencyOptions:
    _field = None
    _versioned_save = False
    _manually = False
    enabled = True

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

class TriggerMixin(object):
    def drop_triggers(self):
        for trigger_name in self.list_triggers():
            self.drop_trigger(trigger_name)

########NEW FILE########
__FILENAME__ = base
from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from concurrency.db.backends.common import TriggerMixin
from concurrency.db.backends.mysql.creation import MySQLCreation


class DatabaseWrapper(TriggerMixin, MySQLDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = MySQLCreation(self)

    def _clone(self):
        return self.__class__(self.settings_dict, self.alias)

    def list_triggers(self):
        cursor = self.cursor()
        cursor.execute("SHOW TRIGGERS LIKE 'concurrency_%%';")
        return [m[0] for m in cursor.fetchall()]

    def drop_trigger(self, trigger_name):
        cursor = self.cursor()
        result = cursor.execute("DROP TRIGGER IF EXISTS %s;" % trigger_name)
        return result



########NEW FILE########
__FILENAME__ = creation
import _mysql_exceptions

from django.db.backends.mysql.creation import DatabaseCreation
from concurrency.db.backends.utils import get_trigger_name


class MySQLCreation(DatabaseCreation):
    sql = """
ALTER TABLE {opts.db_table} CHANGE `{field.column}` `{field.column}` BIGINT(20) NOT NULL DEFAULT 1;
DROP TRIGGER IF EXISTS {trigger_name}_i;
DROP TRIGGER IF EXISTS {trigger_name}_u;

CREATE TRIGGER {trigger_name}_i BEFORE INSERT ON {opts.db_table}
FOR EACH ROW SET NEW.{field.column} = 1 ;
CREATE TRIGGER {trigger_name}_u BEFORE UPDATE ON {opts.db_table}
FOR EACH ROW SET NEW.{field.column} = OLD.{field.column}+1;
"""


    def _create_trigger(self, field):
        import MySQLdb as Database
        from warnings import filterwarnings, resetwarnings

        filterwarnings('ignore', message='Trigger does not exist', category=Database.Warning)

        opts = field.model._meta
        trigger_name = get_trigger_name(field, opts)

        stm = self.sql.format(trigger_name=trigger_name, opts=opts, field=field)
        cursor = self.connection._clone().cursor()
        try:
            cursor.execute(stm)
        except (BaseException, _mysql_exceptions.ProgrammingError) as exc:
            errno, message = exc.args
            if errno != 2014:
                import traceback
                traceback.print_exc(exc)
                raise
        resetwarnings()
        return trigger_name

########NEW FILE########
__FILENAME__ = base
import logging
import re
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PgDatabaseWrapper
from concurrency.db.backends.common import TriggerMixin
from concurrency.db.backends.postgresql_psycopg2.creation import PgCreation

logger = logging.getLogger(__name__)


class DatabaseWrapper(TriggerMixin, PgDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = PgCreation(self)

    def list_triggers(self):
        cursor = self.cursor()
        stm = "select * from pg_trigger where tgname LIKE 'concurrency_%%'; "
        logger.debug(stm)
        cursor.execute(stm)
        return [m[1] for m in cursor.fetchall()]

    def drop_trigger(self, trigger_name):
        if not trigger_name in self.list_triggers():
            return []
        cursor = self.cursor()
        table_name = re.sub('^concurrency_(.*)_[ui]', '\\1', trigger_name)
        stm = "DROP TRIGGER %s ON %s;" % (trigger_name, table_name)
        logger.debug(stm)
        result = cursor.execute(stm)
        return result

########NEW FILE########
__FILENAME__ = creation
from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation
from concurrency.db.backends.utils import get_trigger_name


class PgCreation(DatabaseCreation):
    drop = "DROP TRIGGER {trigger_name}_u ON {opts.db_table};"

    sql = """
ALTER TABLE {opts.db_table} ALTER COLUMN {field.column} SET DEFAULT 1;

CREATE OR REPLACE FUNCTION {trigger_name}_su()
    RETURNS TRIGGER as
    '
    BEGIN
       NEW.{field.column} = OLD.{field.column} +1;
        RETURN NEW;
    END;
    ' language 'plpgsql';

CREATE OR REPLACE FUNCTION {trigger_name}_si()
    RETURNS TRIGGER as
    '
    BEGIN
       NEW.{field.column} = 1;
        RETURN NEW;
    END;
    ' language 'plpgsql';

CREATE TRIGGER {trigger_name}_u BEFORE UPDATE
    ON {opts.db_table} FOR EACH ROW
    EXECUTE PROCEDURE {trigger_name}_su();

CREATE TRIGGER {trigger_name}_i BEFORE INSERT
    ON {opts.db_table} FOR EACH ROW
    EXECUTE PROCEDURE {trigger_name}_si();
"""

    def _create_trigger(self, field):
        from django.db.utils import DatabaseError

        opts = field.model._meta
        trigger_name = get_trigger_name(field, opts)

        stm = self.sql.format(trigger_name=trigger_name,
                              opts=opts,
                              field=field)

        self.connection.drop_trigger('{}_i'.format(trigger_name))
        self.connection.drop_trigger('{}_u'.format(trigger_name))
        try:
            self.connection.cursor().execute(stm)

        except BaseException as exc:
            raise DatabaseError(exc)

        return trigger_name

########NEW FILE########
__FILENAME__ = base
# from django.db.backends.sqlite3.base import *
from django.db.backends.sqlite3.base import DatabaseWrapper as Sqlite3DatabaseWrapper
from concurrency.db.backends.common import TriggerMixin
from concurrency.db.backends.sqlite3.creation import Sqlite3Creation


class DatabaseWrapper(TriggerMixin, Sqlite3DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = Sqlite3Creation(self)

    def list_triggers(self):
        cursor = self.cursor()
        result = cursor.execute("select name from sqlite_master where type = 'trigger';")
        return [m[0] for m in result.fetchall()]

    def drop_trigger(self, trigger_name):
        cursor = self.cursor()
        result = cursor.execute("DROP TRIGGER IF EXISTS %s;" % trigger_name)
        return result

########NEW FILE########
__FILENAME__ = creation
from django.db.backends.sqlite3.creation import DatabaseCreation
from concurrency.db.backends.utils import get_trigger_name


class Sqlite3Creation(DatabaseCreation):
    sql = """
DROP TRIGGER IF EXISTS {trigger_name}_u; ##

CREATE TRIGGER {trigger_name}_u
AFTER UPDATE ON {opts.db_table}
BEGIN UPDATE {opts.db_table} SET {field.column} = {field.column}+1 WHERE {opts.pk.column} = NEW.{opts.pk.column};
END; ##

DROP TRIGGER IF EXISTS {trigger_name}_i; ##

CREATE TRIGGER {trigger_name}_i
AFTER INSERT ON {opts.db_table}
BEGIN UPDATE {opts.db_table} SET {field.column} = 0 WHERE {opts.pk.column} = NEW.{opts.pk.column};
END; ##
"""

    def _create_trigger(self, field):
        from django.db.utils import DatabaseError
        cursor = self.connection.cursor()

        opts = field.model._meta
        trigger_name = get_trigger_name(field, opts)

        stms = self.sql.split('##')
        for template in stms:
            stm = template.format(trigger_name=trigger_name,
                                  opts=opts,
                                  field=field)
            try:
                cursor.execute(stm)
            except BaseException as exc:
                raise DatabaseError(exc)

        return trigger_name

########NEW FILE########
__FILENAME__ = utils
def get_trigger_name(field, opts):
    """

    :param field: Field instance
    :param opts: Options (Model._meta)
    :return:
    """
    return 'concurrency_{1.db_table}'.format(field, opts)

########NEW FILE########
__FILENAME__ = compat
try:
    from django.db.transaction import atomic
except ImportError:
    from django.db.transaction import commit_on_success as atomic  # noqa

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import absolute_import, unicode_literals
from django.core.exceptions import ValidationError, SuspiciousOperation
from django.utils.translation import ugettext as _
from django.db import DatabaseError


class VersionChangedError(ValidationError):
    pass


class RecordModifiedError(DatabaseError):
    def __init__(self, *args, **kwargs):
        self.target = kwargs.pop('target')
        super(RecordModifiedError, self).__init__(*args, **kwargs)


# class InconsistencyError(DatabaseError):
#     pass


class VersionError(SuspiciousOperation):

    def __init__(self, message=None, code=None, params=None, *args, **kwargs):
        self.message = message or _("Version number is missing or has been tampered with")

########NEW FILE########
__FILENAME__ = fields
import time
import copy
import logging
from functools import update_wrapper
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields import Field
from django.db.models.signals import class_prepared, post_syncdb

from concurrency import forms
from concurrency.config import conf
from concurrency.core import ConcurrencyOptions, _wrap_model_save
from concurrency.api import get_revision_of_object, disable_concurrency
from concurrency.utils import refetch


logger = logging.getLogger(__name__)

OFFSET = int(time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, 0)))


def class_prepared_concurrency_handler(sender, **kwargs):
    if hasattr(sender, '_concurrencymeta'):
        origin = getattr(sender._concurrencymeta._base, '_concurrencymeta')
        local = copy.deepcopy(origin)
        setattr(sender, '_concurrencymeta', local)

        if hasattr(sender, 'ConcurrencyMeta'):
            sender._concurrencymeta.enabled = getattr(sender.ConcurrencyMeta, 'enabled')

        if not (sender._concurrencymeta._manually):
            _wrap_model_save(sender)

        setattr(sender, 'get_concurrency_version', get_revision_of_object)
    else:
        logger.debug('Skipped concurrency for %s' % sender)


def post_syncdb_concurrency_handler(sender, **kwargs):
    from django.db import connection

    if hasattr(connection.creation, '_create_trigger'):
        while _TRIGGERS:
            field = _TRIGGERS.pop()
            connection.creation._create_trigger(field)


class_prepared.connect(class_prepared_concurrency_handler, dispatch_uid='class_prepared_concurrency_handler')
post_syncdb.connect(post_syncdb_concurrency_handler, dispatch_uid='post_syncdb_concurrency_handler')

_TRIGGERS = []
class_prepared.connect(class_prepared_concurrency_handler, dispatch_uid='class_prepared_concurrency_handler')


class VersionField(Field):
    """ Base class """

    def __init__(self, **kwargs):
        self.manually = kwargs.pop('manually', False)

        verbose_name = kwargs.get('verbose_name', None)
        name = kwargs.get('name', None)
        db_tablespace = kwargs.get('db_tablespace', None)
        db_column = kwargs.get('db_column', None)
        help_text = kwargs.get('help_text', _('record revision number'))

        super(VersionField, self).__init__(verbose_name, name,
                                           help_text=help_text,
                                           default=1,
                                           db_tablespace=db_tablespace,
                                           db_column=db_column)

    def get_default(self):
        return 0

    def get_internal_type(self):
        return "BigIntegerField"

    def to_python(self, value):
        return int(value)

    def validate(self, value, model_instance):
        pass

    def formfield(self, **kwargs):
        kwargs['form_class'] = self.form_class
        kwargs['widget'] = forms.VersionField.widget
        return super(VersionField, self).formfield(**kwargs)

    def contribute_to_class(self, cls, name, virtual_only=False):
        super(VersionField, self).contribute_to_class(cls, name)
        if hasattr(cls, '_concurrencymeta'):
            return
        setattr(cls, '_concurrencymeta', ConcurrencyOptions())
        cls._concurrencymeta._field = self
        cls._concurrencymeta._base = cls
        cls._concurrencymeta._manually = self.manually

    def _set_version_value(self, model_instance, value):
        setattr(model_instance, self.attname, int(value))

    def pre_save(self, model_instance, add):
        if conf.PROTOCOL >= 2:
            if add:
                value = self._get_next_version(model_instance)
                self._set_version_value(model_instance, value)
            return getattr(model_instance, self.attname)
        value = self._get_next_version(model_instance)
        self._set_version_value(model_instance, value)
        return value

    @staticmethod
    def _wrap_save(func):
        from concurrency.api import concurrency_check

        def inner(self, force_insert=False, force_update=False, using=None, **kwargs):
            if self._concurrencymeta.enabled:
                concurrency_check(self, force_insert, force_update, using, **kwargs)
            return func(self, force_insert, force_update, using, **kwargs)

        return update_wrapper(inner, func)

    def _wrap_save_base(self, func):
        def _save_base(model_instance, raw=False, force_insert=False,
                       force_update=False, using=None, update_fields=None):
            if force_insert:
                with disable_concurrency(model_instance):
                    return func(model_instance, raw, force_insert, force_update, using, update_fields)
            return func(model_instance, raw, force_insert, force_update, using, update_fields)

        return update_wrapper(_save_base, func)

    def _wrap_do_update(self, func):
        def _do_update(model_instance, base_qs, using, pk_val, values, update_fields, forced_update):
            version_field = model_instance._concurrencymeta._field
            old_version = get_revision_of_object(model_instance)

            if not version_field.model._meta.abstract:
                if version_field.model is not base_qs.model:
                    return func(model_instance, base_qs, using, pk_val, values, update_fields, forced_update)

            for i, (field, _1, value) in enumerate(values):
                if field == version_field:
                    new_version = field._get_next_version(model_instance)
                    values[i] = (field, _1, new_version)
                    field._set_version_value(model_instance, new_version)
                    break

            if values:
                if model_instance._concurrencymeta.enabled and old_version:
                    filter_kwargs = {'pk': pk_val, version_field.attname: old_version}
                    updated = base_qs.filter(**filter_kwargs)._update(values) >= 1
                    if not updated:
                        version_field._set_version_value(model_instance, old_version)
                        updated = conf._callback(model_instance)
                else:
                    filter_kwargs = {'pk': pk_val}
                    updated = base_qs.filter(**filter_kwargs)._update(values) >= 1
            else:
                updated = base_qs.filter(pk=pk_val).exists()

            return updated

        return update_wrapper(_do_update, func)


class IntegerVersionField(VersionField):
    """
        Version Field that returns a "unique" version number for the record.

        The version number is produced using time.time() * 1000000, to get the benefits
        of microsecond if the system clock provides them.

    """
    form_class = forms.VersionField

    def _get_next_version(self, model_instance):
        old_value = getattr(model_instance, self.attname, 0)
        return max(int(old_value) + 1, (int(time.time() * 1000000) - OFFSET))


class AutoIncVersionField(VersionField):
    """
        Version Field increment the revision number each commit

    """
    form_class = forms.VersionField

    def _get_next_version(self, model_instance):
        return int(getattr(model_instance, self.attname, 0)) + 1


class TriggerVersionField(VersionField):
    """
        Version Field increment the revision number each commit

    """
    form_class = forms.VersionField

    def contribute_to_class(self, cls, name, virtual_only=False):
        _TRIGGERS.append(self)
        super(TriggerVersionField, self).contribute_to_class(cls, name)

    def _get_next_version(self, model_instance):
        # always returns the same value
        return int(getattr(model_instance, self.attname, 0))

    def pre_save(self, model_instance, add):
        # always returns the same value
        return int(getattr(model_instance, self.attname, 0))


    @staticmethod
    def _increment_version_number(obj):
        old_value = get_revision_of_object(obj)
        setattr(obj, obj._concurrencymeta._field.attname, int(old_value) + 1)

    @staticmethod
    def _wrap_save(func):
        from concurrency.api import concurrency_check

        def inner(self, force_insert=False, force_update=False, using=None, **kwargs):
            reload = kwargs.pop('refetch', False)
            if self._concurrencymeta.enabled and conf.PROTOCOL == 1:
                concurrency_check(self, force_insert, force_update, using, **kwargs)
            ret = func(self, force_insert, force_update, using, **kwargs)
            TriggerVersionField._increment_version_number(self)
            if reload:
                ret = refetch(self)
                setattr(self,
                        self._concurrencymeta._field.attname,
                        get_revision_of_object(ret))

            return ret

        return update_wrapper(inner, func)


try:
    from south.modelsinspector import add_introspection_rules

    rules = [
        (
            (IntegerVersionField, AutoIncVersionField, TriggerVersionField),
            [], {"verbose_name": ["verbose_name", {"default": None}],
                 "name": ["name", {"default": None}],
                 "help_text": ["help_text", {"default": ''}],
                 "db_column": ["db_column", {"default": None}],
                 "db_tablespace": ["db_tablespace", {"default": None}],
                 "default": ["default", {"default": 1}],
                 "manually": ["manually", {"default": False}]})
    ]

    add_introspection_rules(rules, [r"^concurrency\.fields\.IntegerVersionField",
                                    r"^concurrency\.fields\.AutoIncVersionField"])
except ImportError as e:
    from django.conf import settings

    if 'south' in settings.INSTALLED_APPS:
        raise e

########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import, unicode_literals
import django
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured, ValidationError
from django.core.signing import Signer, BadSignature
from django.forms import ModelForm, HiddenInput
from django.utils.importlib import import_module
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from concurrency.config import conf
from concurrency.core import _select_lock
from concurrency.exceptions import VersionError, RecordModifiedError


class ConcurrentForm(ModelForm):
    """ Simple wrapper to ModelForm that try to mitigate some concurrency error.
        Note that is always possible have a RecordModifiedError in model.save().
        Statistically form.clean() should catch most of the concurrent editing, but
        is good to catch RecordModifiedError in the view too.
    """

    def clean(self):
        try:
            if self.instance.pk:
                _select_lock(self.instance, self.cleaned_data[self.instance._concurrencymeta._field.name])

        except RecordModifiedError:
            if django.VERSION[1] < 6:
                self._update_errors({NON_FIELD_ERRORS: self.error_class([_('Record Modified')])})
            else:
                self._update_errors(ValidationError({NON_FIELD_ERRORS: self.error_class([_('Record Modified')])}))

        return super(ConcurrentForm, self).clean()


class VersionWidget(HiddenInput):
    """
    Widget that show the revision number using <div>

    Usually VersionField use `HiddenInput` as Widget to minimize the impact on the
    forms, in the Admin this produce a side effect to have the label *Version* without
    any value, you should use this widget to display the current revision number
    """

    def _format_value(self, value):
        if value:
            value = str(value)
        return value

    def render(self, name, value, attrs=None):
        ret = super(VersionWidget, self).render(name, value, attrs)
        label = ''
        if isinstance(value, SignedValue):
            label = str(value).split(':')[0]
        elif value is not None:
            label = str(value)

        return mark_safe("%s<div>%s</div>" % (ret, label))


class VersionFieldSigner(Signer):
    def sign(self, value):
        if not value:
            return None
        return super(VersionFieldSigner, self).sign(value)


def get_signer():
    path = conf.FIELD_SIGNER
    i = path.rfind('.')
    module, attr = path[:i], path[i + 1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error loading concurrency signer %s: "%s"' % (module, e))
    try:
        signer_class = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a valid signer named "%s"' % (module, attr))
    return signer_class()


class SignedValue(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if self.value:
            return str(self.value)
        else:
            return ''


class VersionField(forms.IntegerField):
    widget = HiddenInput  # Default widget to use when rendering this type of Field.
    hidden_widget = HiddenInput  # Default widget to use when rendering this as "hidden".

    def __init__(self, *args, **kwargs):
        self._signer = kwargs.pop('signer', get_signer())
        kwargs.pop('min_value', None)
        kwargs.pop('max_value', None)
        kwargs['required'] = True
        kwargs['initial'] = None
        kwargs.setdefault('widget', HiddenInput)
        super(VersionField, self).__init__(*args, **kwargs)

    def bound_data(self, data, initial):
        return SignedValue(data)

    def prepare_value(self, value):
        if isinstance(value, SignedValue):
            return value
        elif value is None:
            return ''
        return SignedValue(self._signer.sign(value))

    def to_python(self, value):
        try:
            if value not in (None, '', 'None'):
                return int(self._signer.unsign(value))
            return 0
        except (BadSignature, ValueError):
            raise VersionError(value)

    def widget_attrs(self, widget):
        return {}


# class DateVersionField(forms.DateTimeField):
#     widget = HiddenInput  # Default widget to use when rendering this type of Field.
#     hidden_widget = HiddenInput  # Default widget to use when rendering this as "hidden".
#
#     def __init__(self, *args, **kwargs):
#         kwargs.pop('input_formats', None)
#         kwargs['required'] = True
#         kwargs['initial'] = None
#         kwargs['widget'] = None
#         super(DateVersionField, self).__init__(None, *args, **kwargs)
#
#     def to_python(self, value):
#         value = super(DateVersionField, self).to_python(value)
#         if value in validators.EMPTY_VALUES:
#             return timezone.now()
#         return value
#
#     def widget_attrs(self, widget):
#         return {}

########NEW FILE########
__FILENAME__ = triggers
# -*- coding: utf-8 -*-
from optparse import make_option
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.db import connections
from concurrency.db.compat import atomic
from concurrency.utils import create_triggers, get_triggers, drop_triggers


class Command(BaseCommand):
    args = ''
    help = 'register Report classes and create one ReportConfiguration per each'
    option_list = BaseCommand.option_list + (
        make_option('-d', '--database',
                    action='store',
                    dest='database',
                    default=None,
                    help='limit to this database'),
        make_option('-t', '--trigger',
                    action='store',
                    dest='trigger',
                    default=None,
                    help='limit to this trigger name'))

    def _list(self, databases):
        FMT = "{:20} {}\n"
        self.stdout.write(FMT.format('DATABASE', 'TRIGGERS'))
        for alias, triggers in get_triggers(databases).items():
            self.stdout.write(FMT.format(alias, ", ".join(triggers)))
        self.stdout.write('')

    def handle(self, cmd='list', *args, **options):
        database = options['database']
        if database is None:
            databases = [alias for alias in connections]
        else:
            databases = [database]

        with atomic():
            try:
                if cmd == 'list':
                    self._list(databases)
                elif cmd == 'create':
                    create_triggers(databases)
                    self._list(databases)
                elif cmd == 'drop':
                    drop_triggers(databases)
                    self._list(databases)
                else:
                    raise Exception()
            except ImproperlyConfigured as e:
                self.stdout.write(self.style.ERROR(e))

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.core.signals import got_request_exception
from django.core.urlresolvers import get_callable
from concurrency.config import conf
from concurrency.exceptions import RecordModifiedError


class ConcurrencyMiddleware(object):
    """ Intercept :ref:`RecordModifiedError` and invoke a callable defined in
    :setting:`CONCURRECY_HANDLER409` passing the request and the object.

    """
    def process_exception(self, request, exception):
        if isinstance(exception, RecordModifiedError):
            got_request_exception.send(sender=self, request=request)
            callback = get_callable(conf.HANDLER409)
            return callback(request, target=exception.target)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = concurrency
from __future__ import absolute_import
from django.template import Library
from django.templatetags.l10n import unlocalize
from django.utils.safestring import mark_safe
from concurrency.api import get_revision_of_object
from concurrency.fields import VersionField

register = Library()


@register.filter
def identity(obj):
    """
    returns a string representing "<pk>,<version>" of the passed object
    """
    if hasattr(obj, '_concurrencymeta'):
        return mark_safe("{0},{1}".format(unlocalize(obj.pk), get_revision_of_object(obj)))
    else:
        return mark_safe(unlocalize(obj.pk))


@register.filter
def version(obj):
    """
    returns the value of the VersionField of the passed object
    """
    return get_revision_of_object(obj)


@register.filter
def is_version(field):
    """
    returns True if passed argument is a VersionField instance
    """
    return isinstance(field, VersionField)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
import warnings
from django.core.exceptions import ImproperlyConfigured
from django.db import router, connections
from django.db.models.loading import get_models, get_apps
import sys
from concurrency.exceptions import RecordModifiedError


logger = logging.getLogger(__name__)


def deprecated(replacement=None, version=None):
    """A decorator which can be used to mark functions as deprecated.
    replacement is a callable that will be called with the same args
    as the decorated function.

    >>> @deprecated()
    ... def foo(x):
    ...     return x
    ...
    >>> ret = foo(1)
    DeprecationWarning: foo is deprecated
    >>> ret
    1
    >>>
    >>>
    >>> def newfun(x):
    ...     return 0
    ...
    >>> @deprecated(newfun)
    ... def foo(x):
    ...     return x
    ...
    >>> ret = foo(1)
    DeprecationWarning: foo is deprecated; use newfun instead
    >>> ret
    0
    >>>
    """

    def outer(oldfun):  # pragma: no cover
        def inner(*args, **kwargs):
            msg = "%s is deprecated" % oldfun.__name__
            if version is not None:
                msg += "will be removed in version %s;" % version
            if replacement is not None:
                msg += "; use %s instead" % (replacement)
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            if callable(replacement):
                return replacement(*args, **kwargs)
            else:
                return oldfun(*args, **kwargs)

        return inner

    return outer


class ConcurrencyTestMixin(object):
    """
    Mixin class to test Models that use `VersionField`

    this class offer a simple test scenario. Its purpose is to discover
    some conflict in the `save()` inheritance::

        from concurrency.utils import ConcurrencyTestMixin
        from myproject.models import MyModel

        class MyModelTest(ConcurrencyTestMixin, TestCase):
            concurrency_model = TestModel0
            concurrency_kwargs = {'username': 'test'}

    """

    concurrency_model = None
    concurrency_kwargs = {}

    def _get_concurrency_target(self, **kwargs):
        # WARNING this method must be idempotent. ie must returns
        # always a fresh copy of the record
        args = dict(self.concurrency_kwargs)
        args.update(kwargs)
        return self.concurrency_model.objects.get_or_create(**args)[0]

    def test_concurrency_conflict(self):
        import concurrency.api as api

        target = self._get_concurrency_target()
        target_copy = self._get_concurrency_target()
        v1 = api.get_revision_of_object(target)
        v2 = api.get_revision_of_object(target_copy)
        assert v1 == v2, "got same row with different version (%s/%s)" % (v1, v2)
        target.save()
        assert target.pk is not None  # sanity check
        self.assertRaises(RecordModifiedError, target_copy.save)

    def test_concurrency_safety(self):
        import concurrency.api as api

        target = self.concurrency_model()
        version = api.get_revision_of_object(target)
        self.assertFalse(bool(version), "version is not null %s" % version)

    def test_concurrency_management(self):
        target = self.concurrency_model
        self.assertTrue(hasattr(target, '_concurrencymeta'),
                        "%s is not under concurrency management" % self.concurrency_model)
        info = getattr(target, '_concurrencymeta', None)
        revision_field = info._field

        self.assertTrue(revision_field in target._meta.fields,
                        "%s: version field not in meta.fields" % self.concurrency_model)


class ConcurrencyAdminTestMixin(object):
    pass


def get_triggers(databases):
    triggers = {}
    for alias in databases:
        connection = connections[alias]
        if hasattr(connection, 'list_triggers'):
            triggers[alias] = [trigger_name for trigger_name in connection.list_triggers()]
    return triggers


def drop_triggers(databases, stdout=sys.stdout):
    triggers = {}
    for alias in databases:
        connection = connections[alias]
        if hasattr(connection, 'drop_triggers'):
            connection.drop_triggers()

    return triggers


def create_triggers(databases, stdout=sys.stdout):
    from concurrency.fields import TriggerVersionField

    for app in get_apps():
        for model in get_models(app):
            if hasattr(model, '_concurrencymeta') and \
                    isinstance(model._concurrencymeta._field, TriggerVersionField):
                # stdout.write('Found concurrent model `%s`\n' % model.__name__)
                alias = router.db_for_write(model)
                if alias in databases:
                    connection = connections[alias]
                    if hasattr(connection.creation, '_create_trigger'):
                        connections[alias].creation._create_trigger(model._concurrencymeta._field)
                        # stdout.write('\tCreated trigger`%s`\n' % name)
                    else:
                        raise ImproperlyConfigured('TriggerVersionField need concurrency database backend')


def refetch(model_instance):
    """
    Reload model instance from the database
    """
    return model_instance.__class__.objects.get(pk=model_instance.pk)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.template import loader
from django.template.base import TemplateDoesNotExist, Template
from django.template.context import RequestContext
from concurrency.exceptions import RecordModifiedError


class ConflictResponse(HttpResponse):
    status_code = 409


handler409 = 'concurrency.views.conflict'


def callback(target, *args, **kwargs):
    raise RecordModifiedError(_('Record has been modified'), target=target)


def conflict(request, target=None, template_name='409.html'):
    """409 error handler.

    Templates: `409.html`
    Context:
    `target` : The model to save
    `saved`  : The object stored in the db that produce the conflict or None if not found (ie. deleted)
    `request_path` : The path of the requested URL (e.g., '/app/pages/bad_page/')

    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        template = Template(
            '<h1>Conflict</h1>'
            '<p>The request was unsuccessful due to a conflict. '
            'The object changed during the transaction.</p>')
    try:
        saved = target.__class__._default_manager.get(pk=target.pk)
    except target.__class__.DoesNotExist:
        saved = None
    ctx = RequestContext(request, {'target': target,
                                   'saved': saved,
                                   'request_path': request.path})
    return ConflictResponse(template.render(ctx))

########NEW FILE########
__FILENAME__ = conftest
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

def pytest_collection_modifyitems(items):
    pass


def pytest_configure(config):
    from django.conf import settings

    if not settings.configured:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

    try:
        from django.apps import AppConfig
        import django
        django.setup()
    except ImportError:
        pass

def runtests(args=None):
    import pytest

    if not args:
        args = []

    if not any(a for a in args[1:] if not a.startswith('-')):
        args.append('concurrency')

    sys.exit(pytest.main(args))


if __name__ == '__main__':
    runtests(sys.argv)

########NEW FILE########
__FILENAME__ = backends
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class AnyUserBackend(ModelBackend):
    supports_object_permissions = False
    supports_anonymous_user = True

    def get_all_permissions(self, user_obj, obj=None):
        if settings.DEBUG:
            return Permission.objects.all().values_list('content_type__app_label', 'codename').order_by()
        return super(AnyUserBackend, self).get_all_permissions(user_obj, obj)

    def get_group_permissions(self, user_obj, obj=None):
        if settings.DEBUG:
            return Permission.objects.all().values_list('content_type__app_label', 'codename').order_by()
        return super(AnyUserBackend, self).get_group_permissions(user_obj, obj)

    def has_perm(self, user_obj, perm, obj=None):
        if settings.DEBUG:
            return True
        return super(AnyUserBackend, self).has_perm(user_obj, perm, obj)

    def has_module_perms(self, user_obj, app_label):
        if settings.DEBUG:
            return True
        return super(AnyUserBackend, self).has_module_perms(user_obj, app_label)

########NEW FILE########
__FILENAME__ = admin
from concurrency.admin import ConcurrentModelAdmin
from .models import DemoModel, proxy_factory


class DemoModelAdmin(ConcurrentModelAdmin):
    # list_display = [f.name for f in DemoModel._meta.fields]
    list_display = ('id', 'char', 'integer')
    list_display_links = ('id', )
    list_editable = ('char', 'integer')
    actions = None


try:
    from import_export.admin import ImportExportMixin

    class ImportExportDemoModelAdmin(ImportExportMixin, ConcurrentModelAdmin):
        # list_display = [f.name for f in DemoModel._meta.fields]
        list_display = ('id', 'char', 'integer')
        list_display_links = ('id', )
        list_editable = ('char', 'integer')
        actions = None

except:
    pass


def register(site):
    site.register(DemoModel, DemoModelAdmin)
    site.register(proxy_factory("ImportExport"), ImportExportDemoModelAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from concurrency import fields


class DemoModel(models.Model):
    version = fields.IntegerVersionField()
    char = models.CharField(max_length=255)
    integer = models.IntegerField()

    class Meta:
        app_label = 'demoapp'


class ProxyDemoModel(DemoModel):
    class Meta:
        app_label = 'demoapp'
        proxy = True


def proxy_factory(name):
    return type(name, (ProxyDemoModel,), {'__module__': ProxyDemoModel.__module__,
                                          'Meta': type('Meta', (object,), {'proxy': True, 'app_label': 'demoapp'})})

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from six import StringIO
import os
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django_webtest import WebTest
from concurrency.api import disable_concurrency
from .models import DemoModel

try:
    from import_export.admin import ImportExportMixin  # NOQA
    import csv

    class TestAdminEdit(WebTest):

        def setUp(self):
            self.user = User.objects.get_or_create(is_superuser=True,
                                                   is_staff=True,
                                                   is_active=True,
                                                   email='sax@example.com',
                                                   username='sax')

        def test_export_csv(self):
            url = reverse('admin:demoapp_importexport_changelist')
            res = self.app.get(url, user='sax')
            res = res.click(_("Export"))
            res.form['file_format'] = 0
            res = res.form.submit()
            io = StringIO(res.body)
            c = csv.reader(io)
            list(c)

        def get_file_to_upload(self, filename):
            here = os.path.dirname(__file__)
            filepath = os.path.join(here, "fixtures", filename)
            return open(filepath).read()

        def test_import_csv_no_version(self):
            url = reverse('admin:demoapp_importexport_changelist')
            res = self.app.get(url, user='sax')
            res = res.click(_("Import"))
            res.form['import_file'] = ("import_file2",
                                       self.get_file_to_upload("data_no_version.csv"))
            res.form['input_format'] = 0
            res = res.form.submit()
            res = res.form.submit()

        def test_import_csv_with_version(self):
            url = reverse('admin:demoapp_importexport_changelist')
            res = self.app.get(url, user='sax')
            res = res.click(_("Import"))
            with disable_concurrency(DemoModel):
                res.form['import_file'] = ("import_file2",
                                           self.get_file_to_upload("data_with_version.csv"))
                res.form['input_format'] = 0
                res = res.form.submit()
                res = res.form.submit()

except:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns


urlpatterns = patterns('',)

########NEW FILE########
__FILENAME__ = views
from diff_match_patch import diff_match_patch
from concurrency.views import ConflictResponse
from django.template import loader
from django.utils.safestring import mark_safe
from django.template.context import RequestContext


def get_diff(current, stored):
    data = []
    dmp = diff_match_patch()
    fields = current._meta.fields
    for field in fields:
        v1 = getattr(current, field.name, "")
        v2 = getattr(stored, field.name, "")
        diff = dmp.diff_main(unicode(v1), unicode(v2))
        dmp.diff_cleanupSemantic(diff)
        html = dmp.diff_prettyHtml(diff)
        html = mark_safe(html)
        data.append((field, v1, v2, html))
    return data


def conflict(request, target=None, template_name='409.html'):
    template = loader.get_template(template_name)
    try:
        saved = target.__class__._default_manager.get(pk=target.pk)
        diff = get_diff(target, saved)
    except target.__class__.DoesNotExists:
        saved = None
        diff = None

    ctx = RequestContext(request, {'target': target,
                                   'diff': diff,
                                   'saved': saved,
                                   'request_path': request.path})
    return ConflictResponse(template.render(ctx))


########NEW FILE########
__FILENAME__ = settings
from tests.settings import *
ROOT_URLCONF = 'demoproject.urls'
SECRET_KEY = ';klkj;okj;lkn;lklj;lkj;kjmlliuewhy2ioqwjdkh'

INSTALLED_APPS = ['django.contrib.auth',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django.contrib.sites',
                  'django.contrib.messages',
                  'django.contrib.staticfiles',
                  'django.contrib.admin',
                  'concurrency',
                  'demoproject.demoapp',
                  'django_extensions',
                  'tests']
# AUTHENTICATION_BACKENDS = ('demoproject.backends.AnyUserBackend',)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include
# from django.contrib.admin import ModelAdmin
from django.contrib import admin
from django.contrib.auth.models import User, Group
# from demoproject.demoapp.admin import DemoModelAdmin, ImportExportDemoModelAdmin
# from demoapp.admin import DemoModelAdmin, ImportExportDemoModelAdmin
# from demoapp.models import DemoModel, proxy_factory
from django.db import IntegrityError


class PublicAdminSite(admin.AdminSite):
    def has_permission(self, request):
        request.user = User.objects.get_or_create(username='sax')[0]
        return True


# public_site = PublicAdminSite()
admin.autodiscover()
# public_site.register([User, Group])
#
# for e, v in admin.site._registry.items():
#     public_site._registry[e] = v

# public_site.register(DemoModel, DemoModelAdmin)
# public_site.register(proxy_factory("ImportExport"), ImportExportDemoModelAdmin)
# u = User.objects.get_or_create(username='sax')[0]
# u.is_superuser=True
# u.set_password('123')
# u.save()

urlpatterns = patterns('',
                       # (r'^admin/', include(include(public_site.urls))),
                       (r'', include(include(admin.site.urls))))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demoproject project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
here =  os.path.abspath(os.path.join(os.path.dirname(__file__)))
rel = lambda *args: os.path.join(here, *args)

sys.path.insert(0, rel(os.pardir))


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Grappelli documentation build configuration file, created by
# sphinx-quickstart on Sun Dec  5 19:11:46 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from django.conf import settings

settings.configure()

import concurrency
#os.environ['DJANGO_SETTINGS_MODULE']= 'django.conf.global_settings'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "_ext")))
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.todo',
              'sphinx.ext.graphviz',
              'sphinx.ext.intersphinx',
              'sphinx.ext.doctest',
              'sphinx.ext.extlinks',
              'sphinx.ext.autosummary',
              'sphinx.ext.coverage',
              'sphinx.ext.viewcode',
              'version',
              'github',
              'djangodocs']
intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/v2.7.3/', None),
    'django': ('http://django.readthedocs.org/en/latest/', None),
    'sphinx': ('http://sphinx.readthedocs.org/en/latest/', None),
}
extlinks = {'issue': ('https://github.com/saxix/django-concurrency/issues/%s', 'issue #'),
            'django_issue': ('https://code.djangoproject.com/ticket/%s', 'issue #'),

            }
next_version = '0.9'
todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Concurrency'
copyright = u'2012, Stefano Apostolico'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, concurrency.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = concurrency.get_version()


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

if os.environ.get('READTHEDOCS', None) == 'True':
    html_theme = "sphinx_rtd_theme"
else:
    import sphinx_rtd_theme
    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.


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
#html_static_path = ['_static']

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
htmlhelp_basename = 'djangoconcurrencydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'DjangoConcurrency.tex', u'Django Concurrency Documentation',
     u'Stefano Apostolico', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'djangoconcurrency', u'Django Concurrency Documentation',
     [u'Stefano Apostolico'], 1)
]

########NEW FILE########
__FILENAME__ = djangodocs
"""
Sphinx plugins for Django documentation.
"""
import json
import os
import re

from sphinx import addnodes, __version__ as sphinx_ver
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import SmartyPantsHTMLTranslator
from sphinx.util.console import bold
from sphinx.util.compat import Directive

# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')

def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s; field lookup type",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename      = "djadmin",
        indextemplate = "pair: %s; django-admin command",
        parse_node    = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename      = "djadminopt",
        indextemplate = "pair: %s; django-admin command-line option",
        parse_node    = parse_django_adminopt_node,
    )
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_builder(DjangoStandaloneHTMLBuilder)


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        if len(self.arguments) > 1:
            msg = """Only one argument accepted for directive '{directive_name}::'.
            Comments should be provided as content,
            not as an extra argument.""".format(directive_name=self.name)
            raise self.error(msg)

        env = self.state.document.settings.env
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)

        if self.arguments[0] == env.config.next_version:
            node['version'] = "Development version"
        else:
            node['version'] = self.arguments[0]

        node['type'] = self.name
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


class DjangoHTMLTranslator(SmartyPantsHTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self._table_row_index = 0 # Needed by Sphinx
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

    # <big>? Really?
    def visit_desc_parameterlist(self, node):
        self.body.append('(')
        self.first_param = 1
        self.param_separator = node.child_text_separator

    def depart_desc_parameterlist(self, node):
        self.body.append(')')

    if sphinx_ver < '1.0.8':
        #
        # Don't apply smartypants to literal blocks
        #
        def visit_literal_block(self, node):
            self.no_smarty += 1
            SmartyPantsHTMLTranslator.visit_literal_block(self, node)

        def depart_literal_block(self, node):
            SmartyPantsHTMLTranslator.depart_literal_block(self, node)
            self.no_smarty -= 1

    #
    # Turn the "new in version" stuff (versionadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to change
    # that to accommodate other language docs, but I can't work out how to make
    # that work.
    #
    version_text = {
        'deprecated':       'Deprecated in Django %s',
        'versionchanged':   'Changed in Django %s',
        'versionadded':     'New in Django %s',
    }

    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        title = "%s%s" % (
            self.version_text[node['type']] % node['version'],
            ":" if len(node) else "."
        )
        self.body.append('<span class="title">%s</span> ' % title)

    def depart_versionmodified(self, node):
        self.body.append("</div>\n")

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get('ids', [])
        node['ids'] = ['s-' + i for i in old_ids]
        node['ids'].extend(old_ids)
        SmartyPantsHTMLTranslator.visit_section(self, node)
        node['ids'] = old_ids

def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += addnodes.desc_name(title, title)
    return sig

def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx.domains.std import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not count:
        for m in simple_option_desc_re.finditer(sig):
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
            count += 1
    if not firstname:
        raise ValueError
    return firstname


class DjangoStandaloneHTMLBuilder(StandaloneHTMLBuilder):
    """
    Subclass to add some extra things we need.
    """

    name = 'djangohtml'

    def finish(self):
        super(DjangoStandaloneHTMLBuilder, self).finish()
        self.info(bold("writing templatebuiltins.js..."))
        xrefs = self.env.domaindata["std"]["objects"]
        templatebuiltins = {
            "ttags": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatetag" and l == "ref/templates/builtins"],
            "tfilters": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatefilter" and l == "ref/templates/builtins"],
        }
        outfilename = os.path.join(self.outdir, "templatebuiltins.js")
        with open(outfilename, 'w') as fp:
            fp.write('var django_template_builtins = ')
            json.dump(templatebuiltins, fp)
            fp.write(';\n')

########NEW FILE########
__FILENAME__ = github
"""Define text roles for GitHub

* ghissue - Issue
* ghpull - Pull Request
* ghuser - User

Adapted from bitbucket example here:
https://bitbucket.org/birkenfeld/sphinx-contrib/src/tip/bitbucket/sphinxcontrib/bitbucket.py

Authors
-------

* Doug Hellmann
* Min RK
"""
#
# Original Copyright (c) 2010 Doug Hellmann.  All rights reserved.
#

from docutils import nodes, utils
from docutils.parsers.rst.roles import set_classes


def make_link_node(rawtext, app, type, slug, options):
    """Create a link to a github resource.

    :param rawtext: Text being replaced with link node.
    :param app: Sphinx application context
    :param type: Link type (issues, changeset, etc.)
    :param slug: ID of the thing to link to
    :param options: Options dictionary passed to role func.
    """

    try:
        base = app.config.github_project_url
        if not base:
            raise AttributeError
        if not base.endswith('/'):
            base += '/'
    except AttributeError as err:
        raise ValueError('github_project_url configuration value is not set (%s)' % str(err))

    ref = base + type + '/' + slug + '/'
    set_classes(options)
    prefix = "#"
    if type == 'pull':
        prefix = "PR " + prefix
    node = nodes.reference(rawtext, prefix + utils.unescape(slug), refuri=ref,
                           **options)
    return node


def ghissue_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub issue.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """

    try:
        issue_num = int(text)
        if issue_num <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'GitHub issue number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    app = inliner.document.settings.env.app
    #app.info('issue %r' % text)
    if 'pull' in name.lower():
        category = 'pull'
    elif 'issue' in name.lower():
        category = 'issues'
    else:
        msg = inliner.reporter.error(
            'GitHub roles include "ghpull" and "ghissue", '
            '"%s" is invalid.' % name, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    node = make_link_node(rawtext, app, category, str(issue_num), options)
    return [node], []


def ghuser_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub user.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    app = inliner.document.settings.env.app
    #app.info('user link %r' % text)
    ref = 'https://www.github.com/' + text
    node = nodes.reference(rawtext, text, refuri=ref, **options)
    return [node], []


def ghcommit_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub commit.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    app = inliner.document.settings.env.app
    #app.info('user link %r' % text)
    try:
        base = app.config.github_project_url
        if not base:
            raise AttributeError
        if not base.endswith('/'):
            base += '/'
    except AttributeError as err:
        raise ValueError('github_project_url configuration value is not set (%s)' % str(err))

    ref = base + text
    node = nodes.reference(rawtext, text[:6], refuri=ref, **options)
    return [node], []


def setup(app):
    """Install the plugin.

    :param app: Sphinx application context.
    """
    app.info('Initializing GitHub plugin')
    app.add_role('ghissue', ghissue_role)
    app.add_role('ghpull', ghissue_role)
    app.add_role('ghuser', ghuser_role)
    app.add_role('ghcommit', ghcommit_role)
    app.add_config_value('github_project_url', None, 'env')
    return

########NEW FILE########
__FILENAME__ = version
import re
from sphinx import addnodes, roles
from sphinx.util.console import bold
from sphinx.util.compat import Directive

# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="templatetag",
        rolename="ttag",
        indextemplate="pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename="templatefilter",
        rolename="tfilter",
        indextemplate="pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename="fieldlookup",
        rolename="lookup",
        indextemplate="pair: %s; field lookup type",
    )
    app.add_config_value('next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_crossref_type(
        directivename="release",
        rolename="release",
        indextemplate="pair: %s; release",
    )


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        arg0 = self.arguments[0]
        is_nextversion = env.config.next_version == arg0
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)
        if is_nextversion:
            node['version'] = "Development version"
        else:
            if len(self.arguments) == 1:
            #                linktext = 'Please, see the Changelog <0_0_4>'
            #                xrefs = roles.XRefRole()('release', linktext, linktext, self.lineno, self.state)
            #                node.extend(xrefs[0])

                linktext = 'Please, see the Changelog <changes>'
                xrefs = roles.XRefRole()('doc', linktext, linktext, self.lineno, self.state)
                node.extend(xrefs[0])

        node['version'] = arg0
        node['type'] = self.name
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1], self.lineno + 1)
            node.extend(inodes)
            if self.content:
                self.state.nested_parse(self.content, self.content_offset, node)
            ret = ret + messages
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


########NEW FILE########
__FILENAME__ = admin
from django.contrib.admin.sites import NotRegistered
from django.contrib import admin
from concurrency.admin import ConcurrentModelAdmin
from tests.models import *  # noqa
from tests.models import NoActionsConcurrentModel, ListEditableConcurrentModel


class ListEditableModelAdmin(ConcurrentModelAdmin):
    list_display = ('__unicode__', 'version', 'username')
    list_editable = ('username', )
    ordering = ('id', )


class NoActionsModelAdmin(ConcurrentModelAdmin):
    list_display = ('__unicode__', 'version', 'username')
    list_editable = ('username', )
    ordering = ('id', )
    actions = None


class ActionsModelAdmin(ConcurrentModelAdmin):
    list_display = ('__unicode__', 'version', 'username')
    actions = ['dummy_action']
    ordering = ('id', )

    def dummy_action(self, request, queryset):
        for el in queryset:
            el.username = '**action_update**'
            el.save()


def admin_register(model, modeladmin=ConcurrentModelAdmin):
    try:
        admin.site.unregister(model)
    except NotRegistered:  # pragma: no cover
        pass
    admin.site.register(model, modeladmin)


def admin_register_models():
    admin_register(SimpleConcurrentModel, ActionsModelAdmin)
    admin_register(ProxyModel, ListEditableModelAdmin)
    admin_register(InheritedModel, ActionsModelAdmin)
    admin_register(NoActionsConcurrentModel, NoActionsModelAdmin)
    admin_register(ListEditableConcurrentModel, ListEditableModelAdmin)


admin_register_models()

########NEW FILE########
__FILENAME__ = base
import django
import pytest
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django_webtest import WebTestMixin
from tests.admin import admin_register_models

SENTINEL = '**concurrent_update**'

from concurrency.api import apply_concurrency_check
from django.contrib.auth.models import Permission
from concurrency.fields import IntegerVersionField

apply_concurrency_check(Permission, 'version', IntegerVersionField)

DJANGO_TRUNK = django.VERSION[:2] >= 7


win32only = pytest.mark.skipif("sys.platform != 'win32'")

skipIfDjangoVersion = lambda v: pytest.mark.skipif(django.VERSION[:2] >= v,
                                       reason="Skip if django>={}".format(v))


class AdminTestCase(WebTestMixin, TransactionTestCase):
    urls = 'tests.urls'

    def setUp(self):
        super(AdminTestCase, self).setUp()
        self.user, __ = User.objects.get_or_create(is_superuser=True,
                                                   is_staff=True,
                                                   is_active=True,
                                                   email='sax@example.com',
                                                   username='sax')

        admin_register_models()


# class DjangoAdminTestCase(TransactionTestCase):
#     urls = 'concurrency.tests.urls'
#     MIDDLEWARE_CLASSES = global_settings.MIDDLEWARE_CLASSES
#     AUTHENTICATION_BACKENDS = global_settings.AUTHENTICATION_BACKENDS
#
#     def setUp(self):
#         super(DjangoAdminTestCase, self).setUp()
#         self.sett = self.settings(
#             #INSTALLED_APPS=INSTALLED_APPS,
#             MIDDLEWARE_CLASSES=self.MIDDLEWARE_CLASSES,
#             AUTHENTICATION_BACKENDS=self.AUTHENTICATION_BACKENDS,
#             PASSWORD_HASHERS=('django.contrib.auth.hashers.MD5PasswordHasher',),  # fastest hasher
#             STATIC_URL='/static/',
#             SOUTH_TESTS_MIGRATE=False,
#             TEMPLATE_DIRS=(os.path.join(os.path.dirname(__file__), 'templates'),))
#         self.sett.enable()
#         django.core.management._commands = None  # reset commands cache
#         django.core.management.call_command('syncdb', verbosity=0)
#
#         # admin_register(TestModel0)
#         # admin_register(TestModel1, TestModel1Admin)
#
#         self.user, __ = User.objects.get_or_create(username='sax',
#                                                    is_active=True,
#                                                    is_staff=True,
#                                                    is_superuser=True)
#         self.user.set_password('123')
#         self.user.save()
#         self.client.login(username=self.user.username, password='123')
#         # self.target, __ = TestModel0.objects.get_or_create(username='aaa')
#         # self.target1, __ = TestModel1.objects.get_or_create(username='bbb')
#
#     def tearDown(self):
#         super(DjangoAdminTestCase, self).tearDown()
#         self.sett.disable()
#         # admin_unregister(TestModel0, TestModel1)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.contrib.auth.models import Group
from django.db import models
from concurrency.fields import IntegerVersionField, AutoIncVersionField, TriggerVersionField

__all__ = ['SimpleConcurrentModel', 'AutoIncConcurrentModel',
           'ProxyModel', 'InheritedModel', 'CustomSaveModel',
           'ConcreteModel']


class SimpleConcurrentModel(models.Model):
    version = IntegerVersionField(db_column='cm_version_id')
    username = models.CharField(max_length=30, blank=True, null=True, unique=True)
    date_field = models.DateField(blank=True, null=True)

    class Meta:
        app_label = 'concurrency'
        verbose_name = "SimpleConcurrentModel"
        verbose_name_plural = "SimpleConcurrentModels"

    def __unicode__(self):
        return "{0.__class__.__name__} #{0.pk}".format(self)


class AutoIncConcurrentModel(models.Model):
    version = AutoIncVersionField(db_column='cm_version_id')
    username = models.CharField(max_length=30, blank=True, null=True)
    date_field = models.DateField(blank=True, null=True)

    class Meta:
        app_label = 'concurrency'
        verbose_name = "AutoIncConcurrentModel"
        verbose_name_plural = "AutoIncConcurrentModel"

    def __unicode__(self):
        return "{0.__class__.__name__} #{0.pk}".format(self)


class TriggerConcurrentModel(models.Model):
    version = TriggerVersionField(db_column='cm_version_id')
    username = models.CharField(max_length=30, blank=True, null=True)
    count = models.IntegerField(default=0)

    class Meta:
        app_label = 'concurrency'
        verbose_name = "TriggerConcurrentModel"
        verbose_name_plural = "TriggerConcurrentModels"

    def __unicode__(self):
        return "{0.__class__.__name__} #{0.pk}".format(self)


class ProxyModel(SimpleConcurrentModel):
    class Meta:
        app_label = 'concurrency'
        proxy = True
        verbose_name = "ProxyModel"
        verbose_name_plural = "ProxyModels"


class InheritedModel(SimpleConcurrentModel):
    extra_field = models.CharField(max_length=30, blank=True, null=True, unique=True)

    class Meta:
        app_label = 'concurrency'


class CustomSaveModel(SimpleConcurrentModel):
    extra_field = models.CharField(max_length=30, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        super(CustomSaveModel, self).save(*args, **kwargs)

    class Meta:
        app_label = 'concurrency'


class AbstractModel(models.Model):
    version = IntegerVersionField(db_column='cm_version_id')
    username = models.CharField(max_length=30, blank=True, null=True, unique=True)

    class Meta:
        app_label = 'concurrency'
        abstract = True


class ConcreteModel(AbstractModel):
    pass

    class Meta:
        app_label = 'concurrency'

# class TestCustomUser(User):
#     version = IntegerVersionField(db_column='cm_version_id')
#
#     class Meta:
#         app_label = 'concurrency'
#
#     def __unicode__(self):
#         return "{0.__class__.__name__} #{0.pk}".format(self)


class TestModelGroup(Group):
    #HACK: this field is here because all tests relies on that
    # and we need a 'fresh' model to check for on-the-fly addition
    # of version field.  (added in concurrency 0.3.0)

    username = models.CharField('username', max_length=50)

    class Meta:
        app_label = 'concurrency'


# class TestModelGroupWithCustomSave(TestModelGroup):
#     class Meta:
#         app_label = 'concurrency'
#
#     def save(self, *args, **kwargs):
#         super(TestModelGroupWithCustomSave, self).save(*args, **kwargs)
#         return 222


class TestIssue3Model(models.Model):
    username = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    char_field = models.CharField(max_length=30, blank=True, null=True)
    date_field = models.DateField(blank=True, null=True)

    version = models.CharField(default='abc', max_length=10, blank=True, null=True)
    revision = IntegerVersionField(db_column='cm_version_id')

    class Meta:
        app_label = 'concurrency'


class ListEditableConcurrentModel(SimpleConcurrentModel):
    """ Proxy model used by admin related test.
    This allow to use multiple ModelAdmin configuration with the same 'real' model
    """

    class Meta:
        app_label = 'concurrency'
        proxy = True
        verbose_name = "ListEditableConcurrentModel"
        verbose_name_plural = "ListEditableConcurrentModels"


class NoActionsConcurrentModel(SimpleConcurrentModel):
    """ Proxy model used by admin related test.
    This allow to use multiple ModelAdmin configuration with the same 'real' model
    """

    class Meta:
        app_label = 'concurrency'
        proxy = True
        verbose_name = "NoActions-ConcurrentModel"
        verbose_name_plural = "NoActions-ConcurrentModels"


class ConcurrencyDisabledModel(SimpleConcurrentModel):
    dummy_char = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        app_label = 'concurrency'

    class ConcurrencyMeta:
        enabled = False

########NEW FILE########
__FILENAME__ = settings
import os
from tempfile import mktemp

DEBUG = True
STATIC_URL = '/static/'

SITE_ID = 1
ROOT_URLCONF = 'tests.urls'
SECRET_KEY = 'abc'
STATIC_ROOT = mktemp('static')
MEDIA_ROOT = mktemp('media')

INSTALLED_APPS = ['django.contrib.auth',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django.contrib.sites',
                  'django.contrib.messages',
                  'django.contrib.staticfiles',
                  'django.contrib.admin',
                  'concurrency',
                  'tests']

TEMPLATE_DIRS = ['tests/templates']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'full': {
            'format': '%(levelname)-8s: %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'verbose': {
            'format': '%(levelname)-8s: %(asctime)s %(name)-25s %(message)s'
        },
        'simple': {
            'format': '%(levelname)-8s %(asctime)s %(name)-25s %(funcName)s %(message)s'
        },
        'debug': {
            'format': '%(levelno)s:%(levelname)-8s %(name)s %(funcName)s:%(lineno)s:: %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'debug'
        }
    },
    'loggers': {
        'concurrency': {
            'handlers': ['null'],
            'propagate': False,
            'level': 'DEBUG'
        }
    }
}

DBNAME = os.environ.get('DBNAME', 'concurrency')
db = os.environ.get('DBENGINE', None)
if db == 'pg':
    DATABASES = {
        'default': {
            # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'ENGINE': 'concurrency.db.backends.postgresql_psycopg2',
            'NAME': DBNAME,
            'HOST': '127.0.0.1',
            'PORT': '',
            'USER': 'postgres',
            'PASSWORD': ''}}
elif db == 'mysql':
    DATABASES = {
        'default': {
            # 'ENGINE': 'django.db.backends.mysql',
            'ENGINE': 'concurrency.db.backends.mysql',
            'NAME': DBNAME,
            'HOST': '127.0.0.1',
            'PORT': '',
            'USER': 'root',
            'PASSWORD': '',
            'CHARSET': 'utf8',
            'COLLATION': 'utf8_general_ci',
            'TEST_CHARSET': 'utf8',
            'TEST_COLLATION': 'utf8_general_ci'}}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'concurrency.db.backends.sqlite3',
            'NAME': '%s.sqlite' % DBNAME,
            'HOST': '',
            'PORT': ''}}

########NEW FILE########
__FILENAME__ = test_admin_actions
# -*- coding: utf-8 -*-
from tests.base import AdminTestCase, SENTINEL, skipIfDjangoVersion
from tests.models import SimpleConcurrentModel
from tests.util import unique_id


class TestAdminActions(AdminTestCase):
    def _create_conflict(self, pk):
        u = SimpleConcurrentModel.objects.get(pk=pk)
        u.username = SENTINEL
        u.save()

    def test_dummy_action(self):
        id = next(unique_id)
        SimpleConcurrentModel.objects.get_or_create(pk=id)
        res = self.app.get('/admin/', user='sax')

        res = res.click('^SimpleConcurrentModels')
        assert 'SimpleConcurrentModel #%s' % id in res  # sanity check

        self._create_conflict(id)

        form = res.forms['changelist-form']
        form['action'].value = 'dummy_action'
        sel = form.get('_selected_action', index=0)
        sel.checked = True
        res = form.submit().follow()

        self.assertIn('SimpleConcurrentModel #%s' % id, res)
        self.assertIn('**concurrent_update**', res)
        self.assertNotIn('**action_update**', res)

    @skipIfDjangoVersion([1,7])
    def test_delete_allowed_if_no_updates(self):
        id = next(unique_id)
        SimpleConcurrentModel.objects.get_or_create(pk=id)
        res = self.app.get('/admin/', user='sax')
        res = res.click('^SimpleConcurrentModels')
        assert 'SimpleConcurrentModel #%s' % id in res  # sanity check

        form = res.forms['changelist-form']
        form['action'].value = 'delete_selected'
        sel = form.get('_selected_action', index=0)
        sel.checked = True

        res = form.submit()
        assert 'Are you sure?' in res
        assert 'SimpleConcurrentModel #%s' % id in res
        res = res.form.submit()
        assert 'SimpleConcurrentModel #%s' % id not in res

    def test_delete_not_allowed_if_updates(self):
        id = next(unique_id)

        SimpleConcurrentModel.objects.get_or_create(pk=id)
        res = self.app.get('/admin/', user='sax')
        res = res.click('^SimpleConcurrentModels')
        assert 'SimpleConcurrentModel #%s' % id in res  # sanity check

        self._create_conflict(id)

        form = res.forms['changelist-form']
        form['action'].value = 'delete_selected'
        sel = form.get('_selected_action', index=0)
        sel.checked = True
        res = form.submit().follow()
        self.assertIn('One or more record were updated', res)

########NEW FILE########
__FILENAME__ = test_admin_edit
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from concurrency.forms import VersionFieldSigner
from tests.base import AdminTestCase, SENTINEL
from tests.models import SimpleConcurrentModel

# @pytest.mark.django_db
# @pytest.mark.admin
# def test_creation(superuser, app):
#     url = reverse('admin:concurrency_simpleconcurrentmodel_add')
#     res = app.get(url, user=superuser.username)
#
#     form = res.form
#     form['username'] = 'CHAR'
#     res = form.submit().follow()
#     assert SimpleConcurrentModel.objects.filter(username='CHAR').exists()
#     assert SimpleConcurrentModel.objects.get(username='CHAR').version > 0
#
#     # self.assertTrue(SimpleConcurrentModel.objects.filter(username='CHAR').exists())
#     # self.assertGreater(SimpleConcurrentModel.objects.get(username='CHAR').version, 0)
#
#
# @pytest.mark.django_db
# @pytest.mark.functional
# def test_standard_update(superuser, concurrentmodel, app):
#     url = reverse('admin:concurrency_simpleconcurrentmodel_change',
#                   args=[concurrentmodel.pk])
#     res = app.get(url, user=superuser.username)
#
#     target = res.context['original']
#
#     old_version = target.version
#     form = res.form
#     form['username'] = 'UPDATED'
#     res = form.submit().follow()
#     target = SimpleConcurrentModel.objects.get(pk=target.pk)
#     new_version = target.version
#
#     assert new_version > old_version

# @pytest.mark.django_db
# @pytest.mark.functional
# def test_conflict(superuser, concurrentmodel, app):
#     url = reverse('admin:concurrency_simpleconcurrentmodel_change',
#                   args=[concurrentmodel.pk])
#     res = app.get(url, user=superuser.username)
#     form = res.form
#     concurrentmodel.save()  # create conflict here
#
#     res = form.submit()
#
#     assert 'original' in res.context
#     assert res.context['adminform'].form.errors
#     assert _('Record Modified') in str(res.context['adminform'].form.errors)
from tests.util import nextname


class TestConcurrentModelAdmin(AdminTestCase):

    def test_standard_update(self):
        target, __ = SimpleConcurrentModel.objects.get_or_create(username='aaa')
        url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[target.pk])
        res = self.app.get(url, user='sax')
        target = res.context['original']
        old_version = target.version
        form = res.form
        form['username'] = 'UPDATED'
        res = form.submit().follow()
        target = SimpleConcurrentModel.objects.get(pk=target.pk)
        new_version = target.version
        self.assertGreater(new_version, old_version)

    def test_creation(self):
        url = reverse('admin:concurrency_simpleconcurrentmodel_add')
        res = self.app.get(url, user='sax')
        form = res.form
        form['username'] = 'CHAR'
        res = form.submit().follow()
        self.assertTrue(SimpleConcurrentModel.objects.filter(username='CHAR').exists())
        self.assertGreater(SimpleConcurrentModel.objects.get(username='CHAR').version, 0)

    def test_conflict(self):
        target, __ = SimpleConcurrentModel.objects.get_or_create(username='aaa')
        url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[target.pk])
        res = self.app.get(url, user='sax')

        form = res.form
        target.save()  # create conflict here

        res = form.submit()

        self.assertIn('original', res.context)
        self.assertTrue(res.context['adminform'].form.errors,
                        res.context['adminform'].form.errors)
        self.assertIn(_('Record Modified'),
                      str(res.context['adminform'].form.errors),
                      res.context['adminform'].form.errors)


class TestAdminEdit(AdminTestCase):

    def _create_conflict(self, pk):
        u = SimpleConcurrentModel.objects.get(pk=pk)
        u.username = SENTINEL
        u.save()

    def test_creation(self):
        url = reverse('admin:concurrency_simpleconcurrentmodel_add')
        res = self.app.get(url, user='sax')
        form = res.form
        form['username'] = 'CHAR'
        res = form.submit().follow()
        self.assertTrue(SimpleConcurrentModel.objects.filter(username='CHAR').exists())
        self.assertGreater(SimpleConcurrentModel.objects.get(username='CHAR').version, 0)

    def test_creation_with_customform(self):
        url = reverse('admin:concurrency_simpleconcurrentmodel_add')
        res = self.app.get(url, user='sax')
        form = res.form
        username = next(nextname)
        form['username'] = username
        res = form.submit().follow()
        self.assertTrue(SimpleConcurrentModel.objects.filter(username=username).exists())
        self.assertGreater(SimpleConcurrentModel.objects.get(username=username).version, 0)

        #test no other errors are raised
        res = form.submit()
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "SimpleConcurrentModel with this Username already exists.")

    def test_standard_update(self):
        target, __ = SimpleConcurrentModel.objects.get_or_create(username='aaa')
        url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[target.pk])
        res = self.app.get(url, user='sax')
        target = res.context['original']
        old_version = target.version
        form = res.form
        form['username'] = 'UPDATED'
        res = form.submit().follow()
        target = SimpleConcurrentModel.objects.get(pk=target.pk)
        new_version = target.version
        self.assertGreater(new_version, old_version)

    def test_conflict(self):
        target, __ = SimpleConcurrentModel.objects.get_or_create(username='aaa')
        assert target.version
        url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[target.pk])
        res = self.app.get(url, user='sax')
        form = res.form

        target.save()  # create conflict here
        res = form.submit()
        self.assertIn('original', res.context)
        self.assertTrue(res.context['adminform'].form.errors,
                        res.context['adminform'].form.errors)
        self.assertIn(_('Record Modified'),
                      str(res.context['adminform'].form.errors),
                      res.context['adminform'].form.errors)

    def test_sanity_signer(self):
        target, __ = SimpleConcurrentModel.objects.get_or_create(username='aaa')
        url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[target.pk])
        res = self.app.get(url, user='sax')
        form = res.form
        version1 = int(str(form['version'].value).split(":")[0])
        form['version'] = VersionFieldSigner().sign(version1)
        form['date_field'] = 'esss2010-09-01'
        response = form.submit()
        self.assertIn('original', response.context)
        self.assertTrue(response.context['adminform'].form.errors,
                        response.context['adminform'].form.errors)
        form = response.context['adminform'].form
        version2 = int(str(form['version'].value()).split(":")[0])
        self.assertEqual(version1, version2)

########NEW FILE########
__FILENAME__ = test_admin_list_editable
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.contrib.admin.sites import site
from django.db import transaction
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
import pytest
from concurrency.config import CONCURRENCY_LIST_EDITABLE_POLICY_SILENT, CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL
from concurrency.exceptions import RecordModifiedError

from tests.base import AdminTestCase, SENTINEL
from tests.models import ListEditableConcurrentModel
from tests.util import attributes, unique_id


class TestListEditable(AdminTestCase):
    TARGET = ListEditableConcurrentModel

    def _create_conflict(self, pk):
        u = self.TARGET.objects.get(pk=pk)
        u.username = SENTINEL
        u.save()

    def test_normal_add(self):
        res = self.app.get('/admin/', user='sax')

        res = res.click(self.TARGET._meta.verbose_name_plural)

        res = res.click('Add')
        form = res.form
        form['username'] = 'CHAR'
        res = form.submit().follow()

    def test_normal_update(self):
        self.TARGET.objects.get_or_create(pk=next(unique_id))
        res = self.app.get('/admin/', user='sax')
        res = res.click(self.TARGET._meta.verbose_name_plural)
        form = res.forms['changelist-form']
        form['form-0-username'] = 'CHAR'
        res = form.submit('_save').follow()
        self.assertTrue(self.TARGET.objects.filter(username='CHAR').exists())

    def test_concurrency_policy_abort(self):
        id = next(unique_id)
        self.TARGET.objects.get_or_create(pk=id)
        model_admin = site._registry[self.TARGET]
        with attributes((model_admin.__class__, 'list_editable_policy', CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL)):

            res = self.app.get('/admin/', user='sax')
            res = res.click(self.TARGET._meta.verbose_name_plural)
            self._create_conflict(id)

            form = res.forms['changelist-form']
            form['form-0-username'] = 'CHAR'

            with pytest.raises(RecordModifiedError):
                res = form.submit('_save')

            self.assertTrue(self.TARGET.objects.filter(username=SENTINEL).exists())
            self.assertFalse(self.TARGET.objects.filter(username='CHAR').exists())

    def test_concurrency_policy_silent(self):
        id = next(unique_id)
        self.TARGET.objects.get_or_create(pk=id)
        model_admin = site._registry[self.TARGET]
        with attributes((model_admin.__class__, 'list_editable_policy', CONCURRENCY_LIST_EDITABLE_POLICY_SILENT)):
            res = self.app.get('/admin/', user='sax')
            res = res.click(self.TARGET._meta.verbose_name_plural)
            self._create_conflict(id)

            form = res.forms['changelist-form']
            form['form-0-username'] = 'CHAR'
            res = form.submit('_save').follow()
            self.assertTrue(self.TARGET.objects.filter(username=SENTINEL).exists())
            self.assertFalse(self.TARGET.objects.filter(username='CHAR').exists())

    def test_message_user(self):
        id1 = next(unique_id)
        id2 = next(unique_id)
        self.TARGET.objects.get_or_create(pk=id1)
        self.TARGET.objects.get_or_create(pk=id2)
        res = self.app.get('/admin/', user='sax')
        res = res.click(self.TARGET._meta.verbose_name_plural)

        self._create_conflict(id1)

        form = res.forms['changelist-form']
        form['form-0-username'] = 'CHAR1'
        form['form-1-username'] = 'CHAR2'
        res = form.submit('_save').follow()

        messages = map(str, list(res.context['messages']))

        self.assertIn('Record with pk `%s` has been modified and was not updated' % id1,
                      messages)
        self.assertIn('1 %s was changed successfully.' % force_text(self.TARGET._meta.verbose_name),
                      messages)

    def test_message_user_no_changes(self):
        id = next(unique_id)
        self.TARGET.objects.get_or_create(pk=id)

        res = self.app.get('/admin/', user='sax')
        res = res.click(self.TARGET._meta.verbose_name_plural)

        self._create_conflict(id)

        form = res.forms['changelist-form']
        form['form-0-username'] = 'CHAR1'
        res = form.submit('_save').follow()

        messages = list(map(str, list(res.context['messages'])))

        self.assertIn('No %s were changed due conflict errors' % force_text(self.TARGET._meta.verbose_name),
                      messages)
        self.assertEqual(len(messages), 1)

    def test_log_change(self):
        id = next(unique_id)
        self.TARGET.objects.get_or_create(pk=id)

        res = self.app.get('/admin/', user='sax')
        res = res.click(self.TARGET._meta.verbose_name_plural)
        log_filter = dict(user__username='sax',
                          content_type=ContentType.objects.get_for_model(self.TARGET))

        logs = list(LogEntry.objects.filter(**log_filter).values_list('pk', flat=True))

        self._create_conflict(id)

        form = res.forms['changelist-form']
        form['form-0-username'] = 'CHAR1'
        res = form.submit('_save').follow()
        new_logs = LogEntry.objects.filter(**log_filter).exclude(id__in=logs).exists()
        self.assertFalse(new_logs, "LogEntry created even if conflict error")
        transaction.rollback()


# class TestListEditableWithNoActions(TestListEditable):
#     TARGET = NoActionsConcurrentModel

########NEW FILE########
__FILENAME__ = test_api
from django.core.exceptions import ImproperlyConfigured
import pytest
from django.contrib.auth.models import Permission
from concurrency.api import (get_revision_of_object, is_changed, get_version,
                             apply_concurrency_check, disable_concurrency)
from concurrency.fields import IntegerVersionField
from concurrency.utils import refetch
from tests.models import SimpleConcurrentModel
from tests.util import nextname


@pytest.mark.django_db(transaction=False)
@pytest.mark.skipIf('os.environ["DBENGINE"]=="pg"')
def test_get_revision_of_object(model_class=SimpleConcurrentModel):
    instance = model_class(username=next(nextname))
    instance.save()
    assert get_revision_of_object(instance) == instance.version


@pytest.mark.django_db
def test_is_changed(model_class=SimpleConcurrentModel):
    instance = model_class(username=next(nextname))
    instance.save()
    copy = refetch(instance)
    copy.save()
    assert is_changed(instance)


@pytest.mark.django_db
def test_get_version(model_class=SimpleConcurrentModel):
    instance = model_class(username=next(nextname))
    instance.save()
    copy = refetch(instance)
    copy.save()
    instance = get_version(instance, copy.version)
    assert instance.get_concurrency_version() == copy.get_concurrency_version()


@pytest.mark.django_db
def test_apply_concurrency_check(model_class=SimpleConcurrentModel):
    try:
        apply_concurrency_check(Permission, 'version', IntegerVersionField)
    except ImproperlyConfigured:
        pass


@pytest.mark.django_db(transaction=False)
def test_disable_concurrency(model_class=SimpleConcurrentModel):
    instance = model_class(username=next(nextname))
    instance.save()
    copy = refetch(instance)
    copy.save()
    with disable_concurrency(instance):
        instance.save()

########NEW FILE########
__FILENAME__ = test_base
import pytest
from concurrency.core import _set_version
from concurrency.exceptions import RecordModifiedError
from concurrency.utils import refetch
from tests.util import with_all_models, unique_id, nextname, with_std_models


@pytest.mark.django_db
@with_all_models
def test_standard_save(model_class):
    instance = model_class(username=next(nextname))
    instance.save()
    assert instance.get_concurrency_version() > 0


@pytest.mark.django_db(transaction=False)
@with_std_models
def test_conflict(model_class):
    id = next(unique_id)
    instance = model_class.objects.get_or_create(pk=id)[0]
    instance.save()

    copy = refetch(instance)
    copy.save()

    with pytest.raises(RecordModifiedError):
        instance.save()
    assert copy.get_concurrency_version() > instance.get_concurrency_version()


@pytest.mark.django_db(transaction=False)
@with_std_models
def test_do_not_check_if_no_version(model_class):
    id = next(unique_id)
    instance = model_class.objects.get_or_create(pk=id)[0]
    instance.save()

    copy = refetch(instance)
    copy.save()

    with pytest.raises(RecordModifiedError):
        _set_version(instance, 1)
        instance.save()

    _set_version(instance, 0)
    instance.save()
    assert instance.get_concurrency_version() > 0
    assert instance.get_concurrency_version() != copy.get_concurrency_version()

########NEW FILE########
__FILENAME__ = test_concurrencymetainfo
from concurrency.exceptions import RecordModifiedError
from tests.models import ConcurrencyDisabledModel, SimpleConcurrentModel
from django.test import TransactionTestCase


class TestCustomConcurrencyMeta(TransactionTestCase):
    concurrency_model = ConcurrencyDisabledModel
    concurrency_kwargs = {'username': 'test'}

    def setUp(self):
        super(TestCustomConcurrencyMeta, self).setUp()
        self.TARGET = self._get_concurrency_target()

    def _get_concurrency_target(self, **kwargs):
        # WARNING this method must be idempotent. ie must returns
        # always a fresh copy of the record
        args = dict(self.concurrency_kwargs)
        args.update(kwargs)
        return self.concurrency_model.objects.get_or_create(**args)[0]

    def test_enabled(self):
        assert not self.TARGET._concurrencymeta.enabled

    def test_meta_inheritance(self):
        # TestModelWithCustomOptions extends ConcurrentModel
        # but we disabled concurrency only in TestModelWithCustomOptions
        import concurrency.api as api
        concurrency_enabled1 = SimpleConcurrentModel.objects.get_or_create(**{'username': 'test'})[0]
        concurrency_enabled2 = SimpleConcurrentModel.objects.get_or_create(**{'username': 'test'})[0]
        v1 = api.get_revision_of_object(concurrency_enabled1)
        v2 = api.get_revision_of_object(concurrency_enabled2)
        assert v1 == v2, "got same row with different version (%s/%s)" % (v1, v2)
        concurrency_enabled1.save()
        assert concurrency_enabled1.pk is not None  # sanity check
        self.assertRaises(RecordModifiedError, concurrency_enabled2.save)

        concurrency_disabled1 = ConcurrencyDisabledModel.objects.get_or_create(**{'username': 'test'})[0]
        concurrency_disabled2 = ConcurrencyDisabledModel.objects.get_or_create(**{'username': 'test'})[0]
        v1 = api.get_revision_of_object(concurrency_disabled1)
        v2 = api.get_revision_of_object(concurrency_disabled2)
        assert v1 == v2, "got same row with different version (%s/%s)" % (v1, v2)
        concurrency_disabled1.save()
        assert concurrency_disabled1.pk is not None  # sanity check
        v1 = api.get_revision_of_object(concurrency_disabled1)
        v2 = api.get_revision_of_object(concurrency_disabled2)
        assert v1 != v2

########NEW FILE########
__FILENAME__ = test_forms
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.forms.models import modelform_factory
from django.forms.widgets import HiddenInput, TextInput
from django.utils.encoding import smart_str
from django.test import TestCase
import pytest
from concurrency.exceptions import VersionError
from concurrency.forms import ConcurrentForm, VersionField, VersionFieldSigner, VersionWidget
from django.test.testcases import SimpleTestCase
from django.utils.translation import ugettext as _
from tests.models import SimpleConcurrentModel, TestIssue3Model

__all__ = ['WidgetTest', 'FormFieldTest', 'ConcurrentFormTest']


class DummySigner():
    def sign(self, value):
        return smart_str(value)

    def unsign(self, signed_value):
        return smart_str(signed_value)


class WidgetTest(TestCase):
    def test(self):
        w = VersionWidget()
        self.assertHTMLEqual(w.render('ver', None),
                             '<input name="ver" type="hidden"/><div></div>')
        self.assertHTMLEqual(w.render('ver', 100),
                             '<input name="ver" type="hidden" value="100"/><div>100</div>')


class FormFieldTest(SimpleTestCase):
    def test_with_wrong_signer(self):
        with self.settings(CONCURRENCY_FIELD_SIGNER='invalid.Signer'):
            with pytest.raises(ImproperlyConfigured):
                VersionField()

    def test_with_dummy_signer(self):
        f = VersionField(signer=DummySigner())
        self.assertEqual(1, f.clean(1))
        self.assertEqual(1, f.clean('1'))
        self.assertEqual(0, f.clean(None))
        self.assertEqual(0, f.clean(''))
        self.assertRaises(VersionError, f.clean, 'aa:bb')
        self.assertRaises(VersionError, f.clean, 1.5)

    def test(self):
        f = VersionField()
        self.assertEqual(1, f.clean(VersionFieldSigner().sign(1)))
        self.assertEqual(1, f.clean(VersionFieldSigner().sign('1')))
        self.assertEqual(0, f.clean(None))
        self.assertEqual(0, f.clean(''))
        self.assertRaises(VersionError, f.clean, '100')
        self.assertRaises(VersionError, f.clean, VersionFieldSigner().sign(1.5))


class ConcurrentFormTest(TestCase):
    def test_version(self):
        Form = modelform_factory(SimpleConcurrentModel, ConcurrentForm, exclude=('char_field',))
        form = Form()
        self.assertIsInstance(form.fields['version'].widget, HiddenInput)

    def test_clean(self):
        pass

    def test_dummy_signer(self):
        obj, __ = TestIssue3Model.objects.get_or_create(username='aaa')
        Form = modelform_factory(TestIssue3Model,
                                 fields=('id', 'revision'),
                                 form=type('xxx', (ConcurrentForm,), {'revision': VersionField(signer=DummySigner())}))
        data = {'id': 1,
                'revision': obj.revision}
        form = Form(data, instance=obj)
        self.assertTrue(form.is_valid(), form.non_field_errors())

    def test_signer(self):
        Form = modelform_factory(TestIssue3Model, form=ConcurrentForm,
                                 exclude=('char_field',))
        form = Form({'username': 'aaa'})
        self.assertTrue(form.is_valid(), form.non_field_errors())

    def test_initial_value(self):
        Form = modelform_factory(SimpleConcurrentModel, type('xxx', (ConcurrentForm,), {}), exclude=('char_field',))
        form = Form({'username': 'aaa'})
        self.assertHTMLEqual(str(form['version']), '<input type="hidden" value="" name="version" id="id_version" />')
        self.assertTrue(form.is_valid(), form.non_field_errors())

    def test_initial_value_with_custom_signer(self):
        Form = modelform_factory(TestIssue3Model, exclude=('char_field',),
                                 form=type('xxx', (ConcurrentForm,),
                                           {'version': VersionField(signer=DummySigner())}))
        form = Form({'username': 'aaa'})
        self.assertHTMLEqual(str(form['version']), '<input type="hidden" value="" name="version" id="id_version" />')
        self.assertTrue(form.is_valid(), form.non_field_errors())

    def test_tamperig(self):
        obj, __ = TestIssue3Model.objects.get_or_create(username='aaa')
        Form = modelform_factory(TestIssue3Model, ConcurrentForm, exclude=('char_field',))
        data = {'username': 'aaa',
                'last_name': None,
                'date_field': None,
                'char_field': None,
                'version': 'abc',
                'id': 1,
                'revision': obj.revision}
        form = Form(data, instance=obj)
        self.assertRaises(SuspiciousOperation, form.is_valid)

    def test_custom_name(self):
        Form = modelform_factory(TestIssue3Model, ConcurrentForm, exclude=('char_field',))
        form = Form()
        self.assertIsInstance(form.fields['version'].widget, TextInput)
        self.assertIsInstance(form.fields['revision'].widget, HiddenInput)

    def test_save(self):
        obj, __ = TestIssue3Model.objects.get_or_create(username='aaa')

        obj_copy = TestIssue3Model.objects.get(pk=obj.pk)
        Form = modelform_factory(TestIssue3Model, ConcurrentForm,
                                 fields=('username', 'last_name', 'date_field',
                                         'char_field', 'version', 'id', 'revision'))
        data = {'username': 'aaa',
                'last_name': None,
                'date_field': None,
                'char_field': None,
                'version': 'abc',
                'id': 1,
                'revision': VersionFieldSigner().sign(obj.revision)}
        form = Form(data, instance=obj)
        obj_copy.save()  # save

        self.assertFalse(form.is_valid())
        self.assertIn(_('Record Modified'), form.non_field_errors())

    def test_is_valid(self):
        obj, __ = TestIssue3Model.objects.get_or_create(username='aaa')
        Form = modelform_factory(TestIssue3Model, ConcurrentForm,
                                 fields=('username', 'last_name', 'date_field',
                                         'char_field', 'version', 'id', 'revision'))
        data = {'username': 'aaa',
                'last_name': None,
                'date_field': None,
                'char_field': None,
                'version': 'abc',
                'id': 1,
                'revision': VersionFieldSigner().sign(obj.revision)}
        form = Form(data, instance=obj)
        obj.save()  # save again simulate concurrent editing
        self.assertRaises(ValueError, form.save)

########NEW FILE########
__FILENAME__ = test_functional

########NEW FILE########
__FILENAME__ = test_issues
# -*- coding: utf-8 -*-
import re
from django.contrib.auth.models import User, Group
from django.test.testcases import SimpleTestCase
from django.utils.encoding import force_text
from concurrency.admin import ConcurrentModelAdmin
from concurrency.config import CONCURRENCY_LIST_EDITABLE_POLICY_SILENT
from concurrency.forms import ConcurrentForm
from concurrency.templatetags.concurrency import identity
from django.contrib.admin.sites import site
from django.http import QueryDict
from django.test.client import RequestFactory
from concurrency.utils import refetch
from tests.admin import admin_register, ActionsModelAdmin

from tests.base import AdminTestCase
from tests.models import ListEditableConcurrentModel
from tests.util import unique_id, attributes


def get_fake_request(params):
    u, __ = User.objects.get_or_create(username='sax')
    setattr(u, 'is_authenticated()', True)
    setattr(u, 'selected_office', False)

    request = RequestFactory().request()
    request.user = u

    querydict = QueryDict(params)
    request.POST = querydict

    return request


class TestIssue16(AdminTestCase):
    def test_concurrency(self):
        id = 1
        admin_register(ListEditableConcurrentModel, ActionsModelAdmin)
        model_admin = site._registry[ListEditableConcurrentModel]
        with attributes((ConcurrentModelAdmin, 'list_editable_policy', CONCURRENCY_LIST_EDITABLE_POLICY_SILENT),
                        (ConcurrentModelAdmin, 'form', ConcurrentForm), ):
            obj, __ = ListEditableConcurrentModel.objects.get_or_create(pk=id)
            request1 = get_fake_request('pk=%s&_concurrency_version_1=2' % id)

            model_admin.save_model(request1, obj, None, True)

            self.assertIn(obj.pk, model_admin._get_conflicts(request1))

            obj = refetch(obj)
            request2 = get_fake_request('pk=%s&_concurrency_version_1=%s' % (id, obj.version))
            model_admin.save_model(request2, obj, None, True)
            self.assertNotIn(obj.pk, model_admin._get_conflicts(request2))


class TestIssue18(SimpleTestCase):
    def test_identity_tag(self):
        id = next(unique_id)

        obj = ListEditableConcurrentModel(pk=id)
        self.assertTrue(re.match(r"^%s,\d+$" % id, identity(obj)))

        g = Group(name='GroupTest', pk=3)
        self.assertEqual(identity(g), force_text(g.pk))

########NEW FILE########
__FILENAME__ = test_manager
import pytest
from concurrency.exceptions import RecordModifiedError
from concurrency.utils import refetch
from tests.models import (SimpleConcurrentModel, AutoIncConcurrentModel, CustomSaveModel,
                          InheritedModel, ConcreteModel, ProxyModel)
from tests.util import with_all_models, unique_id, nextname, with_models, with_std_models


@pytest.mark.django_db
@with_std_models
def test_get_or_create(model_class):
    instance, __ = model_class.objects.get_or_create(pk=next(unique_id))
    assert instance.get_concurrency_version()
    instance.save()


@pytest.mark.django_db
@with_std_models
def test_get_or_create_with_pk(model_class):
    instance, __ = model_class.objects.get_or_create(pk=next(unique_id))
    assert instance.get_concurrency_version()
    instance.save()
    copy = refetch(instance)
    copy.save()
    with pytest.raises(RecordModifiedError):
        instance.save()
    assert copy.get_concurrency_version() > instance.get_concurrency_version()


@pytest.mark.django_db(transaction=False)
def test_create(model_class=SimpleConcurrentModel):
    instance = model_class.objects.create(pk=next(unique_id))
    assert instance.get_concurrency_version()


@pytest.mark.django_db
@with_models(SimpleConcurrentModel, AutoIncConcurrentModel,
             InheritedModel, CustomSaveModel,
             ConcreteModel, ProxyModel)
def test_update(model_class):
    # Manager.update() does not change version number
    instance = model_class.objects.create(pk=next(unique_id), username=next(nextname).lower())
    field_value = instance.username
    model_class.objects.filter(pk=instance.pk).update(username=instance.username.upper())

    instance2 = refetch(instance)
    assert instance2.username == field_value.upper()
    assert instance2.get_concurrency_version() == instance.get_concurrency_version()

########NEW FILE########
__FILENAME__ = test_middleware
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.admin.sites import site
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
import mock
from django.http import HttpRequest
from concurrency.admin import ConcurrentModelAdmin
from concurrency.config import CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL
from concurrency.exceptions import RecordModifiedError
from concurrency.middleware import ConcurrencyMiddleware
from tests.base import AdminTestCase
from tests.models import SimpleConcurrentModel
from tests.util import attributes, DELETE_ATTRIBUTE, unique_id


def _get_request(path):
    request = HttpRequest()
    request.META = {
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': 80,
    }
    request.path = request.path_info = "/middleware/%s" % path
    return request


def test_middleware():
    handler = mock.Mock(status_code=409)
    type(handler.return_value).status_code = mock.PropertyMock(return_value=409)

    with override_settings(CONCURRENCY_HANDLER409=handler):
        request = _get_request('needsquoting#')
        r = ConcurrencyMiddleware().process_exception(request, RecordModifiedError(target=SimpleConcurrentModel()))
    assert r.status_code == 409


class ConcurrencyMiddlewareTest(AdminTestCase):
    def _get_request(self, path):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = "/middleware/%s" % path
        return request

    @mock.patch('django.core.signals.got_request_exception.send', mock.Mock())
    def test_process_exception(self):
        """
        Tests that RecordModifiedError is handled correctly.
        """
        id = next(unique_id)
        m, __ = SimpleConcurrentModel.objects.get_or_create(pk=id)
        copy = SimpleConcurrentModel.objects.get(pk=m.pk)
        copy.save()
        request = self._get_request('/')
        r = ConcurrencyMiddleware().process_exception(request, RecordModifiedError(target=m))
        self.assertEqual(r.status_code, 409)

    def test_in_admin(self):
        id = next(unique_id)

        middlewares = list(settings.MIDDLEWARE_CLASSES) + ['concurrency.middleware.ConcurrencyMiddleware']
        model_admin = site._registry[SimpleConcurrentModel]

        with attributes((model_admin.__class__, 'list_editable_policy', CONCURRENCY_LIST_EDITABLE_POLICY_ABORT_ALL),
                        (ConcurrentModelAdmin, 'form', DELETE_ATTRIBUTE)):

            with self.settings(MIDDLEWARE_CLASSES=middlewares):

                saved, __ = SimpleConcurrentModel.objects.get_or_create(pk=id)

                url = reverse('admin:concurrency_simpleconcurrentmodel_change', args=[saved.pk])
                res = self.app.get(url, user='sax')
                form = res.form

                saved.save()  # create conflict here

                res = form.submit(expect_errors=True)

                self.assertEqual(res.status_code, 409)

                target = res.context['target']
                self.assertIn('target', res.context)
                self.assertIn('saved', res.context)

                self.assertEqual(res.context['target'].version, target.version)
                self.assertEqual(res.context['saved'].version, saved.version)
                self.assertEqual(res.context['request_path'], url)

#
# class TestFullStack(DjangoAdminTestCase):
#     MIDDLEWARE_CLASSES = ('django.middleware.common.CommonMiddleware',
#                           'django.contrib.sessions.middleware.SessionMiddleware',
#                           'django.contrib.auth.middleware.AuthenticationMiddleware',
#                           'django.contrib.messages.middleware.MessageMiddleware',
#                           'concurrency.middleware.ConcurrencyMiddleware',)
#
#     @mock.patch('django.core.signals.got_request_exception.send', mock.Mock())
#     def test_stack(self):
#         admin_register(TestModel0, ModelAdmin)
#
#         with self.settings(MIDDLEWARE_CLASSES=self.MIDDLEWARE_CLASSES):
#             m, __ = TestModel0.objects.get_or_create(username="New", last_name="1")
#             copy = TestModel0.objects.get(pk=m.pk)
#             assert copy.version == m.version
#             print 111111111111, m.version
#             url = reverse('admin:concurrency_testmodel0_change', args=[m.pk])
#             data = {'username': 'new_username',
#                     'last_name': None,
#                     'version': VersionFieldSigner().sign(m.version),
#                     'char_field': None,
#                     '_continue': 1,
#                     'date_field': '2010-09-01'}
#             copy.save()
#             assert copy.version > m.version
#
#             r = self.client.post(url, data, follow=True)
#             self.assertEqual(r.status_code, 409)
#             self.assertIn('target', r.context)
#             self.assertIn('saved', r.context)
#             self.assertEqual(r.context['saved'].version, copy.version)
#             self.assertEqual(r.context['target'].version, m.version)
#             self.assertEqual(r.context['request_path'], url)

########NEW FILE########
__FILENAME__ = test_south
# -*- coding: utf-8 -*-
from django.test import TestCase
from concurrency.fields import IntegerVersionField, AutoIncVersionField

__all__ = ['SouthTestCase']

try:
    from south.modelsinspector import can_introspect

    class SouthTestCase(TestCase):
        def test_south_can_introspect_integerversionfield(self):
            self.assertTrue(can_introspect(IntegerVersionField()))

        def test_south_can_introspect_autoincversionfield(self):
            self.assertTrue(can_introspect(AutoIncVersionField()))

except ImportError:
    class SouthTestCase(object):
        pass

########NEW FILE########
__FILENAME__ = test_threads
# import pytest
# from django import db
# from django.db import transaction
# from concurrency.exceptions import RecordModifiedError
# from concurrency.utils import refetch
# from tests.models import TriggerConcurrentModel
# from tests.util import test_concurrently
#

#
# @pytest.mark.django_db(transaction=True)
# @pytest.mark.skipIf(db.connection.vendor == 'sqlite', "in-memory sqlite db can't be used between threads")
# def test_threads_1():
#     obj = TriggerConcurrentModel.objects.create()
#     transaction.commit()
#
#     @test_concurrently(25)
#     def run():
#         for i in range(5):
#             while True:
#                 x = refetch(obj)
#                 transaction.commit()
#                 x.count += 1
#                 try:
#                     x.save()
#                     transaction.commit()
#                 except RecordModifiedError:
#                     # retry
#                     pass
#                 else:
#                     break
#
#     run()
#     assert refetch(obj).count == 5 * 25
#

#
# from django import db
# from django.db import transaction
# class ThreadTests(TransactionTestCase):
#     @pytest.mark.skipIf(db.connection.vendor == 'sqlite',"in-memory sqlite db can't be used between threads")
#     def test_threads_1(self):
#         """
# Run 25 threads, each incrementing a shared counter 5 times.
# """
#
#         obj = TriggerConcurrentModel.objects.create()
#         transaction.commit()
#
#         @test_concurrently(25)
#         def run():
#             for i in range(5):
#                 while True:
#                     x = refetch(obj)
#                     transaction.commit()
#                     x.count += 1
#                     try:
#                         x.save()
#                         transaction.commit()
#                     except RecordModifiedError:
#                         # retry
#                         pass
#                     else:
#                         break
#         run()
#         assert refetch(obj).count== 5 * 25
#
#     @pytest.mark.skipIf(db.connection.vendor == 'sqlite',"in-memory sqlite db can't be used between threads")
#     def test_threads_2(self):
#         """
# Run 25 threads, each incrementing a shared counter 5 times.
# """
#
#         obj = TriggerConcurrentModel.objects.create()
#         transaction.commit()
#
#         @test_concurrently(25)
#         def run():
#             for i in range(5):
#                 x = refetch(obj)
#                 transaction.commit()
#                 x.count += 1
#                 try:
#                     x.save()
#                     transaction.commit()
#                 except RecordModifiedError:
#                     transaction.rollback()
#                     break
#         run()
#         obj = refetch(obj)
#         assert obj.count == obj.version-1

########NEW FILE########
__FILENAME__ = test_triggerversionfield
# -*- coding: utf-8 -*-
from django.core import signals
from django.db import connections, IntegrityError
import mock
import pytest
from concurrency.exceptions import RecordModifiedError
from concurrency.utils import refetch
from tests.models import TriggerConcurrentModel
from django.core.signals import request_started

# Register an event to reset saved queries when a Django request is started.
from tests.util import nextname


def reset_queries(**kwargs):
    for conn in connections.all():
        conn.queries = []


signals.request_started.connect(reset_queries)


class CaptureQueriesContext(object):
    """
    Context manager that captures queries executed by the specified connection.
    """

    def __init__(self, connection):
        self.connection = connection

    def __iter__(self):
        return iter(self.captured_queries)

    def __getitem__(self, index):
        return self.captured_queries[index]

    def __len__(self):
        return len(self.captured_queries)

    @property
    def captured_queries(self):
        return self.connection.queries[self.initial_queries:self.final_queries]

    def __enter__(self):
        self.use_debug_cursor = self.connection.use_debug_cursor
        self.connection.use_debug_cursor = True
        self.initial_queries = len(self.connection.queries)
        self.final_queries = None
        request_started.disconnect(reset_queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.use_debug_cursor = self.use_debug_cursor
        request_started.connect(reset_queries)
        if exc_type is not None:
            return
        self.final_queries = len(self.connection.queries)


@pytest.mark.django_db
def test_trigger():
    instance = TriggerConcurrentModel()
    assert instance.pk is None
    assert instance.version == 0

    instance.username = next(nextname)
    instance.save()  # insert
    instance = refetch(instance)
    assert instance.version == 1

    instance.username = next(nextname)
    instance.save()  # update
    assert instance.version == 2

    instance.username = next(nextname)
    instance.save()  # update
    assert instance.version == 3

    copy = refetch(instance)
    copy.save()

    with pytest.raises(RecordModifiedError):
        instance.save()


@pytest.mark.django_db
def test_trigger_do_not_increase_version_if_error():
    instance = TriggerConcurrentModel()
    assert instance.pk is None
    assert instance.version == 0
    with mock.patch('tests.models.TriggerConcurrentModel.save', side_effect=IntegrityError):
        with pytest.raises(IntegrityError):
            instance.save()

    assert instance.version == 0

########NEW FILE########
__FILENAME__ = test_views

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.edit import UpdateView
from tests.models import SimpleConcurrentModel


try:
    from django.apps import AppConfig
    import django
    django.setup()
except ImportError:
    pass

admin.autodiscover()

class SimpleConcurrentMpdel(object):
    pass


urlpatterns = patterns('',
                       url('cm/(?P<pk>\d+)/',
                           UpdateView.as_view(model=SimpleConcurrentModel),
                           name='concurrent-edit'),
                       (r'^admin/', include(include(admin.site.urls))),
                       (r'', include(include(admin.site.urls))))

########NEW FILE########
__FILENAME__ = util
from contextlib import contextmanager
from functools import partial, update_wrapper
import itertools
import pytest
from concurrency.config import conf
from tests.models import *  # noqa
from itertools import count
from tests.models import TriggerConcurrentModel


def sequence(prefix):
    infinite = itertools.count()
    while 1:
        yield "{0}-{1}".format(prefix, next(infinite))

nextname = sequence('username')
unique_id = count(1)


def override_conf(**kwargs):
    for key, new_value in kwargs.items():
        setattr(conf, key, new_value)


def clone_instance(model_instance):
    """
        returns a copy of the passed instance.

        .. warning: All fields are copied, even primary key

    :param instance: :py:class:`django.db.models.Model` instance
    :return: :py:class:`django.db.models.Model` instance
    """

    fieldnames = [fld.name for fld in model_instance._meta.fields]

    new_kwargs = dict([(name, getattr(model_instance, name)) for name in fieldnames])
    return model_instance.__class__(**new_kwargs)


def with_models(*models, **kwargs):
    ignore = kwargs.pop('ignore', [])
    if ignore:
        models = filter(models, lambda x: not x in ignore)

    ids = [m.__name__ for m in models]

    return pytest.mark.parametrize(('model_class,'),
                                   models,
                                   False,
                                   ids,
                                   None)


MODEL_CLASSES = [SimpleConcurrentModel, AutoIncConcurrentModel,
                 InheritedModel, CustomSaveModel,
                 ConcreteModel, ProxyModel, TriggerConcurrentModel]

with_std_models = partial(with_models, SimpleConcurrentModel, AutoIncConcurrentModel,
                          InheritedModel, CustomSaveModel,
                          ConcreteModel, ProxyModel)()
with_all_models = partial(with_models, *MODEL_CLASSES)()

# with_all_models = partial(models_parametrize, ConcreteModel)()

DELETE_ATTRIBUTE = object()


@contextmanager
def attributes(*values):
    """
        context manager to temporary set/delete object's attributes
    :param values: tulples of (target, name, value)
    Es.


    with attributes((django.contrib.admin.ModelAdmin, 'list_per_page', 200)):
        ...

    with attributes((django.contrib.admin.ModelAdmin, 'list_per_page', DELETE_ATTRIBUTE)):
        ...

    """

    def set(target, name, value):
        if value is DELETE_ATTRIBUTE:
            delattr(target, name)
        else:
            setattr(target, name, value)

    backups = []

    for target, name, value in values:
        if hasattr(target, name):
            backups.append((target, name, getattr(target, name)))
        else:
            backups.append((target, name, getattr(target, name, DELETE_ATTRIBUTE)))
        set(target, name, value)
    yield

    for target, name, value in backups:
        set(target, name, value)


from django import db


def test_concurrently(times=1):
    # from: http://www.caktusgroup.com/blog/2009/05/26/testing-django-views-for-concurrency-issues/
    """
Add this decorator to small pieces of code that you want to test
concurrently to make sure they don't raise exceptions when run at the
same time. E.g., some Django views that do a SELECT and then a subsequent
INSERT might fail when the INSERT assumes that the data has not changed
since the SELECT.
"""

    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []
            import threading

            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception as e:
                    exceptions.append(e)
                    raise
                finally:
                    db.close_connection()

            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception(
                    'test_concurrently intercepted %s exceptions: %s' %
                    (len(exceptions), exceptions))

        return update_wrapper(wrapper, test_func)

    return test_concurrently_decorator

########NEW FILE########
