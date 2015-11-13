__FILENAME__ = settings
# Django settings for migration_helper project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
    }
}

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
SECRET_KEY = '1+lc2sq7!k!(_c*i-q&hyloa01cdq$m5id+bkj*2hg)_i-#e+8'

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

ROOT_URLCONF = 'migration_helper.urls'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'south',
    'django_xworkflows.xworkflow_log',
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
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'migration_helper.views.home', name='home'),
    # url(r'^migration_helper/', include('migration_helper.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

"""Compatibility helpers."""


import sys

is_python2 = (sys.version_info[0] == 2)

try:
    from django.utils import timezone
    now = timezone.now
    del timezone
except ImportError:
    import datetime
    now = datetime.datetime.now
    del datetime

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

try:
    from django.utils.encoding import python_2_unicode_compatible
except ImportError:
    def python_2_unicode_compatible(c):
        if not hasattr(c, '__unicode__'):
            c.__unicode__ = c.__str__
        return c

########NEW FILE########
__FILENAME__ = rebuild_transitionlog_states
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals


"""Rebuild missing from_state/to_state fields on TransitionLog objects."""


from django.contrib.contenttypes import models as ctype_models
from django.core.management import base
from django.db import models


class Command(base.LabelCommand):
    args = "<app.Model> <app.Model> ..."
    help = "Rebuild TransitionLog from_state/to_state fields for selected models."

    def handle_label(self, label, **options):
        self.stdout.write('Rebuilding TransitionLog states for %s\n' % label)

        app_label, model_label = label.rsplit('.', 1)
        model = models.get_model(app_label, model_label)

        if not hasattr(model, '_workflows'):
            raise base.CommandError("Model %s isn't attached to a workflow." % label)

        for field_name, state_field in model._workflows.items():
            self._handle_field(label, model, field_name, state_field.workflow, **options)

    def _handle_field(self, label, model, field_name, workflow, **options):
        if not hasattr(workflow, 'log_model') or not workflow.log_model:
            raise base.CommandError("Field %s of %s does not log to a model." % (field_name, label))

        log_model = workflow._get_log_model_class()
        model_type = ctype_models.ContentType.objects.get_for_model(model)
        verbosity = int(options.get('verbosity', 1))

        if verbosity:
            self.stdout.write('%r.%s: ' % (model, field_name))

        for pk in model.objects.order_by('pk').values_list('pk', flat=True):
            previous_state = workflow.initial_state

            qs = (log_model.objects.filter(content_type=model_type, content_id=pk)
                                   .order_by('timestamp'))
            if verbosity >= 2:
                self.stdout.write('\n  %d:' % pk)

            for log in qs:
                try:
                    transition = workflow.transitions[log.transition]
                except KeyError:
                    self.stderr.write("Unknown transition %s in log %d for %s %d\n" % (log.transition, log.pk, label, pk))
                    continue

                updated = False
                if not log.from_state:
                    log.from_state = previous_state
                    updated = True
                if not log.to_state:
                    log.to_state = workflow.transitions[log.transition].target
                    updated = True

                previous_state = log.to_state
                if updated:
                    log.save()
                    if verbosity:
                        self.stdout.write('.')

        if verbosity:
            self.stdout.write('\n')

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

"""Specific versions of XWorkflows to use with Django."""

from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes import models as ct_models
from django.core import exceptions
from django.forms import fields
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

from xworkflows import base

from .compat import force_text, now, python_2_unicode_compatible


State = base.State
AbortTransition = base.AbortTransition
ForbiddenTransition = base.ForbiddenTransition
InvalidTransitionError = base.InvalidTransitionError
WorkflowError = base.WorkflowError

transition = base.transition


class StateSelect(widgets.Select):
    """Custom 'select' widget to handle state retrieval."""

    def render(self, name, value, attrs=None, choices=()):
        """Handle a few expected values for rendering the current choice.

        Extracts the state name from StateWrapper and State object.
        """
        if isinstance(value, base.StateWrapper):
            state_name = value.state.name
        elif isinstance(value, base.State):
            state_name = value.name
        else:
            state_name = str(value)
        return super(StateSelect, self).render(name, state_name, attrs, choices)


class StateFieldProperty(object):
    """Property-like attribute for WorkflowEnabled classes.

    Similar to django.db.models.fields.subclassing.Creator, but doesn't raise
    AttributeError.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        """Retrieve the related attributed from a class / an instance.

        If retrieving from an instance, return the actual value; if retrieving
        from a class, return the workflow.
        """
        if instance:
            return instance.__dict__.get(self.field.name, self.field.workflow.initial_state)
        else:
            return self.field.workflow

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = self.field.to_python(value)


class StateField(models.Field):
    """Holds the current state of a WorkflowEnabled object."""

    default_error_messages = {
        'invalid': _("Choose a valid state."),
        'wrong_type': _("Please enter a valid value (got %r)."),
        'wrong_workflow': _("Please enter a value from the right workflow (got %r)."),
        'invalid_state': _("%s is not a valid state."),
    }
    description = _("State")

    DEFAULT_MAX_LENGTH = 16

    def __init__(self, workflow, **kwargs):
        if isinstance(workflow, type):
            workflow = workflow()
        self.workflow = workflow
        kwargs['choices'] = list(
            (st.name, st.title) for st in self.workflow.states)

        kwargs['max_length'] = max(
            kwargs.get('max_length', self.DEFAULT_MAX_LENGTH),
            max(len(st.name) for st in self.workflow.states))
        kwargs['blank'] = False
        kwargs['null'] = False
        kwargs['default'] = self.workflow.initial_state.name
        return super(StateField, self).__init__(**kwargs)

    def get_internal_type(self):
        return "CharField"

    def contribute_to_class(self, cls, name):
        """Contribute the state to a Model.

        Attaches a StateFieldProperty to wrap the attribute.
        """
        super(StateField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, StateFieldProperty(self))

    def to_python(self, value):
        """Converts the DB-stored value into a Python value."""
        if isinstance(value, base.StateWrapper):
            res = value
        else:
            if isinstance(value, base.State):
                state = value
            elif value is None:
                state = self.workflow.initial_state
            else:
                try:
                    state = self.workflow.states[value]
                except KeyError:
                    raise exceptions.ValidationError(self.error_messages['invalid'])
            res = base.StateWrapper(state, self.workflow)

        if res.state not in self.workflow.states:
            raise exceptions.ValidationError(self.error_messages['invalid'])

        return res

    def get_prep_value(self, value):
        """Prepares a value.

        Returns a State object.
        """
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        """Convert a value to DB storage.

        Returns the state name.
        """
        if not prepared:
            value = self.get_prep_value(value)
        return value.state.name

    def value_to_string(self, obj):
        """Convert a field value to a string.

        Returns the state name.
        """
        statefield = self.to_python(self._get_val_from_obj(obj))
        return statefield.state.name

    def validate(self, value, model_instance):
        """Validate that a given value is a valid option for a given model instance.

        Args:
            value (xworkflows.base.StateWrapper): The base.StateWrapper returned by to_python.
            model_instance: A WorkflowEnabled instance
        """
        if not isinstance(value, base.StateWrapper):
            raise exceptions.ValidationError(self.error_messages['wrong_type'] % value)
        elif not value.workflow == self.workflow:
            raise exceptions.ValidationError(self.error_messages['wrong_workflow'] % value.workflow)
        elif not value.state in self.workflow.states:
            raise exceptions.ValidationError(self.error_messages['invalid_state'] % value.state)

    def formfield(self, form_class=fields.ChoiceField, widget=StateSelect, **kwargs):
        return super(StateField, self).formfield(form_class, widget=widget, **kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)

        state_def = tuple(
            (str(st.name), str(st.name)) for st in self.workflow.states)
        initial_state_def = str(self.workflow.initial_state.name)

        workflow = (
            "__import__('xworkflows', globals(), locals()).base.WorkflowMeta("
            "'%(class_name)s', (), "
            "{'states': %(states)r, 'initial_state': %(initial_state)r})" % {
                'class_name': str(self.workflow.__class__.__name__),
                'states': state_def,
                'initial_state': initial_state_def,
            })
        kwargs['workflow'] = workflow

        return ('django_xworkflows.models.StateField', args, kwargs)


class WorkflowEnabledMeta(base.WorkflowEnabledMeta, models.base.ModelBase):
    """Metaclass for WorkflowEnabled objects."""

    @classmethod
    def _find_workflows(mcs, attrs):
        """Find workflow definition(s) in a WorkflowEnabled definition.

        This method overrides the default behavior from xworkflows in order to
        use our custom StateField objects.
        """
        workflows = {}
        for k, v in attrs.items():
            if isinstance(v, StateField):
                workflows[k] = v
        return workflows

    @classmethod
    def _add_workflow(mcs, field_name, state_field, attrs):
        """Attach the workflow to a set of attributes.

        Constructs the ImplementationWrapper for transitions, and adds them to
        the attributes dict.

        Args:
            field_name (str): name of the attribute where the StateField lives
            state_field (StateField): StateField describing that attribute
            attrs (dict): dictionary of attributes for the class being created
        """
        # No need to override the 'field_name' from attrs: it already contains
        # a valid value, and that would clash with django model inheritance.
        pass


class BaseWorkflowEnabled(base.BaseWorkflowEnabled):
    """Base class for all django models wishing to use a Workflow."""

    def _get_FIELD_display(self, field):
        if isinstance(field, StateField):
            value = getattr(self, field.attname)
            return force_text(value.title)
        else:
            return super(BaseWorkflowEnabled, self)._get_FIELD_display(field)


# Workaround for metaclasses on python2/3.
# Equivalent to:
# Python2
#
# class WorkflowEnabled(BaseWorkflowEnabled):
#     __metaclass__ = WorkflowEnabledMeta
#
# Python3
#
# class WorkflowEnabled(metaclass=WorkflowEnabledMeta):
#     pass

WorkflowEnabled = WorkflowEnabledMeta(str('WorkflowEnabled'), (BaseWorkflowEnabled,), {})


def get_default_log_model():
    """The default log model depends on whether the xworkflow_log app is there."""
    if 'django_xworkflows.xworkflow_log' in settings.INSTALLED_APPS:
        return 'xworkflow_log.TransitionLog'
    else:
        return ''


class DjangoImplementationWrapper(base.ImplementationWrapper):
    """Restrict execution of transitions within templates"""
    # django < 1.4
    alters_data = True
    # django >= 1.4
    do_not_call_in_templates = True


class TransactionalImplementationWrapper(DjangoImplementationWrapper):
    """Customize the base ImplementationWrapper to run into a db transaction."""

    def __call__(self, *args, **kwargs):
        with transaction.commit_on_success():
            return super(TransactionalImplementationWrapper, self).__call__(*args, **kwargs)


class Workflow(base.Workflow):
    """Extended workflow that handles object saving and logging to the database.

    Attributes:
        log_model (str): the name of the log model to use; if empty, logging to
            database will be disabled.
        log_model_class (obj): the class for the log model; resolved once django
            is completely loaded.
    """
    #: Behave properly in Django templates
    implementation_class = DjangoImplementationWrapper

    #: Save log to this django model (name of the model)
    log_model = get_default_log_model()

    #: Save log to this django model (actual class)
    log_model_class = None

    def __init__(self, *args, **kwargs):
        # Fetch 'log_model' if overridden.
        log_model = kwargs.pop('log_model', self.log_model)

        # Fetch 'log_model_class' if overridden.
        log_model_class = kwargs.pop('log_model_class', self.log_model_class)

        super(Workflow, self).__init__(*args, **kwargs)

        self.log_model = log_model
        self.log_model_class = log_model_class

    def _get_log_model_class(self):
        """Cache for fetching the actual log model object once django is loaded.

        Otherwise, import conflict occur: WorkflowEnabled imports <log_model>
        which tries to import all models to retrieve the proper model class.
        """
        if self.log_model_class is not None:
            return self.log_model_class

        app_label, model_label = self.log_model.rsplit('.', 1)
        self.log_model_class = models.get_model(app_label, model_label)
        return self.log_model_class

    def db_log(self, transition, from_state, instance, *args, **kwargs):
        """Logs the transition into the database."""
        if self.log_model:
            model_class = self._get_log_model_class()

            extras = {}
            for db_field, transition_arg, default in model_class.EXTRA_LOG_ATTRIBUTES:
                extras[db_field] = kwargs.get(transition_arg, default)

            return model_class.log_transition(
                    modified_object=instance,
                   transition=transition.name,
                   from_state=from_state.name,
                   to_state=transition.target.name,
                   **extras)

    def log_transition(self, transition, from_state, instance, *args, **kwargs):
        """Generic transition logging."""
        save = kwargs.pop('save', True)
        log = kwargs.pop('log', True)
        super(Workflow, self).log_transition(
            transition, from_state, instance, *args, **kwargs)
        if save:
            instance.save()
        if log:
            self.db_log(transition, from_state, instance, *args, **kwargs)


@python_2_unicode_compatible
class BaseTransitionLog(models.Model):
    """Abstract model for a minimal database logging setup.

    Class attributes:
        MODIFIED_OBJECT_FIELD (str): name of the field storing the modified
            object.
        EXTRA_LOG_ATTRIBUTES ((db_field, kwarg, default) list): Describes extra
            transition kwargs to store:
            - db_field is the name of the attribute where data should be stored
            - kwarg is the name of the keyword argument of the transition to
              record
            - default is the default value to store if no value was provided for
              kwarg in the transition's arguments

    Attributes:
        modified_object (django.db.model.Model): the object affected by this
            transition.
        from_state (str): the name of the origin state
        to_state (str): the name of the destination state
        transition (str): The name of the transition being performed.
        timestamp (datetime): The time at which the Transition was performed.
    """
    MODIFIED_OBJECT_FIELD = ''
    EXTRA_LOG_ATTRIBUTES = ()

    transition = models.CharField(_("transition"), max_length=255,
        db_index=True)
    from_state = models.CharField(_("from state"), max_length=255,
        db_index=True)
    to_state = models.CharField(_("to state"), max_length=255,
        db_index=True)
    timestamp = models.DateTimeField(_("performed at"),
        default=now, db_index=True)

    class Meta:
        ordering = ('-timestamp', 'transition')
        verbose_name = _('XWorkflow transition log')
        verbose_name_plural = _('XWorkflow transition logs')
        abstract = True

    def get_modified_object(self):
        if self.MODIFIED_OBJECT_FIELD:
            return getattr(self, self.MODIFIED_OBJECT_FIELD, None)
        return None

    @classmethod
    def log_transition(cls, transition, from_state, to_state, modified_object, **kwargs):
        kwargs.update({
            'transition': transition,
            'from_state': from_state,
            'to_state': to_state,
            cls.MODIFIED_OBJECT_FIELD: modified_object,
        })
        return cls.objects.create(**kwargs)

    def __str__(self):
        return '%r: %s -> %s at %s' % (self.get_modified_object(),
            self.from_state, self.to_state, self.timestamp.isoformat())


class GenericTransitionLog(BaseTransitionLog):
    """Abstract model for a minimal database logging setup.

    Specializes BaseTransitionLog to use a GenericForeignKey.

    Attributes:
        modified_object (django.db.model.Model): the object affected by this
            transition.
        from_state (str): the name of the origin state
        to_state (str): the name of the destination state
        transition (str): The name of the transition being performed.
        timestamp (datetime): The time at which the Transition was performed.
    """
    MODIFIED_OBJECT_FIELD = 'modified_object'

    content_type = models.ForeignKey(ct_models.ContentType,
                                     verbose_name=_("Content type"),
                                     blank=True, null=True)
    content_id = models.PositiveIntegerField(_("Content id"),
        blank=True, null=True, db_index=True)
    modified_object = generic.GenericForeignKey(
            ct_field="content_type",
            fk_field="content_id")

    class Meta:
        ordering = ('-timestamp', 'transition')
        verbose_name = _('XWorkflow transition log')
        verbose_name_plural = _('XWorkflow transition logs')
        abstract = True


class BaseLastTransitionLog(BaseTransitionLog):
    """Alternate abstract model holding only the latest transition."""

    class Meta:
        verbose_name = _('XWorkflow last transition log')
        verbose_name_plural = _('XWorkflow last transition logs')
        abstract = True

    @classmethod
    def _update_or_create(cls, unique_fields, **kwargs):
        last_transition, created = cls.objects.get_or_create(defaults=kwargs, **unique_fields)
        if not created:
            for field, value in kwargs.items():
                setattr(last_transition, field, value)
            last_transition.save()

        return last_transition

    @classmethod
    def log_transition(cls, transition, from_state, to_state, modified_object, **kwargs):
        kwargs.update({
            'transition': transition,
            'from_state': from_state,
            'to_state': to_state,
        })

        non_defaults = {
            cls.MODIFIED_OBJECT_FIELD: modified_object,
        }

        return cls._update_or_create(non_defaults, **kwargs)


class GenericLastTransitionLog(BaseLastTransitionLog):
    """Abstract model for a minimal database logging setup.

    Specializes BaseLastTransitionLog to use a GenericForeignKey.

    Attributes:
        modified_object (django.db.model.Model): the object affected by this
            transition.
        from_state (str): the name of the origin state
        to_state (str): the name of the destination state
        transition (str): The name of the transition being performed.
        timestamp (datetime): The time at which the Transition was performed.
    """
    MODIFIED_OBJECT_FIELD = 'modified_object'

    content_type = models.ForeignKey(ct_models.ContentType,
                                     verbose_name=_("Content type"),
                                     related_name='last_transition_logs',
                                     blank=True, null=True)
    content_id = models.PositiveIntegerField(_("Content id"),
        blank=True, null=True, db_index=True)
    modified_object = generic.GenericForeignKey(
            ct_field="content_type",
            fk_field="content_id")

    class Meta:
        verbose_name = _('XWorkflow last transition log')
        verbose_name_plural = _('XWorkflow last transition logs')
        abstract = True
        unique_together =  ('content_type', 'content_id')

    @classmethod
    def _update_or_create(cls, unique_fields, **kwargs):
        modified_object = unique_fields.pop(cls.MODIFIED_OBJECT_FIELD)
        content_type = ct_models.ContentType.objects.get_for_model(modified_object.__class__)
        content_id = modified_object.id

        unique_fields['content_type'] = content_type
        unique_fields['content_id'] = content_id

        return super(GenericLastTransitionLog, cls)._update_or_create(unique_fields, **kwargs)


########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

from . import models

from django.contrib import admin


class TransitionLogAdmin(admin.ModelAdmin):
    actions = None
    date_hierarchy = 'timestamp'
    list_display = ('modified_object', 'transition', 'from_state', 'to_state', 'user', 'timestamp',)
    list_filter = ('content_type', 'transition',)
    read_only_fields = ('user', 'modified_object', 'transition', 'timestamp',)
    search_fields = ('transition', 'user__username',)

    def has_add_permission(self, request):
        return False

    # Allow viewing objects but not actually changing them
    def has_change_permission(self, request, obj=None):
        return request.method == 'GET'

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(models.TransitionLog, TransitionLogAdmin)

########NEW FILE########
__FILENAME__ = 0001_add_transitionlog
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.conf import settings
from django.db import connection
from django.db import models


XWORKFLOWS_USER_MODEL = getattr(settings, 'XWORKFLOWS_USER_MODEL',
    getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))

class Migration(SchemaMigration):

    def forwards(self, orm):

        if 'django_xworkflows_transitionlog' in connection.introspection.table_names():
            db.rename_table('django_xworkflows_transitionlog', 'xworkflow_log_transitionlog')
        else:
            # Adding model 'TransitionLog'
            db.create_table('xworkflow_log_transitionlog', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='workflow_object', null=True, to=orm['contenttypes.ContentType'])),
                ('content_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
                ('transition', self.gf('django.db.models.fields.CharField')(max_length=255)),
                ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[XWORKFLOWS_USER_MODEL], null=True, blank=True)),
                ('timestamp', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ))

        db.send_create_signal('xworkflow_log', ['TransitionLog'])


    def backwards(self, orm):
        # Deleting model 'TransitionLog'
        db.delete_table('xworkflow_log_transitionlog')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        XWORKFLOWS_USER_MODEL.lower(): {
            'Meta': {'object_name': XWORKFLOWS_USER_MODEL.split('.')[1]},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'xworkflow_log.transitionlog': {
            'Meta': {'ordering': "('-timestamp', 'user', 'transition')", 'object_name': 'TransitionLog'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'transition': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % XWORKFLOWS_USER_MODEL, 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['xworkflow_log']

########NEW FILE########
__FILENAME__ = 0002_add_transitionlog_fromstate
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.conf import settings
from django.db import models

XWORKFLOWS_USER_MODEL = getattr(settings, 'XWORKFLOWS_USER_MODEL',
    getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TransitionLog.from_state'
        db.add_column('xworkflow_log_transitionlog', 'from_state', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TransitionLog.from_state'
        db.delete_column('xworkflow_log_transitionlog', 'from_state')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        XWORKFLOWS_USER_MODEL.lower(): {
            'Meta': {'object_name': XWORKFLOWS_USER_MODEL.split('.')[1]},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'xworkflow_log.transitionlog': {
            'Meta': {'ordering': "('-timestamp', 'user', 'transition')", 'object_name': 'TransitionLog'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'from_state': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'transition': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % XWORKFLOWS_USER_MODEL, 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['xworkflow_log']

########NEW FILE########
__FILENAME__ = 0003_add_transitionlog_tostate
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.conf import settings
from django.db import models


XWORKFLOWS_USER_MODEL = getattr(settings, 'XWORKFLOWS_USER_MODEL',
    getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'TransitionLog.to_state'
        db.add_column('xworkflow_log_transitionlog', 'to_state', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'TransitionLog.to_state'
        db.delete_column('xworkflow_log_transitionlog', 'to_state')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        XWORKFLOWS_USER_MODEL.lower(): {
            'Meta': {'object_name': XWORKFLOWS_USER_MODEL.split('.')[1]},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'xworkflow_log.transitionlog': {
            'Meta': {'ordering': "('-timestamp', 'user', 'transition')", 'object_name': 'TransitionLog'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'from_state': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'to_state': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'transition': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % XWORKFLOWS_USER_MODEL, 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['xworkflow_log']

########NEW FILE########
__FILENAME__ = 0004_add_indexes
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.conf import settings
from django.db import models


XWORKFLOWS_USER_MODEL = getattr(settings, 'XWORKFLOWS_USER_MODEL',
    getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'TransitionLog', fields ['from_state']
        db.create_index('xworkflow_log_transitionlog', ['from_state'])

        # Adding index on 'TransitionLog', fields ['to_state']
        db.create_index('xworkflow_log_transitionlog', ['to_state'])

        # Adding index on 'TransitionLog', fields ['timestamp']
        db.create_index('xworkflow_log_transitionlog', ['timestamp'])

        # Adding index on 'TransitionLog', fields ['transition']
        db.create_index('xworkflow_log_transitionlog', ['transition'])

        # Adding index on 'TransitionLog', fields ['content_id']
        db.create_index('xworkflow_log_transitionlog', ['content_id'])


    def backwards(self, orm):
        # Removing index on 'TransitionLog', fields ['content_id']
        db.delete_index('xworkflow_log_transitionlog', ['content_id'])

        # Removing index on 'TransitionLog', fields ['transition']
        db.delete_index('xworkflow_log_transitionlog', ['transition'])

        # Removing index on 'TransitionLog', fields ['timestamp']
        db.delete_index('xworkflow_log_transitionlog', ['timestamp'])

        # Removing index on 'TransitionLog', fields ['to_state']
        db.delete_index('xworkflow_log_transitionlog', ['to_state'])

        # Removing index on 'TransitionLog', fields ['from_state']
        db.delete_index('xworkflow_log_transitionlog', ['from_state'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        XWORKFLOWS_USER_MODEL.lower(): {
            'Meta': {'object_name': XWORKFLOWS_USER_MODEL.split('.')[1]},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'xworkflow_log.transitionlog': {
            'Meta': {'ordering': "('-timestamp', 'transition')", 'object_name': 'TransitionLog'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'from_state': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'to_state': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'transition': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % XWORKFLOWS_USER_MODEL, 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['xworkflow_log']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

from django.conf import settings
from django.db import models as django_models
from django.utils.translation import ugettext_lazy as _

from .. import models


class TransitionLog(models.GenericTransitionLog):
    """The log for a transition.

    Attributes:
        modified_object (django.db.model.Model): the object affected by this
            transition.
        from_state (str): the name of the origin state
        to_state (str): the name of the destination state
        transition (str): The name of the transition being performed.
        timestamp (datetime): The time at which the Transition was performed.
        user (django.contrib.auth.user): the user performing the transition; the
            actual model to use here is defined in the XWORKFLOWS_USER_MODEL
            setting.
    """
    # Additional keyword arguments to store, if provided
    EXTRA_LOG_ATTRIBUTES = (
        ('user', 'user', None),  # Store the 'user' kwarg to transitions.
    )

    user = django_models.ForeignKey(
        getattr(settings, 'XWORKFLOWS_USER_MODEL',
            getattr(settings, 'AUTH_USER_MODEL', 'auth.User')),
        blank=True, null=True, verbose_name=_("author"))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-xworkflows documentation build configuration file, created by
# sphinx-quickstart on Fri Jul  8 16:55:05 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

from __future__ import unicode_literals

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'django-xworkflows'
copyright = '2011-2013, Raphaël Barrois'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
root_dir = os.path.abspath(os.path.dirname(__file__))
def get_version():
    import re
    version_re = re.compile(r"^__version__ = '([\w_.-]+)'$")
    with open(os.path.join(root_dir, os.pardir, 'django_xworkflows', '__init__.py')) as f:
        for line in f:
            match = version_re.match(line[:-1])
            if match:
                return match.groups()[0]
    return '0.0.0'

release = get_version()
version = '.'.join(release.split('.')[:2])

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

intersphinx_mapping = {
    'xworkflows': ('http://readthedocs.org/docs/xworkflows/en/latest/', None),
    'django': ('http://docs.djangoproject.com/en/dev/',
               'http://docs.djangoproject.com/en/dev/_objects/'),
}

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
htmlhelp_basename = 'django-xworkflowsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-xworkflows.tex', 'django-xworkflows Documentation',
   'Raphaël Barrois', 'manual'),
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
    ('index', 'django-xworkflows', 'django-xworkflows Documentation',
     ['Raphaël Barrois'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dev.settings')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

from django.db import models
import xworkflows

from django_xworkflows import models as dxmodels

class MyWorkflow(dxmodels.Workflow):
    states = (
        ('foo', "Foo"),
        ('bar', "Bar"),
        ('baz', "Baz"),
    )
    transitions = (
        ('foobar', 'foo', 'bar'),
        ('gobaz', ('foo', 'bar'), 'baz'),
        ('bazbar', 'baz', 'bar'),
    )
    initial_state = 'foo'

    implementation_class = dxmodels.TransactionalImplementationWrapper


class MyAltWorkflow(dxmodels.Workflow):
    states = (
        ('a', 'StateA'),
        ('b', 'StateB'),
        ('c', 'StateC'),
        ('something_very_long', "A very long name"),
    )
    transitions = (
        ('tob', ('a', 'c'), 'b'),
        ('toa', ('b', 'c'), 'a'),
        ('toc', ('a', 'b'), 'c'),
    )
    initial_state = 'a'

    log_model = ''


class MyWorkflowEnabled(dxmodels.WorkflowEnabled, models.Model):
    OTHER_CHOICES = (
        ('aaa', "AAA"),
        ('bbb', "BBB"),
    )

    state = dxmodels.StateField(MyWorkflow)
    other = models.CharField(max_length=4, choices=OTHER_CHOICES)

    def fail_if_fortytwo(self, res, *args, **kwargs):
        if res == 42:
            raise ValueError()

    @dxmodels.transition(after=fail_if_fortytwo)
    def gobaz(self, foo, save=True):
        return foo * 2

    @xworkflows.on_enter_state(MyWorkflow.states.bar)
    def hook_enter_baz(self, *args, **kwargs):
        self.other = 'aaa'


class WithTwoWorkflows(dxmodels.WorkflowEnabled, models.Model):
    state1 = dxmodels.StateField(MyWorkflow())
    state2 = dxmodels.StateField(MyAltWorkflow())


class SomeWorkflowLastTransitionLog(dxmodels.BaseLastTransitionLog):
    MODIFIED_OBJECT_FIELD = 'obj'
    obj = models.OneToOneField('djworkflows.SomeWorkflowEnabled')


class SomeWorkflow(dxmodels.Workflow):
    states = (
        ('a', 'A'),
        ('b', 'B'),
    )
    transitions = (
        ('ab', 'a', 'b'),
        ('ba', 'b', 'a'),
    )
    initial_state = 'a'

    log_model_class = SomeWorkflowLastTransitionLog


class SomeWorkflowEnabled(dxmodels.WorkflowEnabled, models.Model):
    state = dxmodels.StateField(SomeWorkflow)


class GenericWorkflowLastTransitionLog(dxmodels.GenericLastTransitionLog):
    pass


class GenericWorkflow(dxmodels.Workflow):
    states = (
        ('a', 'A'),
        ('b', 'B'),
    )
    transitions = (
        ('ab', 'a', 'b'),
        ('ba', 'b', 'a'),
    )
    initial_state = 'a'

    log_model_class = GenericWorkflowLastTransitionLog


class GenericWorkflowEnabled(dxmodels.WorkflowEnabled, models.Model):
    state = dxmodels.StateField(GenericWorkflow)


class GenericWorkflowTransitionLog(dxmodels.GenericTransitionLog):
    """This model ensures different GenericTransitionLog may exist together."""

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

import sys

from django import VERSION as django_version
from django.core import exceptions
from django.core import serializers
from django.db import models as django_models
from django import template
from django import test
from django.template import Template, Context
from django.utils import unittest

import xworkflows

from django_xworkflows import models as xwf_models
from django_xworkflows.xworkflow_log import models as xwlog_models

try:
    import south
    import south.orm
    import south.creator.freezer
    import south.modelsinspector
except ImportError:
    south = None

if sys.version_info[0] <= 2:
    def text_type(text):
        return unicode(text)
else:
    def text_type(text):
        return str(text)

from . import models


class ModelTestCase(test.TestCase):
    def test_workflow(self):
        self.assertEqual(models.MyWorkflow.states,
                         models.MyWorkflowEnabled._workflows['state'].workflow.states)

    def test_field_attributes(self):
        field_def = models.MyWorkflowEnabled._meta.get_field_by_name('state')[0]
        self.assertEqual(16, field_def.max_length)
        self.assertFalse(field_def.blank)
        self.assertFalse(field_def.null)
        self.assertEqual(models.MyWorkflow.initial_state.name, field_def.default)
        self.assertEqual(
            list((st.name, st.title) for st in models.MyWorkflow.states),
            field_def.choices,
        )

    def test_ald_field_attributes(self):
        field_def = models.WithTwoWorkflows._meta.get_field_by_name('state2')[0]
        self.assertEqual(19, field_def.max_length)
        self.assertFalse(field_def.blank)
        self.assertFalse(field_def.null)
        self.assertEqual(models.MyAltWorkflow.initial_state.name, field_def.default)
        self.assertEqual(
            list((st.name, st.title) for st in models.MyAltWorkflow.states),
            field_def.choices,
        )

    def test_dual_workflows(self):
        self.assertIn('state1', models.WithTwoWorkflows._workflows)
        self.assertIn('state2', models.WithTwoWorkflows._workflows)

        self.assertEqual('Foo',
                models.WithTwoWorkflows._workflows['state1'].workflow.states['foo'].title)
        self.assertEqual('StateA',
                models.WithTwoWorkflows._workflows['state2'].workflow.states['a'].title)

    def test_instantiation(self):
        o = models.MyWorkflowEnabled()
        self.assertEqual(models.MyWorkflow.states['foo'], o.state)

    def test_instantiation_from_empty(self):
        o = models.MyWorkflowEnabled(state=None)
        self.assertEqual(models.MyWorkflow.states['foo'], o.state)

    def test_class_attribute(self):
        self.assertEqual(models.MyWorkflow, models.MyWorkflowEnabled.state.__class__)

    def test_setting_state(self):
        o = models.MyWorkflowEnabled()
        self.assertEqual(models.MyWorkflow.states['foo'], o.state)

        o.state = models.MyWorkflow.states['bar']

        self.assertEqual(models.MyWorkflow.states['bar'], o.state)

    def test_setting_invalid_state(self):
        o = models.MyWorkflowEnabled()
        self.assertEqual(models.MyWorkflow.states['foo'], o.state)

        def set_invalid_state():
            o.state = models.MyAltWorkflow.states['a']

        self.assertRaises(exceptions.ValidationError, set_invalid_state)
        self.assertEqual(models.MyWorkflow.states['foo'], o.state)

    def test_display(self):
        o = models.MyWorkflowEnabled(other='aaa')
        self.assertEqual("Foo", o.get_state_display())
        self.assertEqual("AAA", o.get_other_display())

    def test_queries(self):
        models.MyWorkflowEnabled.objects.all().delete()

        foo = models.MyWorkflow.states.foo
        bar = models.MyWorkflow.states.bar
        baz = models.MyWorkflow.states.baz

        models.MyWorkflowEnabled.objects.create(state=foo)
        models.MyWorkflowEnabled.objects.create(state=bar)

        self.assertEqual(1, len(models.MyWorkflowEnabled.objects.filter(state=foo)))
        self.assertEqual(1, len(models.MyWorkflowEnabled.objects.filter(state=bar)))
        self.assertEqual(0, len(models.MyWorkflowEnabled.objects.filter(state=baz)))

    def test_dumping(self):
        o = models.MyWorkflowEnabled()
        o.state = o.state.workflow.states.bar
        o.save()

        self.assertTrue(o.state.is_bar)

        data = serializers.serialize('json',
                models.MyWorkflowEnabled.objects.filter(pk=o.id))

        models.MyWorkflowEnabled.objects.all().delete()

        for obj in serializers.deserialize('json', data):
            obj.object.save()

        obj = models.MyWorkflowEnabled.objects.all()[0]
        self.assertTrue(obj.state.is_bar)

    def test_invalid_dump(self):
        data = '[{"pk": 1, "model": "djworkflows.myworkflowenabled", "fields": {"state": "blah"}}]'

        if django_version[:3] >= (1, 4, 0):
            error_class = serializers.base.DeserializationError
        else:
            error_class = exceptions.ValidationError

        self.assertRaises(error_class, list,
            serializers.deserialize('json', data))


class InheritanceTestCase(test.TestCase):
    """Tests inheritance-related behaviour."""
    def test_simple(self):
        class BaseWorkflowEnabled(xwf_models.WorkflowEnabled, django_models.Model):
            state = xwf_models.StateField(models.MyWorkflow)

        class SubWorkflowEnabled(BaseWorkflowEnabled):
            pass

        obj = SubWorkflowEnabled()
        self.assertEqual(models.MyWorkflow.initial_state, obj.state)

    def test_abstract(self):
        class AbstractWorkflowEnabled(xwf_models.WorkflowEnabled, django_models.Model):
            state = xwf_models.StateField(models.MyWorkflow)
            class Meta:
                abstract = True

        class ConcreteWorkflowEnabled(AbstractWorkflowEnabled):
            pass

        obj = ConcreteWorkflowEnabled()
        self.assertEqual(models.MyWorkflow.initial_state, obj.state)


# Not a standard TestCase, since we're testing transactions.
class TransitionTestCase(test.TransactionTestCase):

    def setUp(self):
        self.obj = models.MyWorkflowEnabled()

    def test_transitions(self):
        self.assertEqual(models.MyWorkflow.states['foo'], self.obj.state)

        self.assertEqual(None, self.obj.foobar(save=False, log=False))

        self.assertTrue(self.obj.state.is_bar)

    def test_invalid_transition(self):
        self.assertTrue(self.obj.state.is_foo)

        self.assertRaises(xworkflows.InvalidTransitionError, self.obj.bazbar)

    def test_custom_transition_by_kw(self):
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)
        self.obj.foobar()
        self.assertEqual('abab', self.obj.gobaz(foo='ab'))

    def test_custom_transition_no_kw(self):
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)
        self.obj.foobar()
        self.assertEqual('abab', self.obj.gobaz('ab'))

    def test_hook(self):
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)
        self.assertEqual('', self.obj.other)
        self.obj.foobar()
        self.assertEqual('aaa', self.obj.other)

    def test_logging(self):
        xwlog_models.TransitionLog.objects.all().delete()

        self.obj.save()
        self.obj.foobar(save=False)

        trlog = xwlog_models.TransitionLog.objects.all()[0]
        self.assertEqual(self.obj, trlog.modified_object)
        self.assertEqual('foobar', trlog.transition)
        self.assertEqual(None, trlog.user)
        self.assertEqual('foo', trlog.from_state)
        self.assertEqual('bar', trlog.to_state)

        self.assertIn('foo -> bar', text_type(trlog))

    def test_no_logging(self):
        """Tests disabled transition logs."""
        xwlog_models.TransitionLog.objects.all().delete()

        obj = models.WithTwoWorkflows()
        obj.save()

        # No log model on MyAltWorkflow
        obj.tob()
        self.assertFalse(xwlog_models.TransitionLog.objects.exists())

        # Log model provided for MyWorkflow
        obj.foobar()
        self.assertTrue(xwlog_models.TransitionLog.objects.exists())

    def test_saving(self):
        self.obj.save()

        self.obj.foobar()

        obj = models.MyWorkflowEnabled.objects.get(pk=self.obj.id)

        self.assertEqual(models.MyWorkflow.states.bar, obj.state)

    def test_no_saving(self):
        self.obj.save()
        self.assertEqual(84, self.obj.gobaz(42, save=False))

        obj = models.MyWorkflowEnabled.objects.get(pk=self.obj.id)
        self.assertEqual(models.MyWorkflow.states.foo, obj.state)

    def test_transactions(self):
        self.obj.save()

        self.assertRaises(ValueError, self.obj.gobaz, 21)

        obj = models.MyWorkflowEnabled.objects.get(pk=self.obj.id)

        self.assertEqual(models.MyWorkflow.states.foo, obj.state)


class LastTransitionLogTestCase(test.TestCase):
    def setUp(self):
        self.obj = models.SomeWorkflowEnabled.objects.create()

    def test_transitions(self):
        self.assertEqual(0, models.SomeWorkflowLastTransitionLog.objects.count())

        self.obj.ab()
        self.assertEqual(1, models.SomeWorkflowLastTransitionLog.objects.count())
        tlog = models.SomeWorkflowLastTransitionLog.objects.get()
        self.assertEqual(self.obj, tlog.obj)
        self.assertEqual('ab', tlog.transition)
        self.assertEqual('a', tlog.from_state)
        self.assertEqual('b', tlog.to_state)

    def test_two_transitions(self):
        self.assertEqual(0, models.SomeWorkflowLastTransitionLog.objects.count())

        self.obj.ab()
        self.assertEqual(1, models.SomeWorkflowLastTransitionLog.objects.count())

        self.obj.ba()
        self.assertEqual(1, models.SomeWorkflowLastTransitionLog.objects.count())

        tlog = models.SomeWorkflowLastTransitionLog.objects.get()
        self.assertEqual(self.obj, tlog.obj)
        self.assertEqual('ba', tlog.transition)
        self.assertEqual('b', tlog.from_state)
        self.assertEqual('a', tlog.to_state)


class GenericLastTransitionLogTestCase(test.TestCase):
    def setUp(self):
        self.obj = models.GenericWorkflowEnabled.objects.create()

    def test_transitions(self):
        self.assertEqual(0, models.GenericWorkflowLastTransitionLog.objects.count())

        self.obj.ab()
        self.assertEqual(1, models.GenericWorkflowLastTransitionLog.objects.count())
        tlog = models.GenericWorkflowLastTransitionLog.objects.get()
        self.assertEqual(self.obj, tlog.modified_object)
        self.assertEqual('ab', tlog.transition)
        self.assertEqual('a', tlog.from_state)
        self.assertEqual('b', tlog.to_state)

    def test_two_transitions(self):
        self.assertEqual(0, models.GenericWorkflowLastTransitionLog.objects.count())

        self.obj.ab()
        self.assertEqual(1, models.GenericWorkflowLastTransitionLog.objects.count())

        self.obj.ba()
        self.assertEqual(1, models.GenericWorkflowLastTransitionLog.objects.count())

        tlog = models.GenericWorkflowLastTransitionLog.objects.get()
        self.assertEqual(self.obj, tlog.modified_object)
        self.assertEqual('ba', tlog.transition)
        self.assertEqual('b', tlog.from_state)
        self.assertEqual('a', tlog.to_state)


@unittest.skipIf(south is None, "Couldn't import south.")
class SouthTestCase(test.TestCase):
    """Tests south-related behavior."""

    frozen_workflow = (
        "__import__('xworkflows', globals(), locals()).base.WorkflowMeta("
        "'MyWorkflow', (), {'states': (('foo', 'foo'), ('bar', 'bar'), "
        "('baz', 'baz')), 'initial_state': 'foo'})")

    def test_south_triple(self):
        field = models.MyWorkflowEnabled._meta.get_field_by_name('state')[0]
        triple = field.south_field_triple()

        self.assertEqual(
            (
                'django_xworkflows.models.StateField',  # Class
                [],  # *args
                {
                    'default': "'foo'" if sys.version_info[0] >= 3 else "u'foo'",
                    'max_length': '16',
                    'workflow': self.frozen_workflow},  # **kwargs
            ), triple)

    def test_freezing_model(self):
        frozen = south.modelsinspector.get_model_fields(models.MyWorkflowEnabled)

        self.assertEqual(self.frozen_workflow, frozen['state'][2]['workflow'])

    def test_freezing_app(self):
        frozen = south.creator.freezer.freeze_apps('djworkflows')
        self.assertEqual(self.frozen_workflow, frozen['djworkflows.myworkflowenabled']['state'][2]['workflow'])

    def test_frozen_orm(self):
        frozen = south.creator.freezer.freeze_apps('djworkflows')

        class FakeMigration(object):
            models = frozen

        frozen_orm = south.orm.FakeORM(FakeMigration, 'djworkflows')

        frozen_model = frozen_orm.MyWorkflowEnabled
        frozen_field = frozen_model._meta.get_field_by_name('state')[0]

        for state in models.MyWorkflow.states:
            frozen_state = frozen_field.workflow.states[state.name]
            self.assertEqual(state.name, frozen_state.name)

        self.assertEqual(models.MyWorkflow.initial_state.name,
            frozen_field.workflow.initial_state.name)


class TemplateTestCase(test.TestCase):
    """Tests states and transitions behavior in templates."""

    uTrue = text_type(True)
    uFalse = text_type(False)

    def setUp(self):
        self.obj = models.MyWorkflowEnabled()
        self.context = template.Context({'obj': self.obj, 'true': self.uTrue, 'false': self.uFalse})

    def render_fragment(self, fragment):
        return template.Template(fragment).render(self.context)

    @unittest.skipIf(int(xworkflows.__version__.split('.')[0]) >= 1, "Behaviour changed in xworkflows-1.0.0")
    def test_state_display_is_title(self):
        self.assertEqual(self.render_fragment("{{obj.state}}"), self.obj.state.state.title)

    @unittest.skipIf(int(xworkflows.__version__.split('.')[0]) < 1, "Behaviour changed in xworkflows-1.0.0")
    def test_state_display_is_name(self):
        self.assertEqual(self.render_fragment("{{obj.state}}"), self.obj.state.state.name)

    def test_state(self):
        self.assertEqual(self.render_fragment("{{ obj.state.is_foo }}"), self.uTrue)
        self.assertEqual(self.render_fragment("{% if obj.state == 'foo' %}{{ true }}{% else %}{{ false }}{% endif %}"), self.uTrue)

        self.assertEqual(self.render_fragment("{{ obj.state.is_bar }}"), self.uFalse)
        self.assertEqual(self.render_fragment("{% if obj.state == 'bar' %}{{ true }}{% else %}{{ false }}{% endif %}"), self.uFalse)

    def test_django_magic(self):
        """Ensure that ImplementationWrappers have magic django attributes."""
        self.assertTrue(self.obj.foobar.alters_data)
        self.assertTrue(self.obj.foobar.do_not_call_in_templates)

    @unittest.skipIf(django_version[:2] >= (1, 4), "foo.do_not_call_in_templates implemented since django>=1.4")
    def test_transition_hidden(self):
        """Tests that django (<1.4) will prevent calling the template."""

        self.assertEqual(self.render_fragment("{{ obj.foobar}}"), "")
        self.assertEqual(self.render_fragment("{{ obj.foobar.is_available }}"), "")
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)

        self.assertEqual(self.render_fragment("{{ obj.bazbar|safe}}"), "")
        self.assertEqual(self.render_fragment("{{ obj.bazbar.is_available }}"), "")
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)

    @unittest.skipIf(django_version[:2] < (1, 4), "foo.do_not_call_in_templates requires django>=1.4")
    def test_transaction_attributes(self):
        self.assertEqual(self.render_fragment("{{ obj.foobar|safe}}"), text_type(self.obj.foobar))
        self.assertEqual(self.render_fragment("{{ obj.foobar.is_available }}"), self.uTrue)
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)

        self.assertEqual(self.render_fragment("{{ obj.bazbar|safe}}"), text_type(self.obj.bazbar))
        self.assertEqual(self.render_fragment("{{ obj.bazbar.is_available }}"), self.uFalse)
        self.assertEqual(models.MyWorkflow.states.foo, self.obj.state)

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2013 Raphaël Barrois
# This code is distributed under the two-clause BSD license.

from __future__ import unicode_literals

import os
import sys

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'tests.djworkflows',
            'django_xworkflows',
            'django_xworkflows.xworkflow_log',
        ]
    )

from django.test import simple


def runtests(*test_args):
    if not test_args:
        test_args = ('djworkflows',)
    runner = simple.DjangoTestSuiteRunner(failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])


########NEW FILE########
